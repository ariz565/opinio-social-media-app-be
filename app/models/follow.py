"""
Advanced Follow System Model with connection features
Supports follow requests, close friends, blocking, and muting
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Set
from enum import Enum
import asyncio
from app.database.mongo_connection import get_database

class FollowStatus(str, Enum):
    """Follow request status"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"

class ConnectionType(str, Enum):
    """Types of user connections"""
    FOLLOW = "follow"
    CLOSE_FRIEND = "close_friend"
    BLOCKED = "blocked"
    MUTED = "muted"
    RESTRICTED = "restricted"

class FollowModel:
    """
    Advanced follow system with privacy controls and connection management
    Supports follow requests, close friends, blocking, muting, and restrictions
    """
    
    def __init__(self):
        self.db = None
        
    async def get_db(self):
        """Get database connection"""
        if not self.db:
            self.db = await get_database()
        return self.db

    async def follow_user(
        self,
        follower_id: str,
        following_id: str,
        is_private_account: bool = False
    ) -> Dict[str, Any]:
        """Follow a user or send follow request for private accounts"""
        db = await self.get_db()
        
        # Check if already following or request exists
        existing_follow = await db.follows.find_one({
            "follower_id": follower_id,
            "following_id": following_id
        })
        
        if existing_follow:
            if existing_follow["status"] == FollowStatus.ACCEPTED:
                return {"error": "Already following this user"}
            elif existing_follow["status"] == FollowStatus.PENDING:
                return {"error": "Follow request already sent"}
            elif existing_follow["status"] == FollowStatus.DECLINED:
                # Update declined request to pending
                await db.follows.update_one(
                    {"_id": existing_follow["_id"]},
                    {
                        "$set": {
                            "status": FollowStatus.PENDING.value,
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
                return {"status": "pending", "message": "Follow request sent"}
        
        # Check if blocked
        is_blocked = await self.is_user_blocked(following_id, follower_id)
        if is_blocked:
            return {"error": "Cannot follow this user"}
        
        # Determine status based on account privacy
        status = FollowStatus.PENDING if is_private_account else FollowStatus.ACCEPTED
        
        # Create follow record
        follow_data = {
            "follower_id": follower_id,
            "following_id": following_id,
            "status": status.value,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await db.follows.insert_one(follow_data)
        
        # Update user counts if accepted immediately
        if status == FollowStatus.ACCEPTED:
            await self._update_follow_counts(follower_id, following_id, increment=True)
        
        return {
            "_id": str(result.inserted_id),
            "status": status.value,
            "message": "Following" if status == FollowStatus.ACCEPTED else "Follow request sent"
        }

    async def unfollow_user(
        self,
        follower_id: str,
        following_id: str
    ) -> bool:
        """Unfollow a user or cancel follow request"""
        db = await self.get_db()
        
        # Find and remove follow record
        follow = await db.follows.find_one_and_delete({
            "follower_id": follower_id,
            "following_id": following_id
        })
        
        if follow:
            # Update counts only if was accepted
            if follow["status"] == FollowStatus.ACCEPTED:
                await self._update_follow_counts(follower_id, following_id, increment=False)
            
            return True
        
        return False

    async def respond_to_follow_request(
        self,
        request_id: str,
        user_id: str,
        accept: bool
    ) -> Dict[str, Any]:
        """Accept or decline a follow request"""
        db = await self.get_db()
        
        # Find the follow request
        follow_request = await db.follows.find_one({
            "_id": request_id,
            "following_id": user_id,
            "status": FollowStatus.PENDING.value
        })
        
        if not follow_request:
            return {"error": "Follow request not found"}
        
        new_status = FollowStatus.ACCEPTED if accept else FollowStatus.DECLINED
        
        # Update follow request
        result = await db.follows.update_one(
            {"_id": request_id},
            {
                "$set": {
                    "status": new_status.value,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Update counts if accepted
        if accept and result.modified_count > 0:
            await self._update_follow_counts(
                follow_request["follower_id"],
                follow_request["following_id"],
                increment=True
            )
        
        return {
            "status": new_status.value,
            "message": "Follow request accepted" if accept else "Follow request declined"
        }

    async def get_followers(
        self,
        user_id: str,
        limit: int = 20,
        skip: int = 0,
        search_term: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user's followers with user details"""
        db = await self.get_db()
        
        # Build pipeline
        pipeline = [
            {
                "$match": {
                    "following_id": user_id,
                    "status": FollowStatus.ACCEPTED.value
                }
            },
            {"$sort": {"created_at": -1}},
            {"$skip": skip},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "follower_id",
                    "foreignField": "_id",
                    "as": "follower"
                }
            },
            {"$unwind": "$follower"}
        ]
        
        # Add search filter if provided
        if search_term:
            pipeline.append({
                "$match": {
                    "$or": [
                        {"follower.username": {"$regex": search_term, "$options": "i"}},
                        {"follower.full_name": {"$regex": search_term, "$options": "i"}}
                    ]
                }
            })
        
        # Final projection
        pipeline.append({
            "$project": {
                "_id": {"$toString": "$_id"},
                "follower_id": 1,
                "created_at": 1,
                "follower": {
                    "_id": {"$toString": "$follower._id"},
                    "username": "$follower.username",
                    "full_name": "$follower.full_name",
                    "profile_picture": "$follower.profile_picture",
                    "is_verified": "$follower.is_verified",
                    "bio": "$follower.bio"
                }
            }
        })
        
        followers = await db.follows.aggregate(pipeline).to_list(length=None)
        return followers

    async def get_following(
        self,
        user_id: str,
        limit: int = 20,
        skip: int = 0,
        search_term: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get users that a user is following"""
        db = await self.get_db()
        
        # Build pipeline
        pipeline = [
            {
                "$match": {
                    "follower_id": user_id,
                    "status": FollowStatus.ACCEPTED.value
                }
            },
            {"$sort": {"created_at": -1}},
            {"$skip": skip},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "following_id",
                    "foreignField": "_id",
                    "as": "following"
                }
            },
            {"$unwind": "$following"}
        ]
        
        # Add search filter if provided
        if search_term:
            pipeline.append({
                "$match": {
                    "$or": [
                        {"following.username": {"$regex": search_term, "$options": "i"}},
                        {"following.full_name": {"$regex": search_term, "$options": "i"}}
                    ]
                }
            })
        
        # Final projection
        pipeline.append({
            "$project": {
                "_id": {"$toString": "$_id"},
                "following_id": 1,
                "created_at": 1,
                "following": {
                    "_id": {"$toString": "$following._id"},
                    "username": "$following.username",
                    "full_name": "$following.full_name",
                    "profile_picture": "$following.profile_picture",
                    "is_verified": "$following.is_verified",
                    "bio": "$following.bio"
                }
            }
        })
        
        following = await db.follows.aggregate(pipeline).to_list(length=None)
        return following

    async def get_follow_requests(
        self,
        user_id: str,
        incoming: bool = True,
        limit: int = 20,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Get pending follow requests"""
        db = await self.get_db()
        
        # Build match query for incoming or outgoing requests
        if incoming:
            match_query = {
                "following_id": user_id,
                "status": FollowStatus.PENDING.value
            }
            lookup_field = "follower_id"
            user_field = "follower"
        else:
            match_query = {
                "follower_id": user_id,
                "status": FollowStatus.PENDING.value
            }
            lookup_field = "following_id"
            user_field = "following"
        
        pipeline = [
            {"$match": match_query},
            {"$sort": {"created_at": -1}},
            {"$skip": skip},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "users",
                    "localField": lookup_field,
                    "foreignField": "_id",
                    "as": user_field
                }
            },
            {"$unwind": f"${user_field}"},
            {
                "$project": {
                    "_id": {"$toString": "$_id"},
                    "created_at": 1,
                    user_field: {
                        "_id": {"$toString": f"${user_field}._id"},
                        "username": f"${user_field}.username",
                        "full_name": f"${user_field}.full_name",
                        "profile_picture": f"${user_field}.profile_picture",
                        "is_verified": f"${user_field}.is_verified"
                    }
                }
            }
        ]
        
        requests = await db.follows.aggregate(pipeline).to_list(length=None)
        return requests

    async def add_to_close_friends(
        self,
        user_id: str,
        friend_id: str
    ) -> bool:
        """Add user to close friends list"""
        db = await self.get_db()
        
        # Check if already following
        follow = await db.follows.find_one({
            "follower_id": friend_id,
            "following_id": user_id,
            "status": FollowStatus.ACCEPTED.value
        })
        
        if not follow:
            return False
        
        # Add to close friends
        result = await db.user_connections.update_one(
            {"user_id": user_id},
            {
                "$addToSet": {"close_friends": friend_id},
                "$set": {"updated_at": datetime.utcnow()}
            },
            upsert=True
        )
        
        return True

    async def remove_from_close_friends(
        self,
        user_id: str,
        friend_id: str
    ) -> bool:
        """Remove user from close friends list"""
        db = await self.get_db()
        
        result = await db.user_connections.update_one(
            {"user_id": user_id},
            {
                "$pull": {"close_friends": friend_id},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        return result.modified_count > 0

    async def block_user(
        self,
        user_id: str,
        blocked_user_id: str
    ) -> bool:
        """Block a user"""
        db = await self.get_db()
        
        # Remove any existing follow relationships
        await db.follows.delete_many({
            "$or": [
                {"follower_id": user_id, "following_id": blocked_user_id},
                {"follower_id": blocked_user_id, "following_id": user_id}
            ]
        })
        
        # Update follow counts
        await self._update_follow_counts(user_id, blocked_user_id, increment=False)
        await self._update_follow_counts(blocked_user_id, user_id, increment=False)
        
        # Add to blocked list
        result = await db.user_connections.update_one(
            {"user_id": user_id},
            {
                "$addToSet": {"blocked_users": blocked_user_id},
                "$pull": {
                    "close_friends": blocked_user_id,
                    "muted_users": blocked_user_id,
                    "restricted_users": blocked_user_id
                },
                "$set": {"updated_at": datetime.utcnow()}
            },
            upsert=True
        )
        
        return True

    async def unblock_user(
        self,
        user_id: str,
        blocked_user_id: str
    ) -> bool:
        """Unblock a user"""
        db = await self.get_db()
        
        result = await db.user_connections.update_one(
            {"user_id": user_id},
            {
                "$pull": {"blocked_users": blocked_user_id},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        return result.modified_count > 0

    async def mute_user(
        self,
        user_id: str,
        muted_user_id: str
    ) -> bool:
        """Mute a user"""
        db = await self.get_db()
        
        result = await db.user_connections.update_one(
            {"user_id": user_id},
            {
                "$addToSet": {"muted_users": muted_user_id},
                "$set": {"updated_at": datetime.utcnow()}
            },
            upsert=True
        )
        
        return True

    async def unmute_user(
        self,
        user_id: str,
        muted_user_id: str
    ) -> bool:
        """Unmute a user"""
        db = await self.get_db()
        
        result = await db.user_connections.update_one(
            {"user_id": user_id},
            {
                "$pull": {"muted_users": muted_user_id},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        return result.modified_count > 0

    async def restrict_user(
        self,
        user_id: str,
        restricted_user_id: str
    ) -> bool:
        """Restrict a user (limited interactions)"""
        db = await self.get_db()
        
        result = await db.user_connections.update_one(
            {"user_id": user_id},
            {
                "$addToSet": {"restricted_users": restricted_user_id},
                "$set": {"updated_at": datetime.utcnow()}
            },
            upsert=True
        )
        
        return True

    async def unrestrict_user(
        self,
        user_id: str,
        restricted_user_id: str
    ) -> bool:
        """Remove restriction from a user"""
        db = await self.get_db()
        
        result = await db.user_connections.update_one(
            {"user_id": user_id},
            {
                "$pull": {"restricted_users": restricted_user_id},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        return result.modified_count > 0

    async def get_user_connections(
        self,
        user_id: str
    ) -> Dict[str, List[str]]:
        """Get all user connections (close friends, blocked, muted, restricted)"""
        db = await self.get_db()
        
        connections = await db.user_connections.find_one({"user_id": user_id})
        
        if not connections:
            return {
                "close_friends": [],
                "blocked_users": [],
                "muted_users": [],
                "restricted_users": []
            }
        
        return {
            "close_friends": connections.get("close_friends", []),
            "blocked_users": connections.get("blocked_users", []),
            "muted_users": connections.get("muted_users", []),
            "restricted_users": connections.get("restricted_users", [])
        }

    async def is_user_blocked(
        self,
        user_id: str,
        other_user_id: str
    ) -> bool:
        """Check if a user is blocked by another user"""
        db = await self.get_db()
        
        connections = await db.user_connections.find_one({
            "user_id": user_id,
            "blocked_users": other_user_id
        })
        
        return connections is not None

    async def is_user_muted(
        self,
        user_id: str,
        other_user_id: str
    ) -> bool:
        """Check if a user is muted by another user"""
        db = await self.get_db()
        
        connections = await db.user_connections.find_one({
            "user_id": user_id,
            "muted_users": other_user_id
        })
        
        return connections is not None

    async def is_close_friend(
        self,
        user_id: str,
        other_user_id: str
    ) -> bool:
        """Check if a user is in close friends list"""
        db = await self.get_db()
        
        connections = await db.user_connections.find_one({
            "user_id": user_id,
            "close_friends": other_user_id
        })
        
        return connections is not None

    async def get_follow_status(
        self,
        follower_id: str,
        following_id: str
    ) -> Optional[str]:
        """Get follow status between two users"""
        db = await self.get_db()
        
        follow = await db.follows.find_one({
            "follower_id": follower_id,
            "following_id": following_id
        })
        
        return follow["status"] if follow else None

    async def get_mutual_connections(
        self,
        user_id: str,
        other_user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get mutual followers between two users"""
        db = await self.get_db()
        
        pipeline = [
            {
                "$match": {
                    "following_id": user_id,
                    "status": FollowStatus.ACCEPTED.value
                }
            },
            {
                "$lookup": {
                    "from": "follows",
                    "let": {"follower_id": "$follower_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$follower_id", "$$follower_id"]},
                                        {"$eq": ["$following_id", other_user_id]},
                                        {"$eq": ["$status", FollowStatus.ACCEPTED.value]}
                                    ]
                                }
                            }
                        }
                    ],
                    "as": "mutual_follow"
                }
            },
            {
                "$match": {
                    "mutual_follow": {"$ne": []}
                }
            },
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "follower_id",
                    "foreignField": "_id",
                    "as": "user"
                }
            },
            {"$unwind": "$user"},
            {
                "$project": {
                    "_id": {"$toString": "$user._id"},
                    "username": "$user.username",
                    "full_name": "$user.full_name",
                    "profile_picture": "$user.profile_picture",
                    "is_verified": "$user.is_verified"
                }
            }
        ]
        
        mutual_followers = await db.follows.aggregate(pipeline).to_list(length=None)
        return mutual_followers

    async def get_friend_suggestions(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get friend suggestions based on mutual connections"""
        db = await self.get_db()
        
        # Get users followed by people the user follows
        pipeline = [
            {
                "$match": {
                    "follower_id": user_id,
                    "status": FollowStatus.ACCEPTED.value
                }
            },
            {
                "$lookup": {
                    "from": "follows",
                    "let": {"following_id": "$following_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$follower_id", "$$following_id"]},
                                        {"$eq": ["$status", FollowStatus.ACCEPTED.value]},
                                        {"$ne": ["$following_id", user_id]}
                                    ]
                                }
                            }
                        }
                    ],
                    "as": "suggestions"
                }
            },
            {"$unwind": "$suggestions"},
            {
                "$group": {
                    "_id": "$suggestions.following_id",
                    "mutual_count": {"$sum": 1}
                }
            },
            {"$sort": {"mutual_count": -1}},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "_id",
                    "foreignField": "_id",
                    "as": "user"
                }
            },
            {"$unwind": "$user"},
            {
                "$project": {
                    "_id": {"$toString": "$user._id"},
                    "username": "$user.username",
                    "full_name": "$user.full_name",
                    "profile_picture": "$user.profile_picture",
                    "is_verified": "$user.is_verified",
                    "mutual_count": 1
                }
            }
        ]
        
        suggestions = await db.follows.aggregate(pipeline).to_list(length=None)
        return suggestions

    async def _update_follow_counts(
        self,
        follower_id: str,
        following_id: str,
        increment: bool
    ):
        """Update follower and following counts"""
        db = await self.get_db()
        
        increment_value = 1 if increment else -1
        
        # Update follower's following count
        await db.users.update_one(
            {"_id": follower_id},
            {"$inc": {"following_count": increment_value}}
        )
        
        # Update following's follower count
        await db.users.update_one(
            {"_id": following_id},
            {"$inc": {"follower_count": increment_value}}
        )

# Create global instance
follow_model = FollowModel()
