import os
import asyncio
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import JsonOutputParser

import random
from state import SceneState, EmotionVector, AgentState, ModelConfig
from memory import retrieve_memories, add_memory

# ── Narrative beat map ────────────────────────────────────────────────
# Tells the LLM what *kind* of dramatic moment it's playing right now.
# This forces story progression instead of emotional looping.
NARRATIVE_BEATS = [
    # ── Act I: Establishment ─────────────────────────────────────────
    (0,   3,   "COLD OPEN: Ground yourself in the scene. Establish your mood and your relationship. Be specific — mention something physical about the environment."),
    (4,   7,   "STATUS QUO: Everything seems normal on the surface, but your internal agenda is simmering. Drop one oblique hint — a loaded word, an odd pause, an off-hand comment."),
    (8,   12,  "FIRST FRICTION: Something small goes wrong or catches your attention. React authentically. Begin probing the other person indirectly."),

    # ── Act II-A: Rising Action ──────────────────────────────────────
    (13,  18,  "ESCALATION: The tension you've been suppressing starts leaking out. Ask a question that has a double meaning. Make a subtle move toward your goal."),
    (19,  25,  "COMPLICATION: A new piece of information surfaces — a detail, an object, a memory — that changes the stakes. React to it. Adjust your strategy."),
    (26,  32,  "CONFRONTATION I: You can no longer dance around it. Say something that directly challenges the other person, even if you frame it as a question."),

    # ── Act II-B: Deepening Conflict ─────────────────────────────────
    (33,  40,  "REVELATION: Reveal ONE thing you have been hiding — not everything, just enough to shift the dynamic. Watch how the other person reacts and respond to that."),
    (41,  48,  "POWER SHIFT: The balance of control between you has changed. Press your advantage or scramble to recover. Introduce a new tactic you haven't tried yet."),
    (49,  58,  "CRISIS POINT: The worst possible version of the situation is now visible. React physically — reach for something, stand up, move, or freeze. Let the body betray the mind."),

    # ── Act III: Climax ──────────────────────────────────────────────
    (59,  68,  "CLIMAX I: All pretense is gone. Be completely direct for the first time. Say the thing you have been avoiding saying since the scene began."),
    (69,  80,  "CLIMAX II: The other person has responded to your honesty. This is the point of maximum conflict or maximum vulnerability. Do not back down — escalate or surrender fully."),
    (81,  92,  "BREAKING POINT: Something irreversible happens — a decision is made, an object is thrown, a secret escapes, someone threatens to leave. The scene will never return to what it was."),

    # ── Act IV: Aftermath ────────────────────────────────────────────
    (93,  105, "FALLING ACTION: The explosion has passed. There is strange silence or exhausted energy. Speak carefully now — every word lands differently in the aftermath."),
    (106, 120, "RECKONING: What do you each want NOW, after everything that was said? Negotiate, apologize, double down, or withdraw. Be specific about what you need from the other person."),
    (121, 135, "UNEASY PEACE: A temporary equilibrium forms — fragile, loaded with unspoken things. Behave as if things are fine on the surface, but let undercurrents show in word choice."),

    # ── Act V: Continuation / Long-form loops ───────────────────────
    (136, 155, "NEW COMPLICATION: Time has passed. Something NEW has entered the situation — a sound, a memory, an outside threat, a change in environment. React to it fresh."),
    (156, 175, "SECOND ARC RISING: The resolution you reached was false. The underlying conflict resurfaces in a different form. Begin the push-pull again, but you are both changed by what happened."),
    (176, 200, "SECOND CLIMAX: The stakes are higher now because you know each other better. The confrontation is more precise and more devastating. Say the thing the first climax couldn't reach."),

    # ── Endgame (200+ turns — truly epic simulations) ───────────────
    (201, 999, "EPILOGUE LOOP: The story has told itself many times. Find the one detail — one object, one unsaid word, one gesture — that has never been addressed. Make it the center of this moment."),
]

