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
from app.models.state import AgentState, OrchestratorState, RelationshipVector
from app.services.memory import add_memory, retrieve_memories


def _format_relationships(speaker: str, agent: AgentState) -> str:
    """Format the speaker's stance toward other characters into evocative theatrical subtext."""
    if not agent.relationships:
        return ""

    lines = ["INTERPERSONAL RELATIONSHIPS & SUBTEXT:"]
    for target, rel in agent.relationships.items():
        if target == speaker:
            continue
        trust_str = "High Trust" if rel.trust >= 0.7 else ("Skeptical / Guarded" if rel.trust >= 0.4 else "Zero Trust / Paranoia")
        affinity_str = "Ally / Camaraderie" if rel.affinity >= 0.7 else ("Neutral / Transactional" if rel.affinity >= 0.4 else "Bitter Rival / Contempt")
        fear_str = "Intimidated / Terrified" if rel.fear >= 0.6 else ("Alert / Wary" if rel.fear >= 0.3 else "Fearless")
        dom_str = "Commanding / Dominant" if rel.dominance >= 0.6 else ("Equal / Peer" if rel.dominance >= 0.4 else "Submissive / Deferential")

        lines.append(
            f"- Toward {target}: Trust {int(rel.trust*100)}% ({trust_str}), "
            f"Affinity {int(rel.affinity*100)}% ({affinity_str}), "
            f"Fear {int(rel.fear*100)}% ({fear_str}), "
            f"Dominance {int(rel.dominance*100)}% ({dom_str})"
        )
    return "\n".join(lines) + "\n" if len(lines) > 1 else ""


class ActorOutput(BaseModel):
    dialogue: str = Field(
        description=(
            "The words you say out loud. Use emojis to express feelings. "
            "MUST be completely different from anything said in recent history. "
            "Advance the story — say something NEW."
        )
    )
    emote: Optional[str] = Field(
        None,
        description="A single emoji representing your micro-gesture, reaction, or facial expression (e.g. 💖, ⚡, 🤫, 😳, ☕, 💡, 💭, 💔, 🎲)"
    )
    take_prop: Optional[str] = Field(None, description="A prop ID you want to take")
    move_to: Optional[str] = Field(None, description="A new location to move to")
    addressed_to: Optional[str] = Field(None, description="The name of the other character you are speaking to or reacting to")
    relationship_drift: Optional[dict[str, float]] = Field(
        None,
        description="Shift in your feelings toward addressed_to: e.g. {'trust': -0.05, 'affinity': 0.05, 'fear': 0.0, 'dominance': 0.0}"
    )
    secret_shared: Optional[bool] = Field(
        None,
        description="Set to true if you explicitly confided, gossiped, or leaked a secret/whisper/agenda to addressed_to"
    )


