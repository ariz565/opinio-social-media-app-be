from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

class ConnectionType(str, Enum):
    """Types of connections"""
    STANDARD = "standard"
    CLOSE = "close" 
    PROFESSIONAL = "professional"

class ConnectionStatus(str, Enum):
    """Connection request status"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    BLOCKED = "blocked"

# Request schemas
class ConnectionRequest(BaseModel):
    """Schema for sending connection request"""
    receiver_id: str = Field(..., min_length=1)
    message: Optional[str] = Field(None, max_length=500)
    connection_type: ConnectionType = Field(default=ConnectionType.STANDARD)
    
    @validator('message')
    def validate_message(cls, v):
        if v and len(v.strip()) == 0:
            return None
        return v

class ConnectionResponse(BaseModel):
    """Schema for responding to connection request"""
    connection_id: str = Field(..., min_length=1)
    accept: bool = Field(...)

class RemoveConnectionRequest(BaseModel):
    """Schema for removing connection"""
    connection_id: str = Field(..., min_length=1)

class BlockUserRequest(BaseModel):
    """Schema for blocking user"""
    user_id: str = Field(..., min_length=1)

# Response schemas
class UserInfo(BaseModel):
    """Basic user information"""
    id: str
    username: str
    full_name: str
    profile_picture: Optional[str] = None
    bio: Optional[str] = None
    is_verified: bool = False
    is_online: Optional[bool] = False

class ConnectionRequestInfo(BaseModel):
    """Connection request information"""
    connection_id: str
    user: UserInfo
    message: Optional[str] = None
    connection_type: ConnectionType
    created_at: datetime
    expires_at: Optional[datetime] = None

class ConnectionInfo(BaseModel):
    """Connection information"""
    connection_id: str
    user: UserInfo
    connection_type: ConnectionType
    connected_at: datetime
    mutual_connections: int = 0

class ConnectionStatusInfo(BaseModel):
    """Connection status between two users"""
    status: str  # "none", "pending_sent", "pending_received", "accepted", "rejected", "blocked"
    can_send_request: bool
    connection_id: Optional[str] = None

class MutualConnection(BaseModel):
    """Mutual connection information"""
    id: str
    username: str
    full_name: str
    profile_picture: Optional[str] = None

class ConnectionSuggestion(BaseModel):
    """Connection suggestion"""
    user: UserInfo
    mutual_connections: int
    reason: str

class ConnectionStats(BaseModel):
    """Connection statistics"""
    connections: int = 0
    pending_requests: int = 0

class BlockedUser(BaseModel):
    """Blocked user information"""
    connection_id: str
    user: UserInfo
    blocked_at: datetime

# API Response schemas
class ConnectionRequestResponse(BaseModel):
    """Response for connection request operation"""
    success: bool
    message: str
    connection_id: Optional[str] = None

class ConnectionListResponse(BaseModel):
    """Response for connection list"""
    connections: List[ConnectionInfo]
    total: int
    has_more: bool

class ConnectionRequestListResponse(BaseModel):
    """Response for connection request list"""
    requests: List[ConnectionRequestInfo]
    total: int
    has_more: bool

class ConnectionSuggestionsResponse(BaseModel):
    """Response for connection suggestions"""
    suggestions: List[ConnectionSuggestion]
    total: int

class MutualConnectionsResponse(BaseModel):
    """Response for mutual connections"""
    mutual_connections: List[MutualConnection]
    total: int

class MessageResponse(BaseModel):
    """Generic message response"""
    success: bool
    message: str

class CanMessageResponse(BaseModel):
    """Response for checking if users can message each other"""
    can_message: bool
    reason: Optional[str] = None
    connection_status: str

# Query parameter schemas
class ConnectionListParams(BaseModel):
    """Parameters for listing connections"""
    connection_type: Optional[ConnectionType] = None
    limit: int = Field(default=50, ge=1, le=100)
    skip: int = Field(default=0, ge=0)

class ConnectionRequestParams(BaseModel):
    """Parameters for listing connection requests"""
    incoming: bool = Field(default=True)
    limit: int = Field(default=20, ge=1, le=50)
    skip: int = Field(default=0, ge=0)

class ConnectionSuggestionsParams(BaseModel):
    """Parameters for connection suggestions"""
    limit: int = Field(default=10, ge=1, le=20)

class MutualConnectionsParams(BaseModel):
    """Parameters for mutual connections"""
    user_id: str = Field(..., min_length=1)
    limit: int = Field(default=10, ge=1, le=50)
