from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        # Maps scan_id -> WebSocket
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, scan_id: int):
        await websocket.accept()
        self.active_connections[scan_id] = websocket
        logger.info(f"WebSocket connected for scan_id={scan_id}")

    def disconnect(self, scan_id: int):
        if scan_id in self.active_connections:
            del self.active_connections[scan_id]
            logger.info(f"WebSocket disconnected for scan_id={scan_id}")

    async def send_update(self, scan_id: int, data: dict):
        if scan_id in self.active_connections:
            websocket = self.active_connections[scan_id]
            try:
                await websocket.send_json(data)
            except Exception as e:
                logger.error(f"Failed to send WS update for scan_id={scan_id}: {e}")
                self.disconnect(scan_id)

manager = ConnectionManager()

@router.websocket("/scans/{scan_id}")
async def websocket_endpoint(websocket: WebSocket, scan_id: int):
    await manager.connect(websocket, scan_id)
    try:
        while True:
            # We just keep the connection open, waiting for backend to push updates
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(scan_id)
    except Exception as e:
        logger.error(f"WebSocket error for scan_id={scan_id}: {e}")
        manager.disconnect(scan_id)
