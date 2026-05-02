# 🎭 PersonaPlay: Multi-Agent AI Story Simulation

PersonaPlay is an advanced, multi-agent AI story simulation engine. It allows users to act as a "Director" overseeing a live scene where multiple AI actors driven by Large Language Models interact, think, and evolve in real time. 

Built with **FastAPI**, **LangGraph**, and **React**, it features a robust concurrent WebSocket architecture, enabling instant director interventions (like injecting chaos or teleporting characters) without disrupting ongoing AI thought processes.

![PersonaPlay UI](https://via.placeholder.com/1000x500.png?text=PersonaPlay+Pro+-+Multi-Agent+Theater+Engine)

## 🌟 Key Features

*   **🧠 Parallel Multi-Agent Intelligence**: Powered by LangGraph, all agents compute their internal monologues simultaneously before speaking, providing deep, subtext-driven dialogue.
*   **🎬 Live Director Interventions**: Inject chaos, alter narrative tension, teleport the scene, or hand out props in real-time. State changes merge seamlessly with active LLM generations.
*   **📡 Concurrent WebSocket Engine**: A highly optimized WebSocket dispatcher featuring `asyncio.Lock` state serialization and robust connection cleanup, preventing ghost connections and race conditions.
*   **🎭 Emotional Vitals**: Real-time tracking of agent tension, energy, affection, and suspicion.
*   **🔊 Text-to-Speech (TTS)**: Built-in Web Speech API integration voices the generated dialogue live.
*   **💾 Episodic Memory**: AI actors maintain long-term context using vector-like memory retrieval to ensure continuity across long scenes.
*   **📷 Generative Scene Imaging**: Optional integration for dynamically rendering scene backgrounds.

---

## 🏗 Architecture Overview

The system is separated into a decoupled frontend and backend, communicating exclusively over asynchronous WebSockets.

### Backend (`/backend`)
*   **Framework**: FastAPI, Uvicorn, LangChain, LangGraph.
*   **State Management**: `app.models.state.OrchestratorState` acts as the single source of truth for the entire theater.
*   **Concurrency**: Handled via `SimulationState.lock` to ensure that Director actions (which mutate state instantly) gracefully merge with LangGraph iterations via an **additive state merge strategy**.
*   **Message Validation**: Pydantic `RootModel` ensures strict type-checking on all inbound and outbound payload formats.

### Frontend (`/frontend`)
*   **Framework**: React (Vite) + Vanilla CSS.
*   **Layout**: A complex, three-panel dashboard:
    *   **Theater Panel**: Visualizes the world state, current actors, and the dialogue feed.
    *   **Director Panel**: Allows for manual scene manipulation, prop management, and narrative tension sliding.
    *   **Backstage Panel**: Exposes the hidden internal monologues and emotional sliders of the actors.
*   **Hooks**: `useWebSocket` strictly manages the connection lifecycle (resilient against React StrictMode unmounts), while `useSimulation` handles global app state.

---

## 🚀 Getting Started

### Prerequisites
*   Node.js (v18+)
*   Python (3.11+)
*   An API Key for an OpenAI-compatible LLM provider (e.g., OpenRouter, OpenAI) or a local provider like LM Studio.

### 1. Backend Setup

```bash
cd backend

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (assuming you have a requirements.txt or use poetry/pip)
pip install -r requirements.txt
# Alternatively: pip install fastapi uvicorn langchain langgraph pydantic

# Start the server
uvicorn app.main:app --reload
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

### 3. Configuration & Running
1. Open the UI at `http://localhost:5173`.
2. Click the **Configure (⚙️)** button in the top right.
3. Add your actors (e.g., *Jamie* and *Alex*), setting their specific Hidden Agendas and API URLs (e.g., `https://openrouter.ai/api/v1`).
4. Click **Connect & Start** to initialize the WebSocket connection.
5. Hit **Next Turn** (or enable Auto-Play) to watch the AI actors perform!

---

## 🛠 Advanced Configuration

### Environment Variables
While most configuration happens in the UI, you can configure backend defaults by creating a `.env` in the `/backend` folder:

```env
OPENROUTER_API_KEY=your_key_here
HISTORY_WINDOW_SIZE=10
```

### Scene Configuration
Default scenes and beats can be authored in `backend/scenes/`. You can define custom locations, props, and narrative structures via YAML.

---

## 🧪 Testing

The backend comes with a comprehensive `pytest` suite covering payload validation, memory retrieval, and agent logic.

```bash
cd backend
python -m pytest
```

---

## 🤝 Contributing
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: amazing new feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License
Distributed under the MIT License. See `LICENSE` for more information.
