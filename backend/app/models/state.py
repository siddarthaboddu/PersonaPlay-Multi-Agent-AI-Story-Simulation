"""
Pydantic state models for PersonaPlay Pro.
Migrated from the top-level state.py — import from here going forward.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class Prop(BaseModel):
    id: str
    owner: str = "world"  # character id or "world"
    description: str = ""
    visibility: Literal["visible", "hidden"] = "visible"


class WorldState(BaseModel):
    location: str
    lighting: str
    props: List[Prop]


class EmotionVector(BaseModel):
    tension: float    # 0.0–1.0
    affection: float  # 0.0–1.0
    energy: float     # 0.0–1.0
    suspicion: float  # 0.0–1.0


class RelationshipVector(BaseModel):
    trust: float = 0.5       # 0.0 (betrayal / paranoid) to 1.0 (unwavering faith)
    affinity: float = 0.5    # 0.0 (hatred / bitter rivalry) to 1.0 (devoted camaraderie)
    fear: float = 0.0        # 0.0 (fearless / indifferent) to 1.0 (terrified / intimidated)
    dominance: float = 0.5   # 0.0 (deferential / submissive) to 1.0 (commanding / assertive)


class SceneState(BaseModel):
    active_scene: str
    world_state: WorldState
    narrative_tension: float
    turn_count: int


class ModelConfig(BaseModel):
    provider: Literal["lm_studio", "openrouter", "google"] = "lm_studio"
    base_url: str = "http://localhost:1234/v1"
    model_name: str = "local-model"
    api_key: Optional[str] = None


class AgentState(BaseModel):
    id: str
    emotions: EmotionVector
    hidden_agenda: Optional[str] = None
    traits: Optional[str] = None  # New field for character personality/description
    relationships: dict[str, RelationshipVector] = Field(default_factory=dict)
    llm_config: ModelConfig = ModelConfig()


class OrchestratorState(BaseModel):
    """The top-level state object passed through the LangGraph."""
    scene: SceneState
    agents: dict[str, AgentState]
    chat_history: List[str]
    next_speaker: str
