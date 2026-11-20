"""
Nexus ERP - Tenant Context Manager
==================================

This module provides tenant context management for multi-tenant operations.
Implements thread-safe tenant isolation using context variables.

Features:
- Thread-safe tenant context storage
- Automatic tenant scoping on database queries
- Tenant resolution from JWT token and subdomain
- Query filtering for row-level isolation
- FastAPI middleware and dependencies
"""

from contextvars import ContextVar
from typing import Optional, Dict, Any, Callable
from uuid import UUID
import logging
from dataclasses import dataclass
from functools import wraps

from fastapi import Request, HTTPException, status, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import asyncio

from app.core.config import settings

logger = logging.getLogger(__name__)

# Context variable for storing tenant context
_tenant_context: ContextVar[Optional["TenantContext"]] = ContextVar(
    "tenant_context", default=None
)


@dataclass
class TenantContext:
    """
    Tenant context data class.
    
    Stores information about the current tenant context for the request.
    """
    tenant_id: UUID
    tenant_slug: str
    tenant_subdomain: str
    schema_name: Optional[str] = None
    plan_type: str = "basic"
    features: Dict[str, bool] = None
    
    def __post_init__(self):
        if self.features is None:
            self.features = {}


class TenantManager:
    """
    Tenant Manager Class
    
    Manages tenant context for the current request/thread.
    Provides methods for setting, getting, and clearing tenant context.
    """
    
    @staticmethod
    def set_context(
        tenant_id: str,
        tenant_slug: str,
        tenant_subdomain: str,
        schema_name: Optional[str] = None,
        plan_type: str = "basic",
        features: Optional[Dict[str, bool]] = None
    ) -> TenantContext:
        """
        Set the tenant context for the current request.
        
        Args:
            tenant_id: UUID of the tenant
            tenant_slug: URL-safe slug of the tenant
            tenant_subdomain: Subdomain of the tenant
            schema_name: Database schema name (if using schema isolation)
            plan_type: Current subscription plan type
            features: Feature flags for the tenant
            
        Returns:
            TenantContext: The created tenant context
        """
        context = TenantContext(
            tenant_id=UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id,
            tenant_slug=tenant_slug,
            tenant_subdomain=tenant_subdomain,
            schema_name=schema_name,
            plan_type=plan_type,
            features=features or {}
        )
        
        _tenant_context.set(context)
        logger.debug(f"Tenant context set: {tenant_slug}")
        
        return context
    
    @staticmethod
    def get_context() -> Optional[TenantContext]:
        """
        Get the current tenant context.
        
        Returns:
            TenantContext or None if not set
        """
        return _tenant_context.get()
    
    @staticmethod
    def get_tenant_id() -> Optional[UUID]:
        """
        Get the current tenant ID.
        
        Returns:
            UUID or None if context not set
        """
        context = _tenant_context.get()
        return context.tenant_id if context else None
    
    @staticmethod
    def clear_context():
        """
        Clear the tenant context.
        
        Should be called at the end of each request.
        """
        _tenant_context.set(None)
        logger.debug("Tenant context cleared")
    
    @staticmethod
    def has_context() -> bool:
        """
        Check if tenant context is set.
        
        Returns:
            True if context is set, False otherwise
        """
        return _tenant_context.get() is not None
    
    @staticmethod
    def has_feature(feature_name: str) -> bool:
        """
        Check if current tenant has access to a feature.
        
        Args:
            feature_name: Name of the feature to check
            
        Returns:
            True if tenant has the feature, False otherwise
        """
        context = _tenant_context.get()
        if context and context.features:
            return context.features.get(feature_name, False)
        return False
    
    @staticmethod
    def require_tenant() -> TenantContext:
        """
        Get tenant context or raise an exception.
        
        Returns:
            TenantContext
            
        Raises:
            RuntimeError: If tenant context is not set
        """
        context = _tenant_context.get()
        if not context:
            raise RuntimeError("Tenant context not set")
        return context


# ========================================
# Convenience Functions
# ========================================

