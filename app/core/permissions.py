from fastapi import HTTPException, status, Depends
from app.core.auth import get_current_active_user
from app.models.user import USER_ROLE_USER
from app.models.admin import ADMIN_ROLE_ADMIN, ADMIN_ROLE_MODERATOR

def require_admin(current_user: dict = Depends(get_current_active_user)):
    """
    Dependency to require admin role
    
    Usage:
    @router.get("/admin-only")
    async def admin_endpoint(current_user: dict = Depends(require_admin)):
        return {"message": "This is an admin-only endpoint"}
    """
    # Only users from the admin collection can have admin role
    if current_user.get("role") != ADMIN_ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

def require_admin_or_moderator(current_user: dict = Depends(get_current_active_user)):
    """
    Dependency to require admin or moderator role
    
    Usage:
    @router.get("/mod-or-admin")
    async def mod_endpoint(current_user: dict = Depends(require_admin_or_moderator)):
        return {"message": "This requires moderator or admin privileges"}
    """
    # Only users from the admin collection can have admin/moderator roles
    if current_user.get("role") not in [ADMIN_ROLE_ADMIN, ADMIN_ROLE_MODERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator or admin privileges required"
        )
    return current_user

def validate_permission(user: dict, required_role: str) -> bool:
    """
    Validate if user has required permission level
    
    Args:
        user: User dictionary with role information
        required_role: Required role string (admin, moderator, user)
        
    Returns:
        bool: True if user has required permission
    """
    # Admin collection users have higher privileges
    if user.get("role") == ADMIN_ROLE_ADMIN:
        return True
    
    if user.get("role") == ADMIN_ROLE_MODERATOR and required_role in ["moderator", "user"]:
        return True
    
    if user.get("role") == USER_ROLE_USER and required_role == "user":
        return True
        
    return False

def get_role_hierarchy() -> dict:
    """Get role hierarchy levels for permission checking"""
    return {
        USER_ROLE_USER: 1,
        ADMIN_ROLE_MODERATOR: 2,
        ADMIN_ROLE_ADMIN: 3
    }

def get_user_role_level(user: dict) -> int:
    """Get numerical level for user role"""
    hierarchy = get_role_hierarchy()
    return hierarchy.get(user.get("role"), 0)

def check_admin_permissions(user: dict) -> bool:
    """
    Check if user has admin permissions
    
    Args:
        user: User dictionary
        
    Returns:
        bool: True if user is admin
    """
    return user.get("role") == ADMIN_ROLE_ADMIN

def check_moderator_permissions(user: dict) -> bool:
    """
    Check if user has moderator or admin permissions
    
    Args:
        user: User dictionary
        
    Returns:
        bool: True if user is moderator or admin
    """
    return user.get("role") in [ADMIN_ROLE_ADMIN, ADMIN_ROLE_MODERATOR]

def can_manage_user(admin_user: dict, target_user: dict) -> bool:
    """
    Check if admin can manage target user
    
    Args:
        admin_user: Admin user performing action
        target_user: Target user being managed
        
    Returns:
        bool: True if admin can manage target user
    """
    admin_level = get_user_role_level(admin_user)
    target_level = get_user_role_level(target_user)
    
    # Admins can manage anyone except other admins of same level
    if admin_user.get("role") == ADMIN_ROLE_ADMIN:
        return target_user.get("role") != ADMIN_ROLE_ADMIN
    
    # Moderators can only manage regular users
    if admin_user.get("role") == ADMIN_ROLE_MODERATOR:
        return target_user.get("role") == USER_ROLE_USER
    
    return False
