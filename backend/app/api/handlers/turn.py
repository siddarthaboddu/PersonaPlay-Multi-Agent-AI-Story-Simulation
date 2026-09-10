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
from app.models.payloads import NextTurnPayload
from app.models.state import OrchestratorState


async def handle_next_turn(
    manager: ConnectionManager,
    sim: SimulationState,
    payload: NextTurnPayload,
) -> None:
    async with sim.lock:
        if sim.current_task and not sim.current_task.done():
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

                # 3. Merge Agent updates (emotions, etc.)
                for aid, ag in new_state.agents.items():
                    if aid in sim.state.agents:
                        sim.state.agents[aid].emotions = ag.emotions

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

                # 1. Broadcast monologue
                await manager.broadcast({
                    "type": "monologue",
                    "agent_id": actual_speaker,
                    "content": monologue,
                })

                await asyncio.sleep(1)  # visual pause

                # 2. Broadcast dialogue
                await manager.broadcast({
                    "type": "dialogue",
                    "agent_id": actual_speaker,
                    "content": dialogue,
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
                    },
                })

                # 5. Deep Memory Reflection: synthesize higher-level insights asynchronously
                turn_num = sim.state.scene.turn_count
                from app.agents.beats import get_beat
                current_beat = get_beat(turn_num)
                is_dramatic = any(k in current_beat.upper() for k in ["REVELATION", "CRISIS", "CLIMAX", "BREAKING POINT", "POWER SHIFT"])
                should_reflect = (turn_num > 0 and turn_num % 4 == 0) or is_dramatic

                if should_reflect and actual_speaker in sim.state.agents:
                    async def run_reflection_bg(
                        aid=actual_speaker,
                        ag=sim.state.agents[actual_speaker].model_copy(deep=True),
                        tc=turn_num,
                        beat_str=current_beat,
                        chat_snapshot=list(sim.state.chat_history),
                    ):
                        try:
                            from app.agents.reflection import generate_reflections
                            new_insights = await generate_reflections(aid, ag, chat_snapshot, beat_str, tc)
                            for ins in new_insights:
                                await manager.broadcast({
                                    "type": "insight_update",
                                    "agent_id": aid,
                                    "insight": ins,
                                    "turn": tc,
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

        sim.current_task = asyncio.create_task(run_turn())
