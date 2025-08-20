"""
Dependency injection for the API routes
"""

from fastapi import Depends, HTTPException, status
from app.core.auth import get_current_user as _get_current_user, get_current_active_user as _get_current_active_user

# Re-export authentication dependencies for easier imports
get_current_user = _get_current_user
get_current_active_user = _get_current_active_user

# Optional authentication - returns None if no token provided
async def get_current_user_optional(
    credentials = None
):
    """Get current user if authenticated, otherwise return None"""
    if not credentials:
        return None
    
    try:
        return await _get_current_user(credentials)
    except HTTPException:
        return None
