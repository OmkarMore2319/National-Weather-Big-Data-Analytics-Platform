import logging
from typing import List, Any
from fastapi import WebSocket

logger = logging.getLogger("websocket_manager")


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts event updates."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client removed. Total active: {len(self.active_connections)}")

    async def broadcast_event(self, event_data: Any):
        """
        Broadcasts event dictionary as JSON to all active connections.
        Safely purges dead or uncleanly disconnected clients without crashing.
        """
        if not self.active_connections:
            return

        dead_connections: List[WebSocket] = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(event_data)
            except Exception as e:
                logger.warning(f"Failed to send to client ({e}), dropping connection.")
                dead_connections.append(connection)

        for dead_ws in dead_connections:
            self.disconnect(dead_ws)


ws_manager = ConnectionManager()
