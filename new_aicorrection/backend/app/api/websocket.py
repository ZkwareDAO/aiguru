"""WebSocket API endpoints for real-time communication."""

import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.websocket_manager import websocket_manager, WebSocketMessage
from app.services.class_service import ClassService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/connect")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
    db: AsyncSession = Depends(get_db)
):
    """WebSocket connection endpoint."""
    user_id = None
    
    try:
        # Connect and authenticate user
        user_id = await websocket_manager.connect(websocket, token)
        if not user_id:
            return
        
        # Auto-join user to their class rooms
        class_service = ClassService(db)
        
        # Get user's classes (as student or teacher)
        user_classes = await class_service.get_user_classes(user_id)
        for class_obj in user_classes:
            room_name = f"class_{class_obj.id}"
            websocket_manager.join_room(user_id, room_name)
        
        # Listen for messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Handle different message types
                await handle_websocket_message(user_id, message_data, db)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: user_id={user_id}")
                break
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from user {user_id}")
                await websocket_manager.send_personal_message(user_id, {
                    "type": "error",
                    "data": {"message": "Invalid JSON format"}
                })
            except Exception as e:
                logger.error(f"Error handling WebSocket message from user {user_id}: {e}")
                await websocket_manager.send_personal_message(user_id, {
                    "type": "error",
                    "data": {"message": "Internal server error"}
                })
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    
    finally:
        # Clean up connection
        if user_id:
            websocket_manager.disconnect(user_id)


async def handle_websocket_message(user_id: UUID, message_data: dict, db: AsyncSession):
    """Handle incoming WebSocket messages."""
    message_type = message_data.get("type")
    data = message_data.get("data", {})
    
    logger.debug(f"Handling WebSocket message: user_id={user_id}, type={message_type}")
    
    if message_type == "ping":
        await websocket_manager.handle_ping(user_id)
    
    elif message_type == "join_room":
        room = data.get("room")
        if room:
            success = websocket_manager.join_room(user_id, room)
            await websocket_manager.send_personal_message(user_id, {
                "type": "room_joined" if success else "room_join_failed",
                "data": {"room": room}
            })
    
    elif message_type == "leave_room":
        room = data.get("room")
        if room:
            websocket_manager.leave_room(user_id, room)
            await websocket_manager.send_personal_message(user_id, {
                "type": "room_left",
                "data": {"room": room}
            })
    
    elif message_type == "send_message":
        await handle_send_message(user_id, data, db)
    
    elif message_type == "typing_start":
        await handle_typing_indicator(user_id, data, True)
    
    elif message_type == "typing_stop":
        await handle_typing_indicator(user_id, data, False)
    
    elif message_type == "mark_notifications_read":
        await handle_mark_notifications_read(user_id, data, db)
    
    else:
        logger.warning(f"Unknown message type: {message_type}")
        await websocket_manager.send_personal_message(user_id, {
            "type": "error",
            "data": {"message": f"Unknown message type: {message_type}"}
        })


async def handle_send_message(user_id: UUID, data: dict, db: AsyncSession):
    """Handle sending messages to rooms or users."""
    recipient_type = data.get("recipient_type")  # "user" or "room"
    recipient_id = data.get("recipient_id")
    content = data.get("content")
    
    if not recipient_type or not recipient_id or not content:
        await websocket_manager.send_personal_message(user_id, {
            "type": "error",
            "data": {"message": "Missing required fields: recipient_type, recipient_id, content"}
        })
        return
    
    message = {
        "type": "message",
        "data": {
            "sender_id": str(user_id),
            "content": content,
            "timestamp": data.get("timestamp"),
            "message_id": data.get("message_id")
        }
    }
    
    if recipient_type == "room":
        # Send to room (exclude sender)
        sent_count = await websocket_manager.send_room_message(
            recipient_id, message, exclude_user=user_id
        )
        
        # Confirm to sender
        await websocket_manager.send_personal_message(user_id, {
            "type": "message_sent",
            "data": {
                "message_id": data.get("message_id"),
                "recipients_count": sent_count
            }
        })
    
    elif recipient_type == "user":
        # Send to specific user
        try:
            recipient_user_id = UUID(recipient_id)
            success = await websocket_manager.send_personal_message(recipient_user_id, message)
            
            # Confirm to sender
            await websocket_manager.send_personal_message(user_id, {
                "type": "message_sent",
                "data": {
                    "message_id": data.get("message_id"),
                    "delivered": success
                }
            })
        except ValueError:
            await websocket_manager.send_personal_message(user_id, {
                "type": "error",
                "data": {"message": "Invalid recipient user ID"}
            })


