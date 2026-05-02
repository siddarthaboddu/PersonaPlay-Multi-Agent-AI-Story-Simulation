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

                # Merge result back into sim.state
                if isinstance(new_state, dict):
                    sim.state.chat_history = new_state.get("chat_history", sim.state.chat_history)
                    sim.state.next_speaker = new_state.get("next_speaker", sim.state.next_speaker)
                    scene_val = new_state.get("scene")
                    if scene_val is not None:
                        tc = (
                            scene_val.get("turn_count")
                            if isinstance(scene_val, dict)
                            else getattr(scene_val, "turn_count", None)
                        )
                        if tc is not None:
                            sim.state.scene.turn_count = tc
                else:
                    sim.state = new_state

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