def get_tenant_id() -> Optional[UUID]:
    """
    Convenience function to get current tenant ID.
    
    Returns:
        UUID or None
    """
    return TenantManager.get_tenant_id()


def get_tenant_context() -> Optional[TenantContext]:
    """
    Convenience function to get current tenant context.
    
    Returns:
        TenantContext or None
    """
    return TenantManager.get_context()


def require_tenant_context() -> TenantContext:
    """
    Convenience function to require tenant context.
    
    Returns:
        TenantContext
        
    Raises:
        RuntimeError: If context not set
    """
    return TenantManager.require_tenant()


# ========================================
# FastAPI Dependency for Tenant
# ========================================

async def get_current_tenant(request: Request) -> TenantContext:
    """
    FastAPI dependency to get the current tenant context.
    
    This dependency should be used in endpoints that require tenant context.
    It will raise an HTTPException if tenant context is not available.
    
    Args:
        request: FastAPI request object
        
    Returns:
        TenantContext: The current tenant context
        
    Raises:
        HTTPException: If tenant context is not set
        
    Usage:
        @router.get("/items")
        async def get_items(tenant: TenantContext = Depends(get_current_tenant)):
            # tenant.tenant_id is now available
            pass
    """
    context = TenantManager.get_context()
    
    if not context:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "tenant_required",
                "message": "Tenant context required. Please access via your subdomain."
            }
        )
    
    return context


async def get_optional_tenant(request: Request) -> Optional[TenantContext]:
    """
    FastAPI dependency for optional tenant context.
    
    This dependency returns the tenant context if available, or None otherwise.
    Useful for endpoints that work both with and without tenant context.
    
    Args:
        request: FastAPI request object
        
    Returns:
        TenantContext or None
        
    Usage:
        @router.get("/public/items")
        async def get_public_items(tenant: Optional[TenantContext] = Depends(get_optional_tenant)):
            if tenant:
                # Tenant-specific logic
                pass
            else:
                # Public logic
                pass
    """
    return TenantManager.get_context()


# ========================================
# Tenant Query Filter
# ========================================

class TenantQueryFilter:
    """
    Tenant query filtering utilities.
    
    Provides methods to automatically scope queries to the current tenant.
    """
    
    @staticmethod
    def apply_tenant_filter(query, model_class):
        """
        Apply tenant filter to a SQLAlchemy query.
        
        Args:
            query: SQLAlchemy query object
            model_class: Model class to filter
            
        Returns:
            Filtered query
        """
        tenant_id = get_tenant_id()
        if tenant_id and hasattr(model_class, 'tenant_id'):
            query = query.filter(model_class.tenant_id == tenant_id)
        return query
    
    @staticmethod
    def get_tenant_filter_dict() -> Dict[str, UUID]:
        """
        Get tenant filter dictionary for query filtering.
        
        Returns:
            Dictionary with tenant_id or empty dict
        """
        tenant_id = get_tenant_id()
        if tenant_id:
            return {"tenant_id": tenant_id}
        return {}
    
    @staticmethod
    def filter_by_tenant(model_class) -> list:
        """
        Get filter conditions for tenant-based filtering.
        
        Args:
            model_class: SQLAlchemy model class
            
        Returns:
            List of filter conditions
        """
        tenant_id = get_tenant_id()
        conditions = []
        if tenant_id and hasattr(model_class, 'tenant_id'):
            conditions.append(model_class.tenant_id == tenant_id)
        return conditions


# ========================================
# Tenant Isolation Mixin for Models
# ========================================

class TenantIsolatedModel:
    """
    Mixin class for tenant-isolated models.
    
    Provides methods for automatic tenant filtering on model queries.
    """
    
    @classmethod
    def get_tenant_filtered_query(cls, session: AsyncSession):
        """
        Get a query filtered by current tenant.
        
        Args:
            session: Database session
            
        Returns:
            Filtered query
        """
        query = select(cls)
        return TenantQueryFilter.apply_tenant_filter(query, cls)
    
    @classmethod
    async def get_by_id_tenant(cls, session: AsyncSession, record_id: UUID):
        """
        Get a record by ID with tenant filtering.
        
        Args:
            session: Database session
            record_id: Record UUID
            
        Returns:
            Model instance or None
        """
        query = select(cls).where(cls.id == record_id)
        query = TenantQueryFilter.apply_tenant_filter(query, cls)
        result = await session.execute(query)
        return result.scalar_one_or_none()


