"""
Typed WebSocket message models for PersonaPlay Pro.

Inbound: messages FROM the frontend to the backend.
Outbound: messages FROM the backend to the frontend.

Using Pydantic discriminated unions so that any malformed inbound message
raises a ValidationError immediately rather than silently falling through
the old if/elif chain.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, RootModel

# ── Inbound (frontend → backend) ─────────────────────────────────────────────

class StartScenePayload(BaseModel):
    type: Literal["start_scene"]


class StopScenePayload(BaseModel):
    type: Literal["stop_scene"]


class PauseScenePayload(BaseModel):
    type: Literal["pause_scene"]


class NextTurnPayload(BaseModel):
    type: Literal["next_turn"]


class GetStatePayload(BaseModel):
    type: Literal["get_state"]


class ChangeScenePayload(BaseModel):
    type: Literal["change_scene"]
    location: str | None = None
    scene_name: str | None = None


class RewindPayload(BaseModel):
    type: Literal["rewind_turns"]
    turns: int = 1


class ForceGivePropPayload(BaseModel):
    type: Literal["force_give_prop"]
    prop_id: str
    owner: str


class ConfigureScenePayload(BaseModel):
    type: Literal["configure_scene"]
    agents: list[dict[str, Any]]
    scene_name: str | None = None
    location: str | None = None
    lighting: str | None = None
    props: list[dict[str, Any]] | None = None
    phases_enabled: bool | None = None


class CheckModelPayload(BaseModel):
    type: Literal["check_model"]
    agent_id: str
    llm_config: dict[str, Any]


class DirectorCommandPayload(BaseModel):
    type: Literal["director_command"]
    command: str


class DirectorWhisperPayload(BaseModel):
    type: Literal["director_whisper"]
    agent_id: str
    whisper: str


class ForceEmotionPayload(BaseModel):
    type: Literal["force_emotion"]
    agent_id: str
    emotion: str
    value: float


class ForceRelationshipPayload(BaseModel):
    type: Literal["force_relationship"]
    source_agent: str
    target_agent: str
    metric: Literal["trust", "affinity", "fear", "dominance"]
    value: float


class ForceSceneTensionPayload(BaseModel):
    type: Literal["force_scene_tension"]
    value: float


class ExportScriptPayload(BaseModel):
    type: Literal["export_script"]


class SystemResetPayload(BaseModel):
    type: Literal["system_reset"]


class RetakeTurnPayload(BaseModel):
    type: Literal["retake_turn"]


class TogglePhasesPayload(BaseModel):
    type: Literal["toggle_phases"]
    enabled: bool


class ManualDialoguePayload(BaseModel):
    type: Literal["manual_dialogue"]
    agent_id: str
    content: str
    trigger_response: bool = True


# Discriminated union — validated by 'type' field.
# Kept vertical (rather than one long `A | B | ...` line) so that adding a new
# message type stays a one-line, reviewable diff.
InboundMessage = (
    StartScenePayload
    | StopScenePayload
    | PauseScenePayload
    | NextTurnPayload
    | RetakeTurnPayload
    | TogglePhasesPayload
    | ManualDialoguePayload
    | GetStatePayload
    | ChangeScenePayload
    | RewindPayload
    | ForceGivePropPayload
    | ConfigureScenePayload
    | CheckModelPayload
    | DirectorCommandPayload
    | DirectorWhisperPayload
    | ForceEmotionPayload
    | ForceRelationshipPayload
    | ForceSceneTensionPayload
    | ExportScriptPayload
    | SystemResetPayload
)


class InboundPayload(RootModel):
    root: Annotated[
        InboundMessage,
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
    world: dict[str, Any]


class AgentsUpdateMessage(BaseModel):
    type: Literal["agents_update"] = "agents_update"
    agents: list[dict[str, Any]]


class VitalsUpdateMessage(BaseModel):
    type: Literal["vitals_update"] = "vitals_update"
    vitals: dict[str, Any]


class ImageUpdateMessage(BaseModel):
    type: Literal["image_update"] = "image_update"
    url: str
    prompt: str


class HistoryResetMessage(BaseModel):
    type: Literal["history_reset"] = "history_reset"
    messages: list[dict[str, Any]] = []
    monologues: list[dict[str, Any]] = []


class CheckResultMessage(BaseModel):
    type: Literal["check_result"] = "check_result"
    agent_id: str
    status: Literal["ok", "error"]
    message: str | None = None


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    code: str
    detail: str


class DownloadMessage(BaseModel):
    type: Literal["download"] = "download"
    filename: str
    content: str


class InsightUpdateMessage(BaseModel):
    type: Literal["insight_update"] = "insight_update"
    agent_id: str
    insight: str
    turn: int


class WhisperUpdateMessage(BaseModel):
    type: Literal["whisper_update"] = "whisper_update"
    agent_id: str
    whisper: str | None = None

