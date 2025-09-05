from datetime import datetime
from bson import ObjectId
from typing import Optional

# User role constants - Only regular users
USER_ROLE_USER = "user"

# User status constants
USER_STATUS_ACTIVE = "active"
USER_STATUS_INACTIVE = "inactive"
USER_STATUS_SUSPENDED = "suspended"
USER_STATUS_DELETED = "deleted"

async def get_user_by_email(db, email):
    """Get user by email"""
    if not email:
        return None
    return await db.users.find_one({"email": email.lower()})

async def get_user_by_username(db, username):
    """Get user by username"""
    if not username:
        return None
    
    print(f"🔍 Searching for username: '{username}' (searching as lowercase: '{username.lower()}')")
    result = await db.users.find_one({"username": username.lower()})
    print(f"🔍 Database search result: {result is not None}")
    if result:
        print(f"🔍 Found user with username: '{result.get('username')}', id: {result.get('_id')}")
    else:
        print(f"🚨 No user found with username: '{username.lower()}'")
    
    return result

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
        
        # If the update was attempted and the user was found, return the user
        # Even if modified_count is 0 (e.g., when setting email_verified=True when it's already True)
        if result.matched_count > 0:
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

# Profile management functions
async def get_full_profile(db, user_id):
    """Get complete user profile with all sections"""
    try:
        user = await get_user_by_id(db, user_id)
        if not user:
            return None
        
        # Convert ObjectId to string
        user["_id"] = str(user["_id"])
        
        # Ensure profile structure exists
        if "profile" not in user:
            user["profile"] = {}
        
        # Set defaults for missing sections
        profile_defaults = {
            "experience": [],
            "education": [],
            "skills": [],
            "languages": [],
            "certifications": [],
            "interests": [],
            "social_links": {},
            "cover_photo": None
        }
        
        for key, default_value in profile_defaults.items():
            if key not in user["profile"]:
                user["profile"][key] = default_value
        
        # Add stats
        user["stats"] = {
            "posts": 0,
            "followers": 0,
            "following": 0,
            "connections": 0,
            "profile_views": 0,
            "post_impressions": 0
        }
        
        return user
        
    except Exception as e:
        print(f"Error getting full profile: {str(e)}")
        return None

async def update_profile_section(db, user_id, section, data):
    """Update a specific section of user profile"""
    try:
        # Validate user exists
        user = await get_user_by_id(db, user_id)
        if not user:
            return None
        
        # Prepare update data based on section
        update_data = {
            "updated_at": datetime.utcnow()
        }
        
        if section == "basic_info":
            allowed_fields = ["full_name", "bio", "location", "website", "phone"]
            for field in allowed_fields:
                if field in data:
                    update_data[field] = data[field]
        
        elif section == "experience":
            update_data["profile.experience"] = data.get("experience", [])
        
        elif section == "education":
            update_data["profile.education"] = data.get("education", [])
        
        elif section == "skills":
            update_data["profile.skills"] = data.get("skills", [])
        
        elif section == "languages":
            update_data["profile.languages"] = data.get("languages", [])
        
        elif section == "certifications":
            update_data["profile.certifications"] = data.get("certifications", [])
        
        elif section == "interests":
            update_data["profile.interests"] = data.get("interests", [])
        
        elif section == "social_links":
            update_data["profile.social_links"] = data.get("social_links", {})
        
        elif section == "photos":
            if "profile_picture" in data:
                update_data["profile_picture"] = data["profile_picture"]
            if "cover_photo" in data:
                update_data["profile.cover_photo"] = data["cover_photo"]
        
        # Update user document
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
            
        result = await db.users.update_one(
            {"_id": user_id},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            # Return updated user
            updated_user = await get_user_by_id(db, user_id)
            if updated_user:
                updated_user["_id"] = str(updated_user["_id"])
                return updated_user
        
        return None
        
    except Exception as e:
        print(f"Error updating profile section {section}: {str(e)}")
        return None

async def add_profile_item(db, user_id, section, item_data):
    """Add a single item to a profile section"""
    try:
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        
        result = await db.users.update_one(
            {"_id": user_id},
            {
                "$push": {f"profile.{section}": item_data},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        return result.modified_count > 0
        
    except Exception as e:
        print(f"Error adding profile item: {str(e)}")
        return False

async def delete_profile_item(db, user_id, section, item_id):
    """Delete a single item from a profile section"""
    try:
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        
        result = await db.users.update_one(
            {"_id": user_id},
            {
                "$pull": {f"profile.{section}": {"id": item_id}},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        return result.modified_count > 0
        
    except Exception as e:
        print(f"Error deleting profile item: {str(e)}")
        return False

async def update_profile_item(db, user_id, section, item_id, item_data):
    """Update a single item in a profile section"""
    try:
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        
        # First remove the old item
        await db.users.update_one(
            {"_id": user_id},
            {"$pull": {f"profile.{section}": {"id": item_id}}}
        )
        
        # Then add the updated item
        result = await db.users.update_one(
            {"_id": user_id},
            {
                "$push": {f"profile.{section}": item_data},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        return result.modified_count > 0
        
    except Exception as e:
        print(f"Error updating profile item: {str(e)}")
        return False
