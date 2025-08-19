from fastapi import HTTPException, status, Request, Depends
from app.services.user_service import get_user_profile, verify_token_and_get_user
from app.models.user import update_user
from app.database.mongo_connection import get_database
from app.utils.validators import sanitize_input_dict
from app.utils.helpers import serialize_user

async def get_current_user_from_token(db, token):
    """Helper function to get current user from token"""
    user = await verify_token_and_get_user(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user

async def get_user_profile_logic(request: Request):
    """Business logic for getting user profile"""
    try:
        # Get database
        db = await get_database()
        
        # Get current user from token (this would need to be implemented)
        # For now, let's extract user_id from headers or token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        token = auth_header.split(" ")[1]
        
        # Get current user
        current_user = await get_current_user_from_token(db, token)
        
        # Get user profile
        user_profile = await get_user_profile(db, current_user["id"])
        
        return {
            "message": "User profile retrieved successfully",
            "user": user_profile
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user profile"
        )

async def update_user_profile_logic(request: Request):
    """Business logic for updating user profile"""
    try:
        # Get database
        db = await get_database()
        
        # Get current user from token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        token = auth_header.split(" ")[1]
        
        # Get current user
        current_user = await get_current_user_from_token(db, token)
        
        # Get JSON data from request
        update_data = await request.json()
        
        # Sanitize input data
        sanitized_data = sanitize_input_dict(update_data)
        
        # Update user profile
        updated_user = await update_user(db, current_user["id"], sanitized_data)
        
        # Serialize the updated user
        if updated_user:
            updated_user = serialize_user(updated_user)
        
        return {
            "message": "User profile updated successfully",
            "user": updated_user
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile"
        )
