"""
Test suite for the interaction system
Tests all interaction features: reactions, comments, bookmarks, follows, shares
"""

import pytest
import asyncio
from httpx import AsyncClient
from app.main import app
from app.database.mongo_connection import get_database
from app.core.auth import create_access_token
from bson import ObjectId
import json

# Test data
TEST_USER_1 = {
    "email": "testuser1@example.com",
    "username": "testuser1",
    "full_name": "Test User 1"
}

TEST_USER_2 = {
    "email": "testuser2@example.com", 
    "username": "testuser2",
    "full_name": "Test User 2"
}

TEST_POST = {
    "content": "This is a test post for interaction testing",
    "visibility": "public"
}

@pytest.fixture
async def test_client():
    """Create test client"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
async def test_db():
    """Get test database"""
    db = await get_database()
    yield db
    # Cleanup after tests
    await cleanup_test_data(db)

@pytest.fixture
async def test_users(test_db):
    """Create test users"""
    # Insert test users
    user1_id = await test_db.users.insert_one({
        **TEST_USER_1,
        "_id": ObjectId(),
        "is_active": True,
        "is_private": False
    })
    
    user2_id = await test_db.users.insert_one({
        **TEST_USER_2,
        "_id": ObjectId(),
        "is_active": True,
        "is_private": False
    })
    
    return {
        "user1": str(user1_id.inserted_id),
        "user2": str(user2_id.inserted_id)
    }

@pytest.fixture
async def test_tokens(test_users):
    """Create test tokens"""
    return {
        "user1": create_access_token(data={"sub": test_users["user1"]}),
        "user2": create_access_token(data={"sub": test_users["user2"]})
    }

@pytest.fixture
async def test_post(test_db, test_users):
    """Create test post"""
    post_data = {
        **TEST_POST,
        "_id": ObjectId(),
        "user_id": ObjectId(test_users["user1"]),
        "reactions": {"total": 0, "like": 0, "love": 0, "laugh": 0, "wow": 0, "sad": 0, "angry": 0, "care": 0},
        "comment_count": 0,
        "share_count": 0,
        "bookmark_count": 0
    }
    
    result = await test_db.posts.insert_one(post_data)
    return str(result.inserted_id)

async def cleanup_test_data(db):
    """Clean up test data"""
    await db.users.delete_many({"email": {"$in": [TEST_USER_1["email"], TEST_USER_2["email"]]}})
    await db.posts.delete_many({"content": TEST_POST["content"]})
    await db.reactions.delete_many({})
    await db.comments.delete_many({})
    await db.bookmarks.delete_many({})
    await db.bookmark_collections.delete_many({})
    await db.follows.delete_many({})
    await db.user_connections.delete_many({})
    await db.shares.delete_many({})

class TestReactionSystem:
    """Test reaction system functionality"""
    
    async def test_add_reaction(self, test_client, test_tokens, test_post):
        """Test adding a reaction to a post"""
        headers = {"Authorization": f"Bearer {test_tokens['user1']}"}
        
        response = await test_client.post(
            f"/api/v1/reactions/posts/{test_post}/like",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Reaction added successfully"
        assert data["reaction_type"] == "like"
    
    async def test_toggle_reaction(self, test_client, test_tokens, test_post):
        """Test toggling a reaction"""
        headers = {"Authorization": f"Bearer {test_tokens['user1']}"}
        
        # Add reaction
        await test_client.post(f"/api/v1/reactions/posts/{test_post}/love", headers=headers)
        
        # Toggle (remove) reaction
        response = await test_client.post(f"/api/v1/reactions/posts/{test_post}/love", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "removed"
    
    async def test_get_reactions(self, test_client, test_tokens, test_post):
        """Test getting reactions for a post"""
        headers = {"Authorization": f"Bearer {test_tokens['user1']}"}
        
        # Add some reactions
        await test_client.post(f"/api/v1/reactions/posts/{test_post}/like", headers=headers)
        
        response = await test_client.get(f"/api/v1/reactions/posts/{test_post}")
        
        assert response.status_code == 200
        data = response.json()
        assert "reactions" in data
        assert data["reactions"]["total"] >= 1

class TestCommentSystem:
    """Test comment system functionality"""
    
    async def test_create_comment(self, test_client, test_tokens, test_post):
        """Test creating a comment"""
        headers = {"Authorization": f"Bearer {test_tokens['user1']}"}
        
        comment_data = {
            "content": "This is a test comment",
            "mentions": []
        }
        
        response = await test_client.post(
            f"/api/v1/comments/posts/{test_post}",
            json=comment_data,
            headers=headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == comment_data["content"]
        assert data["depth"] == 0
        return data["id"]
    
    async def test_reply_to_comment(self, test_client, test_tokens, test_post):
        """Test replying to a comment"""
        headers = {"Authorization": f"Bearer {test_tokens['user1']}"}
        
        # Create parent comment
        parent_comment_id = await self.test_create_comment(test_client, test_tokens, test_post)
        
        reply_data = {
            "content": "This is a reply to the comment",
            "mentions": []
        }
        
        response = await test_client.post(
            f"/api/v1/comments/{parent_comment_id}/reply",
            json=reply_data,
            headers=headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == reply_data["content"]
        assert data["depth"] == 1
        assert data["parent_comment_id"] == parent_comment_id
    
    async def test_get_post_comments(self, test_client, test_tokens, test_post):
        """Test getting comments for a post"""
        # Create a comment first
        await self.test_create_comment(test_client, test_tokens, test_post)
        
        response = await test_client.get(f"/api/v1/comments/posts/{test_post}")
        
        assert response.status_code == 200
        data = response.json()
        assert "comments" in data
        assert len(data["comments"]) >= 1

class TestBookmarkSystem:
    """Test bookmark system functionality"""
    
    async def test_bookmark_post(self, test_client, test_tokens, test_post):
        """Test bookmarking a post"""
        headers = {"Authorization": f"Bearer {test_tokens['user1']}"}
        
        response = await test_client.post(
            f"/api/v1/bookmarks/posts/{test_post}",
            headers=headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["post_id"] == test_post
    
    async def test_create_bookmark_collection(self, test_client, test_tokens):
        """Test creating a bookmark collection"""
        headers = {"Authorization": f"Bearer {test_tokens['user1']}"}
        
        collection_data = {
            "name": "Test Collection",
            "description": "A test bookmark collection",
            "is_private": False
        }
        
        response = await test_client.post(
            "/api/v1/bookmarks/collections",
            json=collection_data,
            headers=headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == collection_data["name"]
        return data["id"]
    
    async def test_get_user_bookmarks(self, test_client, test_tokens, test_post):
        """Test getting user bookmarks"""
        headers = {"Authorization": f"Bearer {test_tokens['user1']}"}
        
        # Bookmark a post first
        await self.test_bookmark_post(test_client, test_tokens, test_post)
        
        response = await test_client.get("/api/v1/bookmarks", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "bookmarks" in data
        assert len(data["bookmarks"]) >= 1

class TestFollowSystem:
    """Test follow system functionality"""
    
    async def test_follow_user(self, test_client, test_tokens, test_users):
        """Test following a user"""
        headers = {"Authorization": f"Bearer {test_tokens['user1']}"}
        
        response = await test_client.post(
            f"/api/v1/follows/users/{test_users['user2']}/follow",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "User followed successfully"
    
    async def test_unfollow_user(self, test_client, test_tokens, test_users):
        """Test unfollowing a user"""
        headers = {"Authorization": f"Bearer {test_tokens['user1']}"}
        
        # Follow first
        await self.test_follow_user(test_client, test_tokens, test_users)
        
        # Then unfollow
        response = await test_client.delete(
            f"/api/v1/follows/users/{test_users['user2']}/unfollow",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "User unfollowed successfully"
    
    async def test_get_followers(self, test_client, test_tokens, test_users):
        """Test getting user followers"""
        headers = {"Authorization": f"Bearer {test_tokens['user2']}"}
        
        # Have user1 follow user2
        await self.test_follow_user(test_client, test_tokens, test_users)
        
        response = await test_client.get(
            f"/api/v1/follows/users/{test_users['user2']}/followers",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "followers" in data

class TestShareSystem:
    """Test share system functionality"""
    
    async def test_share_post(self, test_client, test_tokens, test_post):
        """Test sharing a post"""
        headers = {"Authorization": f"Bearer {test_tokens['user1']}"}
        
        share_data = {
            "share_type": "repost",
            "comment": "Check this out!"
        }
        
        response = await test_client.post(
            f"/api/v1/shares/posts/{test_post}",
            json=share_data,
            headers=headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["share_type"] == share_data["share_type"]
        assert data["comment"] == share_data["comment"]
    
    async def test_get_post_shares(self, test_client, test_tokens, test_post):
        """Test getting shares for a post"""
        # Share the post first
        await self.test_share_post(test_client, test_tokens, test_post)
        
        response = await test_client.get(f"/api/v1/shares/posts/{test_post}")
        
        assert response.status_code == 200
        data = response.json()
        assert "shares" in data
        assert len(data["shares"]) >= 1

# Run the tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
