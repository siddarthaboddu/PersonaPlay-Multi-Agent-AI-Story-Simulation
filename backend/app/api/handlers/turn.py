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

                # 1. Append only the NEW messages (preserving Director injections in between)
                new_lines = new_state.chat_history[len(snap.chat_history):]
                sim.state.chat_history.extend(new_lines)
                if len(sim.state.chat_history) > settings.history_window_size:
                    sim.state.chat_history = sim.state.chat_history[-settings.history_window_size:]
                
                # 2. Update next_speaker and turn_count
                sim.state.next_speaker = new_state.next_speaker
                sim.state.scene.turn_count = new_state.scene.turn_count

                # Manual-reply mode is consumed by this completed turn. Do not
                # let a later autonomous turn inherit the user's old instruction.
                if snap.manual_reply_content:
                    sim.state.manual_reply_speaker = None
                    sim.state.manual_reply_content = None

                # gossip_target is a one-shot per-turn signal. The actor already
                # resets it on its own copy each turn, but clear the live copy
                # too so a retake/rewind can never resurrect a stale leak.
                sim.state.gossip_target = None

                # 3. Merge Agent updates.
                #
                # This MUST copy every field the actor node mutates, not just a
                # hand-picked few. The graph works on its own deep copy, so any
                # field omitted here is silently discarded when that copy is
                # thrown away. Previously only `emotions` and `relationships`
                # survived, which silently killed two features:
                #   * `last_emote`   — emotes never reached the UI (always None)
                #   * `known_secrets` — the whole gossip engine reset every turn
                #
                # `pending_whisper` is deliberately excluded: it is a one-shot
                # directive owned by the Director, and turn.py already clears it
                # on the live agent once the speaker has consumed it.
                for aid, ag in new_state.agents.items():
                    if aid in sim.state.agents:
                        live = sim.state.agents[aid]
                        live.emotions = ag.emotions
                        live.relationships = ag.relationships
                        live.last_emote = ag.last_emote
                        live.known_secrets = ag.known_secrets
                        live.traits = ag.traits
                        live.hidden_agenda = ag.hidden_agenda
                        live.relationship_context = ag.relationship_context

                # 4. Selective World Update: Prop transfer and Location change
                for p_new in new_state.scene.world_state.props:
                    for p_curr in sim.state.scene.world_state.props:
                        if p_new.id == p_curr.id and p_new.owner != p_curr.owner:
                            p_curr.owner = p_new.owner
                            break
                if new_state.scene.world_state.location != snap.scene.world_state.location:
                    sim.state.scene.world_state.location = new_state.scene.world_state.location

                # 5. Extract actual speaker, monologue, and dialogue
                monologue = "(Thinking…)"
                dialogue = "…"
                for line in new_lines:
                    if "'s Thought]:" in line:
                        monologue = line.split("]:", 1)[-1].strip()
                    elif ":" in line:
                        dialogue = line

                actual_speaker = None
                if dialogue and ":" in dialogue:
                    cand = dialogue.split(":")[0].strip()
                    if cand in sim.state.agents:
                        actual_speaker = cand
                if not actual_speaker or actual_speaker not in sim.state.agents:
                    actual_speaker = sim.state.next_speaker

                # Clear consumed whisper for the speaker
                if actual_speaker in sim.state.agents:
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
                sim.state.scene.narrative_tension = min(
                    sim.state.scene.narrative_tension + 0.05, 1.0
                )
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
                        "phases_enabled": getattr(sim.state.scene, "phases_enabled", True),
                    },
                })

                # 5. Deep Memory Reflection: synthesize higher-level insights asynchronously
                turn_num = sim.state.scene.turn_count
                from app.agents.beats import get_beat
                current_beat = get_beat(turn_num)
                is_dramatic = any(k in current_beat.upper() for k in ["REVELATION", "CRISIS", "CLIMAX", "BREAKING POINT", "POWER SHIFT"])
                should_reflect = (turn_num > 0 and turn_num % 4 == 0) or is_dramatic

                if should_reflect and actual_speaker in sim.state.agents:
                    # Snapshot everything the background task needs NOW, then
                    # close over those locals. Do not read sim.state from inside
                    # the coroutine — it will have moved on by the time it runs.
                    _aid = actual_speaker
                    _ag = sim.state.agents[actual_speaker].model_copy(deep=True)
                    _tc = turn_num
                    _beat = current_beat
                    _chat = list(sim.state.chat_history)

                    async def run_reflection_bg():
                        try:
                            from app.agents.reflection import generate_reflections
                            new_insights = await generate_reflections(
                                _aid, _ag, _chat, _beat, _tc
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
            "phases_enabled": getattr(sim.state.scene, "phases_enabled", True),
        },
    })

    # Immediately trigger a fresh AI turn for the re-roll!
    await handle_next_turn(manager, sim, NextTurnPayload(type="next_turn"))

