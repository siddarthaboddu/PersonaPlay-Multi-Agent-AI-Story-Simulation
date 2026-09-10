from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.agents.actor import _format_relationships
from app.api.handlers.config import handle_force_relationship
from app.models.payloads import ForceRelationshipPayload, InboundPayload
from app.models.state import AgentState, EmotionVector, RelationshipVector


def test_relationship_vector_defaults():
    """RelationshipVector defaults to balanced initial baseline."""
    rel = RelationshipVector()
    assert rel.trust == 0.5
    assert rel.affinity == 0.5
    assert rel.fear == 0.0
    assert rel.dominance == 0.5


def test_agent_state_relationships_serialization():
    """AgentState must serialize and deserialize relationships dictionary."""
    agent = AgentState(
        id="Cipher",
        emotions=EmotionVector(tension=0.5, affection=0.5, energy=0.5, suspicion=0.5),
        relationships={
            "Echo-7": RelationshipVector(trust=0.2, affinity=0.3, fear=0.8, dominance=0.4),
        },
    )
    dump = agent.model_dump()
    assert "relationships" in dump
    assert dump["relationships"]["Echo-7"]["trust"] == 0.2
    assert dump["relationships"]["Echo-7"]["fear"] == 0.8

    reloaded = AgentState.model_validate(dump)
    assert reloaded.relationships["Echo-7"].trust == 0.2


def test_force_relationship_payload_validation():
    """ForceRelationshipPayload must validate metric and type."""
    payload = InboundPayload.model_validate({
        "type": "force_relationship",
        "source_agent": "Cipher",
        "target_agent": "Echo-7",
        "metric": "trust",
        "value": 0.95,
    }).root
    assert isinstance(payload, ForceRelationshipPayload)
    assert payload.source_agent == "Cipher"
    assert payload.target_agent == "Echo-7"
    assert payload.metric == "trust"
    assert payload.value == 0.95


def test_force_relationship_invalid_metric_fails():
    """Invalid metric should raise validation error."""
    with pytest.raises(ValidationError):
        InboundPayload.model_validate({
            "type": "force_relationship",
            "source_agent": "Cipher",
            "target_agent": "Echo-7",
            "metric": "invalid_metric",
            "value": 0.5,
        })


def test_format_relationships_subtext():
    """_format_relationships should generate readable subtext instructions."""
    agent = AgentState(
        id="Cipher",
        emotions=EmotionVector(tension=0.5, affection=0.5, energy=0.5, suspicion=0.5),
        relationships={
            "Echo-7": RelationshipVector(trust=0.2, affinity=0.3, fear=0.8, dominance=0.3),
        },
    )
    formatted = _format_relationships("Cipher", agent)
    assert "INTERPERSONAL RELATIONSHIPS & SUBTEXT:" in formatted
    assert "Toward Echo-7:" in formatted
    assert "Trust 20%" in formatted
    assert "Fear 80%" in formatted


@pytest.mark.asyncio
async def test_handle_force_relationship_clamping_and_creation():
    """handle_force_relationship must clamp value between 0.0 and 1.0 and create target if missing."""
    mock_manager = AsyncMock()
    mock_sim = MagicMock()
    mock_sim.lock = AsyncMock()
    
    agent = AgentState(
        id="Alice",
        emotions=EmotionVector(tension=0.5, affection=0.5, energy=0.5, suspicion=0.5),
        relationships={},
    )
    mock_sim.state.agents = {"Alice": agent}

    payload = ForceRelationshipPayload(
        type="force_relationship",
        source_agent="Alice",
        target_agent="Bob",
        metric="trust",
        value=1.5,  # Needs clamping to 1.0
    )

    await handle_force_relationship(mock_manager, mock_sim, payload)

    assert "Bob" in agent.relationships
    assert agent.relationships["Bob"].trust == 1.0
    mock_manager.broadcast.assert_called_once()
