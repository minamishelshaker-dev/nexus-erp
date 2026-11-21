"""
Nexus ERP - Activity Timeline Models
=====================================

This module implements activity tracking for all entities,
providing an audit trail, version history, and activity feeds.

Features:
- Track all entity changes
- Version history with restore capability
- Activity feed per record
- Aggregated activity dashboard
- Change comparison
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
    Integer,
    Numeric,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional, List, Dict, Any
import enum
import uuid

from app.models.base import BaseModel, TenantMixin


class ActivityType(str, enum.Enum):
    """Activity type enumeration."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESTORE = "restore"
    STATUS_CHANGE = "status_change"
    APPROVE = "approve"
    REJECT = "reject"
    COMMENT = "comment"
    ATTACHMENT = "attachment"
    EMAIL = "email"
    PRINT = "print"
    EXPORT = "export"
    IMPORT = "import"
    LOGIN = "login"
    LOGOUT = "logout"
    CUSTOM = "custom"


class ActivitySeverity(str, enum.Enum):
    """Activity severity level."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EntityActivity(BaseModel, TenantMixin):
    """
    Entity Activity Model
    
    Tracks all activities performed on entities in the system.
    Provides complete audit trail and activity timeline.
    """
    
    __tablename__ = "entity_activities"
    __table_args__ = (
        Index("ix_entity_activities_tenant", "tenant_id"),
        Index("ix_entity_activities_entity", "entity_type", "entity_id"),
        Index("ix_entity_activities_user", "user_id"),
        Index("ix_entity_activities_type", "activity_type"),
        Index("ix_entity_activities_created", "created_at"),
        Index("ix_entity_activities_entity_date", "entity_type", "entity_id", "created_at"),
    )
    
    # Entity Reference
    entity_type: str = Column(
        String(100),
        nullable=False,
        doc="Type of entity (e.g., 'sale_order', 'customer', 'invoice')"
    )
    
    entity_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        nullable=False,
        doc="ID of the entity"
    )
    
    entity_display_name: Optional[str] = Column(
        String(200),
        nullable=True,
        doc="Display name/number of the entity"
    )
    
    # Activity Details
    activity_type: ActivityType = Column(
        SQLEnum(ActivityType),
        nullable=False,
        doc="Type of activity"
    )
    
    activity_subtype: Optional[str] = Column(
        String(50),
        nullable=True,
        doc="Sub-type for more specific categorization"
    )
    
    description: str = Column(
        Text,
        nullable=False,
        doc="Human-readable description of the activity"
    )
    
    severity: ActivitySeverity = Column(
        SQLEnum(ActivitySeverity),
        default=ActivitySeverity.INFO,
        nullable=False,
        doc="Activity severity level"
    )
    
    # User who performed the action
    user_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User who performed the activity"
    )
    
    user_name: Optional[str] = Column(
        String(200),
        nullable=True,
        doc="User name at time of activity (for historical accuracy)"
    )
    
    # Change Details
    field_name: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Name of field that changed"
    )
    
    old_value: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Value before change (string representation)"
    )
    
    new_value: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Value after change (string representation)"
    )
    
    old_value_display: Optional[str] = Column(
        String(500),
        nullable=True,
        doc="Human-readable old value"
    )
    
    new_value_display: Optional[str] = Column(
        String(500),
        nullable=True,
        doc="Human-readable new value"
    )
    
    # Complete Change Data
    changes: Dict[str, Any] = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Complete change details (field -> {old, new})"
    )
    
    # Related Entities
    related_entity_type: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Type of related entity"
    )
    
    related_entity_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="ID of related entity"
    )
    
    # Context & Metadata
    context: Dict[str, Any] = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Additional context data"
    )
    
    ip_address: Optional[str] = Column(
        String(45),
        nullable=True,
        doc="IP address of user"
    )
    
    user_agent: Optional[str] = Column(
        String(500),
        nullable=True,
        doc="User agent string"
    )
    
    # Version Reference
    version_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("entity_versions.id", ondelete="SET NULL"),
        nullable=True,
        doc="Reference to version snapshot if created"
    )
    
    # Parent Activity (for grouped activities)
    parent_activity_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("entity_activities.id", ondelete="SET NULL"),
        nullable=True,
        doc="Parent activity for grouped activities"
    )
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[user_id]
    )
    
    version: Mapped[Optional["EntityVersion"]] = relationship(
        "EntityVersion", back_populates="activities", foreign_keys=[version_id]
    )
    
    child_activities: Mapped[List["EntityActivity"]] = relationship(
        "EntityActivity", back_populates="parent_activity", foreign_keys=[parent_activity_id], lazy="dynamic"
    )
    parent_activity: Mapped[Optional["EntityActivity"]] = relationship(
        "EntityActivity", back_populates="child_activities", remote_side="EntityActivity.id", foreign_keys=[parent_activity_id]
    )


class EntityVersion(BaseModel, TenantMixin):
    """
    Entity Version Model
    
    Stores snapshots of entity states for version history and restore.
    """
    
    __tablename__ = "entity_versions"
    __table_args__ = (
        Index("ix_entity_versions_tenant", "tenant_id"),
        Index("ix_entity_versions_entity", "entity_type", "entity_id"),
        Index("ix_entity_versions_number", "entity_type", "entity_id", "version_number"),
    )
    
    # Entity Reference
    entity_type: str = Column(
        String(100),
        nullable=False,
        doc="Type of entity"
    )
    
    entity_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        nullable=False,
        doc="ID of the entity"
    )
    
    entity_display_name: Optional[str] = Column(
        String(200),
        nullable=True,
        doc="Display name at this version"
    )
    
    # Version Details
    version_number: int = Column(
        Integer,
        nullable=False,
        doc="Version number (sequential)"
    )
    
    # Complete Snapshot
    snapshot: Dict[str, Any] = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Complete entity snapshot as JSON"
    )
    
    # Related Data Snapshots
    related_snapshots: Dict[str, Any] = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Snapshots of related entities (e.g., line items)"
    )
    
    # Version Info
    change_summary: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Summary of changes from previous version"
    )
    
    changes: Dict[str, Any] = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Detailed changes from previous version"
    )
    
    # User who created this version
    user_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User who created this version"
    )
    
    user_name: Optional[str] = Column(
        String(200),
        nullable=True,
        doc="User name at time of version creation"
    )
    
    # Activity Reference
    activity_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("entity_activities.id", ondelete="SET NULL"),
        nullable=True,
        doc="Activity that created this version"
    )
    
    # Status
    is_current: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this is the current version"
    )
    
    is_restored: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this version was restored from a previous version"
    )
    
    restored_from_version_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("entity_versions.id", ondelete="SET NULL"),
        nullable=True,
        doc="Version this was restored from (if restored)"
    )
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[user_id]
    )
    
    activities: Mapped[List["EntityActivity"]] = relationship(
        "EntityActivity", back_populates="version", foreign_keys="EntityActivity.version_id"
    )


class ActivityFeed(BaseModel, TenantMixin):
    """
    Activity Feed Model
    
    Pre-computed activity feed for efficient querying.
    """
    
    __tablename__ = "activity_feeds"
    __table_args__ = (
        Index("ix_activity_feeds_tenant", "tenant_id"),
        Index("ix_activity_feeds_user", "user_id"),
        Index("ix_activity_feeds_created", "created_at"),
    )
    
    # User whose feed this belongs to
    user_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="User whose feed this belongs to"
    )
    
    # Activity Reference
    activity_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("entity_activities.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the activity"
    )
    
    # Read Status
    is_read: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this feed item has been read"
    )
    
    read_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the feed item was read"
    )
    
    # Relevance Score (for ranking)
    relevance_score: float = Column(
        Numeric(5, 2),
        default=1.0,
        nullable=False,
        doc="Relevance score for ranking"
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id]
    )
    
    activity: Mapped["EntityActivity"] = relationship(
        "EntityActivity",
        foreign_keys=[activity_id]
    )


class ActivityComment(BaseModel, TenantMixin):
    """
    Activity Comment Model
    
    Comments on activities for collaboration.
    """
    
    __tablename__ = "activity_comments"
    __table_args__ = (
        Index("ix_activity_comments_activity", "activity_id"),
        Index("ix_activity_comments_tenant", "tenant_id"),
    )
    
    activity_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("entity_activities.id", ondelete="CASCADE"),
        nullable=False,
        doc="Activity being commented on"
    )
    
    # Comment Content
    content: str = Column(
        Text,
        nullable=False,
        doc="Comment content"
    )
    
    # User who commented
    user_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="User who made the comment"
    )
    
    user_name: Optional[str] = Column(
        String(200),
        nullable=True,
        doc="User name at time of comment"
    )
    
    # Parent Comment (for threaded comments)
    parent_comment_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("activity_comments.id", ondelete="CASCADE"),
        nullable=True,
        doc="Parent comment for threaded replies"
    )
    
    # Mentions
    mentions: List[str] = Column(
        JSONB,
        default=list,
        nullable=False,
        doc="List of user IDs mentioned in the comment"
    )
    
    # Relationships
    activity: Mapped["EntityActivity"] = relationship(
        "EntityActivity",
        foreign_keys=[activity_id]
    )
    
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id]
    )
    
    replies: Mapped[List["ActivityComment"]] = relationship(
        "ActivityComment", back_populates="parent_comment", foreign_keys=[parent_comment_id],
        cascade="all, delete-orphan"
    )
    parent_comment: Mapped[Optional["ActivityComment"]] = relationship(
        "ActivityComment", back_populates="replies", remote_side="ActivityComment.id",
        foreign_keys=[parent_comment_id]
    )


class ActivitySubscription(BaseModel):
    """
    Activity Subscription Model
    
    User subscriptions to entity activities.
    """
    
    __tablename__ = "activity_subscriptions"
    __table_args__ = (
        Index("ix_activity_subscriptions_user", "user_id"),
        UniqueConstraint("user_id", "entity_type", "entity_id", name="uq_activity_subscription"),
    )
    
    user_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="User who subscribed"
    )
    
    # Entity being subscribed to
    entity_type: str = Column(
        String(100),
        nullable=False,
        doc="Type of entity"
    )
    
    entity_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        nullable=False,
        doc="ID of entity"
    )
    
    # Subscription Preferences
    notify_on_create: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Notify on create"
    )
    
    notify_on_update: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Notify on update"
    )
    
    notify_on_delete: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Notify on delete"
    )
    
    notify_on_comment: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Notify on comments"
    )
    
    notify_on_status_change: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Notify on status changes"
    )
    
    # Email Notifications
    email_notifications: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Send email notifications"
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id]
    )


# Import User model at the end to avoid circular import
from app.models.user import User
