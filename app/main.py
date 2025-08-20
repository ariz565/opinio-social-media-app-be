from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import logging

from app.routes import router
from app.admin.routes import router as admin_router
from app.database.mongo_connection import connect_to_mongo, close_mongo_connection
from app.config import get_settings
from app.core.middleware import LoggingMiddleware, RateLimitMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()

# Create FastAPI app
app = FastAPI(
    title="Gulf Return Social Media API",
    description="A comprehensive social media backend API for Gulf Return platform",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure properly for production
)

app.add_middleware(LoggingMiddleware)
# app.add_middleware(RateLimitMiddleware)  # Commented out for now

# Include routes
app.include_router(router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "Gulf Return Social Media API is running!",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """API health check endpoint"""
    return {
        "status": "healthy",
        "message": "Gulf Return Social Media API is running",
        "version": "1.0.0"
    }

@app.get("/health/db")
async def database_health_check():
    """Database health check endpoint"""
    from app.database.mongo_connection import MongoConnectionManager
    try:
        manager = MongoConnectionManager()
        health_status = await manager.health_check()
        return health_status
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": "Database connection failed",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )