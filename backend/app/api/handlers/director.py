"""
Director-facing handlers: inject chaos commands and export script.
"""
import asyncio

from app.api.connection import ConnectionManager, SimulationState
from app.models.payloads import (
    DirectorCommandPayload,
    DirectorWhisperPayload,
    ExportScriptPayload,
    ManualDialoguePayload,
)


async def handle_director_command(
    manager: ConnectionManager,
    sim: SimulationState,
    payload: DirectorCommandPayload,
) -> None:
    async with sim.lock:
        command = payload.command

        # Chaos injection
        chaos_msg = f"[DIRECTOR INJECTS]: {command}"
        sim.state.chat_history.append(chaos_msg)

        await manager.broadcast({"type": "action", "content": chaos_msg})
        sim.state.scene.narrative_tension = min(sim.state.scene.narrative_tension + 0.2, 1.0)
        await manager.broadcast({
            "type": "vitals_update",
            "vitals": {
                "scene_name": sim.state.scene.active_scene,
                "tension": sim.state.scene.narrative_tension,
                "energy": 0.9,
                "turn_count": sim.state.scene.turn_count,
            },
        })
        sim.update_last_history()

    # ── Trigger Immediate AI Reaction ────────────────────────────────────────
    # We do this OUTSIDE the lock to allow handle_next_turn to acquire it.
    from app.api.handlers.turn import handle_next_turn
    from app.models.payloads import NextTurnPayload
    
    await handle_next_turn(manager, sim, NextTurnPayload(type="next_turn"))


async def handle_director_whisper(
    manager: ConnectionManager,
    sim: SimulationState,
    payload: DirectorWhisperPayload,
) -> None:
    async with sim.lock:
        if payload.agent_id in sim.state.agents:
            sim.state.agents[payload.agent_id].pending_whisper = payload.whisper.strip()
            sim.update_last_history()

    await manager.broadcast({
        "type": "whisper_update",
        "agent_id": payload.agent_id,
        "whisper": payload.whisper.strip(),
    })
    await manager.broadcast({
        "type": "action",
        "content": f"[SECRET WHISPER TO {payload.agent_id.upper()}]: \"{payload.whisper.strip()}\"",
    })
    await manager.broadcast({
        "type": "agents_update",
        "agents": [v.model_dump() for v in sim.state.agents.values()],
    })


async def handle_manual_dialogue(
    manager: ConnectionManager,
    sim: SimulationState,
    payload: ManualDialoguePayload,
) -> None:
    """Manually enter dialogue for a character, update state/memory, and prompt AI response."""
    agent_id = payload.agent_id
    raw_text = payload.content.strip()
    if not raw_text:
        return

    clean_dialogue = raw_text if raw_text.startswith(f"{agent_id}:") else f"{agent_id}: {raw_text}"

    async with sim.lock:
        sim.cancel_task()
        sim.state.chat_history.append(clean_dialogue)
        sim.state.scene.turn_count += 1
        # Preserve the exact user-authored line separately from normal history.
        # actor.py uses it to force the next AI turn to be a reply, not a pivot.
        sim.state.manual_reply_speaker = agent_id
        sim.state.manual_reply_content = raw_text
        if agent_id in sim.state.agents:
            sim.state.agents[agent_id].last_addressee = None
            sim.state.agents[agent_id].last_spoke_turn = sim.state.scene.turn_count

        # Choose who replies. Previously this was always `other_agents[0]`,
        # which is correct for a two-hander but ignores the conversation in a
        # 3+ cast: if the user spoke for the middle character, the person who
        # was actually just talking gets skipped. Prefer whoever spoke most
        # recently among the candidates, falling back to roster order.
        agent_ids = list(sim.state.agents.keys())
        other_agents = [aid for aid in agent_ids if aid != agent_id]
        if other_agents:
            last_spoken = None
            for line in reversed(sim.state.chat_history):
                if not line or line.startswith("["):
                    continue
                if ":" in line:
                    cand = line.split(":", 1)[0].strip()
                    if cand in other_agents:
                        last_spoken = cand
                        break
            sim.state.next_speaker = last_spoken or other_agents[0]

        print(f"\n[Manual Dialogue Entered]: '{clean_dialogue}' -> next AI speaker is '{sim.state.next_speaker}'", flush=True)

        # Update last emote on the speaking agent
        if agent_id in sim.state.agents:
            sim.state.agents[agent_id].last_emote = "💬"

        sim.push_history()

    # Memory persistence must not hold up the visible line or its reply.
    from app.services.memory import add_memory
    asyncio.create_task(
        add_memory(agent_id, clean_dialogue, memory_type="observation", turn=sim.state.scene.turn_count)
    )

    # Broadcast dialogue event
    await manager.broadcast({
        "type": "dialogue",
        "agent_id": agent_id,
        "content": clean_dialogue,
        "emote": "💬",
        "is_manual": True,
    })

    # Broadcast updated vitals
    await manager.broadcast({
        "type": "vitals_update",
        "vitals": {
            "scene_name": sim.state.scene.active_scene,
            "tension": sim.state.scene.narrative_tension,
            "energy": 0.8,
            "turn_count": sim.state.scene.turn_count,
        },
    })

    # Broadcast agent updates
    await manager.broadcast({
        "type": "agents_update",
        "agents": [v.model_dump() for v in sim.state.agents.values()],
    })

    # Trigger AI response turn if requested
    if payload.trigger_response:
        from app.api.handlers.turn import handle_next_turn
        from app.models.payloads import NextTurnPayload
        await handle_next_turn(manager, sim, NextTurnPayload(type="next_turn"))


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
