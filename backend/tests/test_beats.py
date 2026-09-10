"""Tests for narrative beat coverage and consistency."""
import pytest
from app.agents.beats import NARRATIVE_BEATS, get_beat, get_beat_label, beats_as_json


def test_beat_exists_for_every_turn():
    """Every turn from 0 to 200 must map to exactly one beat."""
    for turn in range(201):
        beat = get_beat(turn)
        assert beat, f"No beat found for turn {turn}"
        assert len(beat) > 10, f"Beat description suspiciously short at turn {turn}"


def test_high_turn_returns_epilogue():
    """Turns beyond 200 must fall into the EPILOGUE_LOOP beat."""
    beat = get_beat(500)
    assert "EPILOGUE" in beat


def test_beats_are_sorted_and_contiguous():
    """Beat ranges must be sorted and have no gaps or overlaps."""
    sorted_beats = sorted(NARRATIVE_BEATS, key=lambda b: b[0])
    for i in range(len(sorted_beats) - 1):
        current_end = sorted_beats[i][1]
        next_start = sorted_beats[i + 1][0]
        assert current_end + 1 == next_start, (
            f"Gap or overlap between beat ending at {current_end} "
            f"and next starting at {next_start}"
        )


def test_get_beat_label_returns_uppercase():
    label = get_beat_label(0)
    assert label == label.upper()


def test_beats_as_json_structure():
    data = beats_as_json()
    assert isinstance(data, list)
    assert len(data) == len(NARRATIVE_BEATS)
    for item in data:
        assert "start" in item
        assert "end" in item
        assert "label" in item
        assert "description" in item


@pytest.mark.asyncio
async def test_handle_toggle_phases():
    from unittest.mock import AsyncMock, MagicMock
    from app.api.handlers.scene import handle_toggle_phases
    from app.models.payloads import TogglePhasesPayload, InboundPayload
    from app.models.state import OrchestratorState, SceneState, WorldState

    raw = {"type": "toggle_phases", "enabled": False}
    payload = InboundPayload.model_validate(raw).root
    assert isinstance(payload, TogglePhasesPayload)
    assert payload.enabled is False

    mock_manager = AsyncMock()
    mock_sim = MagicMock()
    mock_sim.lock = AsyncMock()
    mock_sim.state = OrchestratorState(
        scene=SceneState(
            active_scene="Test Scene",
            world_state=WorldState(location="Living Room", lighting="Soft", props=[]),
            narrative_tension=0.3,
            turn_count=5,
            phases_enabled=True,
        ),
        agents={},
        chat_history=[],
        next_speaker="",
    )

    await handle_toggle_phases(mock_manager, mock_sim, payload)
    assert mock_sim.state.scene.phases_enabled is False
    assert mock_manager.broadcast.call_count == 2
