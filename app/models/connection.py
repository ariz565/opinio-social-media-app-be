"""
Connection System Model - LinkedIn-like connections
Supports connection requests, acceptance/rejection, and messaging permissions
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Set
from enum import Enum
import asyncio
from bson import ObjectId
from app.database.mongo_connection import get_database

class ConnectionStatus(str, Enum):
    """Connection request status"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    BLOCKED = "blocked"

class ConnectionType(str, Enum):
    """Types of connections"""
    STANDARD = "standard"
    CLOSE = "close"
    PROFESSIONAL = "professional"

class ConnectionModel:
    """
    Connection system for managing user connections
    Handles connection requests, messaging permissions, and connection management
    """
    
    def __init__(self):
        self.db = None
        
    async def get_db(self):
        """Get database connection"""
        if self.db is None:
            self.db = await get_database()
        return self.db

    async def send_connection_request(
        self,
        sender_id: str,
        receiver_id: str,
        message: Optional[str] = None,
        connection_type: ConnectionType = ConnectionType.STANDARD
    ) -> Dict[str, Any]:
        """Send a connection request to another user"""
        db = await self.get_db()
        
        # Validate users are different
        if sender_id == receiver_id:
            raise ValueError("Cannot send connection request to yourself")
        
        # Check if connection already exists
        existing_connection = await db.connections.find_one({
            "$or": [
                {"sender_id": sender_id, "receiver_id": receiver_id},
                {"sender_id": receiver_id, "receiver_id": sender_id}
            ]
        })
        
        if existing_connection:
            if existing_connection.get("status") == ConnectionStatus.ACCEPTED:
                return {"success": False, "message": "Users are already connected"}
            elif existing_connection.get("status") == ConnectionStatus.PENDING:
                return {"success": False, "message": "Connection request already pending"}
            elif existing_connection.get("status") == ConnectionStatus.REJECTED:
                # Allow sending new request after rejection
                await db.connections.delete_one({"_id": existing_connection["_id"]})
            elif existing_connection.get("status") == ConnectionStatus.BLOCKED:
                return {"success": False, "message": "Cannot send connection request"}
        
        # Check if receiver has blocked sender
        blocked = await db.connections.find_one({
            "sender_id": receiver_id,
            "receiver_id": sender_id,
            "status": ConnectionStatus.BLOCKED
        })
        
        if blocked:
            return {"success": False, "message": "Cannot send connection request"}
        
        # Create connection request
        connection_request = {
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "status": ConnectionStatus.PENDING,
            "connection_type": connection_type,
            "message": message,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=30)  # Auto-expire after 30 days
        }
        
        result = await db.connections.insert_one(connection_request)
        
        # Create notification for receiver
        await self._create_connection_notification(
            sender_id, receiver_id, "connection_request", message
        )
        
        return {
            "success": True,
            "message": "Connection request sent successfully",
            "connection_id": str(result.inserted_id)
        }

    async def respond_to_connection_request(
        self,
        connection_id: str,
        user_id: str,
        accept: bool
    ) -> Dict[str, Any]:
        """Accept or reject a connection request"""
        db = await self.get_db()
        
        # Find the connection request
        connection = await db.connections.find_one({
            "_id": ObjectId(connection_id),
            "receiver_id": user_id,
            "status": ConnectionStatus.PENDING
        })
        
        if not connection:
            return {"success": False, "message": "Connection request not found or already processed"}
        
        # Check if request has expired
        if connection.get("expires_at") and connection["expires_at"] < datetime.utcnow():
            await db.connections.delete_one({"_id": ObjectId(connection_id)})
            return {"success": False, "message": "Connection request has expired"}
        
        # Update connection status
        new_status = ConnectionStatus.ACCEPTED if accept else ConnectionStatus.REJECTED
        update_data = {
            "status": new_status,
            "updated_at": datetime.utcnow()
        }
        
        if accept:
            update_data["connected_at"] = datetime.utcnow()
        
        await db.connections.update_one(
            {"_id": ObjectId(connection_id)},
            {"$set": update_data}
        )
        
        # Create notification for sender
        notification_type = "connection_accepted" if accept else "connection_rejected"
        await self._create_connection_notification(
            user_id, connection["sender_id"], notification_type
        )
        
        return {
            "success": True,
            "message": f"Connection request {'accepted' if accept else 'rejected'} successfully"
        }

    async def get_connection_requests(
        self,
        user_id: str,
        incoming: bool = True,
        limit: int = 20,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Get incoming or outgoing connection requests"""
        db = await self.get_db()
        
        # Build query based on incoming/outgoing requests
        if incoming:
            query = {
                "receiver_id": user_id,
                "status": ConnectionStatus.PENDING
            }
        else:
            query = {
                "sender_id": user_id,
                "status": ConnectionStatus.PENDING
            }
        
        # Remove expired requests
        await db.connections.delete_many({
            "status": ConnectionStatus.PENDING,
            "expires_at": {"$lt": datetime.utcnow()}
        })
        
        # Get connection requests
        requests = await db.connections.find(query)\
            .sort("created_at", -1)\
            .skip(skip)\
            .limit(limit)\
            .to_list(length=None)
        
        # Enrich with user details
        enriched_requests = []
        for request in requests:
            # Get the other user's details
            other_user_id = request["sender_id"] if incoming else request["receiver_id"]
            user_details = await db.users.find_one(
                {"_id": ObjectId(other_user_id)},
                {"password": 0, "otp_code": 0, "reset_token": 0}
            )
            
            if user_details:
                enriched_request = {
                    "connection_id": str(request["_id"]),
                    "user": {
                        "id": str(user_details["_id"]),
                        "username": user_details.get("username"),
                        "full_name": user_details.get("full_name"),
                        "profile_picture": user_details.get("profile_picture"),
                        "bio": user_details.get("bio"),
                        "is_verified": user_details.get("is_verified", False)
                    },
                    "message": request.get("message"),
                    "connection_type": request.get("connection_type"),
                    "created_at": request["created_at"],
                    "expires_at": request.get("expires_at")
                }
                enriched_requests.append(enriched_request)
        
        return enriched_requests

    async def get_user_connections(
        self,
        user_id: str,
        connection_type: Optional[ConnectionType] = None,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's accepted connections"""
        db = await self.get_db()
        
        # Build query
        query = {
            "$or": [
                {"sender_id": user_id, "status": ConnectionStatus.ACCEPTED},
                {"receiver_id": user_id, "status": ConnectionStatus.ACCEPTED}
            ]
        }
        
        if connection_type:
            query["connection_type"] = connection_type
        
        # Get connections
        connections = await db.connections.find(query)\
            .sort("connected_at", -1)\
            .skip(skip)\
            .limit(limit)\
            .to_list(length=None)
        
        # Enrich with user details
        enriched_connections = []
        for connection in connections:
            # Get the other user's details
            other_user_id = (
                connection["receiver_id"] if connection["sender_id"] == user_id 
                else connection["sender_id"]
            )
            
            user_details = await db.users.find_one(
                {"_id": ObjectId(other_user_id)},
                {"password": 0, "otp_code": 0, "reset_token": 0}
            )
            
            if user_details:
                enriched_connection = {
                    "connection_id": str(connection["_id"]),
                    "user": {
                        "id": str(user_details["_id"]),
                        "username": user_details.get("username"),
                        "full_name": user_details.get("full_name"),
                        "profile_picture": user_details.get("profile_picture"),
                        "bio": user_details.get("bio"),
                        "is_verified": user_details.get("is_verified", False),
                        "is_online": user_details.get("is_online", False)
                    },
                    "connection_type": connection.get("connection_type"),
                    "connected_at": connection.get("connected_at"),
                    "mutual_connections": await self._get_mutual_connections_count(user_id, other_user_id)
                }
                enriched_connections.append(enriched_connection)
        
        return enriched_connections

    async def are_users_connected(
        self,
        user1_id: str,
        user2_id: str
    ) -> bool:
        """Check if two users are connected"""
        db = await self.get_db()
        
        connection = await db.connections.find_one({
            "$or": [
                {"sender_id": user1_id, "receiver_id": user2_id},
                {"sender_id": user2_id, "receiver_id": user1_id}
            ],
            "status": ConnectionStatus.ACCEPTED
        })
        
        return connection is not None

    async def remove_connection(
        self,
        user_id: str,
        connection_id: str
    ) -> Dict[str, Any]:
        """Remove/disconnect from another user"""
        db = await self.get_db()
        
        # Find the connection
        connection = await db.connections.find_one({
            "_id": ObjectId(connection_id),
            "$or": [
                {"sender_id": user_id},
                {"receiver_id": user_id}
            ],
            "status": ConnectionStatus.ACCEPTED
        })
        
        if not connection:
            return {"success": False, "message": "Connection not found"}
        
        # Remove the connection
        await db.connections.delete_one({"_id": ObjectId(connection_id)})
        
        return {"success": True, "message": "Connection removed successfully"}

    async def block_user(
        self,
        blocker_id: str,
        blocked_id: str
    ) -> Dict[str, Any]:
        """Block a user (prevents connection requests and messaging)"""
        db = await self.get_db()
        
        # Remove any existing connection
        await db.connections.delete_many({
            "$or": [
                {"sender_id": blocker_id, "receiver_id": blocked_id},
                {"sender_id": blocked_id, "receiver_id": blocker_id}
            ]
        })
        
        # Create block record
        block_record = {
            "sender_id": blocker_id,
            "receiver_id": blocked_id,
            "status": ConnectionStatus.BLOCKED,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await db.connections.insert_one(block_record)
        
        return {"success": True, "message": "User blocked successfully"}

    async def unblock_user(
        self,
        blocker_id: str,
        blocked_id: str
    ) -> Dict[str, Any]:
        """Unblock a user"""
        db = await self.get_db()
        
        # Remove block record
        result = await db.connections.delete_one({
            "sender_id": blocker_id,
            "receiver_id": blocked_id,
            "status": ConnectionStatus.BLOCKED
        })
        
        if result.deleted_count == 0:
            return {"success": False, "message": "User was not blocked"}
        
        return {"success": True, "message": "User unblocked successfully"}

    async def get_blocked_users(
        self,
        user_id: str,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Get list of users blocked by the current user"""
        db = await self.get_db()
        
        blocked_connections = await db.connections.find({
            "sender_id": user_id,
            "status": ConnectionStatus.BLOCKED
        })\
        .skip(skip)\
        .limit(limit)\
        .to_list(length=None)
        
        # Enrich with user details
        blocked_users = []
        for connection in blocked_connections:
            user_details = await db.users.find_one(
                {"_id": ObjectId(connection["receiver_id"])},
                {"password": 0, "otp_code": 0, "reset_token": 0}
            )
            
            if user_details:
                blocked_user = {
                    "connection_id": str(connection["_id"]),
                    "user": {
                        "id": str(user_details["_id"]),
                        "username": user_details.get("username"),
                        "full_name": user_details.get("full_name"),
                        "profile_picture": user_details.get("profile_picture")
                    },
                    "blocked_at": connection["created_at"]
                }
                blocked_users.append(blocked_user)
        
        return blocked_users

    async def get_connection_status(
        self,
        user1_id: str,
        user2_id: str
    ) -> Dict[str, Any]:
        """Get connection status between two users"""
        db = await self.get_db()
        
        try:
            # Ensure user IDs are valid ObjectId strings
            # Convert to ObjectId format if needed
            if ObjectId.is_valid(user1_id):
                user1_obj_id = str(ObjectId(user1_id))
            else:
                user1_obj_id = user1_id
                
            if ObjectId.is_valid(user2_id):
                user2_obj_id = str(ObjectId(user2_id))
            else:
                user2_obj_id = user2_id
        
            # Check for any connection between users
            connection = await db.connections.find_one({
                "$or": [
                    {"sender_id": user1_obj_id, "receiver_id": user2_obj_id},
                    {"sender_id": user2_obj_id, "receiver_id": user1_obj_id}
                ]
            })
        except Exception as e:
            # Log the error and return a safe default
            print(f"Error in get_connection_status: {str(e)} - user1_id: {user1_id}, user2_id: {user2_id}")
            return {"status": "none", "can_send_request": True}
        
        if not connection:
            return {"status": "none", "can_send_request": True}
        
        status = connection["status"]
        
        # Check who sent the request for pending status
        if status == ConnectionStatus.PENDING:
            if connection["sender_id"] == user1_id:
                return {"status": "pending_sent", "can_send_request": False}
            else:
                return {"status": "pending_received", "can_send_request": False}
        
        return {
            "status": status,
            "can_send_request": status not in [ConnectionStatus.ACCEPTED, ConnectionStatus.BLOCKED],
            "connection_id": str(connection["_id"]) if status == ConnectionStatus.ACCEPTED else None
        }

    async def get_connection_stats(
        self,
        user_id: str
    ) -> Dict[str, int]:
        """Get connection statistics for a user"""
        db = await self.get_db()
        
        # Count accepted connections
        connections_count = await db.connections.count_documents({
            "$or": [
                {"sender_id": user_id, "status": ConnectionStatus.ACCEPTED},
                {"receiver_id": user_id, "status": ConnectionStatus.ACCEPTED}
            ]
        })
        
        # Count pending incoming requests
        pending_requests = await db.connections.count_documents({
            "receiver_id": user_id,
            "status": ConnectionStatus.PENDING
        })
        
        return {
            "connections": connections_count,
            "pending_requests": pending_requests
        }

    async def get_mutual_connections(
        self,
        user1_id: str,
        user2_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get mutual connections between two users"""
        db = await self.get_db()
        
        # Get user1's connections
        user1_connections = await db.connections.find({
            "$or": [
                {"sender_id": user1_id, "status": ConnectionStatus.ACCEPTED},
                {"receiver_id": user1_id, "status": ConnectionStatus.ACCEPTED}
            ]
        }).to_list(length=None)
        
        # Get user2's connections
        user2_connections = await db.connections.find({
            "$or": [
                {"sender_id": user2_id, "status": ConnectionStatus.ACCEPTED},
                {"receiver_id": user2_id, "status": ConnectionStatus.ACCEPTED}
            ]
        }).to_list(length=None)
        
        # Extract user IDs from connections
        user1_connected_ids = set()
        for conn in user1_connections:
            other_id = conn["receiver_id"] if conn["sender_id"] == user1_id else conn["sender_id"]
            user1_connected_ids.add(other_id)
        
        user2_connected_ids = set()
        for conn in user2_connections:
            other_id = conn["receiver_id"] if conn["sender_id"] == user2_id else conn["sender_id"]
            user2_connected_ids.add(other_id)
        
        # Find mutual connections
        mutual_ids = user1_connected_ids.intersection(user2_connected_ids)
        
        # Get user details for mutual connections
        mutual_connections = []
        for user_id in list(mutual_ids)[:limit]:
            user_details = await db.users.find_one(
                {"_id": ObjectId(user_id)},
                {"username": 1, "full_name": 1, "profile_picture": 1}
            )
            
            if user_details:
                mutual_connections.append({
                    "id": str(user_details["_id"]),
                    "username": user_details.get("username"),
                    "full_name": user_details.get("full_name"),
                    "profile_picture": user_details.get("profile_picture")
                })
        
        return mutual_connections

    async def _get_mutual_connections_count(
        self,
        user1_id: str,
        user2_id: str
    ) -> int:
        """Get count of mutual connections between two users"""
        mutual_connections = await self.get_mutual_connections(user1_id, user2_id, limit=1000)
        return len(mutual_connections)

    async def _create_connection_notification(
        self,
        from_user_id: str,
        to_user_id: str,
        notification_type: str,
        message: Optional[str] = None
    ):
        """Create a notification for connection-related events"""
        db = await self.get_db()
        
        notification = {
            "user_id": to_user_id,
            "from_user_id": from_user_id,
            "type": notification_type,
            "message": message,
            "is_read": False,
            "created_at": datetime.utcnow()
        }
        
        try:
            await db.notifications.insert_one(notification)
        except Exception as e:
            # Log error but don't fail the main operation
            print(f"Failed to create notification: {e}")

    async def suggest_connections(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Suggest potential connections based on mutual connections and other factors"""
        db = await self.get_db()
        
        # Get user's current connections
        user_connections = await db.connections.find({
            "$or": [
                {"sender_id": user_id, "status": ConnectionStatus.ACCEPTED},
                {"receiver_id": user_id, "status": ConnectionStatus.ACCEPTED}
            ]
        }).to_list(length=None)
        
        # Extract connected user IDs
        connected_ids = set()
        for conn in user_connections:
            other_id = conn["receiver_id"] if conn["sender_id"] == user_id else conn["sender_id"]
            connected_ids.add(other_id)
        
        # Also exclude users with pending/blocked status
        excluded_connections = await db.connections.find({
            "$or": [
                {"sender_id": user_id},
                {"receiver_id": user_id}
            ]
        }).to_list(length=None)
        
        excluded_ids = set([user_id])  # Exclude self
        for conn in excluded_connections:
            other_id = conn["receiver_id"] if conn["sender_id"] == user_id else conn["sender_id"]
            excluded_ids.add(other_id)
        
        # Find users with mutual connections (2nd degree connections)
        suggestions = []
        for connected_id in connected_ids:
            # Get this user's connections
            their_connections = await db.connections.find({
                "$or": [
                    {"sender_id": connected_id, "status": ConnectionStatus.ACCEPTED},
                    {"receiver_id": connected_id, "status": ConnectionStatus.ACCEPTED}
                ]
            }).to_list(length=None)
            
            for conn in their_connections:
                suggested_id = conn["receiver_id"] if conn["sender_id"] == connected_id else conn["sender_id"]
                
                if suggested_id not in excluded_ids:
                    # Get user details
                    user_details = await db.users.find_one(
                        {"_id": ObjectId(suggested_id)},
                        {"password": 0, "otp_code": 0, "reset_token": 0}
                    )
                    
                    if user_details:
                        mutual_count = await self._get_mutual_connections_count(user_id, suggested_id)
                        suggestion = {
                            "user": {
                                "id": str(user_details["_id"]),
                                "username": user_details.get("username"),
                                "full_name": user_details.get("full_name"),
                                "profile_picture": user_details.get("profile_picture"),
                                "bio": user_details.get("bio"),
                                "is_verified": user_details.get("is_verified", False)
                            },
                            "mutual_connections": mutual_count,
                            "reason": f"{mutual_count} mutual connection{'s' if mutual_count != 1 else ''}"
                        }
                        
                        # Avoid duplicates
                        if not any(s["user"]["id"] == suggestion["user"]["id"] for s in suggestions):
                            suggestions.append(suggestion)
                        
                        if len(suggestions) >= limit:
                            break
            
            if len(suggestions) >= limit:
                break
        
        # Sort by mutual connections count
        suggestions.sort(key=lambda x: x["mutual_connections"], reverse=True)
        
        return suggestions[:limit]

# Create global instance
connection_model = ConnectionModel()
