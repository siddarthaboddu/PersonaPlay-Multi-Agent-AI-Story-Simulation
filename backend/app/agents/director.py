"""Choose the next person who has a natural reason to speak."""
from __future__ import annotations

import re

from app.models.state import AgentState, OrchestratorState


def _last_utterance(history: list[str], agent_ids: set[str]) -> tuple[str | None, str]:
    for line in reversed(history):
        if not line or line.startswith("[") or ":" not in line:
            continue
        speaker, _, utterance = line.partition(":")
        speaker = speaker.strip()
        if speaker in agent_ids:
            return speaker, utterance.strip()
    return None, ""


def _candidate_score(agent: AgentState, turn_num: int, utterance: str) -> float:
    """Score turn entitlement from address, conversational attention, and airtime."""
    score = max(0, turn_num - agent.last_spoke_turn) * 0.12
    lowered = utterance.lower()

    # A direct name mention is a strong cue to reply. Word boundaries avoid
    # treating a name such as "Ann" as present in a word like "announced".
    if re.search(rf"(?<!\w){re.escape(agent.id.lower())}(?!\w)", lowered):
        score += 1.25

    attention = (agent.current_attention or "").lower()
    attention_words = {w for w in re.findall(r"[a-z0-9']+", attention) if len(w) > 3}
    utterance_words = {w for w in re.findall(r"[a-z0-9']+", lowered) if len(w) > 3}
    if attention_words and attention_words & utterance_words:
        score += 0.35

    # Arousal can make someone more likely to jump in; low energy reduces it.
    score += agent.emotions.tension * 0.2 + agent.emotions.energy * 0.15
    return score


async def director_node(state: OrchestratorState) -> OrchestratorState:
    """Route a reply to an addressed character, otherwise balance the floor."""
    state = state.model_copy(deep=True)
    state.scene.turn_count += 1
    agent_ids = list(state.agents)
    if not agent_ids:
        return state

    history_speaker, utterance = _last_utterance(state.chat_history, set(agent_ids))
    if history_speaker is None:
        if state.next_speaker not in state.agents:
            state.next_speaker = agent_ids[0]
        return state

    # A character can stay quiet. Track who was selected last independently of
    # who produced the latest line so silence does not route the floor back to
    # that same person repeatedly.
    last_speaker = max(
        agent_ids,
        key=lambda agent_id: state.agents[agent_id].last_spoke_turn,
    )
    if state.agents[last_speaker].last_spoke_turn < 0:
        last_speaker = history_speaker

    candidates = [agent_id for agent_id in agent_ids if agent_id != last_speaker]
    if not candidates:
        state.next_speaker = last_speaker
        return state

    # Honour the previous character's explicit addressee when there is one.
    addressed = state.agents[last_speaker].last_addressee
    if last_speaker == history_speaker and addressed in candidates:
        state.next_speaker = addressed
        return state

    # A one-on-one conversation has only one possible responder. With a group,
    # choose from relevance, attention and airtime rather than roster order.
    if len(candidates) == 1:
        state.next_speaker = candidates[0]
        return state

    state.next_speaker = max(
        candidates,
        key=lambda candidate: (
            _candidate_score(state.agents[candidate], state.scene.turn_count, utterance),
            -agent_ids.index(candidate),
        ),
    )
    return state
