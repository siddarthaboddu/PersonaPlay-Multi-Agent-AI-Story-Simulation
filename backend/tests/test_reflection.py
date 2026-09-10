"""Unit tests for the Reflection Agent and Hybrid Memory Retrieval."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document

from app.agents.reflection import generate_reflections
from app.models.payloads import InsightUpdateMessage
from app.models.state import AgentState, EmotionVector
from app.services.memory import _retrieve


def test_insight_update_payload():
    """InsightUpdateMessage must properly validate and serialize fields."""
    msg = InsightUpdateMessage(
        agent_id="Alice",
        insight="Bob seems to be hiding something about the ledger.",
        turn=4,
    )
    assert msg.type == "insight_update"
    assert msg.agent_id == "Alice"
    assert msg.turn == 4
    assert "ledger" in msg.insight

    # Ensure JSON serializable
    data = msg.model_dump()
    assert data["type"] == "insight_update"
    assert data["agent_id"] == "Alice"


def test_retrieve_memories_hybrid_partitioning():
    """_retrieve must partition results into synthesized insights and episodic observations."""
    mock_vs = MagicMock()
    mock_vs.similarity_search.return_value = [
        Document(page_content="Saw Bob near the vault.", metadata={"type": "observation", "agent_id": "Alice"}),
        Document(page_content="Bob cannot be trusted with security codes.", metadata={"type": "reflection", "agent_id": "Alice"}),
        Document(page_content="He glanced nervously at the exit.", metadata={"type": "observation", "agent_id": "Alice"}),
    ]

    with patch("app.services.memory._get_vectorstore", return_value=mock_vs):
        result = _retrieve("Alice", "vault", k_insights=1, k_observations=2)

    assert "YOUR SYNTHESIZED INSIGHTS & BELIEFS:" in result
    assert "- Bob cannot be trusted with security codes." in result
    assert "PAST MOMENTS RECALLED:" in result
    assert "- Saw Bob near the vault." in result
    assert "- He glanced nervously at the exit." in result


@pytest.mark.asyncio
async def test_generate_reflections_parsing():
    """generate_reflections must correctly prompt the LLM, clean prefixes, and call add_reflection."""
    agent = AgentState(
        id="Alice",
        traits="cautious, analytical",
        hidden_agenda="Expose the traitor",
        emotions=EmotionVector(tension=0.5, affection=0.5, energy=0.5, suspicion=0.7),
    )

    mock_llm_response = MagicMock()
    mock_llm_response.content = """
    Insight: Bob is deliberately avoiding eye contact whenever money is mentioned.
    * Insight: I need to check the timestamp on the safe log before dawn.
    """

    mock_model = AsyncMock()
    mock_model.ainvoke.return_value = mock_llm_response

    recent_observations = [
        "Alice: Did you finish the audit?",
        "Bob: Not yet, working on it now.",
    ]

    with patch("app.agents.reflection.get_model", return_value=mock_model), \
         patch("app.agents.reflection.add_reflection", new_callable=AsyncMock) as mock_add:
        insights = await generate_reflections(
            agent_id="Alice",
            agent=agent,
            recent_observations=recent_observations,
            current_beat="SUSPICION",
            turn_num=4,
        )

    assert len(insights) == 2
    assert insights[0] == "Bob is deliberately avoiding eye contact whenever money is mentioned."
    assert insights[1] == "I need to check the timestamp on the safe log before dawn."
    assert mock_add.call_count == 2
    mock_add.assert_any_call("Alice", insights[0], turn=4)
    mock_add.assert_any_call("Alice", insights[1], turn=4)


@pytest.mark.asyncio
async def test_generate_reflections_empty_observations():
    """generate_reflections returns empty list when no observations are provided."""
    agent = AgentState(
        id="Alice",
        emotions=EmotionVector(tension=0.5, affection=0.5, energy=0.5, suspicion=0.5),
    )
    insights = await generate_reflections("Alice", agent, [], "SUSPICION", 1)
    assert insights == []
