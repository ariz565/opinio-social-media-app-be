import os
from dotenv import load_dotenv
from functools import lru_cache

# Load environment variables
load_dotenv()

@lru_cache()
def get_settings():
    """Get application settings"""
    return {
        # API settings
        "API_V1_STR": "/api/v1",
        "PROJECT_NAME": "Gulf Return Social Media API",
        "VERSION": "1.0.0",
        
        # Security settings
        "SECRET_KEY": os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production"),
        "ALGORITHM": "HS256",
        "ACCESS_TOKEN_EXPIRE_MINUTES": int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
        "REFRESH_TOKEN_EXPIRE_DAYS": int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")),
        
        # MongoDB settings
        "MONGODB_URI": os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
        "MONGO_DB_NAME": os.getenv("MONGO_DB_NAME", "gulf-return"),
        
        # MongoDB connection settings
        "MONGODB_HOST": os.getenv("MONGODB_HOST", "localhost"),
        "MONGODB_PORT": int(os.getenv("MONGODB_PORT", "27017")),
        "MONGODB_DATABASE": os.getenv("MONGODB_DATABASE", "gulf-return"),
        "MONGODB_USERNAME": os.getenv("MONGODB_USERNAME"),
        "MONGODB_PASSWORD": os.getenv("MONGODB_PASSWORD"),
        "MONGODB_MAX_CONNECTIONS": int(os.getenv("MONGODB_MAX_CONNECTIONS", "100")),
        "MONGODB_MIN_CONNECTIONS": int(os.getenv("MONGODB_MIN_CONNECTIONS", "10")),
        "MONGODB_MAX_IDLE_TIME": int(os.getenv("MONGODB_MAX_IDLE_TIME", "60000")),
        
        # File upload settings
        "UPLOAD_DIR": os.getenv("UPLOAD_DIR", "uploads"),
        "MAX_UPLOAD_SIZE": int(os.getenv("MAX_UPLOAD_SIZE", "10485760")),  # 10MB
        
        # Email settings
        "EMAIL": os.getenv("EMAIL", ""),
        "EMAIL_PASSWORD": os.getenv("EMAIL_PASSWORD", ""),
        "SMTP_HOST": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "SMTP_PORT": int(os.getenv("SMTP_PORT", "587")),
        
        # Frontend URL for email links
        "FRONTEND_URL": os.getenv("FRONTEND_URL", "http://localhost:3000"),
        
        # Google OAuth settings
        "GOOGLE_CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID", "sample-google-client-id.apps.googleusercontent.com"),
        "GOOGLE_CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET", "sample-google-client-secret"),
        "GOOGLE_REDIRECT_URI": os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/auth/google/callback"),
        
        # Environment
        "ENVIRONMENT": os.getenv("ENVIRONMENT", "development"),
        "DEBUG": os.getenv("DEBUG", "True").lower() == "true"
    }
