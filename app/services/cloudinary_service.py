import cloudinary
import cloudinary.uploader
import cloudinary.api
from fastapi import HTTPException, UploadFile
import asyncio
import functools
from typing import Dict, Any, Optional, List
import os
from io import BytesIO
from PIL import Image
import tempfile

from app.config import get_settings


class CloudinaryService:
    """Service for handling media uploads to Cloudinary"""
    
    def __init__(self):
        """Initialize Cloudinary configuration"""
        settings = get_settings()
        
        cloudinary.config(
            cloud_name=settings["CLOUDINARY_NAME"],
            api_key=settings["CLOUDINARY_KEY"],
            api_secret=settings["CLOUDINARY_SECRET"],
            secure=True
        )
        self.upload_folder = settings["CLOUDINARY_UPLOAD_FOLDER"]
    
    def _run_async(self, func, *args, **kwargs):
        """Run synchronous Cloudinary function in async context"""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(None, functools.partial(func, *args, **kwargs))
    
    async def upload_image(
        self,
        file: UploadFile,
        user_id: str,
        post_id: Optional[str] = None,
        max_width: int = 1920,
        max_height: int = 1080,
        quality: str = "auto"
    ) -> Dict[str, Any]:
        """
        Upload an image to Cloudinary with optimization
        
        Args:
            file: The uploaded file
            user_id: ID of the user uploading
            post_id: Optional post ID for organization
            max_width: Maximum width for resizing
            max_height: Maximum height for resizing
            quality: Image quality setting
            
        Returns:
            Dict containing upload result with URL and metadata
        """
        try:
            # Read file content
            contents = await file.read()
            
            # Validate file type
            if not file.content_type or not file.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="File must be an image")
            
            # Generate public ID
            folder_path = f"{self.upload_folder}/images/{user_id}"
            if post_id:
                folder_path += f"/{post_id}"
            
            public_id = f"{folder_path}/{file.filename.split('.')[0]}"
            
            # Upload to Cloudinary
            result = await self._run_async(
                cloudinary.uploader.upload,
                contents,
                public_id=public_id,
                folder=folder_path,
                resource_type="image",
                transformation=[
                    {"width": max_width, "height": max_height, "crop": "limit"},
                    {"quality": quality, "fetch_format": "auto"}
                ],
                overwrite=True
            )
            
            return {
                "public_id": result["public_id"],
                "url": result["secure_url"],
                "width": result["width"],
                "height": result["height"],
                "format": result["format"],
                "bytes": result["bytes"],
                "created_at": result["created_at"]
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")
    
    async def upload_video(
        self,
        file: UploadFile,
        user_id: str,
        post_id: Optional[str] = None,
        max_duration: int = 300  # 5 minutes
    ) -> Dict[str, Any]:
        """
        Upload a video to Cloudinary with optimization
        
        Args:
            file: The uploaded file
            user_id: ID of the user uploading
            post_id: Optional post ID for organization
            max_duration: Maximum video duration in seconds
            
        Returns:
            Dict containing upload result with URL and metadata
        """
        try:
            # Read file content
            contents = await file.read()
            
            # Validate file type
            if not file.content_type or not file.content_type.startswith('video/'):
                raise HTTPException(status_code=400, detail="File must be a video")
            
            # Generate public ID
            folder_path = f"{self.upload_folder}/videos/{user_id}"
            if post_id:
                folder_path += f"/{post_id}"
            
            public_id = f"{folder_path}/{file.filename.split('.')[0]}"
            
            # Upload to Cloudinary
            result = await self._run_async(
                cloudinary.uploader.upload,
                contents,
                public_id=public_id,
                folder=folder_path,
                resource_type="video",
                transformation=[
                    {"quality": "auto", "fetch_format": "auto"},
                    {"duration": f"lte_{max_duration}"}
                ],
                overwrite=True
            )
            
            return {
                "public_id": result["public_id"],
                "url": result["secure_url"],
                "width": result.get("width"),
                "height": result.get("height"),
                "format": result["format"],
                "bytes": result["bytes"],
                "duration": result.get("duration"),
                "created_at": result["created_at"]
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Video upload failed: {str(e)}")
    
    async def create_thumbnail(
        self,
        video_public_id: str,
        width: int = 300,
        height: int = 200
    ) -> str:
        """
        Create a thumbnail for a video
        
        Args:
            video_public_id: The public ID of the uploaded video
            width: Thumbnail width
            height: Thumbnail height
            
        Returns:
            URL of the generated thumbnail
        """
        try:
            # Generate thumbnail URL
            thumbnail_url = cloudinary.CloudinaryImage(video_public_id).build_url(
                width=width,
                height=height,
                crop="fill",
                quality="auto",
                fetch_format="auto",
                resource_type="video"
            )
            
            return thumbnail_url
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Thumbnail creation failed: {str(e)}")
    
    async def delete_media(self, public_id: str, resource_type: str = "image") -> bool:
        """
        Delete media from Cloudinary
        
        Args:
            public_id: The public ID of the media to delete
            resource_type: Type of resource (image, video, etc.)
            
        Returns:
            True if deletion was successful
        """
        try:
            result = await self._run_async(
                cloudinary.uploader.destroy,
                public_id,
                resource_type=resource_type
            )
            
            return result.get("result") == "ok"
            
        except Exception as e:
            print(f"Media deletion failed: {str(e)}")
            return False
    
    async def upload_multiple_images(
        self,
        files: List[UploadFile],
        user_id: str,
        post_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Upload multiple images concurrently
        
        Args:
            files: List of uploaded files
            user_id: ID of the user uploading
            post_id: Optional post ID for organization
            
        Returns:
            List of upload results
        """
        if len(files) > 10:  # Limit to 10 images per post
            raise HTTPException(status_code=400, detail="Maximum 10 images allowed per post")
        
        # Upload all images concurrently
        upload_tasks = [
            self.upload_image(file, user_id, post_id)
            for file in files
        ]
        
        results = await asyncio.gather(*upload_tasks, return_exceptions=True)
        
        # Filter out exceptions and return successful uploads
        successful_uploads = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Failed to upload file {files[i].filename}: {str(result)}")
            else:
                successful_uploads.append(result)
        
        return successful_uploads
    
    def get_optimized_url(
        self,
        public_id: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        quality: str = "auto",
        format: str = "auto"
    ) -> str:
        """
        Get optimized URL for an image
        
        Args:
            public_id: The public ID of the image
            width: Optional width for resizing
            height: Optional height for resizing
            quality: Image quality setting
            format: Image format
            
        Returns:
            Optimized image URL
        """
        transformations = [{"quality": quality, "fetch_format": format}]
        
        if width or height:
            transformations.append({
                "width": width,
                "height": height,
                "crop": "limit"
            })
        
        return cloudinary.CloudinaryImage(public_id).build_url(
            transformation=transformations
        )


# Create global instance
cloudinary_service = CloudinaryService()
