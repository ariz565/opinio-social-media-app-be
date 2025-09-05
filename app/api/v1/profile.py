from fastapi import HTTPException, Depends, status, UploadFile, File
from typing import Optional, List
from app.models import user as user_model
from app.schemas.profile import *
from app.core.auth import get_current_user
from app.utils.file_upload import save_uploaded_file, delete_file
from app.database.mongo_connection import get_database
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

async def get_user_profile(username: str, current_user: dict = Depends(get_current_user)):
    """Get user profile by username"""
    try:
        logger.info(f"🔍 Looking for profile: username='{username}'")
        db = await get_database()
        
        # First get user by username
        user = await user_model.get_user_by_username(db, username)
        logger.info(f"🔍 User lookup result: {user is not None}")
        if user:
            logger.info(f"🔍 Found user: id={user.get('_id')}, username={user.get('username')}")
        
        if not user:
            logger.warning(f"🚨 User not found: username='{username}'")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get full profile
        profile = await user_model.get_full_profile(db, str(user["_id"]))
        logger.info(f"🔍 Profile lookup result: {profile is not None}")
        
        if not profile:
            logger.warning(f"🚨 Profile not found for user_id: {user['_id']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )
        
        logger.info(f"✅ Successfully retrieved profile for username='{username}'")
        return FullProfile(**profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user profile"
        )

async def update_basic_info(
    data: BasicInfoUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update basic profile information"""
    try:
        db = await get_database()
        user_id = current_user["id"]
        
        result = await user_model.update_profile_section(
            db, user_id, "basic_info", data.model_dump(exclude_unset=True)
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update basic info"
            )
        
        return {"message": "Basic info updated successfully", "data": result}
        
    except Exception as e:
        logger.error(f"Error updating basic info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update basic info"
        )

async def update_experience(
    data: ExperienceUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update work experience"""
    try:
        db = await get_database()
        user_id = current_user["id"]
        
        # Add IDs to experience items if not present
        for i, exp in enumerate(data.experience):
            if not exp.id:
                exp.id = f"exp_{user_id}_{i}_{int(datetime.now().timestamp())}"
        
        result = await user_model.update_profile_section(
            db, user_id, "experience", data.model_dump()
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update experience"
            )
        
        return {"message": "Experience updated successfully", "data": result}
        
    except Exception as e:
        logger.error(f"Error updating experience: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update experience"
        )

async def add_single_experience(
    data: WorkExperience,
    current_user: dict = Depends(get_current_user)
):
    """Add a single work experience"""
    try:
        db = await get_database()
        user_id = current_user["id"]
        
        # Generate ID if not present
        if not data.id:
            data.id = f"exp_{user_id}_{int(datetime.now().timestamp())}"
        
        result = await user_model.add_profile_item(db, user_id, "experience", data.model_dump())
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to add experience"
            )
        
        return {"message": "Experience added successfully", "data": data}
        
    except Exception as e:
        logger.error(f"Error adding experience: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add experience"
        )

async def delete_experience(
    item_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a work experience"""
    try:
        db = await get_database()
        user_id = current_user["id"]
        
        result = await user_model.delete_profile_item(db, user_id, "experience", item_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete experience"
            )
        
        return {"message": "Experience deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting experience: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete experience"
        )

async def update_education(
    data: EducationUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update education"""
    try:
        db = await get_database()
        user_id = current_user["id"]
        
        # Add IDs to education items if not present
        for i, edu in enumerate(data.education):
            if not edu.id:
                edu.id = f"edu_{user_id}_{i}_{int(datetime.now().timestamp())}"
        
        result = await user_model.update_profile_section(
            db, user_id, "education", data.model_dump()
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update education"
            )
        
        return {"message": "Education updated successfully", "data": result}
        
    except Exception as e:
        logger.error(f"Error updating education: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update education"
        )

async def add_single_education(
    data: Education,
    current_user: dict = Depends(get_current_user)
):
    """Add a single education"""
    try:
        db = await get_database()
        user_id = current_user["id"]
        
        # Generate ID if not present
        if not data.id:
            data.id = f"edu_{user_id}_{int(datetime.now().timestamp())}"
        
        result = await user_model.add_profile_item(db, user_id, "education", data.model_dump())
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to add education"
            )
        
        return {"message": "Education added successfully", "data": data}
        
    except Exception as e:
        logger.error(f"Error adding education: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add education"
        )

async def delete_education(
    item_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete an education"""
    try:
        db = await get_database()
        user_id = current_user["id"]
        
        result = await user_model.delete_profile_item(db, user_id, "education", item_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete education"
            )
        
        return {"message": "Education deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting education: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete education"
        )

async def update_skills(
    data: SkillsUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update skills"""
    try:
        db = await get_database()
        user_id = current_user["id"]
        
        result = await user_model.update_profile_section(
            db, user_id, "skills", data.model_dump()
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update skills"
            )
        
        return {"message": "Skills updated successfully", "data": result}
        
    except Exception as e:
        logger.error(f"Error updating skills: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update skills"
        )

async def update_languages(
    data: LanguagesUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update languages"""
    try:
        db = await get_database()
        user_id = current_user["id"]
        
        result = await user_model.update_profile_section(
            db, user_id, "languages", data.model_dump()
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update languages"
            )
        
        return {"message": "Languages updated successfully", "data": result}
        
    except Exception as e:
        logger.error(f"Error updating languages: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update languages"
        )

async def update_certifications(
    data: CertificationsUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update certifications"""
    try:
        db = await get_database()
        user_id = current_user["id"]
        
        # Add IDs to certification items if not present
        for i, cert in enumerate(data.certifications):
            if not cert.id:
                cert.id = f"cert_{user_id}_{i}_{int(datetime.now().timestamp())}"
        
        result = await user_model.update_profile_section(
            db, user_id, "certifications", data.model_dump()
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update certifications"
            )
        
        return {"message": "Certifications updated successfully", "data": result}
        
    except Exception as e:
        logger.error(f"Error updating certifications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update certifications"
        )

async def add_single_certification(
    data: Certification,
    current_user: dict = Depends(get_current_user)
):
    """Add a single certification"""
    try:
        db = await get_database()
        user_id = current_user["id"]
        
        # Generate ID if not present
        if not data.id:
            data.id = f"cert_{user_id}_{int(datetime.now().timestamp())}"
        
        result = await user_model.add_profile_item(db, user_id, "certifications", data.model_dump())
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to add certification"
            )
        
        return {"message": "Certification added successfully", "data": data}
        
    except Exception as e:
        logger.error(f"Error adding certification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add certification"
        )

async def delete_certification(
    item_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a certification"""
    try:
        db = await get_database()
        user_id = current_user["id"]
        
        result = await user_model.delete_profile_item(db, user_id, "certifications", item_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete certification"
            )
        
        return {"message": "Certification deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting certification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete certification"
        )

async def update_interests(
    data: InterestsUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update interests"""
    try:
        db = await get_database()
        user_id = current_user["id"]
        
        result = await user_model.update_profile_section(
            db, user_id, "interests", data.model_dump()
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update interests"
            )
        
        return {"message": "Interests updated successfully", "data": result}
        
    except Exception as e:
        logger.error(f"Error updating interests: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update interests"
        )

async def update_social_links(
    data: SocialLinksUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update social links"""
    try:
        db = await get_database()
        user_id = current_user["id"]
        
        result = await user_model.update_profile_section(
            db, user_id, "social_links", data.model_dump()
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update social links"
            )
        
        return {"message": "Social links updated successfully", "data": result}
        
    except Exception as e:
        logger.error(f"Error updating social links: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update social links"
        )

async def upload_profile_photo(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload profile picture"""
    try:
        db = await get_database()
        user_id = current_user["id"]
        
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only image files are allowed"
            )
        
        # Save file
        file_url = await save_uploaded_file(file, f"profiles/{user_id}/profile")
        
        # Update user profile
        result = await user_model.update_profile_section(
            db, user_id, "photos", {"profile_picture": file_url}
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update profile picture"
            )
        
        return {
            "message": "Profile picture updated successfully",
            "url": file_url
        }
        
    except Exception as e:
        logger.error(f"Error uploading profile photo: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload profile picture"
        )

async def upload_cover_photo(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload cover photo"""
    try:
        db = await get_database()
        user_id = current_user["id"]
        
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only image files are allowed"
            )
        
        # Save file
        file_url = await save_uploaded_file(file, f"profiles/{user_id}/cover")
        
        # Update user profile
        result = await user_model.update_profile_section(
            db, user_id, "photos", {"cover_photo": file_url}
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update cover photo"
            )
        
        return {
            "message": "Cover photo updated successfully",
            "url": file_url
        }
        
    except Exception as e:
        logger.error(f"Error uploading cover photo: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload cover photo"
        )
