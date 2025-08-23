"""
API functions for reactions system
Handles all reaction-related operations with proper authentication
"""

from typing import List, Optional
from fastapi import HTTPException, Depends
from app.models.reaction import reaction_model, ReactionType
from app.schemas.interactions import (
    ReactionCreate, ReactionResponse, ReactionWithUser, 
    ReactionCounts, MessageResponse
)
from app.core.auth import get_current_user

async def add_reaction_to_target(
    reaction_data: ReactionCreate,
    current_user: dict = Depends(get_current_user)
) -> ReactionResponse:
    """
    🔐 Requires Authentication
    Add or update a reaction to a post, comment, or story
    """
    try:
        # Get user_id safely and convert to string
        user_id = current_user.get('_id') or current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        # Ensure user_id is a string
        user_id = str(user_id)
            
        result = await reaction_model.add_reaction(
            user_id=user_id,
            target_id=reaction_data.target_id,
            target_type=reaction_data.target_type,
            reaction_type=reaction_data.reaction_type
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return ReactionResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add reaction: {str(e)}")

async def remove_reaction_from_target(
    target_id: str,
    target_type: str,
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    """
    🔐 Requires Authentication
    Remove user's reaction from a target
    """
    try:
        # Get user_id safely and convert to string
        user_id = current_user.get('_id') or current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        # Ensure user_id is a string
        user_id = str(user_id)
            
        success = await reaction_model.remove_reaction(
            user_id=user_id,
            target_id=target_id,
            target_type=target_type
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Reaction not found")
        
        return MessageResponse(message="Reaction removed successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove reaction: {str(e)}")

async def get_target_reactions(
    target_id: str,
    target_type: str,
    reaction_type: Optional[str] = None,
    limit: int = 50,
    skip: int = 0
) -> List[ReactionWithUser]:
    """
    Get reactions for a specific target with user details
    Public endpoint - no authentication required
    """
    try:
        # Convert string to enum if provided
        reaction_enum = None
        if reaction_type:
            try:
                reaction_enum = ReactionType(reaction_type)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid reaction type")
        
        reactions = await reaction_model.get_reactions_for_target(
            target_id=target_id,
            target_type=target_type,
            reaction_type=reaction_enum,
            limit=limit,
            skip=skip
        )
        
        return [ReactionWithUser(**reaction) for reaction in reactions]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get reactions: {str(e)}")

async def get_target_reaction_counts(
    target_id: str,
    target_type: str
) -> ReactionCounts:
    """
    Get reaction counts for a target
    Public endpoint - no authentication required
    """
    try:
        counts = await reaction_model.get_reaction_counts(
            target_id=target_id,
            target_type=target_type
        )
        
        return ReactionCounts(**counts)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get reaction counts: {str(e)}")

async def get_user_reaction_for_target(
    target_id: str,
    target_type: str,
    current_user: dict = Depends(get_current_user)
) -> Optional[ReactionResponse]:
    """
    🔐 Requires Authentication
    Get current user's reaction for a specific target
    """
    try:
        # Get user_id safely and convert to string
        user_id = current_user.get('_id') or current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        # Ensure user_id is a string
        user_id = str(user_id)
            
        reaction = await reaction_model.get_user_reaction(
            user_id=user_id,
            target_id=target_id,
            target_type=target_type
        )
        
        return ReactionResponse(**reaction) if reaction else None
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user reaction: {str(e)}")

async def get_user_reactions_list(
    target_type: Optional[str] = None,
    reaction_type: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
    current_user: dict = Depends(get_current_user)
) -> List[ReactionResponse]:
    """
    🔐 Requires Authentication
    Get all reactions made by the current user
    """
    try:
        # Convert string to enum if provided
        reaction_enum = None
        if reaction_type:
            try:
                reaction_enum = ReactionType(reaction_type)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid reaction type")
        
        # Get user_id safely
        user_id = current_user.get('_id') or current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        reactions = await reaction_model.get_user_reactions(
            user_id=user_id,
            target_type=target_type,
            reaction_type=reaction_enum,
            limit=limit,
            skip=skip
        )
        
        return [ReactionResponse(**reaction) for reaction in reactions]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user reactions: {str(e)}")

async def get_popular_reactions(
    target_type: str,
    days: int = 7,
    limit: int = 10
) -> List[dict]:
    """
    Get most reacted content in the last N days
    Public endpoint - no authentication required
    """
    try:
        if days < 1 or days > 30:
            raise HTTPException(status_code=400, detail="Days must be between 1 and 30")
        
        popular = await reaction_model.get_popular_reactions(
            target_type=target_type,
            days=days,
            limit=limit
        )
        
        return popular
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get popular reactions: {str(e)}")

async def toggle_reaction(
    target_id: str,
    target_type: str,
    reaction_type: str,
    current_user: dict = Depends(get_current_user)
) -> ReactionResponse:
    """
    🔐 Requires Authentication
    Toggle a reaction (add if not exists, remove if exists, or update if different)
    """
    try:
        print(f"DEBUG: toggle_reaction called with target_id={target_id}, target_type={target_type}, reaction_type={reaction_type}")
        print(f"DEBUG: current_user={current_user}")
        
        # Get user ID safely
        user_id = current_user.get('_id') or current_user.get('id')
        if not user_id:
            print("DEBUG: User ID not found in current_user")
            raise HTTPException(status_code=400, detail="User ID not found")
        
        print(f"DEBUG: Using user_id={user_id}")
        
        # Validate reaction type
        try:
            reaction_enum = ReactionType(reaction_type)
            print(f"DEBUG: Valid reaction type: {reaction_enum}")
        except ValueError:
            print(f"DEBUG: Invalid reaction type: {reaction_type}")
            raise HTTPException(status_code=400, detail="Invalid reaction type")
        
        print("DEBUG: About to check existing reaction")
        # Check if user already has a reaction
        existing_reaction = await reaction_model.get_user_reaction(
            user_id=user_id,
            target_id=target_id,
            target_type=target_type
        )
        print(f"DEBUG: Existing reaction: {existing_reaction}")
        
        if existing_reaction:
            if existing_reaction["reaction_type"] == reaction_type:
                # Same reaction - remove it
                await reaction_model.remove_reaction(
                    user_id=user_id,
                    target_id=target_id,
                    target_type=target_type
                )
                return ReactionResponse(
                    _id=existing_reaction["_id"],
                    user_id=user_id,
                    target_id=target_id,
                    target_type=target_type,
                    reaction_type=reaction_type,
                    created_at=existing_reaction["created_at"],
                    action="removed"
                )
            else:
                # Different reaction - update it
                result = await reaction_model.add_reaction(
                    user_id=user_id,
                    target_id=target_id,
                    target_type=target_type,
                    reaction_type=reaction_enum
                )
                return ReactionResponse(**result)
        else:
            # No existing reaction - add new one
            result = await reaction_model.add_reaction(
                user_id=user_id,
                target_id=target_id,
                target_type=target_type,
                reaction_type=reaction_enum
            )
            return ReactionResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to toggle reaction: {str(e)}")
