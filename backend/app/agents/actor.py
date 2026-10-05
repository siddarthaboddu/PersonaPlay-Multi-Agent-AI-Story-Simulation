"""
Actor node — generates the private thought + public dialogue for the next speaker.

Responsibilities:
1. Compress chat history (anti-repetition)
2. Retrieve episodic memories for the speaker
3. Generate a single structured JSON turn (thought + dialogue + ECS side-effects)
4. Apply ECS prop/location changes
5. Update emotion, relationship, emote, and secret state
6. Store the new observation in long-term memory

Design note: thought and dialogue are produced in ONE LLM call, not two. The
spoken line is conditioned on the private thought within the same pass, which is
what keeps turn latency at ~2-3s. Do not reintroduce a separate background
monologue call — the old `_generate_monologue` was removed for this reason.
"""
import re
from typing import Literal

from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from app.agents.llm import compress_history, get_model
from app.models.state import AgentState, OrchestratorState
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
    """Format the speaker's feelings toward other characters as psychological cues."""
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
            "Match human conversational cadence. Use short fragments when that is how a real person responds "
            "('Wait, what?', 'Since when?', 'Yeah, I guess.'), and use full sentences only when the emotional "
            "intensity genuinely warrants it. Never deliver speeches. Disfluencies, trailing off with '...', "
            "and self-corrections ('Tuesday—wait, no, Wednesday') are encouraged. Micro-actions may appear "
            "in parentheses (takes a sip) (glances at phone). Strip any 'Name:' prefix."
        )
    )
    emote: str | None = Field(
        default=None,
        description=(
            "A single emoji capturing your current state that the viewer will see hovering above you. "
            "Choose from: 🤫 (hiding/guarding a secret), 😏 (smug/goading), 😰 (nervous/anxious), "
            "💢 (angry/defiant), 😳 (caught off guard), 🤨 (suspicious/questioning), 😭 (hurt/emotional), "
            "😏😏 (eager/excited), 😐 (blank/guarded), or 💀 (deadpan/darkly humorous). Null if neutral."
        )
    )
    addressed_to: str | None = Field(
        default=None,
        description="The exact id of the character this line is directed at, if anyone."
    )
    take_prop: str | None = Field(
        default=None,
        description="id of a prop you physically pick up or take in this moment, if any."
    )
    move_to: str | None = Field(
        default=None,
        description="A new location for the scene, if you physically move somewhere."
    )
    relationship_drift: dict | None = Field(
        default=None,
        description=(
            "Small deltas to how you now feel about the person you just spoke to. "
            "Keys: trust, affinity, fear, dominance. Values are signed floats roughly in [-0.3, 0.3]. "
            "Example: {\"trust\": -0.2, \"fear\": 0.1}. Use null if nothing meaningfully shifted."
        )
    )
    secret_shared: bool | None = Field(
        default=False,
        description=(
            "True ONLY if you deliberately confide a piece of your secret knowledge (or a Director whisper "
            "you are holding) to the person you addressed. Do not set this true for ordinary conversation."
        )
    )
    current_goal: str | None = Field(default=None, description="A modest immediate goal for the next few exchanges. Keep the existing goal unless it was achieved or events changed it.")
    current_attention: str | None = Field(default=None, description="What you are paying attention to right now. Keep it brief.")
    belief_update: str | None = Field(default=None, description="One concise, tentative belief formed or changed because of this exchange. Null if nothing changed. Separate observation from inference.")
    belief_to_revise: str | None = Field(default=None, description="If the new exchange clearly disproves or changes one of your listed beliefs, copy that exact old belief here; otherwise null.")
    emotion_drift: dict | None = Field(default=None, description="Small event-grounded changes to tension, affection, energy, and suspicion, each between -0.12 and 0.12. Use zero when unchanged; do not escalate without evidence.")
    scene_tension_delta: float = Field(default=0.0, description="Change to overall scene tension caused by this exchange, from -0.08 to 0.08. Raise it only for a meaningful conflict or revelation; let it fall when things ease. Usually zero.")
    social_action: Literal["respond", "interject", "stay_silent"] = Field(
        default="respond",
        description="Choose stay_silent only when you have no natural contribution or your personality gives you a reason to hold back. A direct question or human-authored line requires a response.",
    )


