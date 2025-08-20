"""
Custom exceptions for the Gulf Return Social Media API
"""

class APIException(Exception):
    """Base API exception"""
    def __init__(self, message: str = "An error occurred"):
        self.message = message
        super().__init__(self.message)

class ValidationError(APIException):
    """Raised when validation fails"""
    pass

class UnauthorizedError(APIException):
    """Raised when user is not authorized"""
    pass

class PostNotFoundError(APIException):
    """Raised when post is not found"""
    pass

class UserNotFoundError(APIException):
    """Raised when user is not found"""
    pass

class ContentModerationError(APIException):
    """Raised when content violates community guidelines"""
    pass

class DuplicateResourceError(APIException):
    """Raised when trying to create a duplicate resource"""
    pass

class RateLimitExceededError(APIException):
    """Raised when rate limit is exceeded"""
    pass

class DatabaseError(APIException):
    """Raised when database operation fails"""
    pass

class MediaUploadError(APIException):
    """Raised when media upload fails"""
    pass

class EmailServiceError(APIException):
    """Raised when email service fails"""
    pass

class TokenExpiredError(APIException):
    """Raised when token has expired"""
    pass

class InvalidTokenError(APIException):
    """Raised when token is invalid"""
    pass

class InsufficientPermissionsError(APIException):
    """Raised when user lacks required permissions"""
    pass

class AccountNotVerifiedError(APIException):
    """Raised when account is not verified"""
    pass

class AccountSuspendedError(APIException):
    """Raised when account is suspended"""
    pass
