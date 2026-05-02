"""
WebSocket connection manager and simulation state manager.

ConnectionManager — only handles WebSocket lifecycle (connect / disconnect / broadcast).
SimulationState   — owns all mutable simulation data and task management.

Keeping them separate means connection logic doesn't need to understand simulation
and vice-versa, making both independently testable.
"""
from __future__ import annotations

import asyncio
import copy
from typing import List, Optional

from fastapi import WebSocket

from app.agents.graph import initial_state
from app.config import settings
from app.models.state import OrchestratorState


class ConnectionManager:
    """Manages active WebSocket connections and broadcasting."""

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        dead: List[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)
        for d in dead:
            self.active_connections.remove(d)


class SimulationState:
    """
    Owns the mutable simulation state and the async task for in-flight turns.

    Key invariant: `state` is always a deep copy when captured for use in a
    background task — never a live reference that can be mutated mid-flight.
    """

    def __init__(self) -> None:
        self.state: OrchestratorState = initial_state.model_copy(deep=True)
        self.history: List[OrchestratorState] = []
        self.current_task: Optional[asyncio.Task] = None
        self.lock = asyncio.Lock()

    def snapshot(self) -> OrchestratorState:
        """Return a deep copy of current state (safe to pass to background tasks)."""
        return self.state.model_copy(deep=True)

    def push_history(self) -> None:
        """Save current state to rewind history, capping at configured max."""
        self.history.append(self.state.model_copy(deep=True))
        if len(self.history) > settings.state_history_max:
            self.history.pop(0)

    def update_last_history(self) -> None:
        """Overwrite the last history snapshot with the current state."""
        if self.history:
            self.history[-1] = self.state.model_copy(deep=True)

    def restore(self, turns: int) -> bool:
        """
        Rewind by `turns` steps.
        Returns True on success, False if not enough history exists.
        """
        if len(self.history) <= turns:
            return False
        self.history = self.history[:-turns]
        self.state = self.history[-1].model_copy(deep=True)

        # Ensure next_speaker is valid after rewind
        agent_ids = list(self.state.agents.keys())
        if self.state.next_speaker not in agent_ids and agent_ids:
            self.state.next_speaker = agent_ids[0]
        return True

    def reset(self, preserve_agents: bool = True) -> None:
        """
        Reset world state for a new scene.

        If preserve_agents=True, custom agent configurations (name, agenda,
        LLM config) are kept but emotions are reset to neutral defaults.
        """
        saved_agents = copy.deepcopy(self.state.agents) if preserve_agents else {}

        self.state = initial_state.model_copy(deep=True)
        self.history = []

        if preserve_agents:
            for agent_id, agent in saved_agents.items():
                agent.emotions.tension = 0.5
                agent.emotions.energy = 0.8
                agent.emotions.affection = 0.5
                agent.emotions.suspicion = 0.5
                self.state.agents[agent_id] = agent

        agent_ids = list(self.state.agents.keys())
        self.state.next_speaker = agent_ids[0] if agent_ids else "Narrator"
        self.history = [self.state.model_copy(deep=True)]

    def cancel_task(self) -> None:
        """Cancel any in-flight turn task."""
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
            self.current_task = None


# Module-level singletons — shared across all WebSocket connections
manager = ConnectionManager()
sim = SimulationState()
