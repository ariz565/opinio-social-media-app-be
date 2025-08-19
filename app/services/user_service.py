from fastapi import HTTPException, status
from jose import jwt, JWTError

from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token, decode_token
from app.models.user import (
    get_user_by_email, get_user_by_username, create_user, get_user_by_id, 
    update_last_login, check_user_exists, update_user, get_user_by_google_id
)
from app.models.otp import create_otp, verify_otp, OTP_TYPE_EMAIL_VERIFICATION
from app.services.email_service import email_service
from app.utils.validators import (
    validate_email, validate_username, validate_password, validate_full_name,
    sanitize_input_dict
)
from app.utils.helpers import serialize_user, create_success_response, create_error_response
from app.config import get_settings

settings = get_settings()

async def register_user(db, user_data):
    """Register a new user with validation"""
    # Sanitize inputs
    sanitized_data = sanitize_input_dict(user_data)
    
    email = sanitized_data.get("email", "").strip().lower()
    username = sanitized_data.get("username", "").strip().lower()
    password = sanitized_data.get("password", "")
    full_name = sanitized_data.get("full_name", "").strip()
    
    # Validate inputs
    if not validate_email(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )
    
    if not validate_username(username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be alphanumeric (with underscores) and between 3-20 characters"
        )
    
    if not validate_password(password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters with uppercase, lowercase and numbers"
        )
    
    if not validate_full_name(full_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name must be between 2-50 characters and contain only letters, spaces, hyphens, and apostrophes"
        )
    
    # Check database availability
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is currently unavailable. Please try again later."
        )
    
    try:
        # Check if user already exists
        if await check_user_exists(db, email, username):
            # Check specific field for better error message
            if await get_user_by_email(db, email):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered"
                )
            if await get_user_by_username(db, username):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Username already taken"
                )
        
        # Hash the password
        hashed_password = get_password_hash(password)
        
        # Create user data
        user_create_data = {
            "email": email,
            "username": username,
            "password": hashed_password,
            "full_name": full_name,
            "profile_picture": sanitized_data.get("profile_picture"),
            "bio": sanitized_data.get("bio", "")
        }
        
        # Create user in database
        created_user = await create_user(db, user_create_data)
        
        if not created_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        # Generate and send verification OTP
        try:
            otp_code = await create_otp(db, created_user["_id"], email, OTP_TYPE_EMAIL_VERIFICATION)
            
            # Send verification email
            email_sent = await email_service.send_verification_email(
                to_email=email,
                full_name=full_name,
                otp_code=otp_code
            )
            
            if not email_sent:
                # Still return success but indicate email issue
                return {
                    **serialize_user(created_user),
                    "email_sent": False,
                    "message": "User created but verification email failed. Please request a new verification email."
                }
        
        except Exception as e:
            # Still return success but indicate email issue
            return {
                **serialize_user(created_user),
                "email_sent": False,
                "message": "User created but verification email failed. Please request a new verification email."
            }
        
        # Serialize user data before returning
        serialized_user = serialize_user(created_user)
        serialized_user["email_sent"] = True
        return serialized_user
    
    except HTTPException:
        # Re-raise HTTP exceptions (business logic errors)
        raise
    except Exception as e:
        # Handle actual database connection errors
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error. Please try again later."
        )

async def authenticate_user(db, email, password):
    """Authenticate user with email and password"""
    if not email or not password:
        return None
    
    # Get user by email
    user = await get_user_by_email(db, email.lower())
    if not user:
        return None
    
    # Check if user is active
    if user.get("status") != "active":
        return None
    
    # Verify password
    if not verify_password(password, user.get("password", "")):
        return None
    
    # Update last login
    await update_last_login(db, user["_id"])
    
    # Remove password from user object and serialize
    user.pop("password", None)
    
    return serialize_user(user)

async def generate_user_tokens(user):
    """Generate access and refresh tokens for user"""
    # Create token data - handle both serialized and raw user objects
    user_id = user.get("id") or str(user.get("_id"))
    
    token_data = {
        "user_id": user_id,
        "email": user["email"],
        "role": user.get("role", "user")
    }
    
    # Generate tokens
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data={"user_id": user_id})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings["ACCESS_TOKEN_EXPIRE_MINUTES"] * 60  # in seconds
    }

