"""Unit tests for Director Secret Whispering (In-Ear Coaching)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.agents.actor import _generate_monologue
from app.api.handlers.director import handle_director_whisper
from app.models.payloads import DirectorWhisperPayload, InboundPayload, WhisperUpdateMessage
from app.models.state import AgentState, EmotionVector


def test_director_whisper_payload_validation():
    """DirectorWhisperPayload must validate required fields and type."""
    raw = {
        "type": "director_whisper",
        "agent_id": "Cipher",
        "whisper": "Play along, then double-cross.",
    }
    payload = InboundPayload.model_validate(raw).root
    assert isinstance(payload, DirectorWhisperPayload)
    assert payload.agent_id == "Cipher"
    assert payload.whisper == "Play along, then double-cross."


def test_director_whisper_missing_fields():
    """Missing whisper text or agent_id should raise ValidationError."""
    with pytest.raises(ValidationError):
        InboundPayload.model_validate({
            "type": "director_whisper",
            "agent_id": "Cipher",
        })


def test_whisper_update_message_schema():
    """WhisperUpdateMessage should serialize cleanly."""
    msg = WhisperUpdateMessage(agent_id="Echo-7", whisper="Do not engage yet.")
    dump = msg.model_dump()
    assert dump["type"] == "whisper_update"
    assert dump["agent_id"] == "Echo-7"
    assert dump["whisper"] == "Do not engage yet."


@pytest.mark.asyncio
async def test_handle_director_whisper_sets_pending_whisper():
    """handle_director_whisper must store pending_whisper on the target agent and broadcast."""
    mock_manager = AsyncMock()
    mock_sim = MagicMock()
    mock_sim.lock = AsyncMock()

    agent = AgentState(
        id="Cipher",
        emotions=EmotionVector(tension=0.5, affection=0.5, energy=0.5, suspicion=0.5),
        pending_whisper=None,
    )
    mock_sim.state.agents = {"Cipher": agent}

    payload = DirectorWhisperPayload(
        type="director_whisper",
        agent_id="Cipher",
        whisper="Demand to see the encryption key.",
    )

    await handle_director_whisper(mock_manager, mock_sim, payload)

    assert agent.pending_whisper == "Demand to see the encryption key."
    assert mock_manager.broadcast.call_count == 3  # whisper_update, action, agents_update


@pytest.mark.asyncio
async def test_monologue_prompt_includes_whisper():
    """_generate_monologue must inject in-ear directive into prompt when pending_whisper exists."""
    agent = AgentState(
        id="Echo-7",
        emotions=EmotionVector(tension=0.5, affection=0.5, energy=0.5, suspicion=0.5),
        pending_whisper="Surrender your weapon immediately.",
    )

    captured_prompt = None

    async def fake_ainvoke(messages):
        nonlocal captured_prompt
        captured_prompt = messages[0].content
        res = MagicMock()
        res.content = "I will obey the order."
        return res

    mock_model = AsyncMock()
    mock_model.ainvoke.side_effect = fake_ainvoke

    with patch("app.agents.actor.get_model", return_value=mock_model):
        result = await _generate_monologue(
            agent_id="Echo-7",
            agent=agent,
            context_summary="Standing on rooftop.",
            world_context="Scene: Neon Heist",
            beat="SUSPICION",
        )

    assert captured_prompt is not None
    assert "SECRET IN-EAR DIRECTIVE FROM THE DIRECTOR" in captured_prompt
    assert "Surrender your weapon immediately." in captured_prompt
    assert result["monologue"] == "I will obey the order."
