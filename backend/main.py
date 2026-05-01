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
        self.current_task = None
        self.state_history = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)
        for d in dead:
            self.active_connections.remove(d)

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
                # Deep-copy current agents so we don't mutate in-place references
                import copy
                from memory import clear_memories
                saved_agents = copy.deepcopy(manager.state.agents)
                
                # Wipe ChromaDB episodic memory so old scenes don't bleed in
                clear_memories()
                
                # Reset world state completely
                manager.state = initial_state.model_copy(deep=True)
                
                # Restore roster (with reset emotions) so custom config is preserved
                for agent_id, agent in saved_agents.items():
                    agent.emotions.tension = 0.5
                    agent.emotions.energy = 0.8
                    agent.emotions.affection = 0.5
                    agent.emotions.suspicion = 0.5
                    manager.state.agents[agent_id] = agent
                
                # Cancel any running task
                if manager.current_task and not manager.current_task.done():
                    manager.current_task.cancel()
                    manager.current_task = None
                    
                manager.state.next_speaker = list(manager.state.agents.keys())[0] if manager.state.agents else "Narrator"
                manager.state_history = [manager.state.model_copy(deep=True)]
                
                await manager.broadcast({"type": "history_reset", "messages": [], "monologues": []})
                await manager.broadcast({"type": "action", "content": f"[SCENE START]: {manager.state.scene.active_scene}"})
                await manager.broadcast({"type": "action", "content": "[SYSTEM]: Stage is set. Click the 'Next Turn' button to trigger the first actor!"})
                await manager.broadcast({"type": "world_update", "world": manager.state.scene.world_state.model_dump()})
                await manager.broadcast({"type": "agents_update", "agents": [v.model_dump() for v in manager.state.agents.values()]})
            
            elif payload.get("type") == "get_state":
                await websocket.send_json({"type": "world_update", "world": manager.state.scene.world_state.model_dump()})
                await websocket.send_json({"type": "agents_update", "agents": [v.model_dump() for v in manager.state.agents.values()]})
                
            elif payload.get("type") == "change_scene":
                new_location = payload.get("location")
                new_scene = payload.get("scene_name")
                if new_location: manager.state.scene.world_state.location = new_location
                if new_scene: manager.state.scene.active_scene = new_scene
                
                change_msg = f"[SCENE CHANGE]: Moved to {manager.state.scene.world_state.location}."
                manager.state.chat_history.append(change_msg)
                
                await manager.broadcast({"type": "action", "content": change_msg})
                await manager.broadcast({"type": "world_update", "world": manager.state.scene.world_state.model_dump()})
            
            elif payload.get("type") == "stop_scene":
                await manager.broadcast({"type": "action", "content": "[SYSTEM]: 🛑 Simulation forcibly stopped."})
                if manager.current_task and not manager.current_task.done():
                    manager.current_task.cancel()
                    manager.current_task = None
            
            elif payload.get("type") == "rewind_turns":
                turns = int(payload.get("turns", 1))
                # Cancel any in-flight turn first
                if manager.current_task and not manager.current_task.done():
                    manager.current_task.cancel()
                    manager.current_task = None
                    
                if len(manager.state_history) > turns:
                    manager.state_history = manager.state_history[:-turns]
                    manager.state = manager.state_history[-1].model_copy(deep=True)
                    
                    # Fix stale next_speaker: reset to first valid agent
                    agent_ids = list(manager.state.agents.keys())
                    if manager.state.next_speaker not in agent_ids and agent_ids:
                        manager.state.next_speaker = agent_ids[0]
                    
                    reconstructed_messages = [{"type": "action", "content": f"[SYSTEM]: ⏪ Rewound {turns} turns."}]
                    reconstructed_monologues = []
                    
                    for line in manager.state.chat_history:
                        if line.startswith("[") and "'s Thought]:" in line:
                            agent_id = line[1:line.find("'s")]
                            content = line.split("]:", 1)[-1].strip()
                            reconstructed_monologues.append({"type": "monologue", "agent_id": agent_id, "content": content})
                        elif line.startswith("["):
                            reconstructed_messages.append({"type": "action", "content": line})
                        else:
                            agent_id = line.split(":")[0].strip() if ":" in line else None
                            reconstructed_messages.append({"type": "dialogue", "agent_id": agent_id, "content": line})
                            
                    await manager.broadcast({"type": "history_reset", "messages": reconstructed_messages, "monologues": reconstructed_monologues})
                    await manager.broadcast({"type": "world_update", "world": manager.state.scene.world_state.model_dump()})
                    await manager.broadcast({"type": "agents_update", "agents": [v.model_dump() for v in manager.state.agents.values()]})
                else:
                    await manager.broadcast({"type": "action", "content": "[SYSTEM]: Cannot rewind that far back!"})
                    
            elif payload.get("type") == "force_give_prop":
                prop_id = payload.get("prop_id")
                new_owner = payload.get("owner")
                for p in manager.state.scene.world_state.props:
                    if p.id == prop_id:
                        p.owner = new_owner
                        break
                await manager.broadcast({"type": "action", "content": f"[DIRECTOR INJECTS]: Forced '{prop_id}' to be owned by {new_owner}."})
                await manager.broadcast({"type": "world_update", "world": manager.state.scene.world_state.model_dump()})
                if manager.state_history:
                    manager.state_history[-1] = manager.state.model_copy(deep=True)
            
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
                    await manager.broadcast({"type": "agents_update", "agents": [v.model_dump() for v in manager.state.agents.values()]})
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
                    # Use async ainvoke (not sync invoke via thread, which passes args incorrectly)
                    await model.ainvoke([HumanMessage(content="Is anyone there? Respond with one word.")])
                    await websocket.send_json({"type": "check_result", "status": "ok", "agent_id": payload.get("agent_id")})
                except Exception as e:
                    await websocket.send_json({"type": "check_result", "status": "error", "message": str(e), "agent_id": payload.get("agent_id")})
            
            elif payload.get("type") == "next_turn":
                if manager.current_task and not manager.current_task.done():
                    await manager.broadcast({"type": "action", "content": "[SYSTEM]: An AI turn is already in progress..."})
                    continue
                
                # Snapshot the current state identity before the closure captures it
                # This prevents configure/rewind from corrupting an in-flight turn
                turn_state_snapshot = manager.state
                    
                async def run_turn(snapshot=turn_state_snapshot):
                    try:
                        await manager.broadcast({"type": "action", "content": "[SYSTEM]: Triggering AI turn..."})
                        from agent import graph
                        # Execute actual LangGraph turn against the snapshot
                        new_state = await graph.ainvoke(snapshot)
                        
                        if isinstance(new_state, dict):
                            # LangGraph returned a state dict
                            manager.state.chat_history = new_state.get('chat_history', manager.state.chat_history)
                            manager.state.next_speaker = new_state.get('next_speaker', manager.state.next_speaker)
                        else:
                            # LangGraph returned the Pydantic object
                            manager.state = new_state
                        
                        chat_hist = manager.state.chat_history
                        
                        # The director runs FIRST and advances next_speaker.
                        # So next_speaker now points to the NEXT actor, not who just spoke.
                        # Derive actual speaker from the last dialogue line in history.
                        actual_speaker = None
                        for line in reversed(chat_hist):
                            if not ("'s Thought]:" in line) and ":" in line:
                                actual_speaker = line.split(":")[0].strip()
                                break
                        if not actual_speaker or actual_speaker not in manager.state.agents:
                            actual_speaker = manager.state.next_speaker
                        
                        if len(chat_hist) >= 2:
                            monologue = chat_hist[-2]
                            if monologue.startswith("[") and "]:" in monologue:
                                monologue = monologue.split("]:", 1)[-1].strip()
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
                        
                        # Also broadcast updated world state in case ECS changed props/location
                        await manager.broadcast({"type": "world_update", "world": manager.state.scene.world_state.model_dump()})
                        await manager.broadcast({"type": "agents_update", "agents": [v.model_dump() for v in manager.state.agents.values()]})
                        
                        # 3. Stream tension update
                        manager.state.scene.narrative_tension = min(manager.state.scene.narrative_tension + 0.05, 1.0)
                        await manager.broadcast({
                            "type": "vitals_update",
                            "vitals": {
                                "tension": manager.state.scene.narrative_tension,
                                "energy": manager.state.agents[actual_speaker].emotions.energy if actual_speaker in manager.state.agents else 0.5
                            }
                        })
                        
                        manager.state_history.append(manager.state.model_copy(deep=True))
                        if len(manager.state_history) > 50:
                            manager.state_history.pop(0)
                        
                    except asyncio.CancelledError:
                        print("Turn was cancelled by user.")
                    except Exception as e:
                        print(f"Error executing turn: {e}")
                        await manager.broadcast({"type": "action", "content": f"[ERROR]: AI Generation failed. Is LM Studio/OpenRouter running? {str(e)}"})
                
                manager.current_task = asyncio.create_task(run_turn())

            # Handle commands from frontend (Director)
            elif payload.get("type") == "director_command":
                command = payload.get("command", "")
                print(f"Received Director command: {command}")
                
                if command.lower().startswith("generate image"):
                    import urllib.parse
                    import random
                    ws = manager.state.scene.world_state
                    props_str = ", ".join([p.id.replace('_', ' ') for p in ws.props if p.visibility == "visible"])
                    # Use Pollinations AI for free, open-source friendly, keyless image generation
                    prompt = f"Cinematic movie still, {ws.lighting} lighting, {ws.location}. Visible props: {props_str}. Dramatic, 8k resolution, highly detailed."
                    encoded_prompt = urllib.parse.quote(prompt)
                    seed = random.randint(1, 100000)
                    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=400&nologo=true&seed={seed}"
                    
                    await manager.broadcast({"type": "action", "content": f"[DIRECTOR INJECTS]: Generating scene image..."})
                    await manager.broadcast({"type": "image_update", "url": image_url, "prompt": prompt})
                else:
                    # Inject chaos into the dialogue stream
                    chaos_msg = f"[DIRECTOR INJECTS]: {command}"
                    manager.state.chat_history.append(chaos_msg)
                    
                    await manager.broadcast({"type": "action", "content": chaos_msg})
                    manager.state.scene.narrative_tension = min(manager.state.scene.narrative_tension + 0.2, 1.0)
                    await manager.broadcast({
                        "type": "vitals_update",
                        "vitals": {
                            "tension": manager.state.scene.narrative_tension,
                            "energy": 0.9
                        }
                    })
                    if manager.state_history:
                        manager.state_history[-1] = manager.state.model_copy(deep=True)
                        
            elif payload.get("type") == "force_emotion":
                agent_id = payload.get("agent_id")
                emotion = payload.get("emotion")
                value = payload.get("value")
                if agent_id in manager.state.agents:
                    setattr(manager.state.agents[agent_id].emotions, emotion, value)
                    await manager.broadcast({"type": "agents_update", "agents": [v.model_dump() for v in manager.state.agents.values()]})
                    
            elif payload.get("type") == "force_scene_tension":
                manager.state.scene.narrative_tension = payload.get("value")
                await manager.broadcast({
                    "type": "vitals_update",
                    "vitals": {
                        "tension": manager.state.scene.narrative_tension,
                        "energy": 0.5
                    }
                })
                
            elif payload.get("type") == "export_script":
                try:
                    script_content = f"Title: {manager.state.scene.active_scene}\n\n"
                    for line in manager.state.chat_history:
                        # Skip internal thoughts only, keep dialogue and director events
                        if "'s Thought]:" in line:
                            continue
                        script_content += f"{line}\n\n"
                    with open("exported_script.txt", "w") as f:
                        f.write(script_content)
                    await manager.broadcast({"type": "action", "content": "[SYSTEM]: Script exported successfully to backend/exported_script.txt"})
                except Exception as e:
                    await manager.broadcast({"type": "action", "content": f"[ERROR]: Failed to export script: {e}"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/")
def read_root():
    return {"status": "PersonaPlay Pro API Running"}
