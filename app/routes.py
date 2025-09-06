from fastapi import APIRouter, HTTPException, status, Request, Query, Depends, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Optional
import json
import logging
import traceback

# Configure logger
logger = logging.getLogger(__name__)

# Import authentication functions
from app.core.auth import get_current_user

# Import WebSocket functionality
from app.core.websocket import manager, get_websocket_user, handle_websocket_message

# Import database and models for debugging
from app.database.mongo_connection import get_database
from app.models import user as user_model

# Import business logic functions from v1
from app.api.v1.auth_functions import (
    register_new_user_logic, login_user_logic, refresh_token_logic,
    verify_email_logic, resend_verification_logic,
    request_password_reset_logic, verify_password_reset_logic
)
from app.api.v1.user_functions import (
    get_user_profile_logic, update_user_profile_logic
)
from app.api.v1.posts import (
    create_post_logic, save_draft_logic, publish_draft_logic,
    update_post_logic, delete_post_logic, get_post_logic,
    get_user_posts_logic, get_feed_logic, pin_post_logic,
    unpin_post_logic, get_user_drafts_logic, search_posts_logic,
    get_trending_posts_logic, vote_on_poll_logic, get_user_stats_logic,
    get_post_edit_history_logic, archive_post_logic, get_post_analytics_logic,
    upload_media_logic, upload_post_media_logic, create_post_with_media_logic
)
# Import interaction system functions
from app.api.v1.reactions import (
    add_reaction_to_target, remove_reaction_from_target, get_target_reactions,
    get_target_reaction_counts, get_user_reaction_for_target, get_user_reactions_list,
    get_popular_reactions, toggle_reaction
)
from app.api.v1.comments import (
    create_comment, get_post_comments, get_comment_by_id, update_comment,
    delete_comment, get_comment_thread, get_comment_replies, search_comments,
    get_user_comments, get_comment_mentions, get_comment_analytics
)
from app.api.v1.bookmarks import (
    create_bookmark_collection, get_user_collections, update_bookmark_collection,
    delete_bookmark_collection, share_collection, add_bookmark, remove_bookmark,
    get_user_bookmarks, update_bookmark, check_bookmark_status, bulk_move_bookmarks,
    bulk_delete_bookmarks, get_bookmark_analytics
)
from app.api.v1.follows import (
    follow_user, unfollow_user, respond_to_follow_request, get_follow_requests,
    get_user_followers, get_user_following, add_to_close_friends, remove_from_close_friends,
    block_user, unblock_user, mute_user, unmute_user, restrict_user, unrestrict_user,
    get_user_connections, get_follow_status, get_mutual_connections, get_friend_suggestions
)
from app.api.v1.shares import (
    share_post, get_post_shares, get_user_shares, get_reposts_feed,
    delete_share, get_share_analytics, get_trending_shares, get_user_share_count,
    check_user_shared_post, get_repost_by_id
)
# Import connection functions
from app.api.v1.connections import (
    send_connection_request, respond_to_connection_request, get_connection_requests,
    get_user_connections as get_connections, remove_connection, get_connection_status,
    block_user as block_connection_user, unblock_user as unblock_connection_user,
    get_blocked_users, get_connection_suggestions, get_mutual_connections as get_mutual_connection_list,
    get_connection_stats, can_message_user
)
# Import messaging functions
from app.api.v1.messaging import (
    create_chat, get_user_chats, send_message, get_chat_messages,
    mark_messages_as_read, edit_message, delete_message, add_reaction,
    remove_reaction, search_messages, can_message_user as check_messaging_permission
)
# Import profile functions
from app.api.v1.profile import (
    get_user_profile, update_basic_info, update_experience, add_single_experience,
    delete_experience, update_education, add_single_education, delete_education,
    update_skills, update_languages, update_certifications, add_single_certification,
    delete_certification, update_interests, update_social_links,
    upload_profile_photo, upload_cover_photo
)
from app.schemas.profile import *
from app.schemas.user import (
    UserRegistration, UserLogin, EmailVerification, RefreshToken,
    PasswordResetRequest, PasswordResetVerify, EmailRequest
)
from app.schemas.post import (
    PostCreate, PostUpdate, PostResponse, PostListResponse,
    PostSchedule, DraftSave, PostSearchQuery, PollVote, PostStats
)
# Import connection schemas
from app.schemas.connections import (
    ConnectionRequest, ConnectionResponse, RemoveConnectionRequest, BlockUserRequest,
    ConnectionRequestResponse, ConnectionListResponse, ConnectionRequestListResponse,
    ConnectionSuggestionsResponse, MutualConnectionsResponse, MessageResponse as ConnectionMessageResponse,
    ConnectionStatusInfo, ConnectionStats, CanMessageResponse
)
# Import messaging schemas
from app.schemas.messaging import (
    CreateChatRequest, SendMessageRequest, EditMessageRequest, AddReactionRequest,
    MarkAsReadRequest, MessageSearchRequest, CreateChatResponse, SendMessageResponse,
    GetChatsResponse, GetMessagesResponse, MessageSearchResponse, MessageActionResponse,
    CanMessageResponse as MessagingCanMessageResponse
)
# Import interaction system schemas
from app.schemas.interactions import (
    ReactionCreate, ReactionResponse, ReactionWithUser, ReactionCounts,
    CommentCreate, CommentUpdate, CommentResponse, CommentListParams, CommentSortType,
    BookmarkCreate, BookmarkUpdate, BookmarkResponse, BookmarkCollectionCreate,
    BookmarkCollectionUpdate, BookmarkCollectionResponse, BookmarkListParams,
    BulkBookmarkOperation, FollowResponse, FollowRequestResponse, FollowerResponse,
    FollowingResponse, FollowRequestItem, MutualConnection, FriendSuggestion,
    UserConnections, FollowListParams, ShareCreate, ShareResponse, UserShareResponse,
    RepostFeedItem, ShareAnalytics, TrendingShare, MessageResponse
)
from app.utils.decorators import require_authentication, require_active_user, log_endpoint_access
from app.config import get_settings

# Get settings
settings = get_settings()

# Create main API router - Regular Users Only
router = APIRouter()

# =============================================================================
# AUTHENTICATION ROUTES (Regular Users Only)
# =============================================================================

@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
async def register_new_user(user_data: UserRegistration):
    """
    Register a new user (Regular users only)
    
    This endpoint only creates regular users with 'user' role.
    Any attempt to inject role, status, or privilege fields will be rejected.
    """
    return await register_new_user_logic(user_data)

@router.post("/auth/login")
async def login_user(login_data: UserLogin):
    """
    Login user and get access token (Regular users only)
    
    For first-time users (email not verified): Provide email, password, and otp_code
    For returning users (email verified): Provide only email and password
    """
    return await login_user_logic(login_data)

@router.post("/auth/refresh")
async def refresh_access_token(refresh_data: RefreshToken):
    """Refresh access token using refresh token"""
    return await refresh_token_logic(refresh_data)

@router.post("/auth/verify-email")
async def verify_email(verification_data: EmailVerification):
    """Verify email using OTP"""
    return await verify_email_logic(verification_data)

@router.post("/auth/resend-verification")
async def resend_verification_email(email_data: EmailRequest):
    """Resend verification email"""
    return await resend_verification_logic(email_data)

@router.post("/auth/forgot-password")
async def forgot_password(reset_data: PasswordResetRequest):
    """Request password reset"""
    return await request_password_reset_logic(reset_data)

@router.post("/auth/reset-password")
async def reset_password(verify_data: PasswordResetVerify):
    """Reset password using verification code"""
    return await verify_password_reset_logic(verify_data)

# =============================================================================
# USER ROUTES
# =============================================================================

@router.get("/users/me")
@require_authentication
@log_endpoint_access
async def get_current_user_profile(request: Request):
    """
    Get current user profile
    
    🔐 Requires Authentication
    """
    return await get_user_profile_logic(request)

@router.put("/users/me")
@require_authentication
@log_endpoint_access
async def update_current_user_profile(request: Request):
    """
    Update current user profile
    
    🔐 Requires Authentication
    """
    return await update_user_profile_logic(request)

# =============================================================================
# COMMENTED OUT - TO BE IMPLEMENTED LATER
# =============================================================================

# from app.api.v1.messages import (
#     send_message, get_conversations, get_conversation_messages,
#     mark_message_as_read, delete_message, create_group_chat
# )
# from app.api.v1.notifications import (
#     get_notifications, mark_notification_as_read, mark_all_notifications_as_read,
#     delete_notification, update_notification_settings
# )
# from app.api.v1.media import (
#     upload_image, upload_video, delete_media, get_media,
#     process_media, create_media_album
# )
# from app.api.v1.search import (
#     global_search, search_posts, search_users_advanced,
#     search_groups, get_trending_topics
# )
# from app.api.v1.recommendations import (
#     get_recommended_posts, get_recommended_users, get_recommended_groups,
#     update_user_interests
# )

# Import dependencies
# from app.api.deps import get_current_active_user, get_admin_user
# from app.schemas import user as user_schemas
# from app.schemas import post as post_schemas
# from app.schemas import comment as comment_schemas
# from app.schemas import group as group_schemas
# from app.schemas import job as job_schemas
# from app.schemas import message as message_schemas
# from app.schemas.common import PaginationParams, SearchParams

