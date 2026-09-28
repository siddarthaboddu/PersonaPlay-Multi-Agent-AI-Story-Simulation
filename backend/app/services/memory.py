import asyncio
import threading

from app.config import settings

_embeddings = None
_vectorstore = None
_lock = asyncio.Lock()

# Set once the vector store has been successfully constructed, or once we have
# determined it cannot be. Without this, `_get_vectorstore` re-attempts the
# (slow, always-failing) import on EVERY memory call — and the graceful
# degradation turns into a hot-path cost on every single turn.
_init_lock = threading.Lock()
_unavailable_reason: str | None = None


def memory_status() -> dict:
    """Report whether the episodic memory engine is actually usable.

    The engine degrades silently: if the embedding backend cannot be imported,
    every write is dropped and every read returns "". Callers (and /api/health)
    need a way to tell a user that the feature is off rather than assuming the
    characters simply have nothing to remember.
    """
    if _vectorstore is not None:
        return {"available": True, "reason": None}
    return {
        "available": False,
        "reason": _unavailable_reason or "not initialised yet",
    }


def _get_vectorstore():
    global _embeddings, _vectorstore, _unavailable_reason

    if _vectorstore is not None:
        return _vectorstore
    if _unavailable_reason is not None:
        # Already failed once; do not pay the import cost again.
        return None

    with _init_lock:
        if _vectorstore is not None:
            return _vectorstore
        if _unavailable_reason is not None:
            return None
        try:
            from langchain_chroma import Chroma
            from langchain_huggingface import HuggingFaceEmbeddings

            _embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            _vectorstore = Chroma(
                embedding_function=_embeddings,
                persist_directory=settings.chroma_persist_dir,
            )
        except Exception as e:
            _unavailable_reason = str(e)
            print(
                f"[Memory] Episodic memory DISABLED ({e}). "
                "Install the embedding backend to enable long-term recall: "
                "pip install sentence-transformers"
            )
            return None
    return _vectorstore


# ── Sync helpers (used internally via asyncio.to_thread) ─────────────────────

def _add(agent_id: str, memory: str, memory_type: str = "observation", turn: int = 0) -> None:
    if not memory or not memory.strip():
        return
    vs = _get_vectorstore()
    if vs is None:
        return
    vs.add_texts(
        texts=[memory.strip()],
        metadatas=[{"agent_id": agent_id, "type": memory_type, "turn": turn}],
    )


def _retrieve(agent_id: str, query: str, k_insights: int = 2, k_observations: int = 2) -> str:
    vs = _get_vectorstore()
    if vs is None:
        return ""
    total_k = max(6, (k_insights + k_observations) * 2)
    results = vs.similarity_search(
        query, k=total_k, filter={"agent_id": agent_id}
    )
    if not results:
        return ""

    insights = []
    observations = []
    for r in results:
        mtype = r.metadata.get("type", "observation")
        if mtype == "reflection":
            if len(insights) < k_insights and r.page_content not in insights:
                insights.append(r.page_content)
        else:
            if len(observations) < k_observations and r.page_content not in observations:
                observations.append(r.page_content)

    sections = []
    if insights:
        sections.append("YOUR SYNTHESIZED INSIGHTS & BELIEFS:\n" + "\n".join(f"- {i}" for i in insights))
    if observations:
        sections.append("PAST MOMENTS RECALLED:\n" + "\n".join(f"- {o}" for o in observations))

    return "\n\n".join(sections) if sections else "\n".join(f"- {r.page_content}" for r in results[:3])


def _clear() -> int:
    vs = _get_vectorstore()
    if vs is None:
        return 0
    all_ids = vs.get()["ids"]
    if all_ids:
        vs.delete(ids=all_ids)
    return len(all_ids)


# ── Async public API ──────────────────────────────────────────────────────────

async def add_memory(agent_id: str, memory: str, memory_type: str = "observation", turn: int = 0) -> None:
    """Store an episodic observation or memory for an agent (async, thread-safe)."""
    async with _lock:
        await asyncio.to_thread(_add, agent_id, memory, memory_type, turn)


async def add_reflection(agent_id: str, reflection: str, turn: int = 0) -> None:
    """Store a high-level synthesized insight/reflection (async, thread-safe)."""
    async with _lock:
        await asyncio.to_thread(_add, agent_id, reflection, "reflection", turn)


async def retrieve_memories(agent_id: str, query: str, k_insights: int = 2, k_observations: int = 2) -> str:
    """Retrieve hybrid past memories and synthesized insights (async, thread-safe)."""
    try:
        async with _lock:
            return await asyncio.to_thread(_retrieve, agent_id, query, k_insights, k_observations)
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
