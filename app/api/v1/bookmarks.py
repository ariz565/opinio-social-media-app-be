"""
API functions for advanced bookmark system
Handles bookmark collections, sharing, and bulk operations
"""

from typing import List, Optional
from fastapi import HTTPException, Depends
from app.models.bookmark import bookmark_model, BookmarkPrivacy
from app.schemas.interactions import (
    BookmarkCreate, BookmarkUpdate, BookmarkResponse,
    BookmarkCollectionCreate, BookmarkCollectionUpdate, BookmarkCollectionResponse,
    BookmarkListParams, BulkBookmarkOperation, MessageResponse
)
from app.core.auth import get_current_user

# Collection Management
async def create_bookmark_collection(
    collection_data: BookmarkCollectionCreate,
    current_user: dict = Depends(get_current_user)
) -> BookmarkCollectionResponse:
    """
    🔐 Requires Authentication
    Create a new bookmark collection/folder
    """
    try:
        collection = await bookmark_model.create_bookmark_collection(
            user_id=current_user["_id"],
            name=collection_data.name,
            description=collection_data.description,
            privacy=collection_data.privacy,
            color=collection_data.color
        )
        
        return BookmarkCollectionResponse(**collection)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create collection: {str(e)}")

async def get_user_collections(
    include_shared: bool = False,
    current_user: dict = Depends(get_current_user)
) -> List[BookmarkCollectionResponse]:
    """
    🔐 Requires Authentication
    Get user's bookmark collections
    """
    try:
        collections = await bookmark_model.get_user_collections(
            user_id=current_user["_id"],
            include_shared=include_shared
        )
        
        return [BookmarkCollectionResponse(**collection) for collection in collections]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get collections: {str(e)}")

async def update_bookmark_collection(
    collection_id: str,
    collection_data: BookmarkCollectionUpdate,
    current_user: dict = Depends(get_current_user)
) -> BookmarkCollectionResponse:
    """
    🔐 Requires Authentication
    Update a bookmark collection
    """
    try:
        updated_collection = await bookmark_model.update_collection(
            collection_id=collection_id,
            user_id=current_user["_id"],
            name=collection_data.name,
            description=collection_data.description,
            privacy=collection_data.privacy,
            color=collection_data.color
        )
        
        if not updated_collection:
            raise HTTPException(
                status_code=404, 
                detail="Collection not found or you don't have permission to update it"
            )
        
        return BookmarkCollectionResponse(**updated_collection)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update collection: {str(e)}")

