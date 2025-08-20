from fastapi import HTTPException, status
from jose import jwt, JWTError
from datetime import datetime

from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token, decode_token
from app.models.user import (
    get_user_by_email, get_user_by_username, create_user, get_user_by_id, 
    update_last_login, check_user_exists, update_user
)
from app.models.account import (
    get_account_by_provider_id, create_account, update_account_last_login
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
    """Register a new user with validation - SECURE: Only allows regular user role"""
    # Sanitize inputs
    sanitized_data = sanitize_input_dict(user_data)
    
    # SECURITY: Remove any role/status/privilege fields that users might try to inject
    # Only allow specific safe fields for regular user registration
    allowed_fields = {
        'email', 'username', 'password', 'full_name', 'bio', 'profile_picture'
    }
    sanitized_data = {k: v for k, v in sanitized_data.items() if k in allowed_fields}
    
    email = sanitized_data.get("email", "").strip().lower()
    username = sanitized_data.get("username", "").strip().lower()
    password = sanitized_data.get("password", "")
    full_name = sanitized_data.get("full_name", "").strip()
    
    # SECURITY: Explicitly check for role injection attempts
    if 'role' in user_data or 'status' in user_data or 'email_verified' in user_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid registration data - privilege escalation attempt detected"
        )
    
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
            # Generate OTP for email verification
            otp_code = await create_otp(db, email, OTP_TYPE_EMAIL_VERIFICATION, created_user["_id"])
            
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
        otp_code = await create_otp(db, email, OTP_TYPE_EMAIL_VERIFICATION, user["_id"])
        
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
        
        # Check if account exists by Google ID
        existing_account = await get_account_by_provider_id(db, "google", google_id)
        if existing_account:
            # Update last login
            await update_account_last_login(db, existing_account["_id"])
            return existing_account
        
        # Check if regular user exists by email
        existing_user = await get_user_by_email(db, email)
        if existing_user:
            # Create linked Google account for existing user
            account_data = {
                "email": email,
                "full_name": google_user_info.get("name", ""),
                "provider": "google",
                "provider_id": google_id,
                "profile_picture": google_user_info.get("picture"),
                "linked_user_id": existing_user["_id"],
                "provider_data": google_user_info
            }
            created_account = await create_account(db, account_data)
            return created_account
        
        # Create new standalone Google account (not linked to any user)
        account_data = {
            "email": email,
            "full_name": google_user_info.get("name", ""),
            "provider": "google",
            "provider_id": google_id,
            "profile_picture": google_user_info.get("picture"),
            "provider_data": google_user_info,
            "linked_user_id": None  # Standalone OAuth account
        }
        
        # Create account
        created_account = await create_account(db, account_data)
        
        if not created_account:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create account"
            )
        
        return created_account
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process Google user"
        )


async def request_password_reset(db, email):
    """Request password reset for a user"""
    try:
        # Sanitize email input
        email = email.strip().lower()
        
        # Validate email format
        if not validate_email(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        
        # Check if user exists
        user = await get_user_by_email(db, email)
        if not user:
            # For security, don't reveal if email exists or not
            return {
                "message": "If the email exists in our system, a password reset link has been sent",
                "email_sent": True
            }
        
        # Generate reset code (6-digit OTP)
        from app.models.otp import create_otp, OTP_TYPE_PASSWORD_RESET
        reset_code = await create_otp(db, email, OTP_TYPE_PASSWORD_RESET)
        
        # Send password reset email
        reset_link = f"{settings['FRONTEND_URL']}/reset-password?email={email}&code={reset_code}"
        
        email_sent = await email_service.send_password_reset_email(
            to_email=email,
            full_name=user.get("full_name", "User"),
            reset_code=reset_code,
            reset_link=reset_link
        )
        
        return {
            "message": "Password reset instructions have been sent to your email",
            "email_sent": email_sent
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Log the actual error but don't expose it
        print(f"Password reset request error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process password reset request"
        )


async def verify_password_reset(db, email, reset_code, new_password):
    """Verify password reset code and update password"""
    try:
        # Sanitize inputs
        email = email.strip().lower()
        reset_code = reset_code.strip()
        
        # Validate inputs
        if not validate_email(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        
        if not validate_password(new_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters with uppercase, lowercase and numbers"
            )
        
        # Check if user exists
        user = await get_user_by_email(db, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify reset code
        from app.models.otp import verify_otp, OTP_TYPE_PASSWORD_RESET
        otp_valid = await verify_otp(db, email, reset_code, OTP_TYPE_PASSWORD_RESET)
        
        if not otp_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset code"
            )
        
        # Hash new password
        hashed_password = get_password_hash(new_password)
        
        # Update user's password
        update_data = {
            "password": hashed_password,
            "updated_at": datetime.utcnow()
        }
        
        await update_user(db, user["_id"], update_data)
        
        # Optionally, invalidate all existing sessions/tokens here
        # This would require implementing a token blacklist system
        
        return {
            "message": "Password has been successfully reset. Please login with your new password."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Password reset verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )
