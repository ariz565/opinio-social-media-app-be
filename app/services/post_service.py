from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
import re
import asyncio
from fastapi import UploadFile
from app.models.post import Post
from app.models import user as user_model
from app.schemas.post import (
    PostCreate, PostUpdate, PostResponse, PostListResponse,
    PostSchedule, DraftSave, PostSearchQuery, PollVote, PostStats
)
from app.core.exceptions import (
    PostNotFoundError, UnauthorizedError, ValidationError,
    ContentModerationError
)
from app.services.cloudinary_service import cloudinary_service
from app.database.mongo_connection import get_database

class PostService:
    def __init__(self):
        self.post_model = Post()
        # We'll use the user functions directly with database instance

    async def create_post(self, user_id: str, post_data: PostCreate) -> PostResponse:
        """Create a new post with content validation and processing"""
        # Get database instance
        db = get_database()
        
        # Validate user exists
        user = await user_model.get_user_by_id(db, user_id)
        if not user:
            raise UnauthorizedError("User not found")

        # Process content
        processed_content = await self._process_content(post_data.content)
        
        # Extract hashtags and mentions from content
        extracted_hashtags = self._extract_hashtags(processed_content)
        extracted_mentions = await self._extract_mentions(processed_content)
        
        # Combine with provided hashtags and mentions
        all_hashtags = list(set(post_data.hashtags + extracted_hashtags))
        all_mentions = list(set(post_data.mentions + extracted_mentions))

        # Validate media based on post type
        await self._validate_media_for_post_type(post_data.post_type, post_data.media)

        # Prepare post data
        post_dict = {
            "user_id": user_id,
            "content": processed_content,
            "post_type": post_data.post_type,
            "media": [media.dict() for media in post_data.media],
            "poll": post_data.poll.dict() if post_data.poll else None,
            "hashtags": all_hashtags,
            "mentions": all_mentions,
            "location": post_data.location.dict() if post_data.location else None,
            "mood_activity": post_data.mood_activity.dict() if post_data.mood_activity else None,
            "visibility": post_data.visibility,
            "status": "published",
            "allow_comments": post_data.allow_comments,
            "allow_shares": post_data.allow_shares
        }

        # Create post
        post = await self.post_model.create_post(post_dict)
        if not post:
            raise ValidationError("Failed to create post")

        # Send notifications for mentions
        if all_mentions:
            await self._send_mention_notifications(user_id, post["_id"], all_mentions)

        return PostResponse(**post)

    async def save_draft(self, user_id: str, draft_data: DraftSave) -> PostResponse:
        """Save post as draft"""
        # Get database instance
        db = get_database()
        
        # Validate user exists
        user = await user_model.get_user_by_id(db, user_id)
        if not user:
            raise UnauthorizedError("User not found")

        # Process content if provided
        processed_content = ""
        if draft_data.content:
            processed_content = await self._process_content(draft_data.content)

        # Prepare draft data
        draft_dict = {
            "user_id": user_id,
            "content": processed_content,
            "post_type": draft_data.post_type,
            "media": [media.dict() for media in draft_data.media],
            "poll": draft_data.poll.dict() if draft_data.poll else None,
            "hashtags": draft_data.hashtags,
            "mentions": draft_data.mentions,
            "location": draft_data.location.dict() if draft_data.location else None,
            "mood_activity": draft_data.mood_activity.dict() if draft_data.mood_activity else None,
            "visibility": draft_data.visibility,
            "status": "draft",
            "allow_comments": True,
            "allow_shares": True
        }

        # Save draft
        draft = await self.post_model.save_draft(draft_dict)
        if not draft:
            raise ValidationError("Failed to save draft")

        return PostResponse(**draft)

    async def publish_draft(self, user_id: str, draft_id: str, 
                          schedule_data: Optional[PostSchedule] = None) -> PostResponse:
        """Publish a draft post or schedule it"""
        scheduled_time = schedule_data.scheduled_for if schedule_data else None
        
        post = await self.post_model.publish_draft(draft_id, user_id, scheduled_time)
        if not post:
            raise PostNotFoundError("Draft not found or already published")

        # If published immediately, send notifications
        if not scheduled_time:
            mentions = post.get("mentions", [])
            if mentions:
                await self._send_mention_notifications(user_id, post["_id"], mentions)

        return PostResponse(**post)

    async def update_post(self, user_id: str, post_id: str, 
                         update_data: PostUpdate) -> PostResponse:
        """Update an existing post"""
        # Get current post to verify ownership
        current_post = await self.post_model.get_post_by_id(post_id)
        if not current_post:
            raise PostNotFoundError("Post not found")
        
        if current_post["user_id"] != user_id:
            raise UnauthorizedError("You can only edit your own posts")

        if current_post["status"] == "archived":
            raise ValidationError("Cannot edit archived posts")

        # Prepare update data
        update_dict = {}
        if update_data.content is not None:
            processed_content = await self._process_content(update_data.content)
            update_dict["content"] = processed_content
            
            # Extract new hashtags and mentions
            extracted_hashtags = self._extract_hashtags(processed_content)
            extracted_mentions = await self._extract_mentions(processed_content)
            
            if update_data.hashtags is not None:
                update_dict["hashtags"] = list(set(update_data.hashtags + extracted_hashtags))
            else:
                update_dict["hashtags"] = extracted_hashtags

        if update_data.media is not None:
            update_dict["media"] = [media.dict() for media in update_data.media]
        
        if update_data.location is not None:
            update_dict["location"] = update_data.location.dict()
        
        if update_data.mood_activity is not None:
            update_dict["mood_activity"] = update_data.mood_activity.dict()
        
        if update_data.visibility is not None:
            update_dict["visibility"] = update_data.visibility
        
        if update_data.allow_comments is not None:
            update_dict["allow_comments"] = update_data.allow_comments
        
        if update_data.allow_shares is not None:
            update_dict["allow_shares"] = update_data.allow_shares

        update_dict["edit_reason"] = update_data.edit_reason

        # Update post
        updated_post = await self.post_model.update_post(post_id, update_dict, user_id)
        if not updated_post:
            raise ValidationError("Failed to update post")

        return PostResponse(**updated_post)

    async def delete_post(self, user_id: str, post_id: str, permanent: bool = False) -> bool:
        """Delete a post (soft delete by default, permanent if specified)"""
        # Verify ownership
        post = await self.post_model.get_post_by_id(post_id)
        if not post:
            raise PostNotFoundError("Post not found")
        
        if post["user_id"] != user_id:
            raise UnauthorizedError("You can only delete your own posts")

        if permanent:
            return await self.post_model.permanently_delete_post(post_id, user_id)
        else:
            return await self.post_model.delete_post(post_id, user_id)

    async def get_post(self, post_id: str, requesting_user_id: Optional[str] = None) -> PostResponse:
        """Get a single post with visibility checks"""
        post = await self.post_model.get_post_by_id(post_id)
        if not post:
            raise PostNotFoundError("Post not found")

        # Check visibility permissions
        if not await self._can_view_post(post, requesting_user_id):
            raise UnauthorizedError("You don't have permission to view this post")

        # Increment view count if not the author
        if requesting_user_id and requesting_user_id != post["user_id"]:
            await self.post_model.update_engagement_stats(post_id, "views_count")

        return PostResponse(**post)

    async def get_user_posts(self, user_id: str, requesting_user_id: Optional[str] = None,
                           page: int = 1, per_page: int = 20, 
                           include_drafts: bool = False) -> PostListResponse:
        """Get posts by a specific user"""
        skip = (page - 1) * per_page
        
        # Only allow viewing drafts if requesting user is the owner
        if include_drafts and requesting_user_id != user_id:
            include_drafts = False

        posts = await self.post_model.get_posts_by_user(
            user_id, skip, per_page, include_drafts
        )

        # Filter posts based on visibility
        filtered_posts = []
        for post in posts:
            if await self._can_view_post(post, requesting_user_id):
                filtered_posts.append(PostResponse(**post))

        # Get total count (this is simplified - in production you'd want a separate count query)
        total = len(filtered_posts)
        
        return PostListResponse(
            posts=filtered_posts,
            total=total,
            page=page,
            per_page=per_page,
            has_next=len(filtered_posts) == per_page,
            has_prev=page > 1
        )

    async def get_feed(self, user_id: str, page: int = 1, per_page: int = 20) -> PostListResponse:
        """Get personalized feed for user"""
        skip = (page - 1) * per_page
        
        # Get database instance
        db = get_database()
        
        # Get user's following list
        user = await user_model.get_user_by_id(db, user_id)
        if not user:
            raise UnauthorizedError("User not found")

        following_ids = user.get("following", [])
        
        posts = await self.post_model.get_feed_posts(
            user_id, following_ids, skip, per_page
        )

        post_responses = [PostResponse(**post) for post in posts]
        
        return PostListResponse(
            posts=post_responses,
            total=len(post_responses),
            page=page,
            per_page=per_page,
            has_next=len(post_responses) == per_page,
            has_prev=page > 1
        )

    async def pin_post(self, user_id: str, post_id: str) -> bool:
        """Pin a post to user's profile"""
        # Verify ownership
        post = await self.post_model.get_post_by_id(post_id)
        if not post:
            raise PostNotFoundError("Post not found")
        
        if post["user_id"] != user_id:
            raise UnauthorizedError("You can only pin your own posts")

        if post["status"] != "published":
            raise ValidationError("Only published posts can be pinned")

        return await self.post_model.pin_post(post_id, user_id)

    async def unpin_post(self, user_id: str, post_id: str) -> bool:
        """Unpin a post from user's profile"""
        return await self.post_model.unpin_post(post_id, user_id)

    async def get_user_drafts(self, user_id: str) -> List[PostResponse]:
        """Get all drafts for a user"""
        drafts = await self.post_model.get_user_drafts(user_id)
        return [PostResponse(**draft) for draft in drafts]

    async def search_posts(self, query_data: PostSearchQuery, 
                          requesting_user_id: Optional[str] = None,
                          page: int = 1, per_page: int = 20) -> PostListResponse:
        """Search posts with filters"""
        skip = (page - 1) * per_page
        
        posts = await self.post_model.search_posts(query_data.query, skip, per_page)
        
        # Apply additional filters
        filtered_posts = []
        for post in posts:
            if await self._can_view_post(post, requesting_user_id):
                # Apply type filter
                if query_data.post_type and post["post_type"] != query_data.post_type:
                    continue
                
                # Apply hashtag filter
                if query_data.hashtags:
                    post_hashtags = set(post.get("hashtags", []))
                    query_hashtags = set(query_data.hashtags)
                    if not query_hashtags.intersection(post_hashtags):
                        continue
                
                # Apply date filters
                post_date = post["created_at"]
                if query_data.date_from and post_date < query_data.date_from:
                    continue
                if query_data.date_to and post_date > query_data.date_to:
                    continue
                
                filtered_posts.append(PostResponse(**post))

        return PostListResponse(
            posts=filtered_posts,
            total=len(filtered_posts),
            page=page,
            per_page=per_page,
            has_next=len(filtered_posts) == per_page,
            has_prev=page > 1
        )

    async def get_trending_posts(self, hours: int = 24, limit: int = 50) -> List[PostResponse]:
        """Get trending posts"""
        posts = await self.post_model.get_trending_posts(hours, limit)
        return [PostResponse(**post) for post in posts]

    async def vote_on_poll(self, user_id: str, post_id: str, vote_data: PollVote) -> PostResponse:
        """Vote on a poll"""
        post = await self.post_model.get_post_by_id(post_id)
        if not post:
            raise PostNotFoundError("Post not found")

        if post["post_type"] != "poll" or not post.get("poll"):
            raise ValidationError("This post is not a poll")

        poll = post["poll"]
        
        # Check if poll has expired
        if poll.get("expires_at") and datetime.now(timezone.utc) > poll["expires_at"]:
            raise ValidationError("This poll has expired")

        # Check if user already voted (for single choice polls)
        if not poll.get("multiple_choice", False):
            for option in poll["options"]:
                if user_id in option.get("voters", []):
                    raise ValidationError("You have already voted on this poll")

        # Validate option indices
        if max(vote_data.option_indices) >= len(poll["options"]):
            raise ValidationError("Invalid option index")

        # Add votes
        for option_index in vote_data.option_indices:
            poll["options"][option_index]["votes"] += 1
            if user_id not in poll["options"][option_index]["voters"]:
                poll["options"][option_index]["voters"].append(user_id)

        # Update total votes
        poll["total_votes"] = sum(option["votes"] for option in poll["options"])

        # Update post
        updated_post = await self.post_model.update_post(
            post_id, {"poll": poll}, post["user_id"]
        )
        
        return PostResponse(**updated_post)

    async def get_user_stats(self, user_id: str) -> PostStats:
        """Get user's post statistics"""
        user_posts = await self.post_model.get_posts_by_user(user_id, 0, 1000, True)
        
        total_posts = len(user_posts)
        published_posts = len([p for p in user_posts if p["status"] == "published"])
        draft_posts = len([p for p in user_posts if p["status"] == "draft"])
        scheduled_posts = len([p for p in user_posts if p["status"] == "scheduled"])
        archived_posts = len([p for p in user_posts if p["status"] == "archived"])
        
        total_likes = sum(p.get("engagement_stats", {}).get("likes_count", 0) for p in user_posts)
        total_comments = sum(p.get("engagement_stats", {}).get("comments_count", 0) for p in user_posts)
        total_shares = sum(p.get("engagement_stats", {}).get("shares_count", 0) for p in user_posts)
        total_views = sum(p.get("engagement_stats", {}).get("views_count", 0) for p in user_posts)

        return PostStats(
            total_posts=total_posts,
            published_posts=published_posts,
            draft_posts=draft_posts,
            scheduled_posts=scheduled_posts,
            archived_posts=archived_posts,
            total_likes=total_likes,
            total_comments=total_comments,
            total_shares=total_shares,
            total_views=total_views
        )

    # Helper methods
    async def _process_content(self, content: str) -> str:
        """Process and clean post content"""
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content.strip())
        
        # Basic content moderation (you'd integrate with a proper moderation service)
        if await self._contains_inappropriate_content(content):
            raise ContentModerationError("Content violates community guidelines")
        
        return content

    async def _contains_inappropriate_content(self, content: str) -> bool:
        """Basic content moderation check"""
        # This is a placeholder - implement proper content moderation
        inappropriate_words = ["spam", "scam", "hate"]  # Simplified example
        content_lower = content.lower()
        return any(word in content_lower for word in inappropriate_words)

    def _extract_hashtags(self, content: str) -> List[str]:
        """Extract hashtags from content"""
        hashtag_pattern = r'#\w+'
        hashtags = re.findall(hashtag_pattern, content)
        return list(set(hashtags))  # Remove duplicates

    async def _extract_mentions(self, content: str) -> List[str]:
        """Extract user mentions from content"""
        mention_pattern = r'@(\w+)'
        usernames = re.findall(mention_pattern, content)
        
        # Get database instance
        db = get_database()
        
        # Validate that mentioned users exist
        valid_mentions = []
        for username in usernames:
            user = await user_model.get_user_by_username(db, username)
            if user:
                valid_mentions.append(str(user["_id"]))
        
        return valid_mentions

    async def _validate_media_for_post_type(self, post_type: str, media: List) -> None:
        """Validate media based on post type"""
        if post_type == "text" and media:
            raise ValidationError("Text posts cannot have media attachments")
        
        if post_type == "image" and not media:
            raise ValidationError("Image posts must have at least one image")
        
        if post_type == "video" and (not media or media[0].type != "video"):
            raise ValidationError("Video posts must have a video attachment")

    async def _can_view_post(self, post: dict, requesting_user_id: Optional[str]) -> bool:
        """Check if user can view a post based on visibility settings"""
        if post["status"] != "published":
            # Only author can view unpublished posts
            return requesting_user_id == post["user_id"]

        visibility = post["visibility"]
        
        if visibility == "public":
            return True
        
        if visibility == "private":
            return requesting_user_id == post["user_id"]
        
        if not requesting_user_id:
            return False
        
        # Get database instance
        db = get_database()
        
        if visibility == "followers":
            # Check if requesting user follows the post author
            author = await user_model.get_user_by_id(db, post["user_id"])
            return requesting_user_id in author.get("followers", [])
        
        if visibility == "close_friends":
            # Check if requesting user is in close friends list
            author = await user_model.get_user_by_id(db, post["user_id"])
            return requesting_user_id in author.get("close_friends", [])
        
        return False

    async def upload_post_media(
        self, 
        files: List[UploadFile], 
        user_id: str, 
        post_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Upload media files for a post
        
        Args:
            files: List of uploaded files
            user_id: ID of the user uploading
            post_id: Optional post ID for organization
            
        Returns:
            List of media metadata
        """
        if not files:
            return []
        
        media_results = []
        
        for file in files:
            try:
                # Determine file type
                if file.content_type and file.content_type.startswith('image/'):
                    # Upload image
                    result = await cloudinary_service.upload_image(
                        file=file,
                        user_id=user_id,
                        post_id=post_id
                    )
                    media_results.append({
                        "type": "image",
                        "url": result["url"],
                        "public_id": result["public_id"],
                        "width": result["width"],
                        "height": result["height"],
                        "format": result["format"],
                        "size": result["bytes"]
                    })
                    
                elif file.content_type and file.content_type.startswith('video/'):
                    # Upload video
                    result = await cloudinary_service.upload_video(
                        file=file,
                        user_id=user_id,
                        post_id=post_id
                    )
                    
                    # Create thumbnail for video
                    thumbnail_url = await cloudinary_service.create_thumbnail(
                        video_public_id=result["public_id"]
                    )
                    
                    media_results.append({
                        "type": "video",
                        "url": result["url"],
                        "thumbnail_url": thumbnail_url,
                        "public_id": result["public_id"],
                        "width": result.get("width"),
                        "height": result.get("height"),
                        "format": result["format"],
                        "size": result["bytes"],
                        "duration": result.get("duration")
                    })
                    
                else:
                    raise ValidationError(f"Unsupported file type: {file.content_type}")
                    
            except Exception as e:
                # Log error but continue with other files
                print(f"Failed to upload {file.filename}: {str(e)}")
                continue
        
        return media_results

    async def delete_post_media(self, media_items: List[Dict[str, Any]]) -> None:
        """
        Delete media files from Cloudinary when a post is deleted
        
        Args:
            media_items: List of media items with public_ids
        """
        for media in media_items:
            if "public_id" in media:
                resource_type = "video" if media.get("type") == "video" else "image"
                await cloudinary_service.delete_media(
                    public_id=media["public_id"],
                    resource_type=resource_type
                )

    async def update_post_with_media(
        self, 
        post_id: str, 
        user_id: str, 
        media_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Update a post with uploaded media
        
        Args:
            post_id: ID of the post to update
            user_id: ID of the user updating
            media_data: List of media metadata
            
        Returns:
            Updated post data
        """
        # Check if post exists and user has permission
        post = await self.post_model.get_post_by_id(post_id)
        if not post:
            raise PostNotFoundError("Post not found")
        
        if post["user_id"] != user_id:
            raise UnauthorizedError("Not authorized to update this post")
        
        # Update post with media
        update_data = {"media": media_data}
        success = await self.post_model.update_post(post_id, update_data)
        
        if not success:
            raise ValidationError("Failed to update post with media")
        
        # Return updated post
        return await self.post_model.get_post_by_id(post_id)

    async def _send_mention_notifications(self, author_id: str, post_id: str, 
                                        mentioned_user_ids: List[str]) -> None:
        """Send notifications to mentioned users"""
        # This would integrate with your notification service
        # For now, it's a placeholder
        pass

    async def publish_scheduled_posts(self) -> int:
        """Background task to publish scheduled posts"""
        scheduled_posts = await self.post_model.get_scheduled_posts()
        published_count = 0
        
        for post in scheduled_posts:
            success = await self.post_model.publish_scheduled_post(post["_id"])
            if success:
                published_count += 1
                # Send notifications for mentions
                mentions = post.get("mentions", [])
                if mentions:
                    await self._send_mention_notifications(
                        post["user_id"], post["_id"], mentions
                    )
        
        return published_count
