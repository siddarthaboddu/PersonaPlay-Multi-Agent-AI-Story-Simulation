"""
Typed WebSocket message models for PersonaPlay Pro.

Inbound: messages FROM the frontend to the backend.
Outbound: messages FROM the backend to the frontend.

Using Pydantic discriminated unions so that any malformed inbound message
raises a ValidationError immediately rather than silently falling through
the old if/elif chain.
"""
from __future__ import annotations

from typing import Annotated, Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, RootModel


# ── Inbound (frontend → backend) ─────────────────────────────────────────────

class StartScenePayload(BaseModel):
    type: Literal["start_scene"]


class StopScenePayload(BaseModel):
    type: Literal["stop_scene"]


class NextTurnPayload(BaseModel):
    type: Literal["next_turn"]


class GetStatePayload(BaseModel):
    type: Literal["get_state"]


class ChangeScenePayload(BaseModel):
    type: Literal["change_scene"]
    location: Optional[str] = None
    scene_name: Optional[str] = None


class RewindPayload(BaseModel):
    type: Literal["rewind_turns"]
    turns: int = 1


class ForceGivePropPayload(BaseModel):
    type: Literal["force_give_prop"]
    prop_id: str
    owner: str


class ConfigureScenePayload(BaseModel):
    type: Literal["configure_scene"]
    agents: List[Dict[str, Any]]


class CheckModelPayload(BaseModel):
    type: Literal["check_model"]
    agent_id: str
    llm_config: Dict[str, Any]


class DirectorCommandPayload(BaseModel):
    type: Literal["director_command"]
    command: str


class ForceEmotionPayload(BaseModel):
    type: Literal["force_emotion"]
    agent_id: str
    emotion: str
    value: float


class ForceSceneTensionPayload(BaseModel):
    type: Literal["force_scene_tension"]
    value: float


class ExportScriptPayload(BaseModel):
    type: Literal["export_script"]


# Discriminated union — validated by 'type' field
class InboundPayload(RootModel):
    root: Annotated[
        Union[
            StartScenePayload,
            StopScenePayload,
            NextTurnPayload,
            GetStatePayload,
            ChangeScenePayload,
            RewindPayload,
            ForceGivePropPayload,
            ConfigureScenePayload,
            CheckModelPayload,
            DirectorCommandPayload,
            ForceEmotionPayload,
            ForceSceneTensionPayload,
            ExportScriptPayload,
        ],
        Field(discriminator="type"),
    ]


# ── Outbound (backend → frontend) ────────────────────────────────────────────

class ActionMessage(BaseModel):
    type: Literal["action"] = "action"
    content: str


class DialogueMessage(BaseModel):
    type: Literal["dialogue"] = "dialogue"
    agent_id: str
    content: str


class MonologueMessage(BaseModel):
    type: Literal["monologue"] = "monologue"
    agent_id: str
    content: str


class WorldUpdateMessage(BaseModel):
    type: Literal["world_update"] = "world_update"
    world: Dict[str, Any]


class AgentsUpdateMessage(BaseModel):
    type: Literal["agents_update"] = "agents_update"
    agents: List[Dict[str, Any]]


class VitalsUpdateMessage(BaseModel):
    type: Literal["vitals_update"] = "vitals_update"
    vitals: Dict[str, Any]


class ImageUpdateMessage(BaseModel):
    type: Literal["image_update"] = "image_update"
    url: str
    prompt: str


class HistoryResetMessage(BaseModel):
    type: Literal["history_reset"] = "history_reset"
    messages: List[Dict[str, Any]] = []
    monologues: List[Dict[str, Any]] = []


class CheckResultMessage(BaseModel):
    type: Literal["check_result"] = "check_result"
    agent_id: str
    status: Literal["ok", "error"]
    message: Optional[str] = None


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    code: str
    detail: str


class DownloadMessage(BaseModel):
    type: Literal["download"] = "download"
    filename: str
    content: str
