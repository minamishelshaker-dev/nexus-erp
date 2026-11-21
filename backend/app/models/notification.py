"""
Nexus ERP - Notification System Models
=======================================

This module implements a comprehensive notification system
supporting in-app notifications, email delivery, and real-time updates.

Features:
- In-app notifications with real-time updates
- Email notifications with templates
- Notification preferences per user
- Bulk notifications
- Notification grouping and archiving
- WebSocket support for real-time delivery
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
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional, List, Dict, Any
import enum
import uuid

from app.models.base import BaseModel, TenantMixin


class NotificationType(str, enum.Enum):
    """Notification type enumeration."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    APPROVAL = "approval"
    REMINDER = "reminder"
    SYSTEM = "system"


class NotificationPriority(str, enum.Enum):
    """Notification priority enumeration."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(str, enum.Enum):
    """Notification status enumeration."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    ARCHIVED = "archived"
    FAILED = "failed"


class NotificationChannel(str, enum.Enum):
    """Notification delivery channel."""
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"


class Notification(BaseModel, TenantMixin):
    """
    Notification Model
    
    Represents a notification to be delivered to one or more users.
    """
    
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_tenant", "tenant_id"),
        Index("ix_notifications_recipient", "recipient_id"),
        Index("ix_notifications_status", "status"),
        Index("ix_notifications_type", "notification_type"),
        Index("ix_notifications_created", "created_at"),
        Index("ix_notifications_read", "is_read", "recipient_id"),
    )
    
    # Recipient
    recipient_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="User who will receive the notification"
    )
    
    # Notification Content
    title: str = Column(
        String(200),
        nullable=False,
        doc="Notification title"
    )
    
    message: str = Column(
        Text,
        nullable=False,
        doc="Notification message body"
    )
    
    notification_type: NotificationType = Column(
        SQLEnum(NotificationType),
        default=NotificationType.INFO,
        nullable=False,
        doc="Type of notification"
    )
    
    priority: NotificationPriority = Column(
        SQLEnum(NotificationPriority),
        default=NotificationPriority.NORMAL,
        nullable=False,
        doc="Notification priority"
    )
    
    # Source/Reference
    source_type: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Source entity type (e.g., 'sale_order', 'workflow')"
    )
    
    source_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Source entity ID"
    )
    
    source_number: Optional[str] = Column(
        String(50),
        nullable=True,
        doc="Source document number for display"
    )
    
    # Action Link
    action_url: Optional[str] = Column(
        String(500),
        nullable=True,
        doc="URL to navigate when notification is clicked"
    )
    
    action_text: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Text for action button"
    )
    
    # Status
    status: NotificationStatus = Column(
        SQLEnum(NotificationStatus),
        default=NotificationStatus.PENDING,
        nullable=False,
        doc="Delivery status"
    )
    
    is_read: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether notification has been read"
    )
    
    read_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When notification was read"
    )
    
    # Delivery Channels
    channels: List[str] = Column(
        ARRAY(String),
        default=["in_app"],
        nullable=False,
        doc="Delivery channels"
    )
    
    # Email Details
    email_sent: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether email was sent"
    )
    
    email_sent_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When email was sent"
    )
    
    email_error: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Email delivery error message"
    )
    
    # Additional Data
    data: Dict[str, Any] = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Additional notification data"
    )
    
    # Expiry
    expires_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When notification expires"
    )
    
    # Grouping
    group_key: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Key for grouping related notifications"
    )
    
    # Archive
    is_archived: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether notification is archived"
    )
    
    archived_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When notification was archived"
    )
    
    # Relationships
    recipient: Mapped["User"] = relationship(
        "User",
        foreign_keys=[recipient_id]
    )


class NotificationPreference(BaseModel):
    """
    Notification Preference Model
    
    User preferences for notification delivery.
    """
    
    __tablename__ = "notification_preferences"
    __table_args__ = (
        Index("ix_notification_preferences_user", "user_id"),
        UniqueConstraint("user_id", "notification_category", name="uq_user_notification_pref"),
    )
    
    user_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="User for these preferences"
    )
    
    # Category (e.g., 'workflow', 'sales', 'inventory', 'system')
    notification_category: str = Column(
        String(50),
        nullable=False,
        doc="Category of notifications"
    )
    
    # Channel Preferences
    enable_in_app: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Enable in-app notifications"
    )
    
    enable_email: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Enable email notifications"
    )
    
    enable_sms: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Enable SMS notifications"
    )
    
    enable_push: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Enable push notifications"
    )
    
    # Priority Filter
    minimum_priority: NotificationPriority = Column(
        SQLEnum(NotificationPriority),
        default=NotificationPriority.LOW,
        nullable=False,
        doc="Minimum priority to receive notifications"
    )
    
    # Digest Settings
    digest_enabled: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Enable notification digest"
    )
    
    digest_frequency: Optional[str] = Column(
        String(20),
        nullable=True,
        doc="Digest frequency: 'immediate', 'hourly', 'daily', 'weekly'"
    )
    
    digest_time: Optional[str] = Column(
        String(5),
        nullable=True,
        doc="Time for daily/weekly digest (HH:MM)"
    )
    
    # Quiet Hours
    quiet_hours_enabled: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Enable quiet hours"
    )
    
    quiet_hours_start: Optional[str] = Column(
        String(5),
        nullable=True,
        doc="Quiet hours start time (HH:MM)"
    )
    
    quiet_hours_end: Optional[str] = Column(
        String(5),
        nullable=True,
        doc="Quiet hours end time (HH:MM)"
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User"
    )


