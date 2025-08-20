from fastapi import APIRouter, HTTPException, status, Depends
from app.admin.schemas import (
    AdminLogin, AdminLoginResponse, AdminUserCreation, AdminUserResponse,
    AdminDashboardStats, UserManagementAction
)
from app.admin.auth_service import admin_login_service
from app.admin.management_service import (
    create_admin_user_service, get_admin_dashboard_stats, manage_user_action
)
from app.core.permissions import require_admin
from app.database.mongo_connection import get_database

router = APIRouter(prefix="/auth/admin", tags=["Admin"])


@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(login_data: AdminLogin):
    """
    Admin login endpoint with enhanced security
    
    Requires:
    - Valid admin email and password
    - Admin secret key for additional security
    - User must have admin role
    """
    db = await get_database()
    return await admin_login_service(
        db=db,
        email=login_data.email,
        password=login_data.password,
        admin_secret=login_data.admin_secret
    )


@router.post("/create-admin", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_user(admin_data: AdminUserCreation):
    """
    Create a new admin user
    
    This endpoint allows creation of admin users by providing the correct admin secret key.
    Admin users have elevated privileges and can access all application functionality.
    
    Security Features:
    - Requires valid admin secret key
    - All standard user validation applies
    - Admin users are automatically email verified
    - Role is automatically set to admin
    """
    db = await get_database()
    
    # Extract admin secret
    admin_secret = admin_data.admin_secret
    admin_dict = admin_data.dict()
    admin_dict.pop("admin_secret")  # Remove secret from user data
    
    return await create_admin_user_service(db, admin_dict, admin_secret)


@router.get("/dashboard/stats", response_model=AdminDashboardStats)
async def get_dashboard_stats(current_admin: dict = Depends(require_admin)):
    """
    Get admin dashboard statistics
    
    Returns:
    - Total users count
    - Total admins count  
    - Total posts count
    - Active users today
    - New registrations today
    - Flagged content count
    """
    db = await get_database()
    return await get_admin_dashboard_stats(db)


@router.post("/users/manage")
async def manage_user(
    action_data: UserManagementAction,
    current_admin: dict = Depends(require_admin)
):
    """
    Perform administrative actions on users
    
    Available actions:
    - suspend: Suspend user account
    - activate: Activate suspended account
    - delete: Soft delete user account
    - promote: Promote user role (user -> moderator -> admin)
    - demote: Demote user role (admin -> moderator -> user)
    """
    db = await get_database()
    return await manage_user_action(
        db=db,
        admin_user_id=current_admin["id"],
        target_user_id=action_data.user_id,
        action=action_data.action,
        reason=action_data.reason
    )


@router.get("/users")
async def list_all_users(
    page: int = 1,
    limit: int = 50,
    role: str = None,
    status: str = None,
    current_admin: dict = Depends(require_admin)
):
    """
    List all users with pagination and filtering
    
    Query Parameters:
    - page: Page number (default: 1)
    - limit: Items per page (default: 50, max: 100)
    - role: Filter by role (admin, moderator, user)
    - status: Filter by status (active, suspended, deleted)
    """
    db = await get_database()
    
    # Build filter
    filter_query = {}
    if role:
        filter_query["role"] = role
    if status:
        filter_query["status"] = status
    
    # Calculate skip
    skip = (page - 1) * limit
    limit = min(limit, 100)  # Max 100 items per page
    
    try:
        # Get users with pagination
        users_cursor = db.users.find(filter_query).skip(skip).limit(limit)
        users = await users_cursor.to_list(length=limit)
        
        # Remove passwords from response
        for user in users:
            user.pop("password", None)
            user["id"] = str(user["_id"])
            user.pop("_id", None)
        
        # Get total count
        total_count = await db.users.count_documents(filter_query)
        
        return {
            "users": users,
            "total": total_count,
            "page": page,
            "limit": limit,
            "total_pages": (total_count + limit - 1) // limit
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: str,
    current_admin: dict = Depends(require_admin)
):
    """Get detailed information about a specific user"""
    db = await get_database()
    
    from app.models.user import get_user_by_id
    user = await get_user_by_id(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Remove password and serialize
    user.pop("password", None)
    user["id"] = str(user["_id"])
    user.pop("_id", None)
    
    return {"user": user}
