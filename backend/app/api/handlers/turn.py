"""
Turn execution handler — runs one LangGraph turn in a background asyncio task.

The critical fix applied here vs. the original code:
  BEFORE: turn_state_snapshot = manager.state  (reference — mutable mid-flight!)
  AFTER:  snapshot = sim.snapshot()             (deep copy — immutable)
"""
import asyncio

from app.agents.graph import graph
from app.api.connection import ConnectionManager, SimulationState
from app.config import settings
from app.models.payloads import NextTurnPayload, RetakeTurnPayload
from app.models.state import OrchestratorState


async def handle_next_turn(
    manager: ConnectionManager,
    sim: SimulationState,
    payload: NextTurnPayload,
) -> None:
    async with sim.lock:
        if sim.current_task and not sim.current_task.done():
            sim.pending_turn = True
            await manager.broadcast({
                "type": "action",
                "content": "[SYSTEM]: An AI turn is already in progress…",
            })
            return

        # ── CRITICAL: deep copy before the async closure captures it ─────────────
        snapshot = sim.snapshot()

        async def run_turn(snap=snapshot) -> None:
            try:
                await manager.broadcast({
                    "type": "action",
                    "content": "[SYSTEM]: Triggering AI turn…",
                })

                new_state = await graph.ainvoke(snap)

                # Merge result back into sim.state (Additively)
                if isinstance(new_state, dict):
                    new_state = OrchestratorState.model_validate(new_state)
                
                if not isinstance(new_state, OrchestratorState):
                    print(f"[Turn] Warning: new_state is not OrchestratorState ({type(new_state)})")
                    return

                scene_tension_delta = max(
                    -0.08,
                    min(0.08, new_state.scene.narrative_tension - snap.scene.narrative_tension),
                )

                async with sim.lock:
                    # Preserve live director actions made while the model ran.
                    new_lines = new_state.chat_history[len(snap.chat_history):]
                    sim.state.chat_history.extend(new_lines)
                    if len(sim.state.chat_history) > settings.history_window_size:
                        sim.state.chat_history = sim.state.chat_history[-settings.history_window_size:]

                    turn_delta = new_state.scene.turn_count - snap.scene.turn_count
                    sim.state.next_speaker = new_state.next_speaker
                    sim.state.scene.turn_count += turn_delta
                    sim.state.scene.narrative_tension = round(max(
                        0.0,
                        min(1.0, sim.state.scene.narrative_tension + scene_tension_delta),
                    ), 3)

                    if snap.manual_reply_content and sim.state.manual_reply_content == snap.manual_reply_content:
                        sim.state.manual_reply_speaker = None
                        sim.state.manual_reply_content = None
                    sim.state.gossip_target = None

                    # Apply actor changes as deltas so concurrent director
                    # slider edits remain authoritative while the turn runs.
                    for aid, ag in new_state.agents.items():
                        if aid not in sim.state.agents or aid not in snap.agents:
                            continue
                        live = sim.state.agents[aid]
                        old = snap.agents[aid]
                        for metric in ("tension", "affection", "energy", "suspicion"):
                            delta = getattr(ag.emotions, metric) - getattr(old.emotions, metric)
                            value = getattr(live.emotions, metric) + delta
                            setattr(live.emotions, metric, max(0.0, min(1.0, round(value, 3))))

                        for target, rel_new in ag.relationships.items():
                            rel_old = old.relationships.get(target)
                            if rel_old is None:
                                if target not in live.relationships:
                                    live.relationships[target] = rel_new.model_copy(deep=True)
                                continue
                            rel_live = live.relationships.get(target)
                            if rel_live is None:
                                continue
                            for metric in ("trust", "affinity", "fear", "dominance"):
                                delta = getattr(rel_new, metric) - getattr(rel_old, metric)
                                value = getattr(rel_live, metric) + delta
                                setattr(rel_live, metric, max(0.0, min(1.0, round(value, 3))))

                        if ag.last_emote != old.last_emote:
                            live.last_emote = ag.last_emote
                        for secret in ag.known_secrets:
                            if secret not in old.known_secrets and secret not in live.known_secrets:
                                live.known_secrets.append(secret)
                        if ag.current_goal != old.current_goal:
                            live.current_goal = ag.current_goal
                        if ag.current_attention != old.current_attention:
                            live.current_attention = ag.current_attention
                        for belief in old.beliefs:
                            if belief not in ag.beliefs and belief in live.beliefs:
                                live.beliefs.remove(belief)
                        for belief in ag.beliefs:
                            if belief not in old.beliefs and belief not in live.beliefs:
                                live.beliefs.append(belief)
                        live.beliefs = live.beliefs[-12:]
                        if ag.last_addressee != old.last_addressee:
                            live.last_addressee = ag.last_addressee
                        if ag.last_spoke_turn != old.last_spoke_turn:
                            live.last_spoke_turn = ag.last_spoke_turn

                    # Commit world changes only when the Director has not edited
                    # that same value since the snapshot was taken.
                    for p_new in new_state.scene.world_state.props:
                        p_old = next((p for p in snap.scene.world_state.props if p.id == p_new.id), None)
                        p_live = next((p for p in sim.state.scene.world_state.props if p.id == p_new.id), None)
                        if p_old and p_live and p_new.owner != p_old.owner and p_live.owner == p_old.owner:
                            p_live.owner = p_new.owner
                    if (
                        new_state.scene.world_state.location != snap.scene.world_state.location
                        and sim.state.scene.world_state.location == snap.scene.world_state.location
                    ):
                        sim.state.scene.world_state.location = new_state.scene.world_state.location

                    # Extract actual speaker, monologue, and dialogue.
                    monologue = "(Thinking…)"
                    dialogue = ""
                    for line in new_lines:
                        if "'s Thought]:" in line:
                            monologue = line.split("]:", 1)[-1].strip()
                        elif ":" in line:
                            dialogue = line

                    actual_speaker = new_state.next_speaker
                    if dialogue and ":" in dialogue:
                        candidate = dialogue.split(":", 1)[0].strip()
                        if candidate in sim.state.agents:
                            actual_speaker = candidate
                    if not actual_speaker or actual_speaker not in sim.state.agents:
                        actual_speaker = sim.state.next_speaker
                    # Clear only the whisper this turn consumed. Preserve a new
                    # whisper sent while generation was in flight.
                    if (
                        actual_speaker in sim.state.agents
                        and actual_speaker in snap.agents
                        and sim.state.agents[actual_speaker].pending_whisper
                        == snap.agents[actual_speaker].pending_whisper
                    ):
                        sim.state.agents[actual_speaker].pending_whisper = None

                # 1. Broadcast monologue
                await manager.broadcast({
                    "type": "monologue",
                    "agent_id": actual_speaker,
                    "content": monologue,
                })

                await asyncio.sleep(1)  # visual pause

                emote = sim.state.agents[actual_speaker].last_emote if actual_speaker in sim.state.agents else None
                # Read the authoritative flag the actor set, not a text search.
                # Matching "[GOSSIP LEAK]" in history produced false positives
                # whenever a character happened to say those words aloud.
                gossip_target = new_state.gossip_target
                is_gossip = bool(gossip_target)
                gossip_note = next((line for line in new_lines if "[GOSSIP LEAK]" in line), None)

                # 2. Broadcast dialogue
                if dialogue:
                    await manager.broadcast({
                        "type": "dialogue",
                        "agent_id": actual_speaker,
                        "content": dialogue,
                        "emote": emote,
                        "is_gossip": is_gossip,
                        "gossip_note": gossip_note,
                    })

                if is_gossip and gossip_note:
                    await manager.broadcast({
                        "type": "action",
                        "content": gossip_note,
                    })
                # 3. Broadcast world + agent updates
                await manager.broadcast({
                    "type": "world_update",
                    "world": sim.state.scene.world_state.model_dump(),
                })
                await manager.broadcast({
                    "type": "agents_update",
                    "agents": [v.model_dump() for v in sim.state.agents.values()],
                })

                # 4. Update narrative tension and broadcast vitals
                energy = (
                    sim.state.agents[actual_speaker].emotions.energy
                    if actual_speaker in sim.state.agents
                    else 0.5
                )
                await manager.broadcast({
                    "type": "vitals_update",
                    "vitals": {
                        "scene_name": sim.state.scene.active_scene,
                        "tension": sim.state.scene.narrative_tension,
                        "energy": energy,
                        "turn_count": sim.state.scene.turn_count,
                    },
                })

                # 5. Deep Memory Reflection: synthesize higher-level insights asynchronously
                turn_num = sim.state.scene.turn_count
                high_tension_event = (
                    sim.state.scene.narrative_tension >= 0.75
                    and scene_tension_delta >= 0.04
                )
                should_reflect = (turn_num > 0 and turn_num % 4 == 0) or high_tension_event

                if should_reflect and actual_speaker in sim.state.agents:
                    # Snapshot everything the background task needs NOW, then
                    # close over those locals. Do not read sim.state from inside
                    # the coroutine — it will have moved on by the time it runs.
                    async with sim.lock:
                        _aid = actual_speaker
                        _ag = sim.state.agents[actual_speaker].model_copy(deep=True)
                        _tc = turn_num
                        _scene_context = f"{sim.state.scene.active_scene}; tension {sim.state.scene.narrative_tension:.2f}"
                        _chat = list(sim.state.chat_history)

                    async def run_reflection_bg():
                        try:
                            from app.agents.reflection import generate_reflections
                            new_insights = await generate_reflections(
                                _aid, _ag, _chat, _scene_context, _tc
                            )
                            for ins in new_insights:
                                await manager.broadcast({
                                    "type": "insight_update",
                                    "agent_id": _aid,
                                    "insight": ins,
                                    "turn": _tc,
                                })
                        except Exception as ex:
                            print(f"[Turn] Background reflection error: {ex}")

                    asyncio.create_task(run_reflection_bg())

                async with sim.lock:
                    sim.push_history()

            except asyncio.CancelledError:
                print("[Turn] Cancelled by user.")
            except Exception as e:
                print(f"[Turn] Error: {e}")
                await manager.broadcast({
                    "type": "action",
                    "content": f"[ERROR]: AI Generation failed. Is LM Studio/OpenRouter running? {e}",
                })
            finally:
                async with sim.lock:
                    is_current = sim.current_task is asyncio.current_task()
                    if is_current:
                        sim.current_task = None
                    run_queued_turn = is_current and sim.pending_turn
                    if run_queued_turn:
                        sim.pending_turn = False
                if run_queued_turn:
                    await handle_next_turn(manager, sim, NextTurnPayload(type="next_turn"))

        sim.current_task = asyncio.create_task(run_turn())


