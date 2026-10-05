"""Tests for state models and simulation state management."""
import pytest
from pydantic import ValidationError

from app.models.payloads import (
    ForceEmotionPayload,
    InboundPayload,
    StartScenePayload,
)
from app.models.state import (
    AgentState,
    EmotionVector,
    OrchestratorState,
    Prop,
    SceneState,
    WorldState,
)


def _make_state() -> OrchestratorState:
    return OrchestratorState(
        scene=SceneState(
            active_scene="Test Scene",
            world_state=WorldState(location="Void", lighting="None", props=[]),
            narrative_tension=0.5,
            turn_count=0,
        ),
        agents={
            "Alice": AgentState(
                id="Alice",
                emotions=EmotionVector(tension=0.5, affection=0.5, energy=0.5, suspicion=0.5),
            )
        },
        chat_history=[],
        next_speaker="Alice",
    )


# ── State model tests ─────────────────────────────────────────────────────────

def test_orchestrator_state_deep_copy():
    """model_copy(deep=True) must not share mutable references."""
    state = _make_state()
    copy = state.model_copy(deep=True)
    copy.agents["Alice"].emotions.tension = 0.9
    assert state.agents["Alice"].emotions.tension == 0.5


def test_emotion_vector_clamps_not_enforced_by_model():
    """EmotionVector accepts any float — clamp enforcement is in the actor logic."""
    ev = EmotionVector(tension=1.5, affection=-0.1, energy=0.0, suspicion=1.0)
    assert ev.tension == 1.5  # model itself doesn't clamp — actor does


# ── Payload validation tests ──────────────────────────────────────────────────



def test_valid_start_scene_payload():
    payload = InboundPayload.model_validate({"type": "start_scene"}).root
    assert isinstance(payload, StartScenePayload)


def test_valid_force_emotion_payload():
    payload = InboundPayload.model_validate({
        "type": "force_emotion",
        "agent_id": "Alice",
        "emotion": "tension",
        "value": 0.8,
    }).root
    assert isinstance(payload, ForceEmotionPayload)
    assert payload.value == 0.8


def test_unknown_type_raises_validation_error():
    with pytest.raises(ValidationError):
        InboundPayload.model_validate({"type": "does_not_exist"})


def test_missing_required_field_raises_validation_error():
    with pytest.raises(ValidationError):
        # force_emotion requires agent_id, emotion, value
        InboundPayload.model_validate({"type": "force_emotion", "agent_id": "Alice"})


def test_prop_defaults():
    p = Prop(id="test_prop")
    assert p.owner == "world"
    assert p.description == ""
    assert p.visibility == "visible"


def test_configure_scene_with_props():
    payload = InboundPayload.model_validate({
        "type": "configure_scene",
        "agents": [{"id": "Ren"}],
        "scene_name": "New Scene",
        "props": [{"id": "key_card", "owner": "Ren", "visibility": "visible"}],
    }).root
    assert payload.scene_name == "New Scene"
    assert len(payload.props) == 1
    assert payload.props[0]["id"] == "key_card"