async def _generate_monologue(
    agent_id: str,
    agent: AgentState,
    context_summary: str,
    world_context: str,
    beat: str,
    phases_enabled: bool = True,
) -> dict:
    """Generate one internal monologue for a single agent."""
    try:
        model = get_model(agent.llm_config, creative=True)
        traits = f"Traits: {agent.traits}\n" if agent.traits else ""
        agenda = f"SECRET MOTIVE: {agent.hidden_agenda}\n" if agent.hidden_agenda else ""
        rel_context = _format_relationships(agent_id, agent)
        if agent.pending_whisper and agent.pending_whisper not in agent.known_secrets:
            agent.known_secrets.append(agent.pending_whisper)
        whisper_ctx = (
            f"SECRET IN-EAR DIRECTIVE FROM THE DIRECTOR (CONFIDENTIAL — FOR YOUR EARS ONLY):\n"
            f"\"{agent.pending_whisper}\"\n"
            f"You MUST react to this instruction internally in your thought while keeping it completely concealed from others!\n"
        ) if agent.pending_whisper else ""
        secrets_ctx = (
            f"SECRETS & RUMORS YOU HARBOR: {'; '.join(agent.known_secrets[-3:])}\n"
        ) if agent.known_secrets else ""
        
        if phases_enabled:
            thought_prompt = (
                f"Dramatic beat: {beat}\n"
                f"What is ONE new specific thought you have RIGHT NOW that reflects your secret motive and interpersonal stance? "
                f"One short sentence only. Do not reveal the secret directly."
            )
        else:
            thought_prompt = (
                f"Mode: Direct casual conversation.\n"
                f"What is ONE authentic thought you have RIGHT NOW regarding the conversation? "
                f"One short sentence only."
            )

        prompt = (
            f"You are {agent_id}. {world_context}\n"
            f"{traits}{agenda}{whisper_ctx}{secrets_ctx}{rel_context}"
            f"Story context: {context_summary}\n"
            f"{thought_prompt}"
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
    phases_enabled = getattr(state.scene, "phases_enabled", True)

    # ── 1. Compress history (anti-repetition) ────────────────────────────────
    creative_model = get_model(agent.llm_config, creative=True)
    context = await compress_history(state.chat_history, creative_model)

    # ── 2. Beat-driven vs Direct Conversation writing ────────────────────────
    if phases_enabled:
        beat = get_beat(turn_num)
        mode_instruction = f"DRAMATIC BEAT FOR THIS TURN: {beat}"
        rules_text = (
            "1. Your dialogue MUST be completely different from anything in the story context above.\n"
            "2. ACKNOWLEDGE & REACT: If there is a [DIRECTOR INJECTS] event, you must react to it immediately.\n"
            "3. SUBTEXT & SECRET MOTIVE: Everything you say must subtly move you closer to your SECRET MOTIVE. Do not state it, but pursue it.\n"
            "4. SYNCHRONIZE: Your words must reflect the tone and intent of your INTERNAL THOUGHT.\n"
            "5. ESCALATE: 1-3 sentences maximum. Stay in character. Say something NEW.\n"
            "6. EMOTE: Choose 1 emoji (e.g. 💖, ⚡, 🤫, 😳, ☕, 💡, 💭, 💔, 🎲) that captures your micro-gesture, attitude, or immediate feeling.\n"
            "7. GOSSIP: If you explicitly leaked or shared a confidential secret or rumor to the person you are addressing, set secret_shared: true."
        )
    else:
        beat = "DIRECT CONVERSATION"
        mode_instruction = (
            "MODE: DIRECT CONVERSATION (Phases disabled).\n"
            "Speak naturally and directly to the other character. Do not force dramatic escalation, crisis, or stagey subtext. "
            "Talk as real people having an authentic, unscripted chat in this room."
        )
        rules_text = (
            "1. Speak directly, casually, and authentically to the other character.\n"
            "2. Listen and respond directly to what was just said or asked without forcing artificial conflict.\n"
            "3. Stay true to your personality traits and feelings.\n"
            "4. 1-3 sentences maximum. Natural conversational flow.\n"
            "5. EMOTE: Choose 1 emoji (e.g. 💖, ☕, 💭, 😊, 🥱, 💡, ⚡) capturing your reaction or mood.\n"
            "6. GOSSIP: If you choose to share confidential information or secrets with the other person, set secret_shared: true."
        )

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
        f"Your secret agenda (pursue through subtext and action): {agent.hidden_agenda}"
    ) if agent.hidden_agenda else ""

    # ── 3. Parallel internal monologues (all agents think simultaneously) ─────
    print("[Actor] Generating parallel monologues…")
    mono_tasks = [
        _generate_monologue(aid, ag, context, world_context, beat, phases_enabled=phases_enabled)
        for aid, ag in state.agents.items()
    ]
    monologues = await asyncio.gather(*mono_tasks)
    speaker_mono = next(
        (m["monologue"] for m in monologues if m["agent_id"] == speaker),
        "...",
    )

    # ── 4. Episodic memory retrieval (hybrid insights + observations) ───────
    memories = await retrieve_memories(speaker, context[:200])
    mem_context = f"\n{memories}\n" if memories else ""

    # ── 5. Generate structured dialogue ──────────────────────────────────────
    parser = JsonOutputParser(pydantic_object=ActorOutput)
    format_instructions = parser.get_format_instructions()

    rel_context = _format_relationships(speaker, agent)
    whisper_str = (
        f"CONFIDENTIAL DIRECTOR DIRECTIVE (FOR YOUR EARS ONLY):\n"
        f"\"{agent.pending_whisper}\"\n"
        f"Act upon this secret guidance through your words or physical actions, but stay in character and NEVER quote the director!\n"
    ) if agent.pending_whisper else ""
    secrets_str = (
        f"SECRETS & RUMORS YOU HARBOR:\n" +
        "\n".join([f"- {s}" for s in agent.known_secrets[-3:]]) +
        "\nIf you have high trust (>= 60%) toward the person you are speaking with or if tension is high, you may decide to CONFIDE or GOSSIP by leaking this secret in your words. If you do, set secret_shared: true.\n"
    ) if agent.known_secrets else ""

    prompt = f"""You are {speaker}, an actor in a live theatrical simulation.
{traits_str}
{agenda_str}
{whisper_str}{secrets_str}{rel_context}{world_context}{mem_context}

STORY CONTEXT (what has happened so far):
{context}

YOUR INTERNAL THOUGHT RIGHT NOW: {speaker_mono}

{mode_instruction}

{rules_text}

{format_instructions}
Output ONLY valid JSON. No preamble."""

    print(f"[Actor] '{speaker}' generating (turn {turn_num}, beat: {beat[:30]}…)")
    dialogue = f"{speaker}: ... (silence)"
    is_gossip = False
    gossip_target_clean = None
    try:
        dia_res = await creative_model.ainvoke([HumanMessage(content=prompt)])
        content = dia_res.content if hasattr(dia_res, "content") else str(dia_res)

        parsed = None
        try:
            parsed = parser.invoke(content)
        except Exception:
            # Fallback 1: Extract JSON substring
            import json
            import re
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                try:
                    cleaned_json = re.sub(r",\s*([\]}])", r"\1", match.group(0))
                    parsed = json.loads(cleaned_json)
                except Exception:
                    pass

            # Fallback 2: Plain text response
            if not parsed or not isinstance(parsed, dict):
                cleaned_text = content.strip()
                cleaned_text = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned_text)
                cleaned_text = re.sub(r"```$", "", cleaned_text).strip()
                parsed = {"dialogue": cleaned_text or "..."}

        raw_dialogue = parsed.get("dialogue", "...")
        dialogue = raw_dialogue if raw_dialogue.startswith(speaker) else f"{speaker}: {raw_dialogue}"

        # ── 6. Micro-gesture & Emote ──────────────────────────────────────────
        chosen_emote = parsed.get("emote")
        if not chosen_emote or not isinstance(chosen_emote, str):
            if agent.emotions.tension > 0.65:
                chosen_emote = "⚡"
            elif agent.emotions.affection > 0.65:
                chosen_emote = "💖"
            elif agent.emotions.suspicion > 0.60:
                chosen_emote = "❓"
            elif agent.pending_whisper or agent.known_secrets:
                chosen_emote = "🤫"
            else:
                chosen_emote = "💬"
        agent.last_emote = chosen_emote.strip()[:2]

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

        # ── 7. Emotion & Relationship drift ───────────────────────────────────
        urgency = min(1.0, turn_num / 20.0)
        agent.emotions.energy = max(0.0, agent.emotions.energy - random.uniform(0.01, 0.04))
        agent.emotions.tension = max(
            0.0, min(1.0, agent.emotions.tension + random.uniform(0.0, 0.1) * urgency)
        )
        agent.emotions.suspicion = max(
            0.0, min(1.0, agent.emotions.suspicion + random.uniform(-0.02, 0.08))
        )

        target_name = parsed.get("addressed_to")
        drift = parsed.get("relationship_drift")
        if target_name and isinstance(drift, dict):
            target_clean = target_name.strip()
            if target_clean in agent.relationships:
                rel = agent.relationships[target_clean]
                for metric in ["trust", "affinity", "fear", "dominance"]:
                    if metric in drift and isinstance(drift[metric], (int, float)):
                        curr_val = getattr(rel, metric)
                        new_val = max(0.0, min(1.0, curr_val + float(drift[metric])))
                        setattr(rel, metric, round(new_val, 3))
                print(f"[Actor] Relationship drift for {speaker} toward {target_clean}: {agent.relationships[target_clean]}")

        # ── 8. Secret & Gossip Diffusion ─────────────────────────────────────
        if parsed.get("secret_shared") and target_name:
            target_clean = target_name.strip()
            if target_clean in state.agents:
                is_gossip = True
                gossip_target_clean = target_clean
                target_agent = state.agents[target_clean]
                secret_to_pass = agent.known_secrets[-1] if agent.known_secrets else (agent.pending_whisper or agent.hidden_agenda or "confidential information")
                if secret_to_pass and secret_to_pass not in target_agent.known_secrets:
                    target_agent.known_secrets.append(f"{speaker} confided: {secret_to_pass}")
                    print(f"[Actor] Gossip diffused! '{speaker}' confided secret in '{target_clean}'")

        # ── 9. Store episodic observation ─────────────────────────────────────
        await add_memory(speaker, dialogue, memory_type="observation", turn=turn_num)

    except Exception as e:
        print(f"[Actor] Model error during dialogue/ECS: {e}")

    # ── 10. Consume pending whisper ──────────────────────────────────────────
    if agent.pending_whisper:
        print(f"[Actor] '{speaker}' consumed secret whisper: \"{agent.pending_whisper[:40]}…\"")
        agent.pending_whisper = None

    # Append monologue + dialogue to history (window limit enforced in turn.py after merge)
    new_history = list(state.chat_history)
    new_history.append(f"[{speaker}'s Thought]: {speaker_mono}")
    if is_gossip and gossip_target_clean:
        new_history.append(f"[GOSSIP LEAK]: 🤫 {speaker} confided a secret to {gossip_target_clean}!")
    new_history.append(dialogue)
    state.chat_history = new_history

    print(f"[Actor] '{speaker}' completed turn {turn_num}.")
    return state
