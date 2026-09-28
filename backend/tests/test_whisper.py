"""Unit tests for Director Secret Whispering (In-Ear Coaching)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.agents.actor import actor_node
from app.api.handlers.director import handle_director_whisper
from app.models.payloads import DirectorWhisperPayload, InboundPayload, WhisperUpdateMessage
from app.models.state import AgentState, EmotionVector, OrchestratorState, SceneState, WorldState


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


def _state_with_whisper():
    """Two-agent state where Echo-7 is holding an in-ear directive."""
    return OrchestratorState(
        scene=SceneState(
            active_scene="Rooftop",
            world_state=WorldState(location="Rooftop", lighting="Neon", props=[]),
            narrative_tension=0.5,
            turn_count=1,
        ),
        agents={
            "Echo-7": AgentState(
                id="Echo-7",
                traits="A disciplined operative.",
                emotions=EmotionVector(tension=0.5, affection=0.5, energy=0.5, suspicion=0.5),
                pending_whisper="Surrender your weapon immediately.",
            ),
            "Vex": AgentState(
                id="Vex",
                traits="A suspicious rival.",
                emotions=EmotionVector(tension=0.5, affection=0.5, energy=0.5, suspicion=0.5),
            ),
        },
        chat_history=["Vex: We are out of time. Give it up."],
        next_speaker="Echo-7",
    )


@pytest.mark.asyncio
async def test_actor_prompt_includes_whisper():
    """actor_node must inject the in-ear directive into the prompt and consume it after one turn."""
    state = _state_with_whisper()
    captured_prompt = None

    async def fake_ainvoke(messages):
        nonlocal captured_prompt
        captured_prompt = messages[0].content
        res = MagicMock()
        res.content = '{"thought":"He told me to surrender.","dialogue":"Fine. Here."}'
        return res

    mock_model = AsyncMock()
    mock_model.ainvoke.side_effect = fake_ainvoke

    with patch("app.agents.actor.get_model", return_value=mock_model), \
         patch("app.agents.actor.compress_history", new=AsyncMock(return_value="story")), \
         patch("app.agents.actor.retrieve_memories", new=AsyncMock(return_value="")), \
         patch("app.agents.actor.add_memory", new=AsyncMock()):
        out = await actor_node(state)

    assert captured_prompt is not None
    assert "DIRECTOR WHISPER" in captured_prompt
    assert "Surrender your weapon immediately." in captured_prompt

    # The whisper is one-shot: consumed by the speaker, and archived to known_secrets
    # so the character keeps the knowledge even after the directive is gone.
    assert out.agents["Echo-7"].pending_whisper is None
    assert any("Surrender your weapon" in s for s in out.agents["Echo-7"].known_secrets)
