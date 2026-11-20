"""
Nexus ERP - Audit Logging System
================================

This module provides comprehensive audit logging for tracking all actions
in the system. Implements decorators, background tasks, and query helpers.

Features:
- Audit log decorator for functions
- Background task for logging
- Query helpers for audit history
- Request context capture
- Change tracking
- Compliance reporting
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from uuid import UUID
from functools import wraps
import logging
import asyncio
import json
from dataclasses import dataclass, field
from contextlib import contextmanager
from contextvars import ContextVar
import time

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func, text
from sqlalchemy.orm import selectinload

from app.models.tenant import AuditLog, AuditAction
from app.core.tenant import get_tenant_id, get_tenant_context
from app.core.database import get_db, db_manager

logger = logging.getLogger(__name__)


# ========================================
# Audit Context
# ========================================

@dataclass
class AuditContext:
    """
    Context for audit logging.
    
    Captures request context for use in audit logs.
    """
    user_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_method: Optional[str] = None
    request_path: Optional[str] = None
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": str(self.user_id) if self.user_id else None,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_method": self.request_method,
            "request_path": self.request_path,
            "request_id": self.request_id,
        }


# Thread-local context for audit
_audit_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar("audit_context", default=None)


def set_audit_context(**kwargs):
    """
    Set audit context for current request.
    
    Args:
        **kwargs: Context fields to set
    """
    current = dict(_audit_context.get() or {})
    current.update(kwargs)
    _audit_context.set(current)


def get_audit_context() -> Dict[str, Any]:
    """
    Get current audit context.
    
    Returns:
        Dictionary with audit context
    """
    context = dict(_audit_context.get() or {})
    
    # Add tenant context if available
    tenant_id = get_tenant_id()
    if tenant_id:
        context["tenant_id"] = tenant_id
    
    return context


def clear_audit_context():
    """Clear audit context."""
    _audit_context.set({})


@contextmanager
def audit_context(**kwargs):
    """
    Context manager for audit context.
    
    Usage:
        with audit_context(user_id=user.id, ip_address=request.client.host):
            # Actions will be logged with this context
            pass
    """
    token = _audit_context.set({**(_audit_context.get() or {}), **kwargs})
    try:
        yield
    finally:
        _audit_context.reset(token)


# ========================================
# Audit Log Decorator
# ========================================

def audit_log(
    action: AuditAction,
    resource_type: str,
    resource_id_field: Optional[str] = None,
    resource_name_field: Optional[str] = None,
    capture_changes: bool = True,
    include_request: bool = True
):
    """
    Decorator to automatically log function execution.
    
    Args:
        action: AuditAction enum value
        resource_type: Type of resource being acted upon
        resource_id_field: Field name to extract resource ID from result
        resource_name_field: Field name to extract resource name from result
        capture_changes: Whether to capture old/new values
        include_request: Whether to include request context
        
    Usage:
        @audit_log(
            action=AuditAction.CREATE,
            resource_type="product",
            resource_id_field="id"
        )
        async def create_product(product_data: dict, db: AsyncSession):
            # ...
            return product
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            error_message = None
            result = None
            
            # Extract context
            context = get_audit_context()
            
            # Extract db session from kwargs or args
            db = kwargs.get("db") or kwargs.get("session")
            if db is None:
                for arg in args:
                    if isinstance(arg, AsyncSession):
                        db = arg
                        break
            
            # Extract old values if updating
            old_values = None
            if capture_changes and action in [AuditAction.UPDATE, AuditAction.DELETE]:
                old_values = await _capture_old_values(
                    resource_type,
                    kwargs.get("id") or kwargs.get(resource_id_field),
                    db
                )
            
            try:
                result = await func(*args, **kwargs)
                
                # Extract resource info from result
                resource_id = None
                resource_name = None
                
                if result:
                    if resource_id_field:
                        resource_id = getattr(result, resource_id_field, None)
                        if resource_id is None and isinstance(result, dict):
                            resource_id = result.get(resource_id_field)
                    
                    if resource_name_field:
                        resource_name = getattr(result, resource_name_field, None)
                        if resource_name is None and isinstance(result, dict):
                            resource_name = result.get(resource_name_field)
                
                # Capture new values
                new_values = None
                if capture_changes and action in [AuditAction.CREATE, AuditAction.UPDATE]:
                    new_values = _extract_values(result)
                
                # Calculate changes
                changes = None
                if old_values and new_values:
                    changes = _calculate_changes(old_values, new_values)
                
                # Log success
                duration_ms = int((time.time() - start_time) * 1000)
                
                await _write_audit_log(
                    db=db,
                    action=action,
                    resource_type=resource_type,
                    resource_id=str(resource_id) if resource_id else None,
                    resource_name=resource_name,
                    old_values=old_values,
                    new_values=new_values,
                    changes=changes,
                    context=context,
                    status=status,
                    duration_ms=duration_ms
                )
                
                return result
                
            except Exception as e:
                status = "failure"
                error_message = str(e)
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Log failure
                await _write_audit_log(
                    db=db,
                    action=action,
                    resource_type=resource_type,
                    resource_id=str(kwargs.get("id")) if kwargs.get("id") else None,
                    resource_name=None,
                    old_values=old_values,
                    new_values=None,
                    changes=None,
                    context=context,
                    status=status,
                    error_message=error_message,
                    duration_ms=duration_ms
                )
                
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, just call without audit
            # (audit requires async db operations)
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def audit_create(resource_type: str, resource_id_field: str = "id"):
    """
    Convenience decorator for create operations.
    
    Args:
        resource_type: Type of resource being created
        resource_id_field: Field name for resource ID
    """
    return audit_log(
        action=AuditAction.CREATE,
        resource_type=resource_type,
        resource_id_field=resource_id_field
    )


