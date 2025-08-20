"""
API functions for advanced comments system
Handles nested comments, threading, reactions, and advanced sorting
"""

from typing import List, Optional
from fastapi import HTTPException, Depends
from app.models.comment import comment_model, CommentSortType
from app.schemas.interactions import (
    CommentCreate, CommentUpdate, CommentResponse, 
    CommentListParams, MessageResponse
)
from app.core.auth import get_current_user

async def create_comment(
    comment_data: CommentCreate,
    current_user: dict = Depends(get_current_user)
) -> CommentResponse:
    """
    🔐 Requires Authentication
    Create a new comment or reply to an existing comment
    """
    try:
        # Validate post exists
        from app.models.post import post_model
        post = await post_model.get_post_by_id(comment_data.post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        # Check if replying to a comment that exists
        if comment_data.parent_comment_id:
            parent_comment = await comment_model.get_comment_by_id(
                comment_data.parent_comment_id, 
                include_user=False
            )
            if not parent_comment:
                raise HTTPException(status_code=404, detail="Parent comment not found")
        
        # Create the comment
        comment = await comment_model.create_comment(
            user_id=current_user["_id"],
            post_id=comment_data.post_id,
            content=comment_data.content,
            parent_comment_id=comment_data.parent_comment_id,
            mentions=comment_data.mentions
        )
        
        return CommentResponse(**comment)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create comment: {str(e)}")

async def get_post_comments(
    post_id: str,
    params: CommentListParams = Depends()
) -> List[CommentResponse]:
    """
    Get comments for a post with advanced sorting and threading
    Public endpoint - no authentication required for viewing comments
    """
    try:
        # Validate post exists
        from app.models.post import post_model
        post = await post_model.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        comments = await comment_model.get_post_comments(
            post_id=post_id,
            sort_type=params.sort_type,
            limit=params.limit,
            skip=params.skip,
            max_depth=params.max_depth,
            load_replies=params.load_replies
        )
        
        return [CommentResponse(**comment) for comment in comments]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get comments: {str(e)}")

async def get_comment_by_id(
    comment_id: str
) -> CommentResponse:
    """
    Get a specific comment by ID
    Public endpoint - no authentication required
    """
    try:
        comment = await comment_model.get_comment_by_id(comment_id)
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        return CommentResponse(**comment)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get comment: {str(e)}")

async def update_comment(
    comment_id: str,
    comment_data: CommentUpdate,
    current_user: dict = Depends(get_current_user)
) -> CommentResponse:
    """
    🔐 Requires Authentication
    Update a comment's content (only by the comment author)
    """
    try:
        updated_comment = await comment_model.update_comment(
            comment_id=comment_id,
            user_id=current_user["_id"],
            new_content=comment_data.content
        )
        
        if not updated_comment:
            raise HTTPException(
                status_code=404, 
                detail="Comment not found or you don't have permission to edit it"
            )
        
        return CommentResponse(**updated_comment)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update comment: {str(e)}")

async def delete_comment(
    comment_id: str,
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    """
    🔐 Requires Authentication
    Delete a comment (soft delete - only by comment author or admin)
    """
    try:
        # Check if user is admin
        is_admin = current_user.get("role") == "admin"
        
        success = await comment_model.delete_comment(
            comment_id=comment_id,
            user_id=current_user["_id"],
            is_admin=is_admin
        )
        
        if not success:
            raise HTTPException(
                status_code=404, 
                detail="Comment not found or you don't have permission to delete it"
            )
        
        return MessageResponse(message="Comment deleted successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete comment: {str(e)}")

async def get_comment_thread(
    comment_id: str,
    max_depth: int = 5
) -> CommentResponse:
    """
    Get a complete comment thread starting from a specific comment
    Public endpoint - no authentication required
    """
    try:
        if max_depth < 1 or max_depth > 10:
            raise HTTPException(status_code=400, detail="Max depth must be between 1 and 10")
        
        thread = await comment_model.get_comment_thread(
            comment_id=comment_id,
            max_depth=max_depth
        )
        
        if not thread:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        return CommentResponse(**thread)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get comment thread: {str(e)}")

async def get_comment_replies(
    comment_id: str,
    limit: int = 10,
    sort_type: CommentSortType = CommentSortType.NEWEST
) -> List[CommentResponse]:
    """
    Get direct replies to a specific comment
    Public endpoint - no authentication required
    """
    try:
        # Verify parent comment exists
        parent_comment = await comment_model.get_comment_by_id(comment_id, include_user=False)
        if not parent_comment:
            raise HTTPException(status_code=404, detail="Parent comment not found")
        
        replies = await comment_model._get_comment_replies(
            parent_comment_id=comment_id,
            max_depth=1,  # Only direct replies
            sort_type=sort_type,
            limit=limit
        )
        
        return [CommentResponse(**reply) for reply in replies]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get comment replies: {str(e)}")

async def search_comments(
    post_id: str,
    search_term: str,
    limit: int = 20,
    skip: int = 0
) -> List[CommentResponse]:
    """
    Search comments within a post by content
    Public endpoint - no authentication required
    """
    try:
        if not search_term or len(search_term.strip()) < 2:
            raise HTTPException(status_code=400, detail="Search term must be at least 2 characters")
        
        # Validate post exists
        from app.models.post import post_model
        post = await post_model.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        comments = await comment_model.search_comments(
            post_id=post_id,
            search_term=search_term.strip(),
            limit=limit,
            skip=skip
        )
        
        return [CommentResponse(**comment) for comment in comments]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search comments: {str(e)}")

async def get_user_comments(
    user_id: Optional[str] = None,
    limit: int = 20,
    skip: int = 0,
    include_replies: bool = True,
    current_user: dict = Depends(get_current_user)
) -> List[dict]:
    """
    🔐 Requires Authentication
    Get comments by a specific user (defaults to current user)
    """
    try:
        # Use current user if no user_id provided
        target_user_id = user_id or current_user["_id"]
        
        comments = await comment_model.get_user_comments(
            user_id=target_user_id,
            limit=limit,
            skip=skip,
            include_replies=include_replies
        )
        
        return comments
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user comments: {str(e)}")

async def get_comment_mentions(
    current_user: dict = Depends(get_current_user),
    limit: int = 20,
    skip: int = 0
) -> List[CommentResponse]:
    """
    🔐 Requires Authentication
    Get comments where the current user is mentioned
    """
    try:
        from app.database.mongo_connection import get_database
        db = await get_database()
        
        # Find comments where user is mentioned
        pipeline = [
            {
                "$match": {
                    "mentions": current_user["_id"],
                    "is_deleted": False
                }
            },
            {"$sort": {"created_at": -1}},
            {"$skip": skip},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "user_id",
                    "foreignField": "_id",
                    "as": "user"
                }
            },
            {"$unwind": "$user"},
            {
                "$lookup": {
                    "from": "posts",
                    "localField": "post_id",
                    "foreignField": "_id",
                    "as": "post"
                }
            },
            {"$unwind": "$post"},
            {
                "$project": {
                    "_id": {"$toString": "$_id"},
                    "user_id": 1,
                    "post_id": 1,
                    "content": 1,
                    "depth": 1,
                    "reactions": 1,
                    "reply_count": 1,
                    "is_edited": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "user": {
                        "username": "$user.username",
                        "full_name": "$user.full_name",
                        "profile_picture": "$user.profile_picture",
                        "is_verified": "$user.is_verified"
                    },
                    "post": {
                        "_id": {"$toString": "$post._id"},
                        "content": "$post.content"
                    }
                }
            }
        ]
        
        comments = await db.comments.aggregate(pipeline).to_list(length=None)
        return [CommentResponse(**comment) for comment in comments]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get mentions: {str(e)}")

