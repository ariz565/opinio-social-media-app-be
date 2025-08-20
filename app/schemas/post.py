from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from bson import ObjectId

# Author schema for posts
class Author(BaseModel):
    """Schema for post author information"""
    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    full_name: str = Field(..., description="Full name")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    email: str = Field(..., description="Email address")

# Enums for validation
POST_TYPES = ["text", "image", "video", "gif", "poll"]
POST_STATUSES = ["draft", "published", "scheduled", "archived"]
POST_VISIBILITIES = ["public", "followers", "close_friends", "private"]
MOODS = [
    "happy", "sad", "excited", "loved", "blessed", "grateful", "motivated",
    "relaxed", "adventurous", "nostalgic", "proud", "creative", "peaceful"
]
ACTIVITIES = [
    "working", "traveling", "eating", "exercising", "studying", "celebrating",
    "cooking", "reading", "watching", "listening", "gaming", "shopping",
    "socializing", "resting", "creating", "learning"
]

# Media schemas
class MediaItem(BaseModel):
    """Schema for media items (images, videos, gifs)"""
    url: str = Field(..., description="URL of the media file")
    type: str = Field(..., description="Type of media: image, video, gif")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL for videos")
    width: Optional[int] = Field(None, description="Width of the media")
    height: Optional[int] = Field(None, description="Height of the media")
    size: Optional[int] = Field(None, description="File size in bytes")
    duration: Optional[float] = Field(None, description="Duration for videos in seconds")
    alt_text: Optional[str] = Field(None, description="Alt text for accessibility")

class PollOption(BaseModel):
    """Schema for poll options"""
    text: str = Field(..., max_length=100, description="Poll option text")
    votes: int = Field(default=0, description="Number of votes for this option")
    voters: List[str] = Field(default_factory=list, description="List of user IDs who voted")

class Poll(BaseModel):
    """Schema for poll data"""
    question: str = Field(..., max_length=500, description="Poll question")
    options: List[PollOption] = Field(..., min_items=2, max_items=4, description="Poll options")
    multiple_choice: bool = Field(default=False, description="Allow multiple selections")
    expires_at: Optional[datetime] = Field(None, description="Poll expiration time")
    total_votes: int = Field(default=0, description="Total number of votes")

class Location(BaseModel):
    """Schema for location data"""
    name: str = Field(..., max_length=200, description="Location name")
    address: Optional[str] = Field(None, description="Full address")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude coordinate")
    place_id: Optional[str] = Field(None, description="Google Places ID or similar")

class MoodActivity(BaseModel):
    """Schema for mood and activity status"""
    mood: Optional[str] = Field(None, description="User's mood")
    activity: Optional[str] = Field(None, description="User's activity")
    custom_status: Optional[str] = Field(None, max_length=100, description="Custom status text")

    @validator('mood')
    def validate_mood(cls, v):
        if v and v not in MOODS:
            raise ValueError(f'Invalid mood. Must be one of: {", ".join(MOODS)}')
        return v

    @validator('activity')
    def validate_activity(cls, v):
        if v and v not in ACTIVITIES:
            raise ValueError(f'Invalid activity. Must be one of: {", ".join(ACTIVITIES)}')
        return v

class EditHistory(BaseModel):
    """Schema for post edit history"""
    edited_at: datetime
    previous_content: str
    previous_media: List[MediaItem] = Field(default_factory=list)
    edit_reason: str = Field(default="Content updated")

class EngagementStats(BaseModel):
    """Schema for post engagement statistics"""
    likes_count: int = Field(default=0)
    comments_count: int = Field(default=0)
    shares_count: int = Field(default=0)
    bookmarks_count: int = Field(default=0)
    views_count: int = Field(default=0)

# Request schemas
class PostCreate(BaseModel):
    """Schema for creating a new post"""
    content: str = Field(..., max_length=5000, description="Post content")
    post_type: str = Field(..., description="Type of post")
    media: List[MediaItem] = Field(default_factory=list, description="Media attachments")
    poll: Optional[Poll] = Field(None, description="Poll data if post_type is poll")
    hashtags: List[str] = Field(default_factory=list, max_items=30, description="Post hashtags")
    mentions: List[str] = Field(default_factory=list, description="Mentioned user IDs")
    location: Optional[Location] = Field(None, description="Location data")
    mood_activity: Optional[MoodActivity] = Field(None, description="Mood and activity status")
    visibility: str = Field(default="public", description="Post visibility")
    allow_comments: bool = Field(default=True, description="Allow comments on post")
    allow_shares: bool = Field(default=True, description="Allow sharing of post")

    @validator('post_type')
    def validate_post_type(cls, v):
        if v not in POST_TYPES:
            raise ValueError(f'Invalid post type. Must be one of: {", ".join(POST_TYPES)}')
        return v

    @validator('visibility')
    def validate_visibility(cls, v):
        if v not in POST_VISIBILITIES:
            raise ValueError(f'Invalid visibility. Must be one of: {", ".join(POST_VISIBILITIES)}')
        return v

    @validator('hashtags')
    def validate_hashtags(cls, v):
        for tag in v:
            if not tag.startswith('#'):
                v[v.index(tag)] = f'#{tag}'
            if len(tag) > 50:
                raise ValueError('Hashtag too long (max 50 characters)')
        return v

    @validator('content')
    def validate_content_based_on_type(cls, v, values):
        post_type = values.get('post_type')
        if post_type == 'text' and len(v.strip()) == 0:
            raise ValueError('Text posts must have content')
        return v