class NotificationTemplate(BaseModel, TenantMixin):
    """
    Notification Template Model
    
    Email and notification templates for consistent messaging.
    """
    
    __tablename__ = "notification_templates"
    __table_args__ = (
        Index("ix_notification_templates_tenant", "tenant_id"),
        Index("ix_notification_templates_code", "code"),
        UniqueConstraint("code", "tenant_id", name="uq_notification_template_code"),
    )
    
    # Template Identification
    code: str = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Unique template code"
    )
    
    name: str = Column(
        String(200),
        nullable=False,
        doc="Template name"
    )
    
    description: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Template description"
    )
    
    category: str = Column(
        String(50),
        nullable=False,
        doc="Template category"
    )
    
    # Email Content
    subject_template: str = Column(
        String(500),
        nullable=False,
        doc="Email subject template (supports Jinja2)"
    )
    
    body_template: str = Column(
        Text,
        nullable=False,
        doc="Email body template (HTML, supports Jinja2)"
    )
    
    text_template: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Plain text email template"
    )
    
    # In-App Content
    title_template: Optional[str] = Column(
        String(200),
        nullable=True,
        doc="In-app notification title template"
    )
    
    message_template: Optional[str] = Column(
        Text,
        nullable=True,
        doc="In-app notification message template"
    )
    
    # Default Values
    default_type: NotificationType = Column(
        SQLEnum(NotificationType),
        default=NotificationType.INFO,
        nullable=False,
        doc="Default notification type"
    )
    
    default_priority: NotificationPriority = Column(
        SQLEnum(NotificationPriority),
        default=NotificationPriority.NORMAL,
        nullable=False,
        doc="Default notification priority"
    )
    
    default_channels: List[str] = Column(
        ARRAY(String),
        default=["in_app", "email"],
        nullable=False,
        doc="Default delivery channels"
    )
    
    # Available Variables
    available_variables: Dict[str, Any] = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Available template variables and their descriptions"
    )
    
    # Status
    is_active: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether template is active"
    )
    
    is_system: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="System template (cannot be deleted)"
    )


class NotificationBatch(BaseModel, TenantMixin):
    """
    Notification Batch Model
    
    Tracks bulk notification operations.
    """
    
    __tablename__ = "notification_batches"
    __table_args__ = (
        Index("ix_notification_batches_tenant", "tenant_id"),
        Index("ix_notification_batches_status", "status"),
    )
    
    # Batch Information
    name: str = Column(
        String(200),
        nullable=False,
        doc="Batch name/description"
    )
    
    status: str = Column(
        String(20),
        default="pending",
        nullable=False,
        doc="Batch status: pending, processing, completed, failed"
    )
    
    # Template
    template_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("notification_templates.id", ondelete="SET NULL"),
        nullable=True,
        doc="Template used for this batch"
    )
    
    # Content Override
    title: Optional[str] = Column(
        String(200),
        nullable=True,
        doc="Override title"
    )
    
    message: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Override message"
    )
    
    # Recipients
    total_recipients: int = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total number of recipients"
    )
    
    recipient_criteria: Dict[str, Any] = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Criteria for recipient selection"
    )
    
    # Statistics
    sent_count: int = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of notifications sent"
    )
    
    delivered_count: int = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of notifications delivered"
    )
    
    failed_count: int = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of failed notifications"
    )
    
    # Timing
    scheduled_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Scheduled send time"
    )
    
    started_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When batch processing started"
    )
    
    completed_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When batch processing completed"
    )
    
    # Additional Data
    context: Dict[str, Any] = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Template context data"
    )
    
    error_details: Dict[str, Any] = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Error details if batch failed"
    )


class NotificationSubscription(BaseModel):
    """
    Notification Subscription Model
    
    Tracks user subscriptions to notification channels (for WebSocket, Push).
    """
    
    __tablename__ = "notification_subscriptions"
    __table_args__ = (
        Index("ix_notification_subscriptions_user", "user_id"),
        Index("ix_notification_subscriptions_device", "device_id"),
    )
    
    user_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="User for this subscription"
    )
    
    # Channel
    channel: NotificationChannel = Column(
        SQLEnum(NotificationChannel),
        nullable=False,
        doc="Subscription channel"
    )
    
    # Device Info
    device_id: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Device identifier"
    )
    
    device_type: Optional[str] = Column(
        String(50),
        nullable=True,
        doc="Device type: desktop, mobile, tablet"
    )
    
    device_name: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Device name"
    )
    
    # Subscription Details
    endpoint: Optional[str] = Column(
        String(500),
        nullable=True,
        doc="Push subscription endpoint"
    )
    
    p256dh_key: Optional[str] = Column(
        String(200),
        nullable=True,
        doc="Push encryption key"
    )
    
    auth_key: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Push auth key"
    )
    
    # Status
    is_active: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether subscription is active"
    )
    
    last_used_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Last time subscription was used"
    )
    
    # User Agent
    user_agent: Optional[str] = Column(
        String(500),
        nullable=True,
        doc="User agent string"
    )


# Import User model at the end to avoid circular import
from app.models.user import User
