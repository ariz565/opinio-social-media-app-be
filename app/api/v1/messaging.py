"""
API functions for messaging system
Handles messaging with connection-based permissions
"""

from typing import List, Optional
from fastapi import HTTPException, Depends, Query
from app.models.messaging import messaging_model
from app.schemas.messaging import (
    CreateChatRequest, SendMessageRequest, EditMessageRequest, AddReactionRequest,
    MarkAsReadRequest, MessageSearchRequest, CreateChatResponse, SendMessageResponse,
    GetChatsResponse, GetMessagesResponse, MessageSearchResponse, MessageActionResponse,
    CanMessageResponse, ChatInfo, MessageInfo, MessageSearchResult, UserInfo
)
from app.core.auth import get_current_user
from app.core.websocket import manager

# Chat management
from app.models.messaging import messaging_model
from app.core.websocket import manager


def get_user_id(user: dict) -> str:
    """Safely extract user ID from user object (handles both 'id' and '_id' fields)"""
    return user.get("id") or user.get("_id")


async def create_chat(
    request_data: CreateChatRequest,
    current_user: dict = Depends(get_current_user)
) -> CreateChatResponse:
    """Create a new chat"""
    try:
        current_user_id = get_user_id(current_user)
        result = await messaging_model.create_chat(
            creator_id=current_user_id,
            participant_ids=request_data.participant_ids,
            chat_type=request_data.chat_type,
            chat_name=request_data.chat_name
        )
        
        return CreateChatResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create chat: {str(e)}")

