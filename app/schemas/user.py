from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime


class UserRegistration(BaseModel):
    """Schema for user registration"""
    email: EmailStr
    username: str
    password: str
    full_name: str
    bio: Optional[str] = ""
    profile_picture: Optional[str] = None
    
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


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str
    otp_code: Optional[str] = None  # Required for first-time login


class UserResponse(BaseModel):
    """Schema for user response (without sensitive data)"""
    id: str
    email: str
    username: str
    full_name: str
    bio: str
    profile_picture: Optional[str]
    role: str
    status: str
    followers_count: int
    following_count: int
    posts_count: int
    email_verified: bool
    auth_provider: str
    google_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]


class TokenResponse(BaseModel):
    """Schema for token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginResponse(BaseModel):
    """Schema for login response"""
    message: str
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RegistrationResponse(BaseModel):
    """Schema for registration response"""
    message: str
    user: UserResponse
    email_sent: bool


class EmailVerification(BaseModel):
    """Schema for email verification"""
    email: EmailStr
    otp_code: str


class EmailRequest(BaseModel):
    """Schema for email-only requests (resend verification, etc.)"""
    email: EmailStr


class RefreshToken(BaseModel):
    """Schema for token refresh"""
    refresh_token: str


class UserProfileUpdate(BaseModel):
    """Schema for user profile update"""
    full_name: Optional[str] = None
    bio: Optional[str] = None
    profile_picture: Optional[str] = None


class PasswordResetRequest(BaseModel):
    """Schema for password reset request"""
    email: EmailStr


class PasswordResetVerify(BaseModel):
    """Schema for password reset verification"""
    email: EmailStr
    reset_code: str
    new_password: str
    
    @validator('new_password')
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


class PasswordResetResponse(BaseModel):
    """Schema for password reset response"""
    message: str
    email_sent: bool
