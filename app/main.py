from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from app.dependencies.index import html

app = FastAPI()


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_broadcast_message(self, message: str):
        for connections in self.active_connections:
            await connections.send_text(message)


manager = ConnectionManager()


@app.get("/")
async def homepage():
    return HTMLResponse(html)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            sender_name = data.get("name")
            message_text = data.get("message")
            broadcast = f"{sender_name} sent :{message_text}"
            await manager.send_broadcast_message(broadcast)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
        await manager.send_broadcast_message(f"Client has disconnected")
