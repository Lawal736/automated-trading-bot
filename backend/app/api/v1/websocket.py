from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, List
import json
import logging
from datetime import datetime
from app.core.security import get_current_user_ws
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
        self.user_subscriptions: Dict[int, List[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"User {user_id} connected to WebSocket")

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"User {user_id} disconnected from WebSocket")

    async def send_personal_message(self, message: dict, user_id: int):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    # Remove broken connection
                    self.active_connections[user_id].remove(connection)

    async def broadcast(self, message: dict):
        for user_id in self.active_connections:
            await self.send_personal_message(message, user_id)

    def subscribe_user_to_bot(self, user_id: int, bot_id: str):
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = []
        if bot_id not in self.user_subscriptions[user_id]:
            self.user_subscriptions[user_id].append(bot_id)

    def unsubscribe_user_from_bot(self, user_id: int, bot_id: str):
        if user_id in self.user_subscriptions and bot_id in self.user_subscriptions[user_id]:
            self.user_subscriptions[user_id].remove(bot_id)

    def is_user_subscribed_to_bot(self, user_id: int, bot_id: str) -> bool:
        return user_id in self.user_subscriptions and bot_id in self.user_subscriptions[user_id]

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    user = None
    try:
        # Get token from query parameters
        token = websocket.query_params.get("token")
        print(f"[WebSocket] Received connection with token: {token}")
        if not token:
            print("[WebSocket] No token provided, closing connection.")
            await websocket.close(code=4001, reason="No token provided")
            return

        # Authenticate user
        user = await get_current_user_ws(token)
        print(f"[WebSocket] User from token: {user}")
        if not user:
            print("[WebSocket] Invalid token or user not found, closing connection.")
            await websocket.close(code=4001, reason="Invalid token")
            return

        await manager.connect(websocket, user.id)

        # Send connection confirmation
        await manager.send_personal_message({
            "type": "connected",
            "message": "Successfully connected to WebSocket",
            "user_id": user.id,
            "timestamp": datetime.utcnow().isoformat()
        }, user.id)

        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                await handle_websocket_message(message, user)
                
            except WebSocketDisconnect:
                manager.disconnect(websocket, user.id)
                break
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.utcnow().isoformat()
                }, user.id)
            except Exception as e:
                logger.error(f"WebSocket error for user {user.id}: {e}")
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Internal server error",
                    "timestamp": datetime.utcnow().isoformat()
                }, user.id)

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        if user:
            manager.disconnect(websocket, user.id)
        await websocket.close(code=4000, reason="Internal server error")

async def handle_websocket_message(message: dict, user: User):
    """Handle incoming WebSocket messages"""
    message_type = message.get("type")
    data = message.get("data", {})

    if message_type == "subscribe_bot":
        bot_id = data.get("bot_id")
        if bot_id:
            manager.subscribe_user_to_bot(user.id, bot_id)
            await manager.send_personal_message({
                "type": "subscribed",
                "message": f"Subscribed to bot {bot_id}",
                "bot_id": bot_id,
                "timestamp": datetime.utcnow().isoformat()
            }, user.id)

    elif message_type == "unsubscribe_bot":
        bot_id = data.get("bot_id")
        if bot_id:
            manager.unsubscribe_user_from_bot(user.id, bot_id)
            await manager.send_personal_message({
                "type": "unsubscribed",
                "message": f"Unsubscribed from bot {bot_id}",
                "bot_id": bot_id,
                "timestamp": datetime.utcnow().isoformat()
            }, user.id)

    elif message_type == "ping":
        await manager.send_personal_message({
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        }, user.id)

    else:
        await manager.send_personal_message({
            "type": "error",
            "message": f"Unknown message type: {message_type}",
            "timestamp": datetime.utcnow().isoformat()
        }, user.id)

# Utility functions for sending notifications
async def send_notification_to_user(user_id: int, notification: dict):
    """Send a notification to a specific user"""
    await manager.send_personal_message({
        "type": "notification",
        "notification": notification,
        "timestamp": datetime.utcnow().isoformat()
    }, user_id)

async def send_trade_update_to_user(user_id: int, trade_data: dict):
    """Send a trade update to a specific user"""
    await manager.send_personal_message({
        "type": "trade_update",
        "trade": trade_data,
        "timestamp": datetime.utcnow().isoformat()
    }, user_id)

async def send_bot_status_update_to_user(user_id: int, bot_data: dict):
    """Send a bot status update to a specific user"""
    await manager.send_personal_message({
        "type": "bot_status",
        "bot": bot_data,
        "timestamp": datetime.utcnow().isoformat()
    }, user_id)

async def broadcast_system_alert(alert_data: dict):
    """Broadcast a system alert to all connected users"""
    await manager.broadcast({
        "type": "system_alert",
        "alert": alert_data,
        "timestamp": datetime.utcnow().isoformat()
    })

def get_connected_users() -> List[int]:
    """Get list of connected user IDs"""
    return list(manager.active_connections.keys())

def get_user_subscriptions(user_id: int) -> List[str]:
    """Get list of bot IDs that a user is subscribed to"""
    return manager.user_subscriptions.get(user_id, []) 