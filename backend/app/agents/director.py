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

    # Find who actually spoke last in chat_history
    last_speaker = None
    for line in reversed(state.chat_history):
        if not line or line.startswith("["):
            continue
        if ":" in line:
            candidate = line.split(":", 1)[0].strip()
            if candidate in agent_ids:
                last_speaker = candidate
                break

    # If no character dialogue exists yet, use designated opening speaker
    if not last_speaker:
        if not state.next_speaker or state.next_speaker not in agent_ids:
            state.next_speaker = agent_ids[0]
        return state

    other_candidates = [aid for aid in agent_ids if aid != last_speaker]

    # A directly named character should always get first right of reply. This
    # avoids asking the director model to guess when the speaker made it clear.
    if other_candidates:
        recent_line = next(
            (
                line.split(":", 1)[1].strip()
                for line in reversed(state.chat_history)
                if ":" in line and line.split(":", 1)[0].strip() == last_speaker
            ),
            "",
        ).lower()
        for candidate in other_candidates:
            if candidate.lower() in recent_line:
                state.next_speaker = candidate
                return state

    # LLM-guided selection only for 3+ agents (round-robin is fine for 2)
    if len(agent_ids) > 2 and other_candidates:
        try:
            director_agent = state.agents[agent_ids[0]]
            model = get_model(director_agent.llm_config, creative=False)
            context = "\n".join(state.chat_history[-5:])
            prompt = (
                f"You are the Director. The actors are: {', '.join(agent_ids)}.\n"
                f"Recent conversation:\n{context}\n"
                f"'{last_speaker}' just spoke. Who should speak next from {', '.join(other_candidates)}? "
                f"Respond with ONLY the exact name of the character from the candidate list."
            )
            res = await model.ainvoke([HumanMessage(content=prompt)])
            suggested = res.content.strip()
            if suggested in other_candidates:
                state.next_speaker = suggested
                print(f"[Director] Intelligently selected: {suggested}")
                return state
        except Exception as e:
            print(f"[Director] LLM error (falling back to round-robin): {e}")

    # Round-robin next speaker after last_speaker
    idx = agent_ids.index(last_speaker)
    state.next_speaker = agent_ids[(idx + 1) % len(agent_ids)]

    # Final guarantee: next speaker must NOT be the same as last speaker if multiple agents exist
    if state.next_speaker == last_speaker and other_candidates:
        state.next_speaker = other_candidates[0]

    return state
