"""
Advanced Comment Model with nested threading and reactions
Supports unlimited depth comments with proper performance optimization
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import asyncio
from enum import Enum
from bson import ObjectId
from app.database.mongo_connection import get_database

class CommentSortType(str, Enum):
    """Comment sorting options"""
    NEWEST = "newest"
    OLDEST = "oldest"
    MOST_LIKED = "most_liked"
    MOST_REPLIES = "most_replies"

class CommentModel:
    """
    Advanced comment system with nested threading
    Supports reactions, editing, deletion, and advanced sorting
    """
    
    def __init__(self):
        self.db = None
        
    async def get_db(self):
        """Get database connection"""
        if self.db is None:
            self.db = await get_database()
        return self.db

    async def create_comment(
        self,
        user_id: str,
        post_id: str,
        content: str,
        parent_comment_id: Optional[str] = None,
        mentions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a new comment or reply"""
        print(f"🔍 create_comment called with user_id: {user_id} (type: {type(user_id)})")
        db = await self.get_db()
        
        # Build comment path for threading
        comment_path = []
        depth = 0
        
        if parent_comment_id:
            # Get parent comment to build path
            try:
                parent_object_id = ObjectId(parent_comment_id)
                parent_comment = await db.comments.find_one({"_id": parent_object_id})
                if parent_comment:
                    comment_path = parent_comment.get("path", []) + [parent_comment_id]
                    depth = len(comment_path)
            except Exception as e:
                print(f"❌ Invalid parent comment ID format: {parent_comment_id}, error: {e}")
                # Continue without parent - treat as top-level comment
        
        comment_data = {
            "user_id": ObjectId(user_id),  # Store as ObjectId
            "post_id": post_id,
            "content": content,
            "parent_comment_id": parent_comment_id,
            "path": comment_path,  # For efficient threading queries
            "depth": depth,
            "mentions": mentions or [],
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
            "reply_count": 0,
            "is_edited": False,
            "edit_history": [],
            "is_deleted": False,
            "deleted_at": None,
            "deleted_by": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        print(f"🔍 About to insert comment data: {comment_data}")
        result = await db.comments.insert_one(comment_data)
        comment_id = str(result.inserted_id)
        print(f"🔍 Comment inserted with ID: {comment_id}")
        
        # Update parent comment reply count
        if parent_comment_id:
            try:
                parent_object_id = ObjectId(parent_comment_id)
                await db.comments.update_one(
                    {"_id": parent_object_id},
                    {"$inc": {"reply_count": 1}}
                )
            except Exception as e:
                print(f"❌ Error updating parent comment reply count: {e}")
        
        # Update post comment count
        try:
            post_object_id = ObjectId(post_id)
            await db.posts.update_one(
                {"_id": post_object_id},
                {"$inc": {"comment_count": 1}}
            )
        except Exception as e:
            print(f"❌ Error updating post comment count: {e}")
        
        # Get created comment with user details
        print(f"🔍 Attempting to retrieve created comment with ID: {comment_id}")
        created_comment = await self.get_comment_by_id(comment_id, include_user=False)
        print(f"🔍 Retrieved comment (without user): {created_comment}")
        
        # If that works, try with user details
        if created_comment:
            print(f"🔍 Now trying to get comment with user details...")
            created_comment_with_user = await self.get_comment_by_id(comment_id, include_user=True)
            print(f"🔍 Retrieved comment (with user): {created_comment_with_user}")
            return created_comment_with_user or created_comment
        
        return created_comment

    async def get_comment_by_id(
        self,
        comment_id: str,
        include_user: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Get a single comment by ID with optional user details"""
        db = await self.get_db()
        
        print(f"🔍 get_comment_by_id called with ID: {comment_id}, include_user: {include_user}")
        
        try:
            # Convert string ID to ObjectId for MongoDB query
            object_id = ObjectId(comment_id)
            print(f"🔍 Converted to ObjectId: {object_id}")
        except Exception as e:
            print(f"❌ Invalid comment ID format: {comment_id}, error: {e}")
            return None
        
        if include_user:
            pipeline = [
                {"$match": {"_id": object_id}},
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
                        "user_id": {"$toString": "$user_id"},
                        "post_id": 1,
                        "content": 1,
                        "parent_comment_id": 1,
                        "path": 1,
                        "depth": 1,
                        "mentions": 1,
                        "reactions": 1,
                        "reply_count": 1,
                        "is_edited": 1,
                        "edit_history": 1,
                        "is_deleted": 1,
                        "created_at": 1,
                        "updated_at": 1,
                        "user.username": 1,
                        "user.full_name": 1,
                        "user.profile_picture": 1,
                        "user.is_verified": 1
                    }
                }
            ]
            
            print(f"🔍 Running aggregation pipeline for comment lookup")
            comments = await db.comments.aggregate(pipeline).to_list(length=1)
            print(f"🔍 Aggregation result: {comments}")
            result = comments[0] if comments else None
            print(f"🔍 Returning from aggregation: {result}")
            return result
        else:
            print(f"🔍 Running simple find_one query")
            comment = await db.comments.find_one({"_id": object_id})
            print(f"🔍 Simple query result: {comment}")
            if comment:
                comment["_id"] = str(comment["_id"])
                comment["user_id"] = str(comment["user_id"])  # Convert ObjectId to string
                print(f"🔍 Converted _id and user_id to string: {comment}")
            return comment

    async def get_post_comments(
        self,
        post_id: str,
        sort_type: CommentSortType = CommentSortType.NEWEST,
        limit: int = 20,
        skip: int = 0,
        max_depth: int = 3,
        load_replies: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get comments for a post with advanced sorting and threading
        Returns a hierarchical structure for nested comments
        """
        db = await self.get_db()
        
        # First, get top-level comments (depth 0)
        sort_options = {
            CommentSortType.NEWEST: {"created_at": -1},
            CommentSortType.OLDEST: {"created_at": 1},
            CommentSortType.MOST_LIKED: {"reactions.total": -1, "created_at": -1},
            CommentSortType.MOST_REPLIES: {"reply_count": -1, "created_at": -1}
        }
        
        sort_criteria = sort_options.get(sort_type, {"created_at": -1})
        
        # Pipeline for top-level comments
        pipeline = [
            {
                "$match": {
                    "post_id": post_id,
                    "depth": 0,
                    "is_deleted": False
                }
            },
            {"$sort": sort_criteria},
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
                    "user_id": {"$toString": "$user_id"},
                    "post_id": 1,
                    "content": 1,
                    "depth": 1,
                    "mentions": 1,
                    "reactions": 1,
                    "reply_count": 1,
                    "is_edited": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "user": {
                        "username": "$user.username",
                        "full_name": "$user.full_name",
                        "profile_picture": "$user.profile_picture",
                        "is_verified": "$user.is_verified"
                    }
                }
            }
        ]
        
        top_comments = await db.comments.aggregate(pipeline).to_list(length=None)
        
        if not load_replies or not top_comments:
            return top_comments
        
        # Load replies for each top-level comment
        for comment in top_comments:
            if comment["reply_count"] > 0:
                comment["replies"] = await self._get_comment_replies(
                    comment["_id"], 
                    max_depth - 1,
                    sort_type
                )
            else:
                comment["replies"] = []
        
        return top_comments

    async def _get_comment_replies(
        self,
        parent_comment_id: str,
        max_depth: int,
        sort_type: CommentSortType = CommentSortType.NEWEST,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get replies for a specific comment"""
        if max_depth <= 0:
            return []
        
        db = await self.get_db()
        
        sort_options = {
            CommentSortType.NEWEST: {"created_at": -1},
            CommentSortType.OLDEST: {"created_at": 1},
            CommentSortType.MOST_LIKED: {"reactions.total": -1, "created_at": -1},
            CommentSortType.MOST_REPLIES: {"reply_count": -1, "created_at": -1}
        }
        
        sort_criteria = sort_options.get(sort_type, {"created_at": -1})
        
        pipeline = [
            {
                "$match": {
                    "parent_comment_id": parent_comment_id,
                    "is_deleted": False
                }
            },
            {"$sort": sort_criteria},
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
                    "post_id": 1,
                    "content": 1,
                    "depth": 1,
                    "mentions": 1,
                    "reactions": 1,
                    "reply_count": 1,
                    "is_edited": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "user": {
                        "username": "$user.username",
                        "full_name": "$user.full_name",
                        "profile_picture": "$user.profile_picture",
                        "is_verified": "$user.is_verified"
                    }
                }
            }
        ]
        
        replies = await db.comments.aggregate(pipeline).to_list(length=None)
        
        # Recursively load nested replies
        for reply in replies:
            if reply["reply_count"] > 0 and max_depth > 1:
                reply["replies"] = await self._get_comment_replies(
                    reply["_id"],
                    max_depth - 1,
                    sort_type
                )
            else:
                reply["replies"] = []
        
        return replies

    async def update_comment(
        self,
        comment_id: str,
        user_id: str,
        new_content: str
    ) -> Optional[Dict[str, Any]]:
        """Update comment content with edit history"""
        db = await self.get_db()
        
        # Get current comment
        comment = await db.comments.find_one({
            "_id": comment_id,
            "user_id": user_id,
            "is_deleted": False
        })
        
        if not comment:
            return None
        
        # Add current content to edit history
        edit_history_entry = {
            "content": comment["content"],
            "edited_at": comment["updated_at"]
        }
        
        # Update comment
        result = await db.comments.update_one(
            {"_id": comment_id},
            {
                "$set": {
                    "content": new_content,
                    "is_edited": True,
                    "updated_at": datetime.utcnow()
                },
                "$push": {
                    "edit_history": edit_history_entry
                }
            }
        )
        
        if result.modified_count > 0:
            return await self.get_comment_by_id(comment_id)
        
        return None

    async def delete_comment(
        self,
        comment_id: str,
        user_id: str,
        is_admin: bool = False
    ) -> bool:
        """Soft delete a comment"""
        db = await self.get_db()
        
        # Build query - admins can delete any comment
        query = {"_id": comment_id, "is_deleted": False}
        if not is_admin:
            query["user_id"] = user_id
        
        comment = await db.comments.find_one(query)
        if not comment:
            return False
        
        # Soft delete the comment
        result = await db.comments.update_one(
            {"_id": comment_id},
            {
                "$set": {
                    "is_deleted": True,
                    "deleted_at": datetime.utcnow(),
                    "deleted_by": user_id,
                    "content": "[This comment has been deleted]"
                }
            }
        )
        
        if result.modified_count > 0:
            # Update post comment count
            await db.posts.update_one(
                {"_id": comment["post_id"]},
                {"$inc": {"comment_count": -1}}
            )
            
            # Update parent comment reply count
            if comment.get("parent_comment_id"):
                await db.comments.update_one(
                    {"_id": comment["parent_comment_id"]},
                    {"$inc": {"reply_count": -1}}
                )
            
            return True
        
        return False

    async def get_comment_thread(
        self,
        comment_id: str,
        max_depth: int = 5
    ) -> Optional[Dict[str, Any]]:
        """Get a complete comment thread starting from a specific comment"""
        db = await self.get_db()
        
        # Get the root comment and all its replies
        comment = await self.get_comment_by_id(comment_id)
        if not comment:
            return None
        
        # If this is a reply, get the root comment
        if comment.get("depth", 0) > 0:
            # Find the root comment by following the path
            path = comment.get("path", [])
            if path:
                root_comment = await self.get_comment_by_id(path[0])
                if root_comment:
                    # Load the complete thread from root
                    root_comment["replies"] = await self._get_comment_replies(
                        root_comment["_id"],
                        max_depth,
                        CommentSortType.OLDEST
                    )
                    return root_comment
        
        # This is already a root comment, load its replies
        if comment["reply_count"] > 0:
            comment["replies"] = await self._get_comment_replies(
                comment["_id"],
                max_depth,
                CommentSortType.OLDEST
            )
        else:
            comment["replies"] = []
        
        return comment

    async def search_comments(
        self,
        post_id: str,
        search_term: str,
        limit: int = 20,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Search comments by content"""
        db = await self.get_db()
        
        pipeline = [
            {
                "$match": {
                    "post_id": post_id,
                    "is_deleted": False,
                    "$text": {"$search": search_term}
                }
            },
            {"$sort": {"score": {"$meta": "textScore"}}},
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
                    "post_id": 1,
                    "content": 1,
                    "depth": 1,
                    "reactions": 1,
                    "reply_count": 1,
                    "is_edited": 1,
                    "created_at": 1,
                    "user": {
                        "username": "$user.username",
                        "full_name": "$user.full_name",
                        "profile_picture": "$user.profile_picture",
                        "is_verified": "$user.is_verified"
                    },
                    "score": {"$meta": "textScore"}
                }
            }
        ]
        
        comments = await db.comments.aggregate(pipeline).to_list(length=None)
        return comments

    async def get_user_comments(
        self,
        user_id: str,
        limit: int = 20,
        skip: int = 0,
        include_replies: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all comments by a specific user"""
        db = await self.get_db()
        
        query = {
            "user_id": user_id,
            "is_deleted": False
        }
        
        if not include_replies:
            query["depth"] = 0
        
        pipeline = [
            {"$match": query},
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
                "$project": {
                    "_id": {"$toString": "$_id"},
                    "content": 1,
                    "depth": 1,
                    "reactions": 1,
                    "reply_count": 1,
                    "is_edited": 1,
                    "created_at": 1,
                    "post": {
                        "_id": {"$toString": "$post._id"},
                        "content": "$post.content",
                        "user_id": "$post.user_id"
                    }
                }
            }
        ]
        
        comments = await db.comments.aggregate(pipeline).to_list(length=None)
        return comments

# Create global instance
comment_model = CommentModel()
