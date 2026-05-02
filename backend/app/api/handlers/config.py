"""
Configuration and force-override handlers.
"""
from app.api.connection import ConnectionManager, SimulationState
from app.models.payloads import (
    CheckModelPayload,
    ConfigureScenePayload,
    ForceEmotionPayload,
    ForceGivePropPayload,
    ForceSceneTensionPayload,
)
from app.models.state import AgentState, EmotionVector, ModelConfig, Prop


async def handle_configure_scene(
    manager: ConnectionManager,
    sim: SimulationState,
    payload: ConfigureScenePayload,
) -> None:
    async with sim.lock:
        try:
            # Update scene metadata if provided
            if payload.scene_name:
                sim.state.scene.active_scene = payload.scene_name
            if payload.location:
                sim.state.scene.world_state.location = payload.location
            if payload.lighting:
                sim.state.scene.world_state.lighting = payload.lighting

            new_agents: dict = {}
            for char in payload.agents:
                char_id = char.get("id")
                new_agents[char_id] = AgentState(
                    id=char_id,
                    hidden_agenda=char.get("hidden_agenda"),
                    traits=char.get("traits"),
                    emotions=EmotionVector(
                        **char.get("emotions", {
                            "tension": 0.5, "affection": 0.5,
                            "energy": 0.5, "suspicion": 0.5,
                        })
                    ),
                    llm_config=ModelConfig(**char.get("llm_config", {})),
                )
            sim.state.agents = new_agents
            
            # Update props if provided
            if payload.props is not None:
                sim.state.scene.world_state.props = [
                    Prop(
                        id=p.get("id", "Prop"),
                        owner=p.get("owner", "world"),
                        description=p.get("description", ""),
                        visibility=p.get("visibility", "visible")
                    ) for p in payload.props
                ]

            # Ensure next_speaker is valid
            if new_agents:
                sim.state.next_speaker = list(new_agents.keys())[0]

            # Reset history and turn count for the "fresh start"
            sim.state.scene.turn_count = 0
            sim.state.chat_history = []
            sim.history = [sim.snapshot()]

            await manager.broadcast({
                "type": "action",
                "content": f"[SYSTEM]: Simulation reset and configured with {len(new_agents)} actors.",
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
        except Exception as e:
            print(f"[Config] Error: {e}")
            await manager.broadcast({
                "type": "action",
                "content": f"[ERROR]: Configuration failed: {e}",
            })


async def handle_check_model(
    manager: ConnectionManager,
    sim: SimulationState,
    payload: CheckModelPayload,
    websocket,
) -> None:
    try:
        from langchain_core.messages import HumanMessage
        from app.agents.llm import get_model

        config = ModelConfig(**payload.llm_config)
        model = get_model(config)
        await model.ainvoke([HumanMessage(content="Is anyone there? Respond with one word.")])
        await websocket.send_json({
            "type": "check_result",
            "status": "ok",
            "agent_id": payload.agent_id,
        })
    except Exception as e:
        await websocket.send_json({
            "type": "check_result",
            "status": "error",
            "message": str(e),
            "agent_id": payload.agent_id,
        })


async def handle_force_give_prop(
    manager: ConnectionManager,
    sim: SimulationState,
    payload: ForceGivePropPayload,
) -> None:
    for p in sim.state.scene.world_state.props:
        if p.id == payload.prop_id:
            p.owner = payload.owner
            break
    await manager.broadcast({
        "type": "action",
        "content": f"[DIRECTOR INJECTS]: Forced '{payload.prop_id}' to be owned by {payload.owner}.",
    })
    await manager.broadcast({
        "type": "world_update",
        "world": sim.state.scene.world_state.model_dump(),
    })
    sim.update_last_history()


async def handle_force_emotion(
    manager: ConnectionManager,
    sim: SimulationState,
    payload: ForceEmotionPayload,
) -> None:
    if payload.agent_id in sim.state.agents:
        setattr(sim.state.agents[payload.agent_id].emotions, payload.emotion, payload.value)
        await manager.broadcast({
            "type": "agents_update",
            "agents": [v.model_dump() for v in sim.state.agents.values()],
        })

async def handle_system_reset(
    manager: ConnectionManager,
    sim: SimulationState,
) -> None:
    """Factory reset — wipe everything back to hardcoded Neon Heist."""
    async with sim.lock:
        sim.cancel_task()
        sim.reset(preserve_agents=False)

    await manager.broadcast({"type": "history_reset", "messages": [], "monologues": []})
    await manager.broadcast({
        "type": "action",
        "content": "[SYSTEM]: ⚠️ Full Factory Reset initiated. All custom blueprints cleared.",
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
async def handle_force_scene_tension(
    manager: ConnectionManager,
    sim: SimulationState,
    payload: ForceSceneTensionPayload,
) -> None:
    sim.state.scene.narrative_tension = payload.value
    await manager.broadcast({
        "type": "vitals_update",
        "vitals": {
            "tension": sim.state.scene.narrative_tension,
            "energy": 0.5,
        },
    })