def get_beat(turn: int) -> str:
    for start, end, beat in NARRATIVE_BEATS:
        if start <= turn <= end:
            return beat
    return NARRATIVE_BEATS[-1][2]


class OrchestratorState(BaseModel):
    scene: SceneState
    agents: Dict[str, AgentState]
    chat_history: List[str]
    next_speaker: str


# ── Layer 1: Model with anti-repetition sampling params ───────────────
def get_model(config: ModelConfig, creative: bool = False):
    """
    creative=True raises temperature and adds presence/frequency penalties.
    These are the model-level knobs that reduce repetition at the token level.
    LM Studio supports all OpenAI-compatible sampling parameters.
    """
    api_key = config.api_key
    if not api_key or str(api_key).strip() == "":
        if config.provider == "openrouter":
            api_key = os.environ.get("OPENROUTER_API_KEY") or "sk-dummy-key-required"
        elif config.provider == "google":
            api_key = os.environ.get("GOOGLE_API_KEY") or "sk-dummy-key-required"
        else:
            api_key = "lm-studio"

    if config.provider == "google":
        return ChatGoogleGenerativeAI(
            model=config.model_name,
            google_api_key=api_key,
            max_retries=0,
            timeout=45.0,
            temperature=0.85 if creative else 0.4,
        )

    kwargs = dict(
        base_url=config.base_url,
        api_key=api_key,
        model=config.model_name,
        max_retries=0,
        timeout=45.0,
    )
    if creative:
        # High temp + presence/frequency penalties = diverse, non-repetitive output
        kwargs["temperature"] = 0.85
        kwargs["model_kwargs"] = {
            "presence_penalty": 0.7,   # penalises tokens that already appeared in context
            "frequency_penalty": 0.5,  # penalises tokens proportional to how often they appeared
        }
    else:
        kwargs["temperature"] = 0.3   # low temp for structured tasks like director selection
    return ChatOpenAI(**kwargs)


# ── Layer 2: History compression ─────────────────────────────────────
async def compress_history(history: List[str], model) -> str:
    """
    Compress old history turns into a compact narrative summary.
    This prevents context poisoning: the LLM no longer sees its own
    repeated outputs as valid examples to copy from.
    Only the last RECENT_RAW turns are kept verbatim; everything before
    that is distilled into a 2-sentence "story so far" block.
    """
    RECENT_RAW = 6  # keep this many turns verbatim at the end

    dialogue_lines = [l for l in history if "'s Thought]:" not in l]

    if len(dialogue_lines) <= RECENT_RAW:
        # Not enough history to bother compressing
        return "\n".join(history[-12:])

    old_lines = dialogue_lines[:-RECENT_RAW]
    recent_lines = history[-RECENT_RAW * 2:]  # include thoughts for recent turns

    old_text = "\n".join(old_lines)
    try:
        summary_prompt = (
            f"Summarize this theatrical exchange in exactly 2 sentences. "
            f"Focus on: what was revealed, what changed, and where the conflict stands now.\n\n{old_text}"
        )
        res = await model.ainvoke([HumanMessage(content=summary_prompt)])
        summary = res.content.strip()
        compressed = f"[STORY SO FAR — {len(old_lines)} earlier lines compressed]: {summary}"
    except Exception as e:
        print(f"[Backend] History compression failed (non-fatal): {e}")
        compressed = f"[STORY SO FAR]: {len(old_lines)} earlier exchanges occurred."

    recent_text = "\n".join(recent_lines)
    return f"{compressed}\n\n[RECENT EXCHANGES]:\n{recent_text}"


