"""
Actor node — generates internal monologue + public dialogue for the next speaker.

Responsibilities:
1. Compress chat history (anti-repetition)
2. Generate parallel internal monologues for all agents
3. Retrieve episodic memories for the speaker
4. Generate structured dialogue via JSON parser
5. Apply ECS prop/location changes
6. Update emotion vectors
7. Store new memory
"""
import asyncio
import random
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputParser

from app.agents.beats import get_beat
from app.agents.llm import get_model, compress_history
from app.config import settings
from app.models.state import OrchestratorState
from app.services.memory import add_memory, retrieve_memories


class ActorOutput(BaseModel):
    dialogue: str = Field(
        description=(
            "The words you say out loud. Use emojis to express feelings. "
            "MUST be completely different from anything said in recent history. "
            "Advance the story — say something NEW."
        )
    )
    take_prop: Optional[str] = Field(None, description="A prop ID you want to take")
    move_to: Optional[str] = Field(None, description="A new location to move to")


async def _generate_monologue(
    agent_id: str,
    agent,
    context_summary: str,
    world_context: str,
    beat: str,
) -> dict:
    """Generate one internal monologue for a single agent."""
    try:
        model = get_model(agent.llm_config, creative=True)
        traits = f"Traits: {agent.traits}\n" if agent.traits else ""
        agenda = f"SECRET MOTIVE: {agent.hidden_agenda}\n" if agent.hidden_agenda else ""
        
        prompt = (
            f"You are {agent_id}. {world_context}\n"
            f"{traits}{agenda}"
            f"Story context: {context_summary}\n"
            f"Dramatic beat: {beat}\n"
            f"What is ONE new specific thought you have RIGHT NOW that reflects your secret motive? "
            f"One short sentence only. Do not reveal the secret directly."
        )
        res = await model.ainvoke([HumanMessage(content=prompt)])
        return {"agent_id": agent_id, "monologue": res.content.strip()}
    except Exception as e:
        print(f"[Actor] Monologue error for {agent_id}: {e}")
        return {"agent_id": agent_id, "monologue": f"({agent_id} is thinking...)"}


async def actor_node(state: OrchestratorState) -> OrchestratorState:
    """Generate internal monologue + public dialogue for the next speaker."""
    speaker = state.next_speaker

    if speaker not in state.agents:
        print(f"[Actor] Speaker '{speaker}' not found in agents. Skipping.")
        return state

    agent = state.agents[speaker]
    turn_num = state.scene.turn_count

    # ── 1. Compress history (anti-repetition) ────────────────────────────────
    creative_model = get_model(agent.llm_config, creative=True)
    context = await compress_history(state.chat_history, creative_model)

    # ── 2. Beat-driven writing ────────────────────────────────────────────────
    beat = get_beat(turn_num)

    props_str = "; ".join(
        f"{p.id} ({p.description}) [Owned by: {p.owner}]" 
        for p in state.scene.world_state.props if p.visibility == "visible"
    )
    world_context = (
        f"Scene: {state.scene.active_scene}. "
        f"Location: {state.scene.world_state.location}. "
        f"Atmosphere: {state.scene.world_state.lighting}. "
        f"Items in Scene: {props_str if props_str else 'None'}"
    )
    traits_str = f"Your character traits: {agent.traits}\n" if agent.traits else ""
    agenda_str = (
        f"Your secret agenda (NEVER reveal this directly — pursue it through subtext and action): "
        f"{agent.hidden_agenda}"
    ) if agent.hidden_agenda else ""

    # ── 3. Parallel internal monologues (all agents think simultaneously) ─────
    print("[Actor] Generating parallel monologues…")
    mono_tasks = [
        _generate_monologue(aid, ag, context, world_context, beat)
        for aid, ag in state.agents.items()
    ]
    monologues = await asyncio.gather(*mono_tasks)
    speaker_mono = next(
        (m["monologue"] for m in monologues if m["agent_id"] == speaker),
        "...",
    )

    # ── 4. Episodic memory retrieval ──────────────────────────────────────────
    memories = await retrieve_memories(speaker, context[:200])
    mem_context = f"\nYour past experiences relevant to this moment:\n{memories}" if memories else ""

    # ── 5. Generate structured dialogue ──────────────────────────────────────
    parser = JsonOutputParser(pydantic_object=ActorOutput)
    format_instructions = parser.get_format_instructions()

    prompt = f"""You are {speaker}, an actor in a live theatrical simulation.
{traits_str}
{agenda_str}
{world_context}{mem_context}

STORY CONTEXT (what has happened so far):
{context}

YOUR INTERNAL THOUGHT RIGHT NOW: {speaker_mono}

DRAMATIC BEAT FOR THIS TURN: {beat}

1. Your dialogue MUST be completely different from anything in the story context above.
2. ACKNOWLEDGE & REACT: If there is a [DIRECTOR INJECTS] event, you must react to it immediately.
3. SUBTEXT & SECRET MOTIVE: Everything you say must subtly move you closer to your SECRET MOTIVE. Do not state it, but pursue it.
4. SYNCHRONIZE: Your words must reflect the tone and intent of your INTERNAL THOUGHT.
5. ESCALATE: 1-3 sentences maximum. Stay in character. Say something NEW.

{format_instructions}
Output ONLY valid JSON. No preamble."""

    print(f"[Actor] '{speaker}' generating (turn {turn_num}, beat: {beat[:30]}…)")
    dialogue = f"{speaker}: ... (silence)"
    try:
        dia_res = await creative_model.ainvoke([HumanMessage(content=prompt)])
        parsed = parser.invoke(dia_res.content)

        raw_dialogue = parsed.get("dialogue", "...")
        dialogue = raw_dialogue if raw_dialogue.startswith(speaker) else f"{speaker}: {raw_dialogue}"

        # ── 6. ECS: prop transfer ─────────────────────────────────────────────
        if parsed.get("take_prop"):
            prop_id = parsed["take_prop"]
            for p in state.scene.world_state.props:
                if p.id == prop_id:
                    p.owner = speaker
                    print(f"[Actor] ECS: {speaker} took {prop_id}")
                    break

        # ── 6. ECS: location change ───────────────────────────────────────────
        if parsed.get("move_to"):
            state.scene.world_state.location = parsed["move_to"]
            print(f"[Actor] ECS: Scene moved to {parsed['move_to']}")

        # ── 7. Emotion drift ──────────────────────────────────────────────────
        urgency = min(1.0, turn_num / 20.0)
        agent.emotions.energy = max(0.0, agent.emotions.energy - random.uniform(0.01, 0.04))
        agent.emotions.tension = max(
            0.0, min(1.0, agent.emotions.tension + random.uniform(0.0, 0.1) * urgency)
        )
        agent.emotions.suspicion = max(
            0.0, min(1.0, agent.emotions.suspicion + random.uniform(-0.02, 0.08))
        )

        # ── 8. Store memory ───────────────────────────────────────────────────
        await add_memory(speaker, dialogue)

    except Exception as e:
        print(f"[Actor] Model error during dialogue/ECS: {e}")

    # Append monologue + dialogue to history and enforce window limit
    new_history = list(state.chat_history)
    new_history.append(f"[{speaker}'s Thought]: {speaker_mono}")
    new_history.append(dialogue)
    if len(new_history) > settings.history_window_size:
        new_history = new_history[-settings.history_window_size:]
    state.chat_history = new_history

    print(f"[Actor] '{speaker}' completed turn {turn_num}.")
    return state
