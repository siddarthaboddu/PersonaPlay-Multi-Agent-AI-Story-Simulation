"""
Backward-compatibility shim.
All code should import from app.services.memory going forward.
"""
from app.services.memory import (  # noqa: F401
    add_memory,
    clear_memories,
    retrieve_memories,
)
