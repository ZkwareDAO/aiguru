"""WebSocket connection manager for real-time communication."""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.core.auth import decode_access_token
from app.models.user import UserRole

logger = logging.getLogger(__name__)


class WebSocketMessage(BaseModel):
    """WebSocket message model."""
    type: str
    data: dict
    timestamp: datetime = datetime.utcnow()
    sender_id: Optional[UUID] = None
    recipient_id: Optional[UUID] = None
    room: Optional[str] = None


class ConnectionInfo(BaseModel):
    """Connection information model."""
    user_id: UUID
    user_role: UserRole
    websocket: WebSocket
    connected_at: datetime = datetime.utcnow()
    last_ping: datetime = datetime.utcnow()


class WebSocketManager:
    """Manages WebSocket connections and message routing."""
    
    def __init__(self):
        # Active connections: user_id -> ConnectionInfo
        self.active_connections: Dict[UUID, ConnectionInfo] = {}
        
        # Room subscriptions: room_name -> set of user_ids
        self.room_subscriptions: Dict[str, Set[UUID]] = {}
        
        # User rooms: user_id -> set of room_names
        self.user_rooms: Dict[UUID, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, token: str) -> Optional[UUID]:
        """Accept WebSocket connection and authenticate user."""
        try:
            # Decode JWT token to get user info
            payload = decode_access_token(token)
            if not payload:
                await websocket.close(code=4001, reason="Invalid token")
                return None
            
            user_id = UUID(payload.get("sub"))
            user_role = UserRole(payload.get("role", "student"))
            
            # Accept connection
            await websocket.accept()
            
            # Store connection info
            connection_info = ConnectionInfo(
                user_id=user_id,
                user_role=user_role,
                websocket=websocket
            )
            self.active_connections[user_id] = connection_info
            
            # Initialize user rooms
            if user_id not in self.user_rooms:
                self.user_rooms[user_id] = set()
            
            logger.info(f"WebSocket connected: user_id={user_id}, role={user_role}")
            
            # Send connection confirmation
            await self.send_personal_message(user_id, {
                "type": "connection_established",
                "data": {
                    "user_id": str(user_id),
                    "connected_at": connection_info.connected_at.isoformat()
                }
            })
            
            return user_id
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            await websocket.close(code=4000, reason="Connection failed")
            return None
    
    def disconnect(self, user_id: UUID):
        """Remove user connection and clean up subscriptions."""
        if user_id in self.active_connections:
            # Remove from all rooms
            if user_id in self.user_rooms:
                for room in self.user_rooms[user_id].copy():
                    self.leave_room(user_id, room)
                del self.user_rooms[user_id]
            
            # Remove connection
            del self.active_connections[user_id]
            logger.info(f"WebSocket disconnected: user_id={user_id}")
    
    def join_room(self, user_id: UUID, room: str):
        """Add user to a room for group messaging."""
        if user_id not in self.active_connections:
            return False
        
        # Add to room subscriptions
        if room not in self.room_subscriptions:
            self.room_subscriptions[room] = set()
        self.room_subscriptions[room].add(user_id)
        
        # Add to user rooms
        if user_id not in self.user_rooms:
            self.user_rooms[user_id] = set()
        self.user_rooms[user_id].add(room)
        
        logger.info(f"User {user_id} joined room {room}")
        return True
    
    def leave_room(self, user_id: UUID, room: str):
        """Remove user from a room."""
        # Remove from room subscriptions
        if room in self.room_subscriptions:
            self.room_subscriptions[room].discard(user_id)
            if not self.room_subscriptions[room]:
                del self.room_subscriptions[room]
        
        # Remove from user rooms
        if user_id in self.user_rooms:
            self.user_rooms[user_id].discard(room)
        
        logger.info(f"User {user_id} left room {room}")
    
    async def send_personal_message(self, user_id: UUID, message: dict):
        """Send message to a specific user."""
        if user_id not in self.active_connections:
            logger.warning(f"User {user_id} not connected, cannot send message")
            return False
        
        try:
            connection = self.active_connections[user_id]
            websocket_message = WebSocketMessage(
                type=message.get("type", "message"),
                data=message.get("data", {}),
                recipient_id=user_id
            )
            
            await connection.websocket.send_text(websocket_message.model_dump_json())
            logger.debug(f"Message sent to user {user_id}: {message.get('type')}")
            return True
            
        except WebSocketDisconnect:
            logger.info(f"User {user_id} disconnected during message send")
            self.disconnect(user_id)
            return False
        except Exception as e:
            logger.error(f"Failed to send message to user {user_id}: {e}")
            return False
    
    async def send_room_message(self, room: str, message: dict, exclude_user: Optional[UUID] = None):
        """Send message to all users in a room."""
        if room not in self.room_subscriptions:
            logger.warning(f"Room {room} has no subscribers")
            return 0
        
        sent_count = 0
        failed_users = []
        
        for user_id in self.room_subscriptions[room].copy():
            if exclude_user and user_id == exclude_user:
                continue
            
            success = await self.send_personal_message(user_id, message)
            if success:
                sent_count += 1
            else:
                failed_users.append(user_id)
        
        # Clean up failed connections
        for user_id in failed_users:
            self.disconnect(user_id)
        
        logger.info(f"Room message sent to {sent_count} users in room {room}")
        return sent_count
    
    async def broadcast_message(self, message: dict, exclude_user: Optional[UUID] = None):
        """Send message to all connected users."""
        sent_count = 0
        failed_users = []
        
        for user_id in list(self.active_connections.keys()):
            if exclude_user and user_id == exclude_user:
                continue
            
            success = await self.send_personal_message(user_id, message)
            if success:
                sent_count += 1
            else:
                failed_users.append(user_id)
        
        # Clean up failed connections
        for user_id in failed_users:
            self.disconnect(user_id)
        
        logger.info(f"Broadcast message sent to {sent_count} users")
        return sent_count
    
    async def send_notification(self, user_id: UUID, notification_data: dict):
        """Send notification through WebSocket."""
        message = {
            "type": "notification",
            "data": {
                "id": notification_data.get("id"),
                "title": notification_data.get("title"),
                "content": notification_data.get("content"),
                "type": notification_data.get("type"),
                "priority": notification_data.get("priority", "normal"),
                "action_url": notification_data.get("action_url"),
                "action_text": notification_data.get("action_text"),
                "created_at": notification_data.get("created_at"),
                "data": notification_data.get("data", {})
            }
        }
        
        return await self.send_personal_message(user_id, message)
    
    async def send_class_notification(self, class_id: UUID, notification_data: dict, exclude_user: Optional[UUID] = None):
        """Send notification to all users in a class."""
        room = f"class_{class_id}"
        message = {
            "type": "class_notification",
            "data": {
                "class_id": str(class_id),
                **notification_data
            }
        }
        
        return await self.send_room_message(room, message, exclude_user)
    
    async def handle_ping(self, user_id: UUID):
        """Handle ping message to keep connection alive."""
        if user_id in self.active_connections:
            self.active_connections[user_id].last_ping = datetime.utcnow()
            await self.send_personal_message(user_id, {
                "type": "pong",
                "data": {"timestamp": datetime.utcnow().isoformat()}
            })
    
    def get_connected_users(self) -> List[UUID]:
        """Get list of connected user IDs."""
        return list(self.active_connections.keys())
    
    def get_room_users(self, room: str) -> List[UUID]:
        """Get list of user IDs in a room."""
        return list(self.room_subscriptions.get(room, set()))
    
    def is_user_connected(self, user_id: UUID) -> bool:
        """Check if user is connected."""
        return user_id in self.active_connections
    
    def get_connection_info(self, user_id: UUID) -> Optional[ConnectionInfo]:
        """Get connection information for a user."""
        return self.active_connections.get(user_id)


# Global WebSocket manager instance
websocket_manager = WebSocketManager()