async def handle_retake_turn(
    manager: ConnectionManager,
    sim: SimulationState,
    payload: RetakeTurnPayload,
) -> None:
    """Re-roll the most recent turn: pops the latest snapshot and re-invokes an AI turn."""
    async with sim.lock:
        sim.cancel_task()
        success = sim.restore(1)

    if not success:
        await manager.broadcast({
            "type": "action",
            "content": "[SYSTEM]: Cannot retake turn — at beginning of scene!",
        })
        return

    # Reconstruct history from the restored state
    reconstructed_messages = [
        {"type": "action", "content": "🎬 [DIRECTOR CALLS RETAKE]: Cut! Rolling take 2..."}
    ]
    reconstructed_monologues = []

    for line in sim.state.chat_history:
        if "'s Thought]:" in line:
            agent_id = line[1:line.find("'s")]
            content = line.split("]:", 1)[-1].strip()
            reconstructed_monologues.append({
                "type": "monologue",
                "agent_id": agent_id,
                "content": content,
            })
        elif line.startswith("["):
            reconstructed_messages.append({"type": "action", "content": line})
        else:
            agent_id = line.split(":")[0].strip() if ":" in line else None
            reconstructed_messages.append({
                "type": "dialogue",
                "agent_id": agent_id,
                "content": line,
            })

    await manager.broadcast({
        "type": "history_reset",
        "messages": reconstructed_messages,
        "monologues": reconstructed_monologues,
    })
    await manager.broadcast({
        "type": "world_update",
        "world": sim.state.scene.world_state.model_dump(),
    })
    await manager.broadcast({
        "type": "agents_update",
        "agents": [v.model_dump() for v in sim.state.agents.values()],
    })
    await manager.broadcast({
        "type": "vitals_update",
        "vitals": {
            "scene_name": sim.state.scene.active_scene,
            "tension": sim.state.scene.narrative_tension,
            "energy": 0.8,
            "turn_count": sim.state.scene.turn_count,
        },
    })

    # Immediately trigger a fresh AI turn for the re-roll!
    await handle_next_turn(manager, sim, NextTurnPayload(type="next_turn"))
