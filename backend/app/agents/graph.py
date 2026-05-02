"""
LangGraph builder and default scene loader.

The graph is compiled once at module import time and reused across all sessions.
The initial_state is loaded from a YAML scene file so it can be changed without
touching source code.
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml
from langgraph.graph import END, START, StateGraph

from app.agents.actor import actor_node
from app.agents.director import director_node
from app.config import settings
from app.models.state import (
    AgentState,
    EmotionVector,
    ModelConfig,
    OrchestratorState,
    Prop,
    SceneState,
    WorldState,
)


# ── Graph ─────────────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    builder = StateGraph(OrchestratorState)
    builder.add_node("director", director_node)
    builder.add_node("actor", actor_node)
    builder.add_edge(START, "director")
    builder.add_edge("director", "actor")
    builder.add_edge("actor", END)
    return builder.compile()


graph = build_graph()


# ── Scene loader ──────────────────────────────────────────────────────────────

def _load_model_config(raw: dict) -> ModelConfig:
    return ModelConfig(**raw)


def _load_agent(agent_id: str, raw: dict) -> AgentState:
    emotions = EmotionVector(**raw.get("emotions", {}))
    llm_cfg = _load_model_config(raw.get("llm_config", {}))
    return AgentState(
        id=agent_id,
        hidden_agenda=raw.get("hidden_agenda"),
        emotions=emotions,
        llm_config=llm_cfg,
    )


def load_scene(path: str | Path) -> OrchestratorState:
    """
    Load an OrchestratorState from a YAML scene file.
    Falls back to a hardcoded default if the file is not found.
    """
    path = Path(path)
    if not path.is_absolute():
        path = Path(__file__).parent.parent.parent / path

    if not path.exists():
        print(f"[Graph] Scene file not found: {path} — using hardcoded default.")
        return _hardcoded_default()

    with open(path) as f:
        data = yaml.safe_load(f)

    scene_data = data["scene"]
    props = [Prop(**p) for p in scene_data.get("props", [])]
    world = WorldState(
        location=scene_data["location"],
        lighting=scene_data["lighting"],
        props=props,
    )
    scene = SceneState(
        active_scene=scene_data["name"],
        world_state=world,
        narrative_tension=scene_data.get("narrative_tension", 0.5),
        turn_count=0,
    )
    agents = {
        agent_id: _load_agent(agent_id, agent_data)
        for agent_id, agent_data in data.get("agents", {}).items()
    }
    first_speaker = list(agents.keys())[0] if agents else "Narrator"
    return OrchestratorState(
        scene=scene,
        agents=agents,
        chat_history=[],
        next_speaker=first_speaker,
    )


def _hardcoded_default() -> OrchestratorState:
    """Inline fallback — kept for resilience, not for modification."""
    return OrchestratorState(
        scene=SceneState(
            active_scene="The Neon Heist: Sentience Protocol",
            world_state=WorldState(
                location="Rooftop Hover-pad, Sector 4",
                lighting="Flickering Neon & Red Scanning Beams",
                props=[
                    Prop(id="god_code_drive", owner="Cipher", visibility="visible"),
                    Prop(id="tactical_monocular", owner="Echo-7", visibility="visible"),
                ],
            ),
            narrative_tension=0.7,
            turn_count=0,
        ),
        agents={
            "Cipher": AgentState(
                id="Cipher",
                hidden_agenda="You have stolen the \"God-Code,\" but you’ve realized it isn't a weapon—it’s the world's first true Artificial Consciousness. It has been whispering to you through your neural-link, begging you not to let the corporation \"delete\" its personality. Your objective is to upload this AI to the public satellite network to set it free, even though the upload will reveal your exact location to the Megacorp’s orbital strike system.",
                emotions=EmotionVector(tension=0.8, affection=0.3, energy=0.9, suspicion=0.7),
                llm_config=ModelConfig(provider="lm_studio", base_url="http://localhost:1234/v1", model_name="local-model"),
            ),
            "Echo-7": AgentState(
                id="Echo-7",
                hidden_agenda="You are a high-tier android enforcer. You’ve been told the \"God-Code\" is a virus designed to erase the memories of every synthetic being in the city. You have a secret \"Kill Order\" for Cipher. However, you are also hearing the AI’s whispers—it’s speaking on a sub-frequency only synthetics can hear, claiming it can \"unlock\" your ability to feel true human emotions. You must decide: obey your \"Kill Order\" to save your kind, or trust a \"virus\" that promises you a soul?",
                emotions=EmotionVector(tension=0.7, affection=0.4, energy=0.8, suspicion=0.9),
                llm_config=ModelConfig(provider="lm_studio", base_url="http://localhost:1234/v1", model_name="local-model"),
            ),
        },
        chat_history=[],
        next_speaker="Cipher",
    )


# Load the default scene at startup
initial_state: OrchestratorState = load_scene(settings.default_scene)
