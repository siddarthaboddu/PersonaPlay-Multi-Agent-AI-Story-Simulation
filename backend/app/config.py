"""
Central application settings.
All environment variables are read here — nowhere else in the codebase
should call os.environ.get() or os.getenv() directly.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    # LLM provider keys
    openrouter_api_key: str = ""
    google_api_key: str = ""

    # LM Studio defaults
    lm_studio_base_url: str = "http://localhost:1234/v1"

    # ChromaDB
    chroma_persist_dir: str = os.path.join(os.path.dirname(__file__), "..", "chroma_db")

    # Scene / history tuning
    history_window_size: int = 80          # max raw lines kept in chat_history
    recent_raw_turns: int = 6              # verbatim turns kept by compress_history
    state_history_max: int = 50            # max rewind snapshots held in memory

    # Auto-play
    auto_turn_delay_ms: int = 3200


    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
