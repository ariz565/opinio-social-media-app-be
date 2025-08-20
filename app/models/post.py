from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from bson import ObjectId
from app.database.mongo_connection import get_database

# Post type constants
POST_TYPE_TEXT = "text"
POST_TYPE_IMAGE = "image"
POST_TYPE_VIDEO = "video"
POST_TYPE_GIF = "gif"
POST_TYPE_POLL = "poll"

# Post status constants
POST_STATUS_DRAFT = "draft"
POST_STATUS_PUBLISHED = "published"
POST_STATUS_SCHEDULED = "scheduled"
POST_STATUS_ARCHIVED = "archived"

# Post visibility constants
POST_VISIBILITY_PUBLIC = "public"
POST_VISIBILITY_FOLLOWERS = "followers"
POST_VISIBILITY_CLOSE_FRIENDS = "close_friends"
POST_VISIBILITY_PRIVATE = "private"

# Mood/Activity constants
MOODS = [
    "happy", "sad", "excited", "loved", "blessed", "grateful", "motivated",
    "relaxed", "adventurous", "nostalgic", "proud", "creative", "peaceful"
]

ACTIVITIES = [
    "working", "traveling", "eating", "exercising", "studying", "celebrating",
    "cooking", "reading", "watching", "listening", "gaming", "shopping",
    "socializing", "resting", "creating", "learning"
]

