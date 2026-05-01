from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import json
import asyncio
from agent import initial_state

app = FastAPI(title="PersonaPlay Pro Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.state = initial_state

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial connection acknowledgment
        await websocket.send_json({"type": "state_update", "status": "connected"})
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            if payload.get("type") == "start_scene":
                # Use model_copy(deep=True) to ensure we have a fresh state for every restart
                manager.state = initial_state.model_copy(deep=True)
                manager.state.next_speaker = list(manager.state.agents.keys())[0] if manager.state.agents else "Narrator"
                await manager.broadcast({"type": "action", "content": f"[SCENE START]: {manager.state.scene.active_scene}"})
                await manager.broadcast({"type": "action", "content": "[SYSTEM]: Stage is set. Click the 'Next Turn' button to trigger the first actor!"})
                await manager.broadcast({"type": "world_update", "world": manager.state.scene.world_state.model_dump()})
            
            elif payload.get("type") == "get_state":
                await websocket.send_json({"type": "world_update", "world": manager.state.scene.world_state.model_dump()})
                
            elif payload.get("type") == "change_scene":
                new_location = payload.get("location")
                new_scene = payload.get("scene_name")
                if new_location: manager.state.scene.world_state.location = new_location
                if new_scene: manager.state.scene.active_scene = new_scene
                await manager.broadcast({"type": "action", "content": f"[SCENE CHANGE]: Moved to {manager.state.scene.world_state.location}."})
                await manager.broadcast({"type": "world_update", "world": manager.state.scene.world_state.model_dump()})
            
            elif payload.get("type") == "stop_scene":
                await manager.broadcast({"type": "action", "content": "[SYSTEM]: 🛑 Simulation forcibly stopped."})
            
            elif payload.get("type") == "configure_scene":
                try:
                    from state import AgentState, ModelConfig, EmotionVector
                    config_data = payload.get("agents", [])
                    new_agents = {}
                    for char in config_data:
                        char_id = char.get("id")
                        new_agents[char_id] = AgentState(
                            id=char_id,
                            hidden_agenda=char.get("hidden_agenda"),
                            emotions=EmotionVector(**char.get("emotions", {"tension":0.5, "affection":0.5, "energy":0.5, "suspicion":0.5})),
                            llm_config=ModelConfig(**char.get("model_config", {}))
                        )
                    manager.state.agents = new_agents
                    await manager.broadcast({"type": "action", "content": f"[SYSTEM]: Roster updated with {len(new_agents)} actors."})
                except Exception as e:
                    print(f"Error configuring scene: {e}")
                    await manager.broadcast({"type": "action", "content": f"[ERROR]: Configuration failed: {str(e)}"})
            
            elif payload.get("type") == "check_model":
                try:
                    from state import ModelConfig
                    from agent import get_model
                    from langchain_core.messages import HumanMessage
                    config = ModelConfig(**payload.get("model_config", {}))
                    model = get_model(config)
                    # Perform a tiny check
                    await asyncio.to_thread(model.invoke, [HumanMessage(content="Is anyone there? Respond with one word.")], {"timeout": 5})
                    await manager.broadcast({"type": "check_result", "status": "ok", "agent_id": payload.get("agent_id")})
                except Exception as e:
                    await manager.broadcast({"type": "check_result", "status": "error", "message": str(e), "agent_id": payload.get("agent_id")})
            
            elif payload.get("type") == "next_turn":
                try:
                    await manager.broadcast({"type": "action", "content": "[SYSTEM]: Triggering AI turn..."})
                    from agent import graph
                    # Execute actual LangGraph turn
                    new_state = await asyncio.to_thread(graph.invoke, manager.state)
                    
                    if isinstance(new_state, dict):
                        # LangGraph returned a state dict
                        manager.state.chat_history = new_state.get('chat_history', manager.state.chat_history)
                        manager.state.next_speaker = new_state.get('next_speaker', manager.state.next_speaker)
                    else:
                        # LangGraph returned the Pydantic object
                        manager.state = new_state
                    
                    chat_hist = manager.state.chat_history
                    actual_speaker = manager.state.next_speaker
                    
                    if len(chat_hist) >= 2:
                        monologue = chat_hist[-2]
                        dialogue = chat_hist[-1]
                    else:
                        monologue = "(Thinking...)"
                        dialogue = "..."
                    
                    # 1. Stream monologue
                    await manager.broadcast({
                        "type": "monologue",
                        "agent_id": actual_speaker,
                        "content": monologue
                    })
                    
                    await asyncio.sleep(1) # visual pause
                    
                    # 2. Stream dialogue
                    await manager.broadcast({
                        "type": "dialogue",
                        "agent_id": actual_speaker,
                        "content": dialogue
                    })
                    
                    # 3. Stream tension update
                    manager.state.scene.narrative_tension = min(manager.state.scene.narrative_tension + 0.05, 1.0)
                    await manager.broadcast({
                        "type": "vitals_update",
                        "vitals": {
                            "tension": manager.state.scene.narrative_tension,
                            "energy": manager.state.agents[actual_speaker].emotions.energy if actual_speaker in manager.state.agents else 0.5
                        }
                    })
                    
                except Exception as e:
                    print(f"Error executing turn: {e}")
                    await manager.broadcast({"type": "action", "content": f"[ERROR]: AI Generation failed. Is LM Studio/OpenRouter running? {str(e)}"})

            # Handle commands from frontend (Director)
            elif payload.get("type") == "director_command":
                print(f"Received Director command: {payload.get('command')}")
                # Inject chaos into the dialogue stream
                await manager.broadcast({"type": "action", "content": f"[DIRECTOR INJECTS]: {payload.get('command')}"})
                manager.state.scene.narrative_tension = min(manager.state.scene.narrative_tension + 0.2, 1.0)
                await manager.broadcast({
                    "type": "vitals_update",
                    "vitals": {
                        "tension": manager.state.scene.narrative_tension,
                        "energy": 0.9
                    }
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/")
def read_root():
    return {"status": "PersonaPlay Pro API Running"}
