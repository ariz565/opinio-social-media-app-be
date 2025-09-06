from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

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

# Request schemas
class CreateChatRequest(BaseModel):
    """Schema for creating a new chat"""
    participant_ids: List[str] = Field(..., min_items=1, max_items=50)
    chat_type: ChatType = Field(default=ChatType.DIRECT)
    chat_name: Optional[str] = Field(None, max_length=100)
    
    @validator('participant_ids')
    def validate_participants(cls, v):
        if len(set(v)) != len(v):
            raise ValueError('Duplicate participant IDs not allowed')
        return v
    
    @validator('chat_name')
    def validate_chat_name(cls, v, values):
        if values.get('chat_type') == ChatType.GROUP and not v:
            raise ValueError('Group chats must have a name')
        return v

class SendMessageRequest(BaseModel):
    """Schema for sending a message"""
    chat_id: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1, max_length=2000)
    message_type: MessageType = Field(default=MessageType.TEXT)
    reply_to: Optional[str] = Field(None, min_length=1)
    media_url: Optional[str] = Field(None, max_length=500)

class EditMessageRequest(BaseModel):
    """Schema for editing a message"""
    message_id: str = Field(..., min_length=1)
    new_content: str = Field(..., min_length=1, max_length=2000)

class AddReactionRequest(BaseModel):
    """Schema for adding reaction to message"""
    message_id: str = Field(..., min_length=1)
    emoji: str = Field(..., min_length=1, max_length=10)

class MarkAsReadRequest(BaseModel):
    """Schema for marking messages as read"""
    chat_id: str = Field(..., min_length=1)

class MessageSearchRequest(BaseModel):
    """Schema for searching messages"""
    query: str = Field(..., min_length=1, max_length=100)
    chat_id: Optional[str] = Field(None, min_length=1)
    limit: int = Field(default=20, ge=1, le=50)

# Response schemas
class UserInfo(BaseModel):
    """Basic user information"""
    id: str
    username: str
    full_name: str
    profile_picture: Optional[str] = None
    is_online: bool = False

class MessageReaction(BaseModel):
    """Message reaction"""
    emoji: str
    user_id: str
    timestamp: datetime

class MessageInfo(BaseModel):
    """Message information"""
    id: str
    chat_id: str
    sender: UserInfo
    content: str
    type: MessageType
    media_url: Optional[str] = None
    reply_to: Optional[str] = None
    created_at: datetime
    delivery_status: DeliveryStatus
    read_by: List[str] = []
    reactions: List[MessageReaction] = []
    is_edited: bool = False
    is_forwarded: bool = False
    disappears_at: Optional[datetime] = None

class LastMessage(BaseModel):
    """Last message in chat"""
    content: str
    sender_id: str
    timestamp: datetime
    type: MessageType

class ChatSettings(BaseModel):
    """Chat settings"""
    encryption: bool = True
    disappearing_messages: bool = False
    muted_by: List[str] = []

class ChatInfo(BaseModel):
    """Chat information"""
    id: str
    type: ChatType
    name: Optional[str] = None
    participants: List[UserInfo]
    creator_id: Optional[str] = None
    last_message: Optional[LastMessage] = None
    unread_count: int = 0
    is_accessible: bool = True
    settings: ChatSettings = ChatSettings()
    created_at: datetime
    updated_at: datetime

class MessageSearchResult(BaseModel):
    """Message search result"""
    message_id: str
    content: str
    sender: UserInfo
    chat: Dict[str, Any]
    created_at: datetime

# API Response schemas
class CreateChatResponse(BaseModel):
    """Response for chat creation"""
    success: bool
    message: str
    chat_id: str
    existing: bool = False

class SendMessageResponse(BaseModel):
    """Response for sending message"""
    success: bool
    message: str
    message_id: Optional[str] = None

class GetChatsResponse(BaseModel):
    """Response for getting user chats"""
    chats: List[ChatInfo]
    total: int
    has_more: bool

class GetMessagesResponse(BaseModel):
    """Response for getting chat messages"""
    success: bool
    messages: List[MessageInfo] = []
    chat: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

class MessageSearchResponse(BaseModel):
    """Response for message search"""
    results: List[MessageSearchResult]
    total: int

class MessageActionResponse(BaseModel):
    """Generic response for message actions"""
    success: bool
    message: str

class CanMessageResponse(BaseModel):
    """Response for checking if user can message another"""
    can_message: bool
    reason: str

# Query parameter schemas
class GetChatsParams(BaseModel):
    """Parameters for getting chats"""
    limit: int = Field(default=50, ge=1, le=100)
    skip: int = Field(default=0, ge=0)

class GetMessagesParams(BaseModel):
    """Parameters for getting messages"""
    limit: int = Field(default=50, ge=1, le=100)
    skip: int = Field(default=0, ge=0)
