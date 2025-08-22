"""
Reaction model for advanced like/reaction system
Supports multiple reaction types with proper indexing
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import asyncio
from app.database.mongo_connection import get_database

class ReactionType(str, Enum):
    """Supported reaction types"""
    LIKE = "like"
    LOVE = "love"
    LAUGH = "laugh"
    WOW = "wow"
    SAD = "sad"
    ANGRY = "angry"
    CARE = "care"

class ReactionModel:
    """
    Advanced reaction system with multiple reaction types
    Supports reactions on posts, comments, and stories
    """
    
    def __init__(self):
        self.db = None
        
    async def get_db(self):
        """Get database connection"""
        try:
            if self.db is None:
                print("DEBUG: Getting new database connection")
                self.db = await get_database()
                print(f"DEBUG: Database connection obtained: {type(self.db)}")
            return self.db
        except Exception as e:
            print(f"DEBUG: Error getting database: {e}")
            raise

    async def add_reaction(
        self,
        user_id: str,
        target_id: str,
        target_type: str,  # 'post', 'comment', 'story'
        reaction_type: ReactionType
    ) -> Dict[str, Any]:
        """
        Add or update a reaction
        Only one reaction per user per target
        """
        db = await self.get_db()
        
        # Check if user already reacted
        existing_reaction = await db.reactions.find_one({
            "user_id": user_id,
            "target_id": target_id,
            "target_type": target_type
        })
        
        if existing_reaction:
            # Update existing reaction
            result = await db.reactions.update_one(
                {"_id": existing_reaction["_id"]},
                {
                    "$set": {
                        "reaction_type": reaction_type.value,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # Update target reaction counts
            await self._update_reaction_counts(target_id, target_type, existing_reaction["reaction_type"], reaction_type.value)
            
            return {
                "_id": str(existing_reaction["_id"]),
                "user_id": user_id,
                "target_id": target_id,
                "target_type": target_type,
                "reaction_type": reaction_type.value,
                "updated_at": datetime.utcnow(),
                "action": "updated"
            }
        else:
            # Create new reaction
            reaction_data = {
                "user_id": user_id,
                "target_id": target_id,
                "target_type": target_type,
                "reaction_type": reaction_type.value,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = await db.reactions.insert_one(reaction_data)
            
            # Update target reaction counts
            await self._update_reaction_counts(target_id, target_type, None, reaction_type.value)
            
            return {
                "_id": str(result.inserted_id),
                "action": "created",
                **reaction_data
            }

    async def remove_reaction(
        self,
        user_id: str,
        target_id: str,
        target_type: str
    ) -> bool:
        """Remove a user's reaction from a target"""
        db = await self.get_db()
        
        # Find and remove reaction
        reaction = await db.reactions.find_one_and_delete({
            "user_id": user_id,
            "target_id": target_id,
            "target_type": target_type
        })
        
        if reaction:
            # Update target reaction counts
            await self._update_reaction_counts(target_id, target_type, reaction["reaction_type"], None)
            return True
        
        return False

    async def get_reactions_for_target(
        self,
        target_id: str,
        target_type: str,
        reaction_type: Optional[ReactionType] = None,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Get reactions for a specific target with user details"""
        db = await self.get_db()
        
        # Build query
        query = {
            "target_id": target_id,
            "target_type": target_type
        }
        
        if reaction_type:
            query["reaction_type"] = reaction_type.value
        
        # Aggregation pipeline to include user details
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
                    "reaction_type": 1,
                    "created_at": 1,
                    "user.username": 1,
                    "user.full_name": 1,
                    "user.profile_picture": 1,
                    "user.is_verified": 1
                }
            }
        ]
        
        reactions = await db.reactions.aggregate(pipeline).to_list(length=None)
        return reactions

    async def get_reaction_counts(
        self,
        target_id: str,
        target_type: str
    ) -> Dict[str, int]:
        """Get reaction counts by type for a target"""
        db = await self.get_db()
        
        pipeline = [
            {
                "$match": {
                    "target_id": target_id,
                    "target_type": target_type
                }
            },
            {
                "$group": {
                    "_id": "$reaction_type",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        results = await db.reactions.aggregate(pipeline).to_list(length=None)
        
        # Initialize all reaction types with 0
        counts = {reaction_type.value: 0 for reaction_type in ReactionType}
        
        # Update with actual counts
        for result in results:
            counts[result["_id"]] = result["count"]
        
        # Add total count
        counts["total"] = sum(counts.values())
        
        return counts

    async def get_user_reaction(
        self,
        user_id: str,
        target_id: str,
        target_type: str
    ) -> Optional[Dict[str, Any]]:
        """Get a specific user's reaction for a target"""
        try:
            print(f"DEBUG: get_user_reaction called with user_id={user_id}, target_id={target_id}, target_type={target_type}")
            db = await self.get_db()
            print(f"DEBUG: Database obtained: {type(db)}")
            
            reaction = await db.reactions.find_one({
                "user_id": user_id,
                "target_id": target_id,
                "target_type": target_type
            })
            print(f"DEBUG: Reaction found: {reaction}")
            
            if reaction:
                reaction["_id"] = str(reaction["_id"])
            
            return reaction
        except Exception as e:
            print(f"DEBUG: Error in get_user_reaction: {e}")
            raise

    async def get_user_reactions(
        self,
        user_id: str,
        target_type: Optional[str] = None,
        reaction_type: Optional[ReactionType] = None,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all reactions by a specific user"""
        db = await self.get_db()
        
        query = {"user_id": user_id}
        
        if target_type:
            query["target_type"] = target_type
        
        if reaction_type:
            query["reaction_type"] = reaction_type.value
        
        reactions = await db.reactions.find(query)\
            .sort("created_at", -1)\
            .skip(skip)\
            .limit(limit)\
            .to_list(length=None)
        
        for reaction in reactions:
            reaction["_id"] = str(reaction["_id"])
        
        return reactions

    async def _update_reaction_counts(
        self,
        target_id: str,
        target_type: str,
        old_reaction: Optional[str],
        new_reaction: Optional[str]
    ):
        """Update reaction counts in the target document"""
        db = await self.get_db()
        
        # Determine collection and update operations
        collection_map = {
            "post": "posts",
            "comment": "comments",
            "story": "stories"
        }
        
        collection_name = collection_map.get(target_type)
        if not collection_name:
            return
        
        collection = getattr(db, collection_name)
        
        # Build update operations
        update_ops = {}
        
        if old_reaction:
            # Decrement old reaction count
            update_ops[f"reactions.{old_reaction}"] = -1
            update_ops["reactions.total"] = -1
        
        if new_reaction:
            # Increment new reaction count
            update_ops[f"reactions.{new_reaction}"] = 1
            if not old_reaction:  # Only increment total if it's a new reaction, not an update
                update_ops["reactions.total"] = 1
        
        if update_ops:
            await collection.update_one(
                {"_id": target_id},
                {"$inc": update_ops}
            )

    async def get_popular_reactions(
        self,
        target_type: str,
        days: int = 7,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get most reacted content in the last N days"""
        db = await self.get_db()
        
        from datetime import timedelta
        from_date = datetime.utcnow() - timedelta(days=days)
        
        pipeline = [
            {
                "$match": {
                    "target_type": target_type,
                    "created_at": {"$gte": from_date}
                }
            },
            {
                "$group": {
                    "_id": "$target_id",
                    "total_reactions": {"$sum": 1},
                    "reaction_types": {"$push": "$reaction_type"}
                }
            },
            {"$sort": {"total_reactions": -1}},
            {"$limit": limit}
        ]
        
        results = await db.reactions.aggregate(pipeline).to_list(length=None)
        return results

# Create global instance
reaction_model = ReactionModel()
