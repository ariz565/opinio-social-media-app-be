from bson import ObjectId
from datetime import datetime
from typing import Any, Dict, List, Union

def serialize_mongo_object(obj: Any) -> Any:
    """Convert MongoDB objects to JSON-serializable format"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: serialize_mongo_object(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [serialize_mongo_object(item) for item in obj]
    else:
        return obj

def serialize_user(user: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize user object for API response"""
    if user is None:
        return None
    
    # Create a copy to avoid modifying the original
    serialized_user = user.copy()
    
    # Convert ObjectId to string
    if "_id" in serialized_user:
        serialized_user["id"] = str(serialized_user["_id"])
        del serialized_user["_id"]
    
    # Remove password if present
    if "password" in serialized_user:
        del serialized_user["password"]
    
    # Serialize other fields
    serialized_user = serialize_mongo_object(serialized_user)
    
    return serialized_user

def serialize_post(post: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize post object for API response"""
    if post is None:
        return None
    
    # Create a copy to avoid modifying the original
    serialized_post = post.copy()
    
    # Convert ObjectId to string
    if "_id" in serialized_post:
        serialized_post["id"] = str(serialized_post["_id"])
        del serialized_post["_id"]
    
    # Convert author_id to string
    if "author_id" in serialized_post:
        serialized_post["author_id"] = str(serialized_post["author_id"])
    
    # Serialize other fields
    serialized_post = serialize_mongo_object(serialized_post)
    
    return serialized_post

def serialize_comment(comment: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize comment object for API response"""
    if comment is None:
        return None
    
    # Create a copy to avoid modifying the original
    serialized_comment = comment.copy()
    
    # Convert ObjectId to string
    if "_id" in serialized_comment:
        serialized_comment["id"] = str(serialized_comment["_id"])
        del serialized_comment["_id"]
    
    # Convert foreign keys to string
    for field in ["author_id", "post_id", "parent_comment_id"]:
        if field in serialized_comment and serialized_comment[field]:
            serialized_comment[field] = str(serialized_comment[field])
    
    # Serialize other fields
    serialized_comment = serialize_mongo_object(serialized_comment)
    
    return serialized_comment

def create_success_response(message: str, data: Any = None) -> Dict[str, Any]:
    """Create a standardized success response"""
    response = {
        "success": True,
        "message": message
    }
    
    if data is not None:
        response["data"] = data
    
    return response

def create_error_response(message: str, details: Any = None) -> Dict[str, Any]:
    """Create a standardized error response"""
    response = {
        "success": False,
        "error": message
    }
    
    if details is not None:
        response["details"] = details
    
    return response
