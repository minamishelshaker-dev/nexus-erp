"""
Nexus ERP - Base Model Module
=============================

This module provides the base model class with common fields
and functionality shared across all models in the system.

Features:
- Automatic timestamp management
- Soft delete support
- UUID primary keys
- Audit trail fields
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    Boolean,
    ForeignKey,
    String,
    func,
    event,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declared_attr, DeclarativeBase
import uuid
from typing import Optional


class Base(DeclarativeBase):
    """Shared SQLAlchemy declarative registry for every ERP model."""
    __allow_unmapped__ = True


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at timestamps.
    
    These fields are automatically managed by SQLAlchemy events.
    """
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when the record was created"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Timestamp when the record was last updated"
    )


class SoftDeleteMixin:
    """
    Mixin that adds soft delete functionality.
    
    Records are never physically deleted, only marked as deleted.
    This enables data recovery and audit trails.
    """
    
    is_deleted = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Soft delete flag - True if record is deleted"
    )
    
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when the record was soft deleted"
    )
    
    deleted_by_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="ID of user who deleted the record"
    )


class AuditMixin:
    """
    Mixin that adds audit trail fields.
    
    Tracks who created and last modified each record.
    """
    
    @declared_attr
    def created_by_id(cls):
        return Column(
            UUID(as_uuid=True),
            nullable=True,
            doc="ID of user who created the record"
        )
    
    @declared_attr
    def updated_by_id(cls):
        return Column(
            UUID(as_uuid=True),
            nullable=True,
            doc="ID of user who last updated the record"
        )


class TenantMixin:
    """
    Mixin for multi-tenant support.
    
    All records are scoped to a specific tenant.
    """
    
    @declared_attr
    def tenant_id(cls):
        return Column(
            UUID(as_uuid=True),
            ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            doc="ID of the tenant this record belongs to"
        )


class BaseModel(Base, TimestampMixin, SoftDeleteMixin, AuditMixin):
    """
    Base model class with all common functionality.
    
    All models should inherit from this class to get:
    - Automatic timestamps
    - Soft delete support
    - Audit trail fields
    - Common methods
    """
    
    __abstract__ = True
    __allow_unmapped__ = True  # Existing models use legacy Column + plain type annotations.
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the record"
    )
    
    def soft_delete(self, user_id: Optional[uuid.UUID] = None):
        """
        Mark the record as deleted without removing it.
        
        Args:
            user_id: ID of the user performing the deletion
        """
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.deleted_by_id = user_id
    
    def restore(self):
        """
        Restore a soft-deleted record.
        """
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by_id = None
    
    def update_audit_fields(self, user_id: Optional[uuid.UUID] = None, is_create: bool = False):
        """
        Update audit fields based on the operation.
        
        Args:
            user_id: ID of the user performing the operation
            is_create: Whether this is a create operation
        """
        if is_create:
            self.created_by_id = user_id
        self.updated_by_id = user_id
    
    def to_dict(self, exclude: Optional[list] = None) -> dict:
        """
        Convert model instance to dictionary.
        
        Args:
            exclude: List of field names to exclude
            
        Returns:
            Dictionary representation of the model
        """
        exclude = exclude or []
        result = {}
        
        for column in self.__table__.columns:
            if column.name not in exclude:
                attribute_name = self.__mapper__.get_property_by_column(column).key
                value = getattr(self, attribute_name)
                if isinstance(value, uuid.UUID):
                    value = str(value)
                elif isinstance(value, datetime):
                    value = value.isoformat()
                result[column.name] = value
        
        return result
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"
