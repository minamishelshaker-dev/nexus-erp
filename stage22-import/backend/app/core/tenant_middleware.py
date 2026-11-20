"""
Nexus ERP - Tenant Middleware
=============================

This module provides middleware for multi-tenant request handling.
Automatically injects tenant context from JWT token and subdomain.

Features:
- Tenant resolution from subdomain
- Tenant resolution from JWT token
- Database schema switching for tenant isolation
- Request logging with tenant context
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Optional, Callable
from urllib.parse import urlparse
import logging

from app.core.tenant import (
    TenantManager,
    extract_tenant_from_subdomain,
)
from app.core.security import decode_token
from app.core.config import settings

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Tenant Middleware
    
    Resolves tenant context for each request and makes it available
    throughout the request lifecycle.
    
    Tenant resolution order:
    1. JWT token (tenant_id claim)
    2. Subdomain extraction
    3. Custom domain lookup
    """
    
    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        # Paths that don't require tenant context
        self.public_paths = {
            "/",
            "/health",
            "/health/ready",
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
        auth_header = request.headers.get("Authorization", "")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        try:
            payload = decode_token(token)
            # Refresh, password-reset and verification tokens must never establish
            # an authenticated tenant context.
            if payload.get("type") != "access":
                return None

            tenant_id = payload.get("tenant_id")
            if tenant_id:
                # The database is the source of truth. Fail closed when the tenant
                # is missing, inactive, deleted, or cannot be looked up.
                return await self._get_tenant_info(tenant_id)
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
        from sqlalchemy import text
        
        try:
            async with db_manager.get_session() as session:
                result = await session.execute(
                    text("""
                        SELECT id, slug, subdomain, schema_name, plan_type, features, status
                        FROM tenants
                        WHERE id = :tenant_id AND is_deleted = false AND is_active = true
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
        from sqlalchemy import text
        
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
        from sqlalchemy import text
        
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


class TenantSchemaMiddleware(BaseHTTPMiddleware):
    """Deprecated no-op middleware retained for import compatibility.

    Schema-per-tenant switching is disabled. Tenant isolation must be enforced
    by tenant_id-scoped database access and authorization checks.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        return await call_next(request)


# Dependency for requiring tenant context
async def require_tenant_dependency(request: Request):
    """
    FastAPI dependency that requires tenant context.
    
    Raises:
        HTTPException: If tenant context is not set
    """
    from app.core.tenant import TenantManager
    
    if not TenantManager.has_context():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required"
        )
    
    return TenantManager.get_context()


# Dependency for optional tenant context
async def optional_tenant_dependency(request: Request):
    """
    FastAPI dependency for optional tenant context.
    
    Returns:
        TenantContext or None
    """
    from app.core.tenant import TenantManager
    
    return TenantManager.get_context()