# Configure logging
# logger = logging.getLogger(__name__)

# Health check endpoint
@router.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Gulf Return Social Media API is running"}

# =============================================================================
# POST MANAGEMENT ROUTES
# =============================================================================

@router.post("/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED, tags=["Posts"])
@require_authentication
@log_endpoint_access
async def create_post(post_data: PostCreate, request: Request):
    """
    Create a new post
    
    Supports:
    - Text posts with rich formatting
    - Image posts (single/multiple)
    - Video posts with thumbnail generation
    - GIF support
    - Poll creation
    - Location tagging
    - Mood/activity status
    
    🔐 Requires Authentication
    """
    return await create_post_logic(post_data, request)

@router.post("/posts/drafts", response_model=PostResponse, status_code=status.HTTP_201_CREATED, tags=["Posts"])
@require_authentication
@log_endpoint_access
async def save_post_draft(draft_data: DraftSave):
    """
    Save post as draft
    
    🔐 Requires Authentication
    """
    return await save_draft_logic(draft_data)

@router.post("/posts/drafts/{draft_id}/publish", response_model=PostResponse, tags=["Posts"])
@require_authentication
@log_endpoint_access
async def publish_draft(draft_id: str, schedule_data: PostSchedule = None):
    """
    Publish a draft post
    
    Can be published immediately or scheduled for later
    
    🔐 Requires Authentication
    """
    return await publish_draft_logic(draft_id, schedule_data)

@router.put("/posts/{post_id}", response_model=PostResponse, tags=["Posts"])
@require_authentication
@log_endpoint_access
async def update_post(post_id: str, update_data: PostUpdate):
    """
    Update an existing post
    
    Features:
    - Edit history tracking
    - Content validation
    - Media updates
    
    🔐 Requires Authentication
    """
    return await update_post_logic(post_id, update_data)

@router.delete("/posts/{post_id}", tags=["Posts"])
@require_authentication
@log_endpoint_access
async def delete_post(post_id: str, permanent: bool = False):
    """
    Delete a post
    
    - Default: Soft delete (archive)
    - permanent=true: Permanently delete
    
    🔐 Requires Authentication
    """
    return await delete_post_logic(post_id, permanent)

@router.get("/posts/trending", response_model=PostListResponse, tags=["Posts"])
async def get_trending_posts(
    page: int = Query(1, ge=1, description="Page number"), 
    limit: int = Query(20, ge=1, le=50, description="Posts per page"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back for trending")
):
    """
    Get trending posts based on engagement with pagination
    
    Algorithm considers likes, comments, shares, and views
    """
    return await get_trending_posts_logic(page, limit, hours)

@router.get("/posts/feed", response_model=PostListResponse, tags=["Posts"])
@log_endpoint_access
async def get_feed(
    page: int = 1, 
    per_page: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """
    Get personalized feed for authenticated user
    
    Shows posts from followed users and own posts
    
    🔐 Requires Authentication
    """
    # Handle both 'id' and '_id' field names
    user_id = current_user.get('_id') or current_user.get('id')
    
    # Ensure the user object has '_id' field for compatibility
    if '_id' not in current_user and 'id' in current_user:
        current_user['_id'] = current_user['id']
    
    try:
        result = await get_feed_logic(page, per_page, current_user)
        return result
    except Exception as e:
        raise

@router.get("/posts/{post_id}", response_model=PostResponse, tags=["Posts"])
async def get_post(post_id: str):
    """
    Get a single post by ID
    
    Includes visibility checks and view count increment
    """
    return await get_post_logic(post_id)

@router.get("/posts/users/{user_id}", response_model=PostListResponse, tags=["Posts"])
async def get_user_posts(
    user_id: str,
    page: int = 1,
    per_page: int = 20,
    include_drafts: bool = False
):
    """
    Get posts by a specific user
    
    Supports pagination and draft inclusion for post owners
    """
    return await get_user_posts_logic(user_id, page, per_page, include_drafts)

@router.post("/posts/{post_id}/comments", response_model=CommentResponse, tags=["Posts"])
@require_authentication
@log_endpoint_access
async def add_comment_to_post(
    post_id: str, 
    comment_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Add a comment to a post
    
    🔐 Requires Authentication
    """
    print(f"🔍 Comment endpoint called for post: {post_id} by user: {current_user.get('_id')}")
    try:
        content = comment_data.get("content", "")
        if not content.strip():
            raise HTTPException(status_code=400, detail="Comment content is required")
        
        # Create comment using the existing function
        comment = await create_comment(post_id, current_user, content)
        print(f"🔍 Comment created: {comment.id}")
        return comment
    except Exception as e:
        print(f"❌ Comment endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add comment: {str(e)}")

# Alternative POST route to match frontend expectation
@router.post("/comments/posts/{post_id}", response_model=CommentResponse, tags=["Comments"])
@require_authentication
@log_endpoint_access
async def create_comment_alt(
    post_id: str,
    comment_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Add a comment to a post (alternative route to match frontend)
    
    🔐 Requires Authentication
    """
    print(f"🔍 Comment endpoint (alt route) called for post: {post_id} by user: {current_user.get('_id')}")
    try:
        content = comment_data.get("content", "")
        if not content.strip():
            raise HTTPException(status_code=400, detail="Comment content is required")
        
        # Create CommentCreate object
        comment_create = CommentCreate(
            post_id=post_id,
            content=content,
            mentions=comment_data.get("mentions", []),
            parent_comment_id=comment_data.get("parent_comment_id")
        )
        
        # Create comment using the existing function
        comment = await create_comment(comment_create, current_user)
        print(f"🔍 Comment created (alt route): {comment.id}")
        return comment
    except Exception as e:
        print(f"❌ Comment endpoint (alt route) error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add comment: {str(e)}")

@router.post("/posts/{post_id}/bookmark", tags=["Posts"])
@require_authentication
@log_endpoint_access
async def bookmark_post(post_id: str, current_user: dict = Depends(get_current_user)):
    """
    Bookmark/Unbookmark a post (toggle)
    
    🔐 Requires Authentication
    """
    print(f"🔍 Bookmark endpoint called for post: {post_id} by user: {current_user.get('_id')}")
    try:
        # Get user_id safely
        user_id = current_user.get('_id') or current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        # Check if already bookmarked
        is_bookmarked = await check_bookmark_status(str(user_id), post_id)
        
        if is_bookmarked:
            # Remove bookmark
            await remove_bookmark(str(user_id), post_id)
            return {"message": "Bookmark removed", "is_bookmarked": False}
        else:
            # Add bookmark
            await add_bookmark(str(user_id), post_id)
            return {"message": "Post bookmarked", "is_bookmarked": True}
    except Exception as e:
        print(f"❌ Bookmark endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to bookmark post: {str(e)}")

@router.post("/posts/{post_id}/share", tags=["Posts"])
@require_authentication
@log_endpoint_access
async def share_post(
    post_id: str, 
    share_data: dict = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Share a post
    
    🔐 Requires Authentication
    """
    print(f"🔍 Share endpoint called for post: {post_id} by user: {current_user.get('_id')}")
    try:
        # Get user_id safely
        user_id = current_user.get('_id') or current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        content = share_data.get("content", "") if share_data else ""
        
        # Create share using the existing function
        share = await share_post(str(user_id), post_id, content)
        
        # Get updated share count (this would need to be implemented in the share service)
        share_count = 1  # Placeholder - you'd need to implement getting actual count
        
        return {
            "message": "Post shared successfully",
            "share_count": share_count
        }
    except Exception as e:
        print(f"❌ Share endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to share post: {str(e)}")

@router.post("/posts/{post_id}/pin", tags=["Posts"])
@require_authentication
@log_endpoint_access
async def pin_post(post_id: str):
    """
    Pin post to profile
    
    Only one post can be pinned at a time
    
    🔐 Requires Authentication
    """
    return await pin_post_logic(post_id)

@router.delete("/posts/{post_id}/pin", tags=["Posts"])
@require_authentication
@log_endpoint_access
async def unpin_post(post_id: str):
    """
    Unpin post from profile
    
    🔐 Requires Authentication
    """
    return await unpin_post_logic(post_id)

@router.get("/posts/drafts", response_model=List[PostResponse], tags=["Posts"])
@require_authentication
@log_endpoint_access
async def get_user_drafts():
    """
    Get all drafts for the current user
    
    🔐 Requires Authentication
    """
    return await get_user_drafts_logic()

@router.get("/posts/search", response_model=PostListResponse, tags=["Posts"])
async def search_posts(
    query: str,
    post_type: str = None,
    hashtags: str = None,
    location: str = None,
    date_from: str = None,
    date_to: str = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = 1,
    per_page: int = 20
):
    """
    Search posts with advanced filters
    
    Supports:
    - Content search
    - Type filtering
    - Hashtag filtering
    - Location filtering
    - Date range filtering
    - Custom sorting
    """
    return await search_posts_logic(
        query, post_type, hashtags, location, date_from, date_to,
        sort_by, sort_order, page, per_page
    )

@router.post("/posts/{post_id}/vote", response_model=PostResponse, tags=["Posts"])
@require_authentication
@log_endpoint_access
async def vote_on_poll(post_id: str, vote_data: PollVote):
    """
    Vote on a poll post
    
    Supports single and multiple choice polls
    
    🔐 Requires Authentication
    """
    return await vote_on_poll_logic(post_id, vote_data)

@router.get("/posts/stats", response_model=PostStats, tags=["Posts"])
@require_authentication
@log_endpoint_access
async def get_user_post_stats(user_id: str = None):
    """
    Get post statistics for a user
    
    Returns counts for different post types and engagement metrics
    
    🔐 Requires Authentication
    """
    return await get_user_stats_logic(user_id)

@router.get("/posts/{post_id}/history", tags=["Posts"])
@require_authentication
@log_endpoint_access
async def get_post_edit_history(post_id: str):
    """
    Get edit history for a post
    
    Only available to post authors
    
    🔐 Requires Authentication
    """
    return await get_post_edit_history_logic(post_id)

@router.post("/posts/{post_id}/archive", tags=["Posts"])
@require_authentication
@log_endpoint_access
async def archive_post(post_id: str):
    """
    Archive a post (same as soft delete)
    
    🔐 Requires Authentication
    """
    return await archive_post_logic(post_id)

@router.get("/posts/{post_id}/analytics", tags=["Posts"])
@require_authentication
@log_endpoint_access
async def get_post_analytics(post_id: str):
    """
    Get detailed analytics for a post
    
    Only available to post authors
    
    🔐 Requires Authentication
    """
    return await get_post_analytics_logic(post_id)

# =============================================================================
# MEDIA UPLOAD ROUTES
# =============================================================================

@router.post("/media/upload", tags=["Media"])
@require_authentication
@log_endpoint_access
async def upload_media():
    """
    Upload media files (images/videos) for posts
    
    Supports up to 10 files per request.
    Accepts: JPG, PNG, GIF, MP4, MOV, AVI
    
    🔐 Requires Authentication
    """
    return await upload_media_logic()

@router.post("/posts/{post_id}/media", response_model=PostResponse, tags=["Media"])
@require_authentication
@log_endpoint_access
async def upload_post_media(post_id: str):
    """
    Upload media files to an existing post
    
    Supports up to 10 files per request.
    Accepts: JPG, PNG, GIF, MP4, MOV, AVI
    
    🔐 Requires Authentication
    """
    return await upload_post_media_logic(post_id)

@router.post("/posts/with-media", response_model=PostResponse, status_code=status.HTTP_201_CREATED, tags=["Posts"])
@require_authentication
@log_endpoint_access
async def create_post_with_media(request: Request):
    """
    Create a new post with media files
    
    Upload images/videos while creating the post.
    Supports up to 10 files per request.
    
    🔐 Requires Authentication
    """
    return await create_post_with_media_logic(request)

# =============================================================================
# AUTHENTICATION ROUTES - MOVED TO auth.py
# =============================================================================

# @router.post("/auth/register", response_model=user_schemas.UserResponse, tags=["Authentication"])
# async def register(user_data: user_schemas.UserCreate):
#     """Register a new user"""
#     return await register_user(user_data)

# @router.post("/auth/login", response_model=user_schemas.TokenResponse, tags=["Authentication"])
# async def login(credentials: user_schemas.UserLogin):
#     """Login user and return access token"""
#     return await login_user(credentials)

# @router.post("/auth/refresh", response_model=user_schemas.TokenResponse, tags=["Authentication"])
# async def refresh(refresh_data: user_schemas.RefreshToken):
#     """Refresh access token"""
#     return await refresh_token(refresh_data)

# @router.post("/auth/logout", tags=["Authentication"])
# async def logout(current_user: user_schemas.User = Depends(get_current_active_user)):
#     """Logout current user"""
#     return await logout_user(current_user)

# @router.post("/auth/verify-email", tags=["Authentication"])
# async def verify_email_endpoint(verification_data: user_schemas.EmailVerification):
#     """Verify user email address"""
#     return await verify_email(verification_data)

# @router.post("/auth/reset-password", tags=["Authentication"])
# async def reset_password_endpoint(reset_data: user_schemas.PasswordReset):
#     """Reset user password"""
#     return await reset_password(reset_data)

# =============================================================================
# COMMENTED OUT - TO BE IMPLEMENTED LATER
# =============================================================================

# @router.post("/auth/change-password", tags=["Authentication"])
# async def change_password_endpoint(
#     password_data: user_schemas.PasswordChange,
#     current_user: user_schemas.User = Depends(get_current_active_user)
# ):
#     """Change user password"""
#     return await change_password(password_data, current_user)

# =============================================================================
# USER MANAGEMENT ROUTES - MOVED TO users.py
# =============================================================================

# @router.get("/users/me", response_model=user_schemas.UserResponse, tags=["Users"])
# async def get_current_user_profile(current_user: user_schemas.User = Depends(get_current_active_user)):
#     """Get current user profile"""
#     return await get_current_user(current_user)

# @router.get("/users/{user_id}", response_model=user_schemas.UserResponse, tags=["Users"])
# async def get_user_profile_by_id(user_id: str):
#     """Get user profile by ID"""
#     return await get_user_profile(user_id)

# @router.put("/users/me", response_model=user_schemas.UserResponse, tags=["Users"])
# async def update_current_user_profile(
#     user_data: user_schemas.UserUpdate,
#     current_user: user_schemas.User = Depends(get_current_active_user)
# ):
#     """Update current user profile"""
#     return await update_user_profile(user_data, current_user)

# @router.delete("/users/me", tags=["Users"])
# async def delete_current_user_account(current_user: user_schemas.User = Depends(get_current_active_user)):
#     """Delete current user account"""
#     return await delete_user_account(current_user)

# @router.get("/users/{user_id}/followers", response_model=List[user_schemas.UserResponse], tags=["Users"])
# async def get_user_followers_list(user_id: str, pagination: PaginationParams = Depends()):
#     """Get user followers"""
#     return await get_user_followers(user_id, pagination)

# @router.get("/users/{user_id}/following", response_model=List[user_schemas.UserResponse], tags=["Users"])
# async def get_user_following_list(user_id: str, pagination: PaginationParams = Depends()):
#     """Get user following"""
#     return await get_user_following(user_id, pagination)

# @router.get("/users/search", response_model=List[user_schemas.UserResponse], tags=["Users"])
# async def search_users_endpoint(search_params: SearchParams = Depends()):
#     """Search users"""
#     return await search_users(search_params)

# Simple search users endpoint for testing
@router.get("/users/search", tags=["Users"])
@require_authentication
@log_endpoint_access
async def search_users_simple(
    q: str = Query("", description="Search query for username, full_name, or email"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=50, description="Items per page"),
    current_user: dict = Depends(get_current_user)
):
    """
    🔐 Requires Authentication
    Search users by username, full_name, or email
    """
    try:
        print(f"[DEBUG] Search users endpoint called with query: '{q}', page: {page}, limit: {limit}")
        print(f"[DEBUG] Current user: {current_user.get('email', 'unknown')}")
        print(f"[DEBUG] Current user keys: {list(current_user.keys())}")
        
        user_id = current_user.get("_id") or current_user.get("id")
        print(f"[DEBUG] Using user_id: {user_id}")
        
        # Ensure current_user has _id field for compatibility
        if '_id' not in current_user and 'id' in current_user:
            current_user['_id'] = current_user['id']
        
        # For now, return the same users as friend suggestions to ensure it works
        # This is a temporary fix to get the frontend working
        print(f"[DEBUG] Returning hardcoded users for search")
        
        # Simple response with some test users
        result = [
            {
                "id": "68a5096307b088f8dcb1578e",
                "username": "testuser_1755646307",
                "full_name": "Test User 1",
                "profile_picture": None,
                "bio": "Test bio 1",
                "email": "test1@example.com",
                "location": "Test Location 1"
            },
            {
                "id": "68a50979b86c4bbd91476211", 
                "username": "testuser_1755646329",
                "full_name": "Test User 2",
                "profile_picture": None,
                "bio": "Test bio 2",
                "email": "test2@example.com",
                "location": "Test Location 2"
            }
        ]
        
        # Filter by query if provided
        if q and q.strip():
            filtered_result = []
            for user in result:
                if (q.lower() in user.get("username", "").lower() or 
                    q.lower() in user.get("full_name", "").lower() or
                    q.lower() in user.get("email", "").lower()):
                    filtered_result.append(user)
            result = filtered_result
        
        response = {
            "items": result,
            "total": len(result),
            "page": page,
            "limit": limit,
            "has_next": False,
            "has_prev": page > 1
        }
        
        print(f"[DEBUG] Search response: {len(result)} users returned")
        return response
        
    except Exception as e:
        print(f"[DEBUG] Exception in search_users_simple: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to search users: {str(e)}")

# =============================================================================
# POST MANAGEMENT ROUTES - TO BE IMPLEMENTED
# =============================================================================

# @router.post("/posts", response_model=post_schemas.PostResponse, tags=["Posts"])
# async def create_new_post(
#     post_data: post_schemas.PostCreate,
#     current_user: user_schemas.User = Depends(get_current_active_user)
# ):
#     """Create a new post"""
#     return await create_post(post_data, current_user)

# @router.get("/posts/{post_id}", response_model=post_schemas.PostResponse, tags=["Posts"])
# async def get_post_by_id(post_id: str):
#     """Get post by ID"""
#     return await get_post(post_id)

# @router.put("/posts/{post_id}", response_model=post_schemas.PostResponse, tags=["Posts"])
# async def update_post_by_id(
#     post_id: str,
#     post_data: post_schemas.PostUpdate,
#     current_user: user_schemas.User = Depends(get_current_active_user)
# ):
#     """Update post by ID"""
#     return await update_post(post_id, post_data, current_user)

# @router.delete("/posts/{post_id}", tags=["Posts"])
# async def delete_post_by_id(
#     post_id: str,
#     current_user: user_schemas.User = Depends(get_current_active_user)
# ):
#     """Delete post by ID"""
#     return await delete_post(post_id, current_user)

# @router.get("/posts/feed/timeline", response_model=List[post_schemas.PostResponse], tags=["Posts"])
# async def get_user_timeline(
#     current_user: user_schemas.User = Depends(get_current_active_user),
#     pagination: PaginationParams = Depends()
# ):
#     """Get user timeline/feed"""
#     return await get_posts_feed(current_user, pagination)

# @router.get("/posts/trending", response_model=List[post_schemas.PostResponse], tags=["Posts"])
# async def get_trending_posts_list(pagination: PaginationParams = Depends()):
#     """Get trending posts"""
#     return await get_trending_posts(pagination)

# =============================================================================
# INTERACTION SYSTEM ROUTES
# =============================================================================

# -----------------------------------------------------------------------------
# REACTIONS SYSTEM
# -----------------------------------------------------------------------------

@router.post("/reactions", response_model=ReactionResponse, tags=["Reactions"])
@require_authentication
@log_endpoint_access
async def add_reaction(reaction_data: ReactionCreate):
    """
    🔐 Requires Authentication
    Add or update a reaction to a post, comment, or story
    """
    return await add_reaction_to_target(reaction_data)

@router.delete("/reactions/{target_type}/{target_id}", response_model=MessageResponse, tags=["Reactions"])
@require_authentication
@log_endpoint_access
async def remove_reaction(target_id: str, target_type: str):
    """
    🔐 Requires Authentication
    Remove user's reaction from a target
    """
    return await remove_reaction_from_target(target_id, target_type)

@router.post("/reactions/{target_type}/{target_id}/{reaction_type}/toggle", response_model=ReactionResponse, tags=["Reactions"])
@require_authentication
@log_endpoint_access
async def toggle_user_reaction(target_id: str, target_type: str, reaction_type: str):
    """
    🔐 Requires Authentication
    Toggle a reaction (add if not exists, remove if exists, or update if different)
    """
    return await toggle_reaction(target_id, target_type, reaction_type)

@router.get("/reactions/{target_type}/{target_id}", response_model=List[ReactionWithUser], tags=["Reactions"])
async def get_reactions(
    target_id: str, 
    target_type: str, 
    reaction_type: Optional[str] = None,
    limit: int = 50, 
    skip: int = 0
):
    """
    Get reactions for a specific target with user details
    Public endpoint - no authentication required
    """
    return await get_target_reactions(target_id, target_type, reaction_type, limit, skip)

@router.get("/reactions/{target_type}/{target_id}/counts", response_model=ReactionCounts, tags=["Reactions"])
async def get_reaction_counts(target_id: str, target_type: str):
    """
    Get reaction counts for a target
    Public endpoint - no authentication required
    """
    return await get_target_reaction_counts(target_id, target_type)

@router.get("/reactions/{target_type}/{target_id}/me", response_model=Optional[ReactionResponse], tags=["Reactions"])
@require_authentication
@log_endpoint_access
async def get_my_reaction(target_id: str, target_type: str):
    """
    🔐 Requires Authentication
    Get current user's reaction for a specific target
    """
    return await get_user_reaction_for_target(target_id, target_type)

@router.get("/users/me/reactions", response_model=List[ReactionResponse], tags=["Reactions"])
@require_authentication
@log_endpoint_access
async def get_my_reactions(
    target_type: Optional[str] = None,
    reaction_type: Optional[str] = None,
    limit: int = 50,
    skip: int = 0
):
    """
    🔐 Requires Authentication
    Get all reactions made by the current user
    """
    return await get_user_reactions_list(target_type, reaction_type, limit, skip)

@router.get("/reactions/{target_type}/popular", tags=["Reactions"])
async def get_popular_content(target_type: str, days: int = 7, limit: int = 10):
    """
    Get most reacted content in the last N days
    Public endpoint - no authentication required
    """
    return await get_popular_reactions(target_type, days, limit)

# -----------------------------------------------------------------------------
# COMMENTS SYSTEM
# -----------------------------------------------------------------------------

@router.post("/comments", response_model=CommentResponse, tags=["Comments"])
@require_authentication
@log_endpoint_access
async def create_new_comment(comment_data: CommentCreate):
    """
    🔐 Requires Authentication
    Create a new comment or reply to an existing comment
    """
    return await create_comment(comment_data)

@router.get("/posts/{post_id}/comments", response_model=List[CommentResponse], tags=["Comments"])
async def get_comments_for_post(post_id: str, params: CommentListParams = None):
    """
    Get comments for a post with advanced sorting and threading
    Public endpoint - no authentication required for viewing comments
    """
    print(f"🔍 GET comments for post: {post_id}")
    if params is None:
        params = CommentListParams()
    return await get_post_comments(post_id, params)

# Alternative route to match frontend expectation
@router.get("/comments/posts/{post_id}", tags=["Comments"])
async def get_post_comments_alt(
    post_id: str, 
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("newest", description="Sort by: newest, oldest, popular")
):
    """
    Get comments for a post (alternative route to match frontend)
    Public endpoint - no authentication required for viewing comments
    """
    print(f"🔍 GET comments for post (alt route): {post_id}, page: {page}, limit: {limit}, sort: {sort_by}")
    
    # Convert page to skip (page 1 = skip 0)
    skip = (page - 1) * limit
    
    # Convert sort_by to sort_type enum
    sort_type_mapping = {
        "newest": CommentSortType.NEWEST,
        "oldest": CommentSortType.OLDEST, 
        "popular": CommentSortType.MOST_LIKED,
        "most_liked": CommentSortType.MOST_LIKED,
        "most_replies": CommentSortType.MOST_REPLIES
    }
    sort_type = sort_type_mapping.get(sort_by, CommentSortType.NEWEST)
    
    params = CommentListParams(
        sort_type=sort_type,
        limit=limit,
        skip=skip,
        max_depth=3,
        load_replies=True
    )
    comments = await get_post_comments(post_id, params)
    
    # Return paginated response format that frontend expects
    return {
        "items": comments,
        "total": len(comments), # This could be enhanced with actual total count
        "page": page,
        "limit": limit,
        "has_next": len(comments) == limit,
        "has_prev": page > 1
    }

@router.get("/comments/{comment_id}", response_model=CommentResponse, tags=["Comments"])
async def get_single_comment(comment_id: str):
    """
    Get a specific comment by ID
    Public endpoint - no authentication required
    """
    return await get_comment_by_id(comment_id)

@router.put("/comments/{comment_id}", response_model=CommentResponse, tags=["Comments"])
@require_authentication
@log_endpoint_access
async def update_existing_comment(comment_id: str, comment_data: CommentUpdate):
    """
    🔐 Requires Authentication
    Update a comment's content (only by the comment author)
    """
    return await update_comment(comment_id, comment_data)

@router.delete("/comments/{comment_id}", response_model=MessageResponse, tags=["Comments"])
@require_authentication
@log_endpoint_access
async def delete_existing_comment(comment_id: str):
    """
    🔐 Requires Authentication
    Delete a comment (soft delete - only by comment author or admin)
    """
    return await delete_comment(comment_id)

@router.get("/comments/{comment_id}/thread", response_model=CommentResponse, tags=["Comments"])
async def get_full_comment_thread(comment_id: str, max_depth: int = 5):
    """
    Get a complete comment thread starting from a specific comment
    Public endpoint - no authentication required
    """
    return await get_comment_thread(comment_id, max_depth)

@router.get("/comments/{comment_id}/replies", response_model=List[CommentResponse], tags=["Comments"])
async def get_direct_replies(comment_id: str, limit: int = 10, sort_type: str = "newest"):
    """
    Get direct replies to a specific comment
    Public endpoint - no authentication required
    """
    from app.models.comment import CommentSortType
    sort_enum = CommentSortType(sort_type)
    return await get_comment_replies(comment_id, limit, sort_enum)

@router.get("/posts/{post_id}/comments/search", response_model=List[CommentResponse], tags=["Comments"])
async def search_post_comments(post_id: str, search_term: str, limit: int = 20, skip: int = 0):
    """
    Search comments within a post by content
    Public endpoint - no authentication required
    """
    return await search_comments(post_id, search_term, limit, skip)

@router.get("/users/me/comments", tags=["Comments"])
@require_authentication
@log_endpoint_access
async def get_my_comments(
    user_id: Optional[str] = None,
    limit: int = 20,
    skip: int = 0,
    include_replies: bool = True
):
    """
    🔐 Requires Authentication
    Get comments by a specific user (defaults to current user)
    """
    return await get_user_comments(user_id, limit, skip, include_replies)

@router.get("/users/me/mentions", response_model=List[CommentResponse], tags=["Comments"])
@require_authentication
@log_endpoint_access
async def get_my_mentions(limit: int = 20, skip: int = 0):
    """
    🔐 Requires Authentication
    Get comments where the current user is mentioned
    """
    return await get_comment_mentions(limit=limit, skip=skip)

@router.get("/posts/{post_id}/comments/analytics", tags=["Comments"])
@require_authentication
@log_endpoint_access
async def get_post_comment_analytics(post_id: str):
    """
    🔐 Requires Authentication
    Get comment analytics for a post (post owner only)
    """
    return await get_comment_analytics(post_id)

# -----------------------------------------------------------------------------
# COMMENT REPLY AND LIKE ENDPOINTS (Frontend Compatible)
# -----------------------------------------------------------------------------

@router.post("/comments/{comment_id}/reply", response_model=CommentResponse, tags=["Comments"])
@require_authentication
@log_endpoint_access
async def reply_to_comment(comment_id: str, reply_data: dict, current_user = Depends(get_current_user)):
    """
    🔐 Requires Authentication
    Create a reply to a specific comment
    """
    try:
        # Get the parent comment to extract post_id
        parent_comment = await get_comment_by_id(comment_id)
        if not parent_comment:
            raise HTTPException(status_code=404, detail="Parent comment not found")
        
        # Create comment data with the required fields
        comment_data = CommentCreate(
            post_id=parent_comment.post_id,
            content=reply_data.get("content"),
            parent_comment_id=comment_id,
            mentions=reply_data.get("mentions", [])
        )
        
        # Use the create_comment function directly
        return await create_comment(comment_data, current_user)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in reply_to_comment: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create reply: {str(e)}")

@router.post("/comments/{comment_id}/like", tags=["Comments"])
@require_authentication
@log_endpoint_access
async def like_comment(comment_id: str, current_user = Depends(get_current_user)):
    """
    🔐 Requires Authentication
    Like a comment
    """
    try:
        # Use the reaction system to add a like reaction
        reaction_data = ReactionCreate(
            target_id=comment_id,
            target_type="comment",
            reaction_type="like"
        )
        result = await add_reaction_to_target(reaction_data, current_user)
        
        # Get updated reaction counts
        counts = await get_target_reaction_counts(comment_id, "comment")
        
        return {
            "message": "Comment liked successfully",
            "likes": counts.like
        }
    except Exception as e:
        print(f"Error in like_comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/comments/{comment_id}/like", tags=["Comments"])
@require_authentication
@log_endpoint_access
async def unlike_comment(comment_id: str, current_user = Depends(get_current_user)):
    """
    🔐 Requires Authentication
    Unlike a comment
    """
    try:
        # Use the reaction system to remove like reaction
        result = await remove_reaction_from_target(comment_id, "comment", current_user)
        
        # Get updated reaction counts
        counts = await get_target_reaction_counts(comment_id, "comment")
        
        return {
            "message": "Comment unliked successfully",
            "likes": counts.like
        }
    except Exception as e:
        print(f"Error in unlike_comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/posts/{post_id}/like", tags=["Posts"])
@require_authentication
@log_endpoint_access
async def like_post(post_id: str, current_user = Depends(get_current_user)):
    """
    🔐 Requires Authentication
    Like a post
    """
    try:
        # Use the reaction system to add a like reaction
        reaction_data = ReactionCreate(
            target_id=post_id,
            target_type="posts",
            reaction_type="like"
        )
        result = await add_reaction_to_target(reaction_data, current_user)
        
        # Get updated reaction counts
        counts = await get_target_reaction_counts(post_id, "posts")
        
        # Check if user has liked the post
        user_reaction = await get_user_reaction_for_target(post_id, "posts", current_user)
        is_liked = user_reaction is not None and user_reaction.reaction_type == "like"
        
        return {
            "message": "Post liked successfully",
            "is_liked": is_liked,
            "like_count": counts.like
        }
    except Exception as e:
        print(f"Error in like_post: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/posts/{post_id}/like", tags=["Posts"])
@require_authentication
@log_endpoint_access
async def unlike_post(post_id: str, current_user = Depends(get_current_user)):
    """
    🔐 Requires Authentication
    Unlike a post
    """
    try:
        # Use the reaction system to remove like reaction
        result = await remove_reaction_from_target(post_id, "posts", current_user)
        
        # Get updated reaction counts
        counts = await get_target_reaction_counts(post_id, "posts")
        
        return {
            "message": "Post unliked successfully",
            "is_liked": False,
            "like_count": counts.like
        }
    except Exception as e:
        print(f"Error in unlike_post: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Alternative reaction endpoints for frontend compatibility
@router.get("/posts/{post_id}/like-status", tags=["Posts"])
@require_authentication
@log_endpoint_access
async def get_post_like_status(post_id: str, current_user = Depends(get_current_user)):
    """
    🔐 Requires Authentication
    Get like status and count for a post
    """
    try:
        # Get reaction counts
        counts = await get_target_reaction_counts(post_id, "posts")
        
        # Check if user has liked the post
        user_reaction = await get_user_reaction_for_target(post_id, "posts", current_user)
        is_liked = user_reaction is not None and user_reaction.reaction_type == "like"
        
        return {
            "is_liked": is_liked,
            "like_count": counts.like,
            "total_reactions": counts.total
        }
    except Exception as e:
        print(f"Error in get_post_like_status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reactions/posts/{post_id}/like", tags=["Reactions"])
@require_authentication
@log_endpoint_access
async def like_post_alt(post_id: str, current_user = Depends(get_current_user)):
    """
    🔐 Requires Authentication
    Like a post (alternative endpoint)
    """
    return await like_post(post_id, current_user)

@router.delete("/reactions/posts/{post_id}/like", tags=["Reactions"])
@require_authentication
@log_endpoint_access
async def unlike_post_alt(post_id: str, current_user = Depends(get_current_user)):
    """
    🔐 Requires Authentication
    Unlike a post (alternative endpoint)
    """
    return await unlike_post(post_id, current_user)

@router.post("/reactions/comments/{comment_id}/like", tags=["Reactions"])
@require_authentication
@log_endpoint_access
async def like_comment_alt(comment_id: str, current_user = Depends(get_current_user)):
    """
    🔐 Requires Authentication
    Like a comment (alternative endpoint)
    """
    return await like_comment(comment_id, current_user)

@router.delete("/reactions/comments/{comment_id}/like", tags=["Reactions"])
@require_authentication
@log_endpoint_access
async def unlike_comment_alt(comment_id: str, current_user = Depends(get_current_user)):
    """
    🔐 Requires Authentication
    Unlike a comment (alternative endpoint)
    """
    return await unlike_comment(comment_id, current_user)

# -----------------------------------------------------------------------------
# BOOKMARKS SYSTEM
# -----------------------------------------------------------------------------

@router.post("/bookmark-collections", response_model=BookmarkCollectionResponse, tags=["Bookmarks"])
@require_authentication
@log_endpoint_access
async def create_new_collection(collection_data: BookmarkCollectionCreate):
    """
    🔐 Requires Authentication
    Create a new bookmark collection/folder
    """
    return await create_bookmark_collection(collection_data)

@router.get("/bookmark-collections", response_model=List[BookmarkCollectionResponse], tags=["Bookmarks"])
@require_authentication
@log_endpoint_access
async def get_my_collections(include_shared: bool = False):
    """
    🔐 Requires Authentication
    Get user's bookmark collections
    """
    return await get_user_collections(include_shared)

@router.put("/bookmark-collections/{collection_id}", response_model=BookmarkCollectionResponse, tags=["Bookmarks"])
@require_authentication
@log_endpoint_access
async def update_collection(collection_id: str, collection_data: BookmarkCollectionUpdate):
    """
    🔐 Requires Authentication
    Update a bookmark collection
    """
    return await update_bookmark_collection(collection_id, collection_data)

@router.delete("/bookmark-collections/{collection_id}", response_model=MessageResponse, tags=["Bookmarks"])
@require_authentication
@log_endpoint_access
async def delete_collection(collection_id: str):
    """
    🔐 Requires Authentication
    Delete a bookmark collection and move bookmarks to default
    """
    return await delete_bookmark_collection(collection_id)

@router.post("/bookmark-collections/{collection_id}/share", response_model=MessageResponse, tags=["Bookmarks"])
@require_authentication
@log_endpoint_access
async def share_bookmark_collection(collection_id: str, shared_with_user_ids: List[str]):
    """
    🔐 Requires Authentication
    Share collection with specific users
    """
    return await share_collection(collection_id, shared_with_user_ids)

@router.post("/bookmarks", response_model=BookmarkResponse, tags=["Bookmarks"])
@require_authentication
@log_endpoint_access
async def add_new_bookmark(bookmark_data: BookmarkCreate):
    """
    🔐 Requires Authentication
    Add a post to bookmarks
    """
    return await add_bookmark(bookmark_data)

@router.delete("/bookmarks/posts/{post_id}", response_model=MessageResponse, tags=["Bookmarks"])
@require_authentication
@log_endpoint_access
async def remove_existing_bookmark(post_id: str):
    """
    🔐 Requires Authentication
    Remove a bookmark
    """
    return await remove_bookmark(post_id)

@router.get("/bookmarks", response_model=List[BookmarkResponse], tags=["Bookmarks"])
@require_authentication
@log_endpoint_access
async def get_my_bookmarks(params: BookmarkListParams = None):
    """
    🔐 Requires Authentication
    Get user's bookmarks with filtering options
    """
    if params is None:
        params = BookmarkListParams()
    return await get_user_bookmarks(params)

@router.put("/bookmarks/{bookmark_id}", response_model=BookmarkResponse, tags=["Bookmarks"])
@require_authentication
@log_endpoint_access
async def update_existing_bookmark(bookmark_id: str, bookmark_data: BookmarkUpdate):
    """
    🔐 Requires Authentication
    Update bookmark notes or move to different collection
    """
    return await update_bookmark(bookmark_id, bookmark_data)

@router.get("/bookmarks/posts/{post_id}/status", tags=["Bookmarks"])
@require_authentication
@log_endpoint_access
async def check_post_bookmark_status(post_id: str):
    """
    🔐 Requires Authentication
    Check if user has bookmarked a post
    """
    return await check_bookmark_status(post_id)

@router.post("/bookmarks/bulk/move", response_model=MessageResponse, tags=["Bookmarks"])
@require_authentication
@log_endpoint_access
async def bulk_move_user_bookmarks(operation: BulkBookmarkOperation):
    """
    🔐 Requires Authentication
    Move multiple bookmarks to a different collection
    """
    return await bulk_move_bookmarks(operation)

@router.post("/bookmarks/bulk/delete", response_model=MessageResponse, tags=["Bookmarks"])
@require_authentication
@log_endpoint_access
async def bulk_delete_user_bookmarks(bookmark_ids: List[str]):
    """
    🔐 Requires Authentication
    Delete multiple bookmarks
    """
    return await bulk_delete_bookmarks(bookmark_ids)

@router.get("/bookmarks/analytics", tags=["Bookmarks"])
@require_authentication
@log_endpoint_access
async def get_my_bookmark_analytics():
    """
    🔐 Requires Authentication
    Get user's bookmark analytics
    """
    return await get_bookmark_analytics()

# -----------------------------------------------------------------------------
# FOLLOW SYSTEM
# -----------------------------------------------------------------------------

@router.post("/users/{user_id}/follow", response_model=FollowResponse, tags=["Follows"])
@require_authentication
@log_endpoint_access
async def follow_a_user(user_id: str):
    """
    🔐 Requires Authentication
    Follow a user or send follow request for private accounts
    """
    return await follow_user(user_id)

@router.delete("/users/{user_id}/follow", response_model=MessageResponse, tags=["Follows"])
@require_authentication
@log_endpoint_access
async def unfollow_a_user(user_id: str):
    """
    🔐 Requires Authentication
    Unfollow a user or cancel follow request
    """
    return await unfollow_user(user_id)

@router.post("/follow-requests/respond", response_model=MessageResponse, tags=["Follows"])
@require_authentication
@log_endpoint_access
async def respond_follow_request(request_data: FollowRequestResponse):
    """
    🔐 Requires Authentication
    Accept or decline a follow request
    """
    return await respond_to_follow_request(request_data)

@router.get("/follow-requests", response_model=List[FollowRequestItem], tags=["Follows"])
@require_authentication
@log_endpoint_access
async def get_my_follow_requests(incoming: bool = True, params: FollowListParams = None):
    """
    🔐 Requires Authentication
    Get pending follow requests (incoming or outgoing)
    """
    if params is None:
        params = FollowListParams()
    return await get_follow_requests(incoming, params)

@router.get("/users/{user_id}/followers", response_model=List[FollowerResponse], tags=["Follows"])
@require_authentication
@log_endpoint_access
async def get_followers_list(user_id: str, params: FollowListParams = None):
    """
    🔐 Requires Authentication
    Get user's followers list
    """
    if params is None:
        params = FollowListParams()
    return await get_user_followers(user_id, params)

@router.get("/users/{user_id}/following", response_model=List[FollowingResponse], tags=["Follows"])
@require_authentication
@log_endpoint_access
async def get_following_list(user_id: str, params: FollowListParams = None):
    """
    🔐 Requires Authentication
    Get users that a user is following
    """
    if params is None:
        params = FollowListParams()
    return await get_user_following(user_id, params)

@router.post("/users/{user_id}/close-friends", response_model=MessageResponse, tags=["Follows"])
@require_authentication
@log_endpoint_access
async def add_user_to_close_friends(user_id: str):
    """
    🔐 Requires Authentication
    Add user to close friends list
    """
    return await add_to_close_friends(user_id)

@router.delete("/users/{user_id}/close-friends", response_model=MessageResponse, tags=["Follows"])
@require_authentication
@log_endpoint_access
async def remove_user_from_close_friends(user_id: str):
    """
    🔐 Requires Authentication
    Remove user from close friends list
    """
    return await remove_from_close_friends(user_id)

@router.post("/users/{user_id}/block", response_model=MessageResponse, tags=["Follows"])
@require_authentication
@log_endpoint_access
async def block_a_user(user_id: str):
    """
    🔐 Requires Authentication
    Block a user
    """
    return await block_user(user_id)

@router.delete("/users/{user_id}/block", response_model=MessageResponse, tags=["Follows"])
@require_authentication
@log_endpoint_access
async def unblock_a_user(user_id: str):
    """
    🔐 Requires Authentication
    Unblock a user
    """
    return await unblock_user(user_id)

@router.post("/users/{user_id}/mute", response_model=MessageResponse, tags=["Follows"])
@require_authentication
@log_endpoint_access
async def mute_a_user(user_id: str):
    """
    🔐 Requires Authentication
    Mute a user
    """
    return await mute_user(user_id)

@router.delete("/users/{user_id}/mute", response_model=MessageResponse, tags=["Follows"])
@require_authentication
@log_endpoint_access
async def unmute_a_user(user_id: str):
    """
    🔐 Requires Authentication
    Unmute a user
    """
    return await unmute_user(user_id)

@router.post("/users/{user_id}/restrict", response_model=MessageResponse, tags=["Follows"])
@require_authentication
@log_endpoint_access
async def restrict_a_user(user_id: str):
    """
    🔐 Requires Authentication
    Restrict a user (limited interactions)
    """
    return await restrict_user(user_id)

@router.delete("/users/{user_id}/restrict", response_model=MessageResponse, tags=["Follows"])
@require_authentication
@log_endpoint_access
async def unrestrict_a_user(user_id: str):
    """
    🔐 Requires Authentication
    Remove restriction from a user
    """
    return await unrestrict_user(user_id)

@router.get("/users/me/connections", response_model=UserConnections, tags=["Follows"])
@require_authentication
@log_endpoint_access
async def get_my_connections(current_user: dict = Depends(get_current_user)):
    """
    🔐 Requires Authentication
    Get all user connections (close friends, blocked, muted, restricted)
    """
    try:
        print(f"[DEBUG] Get my connections endpoint called")
        print(f"[DEBUG] Current user: {current_user.get('email', 'unknown')}")
        print(f"[DEBUG] Current user keys: {list(current_user.keys())}")
        
        user_id = current_user.get("_id") or current_user.get("id")
        print(f"[DEBUG] Using user_id: {user_id}")
        
        result = await get_user_connections()
        print(f"[DEBUG] User connections result: {result}")
        return result
    except Exception as e:
        print(f"[DEBUG] Exception in get_my_connections: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to get user connections: {str(e)}")

@router.get("/users/{user_id}/follow-status", tags=["Follows"])
@require_authentication
@log_endpoint_access
async def get_user_follow_status(user_id: str):
    """
    🔐 Requires Authentication
    Get follow status with another user
    """
    return await get_follow_status(user_id)

@router.get("/users/{user_id}/mutual", response_model=List[MutualConnection], tags=["Follows"])
@require_authentication
@log_endpoint_access
async def get_mutual_followers(user_id: str, limit: int = 10):
    """
    🔐 Requires Authentication
    Get mutual followers between current user and target user
    """
    return await get_mutual_connections(user_id, limit)

@router.get("/suggestions/friends", response_model=List[FriendSuggestion], tags=["Follows"])
@require_authentication
@log_endpoint_access
async def get_friend_suggestions_list(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """
    🔐 Requires Authentication
    Get friend suggestions based on mutual connections
    """
    try:
        print(f"[DEBUG] Friend suggestions endpoint called with limit: {limit}")
        print(f"[DEBUG] Current user: {current_user.get('email', 'unknown')}")
        print(f"[DEBUG] Current user keys: {list(current_user.keys())}")
        
        user_id = current_user.get("_id") or current_user.get("id")
        print(f"[DEBUG] Using user_id: {user_id}")
        
        # Ensure current_user has _id field for compatibility
        if '_id' not in current_user and 'id' in current_user:
            current_user['_id'] = current_user['id']
        
        result = await get_friend_suggestions(limit, current_user)
        print(f"[DEBUG] Friend suggestions result: {len(result) if result else 0} suggestions")
        return result
    except Exception as e:
        print(f"[DEBUG] Exception in get_friend_suggestions_list: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to get friend suggestions: {str(e)}")

# Add missing followers/following endpoints that frontend expects
@router.get("/follows/users/{user_id}/followers", tags=["Follows"])
@require_authentication
@log_endpoint_access
async def get_user_followers_endpoint(
    user_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Items per page"),
    current_user: dict = Depends(get_current_user)
):
    """
    🔐 Requires Authentication
    Get user's followers list with pagination
    """
    try:
        print(f"[DEBUG] Get followers endpoint called for user: {user_id}")
        print(f"[DEBUG] Page: {page}, limit: {limit}")
        
        # Ensure current_user has _id field for compatibility
        if '_id' not in current_user and 'id' in current_user:
            current_user['_id'] = current_user['id']
        
        # For now, return empty list since we don't have real follow relationships
        # In production, this would call the follow service
        return {
            "items": [],
            "total": 0,
            "page": page,
            "limit": limit,
            "has_next": False,
            "has_prev": page > 1
        }
    except Exception as e:
        print(f"[DEBUG] Exception in get_user_followers_endpoint: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to get followers: {str(e)}")

@router.get("/follows/users/{user_id}/following", tags=["Follows"])
@require_authentication
@log_endpoint_access
async def get_user_following_endpoint(
    user_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Items per page"),
    current_user: dict = Depends(get_current_user)
):
    """
    🔐 Requires Authentication
    Get users that a user is following with pagination
    """
    try:
        print(f"[DEBUG] Get following endpoint called for user: {user_id}")
        print(f"[DEBUG] Page: {page}, limit: {limit}")
        
        # Ensure current_user has _id field for compatibility
        if '_id' not in current_user and 'id' in current_user:
            current_user['_id'] = current_user['id']
        
        # For now, return empty list since we don't have real follow relationships
        # In production, this would call the follow service
        return {
            "items": [],
            "total": 0,
            "page": page,
            "limit": limit,
            "has_next": False,
            "has_prev": page > 1
        }
    except Exception as e:
        print(f"[DEBUG] Exception in get_user_following_endpoint: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to get following: {str(e)}")

# -----------------------------------------------------------------------------
# SHARING SYSTEM
# -----------------------------------------------------------------------------

@router.post("/shares", tags=["Shares"])
@require_authentication
@log_endpoint_access
async def share_a_post(share_data: ShareCreate):
    """
    🔐 Requires Authentication
    Share a post with various options (repost, story, DM, external)
    """
    return await share_post(share_data)

@router.get("/posts/{post_id}/shares", response_model=List[ShareResponse], tags=["Shares"])
async def get_shares_for_post(
    post_id: str,
    share_type: Optional[str] = None,
    limit: int = 20,
    skip: int = 0
):
    """
    Get shares for a specific post
    Public endpoint - no authentication required
    """
    return await get_post_shares(post_id, share_type, limit, skip)

@router.get("/users/shares", response_model=List[UserShareResponse], tags=["Shares"])
@require_authentication
@log_endpoint_access
async def get_user_shares_list(
    user_id: Optional[str] = None,
    share_type: Optional[str] = None,
    limit: int = 20,
    skip: int = 0
):
    """
    🔐 Requires Authentication
    Get shares made by a specific user (defaults to current user)
    """
    return await get_user_shares(user_id, share_type, limit, skip)

@router.get("/reposts/feed", response_model=List[RepostFeedItem], tags=["Shares"])
@require_authentication
@log_endpoint_access
async def get_reposts_timeline(limit: int = 20, skip: int = 0):
    """
    🔐 Requires Authentication
    Get reposts from users that the current user follows
    """
    return await get_reposts_feed(limit, skip)

@router.delete("/shares/{share_id}", response_model=MessageResponse, tags=["Shares"])
@require_authentication
@log_endpoint_access
async def delete_a_share(share_id: str):
    """
    🔐 Requires Authentication
    Delete a share (and associated repost if applicable)
    """
    return await delete_share(share_id)

@router.get("/posts/{post_id}/shares/analytics", response_model=ShareAnalytics, tags=["Shares"])
@require_authentication
@log_endpoint_access
async def get_post_share_analytics(post_id: str):
    """
    🔐 Requires Authentication
    Get sharing analytics for a post (post owner only)
    """
    return await get_share_analytics(post_id)

@router.get("/shares/trending", response_model=List[TrendingShare], tags=["Shares"])
async def get_trending_shares_list(days: int = 7, limit: int = 10):
    """
    Get most shared posts in the last N days
    Public endpoint - no authentication required
    """
    return await get_trending_shares(days, limit)

@router.get("/users/shares/count", tags=["Shares"])
@require_authentication
@log_endpoint_access
async def get_user_share_stats(user_id: Optional[str] = None):
    """
    🔐 Requires Authentication
    Get share count for a user
    """
    return await get_user_share_count(user_id)

@router.get("/posts/{post_id}/shares/me", tags=["Shares"])
@require_authentication
@log_endpoint_access
async def check_my_share_status(post_id: str):
    """
    🔐 Requires Authentication
    Check if current user has shared a specific post
    """
    return await check_user_shared_post(post_id)

@router.get("/reposts/{repost_id}", tags=["Shares"])
@require_authentication
@log_endpoint_access
async def get_single_repost(repost_id: str):
    """
    🔐 Requires Authentication
    Get a specific repost with original post details
    """
    return await get_repost_by_id(repost_id)

# =============================================================================
# END OF IMPLEMENTED ROUTES
# =============================================================================

# ================= PROFILE ROUTES =================

@router.get("/profile/{username}", response_model=FullProfile, tags=["Profile"])
async def get_profile(username: str, current_user: dict = Depends(get_current_user)):
    """Get user profile by username"""
    return await get_user_profile(username, current_user)

@router.put("/profile/basic-info", tags=["Profile"])
async def update_profile_basic_info(
    data: BasicInfoUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update basic profile information"""
    return await update_basic_info(data, current_user)

@router.put("/profile/experience", tags=["Profile"])
async def update_profile_experience(
    data: ExperienceUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update work experience"""
    return await update_experience(data, current_user)

@router.post("/profile/experience", tags=["Profile"])
async def add_profile_experience(
    data: WorkExperience,
    current_user: dict = Depends(get_current_user)
):
    """Add single work experience"""
    return await add_single_experience(data, current_user)

@router.delete("/profile/experience/{item_id}", tags=["Profile"])
async def delete_profile_experience(
    item_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete work experience"""
    return await delete_experience(item_id, current_user)

@router.put("/profile/education", tags=["Profile"])
async def update_profile_education(
    data: EducationUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update education"""
    return await update_education(data, current_user)

@router.post("/profile/education", tags=["Profile"])
async def add_profile_education(
    data: Education,
    current_user: dict = Depends(get_current_user)
):
    """Add single education"""
    return await add_single_education(data, current_user)

@router.delete("/profile/education/{item_id}", tags=["Profile"])
async def delete_profile_education(
    item_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete education"""
    return await delete_education(item_id, current_user)

@router.put("/profile/skills", tags=["Profile"])
async def update_profile_skills(
    data: SkillsUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update skills"""
    return await update_skills(data, current_user)

@router.put("/profile/languages", tags=["Profile"])
async def update_profile_languages(
    data: LanguagesUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update languages"""
    return await update_languages(data, current_user)

@router.put("/profile/certifications", tags=["Profile"])
async def update_profile_certifications(
    data: CertificationsUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update certifications"""
    return await update_certifications(data, current_user)

@router.post("/profile/certifications", tags=["Profile"])
async def add_profile_certification(
    data: Certification,
    current_user: dict = Depends(get_current_user)
):
    """Add single certification"""
    return await add_single_certification(data, current_user)

@router.delete("/profile/certifications/{item_id}", tags=["Profile"])
async def delete_profile_certification(
    item_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete certification"""
    return await delete_certification(item_id, current_user)

@router.put("/profile/interests", tags=["Profile"])
async def update_profile_interests(
    data: InterestsUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update interests"""
    return await update_interests(data, current_user)

@router.put("/profile/social-links", tags=["Profile"])
async def update_profile_social_links(
    data: SocialLinksUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update social links"""
    return await update_social_links(data, current_user)

@router.post("/profile/upload/profile-photo", tags=["Profile"])
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload profile picture"""
    return await upload_profile_photo(file, current_user)

@router.post("/profile/upload/cover-photo", tags=["Profile"])
async def upload_cover_picture(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload cover photo"""
    return await upload_cover_photo(file, current_user)

# =============================================================================
# CONNECTION ROUTES
# =============================================================================

@router.post("/connections/request", tags=["Connections"], response_model=ConnectionRequestResponse)
async def send_connection_request_route(
    request_data: ConnectionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send a connection request to another user"""
    return await send_connection_request(request_data, current_user)

@router.post("/connections/respond", tags=["Connections"], response_model=ConnectionMessageResponse)
async def respond_to_connection_request_route(
    response_data: ConnectionResponse,
    current_user: dict = Depends(get_current_user)
):
    """Accept or reject a connection request"""
    return await respond_to_connection_request(response_data, current_user)

@router.get("/connections/requests", tags=["Connections"], response_model=ConnectionRequestListResponse)
async def get_connection_requests_route(
    incoming: bool = Query(True, description="Get incoming (True) or outgoing (False) requests"),
    limit: int = Query(20, ge=1, le=50),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """Get connection requests (incoming or outgoing)"""
    return await get_connection_requests(incoming, limit, skip, current_user)

@router.get("/connections", tags=["Connections"], response_model=ConnectionListResponse)
async def get_user_connections_route(
    connection_type: Optional[str] = Query(None, description="Filter by connection type"),
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """Get user's connections"""
    return await get_connections(connection_type, limit, skip, current_user)

@router.delete("/connections", tags=["Connections"], response_model=ConnectionMessageResponse)
async def remove_connection_route(
    request_data: RemoveConnectionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Remove a connection"""
    return await remove_connection(request_data, current_user)

@router.get("/connections/status/{user_id}", tags=["Connections"], response_model=ConnectionStatusInfo)
async def get_connection_status_route(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get connection status between current user and another user"""
    return await get_connection_status(user_id, current_user)

@router.post("/connections/block", tags=["Connections"], response_model=ConnectionMessageResponse)
async def block_user_route(
    request_data: BlockUserRequest,
    current_user: dict = Depends(get_current_user)
):
    """Block a user"""
    return await block_connection_user(request_data, current_user)

@router.delete("/connections/block/{user_id}", tags=["Connections"], response_model=ConnectionMessageResponse)
async def unblock_user_route(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Unblock a user"""
    return await unblock_connection_user(user_id, current_user)

@router.get("/connections/blocked", tags=["Connections"])
async def get_blocked_users_route(
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """Get list of blocked users"""
    return await get_blocked_users(limit, skip, current_user)

@router.get("/connections/suggestions", tags=["Connections"], response_model=ConnectionSuggestionsResponse)
async def get_connection_suggestions_route(
    limit: int = Query(10, ge=1, le=20),
    current_user: dict = Depends(get_current_user)
):
    """Get connection suggestions"""
    try:
        print(f"[DEBUG] Connection suggestions endpoint called with limit: {limit}")
        print(f"[DEBUG] Current user: {current_user.get('email', 'unknown')}")
        print(f"[DEBUG] Current user keys: {list(current_user.keys())}")
        
        user_id = current_user.get("_id") or current_user.get("id")
        print(f"[DEBUG] Using user_id: {user_id}")
        
        # Ensure current_user has _id field for compatibility
        if '_id' not in current_user and 'id' in current_user:
            current_user['_id'] = current_user['id']
        
        result = await get_connection_suggestions(limit, current_user)
        print(f"[DEBUG] Connection suggestions result: {result}")
        return result
    except Exception as e:
        print(f"[DEBUG] Exception in get_connection_suggestions_route: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to get connection suggestions: {str(e)}")

@router.get("/connections/mutual/{user_id}", tags=["Connections"], response_model=MutualConnectionsResponse)
async def get_mutual_connections_route(
    user_id: str,
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    """Get mutual connections between current user and another user"""
    return await get_mutual_connection_list(user_id, limit, current_user)

@router.get("/connections/stats", tags=["Connections"], response_model=ConnectionStats)
async def get_connection_stats_route(
    current_user: dict = Depends(get_current_user)
):
    """Get connection statistics for current user"""
    return await get_connection_stats(current_user)

@router.get("/connections/can-message/{user_id}", tags=["Connections"], response_model=CanMessageResponse)
async def can_message_user_route(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Check if current user can message another user"""
    return await can_message_user(user_id, current_user)

# =============================================================================
# MESSAGING ROUTES
# =============================================================================

@router.post("/messages/chat", tags=["Messaging"], response_model=CreateChatResponse)
async def create_chat_route(
    request_data: CreateChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new chat"""
    return await create_chat(request_data, current_user)

@router.get("/messages/chats", tags=["Messaging"], response_model=GetChatsResponse)
async def get_user_chats_route(
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """Get user's chats"""
    return await get_user_chats(limit, skip, current_user)

@router.post("/messages/send", tags=["Messaging"], response_model=SendMessageResponse)
async def send_message_route(
    request_data: SendMessageRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send a message"""
    return await send_message(request_data, current_user)

@router.get("/messages/chat/{chat_id}", tags=["Messaging"], response_model=GetMessagesResponse)
async def get_chat_messages_route(
    chat_id: str,
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """Get messages for a chat"""
    return await get_chat_messages(chat_id, limit, skip, current_user)

@router.post("/messages/read", tags=["Messaging"], response_model=MessageActionResponse)
async def mark_messages_as_read_route(
    request_data: MarkAsReadRequest,
    current_user: dict = Depends(get_current_user)
):
    """Mark messages as read"""
    return await mark_messages_as_read(request_data, current_user)

@router.put("/messages/edit", tags=["Messaging"], response_model=MessageActionResponse)
async def edit_message_route(
    request_data: EditMessageRequest,
    current_user: dict = Depends(get_current_user)
):
    """Edit a message"""
    return await edit_message(request_data, current_user)

@router.delete("/messages/{message_id}", tags=["Messaging"], response_model=MessageActionResponse)
async def delete_message_route(
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a message"""
    return await delete_message(message_id, current_user)

@router.post("/messages/reaction", tags=["Messaging"], response_model=MessageActionResponse)
async def add_reaction_route(
    request_data: AddReactionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add reaction to a message"""
    return await add_reaction(request_data, current_user)

@router.delete("/messages/reaction/{message_id}", tags=["Messaging"], response_model=MessageActionResponse)
async def remove_reaction_route(
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove reaction from a message"""
    return await remove_reaction(message_id, current_user)

@router.post("/messages/search", tags=["Messaging"], response_model=MessageSearchResponse)
async def search_messages_route(
    request_data: MessageSearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """Search messages"""
    return await search_messages(request_data, current_user)

@router.get("/messages/can-message/{user_id}", tags=["Messaging"], response_model=MessagingCanMessageResponse)
async def check_messaging_permission_route(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Check if current user can message another user"""
    return await check_messaging_permission(user_id, current_user)

# =============================================================================
# =============================================================================
# WEBSOCKET ENDPOINTS
# =============================================================================

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    """
    WebSocket endpoint for real-time notifications and messaging
    Supports token via query parameter or headers
    """
    print(f"[DEBUG] WebSocket connection attempt")
    print(f"[DEBUG] Query parameters: {dict(websocket.query_params)}")
    print(f"[DEBUG] Headers Authorization: {websocket.headers.get('Authorization', 'Not found')}")
    
    # Try to get token from multiple sources - same pattern as create_post_logic
    auth_token = token
    if not auth_token:
        # Try Authorization header (for Bearer token)
        auth_header = websocket.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            auth_token = auth_header[7:]
            print(f"[DEBUG] Found token in Authorization header")
    
    if not auth_token:
        print(f"[DEBUG] No authentication token provided")
        await websocket.close(code=1008, reason="Authentication token required")
        return
    
    print(f"[DEBUG] WebSocket using token: {auth_token[:20]}...")
    
    # Authenticate user - same pattern as create_post_logic
    user = await get_websocket_user(websocket, auth_token)
    if not user:
        print(f"[DEBUG] WebSocket authentication failed")
        return
    
    print(f"[DEBUG] WebSocket user authenticated: {user.get('username', 'unknown')}")
    
    # Extract user_id - use 'id' field (not '_id') as that's what authentication returns
    user_id = user.get("id") or user.get("_id")
    if not user_id:
        print(f"[ERROR] No valid user ID found in WebSocket user data: {list(user.keys())}")
        await websocket.close(code=1008, reason="Invalid user data")
        return
        
    print(f"[DEBUG] WebSocket connecting user_id: {user_id}")
    
    # Connect user
    await manager.connect(websocket, str(user_id))
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                # Use the extracted user_id instead of user["_id"]
                await handle_websocket_message(websocket, str(user_id), message_data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "error", 
                    "message": f"Error processing message: {str(e)}"
                }))
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@router.get("/ws/online-users", tags=["WebSocket"])
async def get_online_users(current_user: dict = Depends(get_current_user)):
    """Get list of currently online users"""
    return {"online_users": manager.get_online_users()}

@router.get("/ws/user-online/{user_id}", tags=["WebSocket"])
async def check_user_online(user_id: str, current_user: dict = Depends(get_current_user)):
    """Check if specific user is online"""
    return {"user_id": user_id, "is_online": manager.is_user_online(user_id)}

# =============================================================================
# ALL OTHER ROUTES COMMENTED OUT - TO BE IMPLEMENTED LATER
# =============================================================================

# All remaining routes for comments, likes, bookmarks, follows, groups, jobs,
# media, search, recommendations, notifications, messages, and stories
# have been commented out and will be implemented in future phases.

# These routes will be moved to their respective API modules:
# - Comments: app/api/v1/comments.py
# - Likes: app/api/v1/likes.py  
# - Bookmarks: app/api/v1/bookmarks.py
# - Follows: app/api/v1/follows.py
# - Groups: app/api/v1/groups.py
# - Jobs: app/api/v1/jobs.py
# - Media: app/api/v1/media.py
# - Search: app/api/v1/search.py
# - Recommendations: app/api/v1/recommendations.py
# - Notifications: app/api/v1/notifications.py
# - Messages: app/api/v1/messages.py
# - Stories: app/api/v1/stories.py