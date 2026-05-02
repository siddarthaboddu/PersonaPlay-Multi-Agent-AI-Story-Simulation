"""
Episodic memory service using ChromaDB + HuggingFace embeddings.

Thread-safety note: Chroma is a synchronous library. All calls are
wrapped with asyncio.to_thread() and guarded by an asyncio.Lock so
concurrent LLM coroutines (asyncio.gather in actor_node) cannot
produce write races.
"""
import asyncio
import os

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from app.config import settings

# Initialised once at module load — shared across the process
_embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
_vectorstore = Chroma(
    embedding_function=_embeddings,
    persist_directory=settings.chroma_persist_dir,
)
_lock = asyncio.Lock()


# ── Sync helpers (used internally via asyncio.to_thread) ─────────────────────

def _add(agent_id: str, memory: str) -> None:
    if not memory or not memory.strip():
        return
    _vectorstore.add_texts(texts=[memory], metadatas=[{"agent_id": agent_id}])


def _retrieve(agent_id: str, query: str, k: int = 3) -> str:
    results = _vectorstore.similarity_search(
        query, k=k, filter={"agent_id": agent_id}
    )
    if not results:
        return ""
    return "\n".join(f"- {r.page_content}" for r in results)


def _clear() -> int:
    all_ids = _vectorstore.get()["ids"]
    if all_ids:
        _vectorstore.delete(ids=all_ids)
    return len(all_ids)


# ── Async public API ──────────────────────────────────────────────────────────

async def add_memory(agent_id: str, memory: str) -> None:
    """Store an episodic memory for an agent (async, thread-safe)."""
    async with _lock:
        await asyncio.to_thread(_add, agent_id, memory)


async def retrieve_memories(agent_id: str, query: str, k: int = 3) -> str:
    """Retrieve relevant past memories (async, thread-safe)."""
    try:
        async with _lock:
            return await asyncio.to_thread(_retrieve, agent_id, query, k)
    except Exception as e:
        print(f"[Memory] Retrieval error (non-fatal): {e}")
        return ""


async def clear_memories() -> None:
    """Clear all episodic memories. Called on scene restart."""
    try:
        async with _lock:
            count = await asyncio.to_thread(_clear)
        print(f"[Memory] Cleared {count} episodic memories.")
    except Exception as e:
        print(f"[Memory] Clear error (non-fatal): {e}")
