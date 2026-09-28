"""
Tests for the gossip-diffusion signal and the episodic-memory status probe.

Two separate concerns, grouped because both were silent-failure bugs:

1. Gossip. `is_gossip` used to be inferred by searching the appended history
   lines for the literal text "[GOSSIP LEAK]". Two defects came out of that:
   a character who merely *said* the words triggered the badge, and the actor
   raised the flag before its dedup check, so re-confiding a secret the target
   already knew showed "Secret Confided" while transferring nothing. The flag
   is now data (`OrchestratorState.gossip_target`) set only on a real transfer.

2. Memory. The vector store fails soft. When it cannot initialise, every write
   is dropped and every recall returns "" — while the service still reports
   "ok". These tests pin the status probe that makes the degradation visible.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.actor import actor_node
from app.models.state import (
    AgentState,
    EmotionVector,
    OrchestratorState,
    SceneState,
    WorldState,
)


def _state(maya_secrets=None, leo_secrets=None):
    return OrchestratorState(
        scene=SceneState(
            active_scene="Living Room",
            world_state=WorldState(location="Living Room", lighting="Warm", props=[]),
            narrative_tension=0.5,
            turn_count=1,
        ),
        agents={
            "Maya": AgentState(
                id="Maya",
                traits="witty",
                hidden_agenda="keep the surprise",
                emotions=EmotionVector(tension=0.5, affection=0.5, energy=0.5, suspicion=0.5),
                known_secrets=list(maya_secrets or []),
            ),
            "Leo": AgentState(
                id="Leo",
                traits="easygoing",
                emotions=EmotionVector(tension=0.5, affection=0.5, energy=0.5, suspicion=0.5),
                known_secrets=list(leo_secrets or []),
            ),
        },
        chat_history=["Leo: What time is dinner?"],
        next_speaker="Maya",
    )


async def _run(state, payload: dict):
    fake = MagicMock()
    fake.ainvoke = AsyncMock(return_value=MagicMock(content=json.dumps(payload)))
    with patch("app.agents.actor.get_model", return_value=fake), \
         patch("app.agents.actor.compress_history", new=AsyncMock(return_value="story")), \
         patch("app.agents.actor.retrieve_memories", new=AsyncMock(return_value="")), \
         patch("app.agents.actor.add_memory", new=AsyncMock()):
        return await actor_node(state)


# ── Gossip ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_real_secret_transfer_sets_gossip_target():
    """A genuine leak sets the flag and moves the knowledge."""
    state = _state(maya_secrets=["the passes are in my laptop sleeve"])
    out = await _run(state, {
        "thought": "I will tell him.",
        "dialogue": "Fine, the passes are in my laptop sleeve.",
        "addressed_to": "Leo",
        "secret_shared": True,
    })
    assert out.gossip_target == "Maya -> Leo"
    assert any("passes" in s for s in out.agents["Leo"].known_secrets)
    assert any("[GOSSIP LEAK]" in line for line in out.chat_history)


@pytest.mark.asyncio
async def test_reconfiding_a_known_secret_is_not_a_leak():
    """The dedup bug: nothing new transferred, so nothing should be reported."""
    already = "Maya confided: the passes are in my laptop sleeve"
    state = _state(
        maya_secrets=["the passes are in my laptop sleeve"],
        leo_secrets=[already],
    )
    out = await _run(state, {
        "thought": "telling him again",
        "dialogue": "Again: the passes are in my laptop sleeve.",
        "addressed_to": "Leo",
        "secret_shared": True,
    })
    assert out.gossip_target is None, (
        "a no-op re-share must not raise the gossip flag"
    )
    assert not any("[GOSSIP LEAK]" in line for line in out.chat_history)
    # Leo's secret list is unchanged (still exactly the one he had).
    assert out.agents["Leo"].known_secrets == [already]


@pytest.mark.asyncio
async def test_saying_the_words_gossip_leak_is_not_a_leak():
    """Text-matching bug: a character may legitimately say the marker aloud."""
    state = _state()
    out = await _run(state, {
        "thought": "I am only joking.",
        "dialogue": "You keep shouting [GOSSIP LEAK] at me, relax.",
        "addressed_to": "Leo",
        "secret_shared": False,
    })
    assert out.gossip_target is None
    assert out.gossip_target is None, (
        "dialogue containing the marker text must not raise the flag"
    )


@pytest.mark.asyncio
async def test_gossip_target_does_not_leak_into_the_next_turn():
    """One-shot: a leak this turn must not be reported again next turn."""
    state = _state(maya_secrets=["a secret"])
    out = await _run(state, {
        "thought": "tell him",
        "dialogue": "Listen.",
        "addressed_to": "Leo",
        "secret_shared": True,
    })
    assert out.gossip_target == "Maya -> Leo"

    # Next turn: no leak at all, starting from the state that had one set.
    out2 = await _run(out, {
        "thought": "normal reply",
        "dialogue": "Anyway, seven o'clock.",
        "addressed_to": "Leo",
        "secret_shared": False,
    })
    assert out2.gossip_target is None


@pytest.mark.asyncio
async def test_confiding_to_yourself_is_not_a_leak():
    state = _state(maya_secrets=["a secret"])
    out = await _run(state, {
        "thought": "muttering",
        "dialogue": "...the passes are in my sleeve.",
        "addressed_to": "Maya",
        "secret_shared": True,
    })
    assert out.gossip_target is None


# ── Memory status ─────────────────────────────────────────────────────────────

def test_memory_status_reports_unavailable_backend():
    """A dead embedding backend must be visible, not silently swallowed."""
    from app.services import memory

    original_store, original_reason = memory._vectorstore, memory._unavailable_reason
    try:
        memory._vectorstore = None
        memory._unavailable_reason = "Could not import sentence_transformers"
        status = memory.memory_status()
        assert status["available"] is False
        assert "sentence_transformers" in status["reason"]
    finally:
        memory._vectorstore = original_store
        memory._unavailable_reason = original_reason


def test_memory_status_reports_available_store():
    from app.services import memory

    original_store, original_reason = memory._vectorstore, memory._unavailable_reason
    try:
        memory._vectorstore = MagicMock()
        memory._unavailable_reason = None
        assert memory.memory_status() == {"available": True, "reason": None}
    finally:
        memory._vectorstore = original_store
        memory._unavailable_reason = original_reason


def test_health_endpoint_surfaces_memory_state():
    """The health probe is the only way a user learns memory is off."""
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert "memory" in body
    assert "available" in body["memory"]


def test_failed_init_is_not_retried_on_every_call():
    """Regression: the failing import used to re-run on every memory call."""
    from app.services import memory

    original_store, original_reason = memory._vectorstore, memory._unavailable_reason
    try:
        memory._vectorstore = None
        memory._unavailable_reason = "boom"
        with patch.dict("sys.modules", {"langchain_huggingface": None}):
            # Should short-circuit on the cached reason, never import.
            assert memory._get_vectorstore() is None
            assert memory._get_vectorstore() is None
    finally:
        memory._vectorstore = original_store
        memory._unavailable_reason = original_reason
