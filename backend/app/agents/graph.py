"""
LangGraph builder and default scene loader.

The graph is compiled once at module import time and reused across all sessions.
The default state is built from the first entry in
`app.constants.blueprints.STARTING_BLUEPRINTS` — NOT from a YAML file on disk.
(YAML is still accepted as an *input* format: the frontend parses it in
ConfigModal and posts the result over the wire as `configure_scene`.)
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.actor import actor_node
from app.agents.director import director_node
from app.models.state import (
    AgentState,
    EmotionVector,
    ModelConfig,
    OrchestratorState,
    Prop,
    RelationshipVector,
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
    Defaults to the grounded, relatable 'Sunday Living Room' human scenario.
    """
    from app.constants.blueprints import STARTING_BLUEPRINTS
    bp = STARTING_BLUEPRINTS[0]

    agents = {}
    for ag in bp["agents"]:
        agents[ag["id"]] = AgentState(
            id=ag["id"],
            traits=ag["traits"],
            hidden_agenda=ag["hidden_agenda"],
            emotions=EmotionVector(**ag["emotions"]),
            relationships={
                target: RelationshipVector(**r_data)
                for target, r_data in ag.get("relationships", {}).items()
            },
            relationship_context=ag.get("relationship_context", {}),
            llm_config=ModelConfig(**ag["llm_config"]),
        )

    props = [
        Prop(
            id=p["id"],
            owner=p["owner"],
            description=p["description"],
            visibility=p.get("visibility", "visible"),
        )
        for p in bp["props"]
    ]

    first_agent = list(agents.keys())[0] if agents else "Maya"

    return OrchestratorState(
        scene=SceneState(
            active_scene=bp["scene"]["name"],
            world_state=WorldState(
                location=bp["scene"]["location"],
                lighting=bp["scene"]["lighting"],
                props=props,
            ),
            narrative_tension=0.35,
            turn_count=0,
            phases_enabled=False,  # Default to authentic direct human conversation
        ),
        agents=agents,
        chat_history=[],
        next_speaker=first_agent,
    )


# Load the default state at startup
initial_state: OrchestratorState = get_initial_state()
