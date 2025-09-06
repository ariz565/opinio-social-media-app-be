"""
API functions for connection system
Handles connection requests, acceptance/rejection, and connection management
"""

from typing import List, Optional
from fastapi import HTTPException, Depends, Query
from app.models.connection import connection_model
from app.schemas.connections import (
    ConnectionRequest, ConnectionResponse, RemoveConnectionRequest, BlockUserRequest,
    ConnectionRequestResponse, ConnectionListResponse, ConnectionRequestListResponse,
    ConnectionSuggestionsResponse, MutualConnectionsResponse, MessageResponse,
    ConnectionStatusInfo, ConnectionStats, CanMessageResponse,
    ConnectionListParams, ConnectionRequestParams, ConnectionSuggestionsParams,
    MutualConnectionsParams, ConnectionInfo, ConnectionRequestInfo,
    ConnectionSuggestion, MutualConnection
)
from app.core.auth import get_current_user
from app.core.websocket import manager

def get_user_id(user_dict: dict) -> str:
    """Safely extract user ID from user dict, handling both 'id' and '_id' fields"""
    return str(user_dict.get("id") or user_dict.get("_id") or "")

# Connection request operations
async def send_connection_request(
    request_data: ConnectionRequest,
    current_user: dict = Depends(get_current_user)
) -> ConnectionRequestResponse:
    """Send a connection request to another user"""
    try:
        current_user_id = get_user_id(current_user)
        if not current_user_id:
            raise HTTPException(status_code=400, detail="Invalid user authentication")
            
        result = await connection_model.send_connection_request(
            sender_id=current_user_id,
            receiver_id=request_data.receiver_id,
            message=request_data.message,
            connection_type=request_data.connection_type
        )
        
        # Send real-time notification to receiver
        await manager.notify_connection_request(
            sender_id=current_user_id,
            receiver_id=request_data.receiver_id,
            connection_data={
                "connection_id": result["connection_id"],
                "sender_name": current_user.get("full_name", current_user.get("username", "Unknown")),
                "sender_username": current_user.get("username"),
                "sender_avatar": current_user.get("profile_image"),
                "message": request_data.message,
                "connection_type": request_data.connection_type
            }
        )
        
        return ConnectionRequestResponse(**result)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send connection request: {str(e)}")

