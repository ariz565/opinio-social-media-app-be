from datetime import datetime
from bson import ObjectId
from typing import Optional

# Admin role constants
ADMIN_ROLE_ADMIN = "admin"
ADMIN_ROLE_MODERATOR = "moderator"

# Admin status constants
ADMIN_STATUS_ACTIVE = "active"
ADMIN_STATUS_INACTIVE = "inactive"
ADMIN_STATUS_SUSPENDED = "suspended"
ADMIN_STATUS_DELETED = "deleted"

async def get_admin_by_email(db, email):
    """Get admin by email"""
    if not email:
        return None
    return await db.admins.find_one({"email": email.lower()})

async def get_admin_by_username(db, username):
    """Get admin by username"""
    if not username:
        return None
    return await db.admins.find_one({"username": username.lower()})

async def get_admin_by_id(db, admin_id):
    """Get admin by id"""
    if not admin_id:
        return None
    
    try:
        if isinstance(admin_id, str):
            if not ObjectId.is_valid(admin_id):
                return None
            admin_id = ObjectId(admin_id)
        return await db.admins.find_one({"_id": admin_id})
    except Exception:
        return None

async def create_admin(db, admin_data):
    """Create a new admin or moderator"""
    current_time = datetime.utcnow()
    
    # Prepare admin document
    admin_doc = {
        "email": admin_data["email"].lower(),
        "username": admin_data.get("username", "").lower(),
        "password": admin_data["password"],  # Password should be already hashed
        "full_name": admin_data["full_name"],
        "role": admin_data.get("role", ADMIN_ROLE_ADMIN),  # Default to admin
        "status": ADMIN_STATUS_ACTIVE,
        "created_at": current_time,
        "updated_at": current_time,
        "last_login": None,
        "created_by": admin_data.get("created_by"),  # Track who created this admin
        "permissions": admin_data.get("permissions", []),  # Specific permissions
        "bio": admin_data.get("bio", "System Administrator")
    }
    
    # Insert admin
    result = await db.admins.insert_one(admin_doc)
    
    # Return created admin without password
    created_admin = await get_admin_by_id(db, result.inserted_id)
    if created_admin and "password" in created_admin:
        created_admin.pop("password")
    
    return created_admin

async def update_admin(db, admin_id, update_data):
    """Update admin information"""
    if not admin_id:
        return None
    
    try:
        if isinstance(admin_id, str):
            if not ObjectId.is_valid(admin_id):
                return None
            admin_id = ObjectId(admin_id)
    except Exception:
        return None
    
    # Add updated_at timestamp
    update_data["updated_at"] = datetime.utcnow()
    
    # Update admin document
    result = await db.admins.update_one(
        {"_id": admin_id},
        {"$set": update_data}
    )
    
    if result.modified_count > 0:
        return await get_admin_by_id(db, admin_id)
    return None

async def delete_admin(db, admin_id):
    """Soft delete admin (mark as deleted)"""
    if not admin_id:
        return False
    
    try:
        if isinstance(admin_id, str):
            if not ObjectId.is_valid(admin_id):
                return False
            admin_id = ObjectId(admin_id)
    except Exception:
        return False
    
    # Soft delete by updating status
    result = await db.admins.update_one(
        {"_id": admin_id},
        {"$set": {
            "status": ADMIN_STATUS_DELETED,
            "updated_at": datetime.utcnow()
        }}
    )
    
    return result.modified_count > 0

async def update_admin_last_login(db, admin_id):
    """Update admin last login timestamp"""
    if not admin_id:
        return False
    
    try:
        if isinstance(admin_id, str):
            if not ObjectId.is_valid(admin_id):
                return False
            admin_id = ObjectId(admin_id)
    except Exception:
        return False
    
    # Update last login
    result = await db.admins.update_one(
        {"_id": admin_id},
        {"$set": {
            "last_login": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }}
    )
    
    return result.modified_count > 0

async def check_admin_exists(db, email, username):
    """Check if admin exists by email or username"""
    if not email and not username:
        return False
    
    query = {"$or": []}
    if email:
        query["$or"].append({"email": email.lower()})
    if username:
        query["$or"].append({"username": username.lower()})
    
    existing_admin = await db.admins.find_one(query)
    return existing_admin is not None

async def get_admin_count(db):
    """Get count of active admins"""
    return await db.admins.count_documents({
        "role": ADMIN_ROLE_ADMIN, 
        "status": {"$ne": ADMIN_STATUS_DELETED}
    })

async def get_moderator_count(db):
    """Get count of active moderators"""
    return await db.admins.count_documents({
        "role": ADMIN_ROLE_MODERATOR, 
        "status": {"$ne": ADMIN_STATUS_DELETED}
    })

async def get_all_admins(db, skip=0, limit=50):
    """Get all admins with pagination"""
    cursor = db.admins.find(
        {"status": {"$ne": ADMIN_STATUS_DELETED}},
        {"password": 0}  # Exclude password field
    ).skip(skip).limit(limit).sort("created_at", -1)
    
    return await cursor.to_list(length=limit)

async def search_admins(db, search_term, skip=0, limit=50):
    """Search admins by email, username, or full name"""
    if not search_term:
        return await get_all_admins(db, skip, limit)
    
    search_regex = {"$regex": search_term, "$options": "i"}
    query = {
        "status": {"$ne": ADMIN_STATUS_DELETED},
        "$or": [
            {"email": search_regex},
            {"username": search_regex},
            {"full_name": search_regex}
        ]
    }
    
    cursor = db.admins.find(query, {"password": 0}).skip(skip).limit(limit).sort("created_at", -1)
    return await cursor.to_list(length=limit)