async def get_user_chats(
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
) -> GetChatsResponse:
    """Get user's chats"""
    try:
        current_user_id = get_user_id(current_user)
        chats = await messaging_model.get_user_chats(
            user_id=current_user_id,
            limit=limit,
            skip=skip
        )
        
        # Convert to response format
        chat_items = [
            ChatInfo(
                id=chat["id"],
                type=chat["type"],
                name=chat["name"],
                participants=[UserInfo(**p) for p in chat["participants"]],
                creator_id=chat.get("creator_id"),
                last_message=chat.get("last_message"),
                unread_count=chat["unread_count"],
                is_accessible=chat["is_accessible"],
                settings=chat["settings"],
                created_at=chat["created_at"],
                updated_at=chat["updated_at"]
            )
            for chat in chats
        ]
        
        return GetChatsResponse(
            chats=chat_items,
            total=len(chat_items),
            has_more=len(chat_items) == limit
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chats: {str(e)}")

# Message operations
async def send_message(
    request_data: SendMessageRequest,
    current_user: dict = Depends(get_current_user)
) -> SendMessageResponse:
    """Send a message"""
    try:
        current_user_id = get_user_id(current_user)
        
        # Get chat participants before sending message
        from app.database.mongo_connection import get_database
        db = get_database()
        chats_collection = db.chats
        chat = await chats_collection.find_one({"_id": request_data.chat_id})
        
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        result = await messaging_model.send_message(
            sender_id=current_user_id,
            chat_id=request_data.chat_id,
            content=request_data.content,
            message_type=request_data.message_type,
            reply_to=request_data.reply_to,
            media_url=request_data.media_url
        )
        
        # Send real-time notification to other participants
        await manager.notify_new_message(
            chat_id=request_data.chat_id,
            message_data={
                "message_id": result["message_id"],
                "sender_id": current_user_id,
                "sender_name": current_user.get("full_name", current_user.get("username", "Unknown")),
                "content": request_data.content,
                "message_type": request_data.message_type,
                "timestamp": result["timestamp"],
                "chat_name": chat.get("chat_name") if chat.get("chat_type") == "group" else None
            },
            participants=chat.get("participants", []),
            sender_id=current_user_id
        )
        
        return SendMessageResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

async def get_chat_messages(
    chat_id: str,
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
) -> GetMessagesResponse:
    """Get messages for a chat"""
    try:
        current_user_id = get_user_id(current_user)
        result = await messaging_model.get_chat_messages(
            user_id=current_user_id,
            chat_id=chat_id,
            limit=limit,
            skip=skip
        )
        
        if not result["success"]:
            return GetMessagesResponse(success=False, message=result["message"])
        
        # Convert messages to response format
        message_items = [
            MessageInfo(
                id=msg["id"],
                chat_id=msg["chat_id"],
                sender=UserInfo(**msg["sender"]),
                content=msg["content"],
                type=msg["type"],
                media_url=msg.get("media_url"),
                reply_to=msg.get("reply_to"),
                created_at=msg["created_at"],
                delivery_status=msg.get("delivery_status", "sent"),
                read_by=msg.get("read_by", []),
                reactions=msg.get("reactions", []),
                is_edited=msg.get("is_edited", False),
                is_forwarded=msg.get("is_forwarded", False),
                disappears_at=msg.get("disappears_at")
            )
            for msg in result["messages"]
        ]
        
        return GetMessagesResponse(
            success=True,
            messages=message_items,
            chat=result["chat"]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get messages: {str(e)}")

async def mark_messages_as_read(
    request_data: MarkAsReadRequest,
    current_user: dict = Depends(get_current_user)
) -> MessageActionResponse:
    """Mark messages as read"""
    try:
        result = await messaging_model.mark_messages_as_read(
            user_id=str(current_user["_id"]),
            chat_id=request_data.chat_id
        )
        
        return MessageActionResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mark messages as read: {str(e)}")

async def edit_message(
    request_data: EditMessageRequest,
    current_user: dict = Depends(get_current_user)
) -> MessageActionResponse:
    """Edit a message"""
    try:
        result = await messaging_model.edit_message(
            user_id=str(current_user["_id"]),
            message_id=request_data.message_id,
            new_content=request_data.new_content
        )
        
        return MessageActionResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to edit message: {str(e)}")

async def delete_message(
    message_id: str,
    current_user: dict = Depends(get_current_user)
) -> MessageActionResponse:
    """Delete a message"""
    try:
        result = await messaging_model.delete_message(
            user_id=str(current_user["_id"]),
            message_id=message_id
        )
        
        return MessageActionResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete message: {str(e)}")

# Message reactions
async def add_reaction(
    request_data: AddReactionRequest,
    current_user: dict = Depends(get_current_user)
) -> MessageActionResponse:
    """Add reaction to a message"""
    try:
        # Get message and chat info before adding reaction
        from app.database.mongo_connection import get_database
        db = get_database()
        messages_collection = db.messages
        chats_collection = db.chats
        
        message = await messages_collection.find_one({"_id": request_data.message_id})
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        chat = await chats_collection.find_one({"_id": message["chat_id"]})
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        result = await messaging_model.add_reaction(
            user_id=str(current_user["_id"]),
            message_id=request_data.message_id,
            emoji=request_data.emoji
        )
        
        # Send real-time notification for reaction
        await manager.notify_message_reaction(
            message_id=request_data.message_id,
            reaction_data={
                "user_id": str(current_user["_id"]),
                "user_name": current_user.get("full_name", current_user.get("username", "Unknown")),
                "emoji": request_data.emoji,
                "action": "added"
            },
            participants=chat.get("participants", []),
            sender_id=str(current_user["_id"])
        )
        
        return MessageActionResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add reaction: {str(e)}")

async def remove_reaction(
    message_id: str,
    current_user: dict = Depends(get_current_user)
) -> MessageActionResponse:
    """Remove reaction from a message"""
    try:
        result = await messaging_model.remove_reaction(
            user_id=str(current_user["_id"]),
            message_id=message_id
        )
        
        return MessageActionResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove reaction: {str(e)}")

# Search and utilities
async def search_messages(
    request_data: MessageSearchRequest,
    current_user: dict = Depends(get_current_user)
) -> MessageSearchResponse:
    """Search messages"""
    try:
        results = await messaging_model.search_messages(
            user_id=str(current_user["_id"]),
            query=request_data.query,
            chat_id=request_data.chat_id,
            limit=request_data.limit
        )
        
        # Convert to response format
        search_results = [
            MessageSearchResult(
                message_id=result["message_id"],
                content=result["content"],
                sender=UserInfo(**result["sender"]),
                chat=result["chat"],
                created_at=result["created_at"]
            )
            for result in results
        ]
        
        return MessageSearchResponse(
            results=search_results,
            total=len(search_results)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search messages: {str(e)}")

async def can_message_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
) -> CanMessageResponse:
    """Check if current user can message another user"""
    try:
        result = await messaging_model.can_message_user(
            sender_id=str(current_user["_id"]),
            receiver_id=user_id
        )
        
        return CanMessageResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check messaging permission: {str(e)}")

# Utility function for checking messaging permissions
async def check_can_message(
    sender_id: str,
    receiver_id: str
) -> bool:
    """Utility function to check if users can message each other"""
    try:
        result = await messaging_model.can_message_user(sender_id, receiver_id)
        return result["can_message"]
    except Exception:
        return False
