"""
Advanced Sharing/Repost Model
Supports reposts with/without comments, sharing to stories, and external sharing
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import asyncio
from app.database.mongo_connection import get_database

class ShareType(str, Enum):
    """Types of sharing"""
    REPOST = "repost"
    REPOST_WITH_COMMENT = "repost_with_comment"
    STORY = "story"
    DIRECT_MESSAGE = "direct_message"
    EXTERNAL = "external"

class ShareModel:
    """
    Advanced sharing system for posts
    Supports various sharing types with tracking and analytics
    """
    
    def __init__(self):
        self.db = None
        
    async def get_db(self):
        """Get database connection"""
        if self.db is None:
            self.db = await get_database()
        return self.db

    async def share_post(
        self,
        user_id: str,
        original_post_id: str,
        share_type: ShareType,
        comment: Optional[str] = None,
        recipient_ids: Optional[List[str]] = None,
        story_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Share a post with various options"""
        db = await self.get_db()
        
        # Get original post to verify it exists and isn't deleted
        original_post = await db.posts.find_one({
            "_id": original_post_id,
            "is_deleted": False
        })
        
        if not original_post:
            return {"error": "Original post not found"}
        
        # Check if user is blocked by post author
        from app.models.follow import follow_model
        is_blocked = await follow_model.is_user_blocked(original_post["user_id"], user_id)
        if is_blocked:
            return {"error": "Cannot share this post"}
        
        share_data = {
            "user_id": user_id,
            "original_post_id": original_post_id,
            "original_author_id": original_post["user_id"],
            "share_type": share_type.value,
            "comment": comment,
            "recipient_ids": recipient_ids or [],
            "story_settings": story_settings,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Handle different share types
        if share_type == ShareType.REPOST or share_type == ShareType.REPOST_WITH_COMMENT:
            # Create a new post that references the original
            repost_data = {
                "user_id": user_id,
                "content": comment or "",
                "post_type": "repost",
                "original_post_id": original_post_id,
                "original_author_id": original_post["user_id"],
                "media_urls": [],
                "hashtags": [],
                "mentions": [],
                "location": None,
                "privacy": "public",  # Reposts are typically public
                "like_count": 0,
                "comment_count": 0,
                "share_count": 0,
                "bookmark_count": 0,
                "view_count": 0,
                "reactions": {
                    "like": 0,
                    "love": 0,
                    "laugh": 0,
                    "wow": 0,
                    "sad": 0,
                    "angry": 0,
                    "care": 0,
                    "total": 0
                },
                "is_deleted": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            repost_result = await db.posts.insert_one(repost_data)
            share_data["repost_id"] = str(repost_result.inserted_id)
        
        elif share_type == ShareType.STORY:
            # Create story entry
            story_data = {
                "user_id": user_id,
                "story_type": "shared_post",
                "content": {
                    "original_post_id": original_post_id,
                    "text": comment or "",
                    "settings": story_settings or {}
                },
                "media_urls": [],
                "viewers": [],
                "view_count": 0,
                "expires_at": datetime.utcnow() + timedelta(hours=24),
                "is_highlight": False,
                "created_at": datetime.utcnow()
            }
            
            story_result = await db.stories.insert_one(story_data)
            share_data["story_id"] = str(story_result.inserted_id)
        
        elif share_type == ShareType.DIRECT_MESSAGE:
            # Handle direct message sharing
            if not recipient_ids:
                return {"error": "Recipients required for direct message sharing"}
            
            # Create message for each recipient
            for recipient_id in recipient_ids:
                message_data = {
                    "sender_id": user_id,
                    "recipient_id": recipient_id,
                    "message_type": "shared_post",
                    "content": {
                        "text": comment or "",
                        "shared_post_id": original_post_id
                    },
                    "is_read": False,
                    "created_at": datetime.utcnow()
                }
                await db.messages.insert_one(message_data)
        
        # Record the share
        result = await db.shares.insert_one(share_data)
        
        # Update original post share count
        await db.posts.update_one(
            {"_id": original_post_id},
            {"$inc": {"share_count": 1}}
        )
        
        # Create notification for original author (if not sharing own post)
        if original_post["user_id"] != user_id:
            notification_data = {
                "user_id": original_post["user_id"],
                "type": "post_shared",
                "data": {
                    "shared_by_user_id": user_id,
                    "post_id": original_post_id,
                    "share_type": share_type.value,
                    "comment": comment
                },
                "is_read": False,
                "created_at": datetime.utcnow()
            }
            await db.notifications.insert_one(notification_data)
        
        return {
            "_id": str(result.inserted_id),
            "share_type": share_type.value,
            "message": "Post shared successfully",
            **share_data
        }

    async def get_post_shares(
        self,
        post_id: str,
        share_type: Optional[ShareType] = None,
        limit: int = 20,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Get shares for a specific post"""
        db = await self.get_db()
        
        # Build query
        query = {"original_post_id": post_id}
        if share_type:
            query["share_type"] = share_type.value
        
        pipeline = [
            {"$match": query},
            {"$sort": {"created_at": -1}},
            {"$skip": skip},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "user_id",
                    "foreignField": "_id",
                    "as": "user"
                }
            },
            {"$unwind": "$user"},
            {
                "$project": {
                    "_id": {"$toString": "$_id"},
                    "user_id": 1,
                    "share_type": 1,
                    "comment": 1,
                    "created_at": 1,
                    "user": {
                        "username": "$user.username",
                        "full_name": "$user.full_name",
                        "profile_picture": "$user.profile_picture",
                        "is_verified": "$user.is_verified"
                    }
                }
            }
        ]
        
        shares = await db.shares.aggregate(pipeline).to_list(length=None)
        return shares

    async def get_user_shares(
        self,
        user_id: str,
        share_type: Optional[ShareType] = None,
        limit: int = 20,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Get shares made by a specific user"""
        db = await self.get_db()
        
        # Build query
        query = {"user_id": user_id}
        if share_type:
            query["share_type"] = share_type.value
        
        pipeline = [
            {"$match": query},
            {"$sort": {"created_at": -1}},
            {"$skip": skip},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "posts",
                    "localField": "original_post_id",
                    "foreignField": "_id",
                    "as": "original_post"
                }
            },
            {"$unwind": "$original_post"},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "original_author_id",
                    "foreignField": "_id",
                    "as": "original_author"
                }
            },
            {"$unwind": "$original_author"},
            {
                "$project": {
                    "_id": {"$toString": "$_id"},
                    "share_type": 1,
                    "comment": 1,
                    "created_at": 1,
                    "original_post": {
                        "_id": {"$toString": "$original_post._id"},
                        "content": "$original_post.content",
                        "media_urls": "$original_post.media_urls",
                        "post_type": "$original_post.post_type",
                        "created_at": "$original_post.created_at"
                    },
                    "original_author": {
                        "username": "$original_author.username",
                        "full_name": "$original_author.full_name",
                        "profile_picture": "$original_author.profile_picture",
                        "is_verified": "$original_author.is_verified"
                    }
                }
            }
        ]
        
        shares = await db.shares.aggregate(pipeline).to_list(length=None)
        return shares

    async def get_reposts_feed(
        self,
        user_id: str,
        limit: int = 20,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Get reposts from users that the current user follows"""
        db = await self.get_db()
        
        # Get users that current user follows
        following_pipeline = [
            {
                "$match": {
                    "follower_id": user_id,
                    "status": "accepted"
                }
            },
            {
                "$group": {
                    "_id": None,
                    "following_ids": {"$push": "$following_id"}
                }
            }
        ]
        
        following_result = await db.follows.aggregate(following_pipeline).to_list(length=1)
        following_ids = following_result[0]["following_ids"] if following_result else []
        following_ids.append(user_id)  # Include own reposts
        
        # Get reposts from followed users
        pipeline = [
            {
                "$match": {
                    "user_id": {"$in": following_ids},
                    "post_type": "repost"
                }
            },
            {"$sort": {"created_at": -1}},
            {"$skip": skip},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "posts",
                    "localField": "original_post_id",
                    "foreignField": "_id",
                    "as": "original_post"
                }
            },
            {"$unwind": "$original_post"},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "user_id",
                    "foreignField": "_id",
                    "as": "reposter"
                }
            },
            {"$unwind": "$reposter"},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "original_author_id",
                    "foreignField": "_id",
                    "as": "original_author"
                }
            },
            {"$unwind": "$original_author"},
            {
                "$project": {
                    "_id": {"$toString": "$_id"},
                    "content": 1,
                    "created_at": 1,
                    "like_count": 1,
                    "comment_count": 1,
                    "share_count": 1,
                    "reposter": {
                        "_id": {"$toString": "$reposter._id"},
                        "username": "$reposter.username",
                        "full_name": "$reposter.full_name",
                        "profile_picture": "$reposter.profile_picture",
                        "is_verified": "$reposter.is_verified"
                    },
                    "original_post": {
                        "_id": {"$toString": "$original_post._id"},
                        "content": "$original_post.content",
                        "media_urls": "$original_post.media_urls",
                        "post_type": "$original_post.post_type",
                        "created_at": "$original_post.created_at",
                        "like_count": "$original_post.like_count",
                        "comment_count": "$original_post.comment_count"
                    },
                    "original_author": {
                        "_id": {"$toString": "$original_author._id"},
                        "username": "$original_author.username",
                        "full_name": "$original_author.full_name",
                        "profile_picture": "$original_author.profile_picture",
                        "is_verified": "$original_author.is_verified"
                    }
                }
            }
        ]
        
        reposts = await db.posts.aggregate(pipeline).to_list(length=None)
        return reposts

    async def delete_share(
        self,
        share_id: str,
        user_id: str
    ) -> bool:
        """Delete a share (and associated repost if applicable)"""
        db = await self.get_db()
        
        # Find the share
        share = await db.shares.find_one({
            "_id": share_id,
            "user_id": user_id
        })
        
        if not share:
            return False
        
        # Delete associated content based on share type
        if share["share_type"] in ["repost", "repost_with_comment"] and share.get("repost_id"):
            # Delete the repost
            await db.posts.delete_one({"_id": share["repost_id"]})
        
        elif share["share_type"] == "story" and share.get("story_id"):
            # Delete the story
            await db.stories.delete_one({"_id": share["story_id"]})
        
        # Delete the share record
        await db.shares.delete_one({"_id": share_id})
        
        # Update original post share count
        await db.posts.update_one(
            {"_id": share["original_post_id"]},
            {"$inc": {"share_count": -1}}
        )
        
        return True

    async def get_share_analytics(
        self,
        post_id: str
    ) -> Dict[str, Any]:
        """Get sharing analytics for a post"""
        db = await self.get_db()
        
        pipeline = [
            {"$match": {"original_post_id": post_id}},
            {
                "$group": {
                    "_id": "$share_type",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        results = await db.shares.aggregate(pipeline).to_list(length=None)
        
        # Initialize analytics
        analytics = {
            "total_shares": 0,
            "reposts": 0,
            "reposts_with_comment": 0,
            "story_shares": 0,
            "direct_message_shares": 0,
            "external_shares": 0
        }
        
        # Map results
        share_type_map = {
            "repost": "reposts",
            "repost_with_comment": "reposts_with_comment",
            "story": "story_shares",
            "direct_message": "direct_message_shares",
            "external": "external_shares"
        }
        
        for result in results:
            share_type = result["_id"]
            count = result["count"]
            analytics["total_shares"] += count
            
            if share_type in share_type_map:
                analytics[share_type_map[share_type]] = count
        
        return analytics

    async def get_trending_shares(
        self,
        days: int = 7,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get most shared posts in the last N days"""
        db = await self.get_db()
        
        from_date = datetime.utcnow() - timedelta(days=days)
        
        pipeline = [
            {
                "$match": {
                    "created_at": {"$gte": from_date}
                }
            },
            {
                "$group": {
                    "_id": "$original_post_id",
                    "share_count": {"$sum": 1},
                    "latest_share": {"$max": "$created_at"}
                }
            },
            {"$sort": {"share_count": -1, "latest_share": -1}},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "posts",
                    "localField": "_id",
                    "foreignField": "_id",
                    "as": "post"
                }
            },
            {"$unwind": "$post"},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "post.user_id",
                    "foreignField": "_id",
                    "as": "author"
                }
            },
            {"$unwind": "$author"},
            {
                "$project": {
                    "post_id": {"$toString": "$_id"},
                    "share_count": 1,
                    "post": {
                        "content": "$post.content",
                        "media_urls": "$post.media_urls",
                        "created_at": "$post.created_at"
                    },
                    "author": {
                        "username": "$author.username",
                        "full_name": "$author.full_name",
                        "profile_picture": "$author.profile_picture"
                    }
                }
            }
        ]
        
        trending = await db.shares.aggregate(pipeline).to_list(length=None)
        return trending

# Create global instance
share_model = ShareModel()
