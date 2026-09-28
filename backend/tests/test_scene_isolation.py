"""
Tests for cross-scene state isolation and conversational speaker selection.

These cover a class of bug where a full scenario change does not fully reset
derived state:

  * episodic memories are keyed by agent id, so a new scenario that reuses a
    name inherits the previous character's entire recollection
  * the rolling LLM history summary is hashed against the previous scene's
    lines and goes on describing the old plot
  * manual dialogue always routed the reply to the first other agent, which
    skips the actual conversation partner once a cast exceeds two actors
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.handlers.config import handle_configure_scene
from app.api.handlers.director import handle_manual_dialogue
from app.models.payloads import ConfigureScenePayload, ManualDialoguePayload
from app.models.state import (
    AgentState,
    EmotionVector,
    OrchestratorState,
    SceneState,
    WorldState,
)


def _emotion():
    return EmotionVector(tension=0.5, affection=0.5, energy=0.5, suspicion=0.5)


def _sim_with(*names):
    from app.api.connection import SimulationState

    sim = SimulationState()
    sim.state = OrchestratorState(
        scene=SceneState(
            active_scene="Old Scene",
            world_state=WorldState(location="Somewhere", lighting="Dim", props=[]),
            narrative_tension=0.5,
            turn_count=3,
        ),
        agents={n: AgentState(id=n, traits="old", emotions=_emotion()) for n in names},
        chat_history=[],
        next_speaker=names[0],
    )
    sim.history = [sim.snapshot()]
    return sim


# ── configure_scene must wipe derived state ───────────────────────────────────

@pytest.mark.asyncio
async def test_configure_scene_clears_episodic_memories():
    """A new roster must not inherit the old roster's memories."""
    sim = _sim_with("Maya", "Liam")
    mgr = MagicMock()
    mgr.broadcast = AsyncMock()

    payload = ConfigureScenePayload(
        type="configure_scene",
        scene_name="Assassin's Night",
        agents=[
            {"id": "Maya", "traits": "cold assassin",
             "hidden_agenda": "assassinate the mayor", "emotions": {}},
            {"id": "Vex", "traits": "bounty hunter", "emotions": {}},
        ],
    )
    with patch("app.services.memory.clear_memories", new=AsyncMock()) as clear:
        await handle_configure_scene(mgr, sim, payload)

    clear.assert_awaited_once()


@pytest.mark.asyncio
async def test_configure_scene_resets_summary_cache():
    """The rolling LLM summary describes the previous plot; drop it."""
    import app.agents.llm as llm

    llm.reset_summary_cache()
    llm._summary_cache["summary"] = "Old scene: they argued about pizza."
    llm._summary_cache["old_lines_count"] = 4

    sim = _sim_with("Maya", "Liam")
    mgr = MagicMock()
    mgr.broadcast = AsyncMock()

    payload = ConfigureScenePayload(
        type="configure_scene",
        agents=[{"id": "Maya", "emotions": {}}, {"id": "Liam", "emotions": {}}],
    )

    with patch("app.services.memory.clear_memories", new=AsyncMock()):
        await handle_configure_scene(mgr, sim, payload)

    assert llm._summary_cache["summary"] == ""
    assert llm._summary_cache["old_lines_count"] == 0


@pytest.mark.asyncio
async def test_configure_scene_cancels_in_flight_turn():
    """Configuring while a turn is generating must not let it land afterwards."""
    sim = _sim_with("Maya", "Liam")
    mgr = MagicMock()
    mgr.broadcast = AsyncMock()

    # A real in-flight task reports done() == False. A bare MagicMock would
    # return a truthy mock from .done() and cancel_task would skip it.
    cancelled = MagicMock()
    cancelled.done.return_value = False
    sim.current_task = cancelled
    sim.pending_turn = True

    payload = ConfigureScenePayload(
        type="configure_scene",
        agents=[{"id": "Maya", "emotions": {}}, {"id": "Liam", "emotions": {}}],
    )

    with patch("app.services.memory.clear_memories", new=AsyncMock()):
        await handle_configure_scene(mgr, sim, payload)

    cancelled.cancel.assert_called_once()


