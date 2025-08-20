# Admin User Creation - Security Documentation

## Overview

This document describes the secure admin user creation system implemented for the Gulf Return Social Media API. The system allows for the creation of administrator users with elevated privileges using a secret key authentication mechanism.

## Security Features

### 1. Admin Secret Key Protection

- **Environment Variable**: `ADMIN_SECRET` must be set in the environment
- **Access Control**: Only requests with the correct admin secret can create admin users
- **Error Handling**: Invalid secrets return HTTP 403 Forbidden with generic error message
- **No Secret Exposure**: Admin secret is never logged or returned in responses

### 2. User Data Validation

- **Email Validation**: Standard email format validation
- **Username Requirements**: 3-20 characters, alphanumeric with underscores
- **Password Strength**: Minimum 8 characters with uppercase, lowercase, and numbers
- **Full Name Validation**: 2-50 characters, letters, spaces, hyphens, and apostrophes only
- **Duplicate Prevention**: No duplicate emails or usernames allowed

### 3. Admin User Properties

- **Role Assignment**: Automatically assigned "admin" role
- **Email Verification**: Admin users are automatically email verified
- **Password Security**: Passwords are hashed using bcrypt before storage
- **Audit Trail**: Creation timestamp and user tracking

## API Endpoint

### Create Admin User

```
POST /api/v1/auth/create-admin
```

#### Request Body

```json
{
  "admin_secret": "your-admin-secret-key-change-in-production-gulf-return-2025",
  "email": "admin@company.com",
  "username": "admin_user",
  "password": "AdminPass123",
  "full_name": "System Administrator",
  "bio": "System Administrator"
}
```

#### Success Response (HTTP 201)

```json
{
  "message": "Admin user created successfully. Total admin users: 1",
  "user": {
    "id": "64f8a7b2c1d2e3f4a5b6c7d8",
    "email": "admin@company.com",
    "username": "admin_user",
    "full_name": "System Administrator",
    "bio": "System Administrator",
    "role": "admin",
    "status": "active",
    "email_verified": true,
    "created_at": "2025-08-20T05:20:00.000000",
    "updated_at": "2025-08-20T05:20:00.000000"
  }
}
```

#### Error Responses

**Invalid Admin Secret (HTTP 403)**

```json
{
  "detail": "Invalid admin secret key"
}
```

**Duplicate User (HTTP 409)**

```json
{
  "detail": "User with this email or username already exists"
}
```

**Validation Error (HTTP 422)**

```json
{
  "detail": [
    {
      "loc": ["password"],
      "msg": "Password must be at least 8 characters with uppercase, lowercase and numbers",
      "type": "value_error"
    }
  ]
}
```

## Implementation Details

### 1. Database Structure

Admin users are stored in the same `users` collection with:

- `role`: "admin"
- `email_verified`: true (automatically set)
- `status`: "active"
- Standard user fields with enhanced privileges

### 2. Permissions System

The admin role is integrated with a comprehensive permissions system:

- **require_admin()**: Dependency for admin-only endpoints
- **require_admin_or_moderator()**: For elevated privilege endpoints
- **check_admin_permissions()**: Utility function for role checking
- **can_manage_user()**: Hierarchical user management permissions

### 3. Security Considerations

- Admin secret should be rotated regularly in production
- Admin users should use strong, unique passwords
- Consider implementing 2FA for admin accounts (future enhancement)
- Audit logging for admin user creation and actions
- Rate limiting to prevent brute force attacks

## Usage Examples

### Create First Admin User

```bash
curl -X POST "http://localhost:8000/api/v1/auth/create-admin" \
  -H "Content-Type: application/json" \
  -d '{
    "admin_secret": "your-admin-secret-key-change-in-production-gulf-return-2025",
    "email": "admin@company.com",
    "username": "superadmin",
    "password": "SuperSecure123",
    "full_name": "Super Administrator"
  }'
```

### Python Client Example

```python
import httpx

async def create_admin_user():
    admin_data = {
        "admin_secret": "your-admin-secret-key-change-in-production-gulf-return-2025",
        "email": "admin@company.com",
        "username": "admin_user",
        "password": "AdminPass123",
        "full_name": "System Administrator"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/auth/create-admin",
            json=admin_data
        )

        if response.status_code == 201:
            print("Admin user created successfully!")
            return response.json()
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
```

## Production Deployment

### Environment Variables

```bash
# Required - Change these in production!
ADMIN_SECRET=your-production-admin-secret-key-change-me-2025
SECRET_KEY=your-production-secret-key-change-me-2025

# Database
MONGODB_URI=mongodb://production-host:27017/gulf-return-prod

# Email (for admin notifications)
EMAIL=admin@company.com
EMAIL_PASSWORD=your-email-app-password
```

### Security Checklist

- [ ] Change default admin secret in production
- [ ] Use environment variables for all secrets
- [ ] Enable MongoDB authentication and SSL
- [ ] Implement rate limiting on admin endpoints
- [ ] Set up monitoring and alerting for admin user creation
- [ ] Regular security audits of admin accounts
- [ ] Document admin user management procedures

## Future Enhancements

1. **Two-Factor Authentication**: Add 2FA requirement for admin users
2. **Admin User Management**: Endpoints to list, update, and deactivate admin users
3. **Role-Based Permissions**: More granular permission system
4. **Audit Logging**: Comprehensive logging of admin actions
5. **Admin Dashboard**: Web interface for admin user management
6. **Session Management**: Advanced session control for admin users

## Testing

The admin user creation system includes comprehensive tests covering:

- Successful admin user creation
- Invalid admin secret rejection
- Duplicate user prevention
- Input validation (email, username, password, full name)
- Multiple admin user creation
- Edge cases and error handling

Run tests with:

```bash
python -m pytest app/tests/test_admin.py -v
```

## Support

For questions or issues related to admin user management:

1. Check the API logs for detailed error messages
2. Verify environment variables are set correctly
3. Ensure database connectivity
4. Review security best practices
5. Contact the development team for assistance

---

**Security Note**: This system is designed for initial admin setup and should be used carefully in production environments. Always follow security best practices and regularly audit admin user access.
