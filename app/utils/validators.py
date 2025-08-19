import re
import html

def validate_email(email):
    """Validate email format"""
    if not email or not isinstance(email, str):
        return False
    
    # Basic email validation pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))

def validate_username(username):
    """Validate username format"""
    if not username or not isinstance(username, str):
        return False
    
    # Username should be alphanumeric (with underscores) and between 3-20 characters
    username = username.strip()
    if len(username) < 3 or len(username) > 20:
        return False
    
    # Only allow letters, numbers, and underscores
    pattern = r'^[a-zA-Z0-9_]+$'
    return bool(re.match(pattern, username))

def validate_password(password):
    """Validate password strength"""
    if not password or not isinstance(password, str):
        return False
    
    # Minimum 8 characters
    if len(password) < 8:
        return False
    
    # At least one lowercase, one uppercase, one number
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    
    return has_lower and has_upper and has_digit

def validate_full_name(full_name):
    """Validate full name"""
    if not full_name or not isinstance(full_name, str):
        return False
    
    full_name = full_name.strip()
    if len(full_name) < 2 or len(full_name) > 50:
        return False
    
    # Only allow letters, spaces, hyphens, and apostrophes
    pattern = r"^[a-zA-Z\s\-']+$"
    return bool(re.match(pattern, full_name))

def sanitize_string(text):
    """Sanitize string input by removing potential harmful content"""
    if not text or not isinstance(text, str):
        return ""
    
    # HTML escape to prevent XSS
    sanitized = html.escape(text)
    
    # Remove script tags (double safety)
    sanitized = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', sanitized, flags=re.IGNORECASE)
    
    # Remove other potentially dangerous tags
    sanitized = re.sub(r'<[^>]*>', '', sanitized)
    
    # Remove excessive whitespace
    sanitized = re.sub(r'\s+', ' ', sanitized)
    
    return sanitized.strip()

def sanitize_input_dict(data):
    """Sanitize dictionary inputs"""
    if not isinstance(data, dict):
        return {}
    
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_string(value)
        elif isinstance(value, (int, float, bool)):
            sanitized[key] = value
        elif isinstance(value, dict):
            sanitized[key] = sanitize_input_dict(value)
        elif isinstance(value, list):
            sanitized[key] = [sanitize_string(item) if isinstance(item, str) else item for item in value]
        else:
            sanitized[key] = value
    
    return sanitized
