import asyncio
import websockets
import json

async def test_scene():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        # Wait for connected message
        msg = await websocket.recv()
        print("Received:", msg)

        # Configure both to use LM Studio to rule out OpenRouter errors
        config = {
            "type": "configure_scene",
            "agents": [
                {
                    "id": "Character_A",
                    "hidden_agenda": "",
                    "model_config": {"provider": "lm_studio", "base_url": "http://localhost:1234/v1", "model_name": "local-model"}
                },
                {
                    "id": "Character_B",
                    "hidden_agenda": "",
                    "model_config": {"provider": "lm_studio", "base_url": "http://localhost:1234/v1", "model_name": "local-model"}
                }
            ]
        }
        await websocket.send(json.dumps(config))
        print("Received:", await websocket.recv()) # SYSTEM roster updated

        # Start Scene
        await websocket.send(json.dumps({"type": "start_scene"}))
        print("Received:", await websocket.recv()) # SCENE START
        print("Received:", await websocket.recv()) # Stage is set
        print("Received:", await websocket.recv()) # World Update

        # Next turn
        print("Sending next_turn...")
        await websocket.send(json.dumps({"type": "next_turn"}))
        
        # Read the stream
        for _ in range(5):
            try:
                res = await asyncio.wait_for(websocket.recv(), timeout=15)
                print("Stream:", res)
            except Exception as e:
                print("Timeout waiting for response", e)
                break

if __name__ == "__main__":
    asyncio.run(test_scene())
