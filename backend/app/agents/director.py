"""
Director node — selects who speaks next based on narrative context.

For 2-agent scenes: simple round-robin.
For 3+ agent scenes: LLM-guided selection to pick the most dramatically
appropriate next speaker based on recent dialogue.
"""
from langchain_core.messages import HumanMessage

from app.agents.llm import get_model
from app.models.state import OrchestratorState


async def director_node(state: OrchestratorState) -> OrchestratorState:
    """Analyse narrative tension and assign the next speaker."""
    print(f"[Director] Analyzing state… Turn {state.scene.turn_count}")
    state = state.model_copy(deep=True)
    state.scene.turn_count += 1

    agent_ids = list(state.agents.keys())
    if not agent_ids:
        return state

    # LLM-guided selection only for 3+ agents (round-robin is fine for 2)
    if len(agent_ids) > 2 and state.chat_history:
        try:
            director_agent = state.agents[agent_ids[0]]
            model = get_model(director_agent.llm_config, creative=False)
            context = "\n".join(state.chat_history[-5:])
            prompt = (
                f"You are the Director. The actors are: {', '.join(agent_ids)}.\n"
                f"Recent conversation:\n{context}\n"
                f"Who should speak next? Respond with ONLY the exact name of the character from the list."
            )
            res = await model.ainvoke([HumanMessage(content=prompt)])
            suggested = res.content.strip()
            if suggested in agent_ids and suggested != state.next_speaker:
                state.next_speaker = suggested
                print(f"[Director] Intelligently selected: {suggested}")
                return state
        except Exception as e:
            print(f"[Director] LLM error (falling back to round-robin): {e}")

    # Round-robin fallback
    if not state.next_speaker or state.next_speaker not in agent_ids:
        state.next_speaker = agent_ids[0]
    else:
        idx = agent_ids.index(state.next_speaker)
        state.next_speaker = agent_ids[(idx + 1) % len(agent_ids)]

    return state
