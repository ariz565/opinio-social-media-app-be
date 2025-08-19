import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
import logging
from typing import Optional
from app.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

class MongoDB:
    """MongoDB connection manager"""
    client: Optional[AsyncIOMotorClient] = None
    database = None

# MongoDB connection instance
mongodb = MongoDB()

async def connect_to_mongo():
    """Create database connection"""
    try:
        settings = get_settings()
        
        # MongoDB connection string - use environment variable or default
        MONGO_URL = settings.get("MONGODB_URI", "mongodb://localhost:27017")
        DATABASE_NAME = settings.get("MONGO_DB_NAME", "gulf-return")
        
        # Create AsyncIOMotorClient
        mongodb.client = AsyncIOMotorClient(
            MONGO_URL,
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=5000,
            maxPoolSize=50,
            minPoolSize=10
        )
        
        # Test the connection
        await mongodb.client.admin.command('ping')
        
        # Get database
        mongodb.database = mongodb.client[DATABASE_NAME]
        
        logger.info(f"Successfully connected to MongoDB: {DATABASE_NAME}")
        
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error connecting to MongoDB: {e}")
        raise e

async def close_mongo_connection():
    """Close database connection"""
    if mongodb.client is not None:
        mongodb.client.close()
        logger.info("MongoDB connection closed")

async def get_database():
    """Get database instance"""
    if mongodb.database is None:
        # Try to connect if not already connected
        try:
            await connect_to_mongo()
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise Exception(f"Database not connected: {e}")
    
    if mongodb.database is None:
        raise Exception("Database connection failed")
    
    return mongodb.database

async def get_collection(collection_name: str):
    """Get a specific collection"""
    database = await get_database()
    if database is None:
        raise Exception("Database not connected")
    return database[collection_name]

# Health check function
async def ping_database():
    """Check if database is accessible"""
    try:
        if mongodb.client is not None:
            await mongodb.client.admin.command('ping')
            return True
        return False
    except Exception as e:
        logger.error(f"Database ping failed: {e}")
        return False

# For backward compatibility with existing code
class MongoConnectionManager:
    """Backward compatibility wrapper"""
    
    async def connect(self):
        await connect_to_mongo()
    
    async def disconnect(self):
        await close_mongo_connection()
    
    async def get_database(self):
        return await get_database()
    
    async def get_collection(self, collection_name: str):
        return await get_collection(collection_name)
    
    async def health_check(self):
        """Database health check"""
        try:
            if await ping_database():
                return {
                    "status": "healthy",
                    "database_name": mongodb.database.name if mongodb.database is not None else "unknown"
                }
            else:
                return {"status": "unhealthy", "error": "Database ping failed"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}