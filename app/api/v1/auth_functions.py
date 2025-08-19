from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.services.user_service import (
    register_user, authenticate_user, generate_user_tokens, 
    refresh_user_token, get_user_profile, verify_email_otp, resend_verification_otp,
    create_or_get_google_user
)
from app.core.auth import get_current_active_user
from app.database.mongo_connection import get_database
from app.models.user import update_user
from app.schemas.user import UserRegistration, UserLogin, EmailVerification, RefreshToken
from app.utils.validators import sanitize_input_dict


async def register_new_user_logic(user_data: UserRegistration):
    """Business logic for user registration"""
    try:
        # Get database directly
        db = await get_database()
        
        # Convert Pydantic model to dict
        user_dict = user_data.dict()
        
        # Register user
        created_user = await register_user(db, user_dict)
        
        return {
            "message": "User registered successfully. Please check your email for verification code.",
            "user": created_user,
            "email_sent": created_user.get("email_sent", False)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


async def login_user_logic(login_data: UserLogin):
    """Business logic for user login"""
    try:
        # Get database directly
        db = await get_database()
        
        # Extract data from Pydantic model
        email = login_data.email.strip()
        password = login_data.password
        otp_code = login_data.otp_code.strip() if login_data.otp_code else None
        
        if not email or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and password are required"
            )
        
        # Authenticate user credentials
        user = await authenticate_user(db, email, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if user email is verified
        if not user.get("email_verified", False):
            # First-time login: user must provide OTP
            if not otp_code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email verification required. Please provide the OTP code sent to your email."
                )
            
            # Verify OTP and mark email as verified
            otp_verified = await verify_email_otp(db, email, otp_code)
            if not otp_verified:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired OTP code"
                )
            
            # Update user to mark email as verified
            await update_user(db, user["_id"], {"email_verified": True})
            user["email_verified"] = True
        
        # Generate tokens for successful login
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


async def refresh_token_logic(refresh_data: RefreshToken):
    """Business logic for token refresh"""
    try:
        # Get database
        db = await get_database()
        
        # Extract refresh token from Pydantic model
        refresh_token = refresh_data.refresh_token
        
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token is required"
            )
        
        # Refresh the token
        new_tokens = await refresh_user_token(db, refresh_token)
        
        return new_tokens
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


async def verify_email_logic(verification_data: EmailVerification):
    """Business logic for email verification"""
    try:
        # Get database
        db = await get_database()
        
        # Extract data from Pydantic model
        email = verification_data.email.strip()
        otp_code = verification_data.otp_code.strip()
        
        if not email or not otp_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and OTP code are required"
            )
        
        # Verify OTP
        result = await verify_email_otp(db, email, otp_code)
        
        if result:
            return {
                "message": "Email verified successfully",
                "email_verified": True
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP code"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )


async def resend_verification_logic(email_data: EmailVerification):
    """Business logic for resending verification email"""
    try:
        # Get database
        db = await get_database()
        
        # Extract email from Pydantic model  
        email = email_data.email.strip()
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required"
            )
        
        # Resend verification OTP
        result = await resend_verification_otp(db, email)
        
        if result:
            return {
                "message": "Verification email sent successfully",
                "email_sent": True
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to send verification email"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend verification email"
        )
