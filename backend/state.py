from pydantic import BaseModel
from typing import List, Dict, Optional, Literal

class Prop(BaseModel):
    id: str
    owner: str
    visibility: Literal["visible", "hidden"]

class WorldState(BaseModel):
    location: str
    lighting: str
    props: List[Prop]

class EmotionVector(BaseModel):
    tension: float  # 0.0 to 1.0
    affection: float # 0.0 to 1.0
    energy: float # 0.0 to 1.0
    suspicion: float # 0.0 to 1.0

class SceneState(BaseModel):
    active_scene: str
    world_state: WorldState
    narrative_tension: float
    turn_count: int

class ModelConfig(BaseModel):
    provider: Literal["lm_studio", "openrouter"] = "lm_studio"
    base_url: str = "http://localhost:1234/v1"
    model_name: str = "local-model"
    api_key: Optional[str] = None

class AgentState(BaseModel):
    id: str
    emotions: EmotionVector
    hidden_agenda: Optional[str] = None
    llm_config: ModelConfig = ModelConfig()
