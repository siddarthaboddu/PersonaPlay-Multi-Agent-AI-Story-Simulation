"""
WebSocket endpoint — a thin dispatcher.

All the business logic lives in app/api/handlers/*.py.
This file only:
  1. Accepts/disconnects connections
  2. Parses + validates inbound payloads via the discriminated union
  3. Dispatches to the appropriate handler
"""
from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.api.connection import manager, sim
from app.api.handlers.config import (
    handle_check_model,
    handle_configure_scene,
    handle_force_emotion,
    handle_force_give_prop,
    handle_force_scene_tension,
    handle_system_reset,
)
from app.api.handlers.director import (
    handle_director_command,
    handle_export_script,
    handle_rewind_turns,
)
from app.api.handlers.scene import (
    handle_change_scene,
    handle_get_state,
    handle_start_scene,
    handle_stop_scene,
)
from app.api.handlers.turn import handle_next_turn
from app.models.payloads import InboundPayload

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        await websocket.send_json({"type": "state_update", "status": "connected"})

        async for raw in websocket.iter_text():
            try:
                payload = InboundPayload.model_validate(json.loads(raw)).root
            except (ValidationError, json.JSONDecodeError) as e:
                await websocket.send_json({
                    "type": "error",
                    "code": "invalid_payload",
                    "detail": str(e),
                })
                continue

            t = payload.type

            if t == "start_scene":
                await handle_start_scene(manager, sim, payload)
            elif t == "stop_scene":
                await handle_stop_scene(manager, sim, payload)
            elif t == "get_state":
                await handle_get_state(manager, sim, payload, websocket)
            elif t == "change_scene":
                await handle_change_scene(manager, sim, payload)
            elif t == "next_turn":
                await handle_next_turn(manager, sim, payload)
            elif t == "rewind_turns":
                await handle_rewind_turns(manager, sim, payload)
            elif t == "director_command":
                await handle_director_command(manager, sim, payload)
            elif t == "export_script":
                await handle_export_script(manager, sim, payload, websocket)
            elif t == "configure_scene":
                await handle_configure_scene(manager, sim, payload)
            elif t == "check_model":
                await handle_check_model(manager, sim, payload, websocket)
            elif t == "force_give_prop":
                await handle_force_give_prop(manager, sim, payload)
            elif t == "force_emotion":
                await handle_force_emotion(manager, sim, payload)
            elif t == "force_scene_tension":
                await handle_force_scene_tension(manager, sim, payload)
            elif t == "system_reset":
                await handle_system_reset(manager, sim)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS] Unexpected error: {e}")
    finally:
        manager.disconnect(websocket)
