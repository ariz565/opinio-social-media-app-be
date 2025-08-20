from typing import List, Optional
from fastapi import HTTPException, Depends, Query, Body, UploadFile, File
from app.services.post_service import PostService
from app.schemas.post import (
    PostCreate, PostUpdate, PostResponse, PostListResponse,
    PostSchedule, DraftSave, PostSearchQuery, PollVote, PostStats
)
from app.core.exceptions import (
    PostNotFoundError, UnauthorizedError, ValidationError,
    ContentModerationError
)
from app.api.deps import get_current_user

# Initialize service
post_service = PostService()

async def create_post_logic(
    post_data: PostCreate,
    current_user: dict = Depends(get_current_user)
) -> PostResponse:
    """Create a new post"""
    try:
        return await post_service.create_post(str(current_user["_id"]), post_data)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ContentModerationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create post")

async def save_draft_logic(
    draft_data: DraftSave,
    current_user: dict = Depends(get_current_user)
) -> PostResponse:
    """Save post as draft"""
    try:
        return await post_service.save_draft(str(current_user["_id"]), draft_data)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to save draft")

async def publish_draft_logic(
    draft_id: str,
    schedule_data: Optional[PostSchedule] = None,
    current_user: dict = Depends(get_current_user)
) -> PostResponse:
    """Publish a draft post"""
    try:
        return await post_service.publish_draft(
            str(current_user["_id"]), draft_id, schedule_data
        )
    except PostNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to publish draft")

async def update_post_logic(
    post_id: str,
    update_data: PostUpdate,
    current_user: dict = Depends(get_current_user)
) -> PostResponse:
    """Update an existing post"""
    try:
        return await post_service.update_post(
            str(current_user["_id"]), post_id, update_data
        )
    except PostNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update post")