def audit_update(resource_type: str, resource_id_field: str = "id"):
    """
    Convenience decorator for update operations.
    
    Args:
        resource_type: Type of resource being updated
        resource_id_field: Field name for resource ID
    """
    return audit_log(
        action=AuditAction.UPDATE,
        resource_type=resource_type,
        resource_id_field=resource_id_field
    )


def audit_delete(resource_type: str, resource_id_field: str = "id"):
    """
    Convenience decorator for delete operations.
    
    Args:
        resource_type: Type of resource being deleted
        resource_id_field: Field name for resource ID
    """
    return audit_log(
        action=AuditAction.DELETE,
        resource_type=resource_type,
        resource_id_field=resource_id_field
    )


# ========================================
# Background Task for Logging
# ========================================

class AuditLogWriter:
    """
    Background audit log writer.
    
    Handles writing audit logs asynchronously.
    """
    
    @staticmethod
    async def write(
        db: AsyncSession,
        action: AuditAction,
        resource_type: str,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
        changes: Optional[dict] = None,
        description: Optional[str] = None,
        metadata: Optional[dict] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None
    ):
        """
        Write an audit log entry.
        
        Args:
            db: Database session
            action: Action type
            resource_type: Resource type
            resource_id: Resource ID
            resource_name: Human-readable resource name
            old_values: Previous values
            new_values: New values
            changes: Summary of changes
            description: Human-readable description
            metadata: Additional metadata
            status: Action status
            error_message: Error message if failed
            duration_ms: Duration in milliseconds
        """
        context = get_audit_context()
        
        await _write_audit_log(
            db=db,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            old_values=old_values,
            new_values=new_values,
            changes=changes,
            description=description,
            metadata=metadata,
            context=context,
            status=status,
            error_message=error_message,
            duration_ms=duration_ms
        )


# ========================================
# Query Helpers for Audit History
# ========================================

