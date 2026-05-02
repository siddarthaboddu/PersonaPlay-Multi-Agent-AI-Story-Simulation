"""
Director-facing handlers: inject chaos commands, rewind turns, export script.
"""
from app.api.connection import ConnectionManager, SimulationState
from app.models.payloads import DirectorCommandPayload, ExportScriptPayload, RewindPayload
from app.services.image import build_scene_image_url


async def handle_director_command(
    manager: ConnectionManager,
    sim: SimulationState,
    payload: DirectorCommandPayload,
) -> None:
    async with sim.lock:
        command = payload.command

        if command.lower().startswith("generate image"):
            url, prompt = build_scene_image_url(sim.state.scene.world_state)
            await manager.broadcast({
                "type": "action",
                "content": "[DIRECTOR INJECTS]: Generating scene image…",
            })
            await manager.broadcast({"type": "image_update", "url": url, "prompt": prompt})
            return

        # Chaos injection
        chaos_msg = f"[DIRECTOR INJECTS]: {command}"
        sim.state.chat_history.append(chaos_msg)

        await manager.broadcast({"type": "action", "content": chaos_msg})
        sim.state.scene.narrative_tension = min(sim.state.scene.narrative_tension + 0.2, 1.0)
        await manager.broadcast({
            "type": "vitals_update",
            "vitals": {
                "tension": sim.state.scene.narrative_tension,
                "energy": 0.9,
            },
        })
        sim.update_last_history()

    # ── Trigger Immediate AI Reaction ────────────────────────────────────────
    # We do this OUTSIDE the lock to allow handle_next_turn to acquire it.
    from app.api.handlers.turn import handle_next_turn
    from app.models.payloads import NextTurnPayload
    
    await handle_next_turn(manager, sim, NextTurnPayload(type="next_turn"))


async def handle_rewind_turns(
    manager: ConnectionManager,
    sim: SimulationState,
    payload: RewindPayload,
) -> None:
    sim.cancel_task()
    success = sim.restore(payload.turns)

    if not success:
        await manager.broadcast({
            "type": "action",
            "content": "[SYSTEM]: Cannot rewind that far back!",
        })
        return

    reconstructed_messages = [
        {"type": "action", "content": f"[SYSTEM]: ⏪ Rewound {payload.turns} turns."}
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


async def handle_export_script(
    manager: ConnectionManager,
    sim: SimulationState,
    payload: ExportScriptPayload,
    websocket,
) -> None:
    """
    Instead of writing to disk (useless for remote/containerised deployments),
    send the script content over WebSocket and let the browser handle the download.
    """
    script_content = f"Title: {sim.state.scene.active_scene}\n\n"
    for line in sim.state.chat_history:
        if "'s Thought]:" in line:
            continue
        script_content += f"{line}\n\n"

    await websocket.send_json({
        "type": "download",
        "filename": f"{sim.state.scene.active_scene.replace(' ', '_')}_script.txt",
        "content": script_content,
    })
    await manager.broadcast({
        "type": "action",
        "content": "[SYSTEM]: Script ready — downloading in browser.",
    })
