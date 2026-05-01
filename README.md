# PersonaPlay Pro

**PersonaPlay Pro** is a high-fidelity, multi-agent simulation engine designed for autonomous narrative generation, improv theater, and interactive skit production. It treats Large Language Models (LLMs) as distinct, stateful actors operating within a deterministic world environment managed by a centralized "Director" agent.

---

## 🏛 Architecture

The system utilizes a **Stateful Graph Orchestration** pattern (via LangGraph) and is segmented into three logical planes:

1. **The Actor Plane (Participants)**
   * Each character is an isolated agent instance.
   * Uses **Dual-Stream Prompting**: Stream A (Internal Monologue) and Stream B (Public Dialogue/Action).
   * Backed by a Short-Term Sliding Window Memory and a Long-Term Vector Episodic Memory (ChromaDB).

2. **The Director Plane (Orchestrator)**
   * A high-reasoning "Super-Agent" managing turn-taking and speaker selection.
   * Monitors global tension and injects stochastic "Narrative Bombs."
   * Arbitrates conflict (e.g., two agents wanting the same prop).

3. **The World Plane (Deterministic State)**
   * A JSON-based state machine acting as the absolute source of truth.
   * Tracks **Props** (who holds what), **Locations**, and **Environment** variables (lighting, etc.).

### Technology Stack
*   **Backend:** Python 3.13, FastAPI (for native WebSockets), LangGraph, LangChain, ChromaDB.
*   **Frontend:** React (Vite) with Vanilla CSS (Glassmorphic, Dark-Mode aesthetics).
*   **LLMs:** Supports Local Models (via LM Studio) OR Cloud Models (via OpenRouter API).

---

## 📂 Project Structure

```text
PersonaPlay/
├── backend/                  # Python/FastAPI Backend
│   ├── main.py               # FastAPI entry point & WebSocket Server
│   ├── agent.py              # LangGraph Orchestrator (Director & Actors)
│   ├── state.py              # Pydantic Data Models (EmotionVector, WorldState)
│   └── venv/                 # Python Virtual Environment
├── frontend/                 # React/Vite Frontend
│   ├── src/                  # React Components (Theater View, Backstage, Controller)
│   └── package.json          # Node dependencies
├── design doc/               # Original PRDs and Concepts
└── README.md                 # This file
```

---

## 🚀 Setup & Execution Steps

### Prerequisites
*   Python 3.13 and `python3.13-venv` package.
*   Node.js (v18+) and npm.
*   LM Studio running a local model on port 1234 (`http://localhost:1234/v1`).

### 1. Backend Setup
1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```
3. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```
   *The WebSocket server will start on `ws://localhost:8000/ws`.*

### 2. Frontend Setup
1. Open a *new* terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Start the Vite development server:
   ```bash
   npm run dev
   ```
3. Open your browser and navigate to `http://localhost:5173` to access the Director's Command Center.

---

## 🔮 Future Roadmap & Architectural Vision

### Phase 1: Core Engine & UI (Completed)
*   [x] MVP Boilerplate & Environment Setup
*   [x] React "Three-Column Dashboard" Implementation
*   [x] Real-time WebSocket Streaming & World State Sync
*   [x] Provider-Agnostic LLM Integration (LM Studio, OpenRouter, etc.)
*   [x] Browser-native Text-to-Speech (TTS) for Dynamic Dialogue
*   [x] Intelligent Director Node (Context-aware speaker selection)

### Phase 2: Open-Source Optimized Cognitive Architecture (Upcoming)
*   [ ] **Vector Episodic Memory (RAG):** Integrate an open-source vector store (ChromaDB) and standard LangChain retrieval chains to transition from a sliding-window context to semantic recall, ensuring complete compatibility with local LM Studio embeddings and models.
*   [ ] **Parallel Internal Processing:** Refactor the LangGraph orchestration to allow all actors to generate their "Internal Monologue" *asynchronously*. We will leverage native LangChain `RunnableParallel` primitives to reduce latency without relying on proprietary batching APIs.
*   [ ] **Local-Model-Friendly ECS Engine:** Upgrade the basic JSON state into a rigorous Entity-Component-System. Instead of forcing proprietary Tool Calling APIs, we will use robust LangChain output parsers (like generic ReAct prompts or structured JSON extractors) so even smaller open-source models (e.g., Llama 3 8B via LM Studio) can reliably manipulate props and move locations.

### Phase 3: Observability & Export
*   [ ] **Best-in-Class Telemetry (LangSmith):** Integrate LangSmith for enterprise-grade observability. Even when using local models via LM Studio or cloud models via OpenRouter, LangSmith provides the most robust tracing for LangGraph execution paths, token latency, and deep prompt debugging.
*   [ ] **Local VLM Sensory Plane:** Enable Vision-Language Models (like LLaVA running locally on LM Studio, or Gemini 1.5 Pro via OpenRouter) to accept visual context (e.g., stage layouts) into the Director's state evaluation.
*   [ ] **Screenplay Export Pipeline:** Add automated formatting to export the finalized generative theater session into industry-standard Fountain/PDF screenplay formats.
