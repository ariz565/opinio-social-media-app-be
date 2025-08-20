"""
Pydantic schemas for interaction system (reactions, comments, bookmarks, shares)
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

# Reaction Schemas
class ReactionType(str, Enum):
    LIKE = "like"
    LOVE = "love"
    LAUGH = "laugh"
    WOW = "wow"
    SAD = "sad"
    ANGRY = "angry"
    CARE = "care"

class ReactionCreate(BaseModel):
    target_id: str = Field(..., description="ID of the target (post, comment, story)")
    target_type: str = Field(..., description="Type of target (post, comment, story)")
    reaction_type: ReactionType

class ReactionResponse(BaseModel):
    id: str = Field(..., alias="_id")
    user_id: str
    target_id: str
    target_type: str
    reaction_type: str
    created_at: datetime
    action: Optional[str] = None

    class Config:
        populate_by_name = True

class UserReactionInfo(BaseModel):
    id: str = Field(..., alias="_id")
    username: str
    full_name: str
    profile_picture: Optional[str] = None
    is_verified: bool = False

class ReactionWithUser(BaseModel):
    id: str = Field(..., alias="_id")
    user_id: str
    reaction_type: str
    created_at: datetime
    user: UserReactionInfo

    class Config:
        populate_by_name = True

class ReactionCounts(BaseModel):
    like: int = 0
    love: int = 0
    laugh: int = 0
    wow: int = 0
    sad: int = 0
    angry: int = 0
    care: int = 0
    total: int = 0

# Comment Schemas
class CommentSortType(str, Enum):
    NEWEST = "newest"
    OLDEST = "oldest"
    MOST_LIKED = "most_liked"
    MOST_REPLIES = "most_replies"

class CommentCreate(BaseModel):
    post_id: str
    content: str = Field(..., min_length=1, max_length=2000)
    parent_comment_id: Optional[str] = None
    mentions: Optional[List[str]] = []

class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)

class CommentEditHistory(BaseModel):
    content: str
    edited_at: datetime

class UserCommentInfo(BaseModel):
    username: str
    full_name: str
    profile_picture: Optional[str] = None
    is_verified: bool = False

class CommentResponse(BaseModel):
    id: str = Field(..., alias="_id")
    user_id: str
    post_id: str
    content: str
    parent_comment_id: Optional[str] = None
    depth: int = 0
    mentions: List[str] = []
    reactions: ReactionCounts
    reply_count: int = 0
    is_edited: bool = False
    edit_history: List[CommentEditHistory] = []
    created_at: datetime
    updated_at: datetime
    user: UserCommentInfo
    replies: List['CommentResponse'] = []

    class Config:
        populate_by_name = True

# Self-reference for nested comments
CommentResponse.model_rebuild()

class CommentListParams(BaseModel):
    sort_type: CommentSortType = CommentSortType.NEWEST
    limit: int = Field(default=20, ge=1, le=100)
    skip: int = Field(default=0, ge=0)
    max_depth: int = Field(default=3, ge=1, le=10)
    load_replies: bool = True

# Bookmark Schemas
class BookmarkPrivacy(str, Enum):
    PRIVATE = "private"
    CLOSE_FRIENDS = "close_friends"
    PUBLIC = "public"

class BookmarkCollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    privacy: BookmarkPrivacy = BookmarkPrivacy.PRIVATE
    color: Optional[str] = "#007bff"

    @validator('color')
    def validate_color(cls, v):
        if v and not v.startswith('#'):
            raise ValueError('Color must be a valid hex color starting with #')
        return v

class BookmarkCollectionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    privacy: Optional[BookmarkPrivacy] = None
    color: Optional[str] = None

    @validator('color')
    def validate_color(cls, v):
        if v and not v.startswith('#'):
            raise ValueError('Color must be a valid hex color starting with #')
        return v

class BookmarkCollectionResponse(BaseModel):
    id: str = Field(..., alias="_id")
    user_id: str
    name: str
    description: Optional[str] = None
    privacy: str
    color: str
    bookmark_count: int = 0
    shared_with: List[str] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True

class BookmarkCreate(BaseModel):
    post_id: str
    collection_id: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=1000)

class BookmarkUpdate(BaseModel):
    collection_id: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=1000)

class PostAuthorInfo(BaseModel):
    username: str
    full_name: str
    profile_picture: Optional[str] = None

class BookmarkPostInfo(BaseModel):
    id: str = Field(..., alias="_id")
    content: str
    media_urls: List[str] = []
    post_type: str
    created_at: datetime
    user: PostAuthorInfo

    class Config:
        populate_by_name = True

class BookmarkCollectionInfo(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    color: str

    class Config:
        populate_by_name = True

class BookmarkResponse(BaseModel):
    id: str = Field(..., alias="_id")
    user_id: str
    post_id: str
    collection_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    post: BookmarkPostInfo
    collection: Optional[BookmarkCollectionInfo] = None

    class Config:
        populate_by_name = True

class BookmarkListParams(BaseModel):
    collection_id: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)
    skip: int = Field(default=0, ge=0)
    search_term: Optional[str] = None

class BulkBookmarkOperation(BaseModel):
    bookmark_ids: List[str] = Field(..., min_items=1)
    target_collection_id: Optional[str] = None

# Share Schemas
class ShareType(str, Enum):
    REPOST = "repost"
    REPOST_WITH_COMMENT = "repost_with_comment"
    STORY = "story"
    DIRECT_MESSAGE = "direct_message"
    EXTERNAL = "external"

class ShareCreate(BaseModel):
    post_id: str
    share_type: ShareType
    comment: Optional[str] = Field(None, max_length=500)
    recipient_ids: Optional[List[str]] = []
    story_settings: Optional[Dict[str, Any]] = {}

    @validator('recipient_ids')
    def validate_recipients(cls, v, values):
        if values.get('share_type') == ShareType.DIRECT_MESSAGE and not v:
            raise ValueError('Recipients required for direct message sharing')
        return v

class ShareUserInfo(BaseModel):
    username: str
    full_name: str
    profile_picture: Optional[str] = None
    is_verified: bool = False

class ShareResponse(BaseModel):
    id: str = Field(..., alias="_id")
    user_id: str
    share_type: str
    comment: Optional[str] = None
    created_at: datetime
    user: ShareUserInfo

    class Config:
        populate_by_name = True

class OriginalPostInfo(BaseModel):
    id: str = Field(..., alias="_id")
    content: str
    media_urls: List[str] = []
    post_type: str
    created_at: datetime
    like_count: int = 0
    comment_count: int = 0

    class Config:
        populate_by_name = True

class UserShareResponse(BaseModel):
    id: str = Field(..., alias="_id")
    share_type: str
    comment: Optional[str] = None
    created_at: datetime
    original_post: OriginalPostInfo
    original_author: ShareUserInfo

    class Config:
        populate_by_name = True

class RepostFeedItem(BaseModel):
    id: str = Field(..., alias="_id")
    content: str
    created_at: datetime
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    reposter: ShareUserInfo
    original_post: OriginalPostInfo
    original_author: ShareUserInfo

    class Config:
        populate_by_name = True

class ShareAnalytics(BaseModel):
    total_shares: int = 0
    reposts: int = 0
    reposts_with_comment: int = 0
    story_shares: int = 0
    direct_message_shares: int = 0
    external_shares: int = 0

class TrendingShare(BaseModel):
    post_id: str
    share_count: int
    post: Dict[str, Any]
    author: ShareUserInfo

# Follow Schemas
class FollowStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"

class FollowResponse(BaseModel):
    id: str = Field(..., alias="_id")
    status: str
    message: str

    class Config:
        populate_by_name = True

class FollowRequestResponse(BaseModel):
    request_id: str
    accept: bool

class UserFollowInfo(BaseModel):
    id: str = Field(..., alias="_id")
    username: str
    full_name: str
    profile_picture: Optional[str] = None
    is_verified: bool = False
    bio: Optional[str] = None

    class Config:
        populate_by_name = True

class FollowerResponse(BaseModel):
    id: str = Field(..., alias="_id")
    follower_id: str
    created_at: datetime
    follower: UserFollowInfo

    class Config:
        populate_by_name = True

class FollowingResponse(BaseModel):
    id: str = Field(..., alias="_id")
    following_id: str
    created_at: datetime
    following: UserFollowInfo

    class Config:
        populate_by_name = True

class FollowRequestItem(BaseModel):
    id: str = Field(..., alias="_id")
    created_at: datetime
    follower: Optional[UserFollowInfo] = None
    following: Optional[UserFollowInfo] = None

    class Config:
        populate_by_name = True

class MutualConnection(BaseModel):
    id: str = Field(..., alias="_id")
    username: str
    full_name: str
    profile_picture: Optional[str] = None
    is_verified: bool = False

    class Config:
        populate_by_name = True

class FriendSuggestion(BaseModel):
    id: str = Field(..., alias="_id")
    username: str
    full_name: str
    profile_picture: Optional[str] = None
    is_verified: bool = False
    mutual_count: int

    class Config:
        populate_by_name = True

class UserConnections(BaseModel):
    close_friends: List[str] = []
    blocked_users: List[str] = []
    muted_users: List[str] = []
    restricted_users: List[str] = []

class FollowListParams(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    skip: int = Field(default=0, ge=0)
    search_term: Optional[str] = None

# General response schemas
class MessageResponse(BaseModel):
    message: str
    success: bool = True

class ErrorResponse(BaseModel):
    error: str
    success: bool = False

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool
