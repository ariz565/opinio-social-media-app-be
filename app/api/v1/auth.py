from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from app.services.user_service import (
    register_user, authenticate_user, generate_user_tokens, 
    refresh_user_token, get_user_profile, verify_email_otp, resend_verification_otp,
    create_or_get_google_user
)
from app.schemas.user import AdminUserCreation, AdminUserResponse
from app.api.v1.auth_functions import create_admin_user_logic
# Temporarily commented out for testing
# from app.services.google_oauth_service import google_oauth_service
from app.core.auth import get_current_active_user
from app.database.mongo_connection import get_database
from app.utils.validators import sanitize_input_dict

router = APIRouter()

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_new_user(request: Request):
    """Register a new user"""
    try:
        # Get database directly instead of using dependency injection
        db = await get_database()
        
        # Get JSON data from request
        user_data = await request.json()
        
        # Register user
        created_user = await register_user(db, user_data)
        
        return {
            "message": "User registered successfully. Please check your email for verification code.",
            "user": created_user,
            "email_sent": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login")
async def login_user(request: Request):
    """Login user and get access token"""
    try:
        # Get database directly
        db = await get_database()
        
        # Get JSON data from request
        login_data = await request.json()
        
        email = login_data.get("email", "").strip()
        password = login_data.get("password", "")
        
        if not email or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and password are required"
            )
        
        # Authenticate user
        user = await authenticate_user(db, email, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Generate tokens
        tokens = await generate_user_tokens(user)
        
        return {
            "message": "Login successful",
            "user": user,
            **tokens
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/refresh")
async def refresh_access_token(request: Request, db = Depends(get_database)):
    """Get new access token using refresh token"""
    try:
        # Get JSON data from request
        token_data = await request.json()
        
        refresh_token = token_data.get("refresh_token", "")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token is required"
            )
        
        # Refresh token
        new_tokens = await refresh_user_token(db, refresh_token)
        
        if not new_tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return {
            "message": "Token refreshed successfully",
            **new_tokens
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.get("/me")
async def get_current_user_profile(
    current_user = Depends(get_current_active_user)
):
    """Get current user profile"""
    return {
        "message": "User profile retrieved successfully",
        "user": current_user
    }

@router.post("/logout")
async def logout_user(current_user = Depends(get_current_active_user)):
    """Logout user (client should remove tokens)"""
    return {
        "message": "Logout successful. Please remove tokens from client storage."
    }

@router.get("/profile/{user_id}")
async def get_user_profile_by_id(
    user_id: str,
    db = Depends(get_database)
):
    """Get user profile by ID (public endpoint)"""
    try:
        user = await get_user_profile(db, user_id)
        
        # Remove sensitive information for public view
        public_user = {
            "_id": user["_id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "profile_picture": user.get("profile_picture"),
            "bio": user.get("bio", ""),
            "followers_count": user.get("followers_count", 0),
            "following_count": user.get("following_count", 0),
            "posts_count": user.get("posts_count", 0),
            "created_at": user["created_at"]
        }
        
        return {
            "message": "User profile retrieved successfully",
            "user": public_user
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile"
        )

@router.post("/verify-email")
async def verify_email_address(request: Request, db = Depends(get_database)):
    """Verify email using OTP"""
    try:
        # Get JSON data from request
        verification_data = await request.json()
        
        email = verification_data.get("email", "").strip()
        otp_code = verification_data.get("otp_code", "").strip()
        
        if not email or not otp_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and OTP code are required"
            )
        
        # Verify email
        verified_user = await verify_email_otp(db, email, otp_code)
        
        return {
            "message": "Email verified successfully",
            "user": verified_user
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )

@router.post("/resend-verification")
async def resend_verification_email(request: Request, db = Depends(get_database)):
    """Resend verification email"""
    try:
        # Get JSON data from request
        resend_data = await request.json()
        
        email = resend_data.get("email", "").strip()
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required"
            )
        
        # Resend verification email
        await resend_verification_otp(db, email)
        
        return {
            "message": "Verification email sent successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend verification email"
        )


@router.post("/create-admin", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_user(admin_data: AdminUserCreation):
    """
    Create an admin user with admin secret key
    
    This endpoint allows creation of admin users by providing the correct admin secret key.
    Admin users have elevated privileges and can access all application functionality.
    
    Required fields:
    - admin_secret: The secret key from environment variable ADMIN_SECRET
    - email: Valid email address for the admin user
    - username: Unique username (3-20 characters, alphanumeric with underscores)
    - password: Strong password (8+ chars, uppercase, lowercase, number)
    - full_name: Admin user's full name
    - bio: Optional bio (defaults to "System Administrator")
    
    Security considerations:
    - Admin secret must match exactly with ADMIN_SECRET environment variable
    - All user validation rules apply (email format, username uniqueness, password strength)
    - Admin users are automatically email verified
    - Admin role grants access to all system functionality
    """
    return await create_admin_user_logic(admin_data)


# Google OAuth endpoints - temporarily commented out for testing
"""
@router.get("/google/login")
async def google_login():
    try:
        auth_url, state = google_oauth_service.generate_auth_url()
        
        return {
            "auth_url": auth_url,
            "state": state,
            "message": "Redirect user to this URL for Google authentication"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate Google auth URL"
        )

@router.post("/google/callback")
async def google_callback(request: Request, db = Depends(get_database)):
    try:
        callback_data = await request.json()
        
        code = callback_data.get("code", "")
        state = callback_data.get("state", "")
        
        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code is required"
            )
        
        google_user_info = await google_oauth_service.verify_google_token(code, state)
        user = await create_or_get_google_user(db, google_user_info)
        tokens = await generate_user_tokens(user)
        
        return {
            "message": "Google authentication successful",
            "user": user,
            **tokens
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google authentication failed"
        )

@router.post("/google/token")
async def google_token_login(request: Request, db = Depends(get_database)):
    try:
        token_data = await request.json()
        
        credential = token_data.get("credential")
        access_token = token_data.get("access_token")
        
        if credential:
            google_user_info = await google_oauth_service.verify_google_id_token(credential)
        elif access_token:
            google_user_info = await google_oauth_service.get_user_info_from_token(access_token)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either credential (ID token) or access_token is required"
            )
        
        user = await create_or_get_google_user(db, google_user_info)
        tokens = await generate_user_tokens(user)
        
        return {
            "message": "Google authentication successful",
            "user": user,
            **tokens
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google authentication failed: {str(e)}"
        )
"""
