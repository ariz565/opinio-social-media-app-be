"""
Database indexes for interaction system collections
This script creates all necessary indexes for optimal performance
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.mongo_connection import get_database
import asyncio

async def create_interaction_indexes():
    """Create all indexes for interaction system collections"""
    db = await get_database()
    
    print("Creating indexes for interaction system collections...")
    
    # Reactions Collection Indexes
    print("Creating reactions indexes...")
    
    # Compound index for user reactions on targets
    await db.reactions.create_index([
        ("user_id", 1),
        ("target_id", 1),
        ("target_type", 1)
    ], unique=True, name="user_target_unique")
    
    # Index for getting reactions by target
    await db.reactions.create_index([
        ("target_id", 1),
        ("target_type", 1),
        ("created_at", -1)
    ], name="target_reactions")
    
    # Index for user's reactions
    await db.reactions.create_index([
        ("user_id", 1),
        ("created_at", -1)
    ], name="user_reactions")
    
    # Index for reaction type filtering
    await db.reactions.create_index([
        ("target_id", 1),
        ("target_type", 1),
        ("reaction_type", 1)
    ], name="target_reaction_type")
    
    # Index for popular reactions analytics
    await db.reactions.create_index([
        ("target_type", 1),
        ("created_at", -1)
    ], name="popular_reactions")
    
    # Comments Collection Indexes
    print("Creating comments indexes...")
    
    # Index for post comments
    await db.comments.create_index([
        ("post_id", 1),
        ("depth", 1),
        ("created_at", -1)
    ], name="post_comments")
    
    # Index for comment replies
    await db.comments.create_index([
        ("parent_comment_id", 1),
        ("created_at", -1)
    ], name="comment_replies")
    
    # Index for user comments
    await db.comments.create_index([
        ("user_id", 1),
        ("created_at", -1)
    ], name="user_comments")
    
    # Index for comment threading path
    await db.comments.create_index([
        ("path", 1)
    ], name="comment_path")
    
    # Index for mentions
    await db.comments.create_index([
        ("mentions", 1),
        ("created_at", -1)
    ], name="comment_mentions")
    
    # Text index for comment search
    await db.comments.create_index([
        ("content", "text")
    ], name="comment_text_search")
    
    # Index for comment sorting by reactions
    await db.comments.create_index([
        ("post_id", 1),
        ("reactions.total", -1)
    ], name="comments_by_reactions")
    
    # Index for comment sorting by replies
    await db.comments.create_index([
        ("post_id", 1),
        ("reply_count", -1)
    ], name="comments_by_replies")
    
    # Bookmarks Collection Indexes
    print("Creating bookmarks indexes...")
    
    # Compound index for user bookmarks (prevent duplicates)
    await db.bookmarks.create_index([
        ("user_id", 1),
        ("post_id", 1)
    ], unique=True, name="user_post_bookmark")
    
    # Index for user's bookmarks
    await db.bookmarks.create_index([
        ("user_id", 1),
        ("created_at", -1)
    ], name="user_bookmarks")
    
    # Index for collection bookmarks
    await db.bookmarks.create_index([
        ("collection_id", 1),
        ("created_at", -1)
    ], name="collection_bookmarks")
    
    # Index for uncategorized bookmarks
    await db.bookmarks.create_index([
        ("user_id", 1),
        ("collection_id", 1)
    ], name="user_collection_bookmarks")
    
    # Text index for bookmark search
    await db.bookmarks.create_index([
        ("notes", "text")
    ], name="bookmark_search")
    
    # Bookmark Collections Indexes
    print("Creating bookmark collections indexes...")
    
    # Index for user collections
    await db.bookmark_collections.create_index([
        ("user_id", 1),
        ("created_at", -1)
    ], name="user_collections")
    
    # Index for shared collections
    await db.bookmark_collections.create_index([
        ("shared_with", 1)
    ], name="shared_collections")
    
    # Follows Collection Indexes
    print("Creating follows indexes...")
    
    # Compound index for follow relationships (prevent duplicates)
    await db.follows.create_index([
        ("follower_id", 1),
        ("following_id", 1)
    ], unique=True, name="follow_relationship")
    
    # Index for followers
    await db.follows.create_index([
        ("following_id", 1),
        ("status", 1),
        ("created_at", -1)
    ], name="user_followers")
    
    # Index for following
    await db.follows.create_index([
        ("follower_id", 1),
        ("status", 1),
        ("created_at", -1)
    ], name="user_following")
    
    # Index for follow requests
    await db.follows.create_index([
        ("following_id", 1),
        ("status", 1)
    ], name="follow_requests")
    
    # Index for outgoing requests
    await db.follows.create_index([
        ("follower_id", 1),
        ("status", 1)
    ], name="outgoing_requests")
    
    # User Connections Indexes
    print("Creating user connections indexes...")
    
    # Index for user connections
    await db.user_connections.create_index([
        ("user_id", 1)
    ], unique=True, name="user_connections_unique")
    
    # Index for blocked users
    await db.user_connections.create_index([
        ("blocked_users", 1)
    ], name="blocked_users")
    
    # Index for close friends
    await db.user_connections.create_index([
        ("close_friends", 1)
    ], name="close_friends")
    
    # Shares Collection Indexes
    print("Creating shares indexes...")
    
    # Index for post shares
    await db.shares.create_index([
        ("original_post_id", 1),
        ("created_at", -1)
    ], name="post_shares")
    
    # Index for user shares
    await db.shares.create_index([
        ("user_id", 1),
        ("created_at", -1)
    ], name="user_shares")
    
    # Index for share type
    await db.shares.create_index([
        ("share_type", 1),
        ("created_at", -1)
    ], name="shares_by_type")
    
    # Index for trending shares
    await db.shares.create_index([
        ("original_post_id", 1),
        ("share_type", 1)
    ], name="trending_shares")
    
    # Index for direct message shares
    await db.shares.create_index([
        ("share_type", 1),
        ("recipient_ids", 1)
    ], name="dm_shares")
    
    # Update existing posts collection for reactions
    print("Updating posts collection indexes...")
    
    # Add reactions field indexes to posts
    await db.posts.create_index([
        ("reactions.total", -1),
        ("created_at", -1)
    ], name="posts_by_reactions")
    
    # Add bookmark count index
    await db.posts.create_index([
        ("bookmark_count", -1)
    ], name="posts_by_bookmarks")
    
    # Add share count index
    await db.posts.create_index([
        ("share_count", -1)
    ], name="posts_by_shares")
    
    # Stories Collection Indexes (for story sharing)
    print("Creating stories indexes...")
    
    # Index for user stories
    await db.stories.create_index([
        ("user_id", 1),
        ("created_at", -1)
    ], name="user_stories")
    
    # Index for story expiration
    await db.stories.create_index([
        ("expires_at", 1)
    ], name="story_expiration")
    
    # Index for story type
    await db.stories.create_index([
        ("story_type", 1)
    ], name="story_type")
    
    # Messages Collection Indexes (for direct message shares)
    print("Creating messages indexes...")
    
    # Index for conversations
    await db.messages.create_index([
        ("sender_id", 1),
        ("recipient_id", 1),
        ("created_at", -1)
    ], name="conversation_messages")
    
    # Index for user messages
    await db.messages.create_index([
        ("recipient_id", 1),
        ("is_read", 1),
        ("created_at", -1)
    ], name="user_messages")
    
    # Index for message type
    await db.messages.create_index([
        ("message_type", 1)
    ], name="message_type")
    
    print("✅ All interaction system indexes created successfully!")

if __name__ == "__main__":
    asyncio.run(create_interaction_indexes())
