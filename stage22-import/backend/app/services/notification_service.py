"""
Nexus ERP - Notification Service
================================

Comprehensive notification system including:
- Multi-channel notifications (in-app, email, webhook, push)
- Notification templates
- User preferences
- Batch notifications
- Real-time WebSocket delivery
- Notification history and archiving
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Callable, Awaitable
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, update
from sqlalchemy.orm import selectinload
import logging
import asyncio
import json
import aiohttp
from dataclasses import dataclass, field
from enum import Enum
from jinja2 import Template, Environment, BaseLoader
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from app.models.notification import (
    Notification, NotificationType, NotificationPriority, NotificationStatus,
    NotificationChannel, NotificationPreference, NotificationTemplate,
    NotificationBatch, NotificationSubscription
)
from app.models.user import User

logger = logging.getLogger(__name__)


class DeliveryResult(str, Enum):
    """Delivery result status."""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    SKIPPED = "skipped"
    RETRY = "retry"


@dataclass
class NotificationPayload:
    """Notification payload for delivery."""
    notification_id: UUID
    recipient_id: UUID
    title: str
    message: str
    notification_type: NotificationType
    priority: NotificationPriority
    channels: List[NotificationChannel]
    action_url: Optional[str] = None
    action_text: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    template_id: Optional[UUID] = None
    template_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeliveryReport:
    """Report of notification delivery."""
    notification_id: UUID
    channel: NotificationChannel
    status: DeliveryResult
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0


class NotificationService:
    """
    Notification Service
    
    Provides comprehensive notification capabilities:
    - Multi-channel delivery
    - Template rendering
    - User preferences
    - Batch operations
    - Real-time delivery
    """
    
    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self._channel_handlers: Dict[NotificationChannel, Callable] = {}
        self._websocket_manager: Optional[Any] = None
        self._register_default_handlers()
        self._jinja_env = Environment(loader=BaseLoader())

    async def _get_tenant_user(self, user_id: UUID) -> Optional[User]:
        """Return an active user only when they belong to this tenant."""
        result = await self.db.execute(
            select(User).where(
                User.id == user_id,
                User.tenant_id == self.tenant_id,
                User.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def _get_tenant_notification(self, notification_id: UUID) -> Optional[Notification]:
        """Fetch a notification within the service tenant boundary."""
        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()
    
    def _register_default_handlers(self):
        """Register default channel handlers."""
        self._channel_handlers[NotificationChannel.IN_APP] = self._deliver_in_app
        self._channel_handlers[NotificationChannel.EMAIL] = self._deliver_email
        self._channel_handlers[NotificationChannel.WEBHOOK] = self._deliver_webhook
        self._channel_handlers[NotificationChannel.PUSH] = self._deliver_push
        self._channel_handlers[NotificationChannel.SMS] = self._deliver_sms
    
    def set_websocket_manager(self, manager: Any):
        """Set WebSocket connection manager for real-time delivery."""
        self._websocket_manager = manager
    
    # ========================================
    # Notification Creation
    # ========================================
    
    async def create_notification(
        self,
        recipient_id: UUID,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channels: Optional[List[NotificationChannel]] = None,
        source_type: Optional[str] = None,
        source_id: Optional[UUID] = None,
        source_number: Optional[str] = None,
        action_url: Optional[str] = None,
        action_text: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None,
        group_key: Optional[str] = None
    ) -> Notification:
        """
        Create a new notification.
        
        Args:
            recipient_id: User who will receive the notification
            title: Notification title
            message: Notification message body
            notification_type: Type of notification
            priority: Priority level
            channels: Delivery channels (default: in_app)
            source_type: Source entity type
            source_id: Source entity ID
            source_number: Source document number
            action_url: URL to navigate when clicked
            action_text: Text for action button
            data: Additional data
            expires_at: Expiration date
            group_key: Key for grouping related notifications
            
        Returns:
            Created Notification record
        """
        # Default channels
        if not channels:
            channels = [NotificationChannel.IN_APP]

        if not await self._get_tenant_user(recipient_id):
            raise ValueError("Notification recipient does not belong to this tenant")
        
        # Check user preferences
        enabled_channels = await self._filter_channels_by_preference(
            recipient_id, notification_type, priority, channels
        )
        
        notification = Notification(
            recipient_id=recipient_id,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            channels=[ch.value for ch in enabled_channels],
            source_type=source_type,
            source_id=source_id,
            source_number=source_number,
            action_url=action_url,
            action_text=action_text,
            data=data or {},
            expires_at=expires_at,
            group_key=group_key,
            status=NotificationStatus.PENDING,
            tenant_id=self.tenant_id
        )
        
        self.db.add(notification)
        await self.db.flush()
        
        # Delivery is intentionally left pending. Do not spawn a background task
        # with this request-scoped AsyncSession; a durable outbox/worker must own
        # delivery after the transaction commits.
        return notification
    
    async def create_from_template(
        self,
        template_code: str,
        recipient_id: UUID,
        context: Dict[str, Any],
        channels: Optional[List[NotificationChannel]] = None,
        source_type: Optional[str] = None,
        source_id: Optional[UUID] = None,
        source_number: Optional[str] = None,
        action_url: Optional[str] = None,
        action_text: Optional[str] = None
    ) -> Notification:
        """
        Create notification from a template.
        
        Args:
            template_code: Template code
            recipient_id: Recipient user ID
            context: Template context variables
            channels: Override default channels
            source_type: Source entity type
            source_id: Source entity ID
            source_number: Source document number
            action_url: Action URL
            action_text: Action button text
            
        Returns:
            Created Notification record
        """
        # Get template
        template = await self.get_template(template_code)
        if not template:
            raise ValueError(f"Template '{template_code}' not found")
        
        # Render template
        title = self._render_template(template.title_template, context)
        message = self._render_template(template.body_template, context)
        
        # Use default channels if not specified
        if not channels:
            channels = [NotificationChannel(ch) for ch in template.default_channels]
        
        return await self.create_notification(
            recipient_id=recipient_id,
            title=title,
            message=message,
            notification_type=template.default_type,
            priority=template.default_priority,
            channels=channels,
            source_type=source_type,
            source_id=source_id,
            source_number=source_number,
            action_url=action_url or self._render_template(template.message_template or "", context),
            action_text=action_text,
            data=context
        )
    
    async def create_batch(
        self,
        recipient_ids: List[UUID],
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channels: Optional[List[NotificationChannel]] = None,
        source_type: Optional[str] = None,
        source_id: Optional[UUID] = None,
        scheduled_at: Optional[datetime] = None
    ) -> NotificationBatch:
        """
        Create batch notifications for multiple recipients.
        
        Args:
            recipient_ids: List of recipient user IDs
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            priority: Priority level
            channels: Delivery channels
            source_type: Source entity type
            source_id: Source entity ID
            scheduled_at: Scheduled delivery time
            
        Returns:
            NotificationBatch record
        """
        unique_recipient_ids = list(dict.fromkeys(recipient_ids))
        if not unique_recipient_ids:
            raise ValueError("A notification batch requires at least one recipient")
        recipient_result = await self.db.execute(
            select(User.id).where(
                User.id.in_(unique_recipient_ids),
                User.tenant_id == self.tenant_id,
                User.is_deleted == False,
            )
        )
        valid_recipient_ids = set(recipient_result.scalars().all())
        if valid_recipient_ids != set(unique_recipient_ids):
            raise ValueError("All notification recipients must belong to this tenant")

        batch = NotificationBatch(
            name=f"Batch: {title[:50]}",
            status="pending",
            title=title,
            message=message,
            total_recipients=len(unique_recipient_ids),
            recipient_criteria={"recipient_ids": [str(rid) for rid in unique_recipient_ids]},
            context={
                "notification_type": notification_type.value,
                "priority": priority.value,
                "channels": [ch.value for ch in (channels or [NotificationChannel.IN_APP])]
            },
            scheduled_at=scheduled_at,
            tenant_id=self.tenant_id
        )
        
        self.db.add(batch)
        await self.db.flush()
        
        # Processing is deferred until a durable worker/outbox is configured.
        # Running it in a fire-and-forget task would reuse this request session.
        return batch
    
    async def _process_batch(
        self,
        batch_id: UUID,
        recipient_ids: List[UUID]
    ) -> None:
        """Process batch notifications."""
        batch_result = await self.db.execute(
            select(NotificationBatch).where(
                NotificationBatch.id == batch_id,
                NotificationBatch.tenant_id == self.tenant_id,
            )
        )
        batch = batch_result.scalar_one_or_none()
        if not batch:
            return
        
        batch.status = "processing"
        batch.started_at = datetime.utcnow()
        await self.db.flush()
        
        context = batch.context
        notification_type = NotificationType(context.get("notification_type", "info"))
        priority = NotificationPriority(context.get("priority", "normal"))
        channels = [NotificationChannel(ch) for ch in context.get("channels", ["in_app"])]
        
        sent = 0
        failed = 0
        
        for recipient_id in recipient_ids:
            try:
                await self.create_notification(
                    recipient_id=recipient_id,
                    title=batch.title,
                    message=batch.message,
                    notification_type=notification_type,
                    priority=priority,
                    channels=channels
                )
                sent += 1
            except Exception as e:
                logger.error(f"Failed to send notification to {recipient_id}: {e}")
                failed += 1
        
        batch.sent_count = sent
        batch.failed_count = failed
        batch.delivered_count = 0  # Notifications remain pending until a delivery worker runs.
        batch.status = "queued" if failed == 0 else "partially_queued"
        batch.completed_at = None
        await self.db.flush()
    
    # ========================================
    # Delivery
    # ========================================
    
    async def _deliver_notification(
        self,
        notification_id: UUID,
        channels: List[NotificationChannel]
    ) -> List[DeliveryReport]:
        """Deliver notification through specified channels."""
        notification = await self._get_tenant_notification(notification_id)
        if not notification:
            return []
        
        reports = []
        
        for channel in channels:
            handler = self._channel_handlers.get(channel)
            if not handler:
                logger.warning(f"No handler for channel: {channel}")
                continue
            
            try:
                result = await handler(notification)
                reports.append(result)
                
                if result.status == DeliveryResult.SUCCESS:
                    if channel == NotificationChannel.EMAIL:
                        notification.email_sent = True
                        notification.email_sent_at = datetime.utcnow()
                    notification.status = NotificationStatus.SENT
                
            except Exception as e:
                logger.error(f"Failed to deliver via {channel}: {e}")
                reports.append(DeliveryReport(
                    notification_id=notification_id,
                    channel=channel,
                    status=DeliveryResult.FAILED,
                    error_message=str(e)
                ))
        
        await self.db.flush()
        return reports
    
    async def _deliver_in_app(self, notification: Notification) -> DeliveryReport:
        """Deliver in-app notification via WebSocket."""
        try:
            if self._websocket_manager:
                # Send real-time notification
                await self._websocket_manager.send_to_user(
                    str(notification.recipient_id),
                    {
                        "type": "notification",
                        "data": {
                            "id": str(notification.id),
                            "title": notification.title,
                            "message": notification.message,
                            "type": notification.notification_type.value,
                            "priority": notification.priority.value,
                            "action_url": notification.action_url,
                            "action_text": notification.action_text,
                            "created_at": notification.created_at.isoformat()
                        }
                    }
                )
            
            notification.status = NotificationStatus.DELIVERED
            return DeliveryReport(
                notification_id=notification.id,
                channel=NotificationChannel.IN_APP,
                status=DeliveryResult.SUCCESS,
                delivered_at=datetime.utcnow()
            )
            
        except Exception as e:
            return DeliveryReport(
                notification_id=notification.id,
                channel=NotificationChannel.IN_APP,
                status=DeliveryResult.FAILED,
                error_message=str(e)
            )
    
    async def _deliver_email(self, notification: Notification) -> DeliveryReport:
        """Deliver email notification."""
        try:
            # Get recipient email
            user = await self._get_tenant_user(notification.recipient_id)
            if not user or not user.email:
                return DeliveryReport(
                    notification_id=notification.id,
                    channel=NotificationChannel.EMAIL,
                    status=DeliveryResult.SKIPPED,
                    error_message="No email address for recipient"
                )
            
            # Send email (would integrate with actual email service)
            # For now, just log
            logger.info(f"Sending email to {user.email}: {notification.title}")
            
            # Mark as sent
            notification.email_sent = True
            notification.email_sent_at = datetime.utcnow()
            
            return DeliveryReport(
                notification_id=notification.id,
                channel=NotificationChannel.EMAIL,
                status=DeliveryResult.SUCCESS,
                delivered_at=datetime.utcnow()
            )
            
        except Exception as e:
            notification.email_error = str(e)
            return DeliveryReport(
                notification_id=notification.id,
                channel=NotificationChannel.EMAIL,
                status=DeliveryResult.FAILED,
                error_message=str(e)
            )
    
    async def _deliver_webhook(self, notification: Notification) -> DeliveryReport:
        """Deliver webhook notification."""
        try:
            # Get webhook URL from notification data
            webhook_url = notification.data.get("webhook_url")
            if not webhook_url:
                return DeliveryReport(
                    notification_id=notification.id,
                    channel=NotificationChannel.WEBHOOK,
                    status=DeliveryResult.SKIPPED,
                    error_message="No webhook URL configured"
                )
            
            # Prepare payload
            payload = {
                "id": str(notification.id),
                "title": notification.title,
                "message": notification.message,
                "type": notification.notification_type.value,
                "priority": notification.priority.value,
                "source_type": notification.source_type,
                "source_id": str(notification.source_id) if notification.source_id else None,
                "data": notification.data,
                "created_at": notification.created_at.isoformat()
            }
            
            # Send webhook
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status >= 200 and response.status < 300:
                        return DeliveryReport(
                            notification_id=notification.id,
                            channel=NotificationChannel.WEBHOOK,
                            status=DeliveryResult.SUCCESS,
                            delivered_at=datetime.utcnow()
                        )
                    else:
                        return DeliveryReport(
                            notification_id=notification.id,
                            channel=NotificationChannel.WEBHOOK,
                            status=DeliveryResult.FAILED,
                            error_message=f"Webhook returned status {response.status}"
                        )
                        
        except asyncio.TimeoutError:
            return DeliveryReport(
                notification_id=notification.id,
                channel=NotificationChannel.WEBHOOK,
                status=DeliveryResult.RETRY,
                error_message="Webhook timeout"
            )
        except Exception as e:
            return DeliveryReport(
                notification_id=notification.id,
                channel=NotificationChannel.WEBHOOK,
                status=DeliveryResult.FAILED,
                error_message=str(e)
            )
    
    async def _deliver_push(self, notification: Notification) -> DeliveryReport:
        """Deliver push notification."""
        try:
            # Get user's push subscriptions
            result = await self.db.execute(
                select(NotificationSubscription)
                .join(User, User.id == NotificationSubscription.user_id)
                .where(
                    NotificationSubscription.user_id == notification.recipient_id,
                    NotificationSubscription.channel == NotificationChannel.PUSH,
                    NotificationSubscription.is_active == True,
                    User.tenant_id == self.tenant_id,
                    User.is_deleted == False,
                )
            )
            subscriptions = result.scalars().all()
            
            if not subscriptions:
                return DeliveryReport(
                    notification_id=notification.id,
                    channel=NotificationChannel.PUSH,
                    status=DeliveryResult.SKIPPED,
                    error_message="No active push subscriptions"
                )
            
            # Would send push notifications to each subscription
            # For now, just log
            for sub in subscriptions:
                logger.info(f"Sending push to {sub.device_id}: {notification.title}")
            
            return DeliveryReport(
                notification_id=notification.id,
                channel=NotificationChannel.PUSH,
                status=DeliveryResult.SUCCESS,
                delivered_at=datetime.utcnow()
            )
            
        except Exception as e:
            return DeliveryReport(
                notification_id=notification.id,
                channel=NotificationChannel.PUSH,
                status=DeliveryResult.FAILED,
                error_message=str(e)
            )
    
    async def _deliver_sms(self, notification: Notification) -> DeliveryReport:
        """Deliver SMS notification."""
        try:
            # Get recipient phone
            user = await self._get_tenant_user(notification.recipient_id)
            if not user or not hasattr(user, 'phone') or not user.phone:
                return DeliveryReport(
                    notification_id=notification.id,
                    channel=NotificationChannel.SMS,
                    status=DeliveryResult.SKIPPED,
                    error_message="No phone number for recipient"
                )
            
            # Would integrate with SMS provider
            logger.info(f"Sending SMS to {user.phone}: {notification.message[:160]}")
            
            return DeliveryReport(
                notification_id=notification.id,
                channel=NotificationChannel.SMS,
                status=DeliveryResult.SUCCESS,
                delivered_at=datetime.utcnow()
            )
            
        except Exception as e:
            return DeliveryReport(
                notification_id=notification.id,
                channel=NotificationChannel.SMS,
                status=DeliveryResult.FAILED,
                error_message=str(e)
            )
    
    # ========================================
    # User Preferences
    # ========================================
    
    async def get_user_preferences(
        self,
        user_id: UUID
    ) -> List[NotificationPreference]:
        """Get notification preferences for a user."""
        if not await self._get_tenant_user(user_id):
            raise ValueError("User does not belong to this tenant")
        result = await self.db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id
            )
        )
        return result.scalars().all()
    
    async def set_user_preference(
        self,
        user_id: UUID,
        category: str,
        enable_in_app: bool = True,
        enable_email: bool = True,
        enable_sms: bool = False,
        enable_push: bool = False,
        minimum_priority: NotificationPriority = NotificationPriority.LOW,
        digest_enabled: bool = False,
        digest_frequency: Optional[str] = None,
        quiet_hours_enabled: bool = False,
        quiet_hours_start: Optional[str] = None,
        quiet_hours_end: Optional[str] = None
    ) -> NotificationPreference:
        """Set notification preference for a user."""
        if not await self._get_tenant_user(user_id):
            raise ValueError("User does not belong to this tenant")
        # Check for existing preference
        result = await self.db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id,
                NotificationPreference.notification_category == category
            )
        )
        preference = result.scalar_one_or_none()
        
        if preference:
            # Update existing
            preference.enable_in_app = enable_in_app
            preference.enable_email = enable_email
            preference.enable_sms = enable_sms
            preference.enable_push = enable_push
            preference.minimum_priority = minimum_priority
            preference.digest_enabled = digest_enabled
            preference.digest_frequency = digest_frequency
            preference.quiet_hours_enabled = quiet_hours_enabled
            preference.quiet_hours_start = quiet_hours_start
            preference.quiet_hours_end = quiet_hours_end
        else:
            # Create new
            preference = NotificationPreference(
                user_id=user_id,
                notification_category=category,
                enable_in_app=enable_in_app,
                enable_email=enable_email,
                enable_sms=enable_sms,
                enable_push=enable_push,
                minimum_priority=minimum_priority,
                digest_enabled=digest_enabled,
                digest_frequency=digest_frequency,
                quiet_hours_enabled=quiet_hours_enabled,
                quiet_hours_start=quiet_hours_start,
                quiet_hours_end=quiet_hours_end
            )
            self.db.add(preference)
        
        await self.db.flush()
        return preference
    
    async def _filter_channels_by_preference(
        self,
        user_id: UUID,
        notification_type: NotificationType,
        priority: NotificationPriority,
        channels: List[NotificationChannel]
    ) -> List[NotificationChannel]:
        """Filter channels based on user preferences."""
        # Get user preferences for this category
        category = notification_type.value
        result = await self.db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id,
                NotificationPreference.notification_category == category
            )
        )
        preference = result.scalar_one_or_none()
        
        if not preference:
            # No preference set, use provided channels
            return channels
        
        # Check minimum priority
        priority_order = {
            NotificationPriority.LOW: 0,
            NotificationPriority.NORMAL: 1,
            NotificationPriority.HIGH: 2,
            NotificationPriority.URGENT: 3
        }
        if priority_order.get(priority, 0) < priority_order.get(preference.minimum_priority, 0):
            return []  # Below minimum priority
        
        # Check quiet hours
        if preference.quiet_hours_enabled:
            now = datetime.now().strftime("%H:%M")
            if preference.quiet_hours_start and preference.quiet_hours_end:
                if preference.quiet_hours_start <= now < preference.quiet_hours_end:
                    # In quiet hours, skip non-urgent notifications
                    if priority != NotificationPriority.URGENT:
                        return []
        
        # Filter channels
        enabled = []
        if NotificationChannel.IN_APP in channels and preference.enable_in_app:
            enabled.append(NotificationChannel.IN_APP)
        if NotificationChannel.EMAIL in channels and preference.enable_email:
            enabled.append(NotificationChannel.EMAIL)
        if NotificationChannel.SMS in channels and preference.enable_sms:
            enabled.append(NotificationChannel.SMS)
        if NotificationChannel.PUSH in channels and preference.enable_push:
            enabled.append(NotificationChannel.PUSH)
        
        return enabled
    
    # ========================================
    # Templates
    # ========================================
    
    async def create_template(
        self,
        code: str,
        name: str,
        category: str,
        subject_template: str,
        body_template: str,
        text_template: Optional[str] = None,
        title_template: Optional[str] = None,
        message_template: Optional[str] = None,
        default_type: NotificationType = NotificationType.INFO,
        default_priority: NotificationPriority = NotificationPriority.NORMAL,
        default_channels: Optional[List[str]] = None,
        available_variables: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
        is_system: bool = False
    ) -> NotificationTemplate:
        """Create a notification template."""
        template = NotificationTemplate(
            code=code,
            name=name,
            description=description,
            category=category,
            subject_template=subject_template,
            body_template=body_template,
            text_template=text_template,
            title_template=title_template,
            message_template=message_template,
            default_type=default_type,
            default_priority=default_priority,
            default_channels=default_channels or ["in_app", "email"],
            available_variables=available_variables or {},
            is_system=is_system,
            tenant_id=self.tenant_id
        )
        
        self.db.add(template)
        await self.db.flush()
        return template
    
    async def get_template(self, code: str) -> Optional[NotificationTemplate]:
        """Get template by code."""
        result = await self.db.execute(
            select(NotificationTemplate).where(
                NotificationTemplate.code == code,
                NotificationTemplate.tenant_id == self.tenant_id,
                NotificationTemplate.is_active == True
            )
        )
        return result.scalar_one_or_none()
    
    async def get_templates(
        self,
        category: Optional[str] = None
    ) -> List[NotificationTemplate]:
        """Get all templates, optionally filtered by category."""
        query = select(NotificationTemplate).where(
            NotificationTemplate.tenant_id == self.tenant_id,
            NotificationTemplate.is_active == True
        )
        
        if category:
            query = query.where(NotificationTemplate.category == category)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    def _render_template(self, template: str, context: Dict[str, Any]) -> str:
        """Render a template string with context."""
        if not template:
            return ""
        
        try:
            jinja_template = self._jinja_env.from_string(template)
            return jinja_template.render(**context)
        except Exception as e:
            logger.error(f"Template rendering error: {e}")
            return template
    
    # ========================================
    # Notification Management
    # ========================================
    
    async def get_user_notifications(
        self,
        user_id: UUID,
        is_read: Optional[bool] = None,
        notification_type: Optional[NotificationType] = None,
        priority: Optional[NotificationPriority] = None,
        is_archived: bool = False,
        skip: int = 0,
        limit: int = 50
    ) -> List[Notification]:
        """Get notifications for a user."""
        if not await self._get_tenant_user(user_id):
            raise ValueError("User does not belong to this tenant")
        query = select(Notification).where(
            Notification.recipient_id == user_id,
            Notification.tenant_id == self.tenant_id,
            Notification.is_archived == is_archived
        )
        
        if is_read is not None:
            query = query.where(Notification.is_read == is_read)
        if notification_type:
            query = query.where(Notification.notification_type == notification_type)
        if priority:
            query = query.where(Notification.priority == priority)
        
        query = query.order_by(desc(Notification.created_at)).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_unread_count(self, user_id: UUID) -> int:
        """Get count of unread notifications for a user."""
        if not await self._get_tenant_user(user_id):
            raise ValueError("User does not belong to this tenant")
        result = await self.db.execute(
            select(func.count()).select_from(Notification).where(
                Notification.recipient_id == user_id,
                Notification.tenant_id == self.tenant_id,
                Notification.is_read == False,
                Notification.is_archived == False
            )
        )
        return result.scalar() or 0
    
    async def mark_as_read(
        self,
        notification_id: UUID,
        user_id: UUID
    ) -> Notification:
        """Mark a notification as read."""
        notification = await self._get_tenant_notification(notification_id)
        if not notification:
            raise ValueError(f"Notification {notification_id} not found")
        
        if notification.recipient_id != user_id:
            raise PermissionError("Cannot mark another user's notification")
        
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        notification.status = NotificationStatus.READ
        
        await self.db.flush()
        return notification
    
    async def mark_all_as_read(self, user_id: UUID) -> int:
        """Mark all notifications as read for a user."""
        if not await self._get_tenant_user(user_id):
            raise ValueError("User does not belong to this tenant")
        result = await self.db.execute(
            update(Notification).where(
                Notification.recipient_id == user_id,
                Notification.tenant_id == self.tenant_id,
                Notification.is_read == False
            ).values(
                is_read=True,
                read_at=datetime.utcnow(),
                status=NotificationStatus.READ
            )
        )
        await self.db.flush()
        return result.rowcount
    
    async def archive(
        self,
        notification_id: UUID,
        user_id: UUID
    ) -> Notification:
        """Archive a notification."""
        notification = await self._get_tenant_notification(notification_id)
        if not notification:
            raise ValueError(f"Notification {notification_id} not found")
        
        if notification.recipient_id != user_id:
            raise PermissionError("Cannot archive another user's notification")
        
        notification.is_archived = True
        notification.archived_at = datetime.utcnow()
        
        await self.db.flush()
        return notification
    
    async def delete_notification(
        self,
        notification_id: UUID,
        user_id: UUID
    ) -> bool:
        """Delete a notification."""
        notification = await self._get_tenant_notification(notification_id)
        if not notification:
            return False
        
        if notification.recipient_id != user_id:
            raise PermissionError("Cannot delete another user's notification")
        
        await self.db.delete(notification)
        await self.db.flush()
        return True
    
    # ========================================
    # Notification Subscriptions (for Push)
    # ========================================
    
    async def subscribe(
        self,
        user_id: UUID,
        channel: NotificationChannel,
        device_id: Optional[str] = None,
        device_type: Optional[str] = None,
        device_name: Optional[str] = None,
        endpoint: Optional[str] = None,
        p256dh_key: Optional[str] = None,
        auth_key: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> NotificationSubscription:
        """Subscribe a user to a notification channel."""
        if not await self._get_tenant_user(user_id):
            raise ValueError("User does not belong to this tenant")
        # Check for existing subscription
        query = select(NotificationSubscription).where(
            NotificationSubscription.user_id == user_id,
            NotificationSubscription.channel == channel
        )
        
        if device_id:
            query = query.where(NotificationSubscription.device_id == device_id)
        
        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing
            existing.endpoint = endpoint
            existing.p256dh_key = p256dh_key
            existing.auth_key = auth_key
            existing.is_active = True
            existing.last_used_at = datetime.utcnow()
            existing.user_agent = user_agent
            await self.db.flush()
            return existing
        
        # Create new subscription
        subscription = NotificationSubscription(
            user_id=user_id,
            channel=channel,
            device_id=device_id,
            device_type=device_type,
            device_name=device_name,
            endpoint=endpoint,
            p256dh_key=p256dh_key,
            auth_key=auth_key,
            user_agent=user_agent,
            is_active=True,
            last_used_at=datetime.utcnow()
        )
        
        self.db.add(subscription)
        await self.db.flush()
        return subscription
    
    async def unsubscribe(
        self,
        user_id: UUID,
        channel: NotificationChannel,
        device_id: Optional[str] = None
    ) -> bool:
        """Unsubscribe a user from a notification channel."""
        if not await self._get_tenant_user(user_id):
            raise ValueError("User does not belong to this tenant")
        query = select(NotificationSubscription).where(
            NotificationSubscription.user_id == user_id,
            NotificationSubscription.channel == channel
        )
        
        if device_id:
            query = query.where(NotificationSubscription.device_id == device_id)
        
        result = await self.db.execute(query)
        subscription = result.scalar_one_or_none()
        
        if subscription:
            subscription.is_active = False
            await self.db.flush()
            return True
        
        return False
    
    # ========================================
    # Notification History
    # ========================================
    
    async def get_notification_history(
        self,
        user_id: Optional[UUID] = None,
        notification_type: Optional[NotificationType] = None,
        status: Optional[NotificationStatus] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get notification history for reporting."""
        if user_id and not await self._get_tenant_user(user_id):
            raise ValueError("User does not belong to this tenant")
        query = select(Notification).where(
            Notification.tenant_id == self.tenant_id
        )
        
        if user_id:
            query = query.where(Notification.recipient_id == user_id)
        if notification_type:
            query = query.where(Notification.notification_type == notification_type)
        if status:
            query = query.where(Notification.status == status)
        if date_from:
            query = query.where(Notification.created_at >= date_from)
        if date_to:
            query = query.where(Notification.created_at < date_to + timedelta(days=1))
        
        query = query.order_by(desc(Notification.created_at)).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        notifications = result.scalars().all()
        
        return [
            {
                "id": str(n.id),
                "recipient_id": str(n.recipient_id),
                "title": n.title,
                "message": n.message,
                "type": n.notification_type.value,
                "priority": n.priority.value,
                "status": n.status.value,
                "channels": n.channels,
                "source_type": n.source_type,
                "source_id": str(n.source_id) if n.source_id else None,
                "is_read": n.is_read,
                "read_at": n.read_at,
                "created_at": n.created_at,
                "email_sent": n.email_sent,
                "email_sent_at": n.email_sent_at
            }
            for n in notifications
        ]
    
    async def get_notification_stats(
        self,
        date_from: date,
        date_to: date
    ) -> Dict[str, Any]:
        """Get notification statistics."""
        # Total notifications
        total_result = await self.db.execute(
            select(func.count()).select_from(Notification).where(
                Notification.tenant_id == self.tenant_id,
                Notification.created_at >= date_from,
                Notification.created_at < date_to + timedelta(days=1)
            )
        )
        total = total_result.scalar() or 0
        
        # By type
        type_result = await self.db.execute(
            select(
                Notification.notification_type,
                func.count().label("count")
            ).where(
                Notification.tenant_id == self.tenant_id,
                Notification.created_at >= date_from,
                Notification.created_at < date_to + timedelta(days=1)
            ).group_by(Notification.notification_type)
        )
        by_type = {row.notification_type.value: row.count for row in type_result}
        
        # By status
        status_result = await self.db.execute(
            select(
                Notification.status,
                func.count().label("count")
            ).where(
                Notification.tenant_id == self.tenant_id,
                Notification.created_at >= date_from,
                Notification.created_at < date_to + timedelta(days=1)
            ).group_by(Notification.status)
        )
        by_status = {row.status.value: row.count for row in status_result}
        
        # Read rate
        read_result = await self.db.execute(
            select(func.count()).select_from(Notification).where(
                Notification.tenant_id == self.tenant_id,
                Notification.created_at >= date_from,
                Notification.created_at < date_to + timedelta(days=1),
                Notification.is_read == True
            )
        )
        read_count = read_result.scalar() or 0
        read_rate = (read_count / total * 100) if total > 0 else 0
        
        return {
            "period": {
                "date_from": date_from,
                "date_to": date_to
            },
            "total": total,
            "by_type": by_type,
            "by_status": by_status,
            "read_rate": read_rate,
            "email_sent_count": sum(1 for n in by_status if n == "sent")  # Simplified
        }
