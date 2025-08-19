from datetime import datetime, timedelta
from bson import ObjectId
import random
import string

# OTP types
OTP_TYPE_EMAIL_VERIFICATION = "email_verification"
OTP_TYPE_PASSWORD_RESET = "password_reset"

async def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

async def create_otp(db, email, otp_type=OTP_TYPE_EMAIL_VERIFICATION, user_id=None):
    """Create OTP for email address"""
    otp_code = await generate_otp()
    
    # OTP expires in 10 minutes for email verification, 15 minutes for password reset
    minutes = 15 if otp_type == OTP_TYPE_PASSWORD_RESET else 10
    expires_at = datetime.utcnow() + timedelta(minutes=minutes)
    
    otp_doc = {
        "email": email.lower(),
        "otp_code": otp_code,
        "otp_type": otp_type,
        "is_used": False,
        "created_at": datetime.utcnow(),
        "expires_at": expires_at
    }
    
    # Add user_id if provided
    if user_id:
        otp_doc["user_id"] = ObjectId(user_id) if isinstance(user_id, str) else user_id
    
    # Remove any existing OTPs for this email and type
    query = {
        "email": email.lower(),
        "otp_type": otp_type
    }
    await db.otps.delete_many(query)
    
    # Insert new OTP
    result = await db.otps.insert_one(otp_doc)
    
    return otp_code

async def verify_otp(db, email, otp_code, otp_type=OTP_TYPE_EMAIL_VERIFICATION):
    """Verify OTP code"""
    current_time = datetime.utcnow()
    
    # Find valid OTP
    otp_doc = await db.otps.find_one({
        "email": email.lower(),
        "otp_code": otp_code,
        "otp_type": otp_type,
        "is_used": False,
        "expires_at": {"$gt": current_time}
    })
    
    if not otp_doc:
        return None
    
    # Mark OTP as used
    await db.otps.update_one(
        {"_id": otp_doc["_id"]},
        {"$set": {"is_used": True}}
    )
    
    return otp_doc

async def cleanup_expired_otps(db):
    """Remove expired OTPs"""
    current_time = datetime.utcnow()
    
    result = await db.otps.delete_many({
        "expires_at": {"$lt": current_time}
    })
    
    return result.deleted_count

async def get_valid_otp(db, email, otp_type=OTP_TYPE_EMAIL_VERIFICATION):
    """Get valid OTP for user"""
    current_time = datetime.utcnow()
    
    return await db.otps.find_one({
        "email": email.lower(),
        "otp_type": otp_type,
        "is_used": False,
        "expires_at": {"$gt": current_time}
    })
