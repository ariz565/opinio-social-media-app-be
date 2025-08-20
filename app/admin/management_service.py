from fastapi import HTTPException, status
from datetime import datetime
import logging

from app.models.admin import (
    create_admin, get_admin_count, get_moderator_count, get_all_admins,
    check_admin_exists, ADMIN_ROLE_ADMIN, ADMIN_ROLE_MODERATOR, ADMIN_STATUS_ACTIVE
)
from app.models.user import (
    get_user_by_id, update_user, USER_ROLE_USER,
    USER_STATUS_ACTIVE, USER_STATUS_SUSPENDED, USER_STATUS_DELETED
)
from app.core.security import get_password_hash
from app.utils.validators import validate_email, validate_username, validate_password, validate_full_name
from app.utils.helpers import serialize_user
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def create_admin_user_service(db, admin_data: dict, provided_admin_secret: str):
    """
    Create an admin user with admin secret validation
    Enhanced security version of the original function
    """
    try:
        # Validate admin secret
        if provided_admin_secret != settings["ADMIN_SECRET"]:
            logger.warning("Invalid admin secret provided for user creation")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid admin secret key"
            )
        
        # Extract and validate data
        email = admin_data.get("email", "").strip().lower()
        username = admin_data.get("username", "").strip().lower()
        password = admin_data.get("password", "")
        full_name = admin_data.get("full_name", "").strip()
        bio = admin_data.get("bio", "System Administrator")
        
        # Validate all inputs
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
                detail="Full name must be between 2-50 characters"
            )
        
        # Check if user already exists
        from app.models.user import check_user_exists
        if await check_user_exists(db, email, username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email or username already exists"
            )
        
        # Hash password
        hashed_password = get_password_hash(password)
        
        # Prepare admin user data
        admin_user_data = {
            "email": email,
            "username": username,
            "password": hashed_password,
            "full_name": full_name,
            "bio": bio,
            "role": ADMIN_ROLE_ADMIN,
            "permissions": []
        }
        
        # Create admin user
        created_admin = await create_admin(db, admin_user_data)
        
        if not created_admin:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create admin user"
            )
        
        # Get total admin count
        admin_count = await get_admin_count(db)
        
        # Serialize the user for response
        serialized_admin = serialize_user(created_admin)
        
        logger.info(f"Admin user created successfully: {email}")
        
        return {
            "message": f"Admin user created successfully. Total admin users: {admin_count}",
            "user": serialized_admin
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin user creation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create admin user"
        )


async def get_admin_dashboard_stats(db):
    """Get admin dashboard statistics"""
    try:
        # Count total users (only regular users)
        total_users = await db.users.count_documents({})
        
        # Count admins and moderators from admin collection
        total_admins = await get_admin_count(db)
        total_moderators = await get_moderator_count(db)
        
        # Count OAuth accounts
        try:
            total_oauth_accounts = await db.accounts.count_documents({})
        except:
            total_oauth_accounts = 0
        
        # Count posts (if posts collection exists)
        try:
            total_posts = await db.posts.count_documents({})
        except:
            total_posts = 0
        
        # Count active users today (users with last_login today)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        active_users_today = await db.users.count_documents({
            "last_login": {"$gte": today_start}
        })
        
        # Count new registrations today
        new_registrations_today = await db.users.count_documents({
            "created_at": {"$gte": today_start}
        })
        
        # Count flagged content (placeholder)
        flagged_content = 0
        
        return {
            "total_users": total_users,
            "total_admins": total_admins,
            "total_moderators": total_moderators,
            "total_oauth_accounts": total_oauth_accounts,
            "total_posts": total_posts,
            "active_users_today": active_users_today,
            "new_registrations_today": new_registrations_today,
            "flagged_content": flagged_content
        }
        
    except Exception as e:
        logger.error(f"Dashboard stats error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get dashboard statistics"
        )


async def manage_user_action(db, admin_user_id: str, target_user_id: str, action: str, reason: str = None):
    """
    Admin action to manage users (suspend, activate, delete, etc.)
    
    Args:
        db: Database connection
        admin_user_id: ID of the admin performing the action
        target_user_id: ID of the user being managed
        action: Action to perform (suspend, activate, delete, promote, demote)
        reason: Reason for the action
    """
    try:
        # Get target user
        target_user = await get_user_by_id(db, target_user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prevent admin from targeting themselves for certain actions
        if str(target_user["_id"]) == admin_user_id and action in ["suspend", "delete", "demote"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot perform this action on yourself"
            )
        
        # Perform action - only status changes allowed for regular users
        update_data = {"updated_at": datetime.utcnow()}
        
        if action == "suspend":
            update_data["status"] = USER_STATUS_SUSPENDED
        elif action == "activate":
            update_data["status"] = USER_STATUS_ACTIVE
        elif action == "delete":
            update_data["status"] = USER_STATUS_DELETED
        elif action == "promote":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot promote regular users. Admins are created separately."
            )
        elif action == "demote":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Regular users cannot be demoted. Use admin management endpoints for admins."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid action. Valid actions: suspend, activate, delete"
            )
        
        # Update user
        await update_user(db, target_user_id, update_data)
        
        # Log the action
        logger.info(f"Admin {admin_user_id} performed action '{action}' on user {target_user_id}. Reason: {reason}")
        
        return {
            "message": f"Action '{action}' performed successfully on user {target_user['email']}",
            "action": action,
            "target_user": target_user["email"],
            "reason": reason
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User management action error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform user management action"
        )