async def actor_node(state: OrchestratorState) -> OrchestratorState:
    state = state.model_copy(deep=True)

    speaker = state.next_speaker
    agent = state.agents.get(speaker)
    if not agent:
        print(f"[Actor] '{speaker}' is not a valid agent. Skipping.")
        return state

    turn_num = state.scene.turn_count
    print(f"[Actor] '{speaker}' generating (turn {turn_num}).")

    # ── 1. Chat history compression ───────────────────────────────────────────
    model = get_model(agent.llm_config, creative=True)
    try:
        story = await compress_history(state.chat_history, model)
    except Exception as e:
        print(f"[LLM] History compression unavailable (non-fatal): {e}")
        story = "\n".join(state.chat_history[-12:])

    # ── 2. Determine the exact conversational anchor ──────────────────────────
    # This is what stops the model from ignoring what was just said and pivoting
    # to its own agenda instead. The last line of history is the anchor.
    last_spoken_by: str | None = None
    last_utterance: str | None = None
    for line in reversed(state.chat_history):
        if not line or line.startswith("["):
            continue
        if ":" in line:
            maybe_speaker, _, maybe_content = line.partition(":")
            last_spoken_by = maybe_speaker.strip()
            last_utterance = maybe_content.strip()
            break

    is_manual_reply = (
        state.manual_reply_speaker == speaker
        and bool(state.manual_reply_content)
    )

    # ── 3. Retrieve episodic memory for this speaker ─────────────────────────
    memory_query = last_utterance or story
    memories = await retrieve_memories(speaker, memory_query, k_insights=2, k_observations=2, k_beliefs=2)

    # ── 4. Build the psychological prompt ────────────────────────────────────
    traits = agent.traits or "Just a normal person."
    private_notes: list[str] = []

    if agent.pending_whisper:
        private_notes.append(
            f"DIRECTOR WHISPER (you must obey, but keep it secret): {agent.pending_whisper}"
        )
        # Archive the directive so the character still *knows* it after the
        # one-shot pending_whisper is consumed at the end of this turn. Without
        # this, an obeyed whisper is forgotten immediately and the character
        # cannot later leak it or act on it.
        archived = f"SECRET IN-EAR DIRECTIVE FROM THE DIRECTOR: {agent.pending_whisper}"
        if archived not in agent.known_secrets:
            agent.known_secrets.append(archived)

    social_target = state.manual_reply_speaker or last_spoken_by
    if social_target and social_target in state.agents:
        role_context = agent.relationship_context.get(social_target)
        if role_context:
            private_notes.append(f"Social reality with {social_target}: {role_context[:300]}")

    if agent.known_secrets:
        private_notes.append("Secrets you are currently holding: " + " | ".join(agent.known_secrets))

    private_context = "\n".join(f"- {n}" for n in private_notes) if private_notes else "- Nothing unusual."

    # World state
    world_context = (
        f"Location: {state.scene.world_state.location}\n"
        f"Lighting: {state.scene.world_state.lighting}"
    )
    perceivable_props = [
        prop for prop in state.scene.world_state.props
        if prop.visibility == "visible" or prop.owner == speaker
    ]
    if perceivable_props:
        props_text = "\n".join(
            f"- {prop.id}: {prop.description} (held by {prop.owner})"
            for prop in perceivable_props
        )
        world_context += f"\nObjects you can see or are carrying:\n{props_text}"

    rules_text = (
        "GROUND RULES:\n"
        "- Speak as a real human, NOT a stage character. No 'audience', no 'scene', no stage directions.\n"
        "- Respond when appropriate, but you may ask a follow-up, address another person, briefly interrupt, or let a small topic pass. Do not force a plot twist every turn.\n"
        "- Answer direct questions honestly or evade only when your character has a clear reason. Avoid unrelated subject changes.\n"
        "- Length follows emotional intensity, not a quota. A short reaction, question, gesture, or silence can be natural.\n"
        "- Preserve speech quirks, vocabulary, habits, and boundaries. Do not repeat facts everyone already knows.\n"
        "- Keep ordinary needs and immediate goals active alongside any hidden agenda. Do not treat every exchange as a dramatic beat."
    )

    # Conversational anchoring
    if is_manual_reply:
        immediate_anchor = (
            "MANDATORY REPLY: The line you are replying to was written by the human user "
            f"speaking AS {state.manual_reply_speaker}. It reads:\n"
            f"\"{state.manual_reply_content}\"\n"
            "You MUST acknowledge and respond to that specific sentence. This is the most "
            "important rule in this prompt."
        )
    elif last_spoken_by and last_utterance:
        immediate_anchor = (
            f"{last_spoken_by} just said: \"{last_utterance}\"\n"
            "Treat this as the latest conversational context. Reply directly if you have something natural to say; you may also follow an earlier thread, address someone else, or stay quiet when that fits. Do not invent an unrelated dramatic turn."
        )
    else:
        immediate_anchor = "This is the opening of the scene. Speak first."

    output_schema = ActorOutput.model_json_schema()

    prompt = f"""You are {speaker}.

--- WHO YOU ARE ---
{traits}

--- WHAT MATTERS TO YOU ---
{chr(10).join('- ' + item for item in agent.motivations) or '- No explicit long-term motivations; act from your personality and immediate circumstances.'}

--- WHAT YOU WANT RIGHT NOW ---
{agent.current_goal or 'Choose a modest, ordinary short-term goal that fits the moment.'}

--- WHAT YOU CURRENTLY BELIEVE ---
{chr(10).join('- ' + item for item in agent.beliefs[-8:]) or '- No settled beliefs yet.'}
These are fallible interpretations, not objective facts. Update or discard them when new evidence warrants it.

--- WHAT HAS YOUR ATTENTION ---
{agent.current_attention or 'Nothing specific.'}

--- HOW YOU FEEL RIGHT NOW ---
Tension {agent.emotions.tension:.2f}, affection {agent.emotions.affection:.2f}, energy {agent.emotions.energy:.2f}, suspicion {agent.emotions.suspicion:.2f}.

--- WHERE YOU ARE ---
{world_context}

--- YOUR SECRET AGENDA (never reveal directly) ---
{agent.hidden_agenda or "You have no special agenda. Just be yourself."}

--- WHAT YOU ARE HOLDING ---
{private_context}

--- YOUR INNER CIRCLE ---
{_format_relationships(speaker, agent)}

--- WHAT HAS HAPPENED SO FAR ---
{story}

--- DIRECT RESPONSE REQUIREMENT ---
{immediate_anchor}

--- HOW YOU SHOULD SPEAK ---
{rules_text}

--- LONG-TERM MEMORY ---
{memories}

Generate ONE JSON object matching this schema:
{output_schema}
"""

    # ── 5. Generate, repair, and apply side-effects ──────────────────────────
    speaker_mono = "..."
    dialogue = ""
    belief_update = None
    belief_to_revise = None
    is_gossip = False
    gossip_target_clean = ""
    # Always clear any inherited value so a turn with no leak cannot inherit the
    # previous turn's gossip flag through the state copy.
    state.gossip_target = None

    try:
        response = await model.ainvoke([HumanMessage(content=prompt)])
        content = response.content
        raw = content if isinstance(content, str) else str(content)
        print(f"[Actor Output for {speaker}]: {raw[:200]}…", flush=True)

        parser = JsonOutputParser()
        try:
            parsed = parser.parse(raw)
        except Exception:
            # Repair pass: small local models often emit markdown-fenced JSON.
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
            parsed = parser.parse(cleaned)

        speaker_mono = parsed.get("thought") or "..."
        dialogue = parsed.get("dialogue") or "..."
        is_silent = (
            parsed.get("social_action") == "stay_silent"
            and not is_manual_reply
            and bool(last_spoken_by)
        )
        if is_silent:
            dialogue = ""
        if parsed.get("current_goal"):
            agent.current_goal = str(parsed["current_goal"]).strip()[:240]
        if parsed.get("current_attention"):
            agent.current_attention = str(parsed["current_attention"]).strip()[:240]
        if parsed.get("belief_update"):
            belief_update = str(parsed["belief_update"]).strip()[:300]
            belief_to_revise = parsed.get("belief_to_revise")
            if belief_to_revise in agent.beliefs:
                agent.beliefs.remove(belief_to_revise)
            if belief_update and belief_update not in agent.beliefs:
                agent.beliefs = (agent.beliefs + [belief_update])[-12:]

        # ── 6. Lexical relevance repair ───────────────────────────────────────
        # If the user spoke manually and the reply ignores them entirely, force
        # one corrective rewrite. This is the anti-deflection guarantee.
        if is_manual_reply and state.manual_reply_content and not _directly_acknowledges(
            state.manual_reply_content, dialogue
        ):
            print(f"[Actor] Relevance miss for '{speaker}' — running repair pass.")
            repair_prompt = (
                f"{prompt}\n\n"
                "IMPORTANT: The previous attempt ignored what the user actually said. "
                f"The user said: \"{state.manual_reply_content}\". "
                "Rewrite the `dialogue` field so it directly and explicitly responds to "
                "that exact sentence. Keep the same JSON schema. Output only the JSON object."
            )
            repair_result = await model.ainvoke([HumanMessage(content=repair_prompt)])
            rcontent = repair_result.content
            rraw = rcontent if isinstance(rcontent, str) else str(rcontent)
            rcleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", rraw.strip(), flags=re.MULTILINE)
            repaired = parser.parse(rcleaned)
            if repaired.get("dialogue"):
                dialogue = repaired["dialogue"]
                if repaired.get("thought"):
                    speaker_mono = repaired["thought"]
                if repaired.get("emote"):
                    agent.last_emote = repaired["emote"]
                print(f"[Actor] Repair successful for '{speaker}'.")

        # ── 7. Emote ─────────────────────────────────────────────────────────
        if parsed.get("emote"):
            agent.last_emote = str(parsed["emote"])[:4]

        # ── 8. ECS: prop transfer ─────────────────────────────────────────────
        prop_id = parsed.get("take_prop")
        if prop_id:
            for p in state.scene.world_state.props:
                if p.id == prop_id:
                    p.owner = speaker
                    print(f"[Actor] ECS: {speaker} took {prop_id}")
                    break

        # ── 9. ECS: location change ───────────────────────────────────────────
        if parsed.get("move_to"):
            state.scene.world_state.location = parsed["move_to"]
            print(f"[Actor] ECS: Scene moved to {parsed['move_to']}")

        # ── 10. Emotion & relationship drift ───────────────────────────────────
        emotion_drift = parsed.get("emotion_drift")
        if isinstance(emotion_drift, dict):
            for metric in ("tension", "affection", "energy", "suspicion"):
                delta = emotion_drift.get(metric)
                if isinstance(delta, (int, float)):
                    current = getattr(agent.emotions, metric)
                    bounded_delta = max(-0.12, min(0.12, float(delta)))
                    setattr(agent.emotions, metric, round(max(0.0, min(1.0, current + bounded_delta)), 3))

        raw_scene_delta = parsed.get("scene_tension_delta", 0.0)
        if isinstance(raw_scene_delta, (int, float)):
            scene_delta = max(-0.08, min(0.08, float(raw_scene_delta)))
            state.scene.narrative_tension = round(max(0.0, min(1.0, state.scene.narrative_tension + scene_delta)), 3)

        target_name = None if is_silent else parsed.get("addressed_to")
        agent.last_addressee = (
            target_name.strip()
            if isinstance(target_name, str) and target_name.strip() in state.agents
            else None
        )
        agent.last_spoke_turn = turn_num
        drift = parsed.get("relationship_drift")
        if target_name and isinstance(drift, dict):
            target_clean = target_name.strip()
            if target_clean in agent.relationships:
                rel = agent.relationships[target_clean]
                for metric in ("trust", "affinity", "fear", "dominance"):
                    if metric in drift and isinstance(drift[metric], (int, float)):
                        curr_val = getattr(rel, metric)
                        new_val = max(0.0, min(1.0, curr_val + float(drift[metric])))
                        setattr(rel, metric, round(new_val, 3))
                print(f"[Actor] Relationship drift for {speaker} toward {target_clean}: {agent.relationships[target_clean]}")

        # ── 11. Secret & gossip diffusion ─────────────────────────────────────
        # A leak only counts if knowledge ACTUALLY moved. Previously the
        # is_gossip flag was raised before the dedup check, so a character
        # re-confiding something the target already knew still rendered a
        # "Secret Confided" badge while transferring nothing.
        if parsed.get("secret_shared") and target_name:
            target_clean = target_name.strip()
            if target_clean in state.agents and target_clean != speaker:
                target_agent = state.agents[target_clean]
                secret_to_pass = (
                    agent.known_secrets[-1]
                    if agent.known_secrets
                    else (agent.pending_whisper or agent.hidden_agenda or "confidential information")
                )
                if secret_to_pass:
                    # Compare against the exact form we store. Comparing the
                    # raw secret against the prefixed entries never matches, so
                    # re-confiding the same secret appended a duplicate on every
                    # turn and grew known_secrets without bound.
                    entry = f"{speaker} confided: {secret_to_pass}"
                    if entry not in target_agent.known_secrets:
                        target_agent.known_secrets.append(entry)
                        is_gossip = True
                        gossip_target_clean = target_clean
                        state.gossip_target = f"{speaker} -> {target_clean}"
                        print(f"[Actor] Gossip diffused! '{speaker}' confided secret to '{target_clean}'")
                    else:
                        print(f"[Actor] '{speaker}' tried to confide to '{target_clean}', but nothing new transferred.")

        # ── 12. Store episodic observation ────────────────────────────────────
        if dialogue:
            await add_memory(speaker, dialogue, memory_type="event", turn=turn_num)
        if belief_update:
            belief_memory = (
                f"Revised belief: {belief_to_revise} -> {belief_update}"
                if belief_to_revise
                else belief_update
            )
            await add_memory(speaker, belief_memory, memory_type="belief", turn=turn_num)

    except Exception as e:
        print(f"[Actor] Model error during dialogue/ECS: {e}")

    # ── 13. Consume the pending whisper (one-shot) ───────────────────────────
    if agent.pending_whisper:
        print(f"[Actor] '{speaker}' consumed secret whisper: \"{agent.pending_whisper[:40]}…\"")
        agent.pending_whisper = None

    # Append monologue + dialogue to history. The window limit is enforced in
    # turn.py after the merge, not here.
    new_history = list(state.chat_history)
    new_history.append(f"[{speaker}'s Thought]: {speaker_mono}")
    if is_gossip and gossip_target_clean:
        new_history.append(f"[GOSSIP LEAK]: 🤫 {speaker} confided a secret to {gossip_target_clean}!")
    if dialogue:
        new_history.append(dialogue)
    state.chat_history = new_history

    print(f"[Actor] '{speaker}' completed turn {turn_num}.")
    return state
