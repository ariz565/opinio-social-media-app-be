from fastapi import APIRouter, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm

# Import business logic functions from v1
from app.api.v1.auth_functions import (
    register_new_user_logic, login_user_logic, refresh_token_logic,
    verify_email_logic, resend_verification_logic,
    request_password_reset_logic, verify_password_reset_logic
)
from app.api.v1.user_functions import (
    get_user_profile_logic, update_user_profile_logic
)
from app.schemas.user import (
    UserRegistration, UserLogin, EmailVerification, RefreshToken,
    PasswordResetRequest, PasswordResetVerify, EmailRequest
)
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
async def get_current_user_profile(request: Request):
    """Get current user profile"""
    return await get_user_profile_logic(request)

@router.put("/users/me")
async def update_current_user_profile(request: Request):
    """Update current user profile"""
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