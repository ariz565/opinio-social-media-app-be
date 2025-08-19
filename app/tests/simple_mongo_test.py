import os
import sys
import asyncio

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.mongo_connection import MongoDB
from config import get_settings

async def test_mongodb_connection():
    """Simple MongoDB connection test"""
    print("🚀 Starting MongoDB Connection Test...\n")
    
    mongo_db = MongoDB()
    
    try:
        # Test 1: Basic Connection
        print("Test 1: Basic Connection")
        await mongo_db.connect()
        print(f"✅ Connected to: {mongo_db.database.name}\n")
        
        # Test 2: Ping
        print("Test 2: Ping Test")
        result = await mongo_db.client.admin.command('ping')
        print(f"✅ Ping result: {result}\n")
        
        # Test 3: Health Check
        print("Test 3: Health Check")
        health = await mongo_db.health_check()
        print(f"✅ Health status: {health['status']}")
        print(f"   MongoDB Version: {health.get('mongodb_version', 'Unknown')}")
        print(f"   Database: {health.get('database_name', 'Unknown')}\n")
        
        # Test 4: Collection Test
        print("Test 4: Collection Operations")
        test_collection = await mongo_db.get_collection("test_connection")
        
        # Insert test document
        test_doc = {"test": True, "message": "MongoDB connection test", "timestamp": "2025-08-20"}
        result = await test_collection.insert_one(test_doc)
        print(f"✅ Document inserted with ID: {result.inserted_id}")
        
        # Find document
        found = await test_collection.find_one({"test": True})
        print(f"✅ Document found: {found['message']}")
        
        # Count documents in collection
        count = await test_collection.count_documents({})
        print(f"✅ Total documents in test collection: {count}")
        
        # Clean up
        await test_collection.delete_one({"_id": result.inserted_id})
        print("✅ Test document cleaned up\n")
        
        # Test 5: User collection check
        print("Test 5: User Collection Check")
        users_collection = await mongo_db.get_collection("users")
        user_count = await users_collection.count_documents({})
        print(f"✅ Users collection exists with {user_count} documents\n")
        
        print("🎉 All MongoDB tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await mongo_db.disconnect()
        print("✅ Disconnected from MongoDB")

if __name__ == "__main__":
    # Run the test
    success = asyncio.run(test_mongodb_connection())
    if success:
        print("\n✅ MongoDB is ready for the application!")
    else:
        print("\n❌ MongoDB connection issues detected!")
        sys.exit(1)
