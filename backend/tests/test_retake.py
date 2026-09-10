"""Unit tests for Director Retake / Re-roll Turn functionality."""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from pydantic import ValidationError

from app.api.handlers.turn import handle_retake_turn
from app.models.payloads import InboundPayload, RetakeTurnPayload
from app.models.state import AgentState, EmotionVector, OrchestratorState, SceneState, WorldState


def test_retake_turn_payload_validation():
    """RetakeTurnPayload must validate required type."""
    raw = {"type": "retake_turn"}
    payload = InboundPayload.model_validate(raw).root
    assert isinstance(payload, RetakeTurnPayload)
    assert payload.type == "retake_turn"


@pytest.mark.asyncio
async def test_handle_retake_turn_restores_and_reinvokes():
    """handle_retake_turn must restore 1 snapshot and dispatch a fresh turn."""
    mock_manager = AsyncMock()
    mock_sim = MagicMock()
    mock_sim.lock = AsyncMock()
    mock_sim.restore = MagicMock(return_value=True)

    agent = AgentState(
        id="Maya",
        emotions=EmotionVector(tension=0.5, affection=0.5, energy=0.5, suspicion=0.5),
    )
    mock_sim.state = OrchestratorState(
        scene=SceneState(
            active_scene="Sunday Coffee",
            world_state=WorldState(location="Kitchen", lighting="Morning", props=[]),
            narrative_tension=0.4,
            turn_count=2,
        ),
        agents={"Maya": agent},
        chat_history=["Maya: Good morning!", "Leo: Morning, Maya."],
        next_speaker="Leo",
    )

    payload = RetakeTurnPayload(type="retake_turn")

    with patch("app.api.handlers.turn.handle_next_turn", new_callable=AsyncMock) as mock_next_turn:
        await handle_retake_turn(mock_manager, mock_sim, payload)

        mock_sim.cancel_task.assert_called_once()
        mock_sim.restore.assert_called_once_with(1)
        mock_next_turn.assert_called_once()
