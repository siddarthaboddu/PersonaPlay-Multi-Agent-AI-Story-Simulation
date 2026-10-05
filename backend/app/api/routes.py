"""
REST API routes (non-WebSocket operations).
"""
from fastapi import APIRouter

from app.constants.blueprints import get_starting_blueprints

router = APIRouter(prefix="/api")


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

