import os
import uuid
import aiofiles
from fastapi import UploadFile, HTTPException
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# File upload settings
UPLOAD_DIR = "static/uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}

async def save_uploaded_file(file: UploadFile, folder: str) -> str:
    """Save uploaded file and return the URL"""
    try:
        # Validate file size
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large")
        
        # Validate file type
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=400, detail="Invalid file type")
        
        # Create directory if it doesn't exist
        upload_path = os.path.join(UPLOAD_DIR, folder)
        os.makedirs(upload_path, exist_ok=True)
        
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(upload_path, unique_filename)
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(contents)
        
        # Return URL
        return f"/{file_path.replace(os.sep, '/')}"
        
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save file")

async def delete_file(file_path: str) -> bool:
    """Delete a file"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        return False

def get_file_url(file_path: str) -> str:
    """Convert file path to URL"""
    return f"/{file_path.replace(os.sep, '/')}"
