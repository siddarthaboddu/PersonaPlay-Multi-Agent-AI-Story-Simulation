"""
Backward-compatibility shim.
All code should import from app.agents.* going forward.
"""
from app.agents.graph import graph, initial_state  # noqa: F401
from app.agents.llm import get_model              # noqa: F401
from app.agents.beats import get_beat             # noqa: F401