class Post:
    def __init__(self):
        # Don't initialize database connection here
        # It will be retrieved in each method
        pass

    async def _get_collection(self):
        """Get the posts collection"""
        db = await get_database()
        return db.posts

    async def create_post(self, post_data: dict) -> dict:
        """Create a new post"""
        collection = await self._get_collection()
        
        post_data["_id"] = ObjectId()
        post_data["created_at"] = datetime.now(timezone.utc)
        post_data["updated_at"] = datetime.now(timezone.utc)
        post_data["edit_history"] = []
        post_data["engagement_stats"] = {
            "likes_count": 0,
            "comments_count": 0,
            "shares_count": 0,
            "bookmarks_count": 0,
            "views_count": 0
        }
        post_data["is_pinned"] = False
        post_data["is_featured"] = False
        
        result = await collection.insert_one(post_data)
        if result.inserted_id:
            return await self.get_post_by_id(str(result.inserted_id))
        return None

    async def get_post_by_id(self, post_id: str) -> Optional[dict]:
        """Get post by ID"""
        collection = await self._get_collection()
        
        try:
            post = await collection.find_one({"_id": ObjectId(post_id)})
            if post:
                post["_id"] = str(post["_id"])
                post["user_id"] = str(post["user_id"])
                # Convert ObjectId fields in edit_history
                if "edit_history" in post:
                    for edit in post["edit_history"]:
                        if "_id" in edit:
                            edit["_id"] = str(edit["_id"])
            return post
        except Exception:
            return None

    async def get_posts_by_user(self, user_id: str, skip: int = 0, limit: int = 20, 
                               include_drafts: bool = False) -> List[dict]:
        """Get posts by user ID"""
        collection = await self._get_collection()
        
        query = {"user_id": ObjectId(user_id)}
        if not include_drafts:
            query["status"] = {"$ne": POST_STATUS_DRAFT}
        
        cursor = collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        posts = []
        async for post in cursor:
            post["_id"] = str(post["_id"])
            post["user_id"] = str(post["user_id"])
            posts.append(post)
        return posts

    async def get_feed_posts(self, user_id: str, following_ids: List[str], 
                           skip: int = 0, limit: int = 20) -> List[dict]:
        """Get posts for user's feed"""
        collection = await self._get_collection()
        
        following_object_ids = [ObjectId(uid) for uid in following_ids]
        following_object_ids.append(ObjectId(user_id))  # Include user's own posts
        
        query = {
            "user_id": {"$in": following_object_ids},
            "status": POST_STATUS_PUBLISHED,
            "visibility": {"$in": [POST_VISIBILITY_PUBLIC, POST_VISIBILITY_FOLLOWERS]}
        }
        
        cursor = collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        posts = []
        async for post in cursor:
            post["_id"] = str(post["_id"])
            post["user_id"] = str(post["user_id"])
            posts.append(post)
        return posts

    async def update_post(self, post_id: str, update_data: dict, user_id: str) -> Optional[dict]:
        """Update post with edit history"""
        try:
            # Get current post for edit history
            current_post = await self.collection.find_one({
                "_id": ObjectId(post_id),
                "user_id": ObjectId(user_id)
            })
            
            if not current_post:
                return None

            # Create edit history entry
            edit_entry = {
                "_id": ObjectId(),
                "edited_at": datetime.now(timezone.utc),
                "previous_content": current_post.get("content", ""),
                "previous_media": current_post.get("media", []),
                "edit_reason": update_data.pop("edit_reason", "Content updated")
            }

            # Update the post
            update_data["updated_at"] = datetime.now(timezone.utc)
            update_data["$push"] = {"edit_history": edit_entry}
            
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(post_id), "user_id": ObjectId(user_id)},
                {"$set": update_data, "$push": {"edit_history": edit_entry}},
                return_document=True
            )
            
            if result:
                result["_id"] = str(result["_id"])
                result["user_id"] = str(result["user_id"])
            return result
        except Exception:
            return None

    async def delete_post(self, post_id: str, user_id: str) -> bool:
        """Delete post (soft delete by archiving)"""
        try:
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(post_id), "user_id": ObjectId(user_id)},
                {
                    "$set": {
                        "status": POST_STATUS_ARCHIVED,
                        "archived_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            return result is not None
        except Exception:
            return False

    async def permanently_delete_post(self, post_id: str, user_id: str) -> bool:
        """Permanently delete post"""
        try:
            result = await self.collection.delete_one({
                "_id": ObjectId(post_id),
                "user_id": ObjectId(user_id)
            })
            return result.deleted_count > 0
        except Exception:
            return False

    async def pin_post(self, post_id: str, user_id: str) -> bool:
        """Pin post to profile"""
        try:
            # First unpin any existing pinned posts
            await self.collection.update_many(
                {"user_id": ObjectId(user_id), "is_pinned": True},
                {"$set": {"is_pinned": False}}
            )
            
            # Pin the selected post
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(post_id), "user_id": ObjectId(user_id)},
                {"$set": {"is_pinned": True, "pinned_at": datetime.now(timezone.utc)}}
            )
            return result is not None
        except Exception:
            return False

    async def unpin_post(self, post_id: str, user_id: str) -> bool:
        """Unpin post from profile"""
        try:
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(post_id), "user_id": ObjectId(user_id)},
                {"$set": {"is_pinned": False}, "$unset": {"pinned_at": ""}}
            )
            return result is not None
        except Exception:
            return False

    async def save_draft(self, post_data: dict) -> dict:
        """Save post as draft"""
        post_data["status"] = POST_STATUS_DRAFT
        return await self.create_post(post_data)

    async def publish_draft(self, draft_id: str, user_id: str, 
                          scheduled_time: Optional[datetime] = None) -> Optional[dict]:
        """Publish a draft post"""
        try:
            update_data = {
                "status": POST_STATUS_PUBLISHED if not scheduled_time else POST_STATUS_SCHEDULED,
                "published_at": datetime.now(timezone.utc) if not scheduled_time else None,
                "scheduled_for": scheduled_time,
                "updated_at": datetime.now(timezone.utc)
            }
            
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(draft_id), "user_id": ObjectId(user_id), "status": POST_STATUS_DRAFT},
                {"$set": update_data},
                return_document=True
            )
            
            if result:
                result["_id"] = str(result["_id"])
                result["user_id"] = str(result["user_id"])
            return result
        except Exception:
            return None

    async def get_scheduled_posts(self) -> List[dict]:
        """Get posts scheduled for publishing"""
        current_time = datetime.now(timezone.utc)
        cursor = self.collection.find({
            "status": POST_STATUS_SCHEDULED,
            "scheduled_for": {"$lte": current_time}
        })
        
        posts = []
        async for post in cursor:
            post["_id"] = str(post["_id"])
            post["user_id"] = str(post["user_id"])
            posts.append(post)
        return posts

    async def publish_scheduled_post(self, post_id: str) -> bool:
        """Publish a scheduled post"""
        try:
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(post_id), "status": POST_STATUS_SCHEDULED},
                {
                    "$set": {
                        "status": POST_STATUS_PUBLISHED,
                        "published_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc)
                    },
                    "$unset": {"scheduled_for": ""}
                }
            )
            return result is not None
        except Exception:
            return False

    async def update_engagement_stats(self, post_id: str, stat_type: str, increment: int = 1) -> bool:
        """Update engagement statistics"""
        try:
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(post_id)},
                {"$inc": {f"engagement_stats.{stat_type}": increment}}
            )
            return result is not None
        except Exception:
            return False

    async def get_user_drafts(self, user_id: str) -> List[dict]:
        """Get all drafts for a user"""
        cursor = self.collection.find({
            "user_id": ObjectId(user_id),
            "status": POST_STATUS_DRAFT
        }).sort("created_at", -1)
        
        drafts = []
        async for draft in cursor:
            draft["_id"] = str(draft["_id"])
            draft["user_id"] = str(draft["user_id"])
            drafts.append(draft)
        return drafts

    async def search_posts(self, query: str, skip: int = 0, limit: int = 20) -> List[dict]:
        """Search posts by content"""
        search_query = {
            "$or": [
                {"content": {"$regex": query, "$options": "i"}},
                {"hashtags": {"$regex": query, "$options": "i"}},
                {"location.name": {"$regex": query, "$options": "i"}}
            ],
            "status": POST_STATUS_PUBLISHED,
            "visibility": POST_VISIBILITY_PUBLIC
        }
        
        cursor = self.collection.find(search_query).sort("created_at", -1).skip(skip).limit(limit)
        posts = []
        async for post in cursor:
            post["_id"] = str(post["_id"])
            post["user_id"] = str(post["user_id"])
            posts.append(post)
        return posts

    async def get_trending_posts(self, hours: int = 24, limit: int = 50) -> List[dict]:
        """Get trending posts based on recent engagement"""
        since_time = datetime.now(timezone.utc).replace(hour=datetime.now(timezone.utc).hour - hours)
        
        pipeline = [
            {
                "$match": {
                    "status": POST_STATUS_PUBLISHED,
                    "visibility": POST_VISIBILITY_PUBLIC,
                    "created_at": {"$gte": since_time}
                }
            },
            {
                "$addFields": {
                    "trend_score": {
                        "$add": [
                            {"$multiply": ["$engagement_stats.likes_count", 1]},
                            {"$multiply": ["$engagement_stats.comments_count", 2]},
                            {"$multiply": ["$engagement_stats.shares_count", 3]},
                            {"$multiply": ["$engagement_stats.views_count", 0.1]}
                        ]
                    }
                }
            },
            {"$sort": {"trend_score": -1}},
            {"$limit": limit}
        ]
        
        posts = []
        async for post in self.collection.aggregate(pipeline):
            post["_id"] = str(post["_id"])
            post["user_id"] = str(post["user_id"])
            posts.append(post)
        return posts
