"""
Reflection Agent — synthesizes higher-level deductions and strategic insights from recent scene events.

Inspired by the Stanford Generative Agents reflection loop, this module takes raw episodic
observations and prompts the LLM to form abstract beliefs, suspicions, and tactical plans.
"""
from __future__ import annotations

import re

from langchain_core.messages import HumanMessage

from app.agents.llm import get_model
from app.models.state import AgentState
from app.services.memory import add_reflection


async def generate_reflections(
    agent_id: str,
    agent: AgentState,
    recent_observations: list[str],
    scene_context: str,
    turn_num: int,
) -> list[str]:
    """
    Synthesize 1-2 strategic insights from recent dialogue and store them in ChromaDB.

    Returns:
        List of generated insight strings.
    """
    if not recent_observations:
        return []

    # Filter out pure system notices if possible, keeping dialogue and director injections
    meaningful = [
        line for line in recent_observations
        if not line.startswith("[SYSTEM]") and not line.startswith("[SCENE START")
    ]
    if not meaningful:
        meaningful = recent_observations

    context_chunk = "\n".join(meaningful[-8:])
    traits_str = f"Traits: {agent.traits}\n" if agent.traits else ""
    agenda_str = f"Secret Agenda: {agent.hidden_agenda}\n" if agent.hidden_agenda else ""

    prompt = f"""You are {agent_id}.
{traits_str}{agenda_str}Current Scene Context: {scene_context}

Recent events and statements in the scene:
{context_chunk}

Reflect deeply on what just happened.
What are 1 or 2 high-level deductions, realizations, or tactical conclusions you draw regarding your secret agenda and the other characters?
Do not just repeat dialogue. Focus on:
- Who seems suspicious, deceitful, or surprisingly trustworthy?
- What new vulnerability or opportunity has appeared?
- What is your calculated next move?

Format each insight on a new line starting with 'Insight: '. Output 1 or 2 concise bullet points only."""

    insights: list[str] = []
    try:
        model = get_model(agent.llm_config, creative=False)
        res = await model.ainvoke([HumanMessage(content=prompt)])
        raw_text = res.content if hasattr(res, "content") else str(res)

        for line in raw_text.splitlines():
            line = line.strip()
            if not line:
                continue
            # Extract line if it starts with Insight: or markdown bullet
            cleaned = re.sub(r"^(\*|-|\d+\.)\s*", "", line).strip()
            if cleaned.lower().startswith("insight:"):
                cleaned = cleaned[8:].strip()
            if len(cleaned) > 10:
                insights.append(cleaned)

        # Cap at 2 insights
        insights = insights[:2]

        for ins in insights:
            await add_reflection(agent_id, ins, turn=turn_num)
            print(f"[Reflection] {agent_id} (Turn {turn_num}): {ins[:60]}…")

    except Exception as e:
        print(f"[Reflection] Error synthesizing insights for {agent_id}: {e}")

    return insights
