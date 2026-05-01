from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from state import SceneState, EmotionVector, AgentState, ModelConfig

# Define Graph State
class OrchestratorState(BaseModel):
    scene: SceneState
    agents: Dict[str, AgentState]
    chat_history: List[str]
    next_speaker: str

def get_model(config: ModelConfig):
    api_key = config.api_key
    
    # Strictly ensure we have a non-empty string for the API key
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
        timeout=45.0  # Prevent hanging forever
    )

def director_node(state: OrchestratorState) -> OrchestratorState:
    """The Director analyzes narrative tension and assigns the next speaker."""
    print(f"[Backend] Director analyzing state... Turn {state.scene.turn_count}")
    state.scene.turn_count += 1
    
    agent_ids = list(state.agents.keys())
    
    # Intelligent speaker selection if we have an LLM configured for it
    if len(agent_ids) > 2 and state.chat_history:
        try:
            director_agent = state.agents[agent_ids[0]] # Just borrow an LLM config
            model = get_model(director_agent.llm_config)
            context = "\n".join(state.chat_history[-5:])
            prompt = f"You are the Director. The actors are: {', '.join(agent_ids)}.\nRecent conversation:\n{context}\nWho should speak next? Respond with ONLY the exact name of the character from the list."
            res = model.invoke([HumanMessage(content=prompt)])
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

def actor_node(state: OrchestratorState) -> OrchestratorState:
    """The Actor generates an internal monologue followed by a public action/dialogue."""
    speaker = state.next_speaker
    agent = state.agents[speaker]
    
    print(f"[Backend] Actor '{speaker}' preparing to generate monologue...")
    
    # Context
    context = "\n".join(state.chat_history[-5:]) if state.chat_history else "(Start of scene)"
    world_context = f"Scene: {state.scene.active_scene}, Location: {state.scene.world_state.location}"
    
    # 1. Monologue
    mono_prompt = f"You are {speaker}. {world_context}\nRecent history:\n{context}\nWhat are you thinking right now? Keep it to one short sentence."
    try:
        model = get_model(agent.llm_config)
        print(f"[Backend] Sending request to {agent.llm_config.provider} at {agent.llm_config.base_url}...")
        mono_res = model.invoke([HumanMessage(content=mono_prompt)])
        monologue = mono_res.content.strip()
        print(f"[Backend] Received monologue: {monologue}")
    except Exception as e:
        print(f"[Backend] Model error during monologue: {e}")
        monologue = f"({speaker} is lost in thought...)"
        
    # 2. Dialogue
    print(f"[Backend] Actor '{speaker}' preparing to generate dialogue...")
    dialogue_prompt = f"You are {speaker}. {world_context}\nRecent history:\n{context}\nYour internal thought: {monologue}\nSay your next line of dialogue. Format as 'CharacterName: dialogue'."
    try:
        model = get_model(agent.llm_config)
        dia_res = model.invoke([HumanMessage(content=dialogue_prompt)])
        dialogue = dia_res.content.strip()
        if not dialogue.startswith(speaker):
            dialogue = f"{speaker}: {dialogue}"
        print(f"[Backend] Received dialogue: {dialogue}")
    except Exception as e:
        print(f"[Backend] Model error during dialogue: {e}")
        dialogue = f"{speaker}: ... (silence)"
    
    # Use a temporary attribute to pass these specific generated values back easily
    # LangGraph states are immutable pydantic models in some contexts, but we can update chat_history
    # Make sure we don't just mutate, but explicitly assign if needed
    new_chat_history = list(state.chat_history)
    new_chat_history.append(monologue)
    new_chat_history.append(dialogue)
    state.chat_history = new_chat_history
    
    print(f"[Backend] Actor '{speaker}' completed turn.")
    return state

# Build Graph - 1 turn per invocation
builder = StateGraph(OrchestratorState)
builder.add_node("director", director_node)
builder.add_node("actor", actor_node)

builder.add_edge(START, "director")
builder.add_edge("director", "actor")
builder.add_edge("actor", END)

# Compile the graph
graph = builder.compile()

from state import WorldState, Prop
initial_state = OrchestratorState(
    scene=SceneState(
        active_scene="The Disastrous Dinner Party",
        world_state=WorldState(location="Formal Dining Room", lighting="Candlelight", props=[]),
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

if __name__ == "__main__":
    print("Graph Compiled Successfully!")
