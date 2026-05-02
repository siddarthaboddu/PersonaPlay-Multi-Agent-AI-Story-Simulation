"""
Turn execution handler — runs one LangGraph turn in a background asyncio task.

The critical fix applied here vs. the original code:
  BEFORE: turn_state_snapshot = manager.state  (reference — mutable mid-flight!)
  AFTER:  snapshot = sim.snapshot()             (deep copy — immutable)
"""
import asyncio

from app.agents.graph import graph
from app.api.connection import ConnectionManager, SimulationState
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
                
                # 2. Update next_speaker and turn_count
                sim.state.next_speaker = new_state.next_speaker
                sim.state.scene.turn_count = new_state.scene.turn_count

                # 3. Merge Agent updates (emotions, etc.)
                for aid, ag in new_state.agents.items():
                    if aid in sim.state.agents:
                        sim.state.agents[aid].emotions = ag.emotions

                # 4. Selective World Update: Prop transfer
                for p_new in new_state.scene.world_state.props:
                    for p_curr in sim.state.scene.world_state.props:
                        if p_new.id == p_curr.id and p_new.owner != p_curr.owner:
                            p_curr.owner = p_new.owner
                            break

                chat_hist = sim.state.chat_history

                # Derive actual speaker from the last dialogue line (director already
                # advanced next_speaker, so it no longer points to who just spoke)
                actual_speaker = None
                for line in reversed(chat_hist):
                    if "'s Thought]:" not in line and ":" in line:
                        actual_speaker = line.split(":")[0].strip()
                        break
                if not actual_speaker or actual_speaker not in sim.state.agents:
                    actual_speaker = sim.state.next_speaker

                if len(chat_hist) >= 2:
                    monologue = chat_hist[-2]
                    if monologue.startswith("[") and "]:" in monologue:
                        monologue = monologue.split("]:", 1)[-1].strip()
                    dialogue = chat_hist[-1]
                else:
                    monologue = "(Thinking…)"
                    dialogue = "…"

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
