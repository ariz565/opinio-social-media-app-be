"""
API functions for sharing system
Handles reposts, story sharing, direct messages, and external sharing
"""

from typing import List, Optional
from fastapi import HTTPException, Depends
from app.models.share import share_model, ShareType
from app.schemas.interactions import (
    ShareCreate, ShareResponse, UserShareResponse, RepostFeedItem,
    ShareAnalytics, TrendingShare, MessageResponse
)
from app.core.auth import get_current_user

async def share_post(
    share_data: ShareCreate,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    🔐 Requires Authentication
    Share a post with various options (repost, story, DM, external)
    """
    try:
        # Validate post exists
        from app.models.post import post_model
        post = await post_model.get_post_by_id(share_data.post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        # Cannot share own post as repost
        if (share_data.share_type in [ShareType.REPOST, ShareType.REPOST_WITH_COMMENT] 
            and post["user_id"] == current_user["_id"]):
            raise HTTPException(status_code=400, detail="Cannot repost your own post")
        
        # Validate recipients for direct message sharing
        if share_data.share_type == ShareType.DIRECT_MESSAGE:
            if not share_data.recipient_ids:
                raise HTTPException(status_code=400, detail="Recipients required for direct message sharing")
            
            # Validate recipients exist and are not blocked
            from app.models.user import user_model
            from app.models.follow import follow_model
            
            for recipient_id in share_data.recipient_ids:
                recipient = await user_model.get_user_by_id(recipient_id)
                if not recipient:
                    raise HTTPException(status_code=404, detail=f"Recipient {recipient_id} not found")
                
                # Check if blocked
                is_blocked = await follow_model.is_user_blocked(recipient_id, current_user["_id"])
                if is_blocked:
                    raise HTTPException(status_code=403, detail=f"Cannot send message to {recipient['username']}")
        
        result = await share_model.share_post(
            user_id=current_user["_id"],
            original_post_id=share_data.post_id,
            share_type=share_data.share_type,
            comment=share_data.comment,
            recipient_ids=share_data.recipient_ids,
            story_settings=share_data.story_settings
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to share post: {str(e)}")

async def get_post_shares(
    post_id: str,
    share_type: Optional[str] = None,
    limit: int = 20,
    skip: int = 0
) -> List[ShareResponse]:
    """
    Get shares for a specific post
    Public endpoint - no authentication required
    """
    try:
        # Validate post exists
        from app.models.post import post_model
        post = await post_model.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        # Convert string to enum if provided
        share_enum = None
        if share_type:
            try:
                share_enum = ShareType(share_type)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid share type")
        
        shares = await share_model.get_post_shares(
            post_id=post_id,
            share_type=share_enum,
            limit=limit,
            skip=skip
        )
        
        return [ShareResponse(**share) for share in shares]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get post shares: {str(e)}")

async def get_user_shares(
    user_id: Optional[str] = None,
    share_type: Optional[str] = None,
    limit: int = 20,
    skip: int = 0,
    current_user: dict = Depends(get_current_user)
) -> List[UserShareResponse]:
    """
    🔐 Requires Authentication
    Get shares made by a specific user (defaults to current user)
    """
    try:
        # Use current user if no user_id provided
        target_user_id = user_id or current_user["_id"]
        
        # If viewing another user's shares, check privacy
        if target_user_id != current_user["_id"]:
            from app.models.user import user_model
            from app.models.follow import follow_model
            
            target_user = await user_model.get_user_by_id(target_user_id)
            if not target_user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Check if account is private and user is not following
            if target_user.get("is_private_account", False):
                follow_status = await follow_model.get_follow_status(
                    follower_id=current_user["_id"],
                    following_id=target_user_id
                )
                if follow_status != "accepted":
                    raise HTTPException(status_code=403, detail="This account is private")
        
        # Convert string to enum if provided
        share_enum = None
        if share_type:
            try:
                share_enum = ShareType(share_type)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid share type")
        
        shares = await share_model.get_user_shares(
            user_id=target_user_id,
            share_type=share_enum,
            limit=limit,
            skip=skip
        )
        
        return [UserShareResponse(**share) for share in shares]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user shares: {str(e)}")

async def get_reposts_feed(
    limit: int = 20,
    skip: int = 0,
    current_user: dict = Depends(get_current_user)
) -> List[RepostFeedItem]:
    """
    🔐 Requires Authentication
    Get reposts from users that the current user follows
    """
    try:
        reposts = await share_model.get_reposts_feed(
            user_id=current_user["_id"],
            limit=limit,
            skip=skip
        )
        
        return [RepostFeedItem(**repost) for repost in reposts]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get reposts feed: {str(e)}")

async def delete_share(
    share_id: str,
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    """
    🔐 Requires Authentication
    Delete a share (and associated repost if applicable)
    """
    try:
        success = await share_model.delete_share(
            share_id=share_id,
            user_id=current_user["_id"]
        )
        
        if not success:
            raise HTTPException(
                status_code=404, 
                detail="Share not found or you don't have permission to delete it"
            )
        
        return MessageResponse(message="Share deleted successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete share: {str(e)}")

async def get_share_analytics(
    post_id: str,
    current_user: dict = Depends(get_current_user)
) -> ShareAnalytics:
    """
    🔐 Requires Authentication
    Get sharing analytics for a post (post owner only)
    """
    try:
        # Verify post ownership
        from app.models.post import post_model
        post = await post_model.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        if post["user_id"] != current_user["_id"]:
            raise HTTPException(status_code=403, detail="Not authorized to view analytics")
        
        analytics = await share_model.get_share_analytics(post_id)
        return ShareAnalytics(**analytics)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get share analytics: {str(e)}")

async def get_trending_shares(
    days: int = 7,
    limit: int = 10
) -> List[TrendingShare]:
    """
    Get most shared posts in the last N days
    Public endpoint - no authentication required
    """
    try:
        if days < 1 or days > 30:
            raise HTTPException(status_code=400, detail="Days must be between 1 and 30")
        
        trending = await share_model.get_trending_shares(
            days=days,
            limit=limit
        )
        
        return [TrendingShare(**share) for share in trending]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trending shares: {str(e)}")

async def get_user_share_count(
    user_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    🔐 Requires Authentication
    Get share count for a user
    """
    try:
        target_user_id = user_id or current_user["_id"]
        
        from app.database.mongo_connection import get_database
        db = await get_database()
        
        # Get share counts by type
        pipeline = [
            {"$match": {"user_id": target_user_id}},
            {
                "$group": {
                    "_id": "$share_type",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        results = await db.shares.aggregate(pipeline).to_list(length=None)
        
        # Initialize counts
        counts = {
            "total_shares": 0,
            "reposts": 0,
            "reposts_with_comment": 0,
            "story_shares": 0,
            "direct_message_shares": 0,
            "external_shares": 0
        }
        
        # Map results
        share_type_map = {
            "repost": "reposts",
            "repost_with_comment": "reposts_with_comment",
            "story": "story_shares",
            "direct_message": "direct_message_shares",
            "external": "external_shares"
        }
        
        for result in results:
            share_type = result["_id"]
            count = result["count"]
            counts["total_shares"] += count
            
            if share_type in share_type_map:
                counts[share_type_map[share_type]] = count
        
        return counts
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get share count: {str(e)}")

async def check_user_shared_post(
    post_id: str,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    🔐 Requires Authentication
    Check if current user has shared a specific post
    """
    try:
        from app.database.mongo_connection import get_database
        db = await get_database()
        
        # Check if user has shared this post
        share = await db.shares.find_one({
            "user_id": current_user["_id"],
            "original_post_id": post_id
        })
        
        if share:
            return {
                "has_shared": True,
                "share_type": share["share_type"],
                "shared_at": share["created_at"]
            }
        else:
            return {"has_shared": False}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check share status: {str(e)}")

async def get_repost_by_id(
    repost_id: str,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    🔐 Requires Authentication
    Get a specific repost with original post details
    """
    try:
        from app.database.mongo_connection import get_database
        db = await get_database()
        
        # Get repost with original post and user details
        pipeline = [
            {"$match": {"_id": repost_id, "post_type": "repost"}},
            {
                "$lookup": {
                    "from": "posts",
                    "localField": "original_post_id",
                    "foreignField": "_id",
                    "as": "original_post"
                }
            },
            {"$unwind": "$original_post"},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "user_id",
                    "foreignField": "_id",
                    "as": "reposter"
                }
            },
            {"$unwind": "$reposter"},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "original_author_id",
                    "foreignField": "_id",
                    "as": "original_author"
                }
            },
            {"$unwind": "$original_author"},
            {
                "$project": {
                    "_id": {"$toString": "$_id"},
                    "content": 1,
                    "created_at": 1,
                    "like_count": 1,
                    "comment_count": 1,
                    "share_count": 1,
                    "reposter": {
                        "_id": {"$toString": "$reposter._id"},
                        "username": "$reposter.username",
                        "full_name": "$reposter.full_name",
                        "profile_picture": "$reposter.profile_picture",
                        "is_verified": "$reposter.is_verified"
                    },
                    "original_post": {
                        "_id": {"$toString": "$original_post._id"},
                        "content": "$original_post.content",
                        "media_urls": "$original_post.media_urls",
                        "post_type": "$original_post.post_type",
                        "created_at": "$original_post.created_at",
                        "like_count": "$original_post.like_count",
                        "comment_count": "$original_post.comment_count"
                    },
                    "original_author": {
                        "_id": {"$toString": "$original_author._id"},
                        "username": "$original_author.username",
                        "full_name": "$original_author.full_name",
                        "profile_picture": "$original_author.profile_picture",
                        "is_verified": "$original_author.is_verified"
                    }
                }
            }
        ]
        
        reposts = await db.posts.aggregate(pipeline).to_list(length=1)
        
        if not reposts:
            raise HTTPException(status_code=404, detail="Repost not found")
        
        return reposts[0]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get repost: {str(e)}")
