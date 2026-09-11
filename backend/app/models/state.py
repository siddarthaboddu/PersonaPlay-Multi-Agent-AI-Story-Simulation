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
    phases_enabled: bool = False


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
    pending_whisper: Optional[str] = None  # Secret in-ear coaching from the Director
    known_secrets: List[str] = Field(default_factory=list)  # Secrets, rumors, and director whispers remembered
    last_emote: Optional[str] = None  # Last micro-gesture or visual emote displayed
    relationships: dict[str, RelationshipVector] = Field(default_factory=dict)
    # Human-readable social facts complement numeric affinity and define roles,
    # expectations, and boundaries that scores cannot express by themselves.
    # cannot express roles, boundaries, or social expectations by itself.
    relationship_context: dict[str, str] = Field(default_factory=dict)
    llm_config: ModelConfig = ModelConfig()


class OrchestratorState(BaseModel):
    """The top-level state object passed through the LangGraph."""
    scene: SceneState
    agents: dict[str, AgentState]
    chat_history: List[str]
    next_speaker: str
    # Set only for a user-authored character line. The following AI turn uses
    # this as a hard conversational anchor, then turn.py clears it from live state.
    manual_reply_speaker: Optional[str] = None
    manual_reply_content: Optional[str] = None
