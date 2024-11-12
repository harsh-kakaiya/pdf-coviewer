from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import uuid
from typing import Dict, Set, Optional

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store PDF files
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}  # room_id -> {connection_id -> websocket}
        self.current_pages: Dict[str, int] = {}  # room_id -> current page
        self.room_admins: Dict[str, str] = {}  # room_id -> admin connection_id
        self.room_pdfs: Dict[str, str] = {}  # room_id -> pdf path

    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        if room_id not in self.active_connections:
            self.active_connections[room_id] = {}
            self.current_pages[room_id] = 1
        self.active_connections[room_id][connection_id] = websocket

        return connection_id

    def disconnect(self, connection_id: str, room_id: str):
        if room_id in self.active_connections and connection_id in self.active_connections[room_id]:
            del self.active_connections[room_id][connection_id]
            if connection_id == self.room_admins.get(room_id):
                self.room_admins.pop(room_id, None)

    async def broadcast(self, message: dict, room_id: str):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id].values():
                await connection.send_json(message)

    def set_admin(self, connection_id: str, room_id: str):
        self.room_admins[room_id] = connection_id

    def get_viewer_count(self, room_id: str) -> int:
        return len(self.active_connections.get(room_id, {}))

manager = ConnectionManager()

@app.post("/upload/{room_id}")
async def upload_pdf(room_id: str, file: UploadFile = File(...)):
    try:
        # Save the uploaded PDF
        file_path = os.path.join(UPLOAD_DIR, f"{room_id}_{file.filename}")
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Store the PDF path for the room
        manager.room_pdfs[room_id] = file_path
        
        return JSONResponse(
            content={"message": "PDF uploaded successfully"},
            status_code=200
        )
    except Exception as e:
        return JSONResponse(
            content={"message": f"Error uploading PDF: {str(e)}"},
            status_code=500
        )

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    connection_id = await manager.connect(websocket, room_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "admin_connect":
                manager.set_admin(connection_id, room_id)
                await websocket.send_json({
                    "type": "admin_status",
                    "is_admin": True,
                    "current_page": manager.current_pages.get(room_id, 1)
                })
            
            elif data.get("type") == "page_change" and connection_id == manager.room_admins.get(room_id):
                new_page = data.get("page")
                manager.current_pages[room_id] = new_page
                await manager.broadcast(
                    {"type": "page_update", "page": new_page},
                    room_id
                )
            
            # Send viewer count update
            await manager.broadcast(
                {
                    "type": "viewer_count",
                    "count": manager.get_viewer_count(room_id)
                },
                room_id
            )

    except WebSocketDisconnect:
        manager.disconnect(connection_id, room_id)
        await manager.broadcast(
            {
                "type": "viewer_count",
                "count": manager.get_viewer_count(room_id)
            },
            room_id
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)