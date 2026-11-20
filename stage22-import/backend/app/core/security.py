"""
Nexus ERP - Security and Authentication Module
==============================================

This module provides comprehensive security features including:
- JWT token generation and validation
- Password hashing and verification
- OAuth2 integration
- Permission checking utilities
- Rate limiting helpers

Features:
- Secure password storage with bcrypt
- JWT access and refresh tokens
- Token blacklisting for logout
- Permission-based access control
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import hashlib
import secrets
import logging

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User, Permission

# Configure logging
logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Cost factor for bcrypt
)

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=True
)


class TokenData:
    """
    Data class for decoded token information.
    """
    def __init__(
        self,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        tenant_id: Optional[str] = None,
        roles: Optional[List[str]] = None,
        permissions: Optional[List[str]] = None,
        exp: Optional[datetime] = None
    ):
        self.user_id = user_id
        self.email = email
        self.tenant_id = tenant_id
        self.roles = roles or []
        self.permissions = permissions or []
        self.exp = exp


class AuthError(Exception):
    """Custom exception for authentication errors."""
    def __init__(self, message: str, code: str = "auth_error"):
        self.message = message
        self.code = code
        super().__init__(self.message)


# ========================================
# Password Functions
# ========================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: The plain text password to verify
        hashed_password: The hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> Dict[str, Any]:
    """
    Validate password strength.
    
    Args:
        password: Password to validate
        
    Returns:
        Dictionary with validation results
    """
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    if len(password) > 128:
        errors.append("Password must be less than 128 characters")
    
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit")
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain at least one special character")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "strength": _calculate_password_strength(password)
    }


def _calculate_password_strength(password: str) -> str:
    """Calculate password strength level."""
    score = 0
    
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if len(password) >= 16:
        score += 1
    if any(c.isupper() for c in password):
        score += 1
    if any(c.islower() for c in password):
        score += 1
    if any(c.isdigit() for c in password):
        score += 1
    if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        score += 2
    
    if score <= 3:
        return "weak"
    elif score <= 5:
        return "medium"
    elif score <= 7:
        return "strong"
    else:
        return "very_strong"


# ========================================
# JWT Token Functions
# ========================================

def create_access_token(
    user_id: str,
    email: str,
    tenant_id: str,
    roles: List[str],
    permissions: List[str],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        user_id: User's unique identifier
        email: User's email address
        tenant_id: Tenant identifier for multi-tenancy
        roles: List of role codes assigned to user
        permissions: List of permission codes
        expires_delta: Custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    expire = datetime.utcnow() + expires_delta
    
    to_encode = {
        "sub": str(user_id),
        "email": email,
        "tenant_id": str(tenant_id),
        "roles": roles,
        "permissions": permissions,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(
    user_id: str,
    tenant_id: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        user_id: User's unique identifier
        tenant_id: Tenant identifier
        expires_delta: Custom expiration time
        
    Returns:
        Encoded JWT refresh token string
    """
    if expires_delta is None:
        expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    expire = datetime.utcnow() + expires_delta
    
    to_encode = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
        "jti": secrets.token_urlsafe(32)  # Unique token ID
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string to decode
        
    Returns:
        Decoded token payload
        
    Raises:
        AuthError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError("Token has expired", "token_expired")
    except jwt.InvalidTokenError as e:
        raise AuthError(f"Invalid token: {str(e)}", "invalid_token")


def verify_token_type(payload: Dict[str, Any], expected_type: str) -> bool:
    """
    Verify that token is of expected type.
    
    Args:
        payload: Decoded token payload
        expected_type: Expected token type ('access' or 'refresh')
        
    Returns:
        True if token type matches
    """
    return payload.get("type") == expected_type