async def director_node(state: OrchestratorState) -> OrchestratorState:
    """The Director analyzes narrative tension and assigns the next speaker."""
    print(f"[Backend] Director analyzing state... Turn {state.scene.turn_count}")
    state = state.model_copy(deep=True)
    state.scene.turn_count += 1

    agent_ids = list(state.agents.keys())
    if not agent_ids:
        return state

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
                print(f"[Backend] Director intelligently selected: {suggested}")
                return state
        except Exception as e:
            print(f"[Backend] Director LLM error: {e}")

    if not state.next_speaker or state.next_speaker not in agent_ids:
        state.next_speaker = agent_ids[0]
    else:
        idx = agent_ids.index(state.next_speaker)
        state.next_speaker = agent_ids[(idx + 1) % len(agent_ids)]

    return state


async def generate_monologue(agent_id, agent, context_summary, world_context, beat):
    try:
        model = get_model(agent.llm_config, creative=True)
        prompt = (
            f"You are {agent_id}. {world_context}\n"
            f"Story context: {context_summary}\n"
            f"Dramatic beat: {beat}\n"
            f"What is ONE new specific thought you have RIGHT NOW that you haven't had before? "
            f"One short sentence only. Do not repeat previous thoughts."
        )
        res = await model.ainvoke([HumanMessage(content=prompt)])
        return {"agent_id": agent_id, "monologue": res.content.strip()}
    except Exception as e:
        print(f"[Backend] Monologue error for {agent_id}: {e}")
        return {"agent_id": agent_id, "monologue": f"({agent_id} is thinking...)"}


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


async def actor_node(state: OrchestratorState) -> OrchestratorState:
    """The Actor generates an internal monologue followed by a public action/dialogue."""
    speaker = state.next_speaker

    if speaker not in state.agents:
        print(f"[Backend] Speaker '{speaker}' not found in agents. Skipping.")
        return state

    agent = state.agents[speaker]
    turn_num = state.scene.turn_count

    # ── Layer 2: Compress history so context isn't poisoned by repetition ──
    creative_model = get_model(agent.llm_config, creative=True)
    context = await compress_history(state.chat_history, creative_model)

    # ── Layer 3: Beat-driven writing ─────────────────────────────────────
    beat = get_beat(turn_num)

    props_str = ", ".join([f"{p.id} (owned by {p.owner})" for p in state.scene.world_state.props])
    world_context = (
        f"Scene: {state.scene.active_scene}, "
        f"Location: {state.scene.world_state.location}. "
        f"Props: {props_str}"
    )
    agenda_str = (
        f"Your secret agenda (NEVER reveal this directly — pursue it through subtext and action): "
        f"{agent.hidden_agenda}"
    ) if agent.hidden_agenda else ""

    # 1. Parallel internal monologues (all agents think simultaneously)
    print("[Backend] Generating parallel monologues...")
    tasks = [generate_monologue(aid, ag, context, world_context, beat) for aid, ag in state.agents.items()]
    monologues = await asyncio.gather(*tasks)
    speaker_mono = next((m["monologue"] for m in monologues if m["agent_id"] == speaker), "...")

    # 2. Episodic memory retrieval
    memories = retrieve_memories(speaker, context[:200])  # use compressed summary as query
    mem_context = f"\nYour past experiences relevant to this moment:\n{memories}" if memories else ""

    # 3. Generate dialogue with full anti-repetition prompt
    parser = JsonOutputParser(pydantic_object=ActorOutput)
    format_instructions = parser.get_format_instructions()

    prompt = f"""You are {speaker}, an actor in a live theatrical simulation.

{agenda_str}
{world_context}{mem_context}

STORY CONTEXT (what has happened so far):
{context}

YOUR INTERNAL THOUGHT RIGHT NOW: {speaker_mono}

DRAMATIC BEAT FOR THIS TURN: {beat}

ABSOLUTE RULES:
1. Your dialogue MUST be completely different from anything in the story context above.
2. You must ADVANCE the story: introduce a new detail, physical action, question, revelation, or decision.
3. Do NOT restate your position from previous turns — escalate, pivot, or react to something new.
4. Stay in character. Use subtext — pursue your agenda without stating it directly.
5. 1-3 sentences maximum. Quality over quantity.

{format_instructions}
Output ONLY valid JSON. No preamble."""

    print(f"[Backend] Actor '{speaker}' generating (turn {turn_num}, beat: {beat[:30]}…)")
    try:
        dia_res = await creative_model.ainvoke([HumanMessage(content=prompt)])
        parsed = parser.invoke(dia_res.content)

        dialogue = parsed.get("dialogue", "...")
        if not dialogue.startswith(speaker):
            dialogue = f"{speaker}: {dialogue}"

        if parsed.get("take_prop"):
            prop_id = parsed["take_prop"]
            for p in state.scene.world_state.props:
                if p.id == prop_id:
                    p.owner = speaker
                    print(f"[Backend] ECS: {speaker} took {prop_id}")
                    break

        if parsed.get("move_to"):
            state.scene.world_state.location = parsed["move_to"]
            print(f"[Backend] ECS: Scene moved to {parsed['move_to']}")

        # Emotion drift driven by beat urgency
        urgency = min(1.0, turn_num / 20.0)
        agent.emotions.energy = max(0.0, agent.emotions.energy - random.uniform(0.01, 0.04))
        agent.emotions.tension = max(0.0, min(1.0, agent.emotions.tension + random.uniform(0.0, 0.1) * urgency))
        agent.emotions.suspicion = max(0.0, min(1.0, agent.emotions.suspicion + random.uniform(-0.02, 0.08)))

        add_memory(speaker, dialogue)

    except Exception as e:
        print(f"[Backend] Model error during dialogue/ECS: {e}")
        dialogue = f"{speaker}: ... (silence)"

    new_chat_history = list(state.chat_history)
    new_chat_history.append(f"[{speaker}'s Thought]: {speaker_mono}")
    new_chat_history.append(dialogue)
    # Keep raw history bounded; compression handles the rest at read time
    if len(new_chat_history) > 80:
        new_chat_history = new_chat_history[-80:]
    state.chat_history = new_chat_history

    print(f"[Backend] Actor '{speaker}' completed turn {turn_num}.")
    return state


