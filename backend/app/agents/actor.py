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
import re
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputParser

from app.agents.beats import get_beat
from app.agents.llm import get_model, compress_history
from app.config import settings
from app.models.state import AgentState, OrchestratorState, RelationshipVector
from app.services.memory import add_memory, retrieve_memories


_REPLY_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "for", "from", "i", "in", "is",
    "it", "me", "my", "of", "on", "or", "that", "the", "this", "to", "was", "we", "with",
    "you", "your",
}


def _directly_acknowledges(source: str, reply: str) -> bool:
    """Cheap first-pass relevance check; only obvious misses get one repair retry."""
    source_words = {
        word for word in re.findall(r"[a-zA-Z']+", source.lower())
        if len(word) > 2 and word not in _REPLY_STOPWORDS
    }
    if not source_words:
        return True
    reply_words = set(re.findall(r"[a-zA-Z']+", reply.lower()))
    return bool(source_words & reply_words)


def _format_relationships(speaker: str, agent: AgentState) -> str:
    """Format the speaker's emotional feelings toward other characters into natural psychological cues."""
    if not agent.relationships:
        return ""

    lines = ["INTERPERSONAL RELATIONSHIPS & SUBTEXT:"]
    for target, rel in agent.relationships.items():
        if target == speaker:
            continue
        trust_str = "Deep Trust" if rel.trust >= 0.7 else ("Cautious / Guarded" if rel.trust >= 0.4 else "Zero Trust / Suspicious")
        affinity_str = "Positive" if rel.affinity >= 0.7 else ("Neutral / Polite" if rel.affinity >= 0.4 else "Strained / Distant")
        fear_str = "Anxious / Walking on eggshells" if rel.fear >= 0.6 else ("Careful / Alert" if rel.fear >= 0.3 else "Completely relaxed")
        dom_str = "Leading the conversation" if rel.dominance >= 0.6 else ("Balanced" if rel.dominance >= 0.4 else "Deferential / Accommodating")

        lines.append(
            f"- Toward {target}: Trust {int(rel.trust*100)}% ({trust_str}), "
            f"Affinity {int(rel.affinity*100)}% ({affinity_str}), "
            f"Fear {int(rel.fear*100)}% ({fear_str}), "
            f"Dominance {int(rel.dominance*100)}% ({dom_str})"
        )
    return "\n".join(lines) + "\n" if len(lines) > 1 else ""