# ========================================
# Decorators
# ========================================

def tenant_scoped(func):
    """
    Decorator to ensure function runs in tenant context.
    
    Raises:
        RuntimeError: If tenant context is not set
        
    Usage:
        @tenant_scoped
        async def my_function():
            tenant_id = get_tenant_id()
            # ...
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        if not TenantManager.has_context():
            raise RuntimeError(
                f"Function {func.__name__} requires tenant context"
            )
        return await func(*args, **kwargs)
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        if not TenantManager.has_context():
            raise RuntimeError(
                f"Function {func.__name__} requires tenant context"
            )
        return func(*args, **kwargs)
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def require_feature(feature_name: str):
    """
    Decorator to require a specific feature for the current tenant.
    
    Args:
        feature_name: Name of the required feature
        
    Raises:
        HTTPException: If tenant doesn't have the feature
        
    Usage:
        @require_feature("ai_features")
        async def ai_endpoint():
            # ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not TenantManager.has_feature(feature_name):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "feature_not_available",
                        "message": f"Feature '{feature_name}' is not available on your current plan"
                    }
                )
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not TenantManager.has_feature(feature_name):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "feature_not_available",
                        "message": f"Feature '{feature_name}' is not available on your current plan"
                    }
                )
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def require_plan(*allowed_plans: str):
    """
    Decorator to require a specific plan type for the current tenant.
    
    Args:
        allowed_plans: List of allowed plan types
        
    Raises:
        HTTPException: If tenant doesn't have required plan
        
    Usage:
        @require_plan("pro", "enterprise")
        async def pro_feature():
            # ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            context = TenantManager.get_context()
            if not context or context.plan_type not in allowed_plans:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "plan_upgrade_required",
                        "message": f"This feature requires an upgraded plan"
                    }
                )
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            context = TenantManager.get_context()
            if not context or context.plan_type not in allowed_plans:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "plan_upgrade_required",
                        "message": f"This feature requires an upgraded plan"
                    }
                )
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# ========================================
# Context Manager
# ========================================

class TenantContextManager:
    """
    Context manager for temporarily setting tenant context.
    
    Usage:
        with TenantContextManager(tenant_id, slug, subdomain):
            # Operations with tenant context
            pass
    """
    
    def __init__(
        self,
        tenant_id: str,
        tenant_slug: str,
        tenant_subdomain: str,
        schema_name: Optional[str] = None,
        plan_type: str = "basic",
        features: Optional[Dict[str, bool]] = None
    ):
        self.tenant_id = tenant_id
        self.tenant_slug = tenant_slug
        self.tenant_subdomain = tenant_subdomain
        self.schema_name = schema_name
        self.plan_type = plan_type
        self.features = features
    
    def __enter__(self):
        self._previous_context = TenantManager.get_context()
        TenantManager.set_context(
            tenant_id=self.tenant_id,
            tenant_slug=self.tenant_slug,
            tenant_subdomain=self.tenant_subdomain,
            schema_name=self.schema_name,
            plan_type=self.plan_type,
            features=self.features
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        TenantManager.clear_context()
        # Restore previous context if any
        if self._previous_context:
            TenantManager.set_context(
                tenant_id=str(self._previous_context.tenant_id),
                tenant_slug=self._previous_context.tenant_slug,
                tenant_subdomain=self._previous_context.tenant_subdomain,
                schema_name=self._previous_context.schema_name,
                plan_type=self._previous_context.plan_type,
                features=self._previous_context.features
            )
        return False


# ========================================
# Async Context Manager
# ========================================

class AsyncTenantContextManager:
    """
    Async context manager for tenant context.
    
    Usage:
        async with AsyncTenantContextManager(tenant_id, slug, subdomain, db):
            # Operations with tenant context
            pass
    """
    
    def __init__(
        self,
        tenant_id: str,
        tenant_slug: str,
        tenant_subdomain: str,
        db: Optional[AsyncSession] = None,
        schema_name: Optional[str] = None,
        plan_type: str = "basic",
        features: Optional[Dict[str, bool]] = None
    ):
        self.tenant_id = tenant_id
        self.tenant_slug = tenant_slug
        self.tenant_subdomain = tenant_subdomain
        self.db = db
        self.schema_name = schema_name
        self.plan_type = plan_type
        self.features = features
        self._previous_context = None
    
    async def __aenter__(self):
        self._previous_context = TenantManager.get_context()
        TenantManager.set_context(
            tenant_id=self.tenant_id,
            tenant_slug=self.tenant_slug,
            tenant_subdomain=self.tenant_subdomain,
            schema_name=self.schema_name,
            plan_type=self.plan_type,
            features=self.features
        )
        
        # schema_name is retained only for legacy metadata compatibility.
        # It must never alter the database connection's search_path.
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        TenantManager.clear_context()
        
        # No database schema reset is needed: schema switching is disabled.
        # Restore previous context if any
        if self._previous_context:
            TenantManager.set_context(
                tenant_id=str(self._previous_context.tenant_id),
                tenant_slug=self._previous_context.tenant_slug,
                tenant_subdomain=self._previous_context.tenant_subdomain,
                schema_name=self._previous_context.schema_name,
                plan_type=self._previous_context.plan_type,
                features=self._previous_context.features
            )
        
        return False


# ========================================
# Subdomain Utilities
# ========================================

def extract_tenant_from_subdomain(host: str) -> Optional[str]:
    """
    Extract tenant subdomain from host header.
    
    Args:
        host: Host header value (e.g., "acme.nexus-erp.com")
        
    Returns:
        Subdomain string or None
    """
    if not host:
        return None
    
    # Remove port if present
    host = host.split(":")[0]
    
    # Handle localhost for development
    if host in ["localhost", "127.0.0.1"]:
        return None
    
    # Split by dots
    parts = host.split(".")
    
    # Check if we have a subdomain
    # Expected format: tenant.domain.tld
    if len(parts) >= 3:
        return parts[0]
    
    # Check for custom domain format
    if len(parts) == 2:
        # Could be a custom domain like acme-erp.com
        # This would require a separate lookup
        pass
    
    return None


def is_tenant_subdomain(host: str) -> bool:
    """
    Check if the host represents a tenant subdomain.
    
    Args:
        host: Host header value
        
    Returns:
        True if it's a tenant subdomain
    """
    return extract_tenant_from_subdomain(host) is not None


# ========================================
# TenantContextMiddleware for FastAPI
# ========================================

class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    FastAPI Middleware for Tenant Context
    
    This middleware automatically resolves and sets the tenant context
    for each request based on subdomain or JWT token.
    
    Features:
    - Subdomain-based tenant resolution
    - JWT token-based tenant resolution
    - Custom domain support
    - Schema-based tenant isolation
    - Request logging with tenant context
    
    Usage:
        app = FastAPI()
        app.add_middleware(TenantContextMiddleware)
    """
    
    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        # Paths that don't require tenant context
        self.public_paths = {
            "/",
            "/health",
            "/health/ready",
            "/health/live",
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/password/reset",
            "/api/v1/auth/verify-email",
            "/api/v1/auth/confirm-email",
            "/api/v1/billing/webhook/stripe",
        }
        
        # Paths that start with these prefixes don't require tenant
        self.public_prefixes = [
            "/api/v1/public/",
            "/static/",
            "/_next/",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Process request and set tenant context.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response from next handler
        """
        # Clear any previous context
        TenantManager.clear_context()
        
        path = request.url.path
        
        # Skip tenant resolution for public paths
        if self._is_public_path(path):
            return await call_next(request)
        
        try:
            # Try to resolve tenant
            tenant_info = await self._resolve_tenant(request)
            
            if tenant_info:
                # Set tenant context
                TenantManager.set_context(
                    tenant_id=tenant_info["tenant_id"],
                    tenant_slug=tenant_info.get("slug", ""),
                    tenant_subdomain=tenant_info.get("subdomain", ""),
                    schema_name=tenant_info.get("schema_name"),
                    plan_type=tenant_info.get("plan_type", "basic"),
                    features=tenant_info.get("features", {})
                )
                
                # Store tenant info in request state
                request.state.tenant_id = tenant_info["tenant_id"]
                request.state.tenant_slug = tenant_info.get("slug", "")
            else:
                # For paths that require tenant, return error
                if self._requires_tenant(path):
                    logger.warning(f"No tenant context for path: {path}")
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={
                            "success": False,
                            "error": {
                                "code": "tenant_required",
                                "message": "Tenant context required. Please access via your subdomain."
                            }
                        }
                    )
            
            response = await call_next(request)
            
            # Add tenant header to response for debugging
            if TenantManager.has_context():
                response.headers["X-Tenant-ID"] = str(TenantManager.get_tenant_id())
            
            return response
            
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "success": False,
                    "error": {
                        "code": str(e.detail).lower().replace(" ", "_"),
                        "message": e.detail
                    }
                }
            )
        except Exception as e:
            logger.error(f"Tenant middleware error: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "error": {
                        "code": "internal_error",
                        "message": "An error occurred processing your request"
                    }
                }
            )
        finally:
            # Always clear context after request
            TenantManager.clear_context()
    
    def _is_public_path(self, path: str) -> bool:
        """Check if path is public (doesn't require tenant)."""
        if path in self.public_paths:
            return True
        
        for prefix in self.public_prefixes:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _requires_tenant(self, path: str) -> bool:
        """Check if path requires tenant context."""
        # All API paths except auth endpoints require tenant
        if path.startswith("/api/v1/"):
            auth_paths = [
                "/api/v1/auth/login",
                "/api/v1/auth/register",
                "/api/v1/auth/password",
                "/api/v1/auth/verify",
            ]
            return not any(path.startswith(p) for p in auth_paths)
        return False
    
    async def _resolve_tenant(self, request: Request) -> Optional[dict]:
        """
        Resolve tenant from request.
        
        Tries JWT token first, then subdomain.
        
        Args:
            request: FastAPI request
            
        Returns:
            Tenant info dict or None
        """
        # Method 1: Try JWT token
        tenant_info = await self._resolve_from_token(request)
        if tenant_info:
            return tenant_info
        
        # Method 2: Try subdomain
        tenant_info = await self._resolve_from_subdomain(request)
        if tenant_info:
            return tenant_info
        
        # Method 3: Try custom domain header (for white-label tenants)
        tenant_info = await self._resolve_from_custom_domain(request)
        if tenant_info:
            return tenant_info
        
        return None
    
    async def _resolve_from_token(self, request: Request) -> Optional[dict]:
        """
        Resolve tenant from JWT token in Authorization header.
        
        Args:
            request: FastAPI request
            
        Returns:
            Tenant info dict or None
        """
        from app.core.security import decode_token
        
        auth_header = request.headers.get("Authorization", "")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        try:
            payload = decode_token(token)
            tenant_id = payload.get("tenant_id")
            
            if tenant_id:
                # Get additional tenant info from database
                tenant_info = await self._get_tenant_info(tenant_id)
                if tenant_info:
                    return tenant_info
                
                # Return minimal info from token if DB lookup fails
                return {
                    "tenant_id": tenant_id,
                    "slug": payload.get("tenant_slug", ""),
                    "subdomain": "",
                    "plan_type": "basic",
                    "features": {}
                }
        except Exception as e:
            logger.debug(f"Token decode error in tenant resolution: {e}")
        
        return None
    
    async def _resolve_from_subdomain(self, request: Request) -> Optional[dict]:
        """
        Resolve tenant from subdomain in host header.
        
        Args:
            request: FastAPI request
            
        Returns:
            Tenant info dict or None
        """
        host = request.headers.get("host", "")
        subdomain = extract_tenant_from_subdomain(host)
        
        if not subdomain:
            return None
        
        # Look up tenant by subdomain
        tenant_info = await self._get_tenant_by_subdomain(subdomain)
        return tenant_info
    
    async def _resolve_from_custom_domain(self, request: Request) -> Optional[dict]:
        """
        Resolve tenant from custom domain.
        
        For enterprise tenants with custom domains.
        
        Args:
            request: FastAPI request
            
        Returns:
            Tenant info dict or None
        """
        host = request.headers.get("host", "")
        
        if not host or host.startswith(("localhost", "127.0.0.1")):
            return None
        
        # Remove port
        host = host.split(":")[0]
        
        # Check if it's a known custom domain
        # This would require a database lookup in production
        tenant_info = await self._get_tenant_by_custom_domain(host)
        return tenant_info
    
    async def _get_tenant_info(self, tenant_id: str) -> Optional[dict]:
        """
        Get tenant info from database by ID.
        
        Args:
            tenant_id: Tenant UUID string
            
        Returns:
            Tenant info dict or None
        """
        # Import here to avoid circular imports
        from app.core.database import db_manager
        
        try:
            async with db_manager.get_session() as session:
                result = await session.execute(
                    text("""
                        SELECT id, slug, subdomain, schema_name, plan_type, features, status
                        FROM tenants
                        WHERE id = :tenant_id AND is_deleted = false
                    """),
                    {"tenant_id": tenant_id}
                )
                row = result.fetchone()
                
                if row:
                    return {
                        "tenant_id": str(row.id),
                        "slug": row.slug,
                        "subdomain": row.subdomain,
                        "schema_name": row.schema_name,
                        "plan_type": row.plan_type,
                        "features": row.features or {},
                    }
        except Exception as e:
            logger.error(f"Error fetching tenant info: {e}")
        
        return None
    
    async def _get_tenant_by_subdomain(self, subdomain: str) -> Optional[dict]:
        """
        Get tenant info by subdomain.
        
        Args:
            subdomain: Tenant subdomain
            
        Returns:
            Tenant info dict or None
        """
        from app.core.database import db_manager
        
        try:
            async with db_manager.get_session() as session:
                result = await session.execute(
                    text("""
                        SELECT id, slug, subdomain, schema_name, plan_type, features, status
                        FROM tenants
                        WHERE subdomain = :subdomain AND is_deleted = false AND is_active = true
                    """),
                    {"subdomain": subdomain}
                )
                row = result.fetchone()
                
                if row:
                    return {
                        "tenant_id": str(row.id),
                        "slug": row.slug,
                        "subdomain": row.subdomain,
                        "schema_name": row.schema_name,
                        "plan_type": row.plan_type,
                        "features": row.features or {},
                    }
        except Exception as e:
            logger.error(f"Error fetching tenant by subdomain: {e}")
        
        return None
    
    async def _get_tenant_by_custom_domain(self, domain: str) -> Optional[dict]:
        """
        Get tenant info by custom domain.
        
        Args:
            domain: Custom domain
            
        Returns:
            Tenant info dict or None
        """
        from app.core.database import db_manager
        
        try:
            async with db_manager.get_session() as session:
                # Check tenant settings for custom domain
                result = await session.execute(
                    text("""
                        SELECT t.id, t.slug, t.subdomain, t.schema_name, t.plan_type, 
                               t.features, t.status
                        FROM tenants t
                        WHERE t.settings->>'custom_domain' = :domain 
                        AND t.is_deleted = false 
                        AND t.is_active = true
                    """),
                    {"domain": domain}
                )
                row = result.fetchone()
                
                if row:
                    return {
                        "tenant_id": str(row.id),
                        "slug": row.slug,
                        "subdomain": row.subdomain,
                        "schema_name": row.schema_name,
                        "plan_type": row.plan_type,
                        "features": row.features or {},
                    }
        except Exception as e:
            logger.error(f"Error fetching tenant by custom domain: {e}")
        
        return None
