"""
Nexus ERP - Authentication API Endpoints
========================================

This module provides authentication-related API endpoints including:
- User login with JWT token generation
- Token refresh
- Logout with token invalidation
- Password management
- Session management
"""

from datetime import datetime, timedelta
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request,
    BackgroundTasks,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional
from uuid import UUID
import logging

from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    token_blacklist,
    validate_password_strength,
    generate_password_reset_token,
    verify_password_reset_token,
    get_current_user,
    get_token_hash,
)
from app.core.config import settings
from app.models.user import User, UserSession, UserStatus, UserActivityLog
from app.schemas.user import (
    LoginRequest,
    LoginResponse,
    TokenResponse,
    TokenRefreshRequest,
    LogoutResponse,
    UserPasswordChange,
    UserPasswordReset,
    UserPasswordResetConfirm,
    UserBriefResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


# ========================================
# Login Endpoint
# ========================================

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="User Login",
    description="Authenticate user and return JWT tokens",
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials"},
        403: {"description": "Account locked or inactive"},
    }
)
async def login(
    request: Request,
    login_data: LoginRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user and generate JWT tokens.
    
    - **username**: Username or email address
    - **password**: User password
    - **remember_me**: Extend session duration if true
    """
    # Find user by username or email
    result = await db.execute(
        select(User).where(
            and_(
                User.is_deleted == False,
                (User.username == login_data.username.lower()) | 
                (User.email == login_data.username.lower())
            )
        )
    )
    user = result.scalar_one_or_none()
    
    # User not found
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if account is locked
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is temporarily locked. Please try again later.",
        )
    
    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact administrator.",
        )
    
    # Verify password
    if not verify_password(login_data.password, user.password_hash):
        # Increment failed login attempts
        user.failed_login_count += 1
        
        # Lock account after 5 failed attempts
        if user.failed_login_count >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=30)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account locked due to too many failed attempts.",
            )
        
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user roles and permissions
    roles = [role.code for role in user.roles]
    permissions = []
    for role in user.roles:
        permissions.extend(role.get_all_permissions())
    permissions = list(set(permissions))
    
    # Create tokens
    access_token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        tenant_id=str(user.tenant_id),
        roles=roles,
        permissions=permissions,
        expires_delta=timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 
            (24 if login_data.remember_me else 1)
        )
    )
    
    refresh_token = create_refresh_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        expires_delta=timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS * 
            (7 if login_data.remember_me else 1)
        )
    )
    
    # Create session record
    session = UserSession(
        user_id=user.id,
        token_hash=get_token_hash(access_token),
        refresh_token_hash=get_token_hash(refresh_token),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", ""),
        device_type=_detect_device_type(request.headers.get("user-agent", "")),
        expires_at=datetime.utcnow() + timedelta(days=7 if login_data.remember_me else 1),
    )
    db.add(session)
    
    # Update user login info
    user.last_login_at = datetime.utcnow()
    user.last_login_ip = request.client.host if request.client else None
    user.login_count += 1
    user.failed_login_count = 0
    
    # Log activity
    activity = UserActivityLog(
        user_id=user.id,
        action="login",
        description="User logged in successfully",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", ""),
    )
    db.add(activity)
    
    await db.commit()
    
    # Build response
    token_response = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserBriefResponse.model_validate(user),
    )
    
    return LoginResponse(
        success=True,
        message="Login successful",
        token=token_response,
    )


# ========================================
# Token Refresh Endpoint
# ========================================

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh Access Token",
)
async def refresh_token(
    token_data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using refresh token."""
    try:
        payload = decode_token(token_data.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )
    
    user_id = payload.get("sub")
    
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_deleted == False)
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    
    roles = [role.code for role in user.roles]
    permissions = []
    for role in user.roles:
        permissions.extend(role.get_all_permissions())
    permissions = list(set(permissions))
    
    access_token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        tenant_id=str(user.tenant_id),
        roles=roles,
        permissions=permissions,
    )
    
    new_refresh_token = create_refresh_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserBriefResponse.model_validate(user),
    )


# ========================================
# Logout Endpoint
# ========================================

@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="User Logout",
)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Logout user and invalidate tokens."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        token_blacklist.add_token(token)
    
    result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == current_user.id,
            UserSession.is_active == True
        )
    )
    sessions = result.scalars().all()
    
    for session in sessions:
        session.is_active = False
    
    activity = UserActivityLog(
        user_id=current_user.id,
        action="logout",
        description="User logged out",
        ip_address=request.client.host if request.client else None,
    )
    db.add(activity)
    
    await db.commit()
    
    return LogoutResponse(success=True, message="Successfully logged out")


# ========================================
# Password Management
# ========================================

@router.post(
    "/password/change",
    summary="Change Password",
)
async def change_password(
    password_data: UserPasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change user password."""
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    
    validation = validate_password_strength(password_data.new_password)
    if not validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": validation["errors"]},
        )
    
    current_user.password_hash = get_password_hash(password_data.new_password)
    current_user.password_changed_at = datetime.utcnow()
    current_user.must_change_password = False
    
    await db.commit()
    
    return {"success": True, "message": "Password changed successfully"}


@router.post(
    "/password/reset",
    summary="Request Password Reset",
)
async def request_password_reset(
    reset_data: UserPasswordReset,
    db: AsyncSession = Depends(get_db),
):
    """Request password reset email."""
    result = await db.execute(
        select(User).where(User.email == reset_data.email, User.is_deleted == False)
    )
    user = result.scalar_one_or_none()
    
    if user:
        reset_token = generate_password_reset_token(user.email)
        logger.info(f"Password reset requested for user: {user.email}")
    
    return {
        "success": True,
        "message": "If the email exists, a password reset link has been sent."
    }


# ========================================
# Helper Functions
# ========================================

def _detect_device_type(user_agent: str) -> str:
    """Detect device type from user agent."""
    user_agent = user_agent.lower()
    if "mobile" in user_agent or "android" in user_agent or "iphone" in user_agent:
        return "mobile"
    elif "tablet" in user_agent or "ipad" in user_agent:
        return "tablet"
    return "desktop"