class AuditQuery:
    """
    Query helpers for audit history.
    """
    
    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        log_id: UUID
    ) -> Optional[AuditLog]:
        """
        Get audit log by ID.
        
        Args:
            db: Database session
            log_id: Audit log UUID
            
        Returns:
            AuditLog or None
        """
        result = await db.execute(
            select(AuditLog).where(AuditLog.id == log_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_resource(
        db: AsyncSession,
        resource_type: str,
        resource_id: str,
        tenant_id: Optional[UUID] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get audit logs for a specific resource.
        
        Args:
            db: Database session
            resource_type: Type of resource
            resource_id: Resource ID
            tenant_id: Optional tenant filter
            limit: Maximum number of results
            
        Returns:
            List of AuditLog
        """
        query = select(AuditLog).where(
            and_(
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id == resource_id
            )
        ).order_by(desc(AuditLog.created_at)).limit(limit)
        
        if tenant_id:
            query = query.where(AuditLog.tenant_id == tenant_id)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_by_user(
        db: AsyncSession,
        user_id: UUID,
        tenant_id: Optional[UUID] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get audit logs for a specific user.
        
        Args:
            db: Database session
            user_id: User UUID
            tenant_id: Optional tenant filter
            limit: Maximum number of results
            
        Returns:
            List of AuditLog
        """
        query = select(AuditLog).where(
            AuditLog.user_id == user_id
        ).order_by(desc(AuditLog.created_at)).limit(limit)
        
        if tenant_id:
            query = query.where(AuditLog.tenant_id == tenant_id)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_by_action(
        db: AsyncSession,
        action: AuditAction,
        tenant_id: Optional[UUID] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get audit logs by action type.
        
        Args:
            db: Database session
            action: AuditAction enum
            tenant_id: Optional tenant filter
            limit: Maximum number of results
            
        Returns:
            List of AuditLog
        """
        query = select(AuditLog).where(
            AuditLog.action == action
        ).order_by(desc(AuditLog.created_at)).limit(limit)
        
        if tenant_id:
            query = query.where(AuditLog.tenant_id == tenant_id)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def search(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        action: Optional[AuditAction] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search_text: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """
        Search audit logs with filters.
        
        Args:
            db: Database session
            tenant_id: Tenant UUID (required)
            user_id: Filter by user
            action: Filter by action type
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            status: Filter by status
            start_date: Filter by start date
            end_date: Filter by end date
            search_text: Search in description and resource name
            limit: Maximum results
            offset: Offset for pagination
            
        Returns:
            List of AuditLog
        """
        query = select(AuditLog).where(
            AuditLog.tenant_id == tenant_id
        )
        
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        
        if action:
            query = query.where(AuditLog.action == action)
        
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        
        if resource_id:
            query = query.where(AuditLog.resource_id == resource_id)
        
        if status:
            query = query.where(AuditLog.status == status)
        
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)
        
        if search_text:
            query = query.where(
                or_(
                    AuditLog.description.ilike(f"%{search_text}%"),
                    AuditLog.resource_name.ilike(f"%{search_text}%")
                )
            )
        
        query = query.order_by(desc(AuditLog.created_at)).limit(limit).offset(offset)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def count(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        action: Optional[AuditAction] = None,
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """
        Count audit logs matching filters.
        
        Args:
            db: Database session
            tenant_id: Tenant UUID
            user_id: Filter by user
            action: Filter by action type
            resource_type: Filter by resource type
            status: Filter by status
            start_date: Filter by start date
            end_date: Filter by end date
            
        Returns:
            Count of matching logs
        """
        query = select(func.count(AuditLog.id)).where(
            AuditLog.tenant_id == tenant_id
        )
        
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        
        if action:
            query = query.where(AuditLog.action == action)
        
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        
        if status:
            query = query.where(AuditLog.status == status)
        
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)
        
        result = await db.execute(query)
        return result.scalar() or 0
    
    @staticmethod
    async def get_user_activity_summary(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        days: int = 30
    ) -> Dict[str, int]:
        """
        Get activity summary for a user.
        
        Args:
            db: Database session
            tenant_id: Tenant UUID
            user_id: User UUID
            days: Number of days to include
            
        Returns:
            Dictionary with action counts
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        result = await db.execute(
            select(
                AuditLog.action,
                func.count(AuditLog.id).label("count")
            ).where(
                and_(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.user_id == user_id,
                    AuditLog.created_at >= start_date
                )
            ).group_by(AuditLog.action)
        )
        
        return {
            row.action.value if hasattr(row.action, 'value') else row.action: row.count
            for row in result
        }
    
    @staticmethod
    async def get_resource_history(
        db: AsyncSession,
        tenant_id: UUID,
        resource_type: str,
        resource_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get full history for a resource with formatted output.
        
        Args:
            db: Database session
            tenant_id: Tenant UUID
            resource_type: Type of resource
            resource_id: Resource ID
            
        Returns:
            List of formatted history entries
        """
        logs = await AuditQuery.get_by_resource(
            db=db,
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id
        )
        
        history = []
        for log in logs:
            entry = {
                "id": str(log.id),
                "action": log.action.value if log.action else None,
                "performed_at": log.created_at.isoformat() if log.created_at else None,
                "performed_by": str(log.user_id) if log.user_id else None,
                "description": log.description or _generate_description(log),
                "changes": log.changes,
                "status": log.status,
                "ip_address": log.ip_address,
            }
            history.append(entry)
        
        return history


# ========================================
# Helper Functions
# ========================================

async def _write_audit_log(
    db: Optional[AsyncSession],
    action: AuditAction,
    resource_type: str,
    resource_id: Optional[str],
    resource_name: Optional[str],
    old_values: Optional[dict],
    new_values: Optional[dict],
    changes: Optional[dict],
    context: Dict[str, Any],
    description: Optional[str] = None,
    metadata: Optional[dict] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    duration_ms: Optional[int] = None
):
    """
    Write audit log entry to database.
    """
    if db is None:
        logger.warning(f"No database session available for audit log: {action} {resource_type}")
        return
    
    try:
        log = AuditLog(
            tenant_id=context.get("tenant_id"),
            user_id=context.get("user_id"),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            old_values=old_values,
            new_values=new_values,
            changes=changes,
            ip_address=context.get("ip_address"),
            user_agent=context.get("user_agent"),
            request_method=context.get("request_method"),
            request_path=context.get("request_path"),
            request_id=context.get("request_id"),
            description=description,
            metadata=metadata or {},
            status=status,
            error_message=error_message,
            duration_ms=duration_ms
        )
        
        db.add(log)
        await db.commit()
        
        logger.debug(f"Audit log written: {action.value} {resource_type} {resource_id}")
        
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")
        # Don't raise - audit logging should not break the main operation


async def _capture_old_values(
    resource_type: str,
    resource_id: Optional[str],
    db: Optional[AsyncSession]
) -> Optional[dict]:
    """
    Capture current values before update/delete.
    
    Args:
        resource_type: Type of resource
        resource_id: Resource ID
        db: Database session
        
    Returns:
        Dictionary of current values
    """
    if not resource_id or not db:
        return None
    
    # Map resource types to models
    # This would be expanded in a real implementation
    model_map = {
        "product": "app.models.inventory.Product",
        "customer": "app.models.crm.Customer",
        "order": "app.models.sales.SalesOrder",
        "invoice": "app.models.accounting.Invoice",
        "user": "app.models.user.User",
    }
    
    try:
        # For now, return None as model loading would require imports
        # In production, this would fetch the current state from the database
        return None
    except Exception as e:
        logger.error(f"Error capturing old values: {e}")
        return None


def _extract_values(obj: Any) -> Optional[dict]:
    """
    Extract values from an object for audit logging.
    
    Args:
        obj: Object to extract from
        
    Returns:
        Dictionary of values
    """
    if obj is None:
        return None
    
    if isinstance(obj, dict):
        return obj
    
    # Check if it's a SQLAlchemy model
    if hasattr(obj, '__table__'):
        values = {}
        for column in obj.__table__.columns:
            value = getattr(obj, column.name, None)
            if isinstance(value, UUID):
                value = str(value)
            elif isinstance(value, datetime):
                value = value.isoformat()
            values[column.name] = value
        return values
    
    # Try to convert to dict
    if hasattr(obj, 'to_dict'):
        return obj.to_dict()
    
    return None


def _calculate_changes(old_values: dict, new_values: dict) -> dict:
    """
    Calculate the changes between old and new values.
    
    Args:
        old_values: Previous values
        new_values: New values
        
    Returns:
        Dictionary of changes
    """
    if not old_values or not new_values:
        return {}
    
    changes = {}
    
    # Find all keys from both dictionaries
    all_keys = set(old_values.keys()) | set(new_values.keys())
    
    for key in all_keys:
        old_val = old_values.get(key)
        new_val = new_values.get(key)
        
        if old_val != new_val:
            changes[key] = {
                "old": old_val,
                "new": new_val
            }
    
    return changes


def _generate_description(log: AuditLog) -> str:
    """
    Generate a human-readable description for an audit log.
    
    Args:
        log: AuditLog instance
        
    Returns:
        Description string
    """
    action = log.action.value if log.action else "unknown"
    resource = log.resource_type
    
    if log.resource_name:
        return f"{action.title()} {resource}: {log.resource_name}"
    
    return f"{action.title()} {resource}"


# ========================================
# Convenience Functions
# ========================================

async def log_action(
    db: AsyncSession,
    action: AuditAction,
    resource_type: str,
    resource_id: Optional[str] = None,
    resource_name: Optional[str] = None,
    old_values: Optional[dict] = None,
    new_values: Optional[dict] = None,
    description: Optional[str] = None,
    metadata: Optional[dict] = None
):
    """
    Convenience function to log an action.
    
    Args:
        db: Database session
        action: AuditAction enum
        resource_type: Type of resource
        resource_id: Resource ID
        resource_name: Human-readable name
        old_values: Previous values
        new_values: New values
        description: Description
        metadata: Additional metadata
    """
    changes = _calculate_changes(old_values or {}, new_values or {}) if old_values and new_values else None
    
    await _write_audit_log(
        db=db,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        old_values=old_values,
        new_values=new_values,
        changes=changes,
        context=get_audit_context(),
        description=description,
        metadata=metadata
    )


async def log_login(db: AsyncSession, user_id: UUID, success: bool = True, ip_address: Optional[str] = None):
    """Log user login."""
    set_audit_context(user_id=user_id, ip_address=ip_address)
    await log_action(
        db=db,
        action=AuditAction.LOGIN if success else AuditAction.LOGIN_FAILED,
        resource_type="user",
        resource_id=str(user_id),
        description=f"User login {'successful' if success else 'failed'}"
    )


async def log_logout(db: AsyncSession, user_id: UUID, ip_address: Optional[str] = None):
    """Log user logout."""
    set_audit_context(user_id=user_id, ip_address=ip_address)
    await log_action(
        db=db,
        action=AuditAction.LOGOUT,
        resource_type="user",
        resource_id=str(user_id),
        description="User logged out"
    )


async def log_export(
    db: AsyncSession,
    resource_type: str,
    format: str,
    record_count: int,
    ip_address: Optional[str] = None
):
    """Log data export."""
    await log_action(
        db=db,
        action=AuditAction.EXPORT,
        resource_type=resource_type,
        description=f"Exported {record_count} {resource_type} records as {format}",
        metadata={"format": format, "record_count": record_count}
    )


async def log_import(
    db: AsyncSession,
    resource_type: str,
    record_count: int,
    success_count: int,
    error_count: int
):
    """Log data import."""
    await log_action(
        db=db,
        action=AuditAction.IMPORT,
        resource_type=resource_type,
        description=f"Imported {success_count}/{record_count} {resource_type} records",
        metadata={
            "total_records": record_count,
            "success_count": success_count,
            "error_count": error_count
        }
    )


# Need to import timedelta for AuditQuery
from datetime import timedelta
