"""
WebSocket manager for real-time cattle tracking updates
Handles multiple client connections and broadcasts real-time data
"""
import json
import logging
from typing import List
from fastapi import WebSocket

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates
    Handles client connections, disconnections, and message broadcasting
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_info = {}  # Store connection metadata

    async def connect(self, websocket: WebSocket):
        """
        Accept new WebSocket connection
        Args:
            websocket: WebSocket connection instance
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_info[id(websocket)] = {
            "connected_at": "2025-11-27T10:29:00Z",  # Will be dynamic
            "client_info": websocket.client
        }
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")

        # Send welcome message
        await self.send_personal_message({
            "type": "connection_established",
            "message": "Connected to Sumbawa Digital Ranch real-time updates",
            "connection_id": id(websocket)
        }, websocket)

    async def disconnect(self, websocket: WebSocket):
        """
        Remove WebSocket connection
        Args:
            websocket: WebSocket connection instance to remove
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            if id(websocket) in self.connection_info:
                del self.connection_info[id(websocket)]
            logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send message to specific client
        Args:
            message: Dictionary message to send
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            # Remove problematic connection
            await self.disconnect(websocket)

    async def broadcast(self, message: str):
        """
        Broadcast message to all connected clients
        Args:
            message: String message to broadcast
        """
        if not self.active_connections:
            return

        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)

        # Remove disconnected clients
        for connection in disconnected:
            await self.disconnect(connection)

    async def broadcast_cattle_update(self, cattle_list: List[dict]):
        """
        Broadcast cattle position updates to all clients
        Args:
            cattle_list: List of cattle with updated positions
        """
        message = {
            "type": "cattle_update",
            "data": {
                "cattle": cattle_list,
                "timestamp": "2025-11-27T10:29:00Z",  # Will be dynamic
                "count": len(cattle_list)
            }
        }
        await self.broadcast(json.dumps(message))

    async def broadcast_violation_alert(self, alert_data: dict):
        """
        Broadcast geofence violation alerts
        Args:
            alert_data: Alert information including cattle ID, location, etc.
        """
        message = {
            "type": "violation_alert",
            "data": {
                "alert": alert_data,
                "timestamp": "2025-11-27T10:29:00Z"  # Will be dynamic
            }
        }
        await self.broadcast(json.dumps(message))

    async def broadcast_heatmap_refresh(self, heatmap_data: List[dict]):
        """
        Broadcast updated heatmap data
        Args:
            heatmap_data: List of heatmap intensity points
        """
        message = {
            "type": "heatmap_refresh",
            "data": {
                "heatmap": heatmap_data,
                "timestamp": "2025-11-27T10:29:00Z"  # Will be dynamic
            }
        }
        await self.broadcast(json.dumps(message))

    async def broadcast_system_status(self, status_data: dict):
        """
        Broadcast system status updates
        Args:
            status_data: System status information
        """
        message = {
            "type": "system_status",
            "data": {
                "status": status_data,
                "timestamp": "2025-11-27T10:29:00Z"  # Will be dynamic
            }
        }
        await self.broadcast(json.dumps(message))

    def get_connection_stats(self) -> dict:
        """
        Get statistics about current connections
        Returns:
            Dictionary with connection statistics
        """
        return {
            "active_connections": len(self.active_connections),
            "connection_info": self.connection_info
        }


# Global instance for use across the application
manager = ConnectionManager()