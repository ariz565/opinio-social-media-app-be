import pytest
import pytest_asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
import asyncio
import os
from app.main import app
from app.database.mongo_connection import get_database
from app.config import get_settings

settings = get_settings()

class TestAdminUserCreation:
    """Test cases for admin user creation endpoint"""
    
    @pytest_asyncio.fixture
    async def clean_db(self):
        """Clean database before each test"""
        db = await get_database()
        # Clean up specific test emails and any admin users
        test_emails = [
            "admin@test.com", "admin2@test.com", "admin3@test.com", "admin4@test.com",
            "admin5@test.com", "admin6@test.com", "admin7@test.com", "admin8@test.com",
            "admin9@test.com", "admin10@test.com", "admin11@test.com", "debug_admin@test.com"
        ]
        test_usernames = [
            "admin_user", "admin_user2", "admin_user3", "admin_user4", "admin_user5",
            "admin_user6", "admin_user7", "admin_user8", "admin_user9", "admin_user10", 
            "admin_user11", "debug_admin"
        ]
        
        # Delete test users by email or username
        await db.users.delete_many({
            "$or": [
                {"email": {"$in": test_emails}},
                {"username": {"$in": test_usernames}}
            ]
        })
        
        yield
        
        # Cleanup after test
        await db.users.delete_many({
            "$or": [
                {"email": {"$in": test_emails}},
                {"username": {"$in": test_usernames}}
            ]
        })
    
    @pytest_asyncio.fixture
    async def client(self):
        """Create async test client"""
        from httpx import ASGITransport
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    
    async def test_create_admin_user_success(self, client, clean_db):
        """Test successful admin user creation with valid admin secret"""
        admin_data = {
            "admin_secret": settings["ADMIN_SECRET"],
            "email": "admin@test.com",
            "username": "admin_user",
            "password": "AdminPass123",
            "full_name": "Admin User",
            "bio": "System Administrator"
        }
        
        response = await client.post("/api/v1/auth/create-admin", json=admin_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "message" in data
        assert "user" in data
        assert "Admin user created successfully" in data["message"]
        
        user = data["user"]
        assert user["email"] == "admin@test.com"
        assert user["username"] == "admin_user"
        assert user["full_name"] == "Admin User"
        assert user["role"] == "admin"
        assert user["email_verified"] == True
        assert "password" not in user
    
    async def test_create_admin_user_invalid_secret(self, client, clean_db):
        """Test admin user creation with invalid admin secret"""
        admin_data = {
            "admin_secret": "wrong-secret-key",
            "email": "admin2@test.com",
            "username": "admin_user2",
            "password": "AdminPass123",
            "full_name": "Admin User 2"
        }
        
        response = await client.post("/api/v1/auth/create-admin", json=admin_data)
        
        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "Invalid admin secret key"
    
    async def test_create_admin_user_duplicate_email(self, client, clean_db):
        """Test admin user creation with duplicate email"""
        # First, create an admin user
        admin_data = {
            "admin_secret": settings["ADMIN_SECRET"],
            "email": "admin3@test.com",
            "username": "admin_user3",
            "password": "AdminPass123",
            "full_name": "Admin User Three"
        }
        
        response1 = await client.post("/api/v1/auth/create-admin", json=admin_data)
        assert response1.status_code == 201
        
        # Try to create another admin with same email
        admin_data2 = {
            "admin_secret": settings["ADMIN_SECRET"],
            "email": "admin3@test.com",  # Same email
            "username": "admin_user3_new",
            "password": "AdminPass123",
            "full_name": "Admin User Three New"
        }
        
        response2 = await client.post("/api/v1/auth/create-admin", json=admin_data2)
        assert response2.status_code == 409
        data = response2.json()
        assert "already exists" in data["detail"]
    
    async def test_create_admin_user_duplicate_username(self, client, clean_db):
        """Test admin user creation with duplicate username"""
        # First, create an admin user
        admin_data = {
            "admin_secret": settings["ADMIN_SECRET"],
            "email": "admin4@test.com",
            "username": "admin_user4",
            "password": "AdminPass123",
            "full_name": "Admin User Four"
        }
        
        response1 = await client.post("/api/v1/auth/create-admin", json=admin_data)
        assert response1.status_code == 201
        
        # Try to create another admin with same username
        admin_data2 = {
            "admin_secret": settings["ADMIN_SECRET"],
            "email": "admin4_new@test.com",
            "username": "admin_user4",  # Same username
            "password": "AdminPass123",
            "full_name": "Admin User Four New"
        }
        
        response2 = await client.post("/api/v1/auth/create-admin", json=admin_data2)
        assert response2.status_code == 409
        data = response2.json()
        assert "already exists" in data["detail"]
    
    async def test_create_admin_user_invalid_email(self, client, clean_db):
        """Test admin user creation with invalid email format"""
        admin_data = {
            "admin_secret": settings["ADMIN_SECRET"],
            "email": "invalid-email",
            "username": "admin_user5",
            "password": "AdminPass123",
            "full_name": "Admin User Five"
        }
        
        response = await client.post("/api/v1/auth/create-admin", json=admin_data)
        assert response.status_code == 422  # Validation error
    
    async def test_create_admin_user_weak_password(self, client, clean_db):
        """Test admin user creation with weak password"""
        admin_data = {
            "admin_secret": settings["ADMIN_SECRET"],
            "email": "admin6@test.com",
            "username": "admin_user6",
            "password": "weak",
            "full_name": "Admin User Six"
        }
        
        response = await client.post("/api/v1/auth/create-admin", json=admin_data)
        assert response.status_code == 422  # Validation error
    
    async def test_create_admin_user_invalid_username(self, client, clean_db):
        """Test admin user creation with invalid username"""
        admin_data = {
            "admin_secret": settings["ADMIN_SECRET"],
            "email": "admin7@test.com",
            "username": "ab",  # Too short
            "password": "AdminPass123",
            "full_name": "Admin User Seven"
        }
        
        response = await client.post("/api/v1/auth/create-admin", json=admin_data)
        assert response.status_code == 422  # Validation error
    
    async def test_create_admin_user_missing_required_fields(self, client, clean_db):
        """Test admin user creation with missing required fields"""
        admin_data = {
            "admin_secret": settings["ADMIN_SECRET"],
            "email": "admin8@test.com",
            # Missing username, password, full_name
        }
        
        response = await client.post("/api/v1/auth/create-admin", json=admin_data)
        assert response.status_code == 422  # Validation error
    
    async def test_create_admin_user_no_admin_secret(self, client, clean_db):
        """Test admin user creation without admin secret"""
        admin_data = {
            "email": "admin9@test.com",
            "username": "admin_user9",
            "password": "AdminPass123",
            "full_name": "Admin User Nine"
        }
        
        response = await client.post("/api/v1/auth/create-admin", json=admin_data)
        assert response.status_code == 422  # Validation error
    
    async def test_create_multiple_admin_users(self, client, clean_db):
        """Test creating multiple admin users"""
        # Create first admin
        admin_data1 = {
            "admin_secret": settings["ADMIN_SECRET"],
            "email": "admin10@test.com",
            "username": "admin_user10",
            "password": "AdminPass123",
            "full_name": "Admin User Ten"
        }
        
        response1 = await client.post("/api/v1/auth/create-admin", json=admin_data1)
        assert response1.status_code == 201
        
        # Create second admin
        admin_data2 = {
            "admin_secret": settings["ADMIN_SECRET"],
            "email": "admin11@test.com",
            "username": "admin_user11",
            "password": "AdminPass123",
            "full_name": "Admin User Eleven"
        }
        
        response2 = await client.post("/api/v1/auth/create-admin", json=admin_data2)
        assert response2.status_code == 201
        
        # Verify both admins were created
        data1 = response1.json()
        data2 = response2.json()
        
        assert "Total admin users: 1" in data1["message"]
        assert "Total admin users: 2" in data2["message"]
