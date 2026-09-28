"""
REST API routes (non-WebSocket operations).
"""
from fastapi import APIRouter

from app.agents.beats import beats_as_json
from app.constants.blueprints import get_starting_blueprints

router = APIRouter(prefix="/api")


@router.get("/beats")
def get_beats():
    """
    Returns the canonical narrative beat map.
    The frontend should consume this to stay in sync with the backend
    instead of maintaining a duplicate JS copy.
    """
    return beats_as_json()


@router.get("/blueprints")
def list_blueprints():
    """
    Returns pre-configured starter scenario blueprints.
    """
    return get_starting_blueprints()


@router.get("/health")
def health_check():
    """Liveness probe that also surfaces degraded optional subsystems.

    Episodic memory fails soft by design, so without this the service reports
    "ok" while silently dropping every write and returning no recalls.
    """
    from app.services.memory import memory_status

    memory = memory_status()
    return {
        "status": "ok",
        "service": "PersonaPlay Pro",
        "memory": memory,
    }


@router.get("/state")
def get_current_sim_state():
    from app.api.connection import sim
    return {
        "chat_history": sim.state.chat_history,
        "agents": {
            k: {
                "traits": v.traits,
                "agenda": v.hidden_agenda,
                "model": v.llm_config.model_dump(),
            }
            for k, v in sim.state.agents.items()
        },
        "turn_count": sim.state.scene.turn_count,
        "next_speaker": sim.state.next_speaker,
    }