class PostUpdate(BaseModel):
    """Schema for updating a post"""
    content: Optional[str] = Field(None, max_length=5000)
    media: Optional[List[MediaItem]] = Field(None)
    hashtags: Optional[List[str]] = Field(None, max_items=30)
    location: Optional[Location] = Field(None)
    mood_activity: Optional[MoodActivity] = Field(None)
    visibility: Optional[str] = Field(None)
    allow_comments: Optional[bool] = Field(None)
    allow_shares: Optional[bool] = Field(None)
    edit_reason: str = Field(default="Content updated", max_length=200)

    @validator('visibility')
    def validate_visibility(cls, v):
        if v and v not in POST_VISIBILITIES:
            raise ValueError(f'Invalid visibility. Must be one of: {", ".join(POST_VISIBILITIES)}')
        return v

class PostSchedule(BaseModel):
    """Schema for scheduling a post"""
    scheduled_for: datetime = Field(..., description="When to publish the post")

    @validator('scheduled_for')
    def validate_future_time(cls, v):
        if v <= datetime.now(timezone.utc):
            raise ValueError('Scheduled time must be in the future')
        return v

class DraftSave(BaseModel):
    """Schema for saving a draft"""
    content: Optional[str] = Field(None, max_length=5000)
    post_type: str = Field(default="text")
    media: List[MediaItem] = Field(default_factory=list)
    poll: Optional[Poll] = Field(None)
    hashtags: List[str] = Field(default_factory=list, max_items=30)
    mentions: List[str] = Field(default_factory=list)
    location: Optional[Location] = Field(None)
    mood_activity: Optional[MoodActivity] = Field(None)
    visibility: str = Field(default="public")

# Response schemas
class PostResponse(BaseModel):
    """Schema for post response"""
    id: str = Field(..., description="Post ID")
    user_id: str = Field(..., description="Author user ID")
    content: str = Field(..., description="Post content")
    post_type: str = Field(..., description="Type of post")
    media: List[MediaItem] = Field(default_factory=list)
    poll: Optional[Poll] = Field(None)
    hashtags: List[str] = Field(default_factory=list)
    mentions: List[str] = Field(default_factory=list)
    location: Optional[Location] = Field(None)
    mood_activity: Optional[MoodActivity] = Field(None)
    visibility: str = Field(...)
    status: str = Field(...)
    allow_comments: bool = Field(default=True)
    allow_shares: bool = Field(default=True)
    is_pinned: bool = Field(default=False)
    is_featured: bool = Field(default=False)
    engagement_stats: EngagementStats = Field(default_factory=EngagementStats)
    edit_history: List[EditHistory] = Field(default_factory=list)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    published_at: Optional[datetime] = Field(None)
    scheduled_for: Optional[datetime] = Field(None)
    pinned_at: Optional[datetime] = Field(None)
    archived_at: Optional[datetime] = Field(None)
    
    # Author information
    author: Optional[Author] = Field(None, description="Post author information")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            ObjectId: str
        }

class PostListResponse(BaseModel):
    """Schema for paginated post list response"""
    posts: List[PostResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool

class PostStats(BaseModel):
    """Schema for post statistics"""
    total_posts: int
    published_posts: int
    draft_posts: int
    scheduled_posts: int
    archived_posts: int
    total_likes: int
    total_comments: int
    total_shares: int
    total_views: int
    trending_score: Optional[float] = Field(None)

# Search schemas
class PostSearchQuery(BaseModel):
    """Schema for post search queries"""
    query: str = Field(..., min_length=1, max_length=100, description="Search query")
    post_type: Optional[str] = Field(None, description="Filter by post type")
    hashtags: Optional[List[str]] = Field(None, description="Filter by hashtags")
    location: Optional[str] = Field(None, description="Filter by location")
    date_from: Optional[datetime] = Field(None, description="Filter posts from this date")
    date_to: Optional[datetime] = Field(None, description="Filter posts until this date")
    sort_by: str = Field(default="created_at", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order: asc or desc")

    @validator('sort_by')
    def validate_sort_by(cls, v):
        allowed_fields = ['created_at', 'updated_at', 'engagement_stats.likes_count', 
                         'engagement_stats.comments_count', 'engagement_stats.views_count']
        if v not in allowed_fields:
            raise ValueError(f'Invalid sort field. Must be one of: {", ".join(allowed_fields)}')
        return v

    @validator('sort_order')
    def validate_sort_order(cls, v):
        if v not in ['asc', 'desc']:
            raise ValueError('Sort order must be "asc" or "desc"')
        return v

# Vote schema for polls
class PollVote(BaseModel):
    """Schema for poll voting"""
    option_indices: List[int] = Field(..., min_items=1, description="Selected option indices")

    @validator('option_indices')
    def validate_option_indices(cls, v):
        if any(i < 0 for i in v):
            raise ValueError('Option indices must be non-negative')
        return v