async def refresh_user_token(db, refresh_token):
    """Get new access token using refresh token"""
    try:
        # Decode refresh token
        payload = decode_token(refresh_token)
        if not payload:
            return None
        
        user_id = payload.get("user_id")
        if not user_id:
            return None
        
        # Get user from database
        user = await get_user_by_id(db, user_id)
        if not user or user.get("status") != "active":
            return None
        
        # Remove password from user object
        user.pop("password", None)
        
        # Generate new tokens
        return await generate_user_tokens(user)
    
    except Exception:
        return None

async def get_user_profile(db, user_id):
    """Get user profile by ID"""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Remove sensitive information and serialize
    user.pop("password", None)
    
    return serialize_user(user)

async def verify_token_and_get_user(db, token):
    """Verify JWT token and return user"""
    try:
        # Decode token
        payload = decode_token(token)
        if not payload:
            return None
        
        user_id = payload.get("user_id")
        if not user_id:
            return None
        
        # Get user from database
        user = await get_user_by_id(db, user_id)
        if not user or user.get("status") != "active":
            return None
        
        # Remove password from user object and serialize
        user.pop("password", None)
        
        return serialize_user(user)
    
    except Exception:
        return None

async def verify_email_otp(db, email, otp_code):
    """Verify email using OTP"""
    try:
        # Verify OTP
        otp_doc = await verify_otp(db, email, otp_code, OTP_TYPE_EMAIL_VERIFICATION)
        if not otp_doc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP code"
            )
        
        # Get user
        user = await get_user_by_email(db, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update user email verification status
        updated_user = await update_user(db, user["_id"], {"email_verified": True})
        
        if updated_user:
            updated_user.pop("password", None)
        
        return serialize_user(updated_user)
    
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )

async def resend_verification_otp(db, email):
    """Resend verification OTP"""
    try:
        # Get user
        user = await get_user_by_email(db, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if already verified
        if user.get("email_verified", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already verified"
            )
        
        # Generate new OTP
        otp_code = await create_otp(db, user["_id"], email, OTP_TYPE_EMAIL_VERIFICATION)
        
        # Send verification email
        email_sent = await email_service.send_verification_email(
            to_email=email,
            full_name=user.get("full_name", "User"),
            otp_code=otp_code
        )
        
        if not email_sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email"
            )
        
        return True
    
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend verification email"
        )

async def create_or_get_google_user(db, google_user_info):
    """Create or get user from Google OAuth info"""
    try:
        email = google_user_info.get("email")
        google_id = google_user_info.get("google_id")
        
        # Check if user exists by Google ID
        existing_user = await get_user_by_google_id(db, google_id)
        if existing_user:
            # Update last login
            await update_last_login(db, existing_user["_id"])
            # Remove password from response and serialize
            existing_user.pop("password", None)
            return serialize_user(existing_user)
        
        # Check if user exists by email
        existing_user = await get_user_by_email(db, email)
        if existing_user:
            # Link Google account to existing user
            await update_user(db, existing_user["_id"], {
                "google_id": google_id,
                "auth_provider": "google"
            })
            # Update last login
            await update_last_login(db, existing_user["_id"])
            # Remove password from response and serialize
            existing_user.pop("password", None)
            return serialize_user(existing_user)
        
        # Create new user
        # Generate username from email
        username = email.split("@")[0]
        username_counter = 1
        
        # Ensure username is unique
        while await get_user_by_username(db, username):
            username = f"{email.split('@')[0]}{username_counter}"
            username_counter += 1
        
        user_data = {
            "email": email,
            "username": username,
            "full_name": google_user_info.get("full_name", ""),
            "profile_picture": google_user_info.get("profile_picture"),
            "email_verified": google_user_info.get("email_verified", False),
            "auth_provider": "google",
            "google_id": google_id
        }
        
        # Create user
        created_user = await create_user(db, user_data)
        
        if not created_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        return serialize_user(created_user)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process Google user"
        )
