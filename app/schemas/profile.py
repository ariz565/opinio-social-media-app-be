from pydantic import BaseModel, Field, EmailStr, HttpUrl, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import re

class BasicInfoUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    headline: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    about: Optional[str] = Field(None, max_length=1000)
    location: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = None
    phone: Optional[str] = None
    
    @validator('phone')
    def validate_phone(cls, v):
        if v and not re.match(r'^\+?[1-9]\d{1,14}$', v):
            raise ValueError('Invalid phone number format')
        return v

class WorkExperience(BaseModel):
    id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=100)
    company: str = Field(..., min_length=1, max_length=100)
    company_logo: Optional[str] = None
    location: str = Field(..., min_length=1, max_length=100)
    start_date: str = Field(..., min_length=1)
    end_date: Optional[str] = None
    current: bool = False
    description: str = Field(..., min_length=1, max_length=1000)
    skills: List[str] = []

class Education(BaseModel):
    id: Optional[str] = None
    school: str = Field(..., min_length=1, max_length=100)
    degree: str = Field(..., min_length=1, max_length=100)
    field: str = Field(..., min_length=1, max_length=100)
    location: str = Field(..., min_length=1, max_length=100)
    start_date: str = Field(..., min_length=1)
    end_date: str = Field(..., min_length=1)
    gpa: Optional[str] = Field(None, max_length=10)
    achievements: List[str] = []
    logo: Optional[str] = None

class Skill(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    level: int = Field(..., ge=0, le=100)
    endorsements: int = Field(default=0, ge=0)
    category: str = Field(..., min_length=1, max_length=50)

class Language(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    proficiency: str = Field(..., min_length=1, max_length=50)
    level: int = Field(..., ge=0, le=100)

class Certification(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=100)
    issuer: str = Field(..., min_length=1, max_length=100)
    date: str = Field(..., min_length=1)
    credential_id: str = Field(..., min_length=1, max_length=100)
    logo: Optional[str] = None
    expiry_date: Optional[str] = None

class SocialLinks(BaseModel):
    linkedin: Optional[str] = None
    twitter: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    instagram: Optional[str] = None
    facebook: Optional[str] = None

class PhotoUpdate(BaseModel):
    profile_picture: Optional[str] = None
    cover_photo: Optional[str] = None

# Update schemas for each section
class ExperienceUpdate(BaseModel):
    experience: List[WorkExperience]

class EducationUpdate(BaseModel):
    education: List[Education]

class SkillsUpdate(BaseModel):
    skills: List[Skill]

class LanguagesUpdate(BaseModel):
    languages: List[Language]

class CertificationsUpdate(BaseModel):
    certifications: List[Certification]

class InterestsUpdate(BaseModel):
    interests: List[str] = Field(..., max_items=20)

class SocialLinksUpdate(BaseModel):
    social_links: SocialLinks

# Response schemas
class ProfileStats(BaseModel):
    posts: int = 0
    followers: int = 0
    following: int = 0
    connections: int = 0
    profile_views: int = 0
    post_impressions: int = 0

class FullProfile(BaseModel):
    id: str = Field(alias="_id")
    username: str
    email: str
    full_name: str
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    profile_picture: Optional[str] = None
    is_verified: bool = False
    is_online: bool = False
    status: str = "active"
    
    # Profile sections
    profile: Dict[str, Any] = {}
    stats: ProfileStats = ProfileStats()
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# File upload schemas
class FileUploadResponse(BaseModel):
    url: str
    filename: str
    file_type: str
    size: int

class DeleteItemRequest(BaseModel):
    item_id: str
