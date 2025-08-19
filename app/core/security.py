from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from app.config import get_settings

# Get settings
settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    """Create password hash from plain text password"""
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    """Verify plain text password against hashed password"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data, expires_delta=None):
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings["ACCESS_TOKEN_EXPIRE_MINUTES"])
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings["SECRET_KEY"], algorithm=settings["ALGORITHM"])
    
    return encoded_jwt

def create_refresh_token(data):
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings["REFRESH_TOKEN_EXPIRE_DAYS"])
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings["SECRET_KEY"], algorithm=settings["ALGORITHM"])
    
    return encoded_jwt

def decode_token(token):
    """Decode JWT token"""
    try:
        payload = jwt.decode(token, settings["SECRET_KEY"], algorithms=[settings["ALGORITHM"]])
        return payload
    except jwt.JWTError:
        return None
