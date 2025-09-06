"""
WebSocket handler for real-time notifications and messaging
"""

from fastapi import WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List, Set
import json
import asyncio
from datetime import datetime
import logging
from bson import ObjectId

from app.services.user_service import verify_token_and_get_user
from app.database.mongo_connection import get_database

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Store active connections: user_id -> List[WebSocket]
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Store connection metadata
        self.connection_metadata: Dict[WebSocket, Dict] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept WebSocket connection and register user"""
        await websocket.accept()
        
        # Initialize user's connection list if not exists
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        
        # Add connection
        self.active_connections[user_id].append(websocket)
        
        # Store metadata
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow(),
            "last_ping": datetime.utcnow()
        }
        
        logger.info(f"User {user_id} connected via WebSocket")
        
        # Send connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "message": "WebSocket connection established",
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        # Notify user's connections that they're online
        await self.broadcast_user_status(user_id, "online")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.connection_metadata:
            user_id = self.connection_metadata[websocket]["user_id"]
            
            # Remove from active connections
            if user_id in self.active_connections:
                self.active_connections[user_id].remove(websocket)
                
                # Remove user from dict if no more connections
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                    # Notify user's connections that they're offline
                    asyncio.create_task(self.broadcast_user_status(user_id, "offline"))
            
            # Remove metadata
            del self.connection_metadata[websocket]
            
            logger.info(f"User {user_id} disconnected from WebSocket")
    
    async def send_personal_message(self, user_id: str, message: dict):
        """Send message to specific user's all connections"""
        if user_id in self.active_connections:
            message_str = json.dumps(message)
            disconnected_sockets = []
            
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(message_str)
                except:
                    disconnected_sockets.append(websocket)
            
            # Clean up disconnected sockets
            for ws in disconnected_sockets:
                self.disconnect(ws)
    
    async def send_to_multiple_users(self, user_ids: List[str], message: dict):
        """Send message to multiple users"""
        for user_id in user_ids:
            await self.send_personal_message(user_id, message)
    
    async def broadcast_user_status(self, user_id: str, status: str):
        """Broadcast user online/offline status to their connections"""
        try:
            # Get user's connections from database
            db = await get_database()
            connections_collection = db.connections
            
            # Find all users connected to this user
            connected_users = await connections_collection.find({
                "$or": [
                    {"sender_id": user_id, "status": "accepted"},
                    {"receiver_id": user_id, "status": "accepted"}
                ]
            }).to_list(None)
            
            # Extract user IDs
            notify_user_ids = []
            for conn in connected_users:
                if conn["sender_id"] == user_id:
                    notify_user_ids.append(conn["receiver_id"])
                else:
                    notify_user_ids.append(conn["sender_id"])
            
            # Send status update
            status_message = {
                "type": "user_status_update",
                "user_id": user_id,
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.send_to_multiple_users(notify_user_ids, status_message)
            
        except Exception as e:
            logger.error(f"Error broadcasting user status: {e}")
    
    async def notify_connection_request(self, sender_id: str, receiver_id: str, connection_data: dict):
        """Notify user of new connection request"""
        message = {
            "type": "connection_request",
            "sender_id": sender_id,
            "data": connection_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_personal_message(receiver_id, message)
    
    async def notify_connection_response(self, responder_id: str, requester_id: str, accepted: bool, connection_data: dict):
        """Notify user of connection request response"""
        message = {
            "type": "connection_response",
            "responder_id": responder_id,
            "accepted": accepted,
            "data": connection_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_personal_message(requester_id, message)
    
    async def notify_new_message(self, chat_id: str, message_data: dict, participants: List[str], sender_id: str):
        """Notify participants of new message"""
        # Don't notify the sender
        recipients = [p for p in participants if p != sender_id]
        
        notification = {
            "type": "new_message",
            "chat_id": chat_id,
            "message": message_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.send_to_multiple_users(recipients, notification)
    
    async def notify_message_reaction(self, message_id: str, reaction_data: dict, participants: List[str], sender_id: str):
        """Notify participants of message reaction"""
        # Don't notify the sender
        recipients = [p for p in participants if p != sender_id]
        
        notification = {
            "type": "message_reaction",
            "message_id": message_id,
            "reaction": reaction_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.send_to_multiple_users(recipients, notification)
    
    async def notify_typing_status(self, chat_id: str, user_id: str, is_typing: bool, participants: List[str]):
        """Notify participants of typing status"""
        # Don't notify the sender
        recipients = [p for p in participants if p != user_id]
        
        notification = {
            "type": "typing_status",
            "chat_id": chat_id,
            "user_id": user_id,
            "is_typing": is_typing,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.send_to_multiple_users(recipients, notification)
    
    def get_online_users(self) -> List[str]:
        """Get list of currently online users"""
        return list(self.active_connections.keys())
    
    def is_user_online(self, user_id: str) -> bool:
        """Check if user is currently online"""
        return user_id in self.active_connections

# Global connection manager instance
manager = ConnectionManager()

async def get_websocket_user(websocket: WebSocket, token: str):
    """Get current user from WebSocket token - using same pattern as create_post_logic"""
    try:
        print(f"[DEBUG] WebSocket authentication attempt with token length: {len(token)}")
        print(f"[DEBUG] Token preview: {token[:20]}...")
        
        # Get database - same as create_post_logic
        from app.database.mongo_connection import get_database
        db = await get_database()
        print(f"[DEBUG] WebSocket database connection established")
        
        # Use the same authentication function as create_post_logic
        from app.api.v1.user_functions import get_current_user_from_token
        current_user = await get_current_user_from_token(db, token)
        print(f"[DEBUG] WebSocket get_current_user_from_token result: {current_user}")
        
        if current_user:
            print(f"[DEBUG] WebSocket current user: {current_user.get('email', 'unknown')}")
            print(f"[DEBUG] WebSocket current user keys: {list(current_user.keys())}")
            
            # Extract user_id - use 'id' field (not '_id') as that's what authentication returns
            user_id = current_user.get("id") or current_user.get("_id")
            if not user_id:
                print(f"[ERROR] No valid user ID found in WebSocket user data: {list(current_user.keys())}")
                await websocket.close(code=1008, reason="Invalid user data")
                return None
                
            print(f"[DEBUG] WebSocket using user_id: {user_id}")
            
            print(f"✅ WebSocket authentication successful for user: {current_user.get('username', 'unknown')} (ID: {user_id})")
            return current_user
        else:
            print(f"[DEBUG] WebSocket authentication failed: get_current_user_from_token returned None")
            print(f"[DEBUG] This could mean: invalid token, expired token, or user not found")
            await websocket.close(code=1008, reason="Invalid or expired token")
            return None
            
    except Exception as e:
        print(f"[DEBUG] WebSocket authentication exception: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"[DEBUG] WebSocket traceback: {traceback.format_exc()}")
        await websocket.close(code=1008, reason="Authentication failed")
        return None

async def handle_websocket_message(websocket: WebSocket, user_id: str, message_data: dict):
    """Handle incoming WebSocket messages"""
    message_type = message_data.get("type")
    
    # Add debug logging
    logger.info(f"Processing WebSocket message: type={message_type}, user_id={user_id}, data={message_data}")
    
    try:
        if message_type == "ping":
            # Update last ping time
            if websocket in manager.connection_metadata:
                manager.connection_metadata[websocket]["last_ping"] = datetime.utcnow()
            
            # Send pong response
            await websocket.send_text(json.dumps({
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            }))
        
        elif message_type == "typing":
            # Handle typing indicators
            chat_id = message_data.get("chat_id")
            is_typing = message_data.get("is_typing", False)
            
            if chat_id:
                # Get chat participants from database
                db = await get_database()
                chats_collection = db.chats
                
                # Convert string to ObjectId for MongoDB query
                try:
                    chat_obj_id = ObjectId(chat_id) if isinstance(chat_id, str) else chat_id
                    chat = await chats_collection.find_one({"_id": chat_obj_id})
                except Exception as e:
                    logger.error(f"Invalid chat_id format: {chat_id}, error: {e}")
                    return
                
                if chat and user_id in chat.get("participants", []):
                    await manager.notify_typing_status(
                        chat_id, user_id, is_typing, chat["participants"]
                    )
        
        elif message_type == "mark_online":
            # User explicitly marking themselves as online
            await manager.broadcast_user_status(user_id, "online")
        
        elif message_type == "mark_away":
            # User marking themselves as away
            await manager.broadcast_user_status(user_id, "away")
        
        else:
            logger.warning(f"Unknown WebSocket message type: {message_type}")
    
    except Exception as e:
        logger.error(f"Error handling WebSocket message: {str(e)} - message_type: {message_type}, user_id: {user_id}, message_data: {message_data}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Error processing message: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }))
