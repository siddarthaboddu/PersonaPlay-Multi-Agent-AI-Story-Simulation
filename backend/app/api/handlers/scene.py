"""
Scene lifecycle handlers: start, stop, get state, change scene.
"""
from app.api.connection import ConnectionManager, SimulationState
from app.models.payloads import (
    ChangeScenePayload,
    GetStatePayload,
    StartScenePayload,
    StopScenePayload,
)
from app.services.memory import clear_memories


async def handle_start_scene(
    manager: ConnectionManager,
    sim: SimulationState,
    payload: StartScenePayload,
) -> None:
    async with sim.lock:
        sim.cancel_task()
        await clear_memories()
        
        # Session Reset (preserves current Blueprint: scene metadata + agent roster)
        sim.state.scene.turn_count = 0
        sim.state.chat_history = []
        for agent in sim.state.agents.values():
            agent.emotions.tension = 0.5
            agent.emotions.energy = 0.8
            agent.emotions.affection = 0.5
            agent.emotions.suspicion = 0.5
        
        sim.history = [sim.snapshot()]

    await manager.broadcast({"type": "history_reset", "messages": [], "monologues": []})
    await manager.broadcast({
        "type": "action",
        "content": f"[SCENE START]: {sim.state.scene.active_scene}",
    })
    await manager.broadcast({
        "type": "action",
        "content": "[SYSTEM]: Stage is set. Click the 'Next Turn' button to trigger the first actor!",
    })
    await manager.broadcast({
        "type": "world_update",
        "world": sim.state.scene.world_state.model_dump(),
    })
    await manager.broadcast({
        "type": "agents_update",
        "agents": [v.model_dump() for v in sim.state.agents.values()],
    })


async def handle_stop_scene(
    manager: ConnectionManager,
    sim: SimulationState,
    payload: StopScenePayload,
) -> None:
    sim.cancel_task()
    await manager.broadcast({
        "type": "action",
        "content": "[SYSTEM]: 🛑 Simulation forcibly stopped.",
    })


async def handle_get_state(
    manager: ConnectionManager,
    sim: SimulationState,
    payload: GetStatePayload,
    websocket,
) -> None:
    await websocket.send_json({
        "type": "world_update",
        "world": sim.state.scene.world_state.model_dump(),
    })
    await websocket.send_json({
        "type": "agents_update",
        "agents": [v.model_dump() for v in sim.state.agents.values()],
    })


async def handle_change_scene(
    manager: ConnectionManager,
    sim: SimulationState,
    payload: ChangeScenePayload,
) -> None:
    if payload.location:
        sim.state.scene.world_state.location = payload.location
    if payload.scene_name:
        sim.state.scene.active_scene = payload.scene_name

    change_msg = f"[SCENE CHANGE]: Moved to {sim.state.scene.world_state.location}."
    sim.state.chat_history.append(change_msg)

    await manager.broadcast({"type": "action", "content": change_msg})
    await manager.broadcast({
        "type": "world_update",
        "world": sim.state.scene.world_state.model_dump(),
    })

    # ── Trigger Immediate AI Reaction ────────────────────────────────────────
    from app.api.handlers.turn import handle_next_turn
    from app.models.payloads import NextTurnPayload
    
    await handle_next_turn(manager, sim, NextTurnPayload(type="next_turn"))
