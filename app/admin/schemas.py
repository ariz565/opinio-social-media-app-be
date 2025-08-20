from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime


class AdminLogin(BaseModel):
    """Schema for admin login - separate from regular user login"""
    email: EmailStr
    password: str
    admin_secret: str  # Additional security layer for admin login
    
    
class AdminUserCreation(BaseModel):
    """Schema for admin user creation - requires admin secret"""
    admin_secret: str
    email: EmailStr
    username: str
    password: str
    full_name: str
    bio: Optional[str] = "System Administrator"
    
    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3 or len(v) > 20:
            raise ValueError('Username must be between 3-20 characters')
        if not v.replace('_', '').isalnum():
            raise ValueError('Username must be alphanumeric (underscores allowed)')
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        return v


class AdminResponse(BaseModel):
    """Schema for admin user response (without sensitive data)"""
    id: str
    email: str
    username: str
    full_name: str
    bio: str
    role: str
    status: str
    email_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]


class AdminLoginResponse(BaseModel):
    """Schema for admin login response"""
    message: str
    admin: AdminResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AdminUserResponse(BaseModel):
    """Schema for admin user creation response"""
    message: str
    user: AdminResponse


class AdminDashboardStats(BaseModel):
    """Schema for admin dashboard statistics"""
    total_users: int
    total_admins: int
    total_posts: int
    active_users_today: int
    new_registrations_today: int
    flagged_content: int


class UserManagementAction(BaseModel):
    """Schema for admin user management actions"""
    user_id: str
    action: str  # suspend, activate, delete, promote, demote
    reason: Optional[str] = None
    duration_days: Optional[int] = None  # For temporary suspensions