async def handle_typing_indicator(user_id: UUID, data: dict, is_typing: bool):
    """Handle typing indicators."""
    room = data.get("room")
    if not room:
        return
    
    message = {
        "type": "typing_indicator",
        "data": {
            "user_id": str(user_id),
            "is_typing": is_typing,
            "room": room
        }
    }
    
    # Send to room (exclude sender)
    await websocket_manager.send_room_message(room, message, exclude_user=user_id)


async def handle_mark_notifications_read(user_id: UUID, data: dict, db: AsyncSession):
    """Handle marking notifications as read."""
    notification_ids = data.get("notification_ids", [])
    
    if not notification_ids:
        return
    
    try:
        # Import here to avoid circular imports
        from app.services.notification_service import AssignmentNotificationService
        
        notification_service = AssignmentNotificationService(db)
        
        # Convert string IDs to UUIDs
        uuid_ids = [UUID(nid) for nid in notification_ids]
        
        # Mark as read
        updated_count = await notification_service.mark_notifications_read(user_id, uuid_ids)
        
        # Confirm to user
        await websocket_manager.send_personal_message(user_id, {
            "type": "notifications_marked_read",
            "data": {
                "updated_count": updated_count,
                "notification_ids": notification_ids
            }
        })
        
    except Exception as e:
        logger.error(f"Error marking notifications as read: {e}")
        await websocket_manager.send_personal_message(user_id, {
            "type": "error",
            "data": {"message": "Failed to mark notifications as read"}
        })


# WebSocket status endpoints
@router.get("/status")
async def websocket_status():
    """Get WebSocket server status."""
    connected_users = websocket_manager.get_connected_users()
    
    return {
        "status": "active",
        "connected_users_count": len(connected_users),
        "rooms_count": len(websocket_manager.room_subscriptions),
        "total_room_subscriptions": sum(
            len(users) for users in websocket_manager.room_subscriptions.values()
        )
    }


@router.get("/connections")
async def get_connections():
    """Get information about active connections (admin only)."""
    connections = []
    
    for user_id, conn_info in websocket_manager.active_connections.items():
        connections.append({
            "user_id": str(user_id),
            "user_role": conn_info.user_role,
            "connected_at": conn_info.connected_at.isoformat(),
            "last_ping": conn_info.last_ping.isoformat(),
            "rooms": list(websocket_manager.user_rooms.get(user_id, set()))
        })
    
    return {
        "connections": connections,
        "total_count": len(connections)
    }


@router.post("/send-notification/{user_id}")
async def send_notification_to_user(
    user_id: UUID,
    notification_data: dict
):
    """Send notification to a specific user via WebSocket (admin only)."""
    success = await websocket_manager.send_notification(user_id, notification_data)
    
    return {
        "success": success,
        "user_id": str(user_id),
        "message": "Notification sent" if success else "User not connected"
    }


@router.post("/broadcast")
async def broadcast_message(message_data: dict):
    """Broadcast message to all connected users (admin only)."""
    sent_count = await websocket_manager.broadcast_message(message_data)
    
    return {
        "success": True,
        "recipients_count": sent_count,
        "message": f"Message broadcasted to {sent_count} users"
    }