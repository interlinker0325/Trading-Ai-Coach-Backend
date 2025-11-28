from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import json
import logging
import asyncio
from collections import deque
from app.services.websocket_service import get_websocket_service

logger = logging.getLogger(__name__)

router = APIRouter()

class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.websocket_service = get_websocket_service()
        self.update_queue: asyncio.Queue = asyncio.Queue()
        self._broadcast_task: asyncio.Task = None
        
    async def _broadcast_updates(self):
        """Background task to broadcast updates to all connected clients"""
        while True:
            try:
                # Wait for updates from the queue
                update_data = await self.update_queue.get()
                
                if update_data is None:  # Shutdown signal
                    break
                
                message = {
                    "type": "update",
                    "data": update_data
                }
                
                # Send to all connected clients
                disconnected = []
                for connection in self.active_connections:
                    try:
                        await connection.send_json(message)
                    except Exception as e:
                        logger.error(f"Error sending to client: {e}")
                        disconnected.append(connection)
                
                # Remove disconnected clients
                for conn in disconnected:
                    if conn in self.active_connections:
                        self.active_connections.remove(conn)
                
                self.update_queue.task_done()
            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}")
    
    def _sync_update_handler(self, data: Dict[str, Any]):
        """Sync callback handler that puts updates in the queue"""
        try:
            # Put update in queue (non-blocking)
            self.update_queue.put_nowait(data)
        except Exception as e:
            logger.error(f"Error queuing update: {e}")
    
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket connection. Total connections: {len(self.active_connections)}")
        
        # Start broadcast task if not already running
        if self._broadcast_task is None or self._broadcast_task.done():
            self._broadcast_task = asyncio.create_task(self._broadcast_updates())
        
        # Subscribe to updates from the service
        self.websocket_service.subscribe(self._sync_update_handler)
        
        # Send initial data snapshot
        initial_data = self.websocket_service.get_current_data()
        await websocket.send_json({
            "type": "snapshot",
            "data": initial_data
        })
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific client"""
        await websocket.send_json(message)

manager = ConnectionManager()

@router.websocket("/ws/market-data")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time market data
    Clients receive:
    - Initial snapshot of all market data on connection
    - Real-time updates when prices change
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle any client messages
            data = await websocket.receive_text()
            # Echo back or handle client requests
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

