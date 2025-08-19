from datetime import datetime
from bson import ObjectId
from typing import Optional

# User role constants
USER_ROLE_USER = "user"
USER_ROLE_ADMIN = "admin"
USER_ROLE_MODERATOR = "moderator"

# User status constants
USER_STATUS_ACTIVE = "active"
USER_STATUS_INACTIVE = "inactive"
USER_STATUS_SUSPENDED = "suspended"
USER_STATUS_DELETED = "deleted"

async def get_user_by_google_id(db, google_id):
    """Get user by Google ID"""
    if not google_id:
        return None
    return await db.users.find_one({"google_id": google_id})

async def get_user_by_email(db, email):
    """Get user by email"""
    if not email:
        return None
    return await db.users.find_one({"email": email.lower()})

async def get_user_by_username(db, username):
    """Get user by username"""
    if not username:
        return None
    return await db.users.find_one({"username": username.lower()})

async def get_user_by_id(db, user_id):
    """Get user by id"""
    if not user_id:
        return None
    
    try:
        if isinstance(user_id, str):
            if not ObjectId.is_valid(user_id):
                return None
            user_id = ObjectId(user_id)
        return await db.users.find_one({"_id": user_id})
    except Exception:
        return None

async def create_user(db, user_data):
    """Create a new user"""
    current_time = datetime.utcnow()
    
    # Prepare user document
    user_doc = {
        "email": user_data["email"].lower(),
        "username": user_data.get("username", "").lower(),
        "password": user_data.get("password"),  # Optional for OAuth users
        "full_name": user_data["full_name"],
        "profile_picture": user_data.get("profile_picture"),
        "bio": user_data.get("bio", ""),
        "role": USER_ROLE_USER,
        "status": USER_STATUS_ACTIVE,
        "followers_count": 0,
        "following_count": 0,
        "posts_count": 0,
        "email_verified": user_data.get("email_verified", False),
        "auth_provider": user_data.get("auth_provider", "email"),  # email, google, facebook, etc.
        "google_id": user_data.get("google_id"),
        "created_at": current_time,
        "updated_at": current_time,
        "last_login": None
    }
    
    # Insert user
    result = await db.users.insert_one(user_doc)
    
    # Return created user without password
    created_user = await get_user_by_id(db, result.inserted_id)
    if created_user and "password" in created_user:
        created_user.pop("password")
    
    return created_user

async def update_user(db, user_id, update_data):
    """Update user data"""
    if not user_id:
        return None
        
    try:
        if isinstance(user_id, str):
            if not ObjectId.is_valid(user_id):
                return None
            user_id = ObjectId(user_id)
        
        # Add updated timestamp
        update_data["updated_at"] = datetime.utcnow()
        
        # Update user
        result = await db.users.update_one(
            {"_id": user_id},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            updated_user = await get_user_by_id(db, user_id)
            if updated_user and "password" in updated_user:
                updated_user.pop("password")
            return updated_user
        return None
    except Exception:
        return None

async def delete_user(db, user_id):
    """Soft delete a user by setting status to deleted"""
    if not user_id:
        return False
        
    try:
        if isinstance(user_id, str):
            if not ObjectId.is_valid(user_id):
                return False
            user_id = ObjectId(user_id)
        
        result = await db.users.update_one(
            {"_id": user_id},
            {"$set": {
                "status": USER_STATUS_DELETED, 
                "updated_at": datetime.utcnow()
            }}
        )
        return result.modified_count > 0
    except Exception:
        return False

async def update_last_login(db, user_id):
    """Update user's last login timestamp"""
    if not user_id:
        return False
        
    try:
        if isinstance(user_id, str):
            if not ObjectId.is_valid(user_id):
                return False
            user_id = ObjectId(user_id)
        
        result = await db.users.update_one(
            {"_id": user_id},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        return result.modified_count > 0
    except Exception:
        return False

async def check_user_exists(db, email, username):
    """Check if user exists by email or username"""
    existing_user = await db.users.find_one({
        "$or": [
            {"email": email.lower()},
            {"username": username.lower()}
        ]
    })
    return existing_user is not None
