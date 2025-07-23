from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json
import logging
from typing import List

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.active_connections.append(websocket)
        logger.info(f"[WebSocket] Client connected. Total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self.lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"[WebSocket] Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        data = json.dumps(message)
        logger.info(f"[WebSocket] Broadcasting message type '{message.get('type', 'unknown')}' to {len(self.active_connections)} clients")
        async with self.lock:
            for connection in self.active_connections[:]:
                try:
                    await connection.send_text(data)
                    logger.debug(f"[WebSocket] Successfully sent message to client")
                except Exception as e:
                    logger.warning(f"[WebSocket] Error sending to client: {e}")
                    self.active_connections.remove(connection)

manager = ConnectionManager() 