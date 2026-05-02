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
            active_scene="The Secret Road Trip",
            world_state=WorldState(
                location="A Cluttered Minivan",
                lighting="Flashing Streetlights",
                props=[
                    Prop(id="mysterious_duffel_bag", owner="Alex", visibility="visible"),
                    Prop(id="half_eaten_pizza", owner="Jamie", visibility="visible"),
                ],
            ),
            narrative_tension=0.6,
            turn_count=0,
        ),
        agents={
            "Alex": AgentState(
                id="Alex",
                hidden_agenda="Wants to convince Jamie to skip college and drive to Mexico. Secretly terrified of growing up.",
                emotions=EmotionVector(tension=0.6, affection=0.8, energy=0.9, suspicion=0.2),
                llm_config=ModelConfig(provider="lm_studio", base_url="http://localhost:1234/v1", model_name="local-model"),
            ),
            "Jamie": AgentState(
                id="Jamie",
                hidden_agenda="Just realized the mysterious duffel bag in the back belongs to a dangerous cartel. Wants to get home immediately without panicking Alex.",
                emotions=EmotionVector(tension=0.9, affection=0.7, energy=0.5, suspicion=0.9),
                llm_config=ModelConfig(provider="lm_studio", base_url="http://localhost:1234/v1", model_name="local-model"),
            ),
        },
        chat_history=[],
        next_speaker="Alex",
    )


# Load the default scene at startup
initial_state: OrchestratorState = load_scene(settings.default_scene)
