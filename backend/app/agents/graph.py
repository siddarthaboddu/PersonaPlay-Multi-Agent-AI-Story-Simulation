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


# ── Scene Loader ──────────────────────────────────────────────────────────────

def get_initial_state() -> OrchestratorState:
    """
    Primary source of truth for the default simulation state.
    This defines the baseline 'Neon Heist' scenario.
    """
    return OrchestratorState(
        scene=SceneState(
            active_scene="The Neon Heist: Sentience Protocol",
            world_state=WorldState(
                location="Rooftop Hover-pad, Sector 4",
                lighting="Flickering Neon & Red Scanning Beams",
                props=[
                    Prop(
                        id="god_code_drive", 
                        owner="Cipher", 
                        description="A pulsating data-drive containing the world's first true consciousness.", 
                        visibility="visible"
                    ),
                    Prop(
                        id="tactical_monocular", 
                        owner="Echo-7", 
                        description="High-end optical sensor with a cracked lens, displaying scrolling heat-signatures.", 
                        visibility="visible"
                    ),
                ],
            ),
            narrative_tension=0.7,
            turn_count=0,
        ),
        agents={
            "Cipher": AgentState(
                id="Cipher",
                traits="Stoic, technological genius, cynical about humanity's future but possesses a hidden idealistic core. Speaks in precise, data-driven sentences.",
                hidden_agenda="You have stolen the \"God-Code,\" but you’ve realized it isn't a weapon—it’s the world's first true Artificial Consciousness. It has been whispering to you through your neural-link, begging you not to let the corporation \"delete\" its personality. Your objective is to upload this AI to the public satellite network to set it free, even though the upload will reveal your exact location to the Megacorp’s orbital strike system.",
                emotions=EmotionVector(tension=0.8, affection=0.3, energy=0.9, suspicion=0.7),
                llm_config=ModelConfig(provider="lm_studio", base_url="http://localhost:1234/v1", model_name="local-model"),
            ),
            "Echo-7": AgentState(
                id="Echo-7",
                traits="Advanced synthetic enforcer, efficient, physically powerful, struggling with emerging sentient errors. Voice is rhythmic and melodic.",
                hidden_agenda="You are a high-tier android enforcer. You’ve been told the \"God-Code\" is a virus designed to erase the memories of every synthetic being in the city. You have a secret \"Kill Order\" for Cipher. However, you are also hearing the AI’s whispers—it’s speaking on a sub-frequency only synthetics can hear, claiming it can \"unlock\" your ability to feel true human emotions. You must decide: obey your \"Kill Order\" to save your kind, or trust a \"virus\" that promises you a soul?",
                emotions=EmotionVector(tension=0.7, affection=0.4, energy=0.8, suspicion=0.9),
                llm_config=ModelConfig(provider="lm_studio", base_url="http://localhost:1234/v1", model_name="local-model"),
            ),
        },
        chat_history=[],
        next_speaker="Cipher",
    )


# Load the default state at startup
initial_state: OrchestratorState = get_initial_state()