class ActorOutput(BaseModel):
    thought: str = Field(
        default="...",
        description=(
            "Your immediate, unfiltered, messy internal gut thought in first person ('I...'). "
            "Raw stream of consciousness reacting to what was just said, your secret agenda, or a director whisper. "
            "Never speak this out loud. (e.g. 'Wait, why is he asking me that?', 'Act natural, don't bring up the concert tickets.')."
        )
    )
    dialogue: str = Field(
        description=(
            "What you speak out loud to the other person. Speak as an authentic, real human. "
            "Match human conversational cadences: can be a brief reaction or fragment ('Wait, really?', 'I mean... maybe?'), "
            "a casual sentence, or an explanation. You may include subtle physical micro-actions in parentheses like (looks away) or (sips coffee). "
            "Never sound like a stage actor, robot, or book narrator."
        )
    )
    emote: Optional[str] = Field(
        None,
        description="A single emoji representing your micro-gesture, attitude, or facial expression (e.g. ☕, 💭, 😳, 🙄, 🤫, 💡, 🥱, 💖, ⚡)"
    )
    take_prop: Optional[str] = Field(None, description="A prop ID you want to take or use")
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
    """Generate one raw internal stream-of-consciousness thought for a single agent."""
    try:
        model = get_model(agent.llm_config, creative=True)
        traits = f"Traits: {agent.traits}\n" if agent.traits else ""
        agenda = f"SECRET MOTIVE / PERSONAL DESIRE: {agent.hidden_agenda}\n" if agent.hidden_agenda else ""
        rel_context = _format_relationships(agent_id, agent)
        if agent.pending_whisper and agent.pending_whisper not in agent.known_secrets:
            agent.known_secrets.append(agent.pending_whisper)
        whisper_ctx = (
            f"SECRET IN-EAR DIRECTIVE FROM THE DIRECTOR (CONFIDENTIAL — FOR YOUR EARS ONLY):\n"
            f"\"{agent.pending_whisper}\"\n"
            f"You MUST react to this instruction internally in your thought while keeping it completely concealed from others!\n"
        ) if agent.pending_whisper else ""
        secrets_ctx = (
            f"SECRETS & PRIVATE THOUGHTS YOU HARBOR: {'; '.join(agent.known_secrets[-3:])}\n"
        ) if agent.known_secrets else ""
        
        thought_prompt = (
            "What is your immediate, unfiltered gut thought right now? "
            "Not a theatrical soliloquy, but the raw, messy internal voice inside your head "
            "(e.g. 'Wait, why is he asking me that?', 'Don't bring up the money, just act normal', "
            "'I'm so exhausted, can we please not do this right now?'). "
            "One raw, authentic thought in first person ('I...')."
        )

        prompt = (
            f"You are {agent_id}. {world_context}\n"
            f"{traits}{agenda}{whisper_ctx}{secrets_ctx}{rel_context}"
            f"Conversation context: {context_summary}\n"
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
    # A manual line gets a dedicated reply mode. It must override the usual
    # creative/topic-expanding behavior for exactly one response.
    manual_reply_speaker = state.manual_reply_speaker
    manual_reply_content = state.manual_reply_content
    is_manual_reply = bool(
        manual_reply_speaker
        and manual_reply_content
        and manual_reply_speaker != speaker
    )
    creative_model = get_model(
        agent.llm_config,
        creative=True,
        focused_reply=is_manual_reply,
    )
    context = await compress_history(state.chat_history, creative_model)

    # ── 2. Realistic Conversational Guidance ──────────────────────────────────
    if phases_enabled:
        beat = get_beat(turn_num)
        mode_instruction = f"SITUATION UNDERTONE / DRAMATIC ARC: {beat}"
    else:
        beat = "DIRECT CONVERSATION"
        mode_instruction = "SITUATION: An authentic, direct, unscripted everyday conversation."

    rules_text = (
        "HUMAN CONVERSATIONAL REALISM RULES:\n"
        "1. AUTHENTIC VOCAL CADENCE: Speak exactly as real people talk out loud in a room. "
        "Use natural phrasing, contractions ('I'm', 'didn't', 'gonna'), and everyday vocabulary. Never use bookish eloquence, Shakespearean melodrama, or theatrical monologues.\n"
        "2. NATURAL LENGTH & BREVITY: Real human speech is dynamic! Your line can be:\n"
        "   - A brief reactive fragment or exclamation ('Wait, really?', 'Since when?', 'Yeah, I guess.', 'Hold on.')\n"
        "   - A single casual sentence answering or reacting to the other person.\n"
        "   - An interrupted thought or hesitation ('I was just thinking... never mind.')\n"
        "   - Or 1-2 conversational sentences. Do NOT deliver formal paragraph speeches.\n"
        "3. NO DEFLECTION TO DOMESTIC CHORES OR DRINKS: Never respond to a direct statement, confession, or action by offering tea, water, food, or changing the subject! Address what was just said/done directly with emotional, verbal, or physical presence.\n"
        "4. DIRECT CONVERSATIONAL COMMITMENT: If the other person asks you a question, makes a request, or does a physical action in front of you, answer and address it directly! Never pretend they didn't say or do it.\n"
        "5. DISFLUENCIES & HESITATIONS: Natural speech has pauses, self-corrections ('Tuesday—wait, no, Wednesday'), "
        "and trailing off ('...'). Use them naturally when unsure or guarded.\n"
        "6. PHYSICAL ACTIONS: You may include natural micro-gestures or physical reactions in parentheses, e.g. *(looks down)*, *(steps closer)*, *(hesitates, hand trembling)*."
    )

    # Keep the actual prompt compact. The verbose rules above are retained here
    # only as reference while this working tree is evolving.
    rules_text = (
        "REPLY RULES:\n"
        "- Speak naturally and briefly: usually one or two sentences.\n"
        "- Reply to the latest line before adding anything new.\n"
        "- Have a real opinion, feeling, or stake; do not merely agree and stop.\n"
        "- Let private context color the reply; never force an unrelated pivot.\n"
        "- A small pause or micro-action is fine; do not narrate or make a speech."
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
    world_context = f"Scene: {state.scene.active_scene}; {state.scene.world_state.location}; {state.scene.world_state.lighting}."
    if props_str:
        world_context += f" Visible items: {props_str}."
    traits_str = f"Personality: {agent.traits}\n" if agent.traits else ""
    agenda_str = (
        f"BACKGROUND MOTIVATION & SUBTEXT:\n"
        f"Your private desires: {agent.hidden_agenda}\n"
        f"IMPORTANT: Use this background context to inform how you react, but never derail the conversation to force unrelated plot points.\n"
    ) if agent.hidden_agenda else ""

    # ── 3. Episodic memory retrieval (hybrid insights + observations) ───────
    # The immediately preceding line matters more than recalled material. Skip
    # memory on a manual reply, where extra context causes irrelevant pivots.
    memories = "" if is_manual_reply else await retrieve_memories(speaker, context[:200])
    memory_context = (
        f"\nOPTIONAL RECALL (only use it when it directly helps):\n{memories[:500]}\n"
        if memories else ""
    )

    # ── 4. Extract the immediate previous utterance to respond to ─────────────
    last_spoken_by = None
    last_utterance = None
    for line in reversed(state.chat_history):
        if not line or line.startswith("["):
            continue
        if ":" in line:
            cand_speaker, cand_text = line.split(":", 1)
            cand_speaker = cand_speaker.strip()
            if cand_speaker != speaker:
                last_spoken_by = cand_speaker
                last_utterance = cand_text.strip()
                break

    immediate_anchor = ""
    if is_manual_reply:
        immediate_anchor = f"""
======================================================================
MANUAL CHARACTER INPUT — MANDATORY REPLY TURN
{manual_reply_speaker} just said: "{manual_reply_content}"

Your dialogue is a direct reply to this exact line. Your FIRST sentence must
answer, react to, or explicitly acknowledge it. Do not change the subject.
Do not bring up your agenda, memories, food, drinks, props, or an unrelated
event until you have directly responded. This instruction overrides all other
creative or narrative impulses for this turn.
======================================================================
"""
    elif last_spoken_by and last_utterance:
        immediate_anchor = f"""
======================================================================
⚡ PRIORITY ONE — IMMEDIATE CONVERSATIONAL FOCUS:
{last_spoken_by} just said or did directly in front of you: "{last_utterance}"

YOUR TASK:
1. In 'thought': React privately in your head directly to "{last_utterance}".
2. In 'dialogue': Speak directly back to {last_spoken_by}, addressing their specific question, request, or action!
CRITICAL RULES:
- DIRECT RELEVANCE: You MUST directly address what was just said or done. Do NOT ignore it!
- NO UNRELATED PIVOTS: Do NOT offer unrelated drinks (water, tea), food, or domestic chores. Stay locked onto what {last_spoken_by} asked or presented!
- COMMIT IN CHARACTER: Address their specific words or action directly in accordance with your personality and feelings.
======================================================================
"""

    # ── 5. Unified single-pass generation (thought + spoken line) ────────────
    parser = JsonOutputParser(pydantic_object=ActorOutput)

    rel_context = _format_relationships(speaker, agent)
    if agent.pending_whisper and agent.pending_whisper not in agent.known_secrets:
        agent.known_secrets.append(agent.pending_whisper)
    whisper_str = (
        f"CONFIDENTIAL DIRECTOR DIRECTIVE (FOR YOUR EARS ONLY):\n"
        f"\"{agent.pending_whisper}\"\n"
        f"React to this instruction internally in your 'thought' field, and act upon it in character through your dialogue or physical actions. NEVER quote the director!\n"
    ) if agent.pending_whisper else ""
    secrets_str = (
        f"SECRETS & RUMORS YOU HARBOR:\n" +
        "\n".join([f"- {s}" for s in agent.known_secrets[-3:]]) +
        "\nIf you have high trust (>= 60%) toward the person you are speaking with or if tension is high, you may decide to CONFIDE or GOSSIP by leaking this secret in your words. If you do, set secret_shared: true.\n"
    ) if agent.known_secrets else ""

    # Private context stays deliberately small. It should shade a response, not
    # compete with the person standing in front of the character.
    private_notes = []
    if agent.hidden_agenda:
        private_notes.append(f"Motive: {agent.hidden_agenda[:300]}")
    if agent.pending_whisper:
        private_notes.append(f"Director cue: {agent.pending_whisper[:300]}")
    elif agent.known_secrets:
        private_notes.append(f"Private knowledge: {agent.known_secrets[-1][:300]}")
    if agent.relationships:
        target, relationship = next(iter(agent.relationships.items()))
        private_notes.append(
            f"Toward {target}: trust {relationship.trust:.1f}, affinity {relationship.affinity:.1f}, "
            f"fear {relationship.fear:.1f}."
        )
    social_target = manual_reply_speaker or last_spoken_by
    if social_target:
        role_context = agent.relationship_context.get(social_target)
        if role_context:
            private_notes.append(f"Social reality with {social_target}: {role_context[:300]}")
    private_context = "\n".join(private_notes)

    # The last spoken line is the task. Keep this anchor short enough that it
    # remains obvious even to smaller local models.
    if is_manual_reply:
        immediate_anchor = (
            f"MANDATORY REPLY — {manual_reply_speaker}: \"{manual_reply_content}\"\n"
            "First sentence: directly answer, react to, or acknowledge that line. "
            "No unrelated topic before the reply."
        )
    elif last_spoken_by and last_utterance:
        immediate_anchor = (
            f"LATEST LINE — {last_spoken_by}: \"{last_utterance}\"\n"
            "Reply directly before adding anything new."
        )

    if is_manual_reply:
        conversation_drive = (
            "After the direct reply, add at most one natural follow-up, question, "
            "or emotional reaction that stays on this subject."
        )
    elif last_spoken_by and last_utterance:
        conversation_drive = (
            "After replying, move the conversation one small relevant step: ask a question, "
            "push back, reveal a feeling, or make a concrete observation."
        )
    else:
        conversation_drive = "Open naturally with a concrete observation, feeling, or question."

    social_reality_instruction = (
        "SOCIAL REALITY: Register the practical and emotional meaning of the latest line. "
        "Do not act as if a meaningful statement were ordinary. React in character with a clear "
        "feeling, question, disagreement, concern, humor, or acknowledgement when it fits."
    )

    thought_guidance = (
        "INTERNAL THOUGHT GUIDELINES:\n"
        "In your 'thought' field, generate your immediate, unfiltered gut reaction in first person ('I...'). "
        "React honestly to what was just said. Never speak this out loud.\n"
        "Then, in your 'dialogue' field, produce what you actually say aloud, directly replying to what was said to you."
    )

    # A compact JSON contract is more reliable for local models than embedding
    # the complete Pydantic schema and its long field descriptions in every turn.
    format_instructions = (
        'Return only one JSON object: '
        '{"thought":"private reaction", "dialogue":"spoken reply", '
        '"emote":"one emoji or null", "addressed_to":"name or null", '
        '"relationship_drift":null, "secret_shared":false, '
        '"take_prop":null, "move_to":null}.'
    )

    prompt = f"""You are {speaker}, having a real conversation right now.
{traits_str}{world_context}

PRIVATE CONTEXT (background only; never use it to dodge the conversation):
{private_context or 'None'}

RECENT CONVERSATION:
{context}
{memory_context}

{mode_instruction}
{rules_text}

{immediate_anchor}

{social_reality_instruction}

Think privately first, then speak aloud. Keep thought short and in first person.
{conversation_drive}
{format_instructions}"""

    trigger = manual_reply_content if is_manual_reply else last_utterance
    print(f"\n[Actor] '{speaker}' generating (turn {turn_num}). Immediate trigger: '{trigger or 'Opening'}'", flush=True)
    speaker_mono = "..."
    dialogue = f"{speaker}: ... (silence)"
    is_gossip = False
    gossip_target_clean = None
    try:
        dia_res = await creative_model.ainvoke([HumanMessage(content=prompt)])
        content = dia_res.content if hasattr(dia_res, "content") else str(dia_res)
        print(f"[Actor Output for {speaker}]: {content[:200]}…", flush=True)

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
                parsed = {"thought": "...", "dialogue": cleaned_text or "..."}

        extracted_thought = str(parsed.get("thought", "")).strip()
        if extracted_thought and extracted_thought != "...":
            speaker_mono = extracted_thought
        else:
            speaker_mono = f"({speaker} pauses for a moment)"

        raw_dialogue = parsed.get("dialogue", "...")
        if is_manual_reply and not _directly_acknowledges(manual_reply_content, raw_dialogue):
            repair_prompt = f"""You are {speaker}. Your last reply failed to acknowledge this line:
"{manual_reply_content}"

Rewrite only the JSON response. The first spoken sentence must directly react to
the meaning of that line in character. Do not change the subject.
{format_instructions}"""
            try:
                repair_result = await creative_model.ainvoke([HumanMessage(content=repair_prompt)])
                repaired = parser.invoke(
                    repair_result.content if hasattr(repair_result, "content") else str(repair_result)
                )
                if isinstance(repaired, dict) and repaired.get("dialogue"):
                    parsed = repaired
                    raw_dialogue = parsed["dialogue"]
            except Exception as repair_error:
                print(f"[Actor] Reply repair skipped: {repair_error}")
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
