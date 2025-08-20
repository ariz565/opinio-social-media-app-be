"""
Advanced Bookmark Model with collections and sharing
Supports organized bookmark management with folders and privacy controls
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import asyncio
from app.database.mongo_connection import get_database

class BookmarkPrivacy(str, Enum):
    """Bookmark privacy levels"""
    PRIVATE = "private"
    CLOSE_FRIENDS = "close_friends"
    PUBLIC = "public"

class BookmarkModel:
    """
    Advanced bookmark system with collections and sharing
    Supports organized management and bulk operations
    """
    
    def __init__(self):
        self.db = None
        
    async def get_db(self):
        """Get database connection"""
        if not self.db:
            self.db = await get_database()
        return self.db

    async def create_bookmark_collection(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        privacy: BookmarkPrivacy = BookmarkPrivacy.PRIVATE,
        color: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new bookmark collection/folder"""
        db = await self.get_db()
        
        collection_data = {
            "user_id": user_id,
            "name": name,
            "description": description,
            "privacy": privacy.value,
            "color": color or "#007bff",
            "bookmark_count": 0,
            "shared_with": [],  # List of user IDs for close_friends privacy
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await db.bookmark_collections.insert_one(collection_data)
        
        return {
            "_id": str(result.inserted_id),
            **collection_data
        }

    async def add_bookmark(
        self,
        user_id: str,
        post_id: str,
        collection_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a post to bookmarks"""
        db = await self.get_db()
        
        # Check if already bookmarked
        existing_bookmark = await db.bookmarks.find_one({
            "user_id": user_id,
            "post_id": post_id
        })
        
        if existing_bookmark:
            # Update existing bookmark if moving to different collection
            if collection_id and existing_bookmark.get("collection_id") != collection_id:
                # Update collection counts
                if existing_bookmark.get("collection_id"):
                    await db.bookmark_collections.update_one(
                        {"_id": existing_bookmark["collection_id"]},
                        {"$inc": {"bookmark_count": -1}}
                    )
                
                if collection_id:
                    await db.bookmark_collections.update_one(
                        {"_id": collection_id},
                        {"$inc": {"bookmark_count": 1}}
                    )
                
                # Update bookmark
                await db.bookmarks.update_one(
                    {"_id": existing_bookmark["_id"]},
                    {
                        "$set": {
                            "collection_id": collection_id,
                            "notes": notes,
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
            
            return await self.get_bookmark_by_id(str(existing_bookmark["_id"]))
        
        # Create new bookmark
        bookmark_data = {
            "user_id": user_id,
            "post_id": post_id,
            "collection_id": collection_id,
            "notes": notes,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await db.bookmarks.insert_one(bookmark_data)
        
        # Update collection count
        if collection_id:
            await db.bookmark_collections.update_one(
                {"_id": collection_id},
                {"$inc": {"bookmark_count": 1}}
            )
        
        # Update post bookmark count
        await db.posts.update_one(
            {"_id": post_id},
            {"$inc": {"bookmark_count": 1}}
        )
        
        return await self.get_bookmark_by_id(str(result.inserted_id))

    async def remove_bookmark(
        self,
        user_id: str,
        post_id: str
    ) -> bool:
        """Remove a bookmark"""
        db = await self.get_db()
        
        bookmark = await db.bookmarks.find_one({
            "user_id": user_id,
            "post_id": post_id
        })
        
        if not bookmark:
            return False
        
        # Remove bookmark
        await db.bookmarks.delete_one({"_id": bookmark["_id"]})
        
        # Update collection count
        if bookmark.get("collection_id"):
            await db.bookmark_collections.update_one(
                {"_id": bookmark["collection_id"]},
                {"$inc": {"bookmark_count": -1}}
            )
        
        # Update post bookmark count
        await db.posts.update_one(
            {"_id": post_id},
            {"$inc": {"bookmark_count": -1}}
        )
        
        return True

    async def get_bookmark_by_id(
        self,
        bookmark_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get bookmark with post and collection details"""
        db = await self.get_db()
        
        pipeline = [
            {"$match": {"_id": bookmark_id}},
            {
                "$lookup": {
                    "from": "posts",
                    "localField": "post_id",
                    "foreignField": "_id",
                    "as": "post"
                }
            },
            {"$unwind": "$post"},
            {
                "$lookup": {
                    "from": "bookmark_collections",
                    "localField": "collection_id",
                    "foreignField": "_id",
                    "as": "collection"
                }
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "post.user_id",
                    "foreignField": "_id",
                    "as": "post_author"
                }
            },
            {"$unwind": "$post_author"},
            {
                "$project": {
                    "_id": {"$toString": "$_id"},
                    "user_id": 1,
                    "post_id": 1,
                    "collection_id": 1,
                    "notes": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "post": {
                        "_id": {"$toString": "$post._id"},
                        "content": "$post.content",
                        "media_urls": "$post.media_urls",
                        "post_type": "$post.post_type",
                        "created_at": "$post.created_at",
                        "user": {
                            "username": "$post_author.username",
                            "full_name": "$post_author.full_name",
                            "profile_picture": "$post_author.profile_picture"
                        }
                    },
                    "collection": {
                        "$cond": {
                            "if": {"$gt": [{"$size": "$collection"}, 0]},
                            "then": {
                                "_id": {"$toString": {"$arrayElemAt": ["$collection._id", 0]}},
                                "name": {"$arrayElemAt": ["$collection.name", 0]},
                                "color": {"$arrayElemAt": ["$collection.color", 0]}
                            },
                            "else": None
                        }
                    }
                }
            }
        ]
        
        bookmarks = await db.bookmarks.aggregate(pipeline).to_list(length=1)
        return bookmarks[0] if bookmarks else None

    async def get_user_bookmarks(
        self,
        user_id: str,
        collection_id: Optional[str] = None,
        limit: int = 20,
        skip: int = 0,
        search_term: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user's bookmarks with filtering options"""
        db = await self.get_db()
        
        # Build match query
        match_query = {"user_id": user_id}
        
        if collection_id:
            match_query["collection_id"] = collection_id
        
        # Build pipeline
        pipeline = [
            {"$match": match_query},
            {"$sort": {"created_at": -1}},
            {"$skip": skip},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "posts",
                    "localField": "post_id",
                    "foreignField": "_id",
                    "as": "post"
                }
            },
            {"$unwind": "$post"},
            {
                "$lookup": {
                    "from": "bookmark_collections",
                    "localField": "collection_id",
                    "foreignField": "_id",
                    "as": "collection"
                }
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "post.user_id",
                    "foreignField": "_id",
                    "as": "post_author"
                }
            },
            {"$unwind": "$post_author"}
        ]
        
        # Add search filter if provided
        if search_term:
            pipeline.append({
                "$match": {
                    "$or": [
                        {"post.content": {"$regex": search_term, "$options": "i"}},
                        {"notes": {"$regex": search_term, "$options": "i"}}
                    ]
                }
            })
        
        # Final projection
        pipeline.append({
            "$project": {
                "_id": {"$toString": "$_id"},
                "user_id": 1,
                "post_id": 1,
                "collection_id": 1,
                "notes": 1,
                "created_at": 1,
                "updated_at": 1,
                "post": {
                    "_id": {"$toString": "$post._id"},
                    "content": "$post.content",
                    "media_urls": "$post.media_urls",
                    "post_type": "$post.post_type",
                    "created_at": "$post.created_at",
                    "like_count": "$post.like_count",
                    "comment_count": "$post.comment_count",
                    "user": {
                        "username": "$post_author.username",
                        "full_name": "$post_author.full_name",
                        "profile_picture": "$post_author.profile_picture",
                        "is_verified": "$post_author.is_verified"
                    }
                },
                "collection": {
                    "$cond": {
                        "if": {"$gt": [{"$size": "$collection"}, 0]},
                        "then": {
                            "_id": {"$toString": {"$arrayElemAt": ["$collection._id", 0]}},
                            "name": {"$arrayElemAt": ["$collection.name", 0]},
                            "color": {"$arrayElemAt": ["$collection.color", 0]}
                        },
                        "else": None
                    }
                }
            }
        })
        
        bookmarks = await db.bookmarks.aggregate(pipeline).to_list(length=None)
        return bookmarks

    async def get_user_collections(
        self,
        user_id: str,
        include_shared: bool = False
    ) -> List[Dict[str, Any]]:
        """Get user's bookmark collections"""
        db = await self.get_db()
        
        # Build query
        if include_shared:
            query = {
                "$or": [
                    {"user_id": user_id},
                    {"shared_with": user_id}
                ]
            }
        else:
            query = {"user_id": user_id}
        
        collections = await db.bookmark_collections.find(query)\
            .sort("created_at", -1)\
            .to_list(length=None)
        
        for collection in collections:
            collection["_id"] = str(collection["_id"])
        
        return collections

    async def update_collection(
        self,
        collection_id: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        privacy: Optional[BookmarkPrivacy] = None,
        color: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update bookmark collection"""
        db = await self.get_db()
        
        update_data = {"updated_at": datetime.utcnow()}
        
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if privacy is not None:
            update_data["privacy"] = privacy.value
        if color is not None:
            update_data["color"] = color
        
        result = await db.bookmark_collections.update_one(
            {"_id": collection_id, "user_id": user_id},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            collection = await db.bookmark_collections.find_one({"_id": collection_id})
            if collection:
                collection["_id"] = str(collection["_id"])
            return collection
        
        return None

    async def delete_collection(
        self,
        collection_id: str,
        user_id: str
    ) -> bool:
        """Delete bookmark collection and move bookmarks to default"""
        db = await self.get_db()
        
        # Check if user owns the collection
        collection = await db.bookmark_collections.find_one({
            "_id": collection_id,
            "user_id": user_id
        })
        
        if not collection:
            return False
        
        # Move all bookmarks to no collection (collection_id = None)
        await db.bookmarks.update_many(
            {"collection_id": collection_id},
            {"$unset": {"collection_id": ""}}
        )
        
        # Delete the collection
        await db.bookmark_collections.delete_one({"_id": collection_id})
        
        return True

    async def share_collection(
        self,
        collection_id: str,
        user_id: str,
        shared_with_user_ids: List[str]
    ) -> bool:
        """Share collection with specific users"""
        db = await self.get_db()
        
        result = await db.bookmark_collections.update_one(
            {"_id": collection_id, "user_id": user_id},
            {
                "$set": {
                    "shared_with": shared_with_user_ids,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return result.modified_count > 0

    async def bulk_move_bookmarks(
        self,
        user_id: str,
        bookmark_ids: List[str],
        target_collection_id: Optional[str]
    ) -> int:
        """Move multiple bookmarks to a different collection"""
        db = await self.get_db()
        
        # Get current bookmarks to update collection counts
        bookmarks = await db.bookmarks.find({
            "_id": {"$in": bookmark_ids},
            "user_id": user_id
        }).to_list(length=None)
        
        if not bookmarks:
            return 0
        
        # Count bookmarks by current collection
        collection_counts = {}
        for bookmark in bookmarks:
            current_collection = bookmark.get("collection_id")
            collection_counts[current_collection] = collection_counts.get(current_collection, 0) + 1
        
        # Update bookmarks
        update_data = {"updated_at": datetime.utcnow()}
        if target_collection_id:
            update_data["collection_id"] = target_collection_id
        else:
            update_data = {"$unset": {"collection_id": ""}, "$set": {"updated_at": datetime.utcnow()}}
        
        if target_collection_id:
            result = await db.bookmarks.update_many(
                {"_id": {"$in": bookmark_ids}, "user_id": user_id},
                {"$set": update_data}
            )
        else:
            result = await db.bookmarks.update_many(
                {"_id": {"$in": bookmark_ids}, "user_id": user_id},
                update_data
            )
        
        # Update collection counts
        for collection_id, count in collection_counts.items():
            if collection_id:
                await db.bookmark_collections.update_one(
                    {"_id": collection_id},
                    {"$inc": {"bookmark_count": -count}}
                )
        
        if target_collection_id:
            await db.bookmark_collections.update_one(
                {"_id": target_collection_id},
                {"$inc": {"bookmark_count": result.modified_count}}
            )
        
        return result.modified_count

    async def bulk_delete_bookmarks(
        self,
        user_id: str,
        bookmark_ids: List[str]
    ) -> int:
        """Delete multiple bookmarks"""
        db = await self.get_db()
        
        # Get bookmarks to update counts
        bookmarks = await db.bookmarks.find({
            "_id": {"$in": bookmark_ids},
            "user_id": user_id
        }).to_list(length=None)
        
        if not bookmarks:
            return 0
        
        # Delete bookmarks
        result = await db.bookmarks.delete_many({
            "_id": {"$in": bookmark_ids},
            "user_id": user_id
        })
        
        # Update collection and post counts
        collection_counts = {}
        post_ids = []
        
        for bookmark in bookmarks:
            collection_id = bookmark.get("collection_id")
            if collection_id:
                collection_counts[collection_id] = collection_counts.get(collection_id, 0) + 1
            post_ids.append(bookmark["post_id"])
        
        # Update collection counts
        for collection_id, count in collection_counts.items():
            await db.bookmark_collections.update_one(
                {"_id": collection_id},
                {"$inc": {"bookmark_count": -count}}
            )
        
        # Update post bookmark counts
        if post_ids:
            await db.posts.update_many(
                {"_id": {"$in": post_ids}},
                {"$inc": {"bookmark_count": -1}}
            )
        
        return result.deleted_count

    async def check_bookmark_exists(
        self,
        user_id: str,
        post_id: str
    ) -> bool:
        """Check if user has bookmarked a post"""
        db = await self.get_db()
        
        bookmark = await db.bookmarks.find_one({
            "user_id": user_id,
            "post_id": post_id
        })
        
        return bookmark is not None

# Create global instance
bookmark_model = BookmarkModel()
