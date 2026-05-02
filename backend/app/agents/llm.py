"""
LLM factory and history compression utilities.

get_model() is the single place where LangChain model objects are created.
All sampling parameters live here — never scattered across node functions.
"""
from __future__ import annotations

import os
from typing import List

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.config import settings
from app.models.state import ModelConfig


def get_model(config: ModelConfig, creative: bool = False):
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
            temperature=0.85 if creative else 0.4,
        )

    kwargs: dict = dict(
        base_url=config.base_url,
        api_key=api_key,
        model=config.model_name,
        max_retries=0,
        timeout=45.0,
    )
    if creative:
        kwargs["temperature"] = 0.85
        kwargs["presence_penalty"] = 0.7
        kwargs["frequency_penalty"] = 0.5
    else:
        kwargs["temperature"] = 0.3

    return ChatOpenAI(**kwargs)


async def compress_history(history: List[str], model) -> str:
    """
    Compress old chat history into a compact narrative summary.

    Only the last `settings.recent_raw_turns` dialogue lines are kept verbatim;
    everything older is distilled into a 2-sentence "story so far" block.
    This prevents context poisoning from the LLM seeing its own prior outputs
    as examples to copy.
    """
    recent_raw = settings.recent_raw_turns
    dialogue_lines = [l for l in history if "'s Thought]:" not in l]

    if len(dialogue_lines) <= recent_raw:
        return "\n".join(history[-12:])

    old_lines = dialogue_lines[:-recent_raw]
    recent_lines = history[-recent_raw * 2:]
    old_text = "\n".join(old_lines)

    try:
        summary_prompt = (
            f"Summarize this theatrical exchange in exactly 2 sentences. "
            f"Focus on: what was revealed, what changed, and where the conflict stands now.\n\n{old_text}"
        )
        res = await model.ainvoke([HumanMessage(content=summary_prompt)])
        summary = res.content.strip()
        compressed = f"[STORY SO FAR — {len(old_lines)} earlier lines compressed]: {summary}"
    except Exception as e:
        print(f"[LLM] History compression failed (non-fatal): {e}")
        compressed = f"[STORY SO FAR]: {len(old_lines)} earlier exchanges occurred."

    return f"{compressed}\n\n[RECENT EXCHANGES]:\n" + "\n".join(recent_lines)