async def respond_to_connection_request(
    response_data: ConnectionResponse,
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    """Accept or reject a connection request"""
    try:
        # Get connection details before responding (for notification)
        from app.database.mongo_connection import get_database
        db = await get_database()
        connections_collection = db.connections
        connection = await connections_collection.find_one({"_id": response_data.connection_id})
        
        if not connection:
            raise HTTPException(status_code=404, detail="Connection request not found")
        
        # Get requester ID for notification
        requester_id = connection["sender_id"]
        
        current_user_id = get_user_id(current_user)
        if not current_user_id:
            raise HTTPException(status_code=400, detail="Invalid user authentication")
        
        result = await connection_model.respond_to_connection_request(
            connection_id=response_data.connection_id,
            user_id=current_user_id,
            accept=response_data.accept
        )
        
        # Send real-time notification to requester
        await manager.notify_connection_response(
            responder_id=current_user_id,
            requester_id=requester_id,
            accepted=response_data.accept,
            connection_data={
                "connection_id": response_data.connection_id,
                "responder_name": current_user.get("full_name", current_user.get("username", "Unknown")),
                "responder_username": current_user.get("username"),
                "responder_avatar": current_user.get("profile_image"),
                "status": "accepted" if response_data.accept else "rejected"
            }
        )
        
        return MessageResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to respond to connection request: {str(e)}")

async def get_connection_requests(
    incoming: bool = Query(True, description="Get incoming (True) or outgoing (False) requests"),
    limit: int = Query(20, ge=1, le=50),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
) -> ConnectionRequestListResponse:
    """Get connection requests (incoming or outgoing)"""
    try:
        requests = await connection_model.get_connection_requests(
            user_id=str(current_user["_id"]),
            incoming=incoming,
            limit=limit,
            skip=skip
        )
        
        # Convert to response format
        request_items = [
            ConnectionRequestInfo(
                connection_id=req["connection_id"],
                user=req["user"],
                message=req["message"],
                connection_type=req["connection_type"],
                created_at=req["created_at"],
                expires_at=req.get("expires_at")
            )
            for req in requests
        ]
        
        return ConnectionRequestListResponse(
            requests=request_items,
            total=len(request_items),
            has_more=len(request_items) == limit
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get connection requests: {str(e)}")

# Connection management
async def get_user_connections(
    connection_type: Optional[str] = Query(None, description="Filter by connection type"),
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
) -> ConnectionListResponse:
    """Get user's connections"""
    try:
        connections = await connection_model.get_user_connections(
            user_id=str(current_user["_id"]),
            connection_type=connection_type,
            limit=limit,
            skip=skip
        )
        
        # Convert to response format
        connection_items = [
            ConnectionInfo(
                connection_id=conn["connection_id"],
                user=conn["user"],
                connection_type=conn["connection_type"],
                connected_at=conn["connected_at"],
                mutual_connections=conn["mutual_connections"]
            )
            for conn in connections
        ]
        
        return ConnectionListResponse(
            connections=connection_items,
            total=len(connection_items),
            has_more=len(connection_items) == limit
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get connections: {str(e)}")

async def remove_connection(
    request_data: RemoveConnectionRequest,
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    """Remove a connection"""
    try:
        result = await connection_model.remove_connection(
            user_id=str(current_user["_id"]),
            connection_id=request_data.connection_id
        )
        
        return MessageResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove connection: {str(e)}")

async def get_connection_status(
    user_id: str,
    current_user: dict = Depends(get_current_user)
) -> ConnectionStatusInfo:
    """Get connection status between current user and another user"""
    try:
        # Use 'id' field from current_user (not '_id')
        current_user_id = get_user_id(current_user)
        if not current_user_id:
            print(f"[ERROR] No valid user ID found in current_user: {list(current_user.keys())}")
            raise HTTPException(status_code=400, detail="Invalid user authentication")
            
        print(f"[DEBUG] Connection status check: current_user_id={current_user_id}, target_user_id={user_id}")
        
        status_info = await connection_model.get_connection_status(
            user1_id=current_user_id,
            user2_id=user_id
        )
        
        print(f"[DEBUG] Connection status result: {status_info}")
        return ConnectionStatusInfo(**status_info)
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Connection status error: {str(e)} - current_user_id: {current_user.get('id', 'N/A')}, target_user_id: {user_id}")
        raise HTTPException(status_code=500, detail=f"Failed to get connection status: {str(e)}")

# Blocking functionality
async def block_user(
    request_data: BlockUserRequest,
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    """Block a user"""
    try:
        result = await connection_model.block_user(
            blocker_id=str(current_user["_id"]),
            blocked_id=request_data.user_id
        )
        
        return MessageResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to block user: {str(e)}")

async def unblock_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    """Unblock a user"""
    try:
        result = await connection_model.unblock_user(
            blocker_id=str(current_user["_id"]),
            blocked_id=user_id
        )
        
        return MessageResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unblock user: {str(e)}")

async def get_blocked_users(
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
) -> List[dict]:
    """Get list of blocked users"""
    try:
        blocked_users = await connection_model.get_blocked_users(
            user_id=str(current_user["_id"]),
            limit=limit,
            skip=skip
        )
        
        return blocked_users
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get blocked users: {str(e)}")

# Discovery and suggestions
async def get_connection_suggestions(
    limit: int = Query(10, ge=1, le=20),
    current_user: dict = Depends(get_current_user)
) -> ConnectionSuggestionsResponse:
    """Get connection suggestions based on mutual connections"""
    try:
        suggestions = await connection_model.suggest_connections(
            user_id=str(current_user["_id"]),
            limit=limit
        )
        
        # If no suggestions found, return some users from database for testing
        if not suggestions:
            print(f"[DEBUG] No connection suggestions found, getting users from database")
            from app.database.mongo_connection import get_database
            db = await get_database()
            users_collection = db.users
            
            # Get users excluding current user
            users_cursor = users_collection.find({
                "_id": {"$ne": current_user["_id"]},
                "status": "active"
            }).limit(limit)
            users = await users_cursor.to_list(length=limit)
            
            print(f"[DEBUG] Found {len(users)} users for connection suggestions")
            
            # Convert users to connection suggestions format
            suggestions = []
            for user in users:
                suggestions.append({
                    "user": {
                        "id": str(user["_id"]),
                        "username": user.get("username", ""),
                        "full_name": user.get("full_name", ""),
                        "profile_picture": user.get("profile_picture"),
                        "bio": user.get("bio", ""),
                        "location": user.get("location", ""),
                        "headline": user.get("headline", "")
                    },
                    "mutual_connections": 0,
                    "reason": "suggested_user"
                })
        
        # Convert to response format
        from app.schemas.connections import ConnectionSuggestion
        suggestion_items = [
            ConnectionSuggestion(
                user=sug["user"],
                mutual_connections=sug["mutual_connections"],
                reason=sug["reason"]
            )
            for sug in suggestions
        ]
        
        return ConnectionSuggestionsResponse(
            suggestions=suggestion_items,
            total=len(suggestion_items)
        )
    
    except Exception as e:
        print(f"[DEBUG] Exception in get_connection_suggestions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get connection suggestions: {str(e)}")

async def get_mutual_connections(
    user_id: str,
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
) -> MutualConnectionsResponse:
    """Get mutual connections between current user and another user"""
    try:
        mutual_connections = await connection_model.get_mutual_connections(
            user1_id=str(current_user["_id"]),
            user2_id=user_id,
            limit=limit
        )
        
        # Convert to response format
        mutual_items = [
            MutualConnection(**conn)
            for conn in mutual_connections
        ]
        
        return MutualConnectionsResponse(
            mutual_connections=mutual_items,
            total=len(mutual_items)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get mutual connections: {str(e)}")

async def get_connection_stats(
    current_user: dict = Depends(get_current_user)
) -> ConnectionStats:
    """Get connection statistics for current user"""
    try:
        stats = await connection_model.get_connection_stats(
            user_id=str(current_user["_id"])
        )
        
        return ConnectionStats(**stats)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get connection stats: {str(e)}")

# Messaging permission check
async def can_message_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
) -> CanMessageResponse:
    """Check if current user can message another user"""
    try:
        # Check if users are connected
        are_connected = await connection_model.are_users_connected(
            user1_id=str(current_user["_id"]),
            user2_id=user_id
        )
        
        if are_connected:
            return CanMessageResponse(
                can_message=True,
                connection_status="connected"
            )
        
        # Get connection status for more details
        status_info = await connection_model.get_connection_status(
            user1_id=str(current_user["_id"]),
            user2_id=user_id
        )
        
        # Determine if messaging is allowed and reason
        if status_info["status"] == "blocked":
            return CanMessageResponse(
                can_message=False,
                reason="User is blocked",
                connection_status=status_info["status"]
            )
        elif status_info["status"] == "pending_sent":
            return CanMessageResponse(
                can_message=False,
                reason="Connection request sent, waiting for acceptance",
                connection_status=status_info["status"]
            )
        elif status_info["status"] == "pending_received":
            return CanMessageResponse(
                can_message=False,
                reason="Please accept their connection request first",
                connection_status=status_info["status"]
            )
        else:
            return CanMessageResponse(
                can_message=False,
                reason="You need to be connected to send messages",
                connection_status=status_info["status"]
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check messaging permission: {str(e)}")

# Utility functions for checking connections
async def check_users_connected(
    user1_id: str,
    user2_id: str
) -> bool:
    """Utility function to check if two users are connected (for internal use)"""
    try:
        return await connection_model.are_users_connected(user1_id, user2_id)
    except Exception:
        return False
