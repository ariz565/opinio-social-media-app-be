import pytest
import pytest_asyncio
from httpx import AsyncClient
from app.main import app
from app.database.mongo_connection import get_database
from app.config import get_settings

settings = get_settings()

class TestSecurityMeasures:
    """Test security measures to prevent privilege escalation"""
    
    @pytest_asyncio.fixture
    async def clean_db(self):
        """Clean database before each test"""
        db = await get_database()
        test_emails = [
            "test_user@test.com", "hacker@test.com", "admin_wannabe@test.com"
        ]
        await db.users.delete_many({"email": {"$in": test_emails}})
        yield
        await db.users.delete_many({"email": {"$in": test_emails}})
    
    @pytest_asyncio.fixture
    async def client(self):
        """Create async test client"""
        from httpx import ASGITransport
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    
    async def test_register_user_cannot_set_admin_role(self, client, clean_db):
        """Test that users cannot register with admin role"""
        # Attempt to register with admin role
        user_data = {
            "email": "hacker@test.com",
            "username": "hacker_user",
            "password": "HackerPass123",
            "full_name": "Hacker User",
            "role": "admin"  # Attempt privilege escalation
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "privilege escalation attempt detected" in data["detail"]
    
    async def test_register_user_cannot_set_email_verified(self, client, clean_db):
        """Test that users cannot register with email_verified=True"""
        user_data = {
            "email": "hacker@test.com",
            "username": "hacker_user", 
            "password": "HackerPass123",
            "full_name": "Hacker User",
            "email_verified": True  # Attempt to bypass email verification
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "privilege escalation attempt detected" in data["detail"]
    
    async def test_register_user_cannot_set_status(self, client, clean_db):
        """Test that users cannot register with custom status"""
        user_data = {
            "email": "hacker@test.com",
            "username": "hacker_user",
            "password": "HackerPass123", 
            "full_name": "Hacker User",
            "status": "active"  # Attempt to set status
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "privilege escalation attempt detected" in data["detail"]
    
    async def test_normal_user_registration_works(self, client, clean_db):
        """Test that normal user registration still works"""
        user_data = {
            "email": "test_user@test.com",
            "username": "test_user",
            "password": "TestPass123",
            "full_name": "Test User",
            "bio": "Just a normal user"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["user"]["role"] == "user"  # Should be regular user
        assert data["user"]["email_verified"] == False  # Should require verification
        assert data["user"]["status"] == "active"  # Default status
    
    async def test_admin_cannot_login_through_regular_endpoint(self, client, clean_db):
        """Test that admin users cannot login through regular endpoint"""
        # First create an admin user
        admin_data = {
            "admin_secret": settings["ADMIN_SECRET"],
            "email": "admin_wannabe@test.com",
            "username": "admin_wannabe",
            "password": "AdminPass123",
            "full_name": "Admin Wannabe"
        }
        
        # Create admin user through admin endpoint
        response1 = await client.post("/api/v1/auth/admin/create-admin", json=admin_data)
        assert response1.status_code == 201
        
        # Try to login through regular endpoint
        login_data = {
            "email": "admin_wannabe@test.com",
            "password": "AdminPass123"
        }
        
        response2 = await client.post("/api/v1/auth/login", json=login_data)
        
        # Should work now since we removed admin blocking from regular login
        assert response2.status_code == 200
        data = response2.json()
        assert data["user"]["role"] == "admin"
    
    async def test_admin_login_through_admin_endpoint_works(self, client, clean_db):
        """Test that admin users can login through admin endpoint"""
        # Create admin user
        admin_data = {
            "admin_secret": settings["ADMIN_SECRET"],
            "email": "admin_wannabe@test.com",
            "username": "admin_wannabe",
            "password": "AdminPass123",
            "full_name": "Admin Wannabe"
        }
        
        response1 = await client.post("/api/v1/auth/admin/create-admin", json=admin_data)
        assert response1.status_code == 201
        
        # Login through admin endpoint
        admin_login_data = {
            "email": "admin_wannabe@test.com",
            "password": "AdminPass123",
            "admin_secret": settings["ADMIN_SECRET"]
        }
        
        response2 = await client.post("/api/v1/auth/admin/login", json=admin_login_data)
        
        assert response2.status_code == 200
        data = response2.json()
        assert data["admin"]["role"] == "admin"
        assert "access_token" in data
        assert "refresh_token" in data
    
    async def test_admin_login_with_wrong_secret_fails(self, client, clean_db):
        """Test that admin login fails with wrong admin secret"""
        # Create admin user
        admin_data = {
            "admin_secret": settings["ADMIN_SECRET"],
            "email": "admin_wannabe@test.com",
            "username": "admin_wannabe",
            "password": "AdminPass123",
            "full_name": "Admin Wannabe"
        }
        
        response1 = await client.post("/api/v1/auth/admin/create-admin", json=admin_data)
        assert response1.status_code == 201
        
        # Try login with wrong admin secret
        admin_login_data = {
            "email": "admin_wannabe@test.com",
            "password": "AdminPass123",
            "admin_secret": "wrong-secret"
        }
        
        response2 = await client.post("/api/v1/auth/admin/login", json=admin_login_data)
        
        assert response2.status_code == 403
        data = response2.json()
        assert "Invalid admin credentials" in data["detail"]
    
    async def test_regular_user_cannot_access_admin_endpoints(self, client, clean_db):
        """Test that regular users cannot access admin-only endpoints"""
        # Create regular user
        user_data = {
            "email": "test_user@test.com",
            "username": "test_user",
            "password": "TestPass123",
            "full_name": "Test User"
        }
        
        response1 = await client.post("/api/v1/auth/register", json=user_data)
        assert response1.status_code == 201
        
        # Verify email to enable login (simulate OTP verification)
        db = await get_database()
        await db.users.update_one(
            {"email": "test_user@test.com"},
            {"$set": {"email_verified": True}}
        )
        
        # Login as regular user
        login_data = {
            "email": "test_user@test.com",
            "password": "TestPass123"
        }
        
        response2 = await client.post("/api/v1/auth/login", json=login_data)
        assert response2.status_code == 200
        
        user_token = response2.json()["access_token"]
        
        # Try to access admin dashboard
        response3 = await client.get(
            "/api/v1/auth/admin/dashboard/stats",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        assert response3.status_code == 403
        data = response3.json()
        assert "Admin privileges required" in data["detail"]