def get_token_hash(token: str) -> str:
    """
    Get SHA-256 hash of token for storage/comparison.
    
    Args:
        token: Token to hash
        
    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(token.encode()).hexdigest()


# ========================================
# Authentication Dependencies
# ========================================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get current authenticated user.
    
    Validates the JWT token and retrieves the user from database.
    
    Args:
        token: JWT token from Authorization header
        db: Database session
        
    Returns:
        User instance if authentication successful
        
    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_token(token)
        
        if not verify_token_type(payload, "access"):
            raise credentials_exception
        
        user_id: str = payload.get("sub")
        token_tenant_id: Optional[str] = payload.get("tenant_id")
        if user_id is None or not token_tenant_id:
            raise credentials_exception
        
    except AuthError as e:
        raise credentials_exception
    
    # Get user from database
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_deleted == False)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception

    # A valid JWT must still belong to the user's currently assigned tenant.
    # Never trust tenant_id from the token without comparing it to DB state.
    if str(getattr(user, "tenant_id", "")) != str(token_tenant_id):
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is temporarily locked"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to ensure user is active.
    
    Args:
        current_user: User from get_current_user
        
    Returns:
        Active user instance
        
    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to ensure user is a superuser.
    
    Args:
        current_user: User from get_current_user
        
    Returns:
        Superuser instance
        
    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user


# ========================================
# Permission Checking
# ========================================

class PermissionChecker:
    """
    Permission checker class for dependency injection.
    
    Usage:
        @router.post("/items", dependencies=[Depends(PermissionChecker("items.create"))])
        async def create_item(...):
            ...
    """
    
    def __init__(self, permission: str):
        """
        Initialize permission checker.
        
        Args:
            permission: Required permission code (e.g., 'sales.invoice.create')
        """
        self.permission = permission
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_user)
    ) -> User:
        """
        Check if user has required permission.
        
        Args:
            current_user: Current authenticated user
            
        Returns:
            User if permission check passes
            
        Raises:
            HTTPException: If permission check fails
        """
        if current_user.is_superuser:
            return current_user
        
        required_permission = _PERMISSION_ALIASES.get(self.permission, self.permission)
        if not current_user.has_permission(required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{self.permission}' required"
            )
        
        return current_user


# Explicit aliases for legacy endpoint permission codes. These aliases only
# translate names; they do not grant permissions that are absent from RBAC.
_PERMISSION_ALIASES = {
    "sales.quotation.read": "sales.quotations.view",
    "sales.quotation.create": "sales.quotations.create",
    "sales.quotation.update": "sales.quotations.update",
    "sales.order.read": "sales.orders.view",
    "sales.order.create": "sales.orders.create",
    "sales.order.update": "sales.orders.update",
    "sales.invoice.read": "sales.invoices.view",
    "sales.invoice.create": "sales.invoices.create",
    "sales.invoice.update": "sales.invoices.update",
    "purchase.order.read": "purchase.orders.view",
    "purchase.order.create": "purchase.orders.create",
    "purchase.order.update": "purchase.orders.update",
    "purchase.order.approve": "purchase.orders.approve",
    "purchase.receipt.read": "purchase.receipt.view",
    "accounting.account.create": "accounting.accounts.create",
    "accounting.account.update": "accounting.accounts.update",
    "accounting.account.delete": "accounting.accounts.delete",
    "crm.customer.create": "crm.customers.create",
    "crm.customer.update": "crm.customers.update",
    "crm.customer.delete": "crm.customers.delete",
    "inventory.stock.create": "inventory.movements.create",
    "manufacturing.order.create": "manufacturing.orders.create",
    "manufacturing.order.update": "manufacturing.orders.update",
    "manufacturing.bom.read": "manufacturing.bom.view",
    "manufacturing.workcenter.read": "manufacturing.workcenter.view",
    "manufacturing.order.read": "manufacturing.orders.view",
}


def require_permission(permission_or_user, permission: Optional[str] = None):
    """Require a permission either as a FastAPI dependency or inline check.

    Dependency form (preferred for new endpoints)::
        current_user: User = Depends(require_permission("sales.orders.view"))

    Inline form (retained for existing endpoints)::
        await require_permission(current_user, "sales.orders.view")

    Inline checks return a coroutine so existing ``await`` call sites remain
    compatible. Both forms use the same authorization logic.
    """
    if permission is None:
        if not isinstance(permission_or_user, str) or not permission_or_user:
            raise TypeError("require_permission expects a permission code")
        return PermissionChecker(permission_or_user)

    current_user = permission_or_user
    required_permission = _PERMISSION_ALIASES.get(permission, permission)

    async def _check_inline():
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if getattr(current_user, "is_superuser", False):
            return current_user
        if not current_user.has_permission(required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required",
            )
        return current_user

    return _check_inline()


class RoleChecker:
    """
    Role checker class for dependency injection.
    """
    
    def __init__(self, role: str):
        self.role = role
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_user)
    ) -> User:
        if current_user.is_superuser:
            return current_user
        
        if not current_user.has_role(self.role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{self.role}' required"
            )
        
        return current_user


def require_role(role: str):
    """Create a role requirement dependency."""
    return RoleChecker(role)


# ========================================
# Token Blacklist (for logout)
# ========================================

class TokenBlacklist:
    """
    Token blacklist manager for logout functionality.
    
    In production, this should use Redis for distributed systems.
    """
    
    def __init__(self):
        self._blacklist: set = set()
    
    def add_token(self, token: str):
        """Add token to blacklist."""
        token_hash = get_token_hash(token)
        self._blacklist.add(token_hash)
    
    def is_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted."""
        token_hash = get_token_hash(token)
        return token_hash in self._blacklist
    
    def cleanup_expired(self):
        """Remove expired tokens from blacklist."""
        # In production with Redis, use TTL instead
        pass


# Global token blacklist instance
token_blacklist = TokenBlacklist()


# ========================================
# Utility Functions
# ========================================

def generate_api_key() -> str:
    """
    Generate a secure API key.
    
    Returns:
        URL-safe API key string
    """
    return secrets.token_urlsafe(32)


def generate_verification_token() -> str:
    """
    Generate a verification token for email/phone verification.
    
    Returns:
        Verification token string
    """
    return secrets.token_urlsafe(32)


def generate_password_reset_token(email: str) -> str:
    """
    Generate a password reset token.
    
    Args:
        email: User's email address
        
    Returns:
        Password reset token
    """
    expire = datetime.utcnow() + timedelta(hours=24)
    
    to_encode = {
        "sub": email,
        "exp": expire,
        "type": "password_reset"
    }
    
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify a password reset token.
    
    Args:
        token: Password reset token
        
    Returns:
        Email address if token is valid, None otherwise
    """
    try:
        payload = decode_token(token)
        
        if payload.get("type") != "password_reset":
            return None
        
        return payload.get("sub")
        
    except AuthError:
        return None