async def delete_bookmark_collection(
    collection_id: str,
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    """
    🔐 Requires Authentication
    Delete a bookmark collection and move bookmarks to default
    """
    try:
        success = await bookmark_model.delete_collection(
            collection_id=collection_id,
            user_id=current_user["_id"]
        )
        
        if not success:
            raise HTTPException(
                status_code=404, 
                detail="Collection not found or you don't have permission to delete it"
            )
        
        return MessageResponse(message="Collection deleted successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete collection: {str(e)}")

async def share_collection(
    collection_id: str,
    shared_with_user_ids: List[str],
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    """
    🔐 Requires Authentication
    Share collection with specific users
    """
    try:
        success = await bookmark_model.share_collection(
            collection_id=collection_id,
            user_id=current_user["_id"],
            shared_with_user_ids=shared_with_user_ids
        )
        
        if not success:
            raise HTTPException(
                status_code=404, 
                detail="Collection not found or you don't have permission to share it"
            )
        
        return MessageResponse(message="Collection shared successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to share collection: {str(e)}")

# Bookmark Management
async def add_bookmark(
    bookmark_data: BookmarkCreate,
    current_user: dict = Depends(get_current_user)
) -> BookmarkResponse:
    """
    🔐 Requires Authentication
    Add a post to bookmarks
    """
    try:
        # Validate post exists
        from app.models.post import post_model
        post = await post_model.get_post_by_id(bookmark_data.post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        # Validate collection if provided
        if bookmark_data.collection_id:
            collections = await bookmark_model.get_user_collections(
                user_id=current_user["_id"],
                include_shared=True
            )
            collection_ids = [col["_id"] for col in collections]
            if bookmark_data.collection_id not in collection_ids:
                raise HTTPException(status_code=404, detail="Collection not found")
        
        bookmark = await bookmark_model.add_bookmark(
            user_id=current_user["_id"],
            post_id=bookmark_data.post_id,
            collection_id=bookmark_data.collection_id,
            notes=bookmark_data.notes
        )
        
        return BookmarkResponse(**bookmark)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add bookmark: {str(e)}")

async def remove_bookmark(
    post_id: str,
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    """
    🔐 Requires Authentication
    Remove a bookmark
    """
    try:
        success = await bookmark_model.remove_bookmark(
            user_id=current_user["_id"],
            post_id=post_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Bookmark not found")
        
        return MessageResponse(message="Bookmark removed successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove bookmark: {str(e)}")

async def get_user_bookmarks(
    params: BookmarkListParams = Depends(),
    current_user: dict = Depends(get_current_user)
) -> List[BookmarkResponse]:
    """
    🔐 Requires Authentication
    Get user's bookmarks with filtering options
    """
    try:
        bookmarks = await bookmark_model.get_user_bookmarks(
            user_id=current_user["_id"],
            collection_id=params.collection_id,
            limit=params.limit,
            skip=params.skip,
            search_term=params.search_term
        )
        
        return [BookmarkResponse(**bookmark) for bookmark in bookmarks]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get bookmarks: {str(e)}")

async def update_bookmark(
    bookmark_id: str,
    bookmark_data: BookmarkUpdate,
    current_user: dict = Depends(get_current_user)
) -> BookmarkResponse:
    """
    🔐 Requires Authentication
    Update bookmark notes or move to different collection
    """
    try:
        # Get existing bookmark to verify ownership
        from app.database.mongo_connection import get_database
        db = await get_database()
        
        existing_bookmark = await db.bookmarks.find_one({
            "_id": bookmark_id,
            "user_id": current_user["_id"]
        })
        
        if not existing_bookmark:
            raise HTTPException(status_code=404, detail="Bookmark not found")
        
        # Validate collection if provided
        if bookmark_data.collection_id:
            collections = await bookmark_model.get_user_collections(
                user_id=current_user["_id"],
                include_shared=True
            )
            collection_ids = [col["_id"] for col in collections]
            if bookmark_data.collection_id not in collection_ids:
                raise HTTPException(status_code=404, detail="Collection not found")
        
        # Update bookmark using bulk move for collection change
        if bookmark_data.collection_id != existing_bookmark.get("collection_id"):
            await bookmark_model.bulk_move_bookmarks(
                user_id=current_user["_id"],
                bookmark_ids=[bookmark_id],
                target_collection_id=bookmark_data.collection_id
            )
        
        # Update notes if provided
        if bookmark_data.notes is not None:
            await db.bookmarks.update_one(
                {"_id": bookmark_id},
                {"$set": {"notes": bookmark_data.notes}}
            )
        
        # Return updated bookmark
        updated_bookmark = await bookmark_model.get_bookmark_by_id(bookmark_id)
        return BookmarkResponse(**updated_bookmark)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update bookmark: {str(e)}")

async def check_bookmark_status(
    post_id: str,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    🔐 Requires Authentication
    Check if user has bookmarked a post
    """
    try:
        is_bookmarked = await bookmark_model.check_bookmark_exists(
            user_id=current_user["_id"],
            post_id=post_id
        )
        
        return {"is_bookmarked": is_bookmarked}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check bookmark status: {str(e)}")

# Bulk Operations
async def bulk_move_bookmarks(
    operation: BulkBookmarkOperation,
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    """
    🔐 Requires Authentication
    Move multiple bookmarks to a different collection
    """
    try:
        # Validate collection if provided
        if operation.target_collection_id:
            collections = await bookmark_model.get_user_collections(
                user_id=current_user["_id"],
                include_shared=True
            )
            collection_ids = [col["_id"] for col in collections]
            if operation.target_collection_id not in collection_ids:
                raise HTTPException(status_code=404, detail="Target collection not found")
        
        moved_count = await bookmark_model.bulk_move_bookmarks(
            user_id=current_user["_id"],
            bookmark_ids=operation.bookmark_ids,
            target_collection_id=operation.target_collection_id
        )
        
        if moved_count == 0:
            raise HTTPException(status_code=404, detail="No bookmarks found to move")
        
        collection_name = "default" if not operation.target_collection_id else "collection"
        return MessageResponse(
            message=f"Successfully moved {moved_count} bookmarks to {collection_name}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to move bookmarks: {str(e)}")

async def bulk_delete_bookmarks(
    bookmark_ids: List[str],
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    """
    🔐 Requires Authentication
    Delete multiple bookmarks
    """
    try:
        if not bookmark_ids:
            raise HTTPException(status_code=400, detail="No bookmark IDs provided")
        
        deleted_count = await bookmark_model.bulk_delete_bookmarks(
            user_id=current_user["_id"],
            bookmark_ids=bookmark_ids
        )
        
        if deleted_count == 0:
            raise HTTPException(status_code=404, detail="No bookmarks found to delete")
        
        return MessageResponse(message=f"Successfully deleted {deleted_count} bookmarks")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete bookmarks: {str(e)}")

async def get_bookmark_analytics(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    🔐 Requires Authentication
    Get user's bookmark analytics
    """
    try:
        from app.database.mongo_connection import get_database
        db = await get_database()
        
        # Get bookmark statistics
        pipeline = [
            {"$match": {"user_id": current_user["_id"]}},
            {
                "$group": {
                    "_id": "$collection_id",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        collection_stats = await db.bookmarks.aggregate(pipeline).to_list(length=None)
        
        # Get total counts
        total_bookmarks = sum(stat["count"] for stat in collection_stats)
        uncategorized = next((stat["count"] for stat in collection_stats if stat["_id"] is None), 0)
        categorized = total_bookmarks - uncategorized
        
        # Get collection count
        collections = await bookmark_model.get_user_collections(current_user["_id"])
        
        return {
            "total_bookmarks": total_bookmarks,
            "total_collections": len(collections),
            "uncategorized_bookmarks": uncategorized,
            "categorized_bookmarks": categorized,
            "collection_breakdown": collection_stats
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get bookmark analytics: {str(e)}")
