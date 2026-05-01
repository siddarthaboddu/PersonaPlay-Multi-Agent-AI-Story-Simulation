import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Initialize local embeddings
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Setup persistent chroma
persist_dir = os.path.join(os.path.dirname(__file__), "chroma_db")
vectorstore = Chroma(embedding_function=embeddings, persist_directory=persist_dir)

def add_memory(agent_id: str, memory: str):
    """Store an episodic memory for an agent."""
    if not memory or memory.strip() == "": return
    vectorstore.add_texts(texts=[memory], metadatas=[{"agent_id": agent_id}])

def retrieve_memories(agent_id: str, query: str, k: int = 3) -> str:
    """Retrieve relevant past memories."""
    try:
        results = vectorstore.similarity_search(query, k=k, filter={"agent_id": agent_id})
        if not results:
            return ""
        return "\n".join([f"- {r.page_content}" for r in results])
    except Exception as e:
        print(f"Memory retrieval error: {e}")
        return ""
