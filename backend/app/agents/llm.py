"""
LLM factory and history compression utilities.

get_model() is the single place where LangChain model objects are created.
All sampling parameters live here — never scattered across node functions.
"""
from __future__ import annotations

import hashlib

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.config import settings
from app.models.state import ModelConfig


def get_model(config: ModelConfig, creative: bool = False, focused_reply: bool = False):
    """
    Build a LangChain chat model from a ModelConfig.

    creative=True raises temperature and adds presence/frequency penalties
    to produce diverse, non-repetitive actor output.
    creative=False uses low temperature for structured director tasks.
    """
    api_key = config.api_key
    if not api_key or str(api_key).strip() == "":
        if config.provider == "openrouter":
            api_key = settings.openrouter_api_key or "sk-dummy-key-required"
        elif config.provider == "google":
            api_key = settings.google_api_key or "sk-dummy-key-required"
        else:
            api_key = "lm-studio"

    if config.provider == "google":
        return ChatGoogleGenerativeAI(
            model=config.model_name,
            google_api_key=api_key,
            max_retries=0,
            timeout=45.0,
            temperature=0.65 if focused_reply else (0.85 if creative else 0.4),
        )

    base_url = config.base_url
    if config.provider == "openrouter" and (not base_url or "localhost" in base_url):
        base_url = "https://openrouter.ai/api/v1"
    elif config.provider == "lm_studio" and not base_url:
        base_url = settings.lm_studio_base_url or "http://localhost:1234/v1"

    kwargs: dict = dict(
        base_url=base_url,
        api_key=api_key,
        model=config.model_name,
        max_retries=0,
        timeout=45.0,
    )
    if creative:
        # Manual character dialogue is a reply turn, not an invitation to invent
        # a fresh topic. Lower sampling and remove novelty penalties accordingly.
        if focused_reply:
            kwargs["temperature"] = 0.65
        else:
            kwargs["temperature"] = 0.85
            kwargs["presence_penalty"] = 0.7
            kwargs["frequency_penalty"] = 0.5
    else:
        kwargs["temperature"] = 0.3

    return ChatOpenAI(**kwargs)


_summary_cache: dict = {
    "old_lines_count": 0,
    "summary": "",
    "prefix_hash": "",
}


def reset_summary_cache() -> None:
    """Clear cached history summary upon scene restart or rewind."""
    global _summary_cache
    _summary_cache = {
        "old_lines_count": 0,
        "summary": "",
        "prefix_hash": "",
    }


async def compress_history(history: list[str], model) -> str:
    """
    Compress old chat history into a compact narrative summary.

    Only the last `settings.recent_raw_turns` dialogue lines are kept verbatim;
    everything older is distilled into a 2-sentence "story so far" block.
    This prevents context poisoning from the LLM seeing its own prior outputs
    as examples to copy.
    """
    recent_raw = settings.recent_raw_turns
    dialogue_lines = [line for line in history if "'s Thought]:" not in line]

    if len(dialogue_lines) <= recent_raw:
        return "\n".join(dialogue_lines[-12:])

    old_lines = dialogue_lines[:-recent_raw]
    recent_lines = dialogue_lines[-recent_raw * 2:]
    old_text = "\n".join(old_lines)

    # Check if we can reuse the cached summary (refresh every 6 turns to avoid burning an LLM call per turn)
    cached_summary = _summary_cache.get("summary", "")
    cached_count = _summary_cache.get("old_lines_count", 0)
    current_prefix = "\n".join(old_lines[:cached_count])
    current_prefix_hash = hashlib.sha256(current_prefix.encode()).hexdigest()

    if (
        cached_summary
        and cached_count <= len(old_lines)
        and current_prefix_hash == _summary_cache.get("prefix_hash")
        and (len(old_lines) - cached_count < 6)
    ):
        compressed = f"[STORY SO FAR — {len(old_lines)} earlier lines compressed]: {cached_summary}"
    else:
        try:
            summary_prompt = (
                f"Summarize this conversation in exactly 2 sentences. "
                f"Focus on: what was revealed, what changed, and where things stand now.\n\n{old_text}"
            )
            res = await model.ainvoke([HumanMessage(content=summary_prompt)])
            summary = res.content.strip()
            _summary_cache["old_lines_count"] = len(old_lines)
            _summary_cache["summary"] = summary
            _summary_cache["prefix_hash"] = hashlib.sha256(old_text.encode()).hexdigest()
            compressed = f"[STORY SO FAR — {len(old_lines)} earlier lines compressed]: {summary}"
        except Exception as e:
            print(f"[LLM] History compression failed (non-fatal): {e}")
            compressed = f"[STORY SO FAR]: {len(old_lines)} earlier exchanges occurred."

    return f"{compressed}\n\n[RECENT EXCHANGES]:\n" + "\n".join(recent_lines)
