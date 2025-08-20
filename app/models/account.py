from datetime import datetime
from bson import ObjectId
from typing import Optional

# Account provider constants
PROVIDER_GOOGLE = "google"
PROVIDER_FACEBOOK = "facebook"
PROVIDER_GITHUB = "github"
PROVIDER_EMAIL = "email"

# Account status constants
ACCOUNT_STATUS_ACTIVE = "active"
ACCOUNT_STATUS_INACTIVE = "inactive"
ACCOUNT_STATUS_SUSPENDED = "suspended"
ACCOUNT_STATUS_DELETED = "deleted"

async def get_account_by_provider_id(db, provider, provider_id):
    """Get account by provider and provider ID (e.g., Google ID)"""
    if not provider or not provider_id:
        return None
    return await db.accounts.find_one({
        "provider": provider,
        "provider_id": str(provider_id)
    })

async def get_account_by_email(db, email):
    """Get account by email"""
    if not email:
        return None
    return await db.accounts.find_one({"email": email.lower()})

async def get_account_by_id(db, account_id):
    """Get account by id"""
    if not account_id:
        return None
    
    try:
        if isinstance(account_id, str):
            if not ObjectId.is_valid(account_id):
                return None
            account_id = ObjectId(account_id)
        return await db.accounts.find_one({"_id": account_id})
    except Exception:
        return None

async def create_account(db, account_data):
    """Create a new OAuth account"""
    current_time = datetime.utcnow()
    
    # Prepare account document
    account_doc = {
        "email": account_data["email"].lower(),
        "full_name": account_data["full_name"],
        "provider": account_data["provider"],
        "provider_id": str(account_data["provider_id"]),
        "profile_picture": account_data.get("profile_picture"),
        "status": ACCOUNT_STATUS_ACTIVE,
        "email_verified": account_data.get("email_verified", True),  # OAuth providers usually verify email
        "created_at": current_time,
        "updated_at": current_time,
        "last_login": current_time,
        
        # Provider-specific data
        "provider_data": account_data.get("provider_data", {}),
        
        # Linked user account (if any)
        "linked_user_id": account_data.get("linked_user_id"),
        
        # Permissions and preferences
        "permissions": account_data.get("permissions", []),
        "preferences": account_data.get("preferences", {})
    }
    
    # Insert account
    result = await db.accounts.insert_one(account_doc)
    
    # Return created account
    return await get_account_by_id(db, result.inserted_id)

async def update_account(db, account_id, update_data):
    """Update account information"""
    if not account_id:
        return None
    
    try:
        if isinstance(account_id, str):
            if not ObjectId.is_valid(account_id):
                return None
            account_id = ObjectId(account_id)
    except Exception:
        return None
    
    # Add updated_at timestamp
    update_data["updated_at"] = datetime.utcnow()
    
    # Update account document
    result = await db.accounts.update_one(
        {"_id": account_id},
        {"$set": update_data}
    )
    
    if result.modified_count > 0:
        return await get_account_by_id(db, account_id)
    return None

async def delete_account(db, account_id):
    """Soft delete account (mark as deleted)"""
    if not account_id:
        return False
    
    try:
        if isinstance(account_id, str):
            if not ObjectId.is_valid(account_id):
                return False
            account_id = ObjectId(account_id)
    except Exception:
        return False
    
    # Soft delete by updating status
    result = await db.accounts.update_one(
        {"_id": account_id},
        {"$set": {
            "status": ACCOUNT_STATUS_DELETED,
            "updated_at": datetime.utcnow()
        }}
    )
    
    return result.modified_count > 0

async def update_account_last_login(db, account_id):
    """Update account last login timestamp"""
    if not account_id:
        return False
    
    try:
        if isinstance(account_id, str):
            if not ObjectId.is_valid(account_id):
                return False
            account_id = ObjectId(account_id)
    except Exception:
        return False
    
    # Update last login
    result = await db.accounts.update_one(
        {"_id": account_id},
        {"$set": {
            "last_login": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }}
    )
    
    return result.modified_count > 0

async def link_account_to_user(db, account_id, user_id):
    """Link an OAuth account to a regular user account"""
    if not account_id or not user_id:
        return False
    
    try:
        if isinstance(account_id, str):
            if not ObjectId.is_valid(account_id):
                return False
            account_id = ObjectId(account_id)
        
        if isinstance(user_id, str):
            if not ObjectId.is_valid(user_id):
                return False
            user_id = ObjectId(user_id)
    except Exception:
        return False
    
    # Link the account to user
    result = await db.accounts.update_one(
        {"_id": account_id},
        {"$set": {
            "linked_user_id": user_id,
            "updated_at": datetime.utcnow()
        }}
    )
    
    return result.modified_count > 0

async def get_accounts_by_user(db, user_id):
    """Get all OAuth accounts linked to a user"""
    if not user_id:
        return []
    
    try:
        if isinstance(user_id, str):
            if not ObjectId.is_valid(user_id):
                return []
            user_id = ObjectId(user_id)
    except Exception:
        return []
    
    cursor = db.accounts.find({
        "linked_user_id": user_id,
        "status": {"$ne": ACCOUNT_STATUS_DELETED}
    }).sort("created_at", -1)
    
    return await cursor.to_list(length=None)

async def check_account_exists(db, provider, provider_id):
    """Check if account exists by provider and provider ID"""
    if not provider or not provider_id:
        return False
    
    existing_account = await db.accounts.find_one({
        "provider": provider,
        "provider_id": str(provider_id),
        "status": {"$ne": ACCOUNT_STATUS_DELETED}
    })
    return existing_account is not None

async def get_account_count_by_provider(db, provider):
    """Get count of accounts by provider"""
    return await db.accounts.count_documents({
        "provider": provider,
        "status": {"$ne": ACCOUNT_STATUS_DELETED}
    })

async def get_all_accounts(db, skip=0, limit=50):
    """Get all accounts with pagination"""
    cursor = db.accounts.find(
        {"status": {"$ne": ACCOUNT_STATUS_DELETED}}
    ).skip(skip).limit(limit).sort("created_at", -1)
    
    return await cursor.to_list(length=limit)

async def search_accounts(db, search_term, skip=0, limit=50):
    """Search accounts by email or full name"""
    if not search_term:
        return await get_all_accounts(db, skip, limit)
    
    search_regex = {"$regex": search_term, "$options": "i"}
    query = {
        "status": {"$ne": ACCOUNT_STATUS_DELETED},
        "$or": [
            {"email": search_regex},
            {"full_name": search_regex}
        ]
    }
    
    cursor = db.accounts.find(query).skip(skip).limit(limit).sort("created_at", -1)
    return await cursor.to_list(length=limit)
