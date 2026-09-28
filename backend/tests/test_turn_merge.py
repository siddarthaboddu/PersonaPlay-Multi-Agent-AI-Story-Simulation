"""
Regression tests for the turn-merge contract.

The LangGraph turn runs on its own deep copy of OrchestratorState. After it
returns, `handle_next_turn` copies selected fields back into the live state.
Any field the actor node mutates but the merge forgets to copy is SILENTLY
DISCARDED.

This exact class of bug shipped once: the merge carried only `emotions` and
`relationships`, which quietly destroyed the emote system and reset the gossip
engine's `known_secrets` on every single turn. These tests lock the contract
down so that adding a new mutable field to AgentState forces a decision here.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.handlers.turn import handle_next_turn
from app.models.payloads import NextTurnPayload
from app.models.state import (
    AgentState,
    EmotionVector,
    OrchestratorState,
    SceneState,
    WorldState,
)


def _emotion():
    return EmotionVector(tension=0.5, affection=0.5, energy=0.5, suspicion=0.5)


def _state():
    return OrchestratorState(
        scene=SceneState(
            active_scene="Living Room",
            world_state=WorldState(location="Living Room", lighting="Warm", props=[]),
            narrative_tension=0.5,
            turn_count=1,
        ),
        agents={
            "Maya": AgentState(id="Maya", traits="witty", emotions=_emotion()),
            "Leo": AgentState(id="Leo", traits="easygoing", emotions=_emotion()),
        },
        chat_history=["Maya: I know about the tickets."],
        next_speaker="Leo",
    )


async def _run_turn(graph_result: OrchestratorState, live_state: OrchestratorState | None = None):
    """Drive handle_next_turn with a stubbed graph, return the mutated sim."""
    from app.api.connection import SimulationState

    sim = SimulationState()
    sim.state = live_state if live_state is not None else _state()
    sim.history = [sim.snapshot()]

    manager = MagicMock()
    manager.broadcast = AsyncMock()

    fake_graph = MagicMock()
    fake_graph.ainvoke = AsyncMock(return_value=graph_result)

    with patch("app.api.handlers.turn.graph", fake_graph), \
         patch("app.api.handlers.turn.asyncio.sleep", new=AsyncMock()):
        await handle_next_turn(manager, sim, NextTurnPayload(type="next_turn"))
        if sim.current_task:
            await sim.current_task

    return sim


@pytest.mark.asyncio
async def test_merge_preserves_emote_and_known_secrets():
    """The regression: emote + known_secrets must survive the turn merge."""
    result = _state()
    result.chat_history = [
        "Maya: I know about the tickets.",
        "[Leo's Thought]: He is hiding something.",
        "Leo: Fine. Here.",
    ]
    # Simulate what actor_node produced on its graph-local copy.
    result.agents["Leo"].last_emote = "\U0001F92B"
    result.agents["Leo"].known_secrets.append(
        "Maya confided: the concert passes are in her laptop sleeve"
    )
    result.agents["Leo"].emotions.tension = 0.72

    sim = await _run_turn(result)

    live = sim.state.agents["Leo"]
    assert live.last_emote == "\U0001F92B", (
        "emote was dropped by the merge — the emote system is dead again"
    )
    assert any("concert passes" in s for s in live.known_secrets), (
        "known_secrets was dropped by the merge — the gossip engine resets every turn"
    )
    assert live.emotions.tension == pytest.approx(0.72)


@pytest.mark.asyncio
async def test_merge_preserves_secrets_gained_by_a_third_party():
    """Secrets diffused INTO another agent by gossip must also survive."""
    result = _state()
    result.chat_history = [
        "Maya: I know about the tickets.",
        "[GOSSIP LEAK]: \U0001F92B Maya confided a secret to Leo!",
        "Leo: Fine. Here.",
    ]
    result.agents["Leo"].known_secrets.append("Maya confided: the spare key")

    sim = await _run_turn(result)
    assert any("spare key" in s for s in sim.state.agents["Leo"].known_secrets)


@pytest.mark.asyncio
async def test_merge_does_not_resurrect_a_consumed_whisper():
    """pending_whisper is one-shot: a consumed directive must not come back."""
    result = _state()
    result.chat_history = [
        "Maya: I know about the tickets.",
        "[Leo's Thought]: obeying",
        "Leo: Fine. Here.",
    ]
    result.agents["Leo"].pending_whisper = None  # consumed by the actor node

    # The live agent still holds a stale directive from before the turn.
    live = _state()
    live.agents["Leo"].pending_whisper = "stale directive"

    sim = await _run_turn(result, live_state=live)
    assert sim.state.agents["Leo"].pending_whisper is None


@pytest.mark.asyncio
async def test_merge_preserves_static_identity_fields():
    """traits / hidden_agenda / relationship_context round-trip unchanged."""
    result = _state()
    result.chat_history = ["Maya: I know about the tickets.", "Leo: Fine. Here."]
    result.agents["Leo"].traits = "calm, deflects with jokes"
    result.agents["Leo"].hidden_agenda = "protect the sister"
    result.agents["Leo"].relationship_context = {"Maya": "ex-girlfriend, still friends"}

    sim = await _run_turn(result)
    live = sim.state.agents["Leo"]
    assert live.traits == "calm, deflects with jokes"
    assert live.hidden_agenda == "protect the sister"
    assert live.relationship_context["Maya"] == "ex-girlfriend, still friends"
