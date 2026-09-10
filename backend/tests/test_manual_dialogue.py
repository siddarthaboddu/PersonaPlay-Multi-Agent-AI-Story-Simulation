"""Unit tests for Manual Character Dialogue."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.api.handlers.director import handle_manual_dialogue
from app.models.payloads import InboundPayload, ManualDialoguePayload
from app.models.state import AgentState, EmotionVector, SceneState, WorldState


def test_manual_dialogue_payload_validation():
    """ManualDialoguePayload must validate properly via InboundPayload union."""
    raw = {
        "type": "manual_dialogue",
        "agent_id": "Maya",
        "content": "I don't think we are alone in this room.",
        "trigger_response": True,
    }
    payload = InboundPayload.model_validate(raw).root
    assert isinstance(payload, ManualDialoguePayload)
    assert payload.agent_id == "Maya"
    assert payload.content == "I don't think we are alone in this room."
    assert payload.trigger_response is True


def test_manual_dialogue_validation_missing_agent():
    """Missing agent_id must fail validation."""
    with pytest.raises(ValidationError):
        InboundPayload.model_validate({
            "type": "manual_dialogue",
            "content": "Hello there",
        })


@pytest.mark.asyncio
async def test_handle_manual_dialogue_updates_history_and_next_speaker():
    """handle_manual_dialogue records line, increments turn, and switches next_speaker."""
    mock_manager = AsyncMock()
    mock_sim = MagicMock()
    mock_sim.lock = AsyncMock()

    maya = AgentState(
        id="Maya",
        emotions=EmotionVector(tension=0.5, affection=0.5, energy=0.5, suspicion=0.5),
    )
    leo = AgentState(
        id="Leo",
        emotions=EmotionVector(tension=0.5, affection=0.5, energy=0.5, suspicion=0.5),
    )
    mock_sim.state.agents = {"Maya": maya, "Leo": leo}
    mock_sim.state.chat_history = []
    mock_sim.state.scene = SceneState(
        active_scene="Living Room",
        world_state=WorldState(location="Living Room", lighting="Warm", props=[]),
        narrative_tension=0.5,
        turn_count=5,
    )
    mock_sim.state.next_speaker = "Maya"

    payload = ManualDialoguePayload(
        type="manual_dialogue",
        agent_id="Maya",
        content="I have a confession to make.",
        trigger_response=False,
    )

    with patch("app.services.memory.add_memory", new_callable=AsyncMock) as mock_memory:
        await handle_manual_dialogue(mock_manager, mock_sim, payload)

    assert mock_sim.state.chat_history[-1] == "Maya: I have a confession to make."
    assert mock_sim.state.scene.turn_count == 6
    assert mock_sim.state.next_speaker == "Leo"
    assert maya.last_emote == "💬"

    # Verify memory was recorded
    mock_memory.assert_awaited_once_with(
        "Maya", "Maya: I have a confession to make.", memory_type="observation", turn=6
    )

    # Verify broadcast of dialogue event
    broadcast_types = [c.args[0]["type"] for c in mock_manager.broadcast.call_args_list]
    assert "dialogue" in broadcast_types
    assert "vitals_update" in broadcast_types
    assert "agents_update" in broadcast_types


@pytest.mark.asyncio
async def test_handle_manual_dialogue_triggers_response():
    """When trigger_response=True, handle_next_turn is invoked."""
    mock_manager = AsyncMock()
    mock_sim = MagicMock()
    mock_sim.lock = AsyncMock()

    maya = AgentState(
        id="Maya",
        emotions=EmotionVector(tension=0.5, affection=0.5, energy=0.5, suspicion=0.5),
    )
    leo = AgentState(
        id="Leo",
        emotions=EmotionVector(tension=0.5, affection=0.5, energy=0.5, suspicion=0.5),
    )
    mock_sim.state.agents = {"Maya": maya, "Leo": leo}
    mock_sim.state.chat_history = []
    mock_sim.state.scene = SceneState(
        active_scene="Living Room",
        world_state=WorldState(location="Living Room", lighting="Warm", props=[]),
        narrative_tension=0.5,
        turn_count=0,
    )

    payload = ManualDialoguePayload(
        type="manual_dialogue",
        agent_id="Maya",
        content="Testing AI reply trigger",
        trigger_response=True,
    )

    with patch("app.services.memory.add_memory", new_callable=AsyncMock), \
         patch("app.api.handlers.turn.handle_next_turn", new_callable=AsyncMock) as mock_next_turn:
        await handle_manual_dialogue(mock_manager, mock_sim, payload)
        mock_next_turn.assert_awaited_once()
