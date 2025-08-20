"""
API functions for follow system and social connections
Handles following, followers, connection management, and privacy controls
"""

from typing import List, Optional
from fastapi import HTTPException, Depends
from app.models.follow import follow_model, FollowStatus
from app.schemas.interactions import (
    FollowResponse, FollowRequestResponse, FollowerResponse, FollowingResponse,
    FollowRequestItem, MutualConnection, FriendSuggestion, UserConnections,
    FollowListParams, MessageResponse
)
from app.core.auth import get_current_user

# Follow/Unfollow Operations
async def follow_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
) -> FollowResponse:
    """
    🔐 Requires Authentication
    Follow a user or send follow request for private accounts
    """
    try:
        if user_id == current_user["_id"]:
            raise HTTPException(status_code=400, detail="Cannot follow yourself")
        
        # Check if target user exists and get privacy settings
        from app.models.user import user_model
        target_user = await user_model.get_user_by_id(user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        is_private = target_user.get("is_private_account", False)
        
        result = await follow_model.follow_user(
            follower_id=current_user["_id"],
            following_id=user_id,
            is_private_account=is_private
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return FollowResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to follow user: {str(e)}")

async def unfollow_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    """
    🔐 Requires Authentication
    Unfollow a user or cancel follow request
    """
    try:
        if user_id == current_user["_id"]:
            raise HTTPException(status_code=400, detail="Cannot unfollow yourself")
        
        success = await follow_model.unfollow_user(
            follower_id=current_user["_id"],
            following_id=user_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Not following this user")
        
        return MessageResponse(message="Successfully unfollowed user")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unfollow user: {str(e)}")

# Follow Request Management
async def respond_to_follow_request(
    request_data: FollowRequestResponse,
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    """
    🔐 Requires Authentication
    Accept or decline a follow request
    """
    try:
        result = await follow_model.respond_to_follow_request(
            request_id=request_data.request_id,
            user_id=current_user["_id"],
            accept=request_data.accept
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return MessageResponse(message=result["message"])
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to respond to follow request: {str(e)}")

async def get_follow_requests(
    incoming: bool = True,
    params: FollowListParams = Depends(),
    current_user: dict = Depends(get_current_user)
) -> List[FollowRequestItem]:
    """
    🔐 Requires Authentication
    Get pending follow requests (incoming or outgoing)
    """
    try:
        requests = await follow_model.get_follow_requests(
            user_id=current_user["_id"],
            incoming=incoming,
            limit=params.limit,
            skip=params.skip
        )
        
        return [FollowRequestItem(**request) for request in requests]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get follow requests: {str(e)}")

# Followers and Following
async def get_user_followers(
    user_id: str,
    params: FollowListParams = Depends(),
    current_user: dict = Depends(get_current_user)
) -> List[FollowerResponse]:
    """
    🔐 Requires Authentication
    Get user's followers list
    """
    try:
        # Check if user exists
        from app.models.user import user_model
        target_user = await user_model.get_user_by_id(user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check privacy - only allow if public profile or user is following/same user
        if target_user.get("is_private_account", False) and user_id != current_user["_id"]:
            # Check if current user is following target user
            follow_status = await follow_model.get_follow_status(
                follower_id=current_user["_id"],
                following_id=user_id
            )
            if follow_status != FollowStatus.ACCEPTED.value:
                raise HTTPException(status_code=403, detail="This account is private")
        
        followers = await follow_model.get_followers(
            user_id=user_id,
            limit=params.limit,
            skip=params.skip,
            search_term=params.search_term
        )
        
        return [FollowerResponse(**follower) for follower in followers]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get followers: {str(e)}")

async def get_user_following(
    user_id: str,
    params: FollowListParams = Depends(),
    current_user: dict = Depends(get_current_user)
) -> List[FollowingResponse]:
    """
    🔐 Requires Authentication
    Get users that a user is following
    """
    try:
        # Check if user exists
        from app.models.user import user_model
        target_user = await user_model.get_user_by_id(user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check privacy - only allow if public profile or user is following/same user
        if target_user.get("is_private_account", False) and user_id != current_user["_id"]:
            # Check if current user is following target user
            follow_status = await follow_model.get_follow_status(
                follower_id=current_user["_id"],
                following_id=user_id
            )
            if follow_status != FollowStatus.ACCEPTED.value:
                raise HTTPException(status_code=403, detail="This account is private")
        
        following = await follow_model.get_following(
            user_id=user_id,
            limit=params.limit,
            skip=params.skip,
            search_term=params.search_term
        )
        
        return [FollowingResponse(**follow) for follow in following]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get following: {str(e)}")

# Connection Management
async def add_to_close_friends(
    user_id: str,
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    """
    🔐 Requires Authentication
    Add user to close friends list
    """
    try:
        if user_id == current_user["_id"]:
            raise HTTPException(status_code=400, detail="Cannot add yourself to close friends")
        
        success = await follow_model.add_to_close_friends(
            user_id=current_user["_id"],
            friend_id=user_id
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="User is not following you or doesn't exist")
        
        return MessageResponse(message="User added to close friends")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add to close friends: {str(e)}")

async def remove_from_close_friends(
    user_id: str,
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    """
    🔐 Requires Authentication
    Remove user from close friends list
    """
    try:
        success = await follow_model.remove_from_close_friends(
            user_id=current_user["_id"],
            friend_id=user_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="User not in close friends list")
        
        return MessageResponse(message="User removed from close friends")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove from close friends: {str(e)}")

async def block_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    """
    🔐 Requires Authentication
    Block a user
    """
    try:
        if user_id == current_user["_id"]:
            raise HTTPException(status_code=400, detail="Cannot block yourself")
        
        success = await follow_model.block_user(
            user_id=current_user["_id"],
            blocked_user_id=user_id
        )
        
        return MessageResponse(message="User blocked successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to block user: {str(e)}")

async def unblock_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    """
    🔐 Requires Authentication
    Unblock a user
    """
    try:
        success = await follow_model.unblock_user(
            user_id=current_user["_id"],
            blocked_user_id=user_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="User not blocked")
        
        return MessageResponse(message="User unblocked successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unblock user: {str(e)}")

async def mute_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    """
    🔐 Requires Authentication
    Mute a user
    """
    try:
        if user_id == current_user["_id"]:
            raise HTTPException(status_code=400, detail="Cannot mute yourself")
        
        success = await follow_model.mute_user(
            user_id=current_user["_id"],
            muted_user_id=user_id
        )
        
        return MessageResponse(message="User muted successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mute user: {str(e)}")

async def unmute_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    """
    🔐 Requires Authentication
    Unmute a user
    """
    try:
        success = await follow_model.unmute_user(
            user_id=current_user["_id"],
            muted_user_id=user_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="User not muted")
        
        return MessageResponse(message="User unmuted successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unmute user: {str(e)}")

async def restrict_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    """
    🔐 Requires Authentication
    Restrict a user (limited interactions)
    """
    try:
        if user_id == current_user["_id"]:
            raise HTTPException(status_code=400, detail="Cannot restrict yourself")
        
        success = await follow_model.restrict_user(
            user_id=current_user["_id"],
            restricted_user_id=user_id
        )
        
        return MessageResponse(message="User restricted successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restrict user: {str(e)}")

async def unrestrict_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    """
    🔐 Requires Authentication
    Remove restriction from a user
    """
    try:
        success = await follow_model.unrestrict_user(
            user_id=current_user["_id"],
            restricted_user_id=user_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="User not restricted")
        
        return MessageResponse(message="User restriction removed successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unrestrict user: {str(e)}")

# Connection Information
async def get_user_connections(
    current_user: dict = Depends(get_current_user)
) -> UserConnections:
    """
    🔐 Requires Authentication
    Get all user connections (close friends, blocked, muted, restricted)
    """
    try:
        connections = await follow_model.get_user_connections(current_user["_id"])
        return UserConnections(**connections)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get connections: {str(e)}")

async def get_follow_status(
    user_id: str,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    🔐 Requires Authentication
    Get follow status with another user
    """
    try:
        # Get follow status in both directions
        following_status = await follow_model.get_follow_status(
            follower_id=current_user["_id"],
            following_id=user_id
        )
        
        followed_by_status = await follow_model.get_follow_status(
            follower_id=user_id,
            following_id=current_user["_id"]
        )
        
        # Check connection types
        is_close_friend = await follow_model.is_close_friend(
            user_id=current_user["_id"],
            other_user_id=user_id
        )
        
        is_blocked = await follow_model.is_user_blocked(
            user_id=current_user["_id"],
            other_user_id=user_id
        )
        
        is_muted = await follow_model.is_user_muted(
            user_id=current_user["_id"],
            other_user_id=user_id
        )
        
        return {
            "following": following_status,
            "followed_by": followed_by_status,
            "is_close_friend": is_close_friend,
            "is_blocked": is_blocked,
            "is_muted": is_muted
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get follow status: {str(e)}")

# Discovery and Suggestions
async def get_mutual_connections(
    user_id: str,
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
) -> List[MutualConnection]:
    """
    🔐 Requires Authentication
    Get mutual followers between current user and target user
    """
    try:
        if user_id == current_user["_id"]:
            raise HTTPException(status_code=400, detail="Cannot get mutual connections with yourself")
        
        mutual = await follow_model.get_mutual_connections(
            user_id=current_user["_id"],
            other_user_id=user_id,
            limit=limit
        )
        
        return [MutualConnection(**connection) for connection in mutual]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get mutual connections: {str(e)}")

async def get_friend_suggestions(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
) -> List[FriendSuggestion]:
    """
    🔐 Requires Authentication
    Get friend suggestions based on mutual connections
    """
    try:
        suggestions = await follow_model.get_friend_suggestions(
            user_id=current_user["_id"],
            limit=limit
        )
        
        return [FriendSuggestion(**suggestion) for suggestion in suggestions]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get friend suggestions: {str(e)}")
