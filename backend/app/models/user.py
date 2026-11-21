"""
Nexus ERP - User and RBAC Models
=================================

This module implements a comprehensive Role-Based Access Control (RBAC) system
with the following features:

Features:
- User management with secure password storage
- Role-based permissions
- Hierarchical roles (roles can inherit from other roles)
- Fine-grained permissions (module, action, resource level)
- Multi-tenant user isolation
- User sessions and activity tracking
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    UniqueConstraint,
    Index,
    Enum as SQLEnum,
    CheckConstraint,
    Integer,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional, List
import enum
import uuid

from app.models.base import BaseModel, TenantMixin


class UserStatus(str, enum.Enum):
    """User account status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class PermissionScope(str, enum.Enum):
    """Permission scope levels."""
    GLOBAL = "global"          # All tenants (super admin only)
    TENANT = "tenant"          # Within tenant
    DEPARTMENT = "department"  # Within department
    OWN = "own"                # Own records only


class User(BaseModel, TenantMixin):
    __allow_unmapped__ = True
    """
    User Model
    
    Represents a system user with authentication and authorization capabilities.
    Supports multiple authentication methods and comprehensive profile management.
    """
    
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email_tenant", "email", "tenant_id", unique=True),
        Index("ix_users_username_tenant", "username", "tenant_id", unique=True),
        Index("ix_users_status", "status"),
        CheckConstraint(
            "length(password_hash) >= 60",
            name="ck_users_password_length"
        ),
        {"schema": None}  # Will be set dynamically for multi-tenancy
    )
    
    # ========================================
    # Authentication Fields
    # ========================================
    email: str = Column(
        String(255),
        nullable=False,
        index=True,
        doc="User email address - used for login and notifications"
    )
    
    username: str = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Unique username for login"
    )
    
    password_hash: str = Column(
        String(255),
        nullable=False,
        doc="Bcrypt hashed password"
    )
    
    # ========================================
    # Profile Fields
    # ========================================
    first_name: str = Column(
        String(100),
        nullable=False,
        doc="User first name"
    )
    
    last_name: str = Column(
        String(100),
        nullable=False,
        doc="User last name"
    )
    
    full_name: Optional[str] = Column(
        String(201),
        nullable=True,
        doc="Full name (computed or custom)"
    )
    
    avatar_url: Optional[str] = Column(
        String(500),
        nullable=True,
        doc="URL to user avatar image"
    )
    
    phone: Optional[str] = Column(
        String(20),
        nullable=True,
        doc="User phone number"
    )
    
    mobile: Optional[str] = Column(
        String(20),
        nullable=True,
        doc="User mobile number"
    )
    
    job_title: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="User job title/position"
    )
    
    department_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        doc="Reference to user's department"
    )
    
    # ========================================
    # Status and Settings
    # ========================================
    status: UserStatus = Column(
        SQLEnum(UserStatus),
        default=UserStatus.PENDING_VERIFICATION,
        nullable=False,
        doc="Current account status"
    )
    
    is_superuser: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Superuser flag - bypasses all permission checks"
    )
    
    is_staff: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Staff flag - can access admin interface"
    )
    
    email_verified: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether email has been verified"
    )
    
    phone_verified: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether phone has been verified"
    )
    
    two_factor_enabled: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether 2FA is enabled"
    )
    
    two_factor_secret: Optional[str] = Column(
        String(32),
        nullable=True,
        doc="TOTP secret for 2FA"
    )
    
    # ========================================
    # Locale and Preferences
    # ========================================
    language: str = Column(
        String(10),
        default="en",
        nullable=False,
        doc="User preferred language code (ISO 639-1)"
    )
    
    timezone: str = Column(
        String(50),
        default="UTC",
        nullable=False,
        doc="User timezone (IANA format)"
    )
    
    preferences: dict = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="User preferences and settings as JSON"
    )
    
    # ========================================
    # OAuth Integration
    # ========================================
    oauth_provider: Optional[str] = Column(
        String(50),
        nullable=True,
        doc="OAuth provider name (google, microsoft, etc.)"
    )
    
    oauth_provider_id: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="User ID from OAuth provider"
    )
    
    # ========================================
    # Session Tracking
    # ========================================
    last_login_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of last successful login"
    )
    
    last_login_ip: Optional[str] = Column(
        String(45),
        nullable=True,
        doc="IP address of last login"
    )
    
    login_count: int = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total number of successful logins"
    )
    
    failed_login_count: int = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Consecutive failed login attempts"
    )
    
    locked_until: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Account locked until this timestamp"
    )
    
    password_changed_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When password was last changed"
    )
    
    must_change_password: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether user must change password on next login"
    )
    
    # ========================================
    # Relationships
    # ========================================
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary="user_roles",
        primaryjoin="User.id == UserRole.user_id",
        secondaryjoin="Role.id == UserRole.role_id",
        back_populates="users",
        lazy="selectin",
        doc="Roles assigned to this user"
    )
    
    sessions: Mapped[List["UserSession"]] = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
        doc="Active sessions for this user"
    )
    
    activity_logs: Mapped[List["UserActivityLog"]] = relationship(
        "UserActivityLog",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
        doc="Activity history for this user"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="user", lazy="dynamic"
    )
    
    @property
    def display_name(self) -> str:
        """Get the user's display name."""
        return self.full_name or f"{self.first_name} {self.last_name}"
    
    @property
    def is_active(self) -> bool:
        """Check if user account is active."""
        return self.status == UserStatus.ACTIVE and not self.is_deleted
    
    @property
    def is_locked(self) -> bool:
        """Check if account is currently locked."""
        if self.locked_until:
            return datetime.utcnow() < self.locked_until
        return False
    
    def has_permission(self, permission_code: str) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            permission_code: Permission code to check (e.g., 'sales.invoice.create')
            
        Returns:
            True if user has the permission
        """
        if self.is_superuser:
            return True
        
        for role in self.roles:
            if role.has_permission(permission_code):
                return True
        return False
    
    def has_role(self, role_code: str) -> bool:
        """
        Check if user has a specific role.
        
        Args:
            role_code: Role code to check
            
        Returns:
            True if user has the role
        """
        return any(role.code == role_code for role in self.roles)


class Role(BaseModel, TenantMixin):
    """
    Role Model
    
    Represents a collection of permissions that can be assigned to users.
    Supports hierarchical roles through parent relationship.
    """
    
    __tablename__ = "roles"
    __table_args__ = (
        Index("ix_roles_code_tenant", "code", "tenant_id", unique=True),
        CheckConstraint(
            "length(code) >= 2",
            name="ck_roles_code_length"
        ),
    )
    
    # ========================================
    # Role Fields
    # ========================================
    code: str = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Unique role code (e.g., 'sales_manager')"
    )
    
    name: str = Column(
        String(100),
        nullable=False,
        doc="Human-readable role name"
    )
    
    description: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Role description"
    )
    
    is_system: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="System roles cannot be deleted"
    )
    
    is_active: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether role is active"
    )
    
    parent_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=True,
        doc="Parent role for inheritance"
    )
    
    priority: int = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Role priority for conflict resolution"
    )
    
    # ========================================
    # Relationships
    # ========================================
    users: Mapped[List["User"]] = relationship(
        "User",
        secondary="user_roles",
        primaryjoin="Role.id == UserRole.role_id",
        secondaryjoin="User.id == UserRole.user_id",
        back_populates="roles",
        lazy="dynamic",
        doc="Users assigned to this role"
    )
    
    permissions: Mapped[List["Permission"]] = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
        lazy="selectin",
        doc="Permissions granted by this role"
    )
    
    parent: Mapped[Optional["Role"]] = relationship(
        "Role",
        remote_side="Role.id",
        backref="children",
        lazy="selectin",
        doc="Parent role for inheritance"
    )
    
    def has_permission(self, permission_code: str) -> bool:
        """
        Check if role grants a specific permission.
        
        Also checks parent roles for inheritance.
        
        Args:
            permission_code: Permission code to check
            
        Returns:
            True if role grants the permission
        """
        # Check direct permissions
        if any(p.code == permission_code for p in self.permissions):
            return True
        
        # Check inherited permissions from parent
        if self.parent:
            return self.parent.has_permission(permission_code)
        
        return False
    
    def get_all_permissions(self) -> List[str]:
        """
        Get all permission codes including inherited ones.
        
        Returns:
            List of permission codes
        """
        permissions = [p.code for p in self.permissions]
        
        if self.parent:
            permissions.extend(self.parent.get_all_permissions())
        
        return list(set(permissions))


class Permission(BaseModel):
    """
    Permission Model
    
    Represents a fine-grained permission in the system.
    Permissions are organized by module and action.
    """
    
    __tablename__ = "permissions"
    __table_args__ = (
        Index("ix_permissions_code", "code", unique=True),
        Index("ix_permissions_module", "module"),
    )
    
    # ========================================
    # Permission Fields
    # ========================================
    code: str = Column(
        String(100),
        nullable=False,
        unique=True,
        doc="Unique permission code (e.g., 'sales.invoice.create')"
    )
    
    name: str = Column(
        String(100),
        nullable=False,
        doc="Human-readable permission name"
    )
    
    description: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Permission description"
    )
    
    module: str = Column(
        String(50),
        nullable=False,
        doc="Module this permission belongs to"
    )
    
    action: str = Column(
        String(50),
        nullable=False,
        doc="Action type (create, read, update, delete, etc.)"
    )
    
    resource: str = Column(
        String(100),
        nullable=False,
        doc="Resource this permission applies to"
    )
    
    scope: PermissionScope = Column(
        SQLEnum(PermissionScope),
        default=PermissionScope.TENANT,
        nullable=False,
        doc="Permission scope level"
    )
    
    conditions: dict = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Additional conditions for permission check"
    )
    
    # ========================================
    # Relationships
    # ========================================
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
        lazy="dynamic",
        doc="Roles that grant this permission"
    )


class UserRole(BaseModel):
    """
    UserRole Association Model
    
    Represents the many-to-many relationship between users and roles.
    """
    
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
        Index("ix_user_roles_user", "user_id"),
        Index("ix_user_roles_role", "role_id"),
    )
    
    user_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    role_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False
    )
    
    assigned_by_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User who assigned this role"
    )
    
    assigned_at: datetime = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When this role was assigned"
    )
    
    expires_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When this role assignment expires"
    )


class RolePermission(BaseModel):
    """
    RolePermission Association Model
    
    Represents the many-to-many relationship between roles and permissions.
    """
    
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )
    
    role_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False
    )
    
    permission_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        nullable=False
    )


class UserSession(BaseModel):
    """
    UserSession Model
    
    Tracks active user sessions for security and management.
    """
    
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_user_sessions_token", "token_hash"),
        Index("ix_user_sessions_expires", "expires_at"),
    )
    
    user_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    token_hash: str = Column(
        String(64),
        nullable=False,
        unique=True,
        doc="Hashed session token"
    )
    
    refresh_token_hash: Optional[str] = Column(
        String(64),
        nullable=True,
        unique=True,
        doc="Hashed refresh token"
    )
    
    ip_address: Optional[str] = Column(
        String(45),
        nullable=True,
        doc="Client IP address"
    )
    
    user_agent: Optional[str] = Column(
        String(500),
        nullable=True,
        doc="Client user agent string"
    )
    
    device_type: Optional[str] = Column(
        String(50),
        nullable=True,
        doc="Device type (desktop, mobile, tablet)"
    )
    
    device_name: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Device name if available"
    )
    
    location: Optional[str] = Column(
        String(200),
        nullable=True,
        doc="Geographic location based on IP"
    )
    
    is_active: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether session is active"
    )
    
    expires_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        doc="Session expiration timestamp"
    )
    
    last_activity_at: datetime = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Last activity timestamp"
    )
    
    # ========================================
    # Relationships
    # ========================================
    user: Mapped["User"] = relationship(
        "User",
        back_populates="sessions"
    )
    
    @property
    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.utcnow() > self.expires_at


class UserActivityLog(BaseModel):
    """
    UserActivityLog Model
    
    Records user activities for audit and analytics.
    """
    
    __tablename__ = "user_activity_logs"
    __table_args__ = (
        Index("ix_user_activity_logs_user", "user_id"),
        Index("ix_user_activity_logs_action", "action"),
        Index("ix_user_activity_logs_created", "created_at"),
    )
    
    user_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    action: str = Column(
        String(100),
        nullable=False,
        doc="Action performed (e.g., 'login', 'create_invoice')"
    )
    
    resource_type: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Type of resource affected"
    )
    
    resource_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="ID of resource affected"
    )
    
    description: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Activity description"
    )
    
    ip_address: Optional[str] = Column(
        String(45),
        nullable=True,
        doc="Client IP address"
    )
    
    user_agent: Optional[str] = Column(
        String(500),
        nullable=True,
        doc="Client user agent"
    )
    
    old_values: dict = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Values before change (for updates)"
    )
    
    new_values: dict = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Values after change"
    )
    
    metadata_json: dict = Column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
        doc="Additional metadata"
    )
    
    # ========================================
    # Relationships
    # ========================================
    user: Mapped["User"] = relationship(
        "User",
        back_populates="activity_logs"
    )


# Import Integer at the end to avoid circular import
from sqlalchemy import Integer
