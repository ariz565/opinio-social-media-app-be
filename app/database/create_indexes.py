import asyncio
import logging
from pymongo import IndexModel, ASCENDING

from app.database.mongo_connection import get_database

logger = logging.getLogger(__name__)

async def create_indexes():
    """Create database indexes"""
    db = await get_database()
    
    # User collection indexes
    user_indexes = [
        IndexModel([("email", ASCENDING)], unique=True),
        IndexModel([("username", ASCENDING)], unique=True),
        IndexModel([("google_id", ASCENDING)], sparse=True),
        IndexModel([("status", ASCENDING)]),
        IndexModel([("auth_provider", ASCENDING)]),
        IndexModel([("created_at", ASCENDING)])
    ]
    
    try:
        await db.users.create_indexes(user_indexes)
        logger.info("User indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating user indexes: {e}")
    
    # OTP collection indexes
    otp_indexes = [
        IndexModel([("email", ASCENDING)]),
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("otp_type", ASCENDING)]),
        IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0),  # TTL index for auto cleanup
        IndexModel([("email", ASCENDING), ("otp_type", ASCENDING)])
    ]
    
    try:
        await db.otps.create_indexes(otp_indexes)
        logger.info("OTP indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating OTP indexes: {e}")

if __name__ == "__main__":
    asyncio.run(create_indexes())