# ── partial blueprints must not abort configuration ──────────────────────────

def test_emotion_vector_tolerates_partial_specification():
    """A blueprint may omit vitals; it must not raise and abort the whole scene."""
    assert EmotionVector().tension == 0.5
    assert EmotionVector(tension=0.9).tension == 0.9
    assert EmotionVector(tension=0.9).affection == 0.5


@pytest.mark.asyncio
async def test_configure_scene_applies_roster_with_empty_emotions():
    """Regression: an empty emotions dict used to raise mid-loop and leave a
    half-applied roster, with the failure only visible as a feed error."""
    sim = _sim_with("Old", "Cast")
    mgr = MagicMock()
    mgr.broadcast = AsyncMock()

    payload = ConfigureScenePayload(
        type="configure_scene",
        agents=[
            {"id": "Maya", "traits": "a", "emotions": {}},
            {"id": "Vex", "traits": "b", "emotions": {}},
        ],
    )

    with patch("app.services.memory.clear_memories", new=AsyncMock()):
        await handle_configure_scene(mgr, sim, payload)

    assert list(sim.state.agents) == ["Maya", "Vex"], "roster should be fully replaced"
    sent = [c.args[0] for c in mgr.broadcast.call_args_list]
    assert not any("[ERROR]" in str(m.get("content", "")) for m in sent)


# ── manual dialogue picks a conversational reply ─────────────────────────────

@pytest.mark.asyncio
async def test_manual_dialogue_replies_to_last_speaker_in_three_actor_scene():
    """The person who was just talking should get the reply, not roster[0]."""
    sim = _sim_with("Maya", "Liam", "Zoe")
    sim.state.chat_history = [
        "Liam: I already told you, no.",
        "Zoe: Honestly? Same.",
    ]
    mgr = MagicMock()
    mgr.broadcast = AsyncMock()

    payload = ManualDialoguePayload(
        type="manual_dialogue", agent_id="Liam", content="Fine, whatever."
    )

    with patch("app.api.handlers.director.asyncio.create_task", side_effect=lambda c: c.close()):
        await handle_manual_dialogue(mgr, sim, payload)

    # Zoe spoke most recently and is not the user; Maya (roster[0]) must not
    # be jumped to just because she happens to be first in the dict.
    assert sim.state.next_speaker == "Zoe"


@pytest.mark.asyncio
async def test_manual_dialogue_two_actor_scene_still_alternates():
    """The 2-actor case (the common one) must be unchanged."""
    sim = _sim_with("Maya", "Liam")
    mgr = MagicMock()
    mgr.broadcast = AsyncMock()

    payload = ManualDialoguePayload(
        type="manual_dialogue", agent_id="Maya", content="Are we ordering in?"
    )

    with patch("app.api.handlers.director.asyncio.create_task", side_effect=lambda c: c.close()):
        await handle_manual_dialogue(mgr, sim, payload)

    assert sim.state.next_speaker == "Liam"


@pytest.mark.asyncio
async def test_manual_dialogue_ignores_thought_lines_when_picking_reply():
    """Monologue markers are not speakers and must not win the search."""
    sim = _sim_with("Maya", "Liam", "Zoe")
    sim.state.chat_history = [
        "Liam: pass the salt",
        "[Zoe's Thought]: he is so dramatic",
    ]
    mgr = MagicMock()
    mgr.broadcast = AsyncMock()

    payload = ManualDialoguePayload(
        type="manual_dialogue", agent_id="Liam", content="Here."
    )

    with patch("app.api.handlers.director.asyncio.create_task", side_effect=lambda c: c.close()):
        await handle_manual_dialogue(mgr, sim, payload)

    # Zoe only appears in a Thought line, so no one has spoken; fall back to
    # roster order rather than trusting the marker.
    assert sim.state.next_speaker == "Maya"
