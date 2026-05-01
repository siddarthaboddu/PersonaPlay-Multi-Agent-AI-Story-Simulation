import os
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import JsonOutputParser

from state import SceneState, EmotionVector, AgentState, ModelConfig
from memory import retrieve_memories, add_memory

class OrchestratorState(BaseModel):
    scene: SceneState
    agents: Dict[str, AgentState]
    chat_history: List[str]
    next_speaker: str

def get_model(config: ModelConfig):
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
            timeout=45.0
        )
            
    return ChatOpenAI(
        base_url=config.base_url,
        api_key=api_key,
        model=config.model_name,
        max_retries=0,
        timeout=45.0
    )

async def director_node(state: OrchestratorState) -> OrchestratorState:
    """The Director analyzes narrative tension and assigns the next speaker."""
    print(f"[Backend] Director analyzing state... Turn {state.scene.turn_count}")
    state.scene.turn_count += 1
    
    agent_ids = list(state.agents.keys())
    
    if len(agent_ids) > 2 and state.chat_history:
        try:
            director_agent = state.agents[agent_ids[0]]
            model = get_model(director_agent.llm_config)
            context = "\n".join(state.chat_history[-5:])
            prompt = f"You are the Director. The actors are: {', '.join(agent_ids)}.\nRecent conversation:\n{context}\nWho should speak next? Respond with ONLY the exact name of the character from the list."
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

async def generate_monologue(agent_id, agent, context, world_context):
    try:
        model = get_model(agent.llm_config)
        prompt = f"You are {agent_id}. {world_context}\nRecent history:\n{context}\nWhat are you thinking right now? Keep it to one short sentence."
        res = await model.ainvoke([HumanMessage(content=prompt)])
        return {"agent_id": agent_id, "monologue": res.content.strip()}
    except Exception as e:
        print(f"[Backend] Monologue error for {agent_id}: {e}")
        return {"agent_id": agent_id, "monologue": f"({agent_id} is thinking...)"}

class ActorOutput(BaseModel):
    dialogue: str = Field(description="The words you say out loud. Omit character name.")
    take_prop: Optional[str] = Field(None, description="A prop ID you want to take from the world")
    move_to: Optional[str] = Field(None, description="A new location to move to")

async def actor_node(state: OrchestratorState) -> OrchestratorState:
    """The Actor generates an internal monologue followed by a public action/dialogue."""
    speaker = state.next_speaker
    agent = state.agents[speaker]
    
    context = "\n".join(state.chat_history[-5:]) if state.chat_history else "(Start of scene)"
    
    # Format props for world context
    props_str = ", ".join([f"{p.id} (owned by {p.owner})" for p in state.scene.world_state.props])
    world_context = f"Scene: {state.scene.active_scene}, Location: {state.scene.world_state.location}. Props available: {props_str}"
    
    # 1. Parallel Internal Processing
    print("[Backend] Generating parallel monologues...")
    tasks = [generate_monologue(aid, ag, context, world_context) for aid, ag in state.agents.items()]
    monologues = await asyncio.gather(*tasks)
    
    speaker_mono = next((m["monologue"] for m in monologues if m["agent_id"] == speaker), "...")
    
    # 2. Episodic Memory Retrieval
    memories = retrieve_memories(speaker, context)
    mem_context = f"\nPast Memories:\n{memories}" if memories else ""
    
    # 3. ECS JSON Tool Calling
    parser = JsonOutputParser(pydantic_object=ActorOutput)
    format_instructions = parser.get_format_instructions()
    
    prompt = f"You are {speaker}. {world_context}{mem_context}\nRecent history:\n{context}\nYour internal thought: {speaker_mono}\n\n{format_instructions}\nProvide your next action. Output strictly valid JSON."
    
    print(f"[Backend] Actor '{speaker}' generating dialogue + ECS action...")
    try:
        model = get_model(agent.llm_config)
        dia_res = await model.ainvoke([HumanMessage(content=prompt)])
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
                    
        if parsed.get("move_to"):
            state.scene.world_state.location = parsed["move_to"]
            print(f"[Backend] ECS: Scene moved to {parsed['move_to']}")
            
        add_memory(speaker, dialogue)
        
    except Exception as e:
        print(f"[Backend] Model error during dialogue/ECS: {e}")
        dialogue = f"{speaker}: ... (silence)"
    
    new_chat_history = list(state.chat_history)
    new_chat_history.append(f"[{speaker}'s Thought]: {speaker_mono}")
    new_chat_history.append(dialogue)
    state.chat_history = new_chat_history
    
    print(f"[Backend] Actor '{speaker}' completed turn.")
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
        active_scene="The Disastrous Dinner Party",
        world_state=WorldState(
            location="Formal Dining Room", 
            lighting="Candlelight", 
            props=[
                Prop(id="poisoned_wine", owner="Character_A", visibility="hidden"),
                Prop(id="silver_spoon", owner="Character_B", visibility="visible")
            ]
        ),
        narrative_tension=0.5,
        turn_count=0
    ),
    agents={
        "Character_A": AgentState(id="Character_A", emotions=EmotionVector(tension=0.5, affection=0.5, energy=0.8, suspicion=0.2)),
        "Character_B": AgentState(id="Character_B", emotions=EmotionVector(tension=0.8, affection=0.2, energy=0.5, suspicion=0.9))
    },
    chat_history=[],
    next_speaker=""
)
