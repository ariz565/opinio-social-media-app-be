"""
Messaging System Model with Connection-based permissions
Only allows messaging between connected users
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Set
from enum import Enum
import asyncio
from bson import ObjectId
from app.database.mongo_connection import get_database
from app.models.connection import connection_model

class MessageType(str, Enum):
    """Message types"""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    VOICE = "voice"
    FILE = "file"
    LOCATION = "location"

class ChatType(str, Enum):
    """Chat types"""
    DIRECT = "direct"
    GROUP = "group"

class DeliveryStatus(str, Enum):
    """Message delivery status"""
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"

class MessagingModel:
    """
    Messaging system with connection-based permissions
    Only allows messaging between connected users
    """
    
    def __init__(self):
        self.db = None
        
    async def get_db(self):
        """Get database connection"""
        if self.db is None:
            self.db = await get_database()
        return self.db

    async def create_chat(
        self,
        creator_id: str,
        participant_ids: List[str],
        chat_type: ChatType = ChatType.DIRECT,
        chat_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new chat (only between connected users for direct chats)"""
        db = await self.get_db()
        
        # For direct chats, ensure users are connected
        if chat_type == ChatType.DIRECT:
            if len(participant_ids) != 1:
                return {"success": False, "message": "Direct chat must have exactly one other participant"}
            
            other_user_id = participant_ids[0]
            
            # Check if users are connected
            are_connected = await connection_model.are_users_connected(creator_id, other_user_id)
            if not are_connected:
                return {"success": False, "message": "You can only message users you're connected with"}
            
            # Check if direct chat already exists
            existing_chat = await db.chats.find_one({
                "type": ChatType.DIRECT,
                "participants": {"$all": [creator_id, other_user_id], "$size": 2}
            })
            
            if existing_chat:
                return {
                    "success": True,
                    "message": "Chat already exists",
                    "chat_id": str(existing_chat["_id"]),
                    "existing": True
                }
        
        # Create new chat
        all_participants = [creator_id] + participant_ids
        chat_data = {
            "type": chat_type,
            "name": chat_name,
            "participants": list(set(all_participants)),  # Remove duplicates
            "creator_id": creator_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_message": None,
            "is_active": True,
            "settings": {
                "encryption": True,
                "disappearing_messages": False,
                "muted_by": []
            }
        }
        
        result = await db.chats.insert_one(chat_data)
        
        return {
            "success": True,
            "message": "Chat created successfully",
            "chat_id": str(result.inserted_id),
            "existing": False
        }

    async def send_message(
        self,
        sender_id: str,
        chat_id: str,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        reply_to: Optional[str] = None,
        media_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a message in a chat"""
        db = await self.get_db()
        
        # Get chat and verify sender is participant
        chat = await db.chats.find_one({
            "_id": ObjectId(chat_id),
            "participants": sender_id,
            "is_active": True
        })
        
        if not chat:
            return {"success": False, "message": "Chat not found or you're not a participant"}
        
        # For direct chats, verify users are still connected
        if chat["type"] == ChatType.DIRECT:
            other_participant = next(p for p in chat["participants"] if p != sender_id)
            are_connected = await connection_model.are_users_connected(sender_id, other_participant)
            
            if not are_connected:
                return {"success": False, "message": "You can only message connected users"}
        
        # Create message
        message_data = {
            "chat_id": chat_id,
            "sender_id": sender_id,
            "content": content,
            "type": message_type,
            "media_url": media_url,
            "reply_to": reply_to,
            "created_at": datetime.utcnow(),
            "delivery_status": DeliveryStatus.SENT,
            "read_by": [sender_id],  # Sender has read their own message
            "reactions": [],
            "is_edited": False,
            "is_forwarded": False,
            "edit_history": []
        }
        
        # Add disappearing message settings if enabled
        if chat.get("settings", {}).get("disappearing_messages"):
            message_data["disappears_at"] = datetime.utcnow() + timedelta(hours=24)
        
        result = await db.messages.insert_one(message_data)
        
        # Update chat's last message
        await db.chats.update_one(
            {"_id": ObjectId(chat_id)},
            {
                "$set": {
                    "last_message": {
                        "content": content,
                        "sender_id": sender_id,
                        "timestamp": datetime.utcnow(),
                        "type": message_type
                    },
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Create notifications for other participants
        for participant_id in chat["participants"]:
            if participant_id != sender_id:
                await self._create_message_notification(
                    sender_id, participant_id, chat_id, content
                )
        
        return {
            "success": True,
            "message": "Message sent successfully",
            "message_id": str(result.inserted_id)
        }

    async def get_user_chats(
        self,
        user_id: str,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's chats with last message and unread count"""
        db = await self.get_db()
        
        # Get user's chats
        chats = await db.chats.find({
            "participants": user_id,
            "is_active": True
        })\
        .sort("updated_at", -1)\
        .skip(skip)\
        .limit(limit)\
        .to_list(length=None)
        
        enriched_chats = []
        
        for chat in chats:
            # Get unread message count
            unread_count = await db.messages.count_documents({
                "chat_id": str(chat["_id"]),
                "sender_id": {"$ne": user_id},
                "read_by": {"$ne": user_id}
            })
            
            # Get other participants' details
            other_participants = [p for p in chat["participants"] if p != user_id]
            participant_details = []
            
            for participant_id in other_participants:
                user_details = await db.users.find_one(
                    {"_id": ObjectId(participant_id)},
                    {"username": 1, "full_name": 1, "profile_picture": 1, "is_online": 1}
                )
                if user_details:
                    participant_details.append({
                        "id": str(user_details["_id"]),
                        "username": user_details.get("username"),
                        "full_name": user_details.get("full_name"),
                        "profile_picture": user_details.get("profile_picture"),
                        "is_online": user_details.get("is_online", False)
                    })
            
            # For direct chats, verify connection still exists
            is_accessible = True
            if chat["type"] == ChatType.DIRECT and other_participants:
                is_accessible = await connection_model.are_users_connected(
                    user_id, other_participants[0]
                )
            
            # Set chat name for direct chats
            chat_name = chat.get("name")
            if not chat_name and chat["type"] == ChatType.DIRECT and participant_details:
                chat_name = participant_details[0]["full_name"]
            
            enriched_chat = {
                "id": str(chat["_id"]),
                "type": chat["type"],
                "name": chat_name,
                "participants": participant_details,
                "creator_id": chat.get("creator_id"),
                "last_message": chat.get("last_message"),
                "unread_count": unread_count,
                "is_accessible": is_accessible,
                "settings": chat.get("settings", {}),
                "created_at": chat["created_at"],
                "updated_at": chat["updated_at"]
            }
            
            enriched_chats.append(enriched_chat)
        
        return enriched_chats

    async def get_chat_messages(
        self,
        user_id: str,
        chat_id: str,
        limit: int = 50,
        skip: int = 0
    ) -> Dict[str, Any]:
        """Get messages for a chat"""
        db = await self.get_db()
        
        # Verify user is participant
        chat = await db.chats.find_one({
            "_id": ObjectId(chat_id),
            "participants": user_id,
            "is_active": True
        })
        
        if not chat:
            return {"success": False, "message": "Chat not found or access denied"}
        
        # For direct chats, verify connection still exists
        if chat["type"] == ChatType.DIRECT:
            other_participant = next(p for p in chat["participants"] if p != user_id)
            are_connected = await connection_model.are_users_connected(user_id, other_participant)
            
            if not are_connected:
                return {"success": False, "message": "Cannot access messages from disconnected users"}
        
        # Get messages
        messages = await db.messages.find({
            "chat_id": chat_id
        })\
        .sort("created_at", -1)\
        .skip(skip)\
        .limit(limit)\
        .to_list(length=None)
        
        # Enrich messages with sender details
        enriched_messages = []
        for message in messages:
            sender_details = await db.users.find_one(
                {"_id": ObjectId(message["sender_id"])},
                {"username": 1, "full_name": 1, "profile_picture": 1}
            )
            
            enriched_message = {
                "id": str(message["_id"]),
                "chat_id": message["chat_id"],
                "sender": {
                    "id": message["sender_id"],
                    "username": sender_details.get("username") if sender_details else "Unknown",
                    "full_name": sender_details.get("full_name") if sender_details else "Unknown",
                    "profile_picture": sender_details.get("profile_picture") if sender_details else None
                },
                "content": message["content"],
                "type": message["type"],
                "media_url": message.get("media_url"),
                "reply_to": message.get("reply_to"),
                "created_at": message["created_at"],
                "delivery_status": message.get("delivery_status"),
                "read_by": message.get("read_by", []),
                "reactions": message.get("reactions", []),
                "is_edited": message.get("is_edited", False),
                "is_forwarded": message.get("is_forwarded", False),
                "disappears_at": message.get("disappears_at")
            }
            
            enriched_messages.append(enriched_message)
        
        # Mark messages as read by this user
        await db.messages.update_many(
            {
                "chat_id": chat_id,
                "sender_id": {"$ne": user_id},
                "read_by": {"$ne": user_id}
            },
            {"$push": {"read_by": user_id}}
        )
        
        return {
            "success": True,
            "messages": list(reversed(enriched_messages)),  # Return in chronological order
            "chat": {
                "id": str(chat["_id"]),
                "type": chat["type"],
                "name": chat.get("name"),
                "participants": chat["participants"]
            }
        }

    async def mark_messages_as_read(
        self,
        user_id: str,
        chat_id: str
    ) -> Dict[str, Any]:
        """Mark all messages in a chat as read by user"""
        db = await self.get_db()
        
        # Verify user is participant
        chat = await db.chats.find_one({
            "_id": ObjectId(chat_id),
            "participants": user_id
        })
        
        if not chat:
            return {"success": False, "message": "Chat not found or access denied"}
        
        # Mark messages as read
        result = await db.messages.update_many(
            {
                "chat_id": chat_id,
                "sender_id": {"$ne": user_id},
                "read_by": {"$ne": user_id}
            },
            {"$push": {"read_by": user_id}}
        )
        
        return {
            "success": True,
            "message": f"Marked {result.modified_count} messages as read"
        }

    async def delete_message(
        self,
        user_id: str,
        message_id: str
    ) -> Dict[str, Any]:
        """Delete a message (only sender can delete)"""
        db = await self.get_db()
        
        # Find message and verify sender
        message = await db.messages.find_one({
            "_id": ObjectId(message_id),
            "sender_id": user_id
        })
        
        if not message:
            return {"success": False, "message": "Message not found or permission denied"}
        
        # Delete message
        await db.messages.delete_one({"_id": ObjectId(message_id)})
        
        return {"success": True, "message": "Message deleted successfully"}

    async def edit_message(
        self,
        user_id: str,
        message_id: str,
        new_content: str
    ) -> Dict[str, Any]:
        """Edit a message (only sender can edit within time limit)"""
        db = await self.get_db()
        
        # Find message and verify sender
        message = await db.messages.find_one({
            "_id": ObjectId(message_id),
            "sender_id": user_id
        })
        
        if not message:
            return {"success": False, "message": "Message not found or permission denied"}
        
        # Check if message is too old to edit (15 minutes limit)
        if datetime.utcnow() - message["created_at"] > timedelta(minutes=15):
            return {"success": False, "message": "Message is too old to edit"}
        
        # Update message
        edit_entry = {
            "content": message["content"],
            "timestamp": datetime.utcnow()
        }
        
        await db.messages.update_one(
            {"_id": ObjectId(message_id)},
            {
                "$set": {
                    "content": new_content,
                    "is_edited": True
                },
                "$push": {"edit_history": edit_entry}
            }
        )
        
        return {"success": True, "message": "Message edited successfully"}

    async def add_reaction(
        self,
        user_id: str,
        message_id: str,
        emoji: str
    ) -> Dict[str, Any]:
        """Add reaction to a message"""
        db = await self.get_db()
        
        # Find message and verify user has access
        message = await db.messages.find_one({"_id": ObjectId(message_id)})
        if not message:
            return {"success": False, "message": "Message not found"}
        
        # Verify user is participant in the chat
        chat = await db.chats.find_one({
            "_id": ObjectId(message["chat_id"]),
            "participants": user_id
        })
        
        if not chat:
            return {"success": False, "message": "Access denied"}
        
        # Add or update reaction
        await db.messages.update_one(
            {"_id": ObjectId(message_id)},
            {
                "$pull": {"reactions": {"user_id": user_id}},  # Remove existing reaction
            }
        )
        
        await db.messages.update_one(
            {"_id": ObjectId(message_id)},
            {
                "$push": {"reactions": {"emoji": emoji, "user_id": user_id, "timestamp": datetime.utcnow()}}
            }
        )
        
        return {"success": True, "message": "Reaction added successfully"}

    async def remove_reaction(
        self,
        user_id: str,
        message_id: str
    ) -> Dict[str, Any]:
        """Remove user's reaction from a message"""
        db = await self.get_db()
        
        # Remove reaction
        result = await db.messages.update_one(
            {"_id": ObjectId(message_id)},
            {"$pull": {"reactions": {"user_id": user_id}}}
        )
        
        if result.modified_count == 0:
            return {"success": False, "message": "No reaction to remove"}
        
        return {"success": True, "message": "Reaction removed successfully"}

    async def can_message_user(
        self,
        sender_id: str,
        receiver_id: str
    ) -> Dict[str, Any]:
        """Check if sender can message receiver (wrapper for connection check)"""
        are_connected = await connection_model.are_users_connected(sender_id, receiver_id)
        
        if are_connected:
            return {
                "can_message": True,
                "reason": "Users are connected"
            }
        else:
            return {
                "can_message": False,
                "reason": "Users must be connected to message each other"
            }

    async def search_messages(
        self,
        user_id: str,
        query: str,
        chat_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search messages (only in chats user participates in)"""
        db = await self.get_db()
        
        # Build search query
        search_query = {
            "content": {"$regex": query, "$options": "i"}
        }
        
        if chat_id:
            # Search in specific chat
            chat = await db.chats.find_one({
                "_id": ObjectId(chat_id),
                "participants": user_id
            })
            
            if not chat:
                return []
            
            search_query["chat_id"] = chat_id
        else:
            # Search in all user's chats
            user_chats = await db.chats.find({
                "participants": user_id,
                "is_active": True
            }).to_list(length=None)
            
            chat_ids = [str(chat["_id"]) for chat in user_chats]
            search_query["chat_id"] = {"$in": chat_ids}
        
        # Search messages
        messages = await db.messages.find(search_query)\
            .sort("created_at", -1)\
            .limit(limit)\
            .to_list(length=None)
        
        # Enrich with sender and chat details
        enriched_results = []
        for message in messages:
            sender_details = await db.users.find_one(
                {"_id": ObjectId(message["sender_id"])},
                {"username": 1, "full_name": 1, "profile_picture": 1}
            )
            
            chat_details = await db.chats.find_one({"_id": ObjectId(message["chat_id"])})
            
            enriched_results.append({
                "message_id": str(message["_id"]),
                "content": message["content"],
                "sender": sender_details,
                "chat": {
                    "id": str(chat_details["_id"]),
                    "name": chat_details.get("name"),
                    "type": chat_details["type"]
                },
                "created_at": message["created_at"]
            })
        
        return enriched_results

    async def _create_message_notification(
        self,
        sender_id: str,
        receiver_id: str,
        chat_id: str,
        content: str
    ):
        """Create notification for new message"""
        db = await self.get_db()
        
        # Get sender details
        sender = await db.users.find_one(
            {"_id": ObjectId(sender_id)},
            {"username": 1, "full_name": 1}
        )
        
        notification = {
            "user_id": receiver_id,
            "from_user_id": sender_id,
            "type": "new_message",
            "title": f"New message from {sender.get('full_name', 'Someone')}",
            "message": content[:100] + "..." if len(content) > 100 else content,
            "data": {
                "chat_id": chat_id,
                "sender_name": sender.get("full_name")
            },
            "is_read": False,
            "created_at": datetime.utcnow()
        }
        
        try:
            await db.notifications.insert_one(notification)
        except Exception as e:
            # Log error but don't fail message sending
            print(f"Failed to create message notification: {e}")

# Create global instance
messaging_model = MessagingModel()
