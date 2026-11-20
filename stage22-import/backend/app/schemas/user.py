"""
Nexus ERP - Pydantic Schemas for Users and Authentication
=========================================================

This module defines Pydantic schemas for request/response validation
and serialization of user and authentication related data.

Features:
- Input validation with detailed error messages
- Output serialization with controlled exposure
- Nested schema support for complex data
- Type-safe API contracts
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
    ConfigDict,
)
from uuid import UUID
import re


# ========================================
# Base Configuration
# ========================================

class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )


# ========================================
# Token Schemas
# ========================================

class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str = Field(
        ...,
        description="JWT access token"
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token"
    )
    token_type: str = Field(
        default="bearer",
        description="Token type"
    )
    expires_in: int = Field(
        ...,
        description="Token expiration time in seconds"
    )
    user: "UserBriefResponse" = Field(
        ...,
        description="Brief user information"
    )


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str = Field(
        ...,
        description="Refresh token to exchange for new access token"
    )


class TokenVerifyRequest(BaseModel):
    """Schema for token verification request."""
    token: str = Field(..., description="Token to verify")


class TokenVerifyResponse(BaseModel):
    """Schema for token verification response."""
    valid: bool = Field(..., description="Whether token is valid")
    user_id: Optional[str] = Field(None, description="User ID if valid")
    expires_at: Optional[datetime] = Field(None, description="Token expiration")


# ========================================
# Login Schemas
# ========================================

class LoginRequest(BaseModel):
    """Schema for login request."""
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Username or email"
    )
    password: str = Field(
        ...,
        min_length=1,
        description="User password"
    )
    remember_me: bool = Field(
        default=False,
        description="Whether to extend session duration"
    )
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        return v.lower().strip()


class LoginResponse(BaseModel):
    """Schema for login response."""
    success: bool = Field(..., description="Login success status")
    message: str = Field(..., description="Login message")
    token: Optional[TokenResponse] = Field(
        None,
        description="Token information if login successful"
    )
    requires_2fa: bool = Field(
        default=False,
        description="Whether 2FA is required"
    )


class LogoutResponse(BaseModel):
    """Schema for logout response."""
    success: bool = Field(default=True, description="Logout success status")
    message: str = Field(default="Successfully logged out")


# ========================================
# User Schemas
# ========================================

class UserBriefResponse(BaseSchema):
    """Brief user information for nested responses."""
    id: UUID
    email: str
    username: str
    first_name: str
    last_name: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    status: str
    is_superuser: bool = False


class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr = Field(
        ...,
        description="User email address"
    )
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Unique username"
    )
    first_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User first name"
    )
    last_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User last name"
    )
    phone: Optional[str] = Field(
        None,
        max_length=20,
        description="Phone number"
    )
    job_title: Optional[str] = Field(
        None,
        max_length=100,
        description="Job title"
    )
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        return v.lower()


class UserCreate(UserBase):
    """Schema for user creation."""
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User password"
    )
    confirm_password: str = Field(
        ...,
        description="Password confirmation"
    )
    tenant_id: Optional[UUID] = Field(
        None,
        description="Tenant ID (for multi-tenant)"
    )
    role_ids: List[UUID] = Field(
        default_factory=list,
        description="List of role IDs to assign"
    )
    send_welcome_email: bool = Field(
        default=True,
        description="Whether to send welcome email"
    )
    
    @model_validator(mode='after')
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self


class UserUpdate(BaseModel):
    """Schema for user update."""
    email: Optional[EmailStr] = Field(None, description="Email address")
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    mobile: Optional[str] = Field(None, max_length=20, description="Mobile number")
    job_title: Optional[str] = Field(None, max_length=100, description="Job title")
    department_id: Optional[UUID] = Field(None, description="Department ID")
    language: Optional[str] = Field(None, max_length=10, description="Language code")
    timezone: Optional[str] = Field(None, max_length=50, description="Timezone")
    avatar_url: Optional[str] = Field(None, max_length=500, description="Avatar URL")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")


class UserPasswordChange(BaseModel):
    """Schema for password change."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password"
    )
    confirm_password: str = Field(..., description="Confirm new password")
    
    @model_validator(mode='after')
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self


