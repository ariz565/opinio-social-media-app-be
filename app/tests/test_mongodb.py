import pytest
import asyncio
from app.database.mongo_connection import MongoDB
from app.config import get_settings

class TestMongoDBConnection:
    """Test cases for MongoDB connection"""
    
    @pytest.fixture
    async def mongo_db(self):
        """Create MongoDB instance for testing"""
        db = MongoDB()
        yield db
        # Cleanup after test
        await db.disconnect()
    
    @pytest.mark.asyncio
    async def test_mongodb_connection(self, mongo_db):
        """Test basic MongoDB connection"""
        # Test connection
        await mongo_db.connect()
        
        # Verify client and database are created
        assert mongo_db.client is not None
        assert mongo_db.database is not None
        
        # Test database name
        settings = get_settings()
        expected_db_name = settings.get("MONGO_DB_NAME", "gulf-return")
        assert mongo_db.database.name == expected_db_name
        
        print(f"✅ Connected to MongoDB database: {mongo_db.database.name}")
    
    @pytest.mark.asyncio
    async def test_mongodb_ping(self, mongo_db):
        """Test MongoDB ping command"""
        await mongo_db.connect()
        
        # Test ping command directly
        result = await mongo_db.client.admin.command('ping')
        assert result['ok'] == 1
        
        print("✅ MongoDB ping successful")
    
    @pytest.mark.asyncio
    async def test_get_database(self, mongo_db):
        """Test get_database method"""
        database = await mongo_db.get_database()
        
        assert database is not None
        assert database.name == get_settings().get("MONGO_DB_NAME", "gulf-return")
        
        print(f"✅ Database retrieved: {database.name}")
    
    @pytest.mark.asyncio
    async def test_get_collection(self, mongo_db):
        """Test get_collection method"""
        await mongo_db.connect()
        
        # Test getting a collection
        users_collection = await mongo_db.get_collection("users")
        assert users_collection is not None
        assert users_collection.name == "users"
        
        print("✅ Collection retrieved successfully")
    
    @pytest.mark.asyncio
    async def test_health_check(self, mongo_db):
        """Test database health check"""
        await mongo_db.connect()
        
        health_status = await mongo_db.health_check()
        
        assert health_status["status"] == "healthy"
        assert "mongodb_version" in health_status
        assert "database_name" in health_status
        
        print(f"✅ Health check passed: {health_status}")
    
    @pytest.mark.asyncio
    async def test_collection_operations(self, mongo_db):
        """Test basic collection operations"""
        await mongo_db.connect()
        
        # Get test collection
        test_collection = await mongo_db.get_collection("test_collection")
        
        # Insert a test document
        test_doc = {"name": "test", "value": 123}
        result = await test_collection.insert_one(test_doc)
        assert result.inserted_id is not None
        
        # Find the document
        found_doc = await test_collection.find_one({"name": "test"})
        assert found_doc is not None
        assert found_doc["value"] == 123
        
        # Clean up - delete the test document
        await test_collection.delete_one({"_id": result.inserted_id})
        
        print("✅ Basic collection operations successful")
    
    @pytest.mark.asyncio
    async def test_disconnect(self, mongo_db):
        """Test MongoDB disconnection"""
        await mongo_db.connect()
        assert mongo_db.client is not None
        
        await mongo_db.disconnect()
        assert mongo_db.client is None
        assert mongo_db.database is None
        
        print("✅ MongoDB disconnection successful")

# Function to run tests manually
async def run_manual_tests():
    """Run tests manually without pytest"""
    print("🚀 Starting MongoDB Connection Tests...\n")
    
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
        print(f"✅ Health status: {health}\n")
        
        # Test 4: Collection Test
        print("Test 4: Collection Operations")
        test_collection = await mongo_db.get_collection("test_connection")
        
        # Insert test document
        test_doc = {"test": True, "timestamp": "2025-08-20"}
        result = await test_collection.insert_one(test_doc)
        print(f"✅ Document inserted with ID: {result.inserted_id}")
        
        # Find and display document
        found = await test_collection.find_one({"test": True})
        print(f"✅ Document found: {found}")
        
        # Clean up
        await test_collection.delete_one({"_id": result.inserted_id})
        print("✅ Test document cleaned up\n")
        
        print("🎉 All tests passed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        await mongo_db.disconnect()
        print("✅ Disconnected from MongoDB")

if __name__ == "__main__":
    # Run manual tests
    asyncio.run(run_manual_tests())