async def delete_post_logic(
    post_id: str,
    permanent: bool = False,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Delete a post"""
    try:
        success = await post_service.delete_post(
            str(current_user["_id"]), post_id, permanent
        )
        if success:
            return {"message": "Post deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete post")
    except PostNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete post")

async def get_post_logic(
    post_id: str,
    current_user: Optional[dict] = None
) -> PostResponse:
    """Get a single post"""
    try:
        user_id = str(current_user["_id"]) if current_user else None
        return await post_service.get_post(post_id, user_id)
    except PostNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get post")

async def get_user_posts_logic(
    user_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Posts per page"),
    include_drafts: bool = Query(False, description="Include draft posts"),
    current_user: Optional[dict] = None
) -> PostListResponse:
    """Get posts by a specific user"""
    try:
        requesting_user_id = str(current_user["_id"]) if current_user else None
        return await post_service.get_user_posts(
            user_id, requesting_user_id, page, per_page, include_drafts
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get user posts")

async def get_feed_logic(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Posts per page"),
    current_user: dict = Depends(get_current_user)
) -> PostListResponse:
    """Get personalized feed for user"""
    try:
        return await post_service.get_feed(str(current_user["_id"]), page, per_page)
    except UnauthorizedError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get feed")

async def pin_post_logic(
    post_id: str,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Pin a post to user's profile"""
    try:
        success = await post_service.pin_post(str(current_user["_id"]), post_id)
        if success:
            return {"message": "Post pinned successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to pin post")
    except PostNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to pin post")

async def unpin_post_logic(
    post_id: str,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Unpin a post from user's profile"""
    try:
        success = await post_service.unpin_post(str(current_user["_id"]), post_id)
        if success:
            return {"message": "Post unpinned successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to unpin post")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to unpin post")

async def get_user_drafts_logic(
    current_user: dict = Depends(get_current_user)
) -> List[PostResponse]:
    """Get all drafts for the current user"""
    try:
        return await post_service.get_user_drafts(str(current_user["_id"]))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get drafts")

async def search_posts_logic(
    query: str = Query(..., min_length=1, max_length=100, description="Search query"),
    post_type: Optional[str] = Query(None, description="Filter by post type"),
    hashtags: Optional[str] = Query(None, description="Comma-separated hashtags"),
    location: Optional[str] = Query(None, description="Filter by location"),
    date_from: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Posts per page"),
    current_user: Optional[dict] = None
) -> PostListResponse:
    """Search posts with filters"""
    try:
        # Parse hashtags
        hashtag_list = []
        if hashtags:
            hashtag_list = [tag.strip() for tag in hashtags.split(",")]

        # Parse dates
        date_from_parsed = None
        date_to_parsed = None
        if date_from:
            from datetime import datetime
            date_from_parsed = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        if date_to:
            from datetime import datetime
            date_to_parsed = datetime.fromisoformat(date_to.replace('Z', '+00:00'))

        # Create search query
        search_query = PostSearchQuery(
            query=query,
            post_type=post_type,
            hashtags=hashtag_list,
            location=location,
            date_from=date_from_parsed,
            date_to=date_to_parsed,
            sort_by=sort_by,
            sort_order=sort_order
        )

        requesting_user_id = str(current_user["_id"]) if current_user else None
        return await post_service.search_posts(search_query, requesting_user_id, page, per_page)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to search posts")

async def get_trending_posts_logic(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back for trending"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of posts")
) -> List[PostResponse]:
    """Get trending posts"""
    try:
        return await post_service.get_trending_posts(hours, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get trending posts")

async def vote_on_poll_logic(
    post_id: str,
    vote_data: PollVote,
    current_user: dict = Depends(get_current_user)
) -> PostResponse:
    """Vote on a poll"""
    try:
        return await post_service.vote_on_poll(str(current_user["_id"]), post_id, vote_data)
    except PostNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to vote on poll")

async def get_user_stats_logic(
    user_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
) -> PostStats:
    """Get user's post statistics"""
    try:
        # If no user_id provided, get stats for current user
        target_user_id = user_id or str(current_user["_id"])
        return await post_service.get_user_stats(target_user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get user stats")

# Background task functions
async def publish_scheduled_posts_logic() -> dict:
    """Background task to publish scheduled posts"""
    try:
        published_count = await post_service.publish_scheduled_posts()
        return {"published_posts": published_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to publish scheduled posts")

# Additional utility functions
async def get_post_edit_history_logic(
    post_id: str,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Get edit history for a post"""
    try:
        post = await post_service.get_post(post_id, str(current_user["_id"]))
        
        # Only post author can view edit history
        if post.user_id != str(current_user["_id"]):
            raise HTTPException(status_code=403, detail="You can only view edit history of your own posts")
        
        return {"edit_history": post.edit_history}
    except PostNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get edit history")

async def archive_post_logic(
    post_id: str,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Archive a post (same as soft delete)"""
    return await delete_post_logic(post_id, False, current_user)

async def restore_post_logic(
    post_id: str,
    current_user: dict = Depends(get_current_user)
) -> PostResponse:
    """Restore an archived post"""
    try:
        post_update = PostUpdate(edit_reason="Post restored from archive")
        # This would need a restore method in the service
        # For now, we'll use update to change status back to published
        return await post_service.update_post(
            str(current_user["_id"]), post_id, post_update
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to restore post")

async def get_post_analytics_logic(
    post_id: str,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Get detailed analytics for a specific post"""
    try:
        post = await post_service.get_post(post_id, str(current_user["_id"]))
        
        # Only post author can view detailed analytics
        if post.user_id != str(current_user["_id"]):
            raise HTTPException(status_code=403, detail="You can only view analytics of your own posts")
        
        # Return engagement stats and additional analytics
        return {
            "post_id": post_id,
            "engagement_stats": post.engagement_stats.dict(),
            "created_at": post.created_at,
            "last_updated": post.updated_at,
            "visibility": post.visibility,
            "post_type": post.post_type,
            "has_media": len(post.media) > 0,
            "hashtag_count": len(post.hashtags),
            "mention_count": len(post.mentions),
            "edit_count": len(post.edit_history)
        }
    except PostNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get post analytics")

async def upload_media_logic(
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Upload media files for posts"""
    try:
        # Validate file count
        if len(files) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 files allowed")
        
        # Upload media
        media_data = await post_service.upload_post_media(
            files=files,
            user_id=str(current_user["_id"])
        )
        
        return {
            "message": "Media uploaded successfully",
            "media_count": len(media_data),
            "media": media_data
        }
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to upload media")

async def upload_post_media_logic(
    post_id: str,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
) -> PostResponse:
    """Upload media files for a specific post"""
    try:
        # Upload media with post ID
        media_data = await post_service.upload_post_media(
            files=files,
            user_id=str(current_user["_id"]),
            post_id=post_id
        )
        
        # Update post with media
        updated_post = await post_service.update_post_with_media(
            post_id=post_id,
            user_id=str(current_user["_id"]),
            media_data=media_data
        )
        
        return PostResponse(**updated_post)
    except PostNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to upload media to post")

async def create_post_with_media_logic(
    content: str = Body(...),
    post_type: str = Body(default="text"),
    visibility: str = Body(default="public"),
    files: List[UploadFile] = File(default=[]),
    current_user: dict = Depends(get_current_user)
) -> PostResponse:
    """Create a new post with media files"""
    try:
        # First upload media if provided
        media_data = []
        if files:
            media_data = await post_service.upload_post_media(
                files=files,
                user_id=str(current_user["_id"])
            )
        
        # Create post data
        from app.schemas.post import MediaItem
        media_items = [MediaItem(**media) for media in media_data]
        
        post_data = PostCreate(
            content=content,
            post_type=post_type,
            visibility=visibility,
            media=media_items
        )
        
        # Create post
        return await post_service.create_post(str(current_user["_id"]), post_data)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ContentModerationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create post with media")