class UserPasswordReset(BaseModel):
    """Schema for password reset request."""
    email: EmailStr = Field(..., description="Email address for reset")


class UserPasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""
    token: str = Field(..., description="Reset token")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password"
    )
    confirm_password: str = Field(..., description="Confirm new password")
    
    @model_validator(mode='after')
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self


class UserResponse(UserBriefResponse):
    """Full user response schema."""
    mobile: Optional[str] = None
    job_title: Optional[str] = None
    department_id: Optional[UUID] = None
    language: str = "en"
    timezone: str = "UTC"
    email_verified: bool = False
    phone_verified: bool = False
    two_factor_enabled: bool = False
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    roles: List["RoleBriefResponse"] = Field(default_factory=list)


class UserListResponse(BaseModel):
    """Schema for paginated user list."""
    items: List[UserResponse]
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")


# ========================================
# Role Schemas
# ========================================

class RoleBriefResponse(BaseSchema):
    """Brief role information for nested responses."""
    id: UUID
    code: str
    name: str
    is_system: bool = False


class RoleBase(BaseModel):
    """Base role schema."""
    code: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Unique role code"
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Role display name"
    )
    description: Optional[str] = Field(None, description="Role description")
    parent_id: Optional[UUID] = Field(None, description="Parent role ID")
    priority: int = Field(default=0, description="Role priority")


class RoleCreate(RoleBase):
    """Schema for role creation."""
    permission_ids: List[UUID] = Field(
        default_factory=list,
        description="List of permission IDs to assign"
    )


class RoleUpdate(BaseModel):
    """Schema for role update."""
    name: Optional[str] = Field(None, max_length=100, description="Role name")
    description: Optional[str] = Field(None, description="Role description")
    is_active: Optional[bool] = Field(None, description="Whether role is active")
    parent_id: Optional[UUID] = Field(None, description="Parent role ID")
    priority: Optional[int] = Field(None, description="Role priority")


class RoleResponse(RoleBriefResponse):
    """Full role response schema."""
    description: Optional[str] = None
    is_active: bool = True
    parent_id: Optional[UUID] = None
    priority: int = 0
    created_at: datetime
    updated_at: datetime
    permissions: List["PermissionBriefResponse"] = Field(default_factory=list)


class RoleListResponse(BaseModel):
    """Schema for role list."""
    items: List[RoleResponse]
    total: int


# ========================================
# Permission Schemas
# ========================================

class PermissionBriefResponse(BaseSchema):
    """Brief permission information."""
    id: UUID
    code: str
    name: str
    module: str
    action: str


class PermissionResponse(PermissionBriefResponse):
    """Full permission response schema."""
    description: Optional[str] = None
    resource: str
    scope: str
    conditions: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class PermissionListResponse(BaseModel):
    """Schema for permission list."""
    items: List[PermissionResponse]
    total: int


# ========================================
# Session Schemas
# ========================================

class SessionResponse(BaseSchema):
    """Schema for user session."""
    id: UUID
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_type: Optional[str] = None
    device_name: Optional[str] = None
    location: Optional[str] = None
    is_active: bool
    expires_at: datetime
    last_activity_at: datetime
    created_at: datetime


class SessionListResponse(BaseModel):
    """Schema for session list."""
    items: List[SessionResponse]
    total: int


# ========================================
# Activity Log Schemas
# ========================================

class ActivityLogResponse(BaseSchema):
    """Schema for activity log."""
    id: UUID
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[UUID] = None
    description: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime


class ActivityLogListResponse(BaseModel):
    """Schema for activity log list."""
    items: List[ActivityLogResponse]
    total: int
    page: int
    page_size: int


# ========================================
# User Assignment Schemas
# ========================================

class UserRoleAssign(BaseModel):
    """Schema for assigning roles to user."""
    role_ids: List[UUID] = Field(..., description="Role IDs to assign")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")


class UserRoleRemove(BaseModel):
    """Schema for removing roles from user."""
    role_ids: List[UUID] = Field(..., description="Role IDs to remove")


# Update forward references
TokenResponse.model_rebuild()
UserResponse.model_rebuild()
RoleResponse.model_rebuild()