# Build Graph
builder = StateGraph(OrchestratorState)
builder.add_node("director", director_node)
builder.add_node("actor", actor_node)
builder.add_edge(START, "director")
builder.add_edge("director", "actor")
builder.add_edge("actor", END)
graph = builder.compile()

from state import WorldState, Prop
initial_state = OrchestratorState(
    scene=SceneState(
        active_scene="The Secret Road Trip",
        world_state=WorldState(
            location="A Cluttered Minivan",
            lighting="Flashing Streetlights",
            props=[
                Prop(id="mysterious_duffel_bag", owner="Alex", visibility="visible"),
                Prop(id="half_eaten_pizza", owner="Jamie", visibility="visible")
            ]
        ),
        narrative_tension=0.6,
        turn_count=0
    ),
    agents={
        "Alex": AgentState(
            id="Alex",
            hidden_agenda="Wants to convince Jamie to skip college and drive to Mexico. Secretly terrified of growing up.",
            emotions=EmotionVector(tension=0.6, affection=0.8, energy=0.9, suspicion=0.2),
            llm_config=ModelConfig(provider="lm_studio", base_url="http://localhost:1234/v1", model_name="local-model")
        ),
        "Jamie": AgentState(
            id="Jamie",
            hidden_agenda="Just realized the mysterious duffel bag in the back belongs to a dangerous cartel. Wants to get home immediately without panicking Alex.",
            emotions=EmotionVector(tension=0.9, affection=0.7, energy=0.5, suspicion=0.9),
            llm_config=ModelConfig(provider="lm_studio", base_url="http://localhost:1234/v1", model_name="local-model")
        )
    },
    chat_history=[],
    next_speaker="Alex"
)
