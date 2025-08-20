import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from app.main import app
from app.database.mongo_connection import get_database
from app.models.user import get_user_by_email
import time

# Pytest configuration for async tests
pytest_plugins = ('pytest_asyncio',)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture
async def async_client():
    """Create an async test client for the FastAPI app."""
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def test_db():
    """Get test database connection."""
    return await get_database()

@pytest.fixture
def test_user_data():
    """Sample user data for testing."""
    timestamp = int(time.time())
    return {
        "email": f"testuser_{timestamp}@example.com",
        "username": f"testuser_{timestamp}",
        "password": "TestPassword123!",
        "full_name": "Test User",
        "bio": "Test bio"
    }

@pytest.fixture
def test_user_data_2():
    """Second sample user data for testing."""
    timestamp = int(time.time())
    return {
        "email": f"testuser2_{timestamp}@example.com",
        "username": f"testuser2_{timestamp}",
        "password": "TestPassword456!",
        "full_name": "Test User 2",
        "bio": "Test bio 2"
    }

@pytest.fixture
async def registered_user(async_client, test_user_data, test_db):
    """Create a registered user for testing."""
    response = await async_client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 201
    user_data = response.json()
    
    # Get the OTP from database for testing
    from app.models.otp import get_latest_otp, OTP_TYPE_EMAIL_VERIFICATION
    otp_code = await get_latest_otp(test_db, test_user_data["email"], OTP_TYPE_EMAIL_VERIFICATION)
    
    # Return both registration response and original password
    return {
        "registration_response": user_data,
        "email": test_user_data["email"],
        "password": test_user_data["password"],
        "otp_code": otp_code
    }

@pytest.fixture
async def verified_user(async_client, registered_user):
    """Create a verified user (completed first login) for testing."""
    # Perform first login with OTP to verify email
    login_data = {
        "email": registered_user["email"],
        "password": registered_user["password"],
        "otp_code": registered_user["otp_code"]
    }
    
    response = await async_client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    login_response = response.json()
    
    return {
        **registered_user,
        "login_response": login_response,
        "access_token": login_response["access_token"],
        "refresh_token": login_response["refresh_token"]
    }

@pytest.fixture
def auth_headers(verified_user):
    """Create authorization headers for authenticated requests."""
    return {"Authorization": f"Bearer {verified_user['access_token']}"}