async def get_comment_analytics(
    post_id: str,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    🔐 Requires Authentication
    Get comment analytics for a post (post owner only)
    """
    try:
        # Verify post ownership
        from app.models.post import post_model
        post = await post_model.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        if post["user_id"] != current_user["_id"]:
            raise HTTPException(status_code=403, detail="Not authorized to view analytics")
        
        from app.database.mongo_connection import get_database
        db = await get_database()
        
        # Get comment analytics
        pipeline = [
            {
                "$match": {
                    "post_id": post_id,
                    "is_deleted": False
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_comments": {"$sum": 1},
                    "top_level_comments": {
                        "$sum": {"$cond": [{"$eq": ["$depth", 0]}, 1, 0]}
                    },
                    "replies": {
                        "$sum": {"$cond": [{"$gt": ["$depth", 0]}, 1, 0]}
                    },
                    "total_reactions": {"$sum": "$reactions.total"},
                    "avg_depth": {"$avg": "$depth"},
                    "max_depth": {"$max": "$depth"}
                }
            }
        ]
        
        analytics = await db.comments.aggregate(pipeline).to_list(length=1)
        
        if not analytics:
            return {
                "total_comments": 0,
                "top_level_comments": 0,
                "replies": 0,
                "total_reactions": 0,
                "avg_depth": 0,
                "max_depth": 0
            }
        
        return analytics[0]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get comment analytics: {str(e)}")
