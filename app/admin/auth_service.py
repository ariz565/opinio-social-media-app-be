from fastapi import HTTPException, status
from datetime import datetime
import logging

from app.core.security import verify_password, create_access_token, create_refresh_token
from app.models.admin import get_admin_by_email, update_admin_last_login, ADMIN_ROLE_ADMIN, ADMIN_STATUS_ACTIVE
from app.config import get_settings
from app.utils.helpers import serialize_user

logger = logging.getLogger(__name__)
settings = get_settings()


async def authenticate_admin(db, email: str, password: str, admin_secret: str):
    """
    Authenticate admin user with additional security checks
    
    Args:
        db: Database connection
        email: Admin email
        password: Admin password  
        admin_secret: Admin secret key for additional security
        
    Returns:
        dict: Admin user data if authentication successful
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Verify admin secret first
        if admin_secret != settings["ADMIN_SECRET"]:
            logger.warning(f"Invalid admin secret attempt for email: {email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid admin credentials"
            )
        
        # Get admin by email
        admin = await get_admin_by_email(db, email)
        if not admin:
            logger.warning(f"Admin login attempt with non-existent email: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin credentials"
            )
        
        # Check if user is actually an admin or moderator
        if admin.get("role") not in [ADMIN_ROLE_ADMIN, "moderator"]:
            logger.warning(f"Non-admin user attempted admin login: {email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        
        # Verify password
        if not verify_password(password, admin.get("password", "")):
            logger.warning(f"Invalid password for admin login: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin credentials"
            )
        
        # Check if admin account is active
        if admin.get("status") != ADMIN_STATUS_ACTIVE:
            logger.warning(f"Inactive admin account login attempt: {email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin account is not active"
            )
        
        # Update last login
        await update_admin_last_login(db, admin["_id"])
        
        # Log successful admin login
        logger.info(f"Successful admin login: {email}")
        
        return admin
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )


async def generate_admin_tokens(admin_user: dict):
    """
    Generate access and refresh tokens for admin user
    
    Args:
        admin_user: Admin user dictionary
        
    Returns:
        dict: Tokens and expiration info
    """
    try:
        user_id = str(admin_user["_id"])
        
        # Generate tokens with admin-specific claims
        access_token = create_access_token(
            data={
                "sub": user_id,
                "email": admin_user["email"],
                "role": admin_user["role"],
                "type": "admin_access"
            }
        )
        
        refresh_token = create_refresh_token(
            data={
                "sub": user_id,
                "type": "admin_refresh"
            }
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings["ACCESS_TOKEN_EXPIRE_MINUTES"] * 60
        }
        
    except Exception as e:
        logger.error(f"Token generation error for admin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token generation failed"
        )


async def admin_login_service(db, email: str, password: str, admin_secret: str):
    """
    Complete admin login service
    
    Args:
        db: Database connection
        email: Admin email
        password: Admin password
        admin_secret: Admin secret key
        
    Returns:
        dict: Login response with user data and tokens
    """
    try:
        # Authenticate admin
        admin_user = await authenticate_admin(db, email, password, admin_secret)
        
        # Generate tokens
        tokens = await generate_admin_tokens(admin_user)
        
        # Serialize admin user data (remove sensitive fields)
        admin_data = serialize_user(admin_user)
        
        return {
            "message": "Admin login successful",
            "admin": admin_data,
            **tokens
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin login service error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin login service error"
        )
