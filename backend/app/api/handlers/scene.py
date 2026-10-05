"""
Scene lifecycle handlers: start, stop, get state.
"""
from app.api.connection import ConnectionManager, SimulationState
from app.models.payloads import (
    GetStatePayload,
    PauseScenePayload,
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
        from app.agents.llm import reset_summary_cache
        reset_summary_cache()
        
        # Session Reset (preserves current Blueprint: scene metadata + agent roster)
        sim.state.scene.turn_count = 0
        sim.state.chat_history = []
        for agent in sim.state.agents.values():
            agent.emotions.tension = 0.5
            agent.emotions.energy = 0.8
            agent.emotions.affection = 0.5
            agent.emotions.suspicion = 0.5
            agent.current_goal = agent.starting_goal
            agent.current_attention = None
            agent.beliefs = list(agent.starting_beliefs)
            agent.known_secrets = []
            agent.pending_whisper = None
            agent.last_addressee = None
            agent.last_spoke_turn = -1
        
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
    await manager.broadcast({
        "type": "vitals_update",
        "vitals": {
            "scene_name": sim.state.scene.active_scene,
            "tension": sim.state.scene.narrative_tension,
            "energy": 0.8,
            "turn_count": 0,
        },
    })
async def handle_stop_scene(
    manager: ConnectionManager,
    sim: SimulationState,
    payload: StopScenePayload,
) -> None:
    async with sim.lock:
        sim.cancel_task()
    await manager.broadcast({
        "type": "action",
        "content": "[SYSTEM]: 🛑 Simulation forcibly stopped.",
    })


async def handle_pause_scene(
    manager: ConnectionManager,
    sim: SimulationState,
    payload: PauseScenePayload,
) -> None:
    async with sim.lock:
        sim.cancel_task()
    await manager.broadcast({
        "type": "action",
        "content": "[SYSTEM]: ⏸ Simulation paused. Enter character dialogue or resume when ready.",
    })
    # Broadcast vitals to release any processing state
    await manager.broadcast({
        "type": "vitals_update",
        "vitals": {
            "scene_name": sim.state.scene.active_scene,
            "tension": sim.state.scene.narrative_tension,
            "energy": 0.8,
            "turn_count": sim.state.scene.turn_count,
        },
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
    await websocket.send_json({
        "type": "vitals_update",
        "vitals": {
            "scene_name": sim.state.scene.active_scene,
            "tension": sim.state.scene.narrative_tension,
            "energy": 0.8,
            "turn_count": sim.state.scene.turn_count,
        },
    })
