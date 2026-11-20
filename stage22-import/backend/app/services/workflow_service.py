"""
Nexus ERP - Workflow Automation Service
=======================================

Comprehensive workflow automation including:
- Workflow definition and management
- Trigger system (events, schedules, conditions)
- Action execution (notifications, approvals, webhooks)
- Rule engine with conditional logic
- Pre-built workflow templates
- Background task integration
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Callable, Awaitable
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload
import logging
import asyncio
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from croniter import croniter
import aiohttp

from app.models.workflow import (
    Workflow, WorkflowStep, WorkflowStepType, WorkflowStatus,
    WorkflowTriggerType, WorkflowExecution, WorkflowExecutionStatus,
    WorkflowStepExecution, WorkflowStepExecutionStatus,
    WorkflowApproval, ApprovalDecision, WorkflowTemplate
)
from app.models.user import User
from app.models.notification import Notification, NotificationType, NotificationPriority

logger = logging.getLogger(__name__)


class TriggerEvent(str, Enum):
    """System trigger events."""
    # Sales events
    SALE_ORDER_CREATED = "sale_order_created"
    SALE_ORDER_CONFIRMED = "sale_order_confirmed"
    SALE_ORDER_CANCELLED = "sale_order_cancelled"
    INVOICE_CREATED = "invoice_created"
    INVOICE_POSTED = "invoice_posted"
    INVOICE_PAID = "invoice_paid"
    PAYMENT_RECEIVED = "payment_received"
    
    # Inventory events
    STOCK_LOW = "stock_low"
    STOCK_OUT = "stock_out"
    STOCK_MOVE_DONE = "stock_move_done"
    INVENTORY_ADJUSTMENT = "inventory_adjustment"
    
    # Purchase events
    PURCHASE_ORDER_CREATED = "purchase_order_created"
    PURCHASE_ORDER_CONFIRMED = "purchase_order_confirmed"
    PURCHASE_ORDER_RECEIVED = "purchase_order_received"
    
    # Accounting events
    JOURNAL_ENTRY_POSTED = "journal_entry_posted"
    PAYMENT_CREATED = "payment_created"
    
    # Customer events
    CUSTOMER_CREATED = "customer_created"
    CUSTOMER_INACTIVE = "customer_inactive"
    
    # System events
    SCHEDULED_DAILY = "scheduled_daily"
    SCHEDULED_WEEKLY = "scheduled_weekly"
    SCHEDULED_MONTHLY = "scheduled_monthly"


class ConditionOperator(str, Enum):
    """Condition operators for rule engine."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    BETWEEN = "between"


class ActionType(str, Enum):
    """Workflow action types."""
    SEND_NOTIFICATION = "send_notification"
    SEND_EMAIL = "send_email"
    CALL_WEBHOOK = "call_webhook"
    UPDATE_FIELD = "update_field"
    CREATE_RECORD = "create_record"
    REQUEST_APPROVAL = "request_approval"
    CHANGE_STATUS = "change_status"
    CREATE_TASK = "create_task"
    SEND_SMS = "send_sms"


@dataclass
class Condition:
    """Condition definition for rule engine."""
    field: str
    operator: ConditionOperator
    value: Any
    data_type: str = "string"  # string, number, date, boolean


@dataclass
class Rule:
    """Rule definition combining conditions and actions."""
    name: str
    conditions: List[Condition]
    condition_logic: str = "all"  # all, any
    actions: List[Dict[str, Any]] = field(default_factory=list)
    priority: int = 0


@dataclass
class WorkflowContext:
    """Context passed during workflow execution."""
    execution_id: UUID
    workflow_id: UUID
    tenant_id: UUID
    trigger_type: WorkflowTriggerType
    record_type: str
    record_id: UUID
    record_data: Dict[str, Any]
    variables: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[UUID] = None
    history: List[Dict[str, Any]] = field(default_factory=list)


class WorkflowService:
    """
    Workflow Automation Service
    
    Provides comprehensive workflow management including:
    - Workflow definition and configuration
    - Trigger handling
    - Action execution
    - Approval management
    - Background task integration
    """
    
    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self._action_handlers: Dict[str, Callable] = {}
        self._register_default_handlers()
    
    async def _get_tenant_workflow(self, workflow_id: UUID) -> Optional[Workflow]:
        """Load a workflow only when it belongs to this service tenant."""
        result = await self.db.execute(
            select(Workflow).where(
                Workflow.id == workflow_id,
                Workflow.tenant_id == self.tenant_id,
                Workflow.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def _get_tenant_execution(self, execution_id: UUID) -> Optional[WorkflowExecution]:
        """Load a workflow execution only within this tenant boundary."""
        result = await self.db.execute(
            select(WorkflowExecution).where(
                WorkflowExecution.id == execution_id,
                WorkflowExecution.tenant_id == self.tenant_id,
                WorkflowExecution.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def _get_tenant_approval(self, approval_id: UUID) -> Optional[WorkflowApproval]:
        """Load an approval through its tenant-owned execution parent."""
        result = await self.db.execute(
            select(WorkflowApproval)
            .join(WorkflowExecution, WorkflowApproval.execution_id == WorkflowExecution.id)
            .where(
                WorkflowApproval.id == approval_id,
                WorkflowExecution.tenant_id == self.tenant_id,
                WorkflowExecution.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    def _register_default_handlers(self):
        """Register default action handlers."""
        self._action_handlers[ActionType.SEND_NOTIFICATION] = self._handle_notification
        self._action_handlers[ActionType.SEND_EMAIL] = self._handle_email
        self._action_handlers[ActionType.CALL_WEBHOOK] = self._handle_webhook
        self._action_handlers[ActionType.UPDATE_FIELD] = self._handle_update_field
        self._action_handlers[ActionType.CREATE_RECORD] = self._handle_create_record
        self._action_handlers[ActionType.REQUEST_APPROVAL] = self._handle_request_approval
        self._action_handlers[ActionType.CHANGE_STATUS] = self._handle_change_status
    
    # ========================================
    # Workflow Definition Management
    # ========================================
    
    async def create_workflow(
        self,
        code: str,
        name: str,
        model_name: str,
        description: Optional[str] = None,
        trigger_type: WorkflowTriggerType = WorkflowTriggerType.MANUAL,
        trigger_config: Optional[Dict[str, Any]] = None,
        steps: Optional[List[Dict[str, Any]]] = None,
        config: Optional[Dict[str, Any]] = None,
        created_by_id: Optional[UUID] = None
    ) -> Workflow:
        """
        Create a new workflow definition.
        
        Args:
            code: Unique workflow code
            name: Workflow name
            model_name: Target model name
            description: Workflow description
            trigger_type: How workflow is triggered
            trigger_config: Trigger configuration
            steps: Workflow steps
            config: Additional configuration
            created_by_id: User creating the workflow
            
        Returns:
            Created Workflow record
        """
        # Check for duplicate code
        existing = await self.db.execute(
            select(Workflow).where(
                Workflow.code == code,
                Workflow.tenant_id == self.tenant_id,
                Workflow.is_deleted == False
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Workflow with code '{code}' already exists")
        
        # Create workflow
        workflow = Workflow(
            code=code,
            name=name,
            model_name=model_name,
            description=description,
            trigger_type=trigger_type,
            trigger_config=trigger_config or {},
            config=config or {},
            status=WorkflowStatus.DRAFT,
            tenant_id=self.tenant_id,
            created_by_id=created_by_id
        )
        
        self.db.add(workflow)
        await self.db.flush()
        
        # Create steps if provided
        if steps:
            for idx, step_data in enumerate(steps):
                step = WorkflowStep(
                    workflow_id=workflow.id,
                    code=step_data.get("code", f"step_{idx+1}"),
                    name=step_data.get("name", f"Step {idx+1}"),
                    description=step_data.get("description"),
                    sequence=step_data.get("sequence", (idx + 1) * 10),
                    step_type=step_data.get("step_type", WorkflowStepType.ACTION),
                    action_type=step_data.get("action_type"),
                    action_config=step_data.get("action_config", {}),
                    conditions=step_data.get("conditions", {}),
                    approvers=step_data.get("approvers", {}),
                    timeout_hours=step_data.get("timeout_hours"),
                    timeout_action=step_data.get("timeout_action")
                )
                self.db.add(step)
            
            await self.db.flush()
        
        return workflow
    
    async def update_workflow(
        self,
        workflow_id: UUID,
        **kwargs
    ) -> Workflow:
        """Update workflow definition."""
        workflow = await self._get_tenant_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        # Update allowed fields
        allowed_fields = [
            "name", "description", "trigger_type", "trigger_config",
            "config", "is_parallel", "auto_start", "allow_restart",
            "timeout_hours", "notify_on_start", "notify_on_complete",
            "notify_on_error", "notification_recipients"
        ]
        
        for field in allowed_fields:
            if field in kwargs:
                setattr(workflow, field, kwargs[field])
        
        await self.db.flush()
        return workflow
    
    async def activate_workflow(self, workflow_id: UUID) -> Workflow:
        """Activate a workflow for automatic triggering."""
        workflow = await self._get_tenant_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        # Validate workflow has steps
        steps = await self.db.execute(
            select(WorkflowStep).where(WorkflowStep.workflow_id == workflow_id)
        )
        if not steps.scalars().all():
            raise ValueError("Cannot activate workflow without steps")
        
        workflow.status = WorkflowStatus.ACTIVE
        await self.db.flush()
        return workflow
    
    async def deactivate_workflow(self, workflow_id: UUID) -> Workflow:
        """Deactivate a workflow."""
        workflow = await self._get_tenant_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow.status = WorkflowStatus.INACTIVE
        await self.db.flush()
        return workflow
    
    async def get_workflow(
        self,
        workflow_id: UUID,
        include_steps: bool = True
    ) -> Optional[Workflow]:
        """Get workflow by ID with optional steps."""
        query = select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.tenant_id == self.tenant_id,
            Workflow.is_deleted == False
        )
        
        if include_steps:
            query = query.options(selectinload(Workflow.steps))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_workflows(
        self,
        status: Optional[WorkflowStatus] = None,
        model_name: Optional[str] = None,
        trigger_type: Optional[WorkflowTriggerType] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Workflow]:
        """Get workflows with optional filters."""
        query = select(Workflow).where(
            Workflow.tenant_id == self.tenant_id,
            Workflow.is_deleted == False
        )
        
        if status:
            query = query.where(Workflow.status == status)
        if model_name:
            query = query.where(Workflow.model_name == model_name)
        if trigger_type:
            query = query.where(Workflow.trigger_type == trigger_type)
        
        query = query.order_by(desc(Workflow.created_at)).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    # ========================================
    # Trigger Handling
    # ========================================
    
    async def trigger_workflow(
        self,
        event: TriggerEvent,
        record_type: str,
        record_id: UUID,
        record_data: Dict[str, Any],
        user_id: Optional[UUID] = None,
        manual: bool = False
    ) -> List[WorkflowExecution]:
        """
        Trigger workflows based on an event.
        
        Args:
            event: The trigger event
            record_type: Type of record (e.g., 'sale_order')
            record_id: ID of the record
            record_data: Record data for condition evaluation
            user_id: User who triggered the event
            manual: Whether this is a manual trigger
            
        Returns:
            List of created workflow executions
        """
        # Find matching workflows
        workflows = await self._find_matching_workflows(event, record_type, record_data)
        
        executions = []
        for workflow in workflows:
            try:
                execution = await self._create_execution(
                    workflow=workflow,
                    record_type=record_type,
                    record_id=record_id,
                    record_data=record_data,
                    user_id=user_id,
                    trigger_type=WorkflowTriggerType.MANUAL if manual else workflow.trigger_type
                )
                executions.append(execution)
                
                # Start execution asynchronously
                asyncio.create_task(
                    self._execute_workflow(execution.id)
                )
            except Exception as e:
                logger.error(f"Failed to create execution for workflow {workflow.id}: {e}")
        
        return executions
    
    async def _find_matching_workflows(
        self,
        event: TriggerEvent,
        record_type: str,
        record_data: Dict[str, Any]
    ) -> List[Workflow]:
        """Find workflows that match the trigger event."""
        query = select(Workflow).where(
            Workflow.tenant_id == self.tenant_id,
            Workflow.status == WorkflowStatus.ACTIVE,
            Workflow.is_deleted == False,
            Workflow.model_name == record_type
        )
        
        result = await self.db.execute(query)
        workflows = result.scalars().all()
        
        matching = []
        for workflow in workflows:
            if await self._check_trigger_conditions(workflow, event, record_data):
                matching.append(workflow)
        
        return matching
    
    async def _check_trigger_conditions(
        self,
        workflow: Workflow,
        event: TriggerEvent,
        record_data: Dict[str, Any]
    ) -> bool:
        """Check if workflow trigger conditions are met."""
        trigger_config = workflow.trigger_config or {}
        
        # Check event match
        trigger_events = trigger_config.get("events", [])
        if trigger_events and event.value not in trigger_events:
            return False
        
        # Check conditions
        conditions = trigger_config.get("conditions", [])
        if conditions:
            return await self._evaluate_conditions(conditions, record_data)
        
        return True
    
    # ========================================
    # Workflow Execution
    # ========================================
    
    async def _create_execution(
        self,
        workflow: Workflow,
        record_type: str,
        record_id: UUID,
        record_data: Dict[str, Any],
        user_id: Optional[UUID],
        trigger_type: WorkflowTriggerType
    ) -> WorkflowExecution:
        """Create a new workflow execution."""
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            record_type=record_type,
            record_id=record_id,
            status=WorkflowExecutionStatus.PENDING,
            trigger_type=trigger_type,
            triggered_by_id=user_id,
            context={"record_data": record_data},
            input_data=record_data,
            tenant_id=self.tenant_id
        )
        
        self.db.add(execution)
        await self.db.flush()
        
        # Update workflow statistics
        workflow.total_executions += 1
        workflow.last_execution_at = datetime.utcnow()
        
        return execution
    
    async def _execute_workflow(self, execution_id: UUID) -> None:
        """Execute a workflow (runs in background)."""
        try:
            # Get execution with workflow and steps
            execution = await self._get_tenant_execution(execution_id)
            if not execution:
                logger.error(f"Execution {execution_id} not found")
                return
            
            workflow = await self._get_tenant_workflow(execution.workflow_id)
            if not workflow:
                logger.error(f"Workflow {execution.workflow_id} not found")
                return
            
            # Get steps
            steps_result = await self.db.execute(
                select(WorkflowStep).where(
                    WorkflowStep.workflow_id == workflow.id
                ).order_by(WorkflowStep.sequence)
            )
            steps = steps_result.scalars().all()
            
            # Update status to running
            execution.status = WorkflowExecutionStatus.RUNNING
            execution.started_at = datetime.utcnow()
            await self.db.flush()
            
            # Send start notification if configured
            if workflow.notify_on_start:
                await self._send_workflow_notification(
                    workflow, execution, "started"
                )
            
            # Execute steps
            context = WorkflowContext(
                execution_id=execution.id,
                workflow_id=workflow.id,
                tenant_id=self.tenant_id,
                trigger_type=execution.trigger_type,
                record_type=execution.record_type,
                record_id=execution.record_id,
                record_data=execution.input_data,
                variables=execution.context.get("variables", {}),
                user_id=execution.triggered_by_id
            )
            
            for step in steps:
                try:
                    result = await self._execute_step(step, context)
                    
                    if result.get("status") == "waiting":
                        execution.status = WorkflowExecutionStatus.PAUSED
                        await self.db.flush()
                        return
                    
                    if result.get("status") == "failed":
                        execution.status = WorkflowExecutionStatus.FAILED
                        execution.error_message = result.get("error")
                        await self.db.flush()
                        return
                    
                except Exception as e:
                    logger.error(f"Step {step.code} failed: {e}")
                    execution.status = WorkflowExecutionStatus.FAILED
                    execution.error_message = str(e)
                    execution.error_details = {"step_id": str(step.id), "error": str(e)}
                    await self.db.flush()
                    
                    # Send error notification
                    if workflow.notify_on_error:
                        await self._send_workflow_notification(
                            workflow, execution, "error"
                        )
                    
                    workflow.failed_executions += 1
                    return
            
            # All steps completed
            execution.status = WorkflowExecutionStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            execution.output_data = context.variables
            workflow.successful_executions += 1
            await self.db.flush()
            
            # Send completion notification
            if workflow.notify_on_complete:
                await self._send_workflow_notification(
                    workflow, execution, "completed"
                )
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            # Try to update execution status
            try:
                execution = await self._get_tenant_execution(execution_id)
                if execution:
                    execution.status = WorkflowExecutionStatus.FAILED
                    execution.error_message = str(e)
                    await self.db.flush()
            except Exception:
                pass
    
    async def _execute_step(
        self,
        step: WorkflowStep,
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """Execute a single workflow step."""
        # Create step execution record
        step_execution = WorkflowStepExecution(
            execution_id=context.execution_id,
            step_id=step.id,
            status=WorkflowStepExecutionStatus.RUNNING,
            started_at=datetime.utcnow(),
            input_data=context.record_data
        )
        self.db.add(step_execution)
        await self.db.flush()
        
        try:
            result = {}
            
            if step.step_type == WorkflowStepType.APPROVAL:
                result = await self._execute_approval_step(step, context)
            elif step.step_type == WorkflowStepType.NOTIFICATION:
                result = await self._execute_notification_step(step, context)
            elif step.step_type == WorkflowStepType.ACTION:
                result = await self._execute_action_step(step, context)
            elif step.step_type == WorkflowStepType.CONDITION:
                result = await self._execute_condition_step(step, context)
            elif step.step_type == WorkflowStepType.WEBHOOK:
                result = await self._execute_webhook_step(step, context)
            elif step.step_type == WorkflowStepType.WAIT:
                result = await self._execute_wait_step(step, context)
            
            step_execution.status = WorkflowStepExecutionStatus.COMPLETED
            step_execution.completed_at = datetime.utcnow()
            step_execution.output_data = result
            await self.db.flush()
            
            return result
            
        except Exception as e:
            step_execution.status = WorkflowStepExecutionStatus.FAILED
            step_execution.error_message = str(e)
            step_execution.completed_at = datetime.utcnow()
            await self.db.flush()
            
            return {"status": "failed", "error": str(e)}
    
    async def _execute_approval_step(
        self,
        step: WorkflowStep,
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """Execute an approval step."""
        # Get approvers
        approvers = step.approvers or {}
        user_ids = approvers.get("users", [])
        role_ids = approvers.get("roles", [])
        
        if not user_ids and not role_ids:
            raise ValueError(f"No approvers defined for step {step.code}")
        
        # Create approval requests
        all_approver_ids = list(user_ids)
        # Would also get users by role_ids here
        
        for approver_id in all_approver_ids:
            approval = WorkflowApproval(
                execution_id=context.execution_id,
                step_id=step.id,
                approver_id=approver_id,
                decision=None,  # Pending; tenant ownership is inherited through WorkflowExecution.
            )
            self.db.add(approval)
        
        await self.db.flush()
        
        # Send notification to approvers
        await self._notify_approvers(step, context, all_approver_ids)
        
        return {"status": "waiting", "waiting_for": "approval"}
    
    async def _execute_notification_step(
        self,
        step: WorkflowStep,
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """Execute a notification step."""
        config = step.action_config or {}
        
        recipients = config.get("recipients", [])
        template_id = config.get("template_id")
        
        # Create notifications
        for recipient_id in recipients:
            notification = Notification(
                recipient_id=recipient_id,
                title=self._render_template(config.get("title", ""), context),
                message=self._render_template(config.get("message", ""), context),
                notification_type=NotificationType.INFO,
                priority=NotificationPriority.NORMAL,
                source_type="workflow",
                source_id=context.workflow_id,
                tenant_id=self.tenant_id
            )
            self.db.add(notification)
        
        await self.db.flush()
        
        return {"status": "completed", "notifications_sent": len(recipients)}
    
    async def _execute_action_step(
        self,
        step: WorkflowStep,
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """Execute an action step."""
        action_type = step.action_type
        action_config = step.action_config or {}
        
        handler = self._action_handlers.get(action_type)
        if not handler:
            raise ValueError(f"Unknown action type: {action_type}")
        
        result = await handler(action_config, context)
        return result
    
    async def _execute_condition_step(
        self,
        step: WorkflowStep,
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """Execute a condition step."""
        conditions = step.conditions or {}
        condition_list = conditions.get("conditions", [])
        logic = conditions.get("logic", "all")
        
        result = await self._evaluate_conditions(condition_list, context.record_data, logic)
        
        return {
            "status": "completed",
            "result": result,
            "next_step": step.next_step_id if result else step.else_step_id
        }
    
    async def _execute_webhook_step(
        self,
        step: WorkflowStep,
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """Execute a webhook step."""
        config = step.action_config or {}
        url = config.get("url")
        method = config.get("method", "POST")
        headers = config.get("headers", {})
        body_template = config.get("body", {})
        
        if not url:
            raise ValueError("Webhook URL not configured")
        
        # Render body template
        body = json.dumps(self._render_dict(body_template, context))
        
        # Make HTTP request
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=method,
                url=url,
                headers=headers,
                data=body
            ) as response:
                response_text = await response.text()
                
                return {
                    "status": "completed",
                    "status_code": response.status,
                    "response": response_text[:500]  # Truncate
                }
    
    async def _execute_wait_step(
        self,
        step: WorkflowStep,
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """Execute a wait step."""
        config = step.action_config or {}
        wait_seconds = config.get("seconds", 0)
        wait_until = config.get("until")  # datetime string
        
        if wait_seconds > 0:
            await asyncio.sleep(min(wait_seconds, 60))  # Cap at 60 seconds
        
        return {"status": "completed"}
    
    # ========================================
    # Action Handlers
    # ========================================
    
    async def _handle_notification(
        self,
        config: Dict[str, Any],
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """Handle send notification action."""
        recipients = config.get("recipients", [])
        
        for recipient_id in recipients:
            notification = Notification(
                recipient_id=recipient_id,
                title=self._render_template(config.get("title", ""), context),
                message=self._render_template(config.get("message", ""), context),
                notification_type=NotificationType.INFO,
                priority=NotificationPriority.HIGH if config.get("priority") == "high" else NotificationPriority.NORMAL,
                source_type="workflow",
                source_id=context.workflow_id,
                tenant_id=self.tenant_id
            )
            self.db.add(notification)
        
        await self.db.flush()
        return {"status": "completed", "recipients_notified": len(recipients)}
    
    async def _handle_email(
        self,
        config: Dict[str, Any],
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """Handle send email action."""
        # Would integrate with email service
        logger.info(f"Sending email: {config.get('subject')}")
        return {"status": "completed", "email_sent": True}
    
    async def _handle_webhook(
        self,
        config: Dict[str, Any],
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """Handle call webhook action."""
        url = config.get("url")
        method = config.get("method", "POST")
        headers = config.get("headers", {})
        body = config.get("body", {})
        
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=method,
                url=url,
                headers=headers,
                json=self._render_dict(body, context)
            ) as response:
                return {
                    "status": "completed",
                    "status_code": response.status
                }
    
    async def _handle_update_field(
        self,
        config: Dict[str, Any],
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """Handle update field action."""
        field_name = config.get("field")
        field_value = self._render_template(config.get("value", ""), context)
        
        # Would update the record in database
        logger.info(f"Updating field {field_name} to {field_value}")
        
        return {"status": "completed", "field": field_name, "new_value": field_value}
    
    async def _handle_create_record(
        self,
        config: Dict[str, Any],
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """Handle create record action."""
        model_name = config.get("model")
        record_data = self._render_dict(config.get("data", {}), context)
        
        # Would create the record in database
        logger.info(f"Creating record in {model_name}: {record_data}")
        
        return {"status": "completed", "model": model_name}
    
    async def _handle_request_approval(
        self,
        config: Dict[str, Any],
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """Handle request approval action."""
        approvers = config.get("approvers", [])
        
        for approver_id in approvers:
            approval = WorkflowApproval(
                execution_id=context.execution_id,
                step_id=None,  # Not tied to a specific step
                approver_id=approver_id,
                decision=None,  # Pending; tenant ownership is inherited through WorkflowExecution.
            )
            self.db.add(approval)
        
        await self.db.flush()
        return {"status": "waiting", "waiting_for": "approval"}
    
    async def _handle_change_status(
        self,
        config: Dict[str, Any],
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """Handle change status action."""
        new_status = config.get("status")
        
        # Would update record status
        logger.info(f"Changing status to {new_status}")
        
        return {"status": "completed", "new_status": new_status}
    
    # ========================================
    # Approval Management
    # ========================================
    
    async def get_pending_approvals(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get pending approvals for a user."""
        query = select(WorkflowApproval).join(
            WorkflowExecution,
            WorkflowApproval.execution_id == WorkflowExecution.id,
        ).options(
            selectinload(WorkflowApproval.execution)
        ).where(
            WorkflowApproval.approver_id == user_id,
            WorkflowApproval.decision.is_(None),
            WorkflowExecution.tenant_id == self.tenant_id,
            WorkflowExecution.is_deleted.is_(False),
        ).order_by(desc(WorkflowApproval.created_at)).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        approvals = result.scalars().all()
        
        pending = []
        for approval in approvals:
            execution = approval.execution
            workflow = await self._get_tenant_workflow(execution.workflow_id)
            
            pending.append({
                "approval_id": str(approval.id),
                "execution_id": str(execution.id),
                "workflow_name": workflow.name if workflow else "Unknown",
                "record_type": execution.record_type,
                "record_id": str(execution.record_id),
                "created_at": approval.created_at,
                "record_data": execution.input_data
            })
        
        return pending
    
    async def approve(
        self,
        approval_id: UUID,
        user_id: UUID,
        comments: Optional[str] = None
    ) -> WorkflowApproval:
        """Approve a workflow step."""
        approval = await self._get_tenant_approval(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        
        if approval.approver_id != user_id:
            raise PermissionError("Only assigned approver can approve")
        
        if approval.decision is not None:
            raise ValueError("Approval already decided")
        
        approval.decision = ApprovalDecision.APPROVED
        approval.comments = comments
        approval.decided_at = datetime.utcnow()
        
        await self.db.flush()
        
        # Check if all approvals complete
        await self._check_approval_completion(approval.execution_id)
        
        return approval
    
    async def reject(
        self,
        approval_id: UUID,
        user_id: UUID,
        comments: Optional[str] = None
    ) -> WorkflowApproval:
        """Reject a workflow step."""
        approval = await self._get_tenant_approval(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        
        if approval.approver_id != user_id:
            raise PermissionError("Only assigned approver can reject")
        
        approval.decision = ApprovalDecision.REJECTED
        approval.comments = comments
        approval.decided_at = datetime.utcnow()
        
        await self.db.flush()
        
        # Mark execution as failed
        execution = await self._get_tenant_execution(approval.execution_id)
        if not execution:
            raise ValueError(f"Workflow execution {approval.execution_id} not found")
        execution.status = WorkflowExecutionStatus.CANCELLED
        execution.error_message = f"Rejected: {comments}"
        await self.db.flush()
        
        return approval
    
    async def _check_approval_completion(self, execution_id: UUID) -> None:
        """Check if all approvals are complete and continue workflow."""
        execution = await self._get_tenant_execution(execution_id)
        if not execution:
            return
        result = await self.db.execute(
            select(WorkflowApproval)
            .join(WorkflowExecution, WorkflowApproval.execution_id == WorkflowExecution.id)
            .where(
                WorkflowApproval.execution_id == execution_id,
                WorkflowExecution.tenant_id == self.tenant_id,
                WorkflowExecution.is_deleted.is_(False),
                WorkflowApproval.decision.is_(None),
            )
        )
        pending = result.scalars().all()
        
        if not pending:
            # All approvals complete, continue workflow
            asyncio.create_task(
                self._continue_workflow(execution_id)
            )
    
    async def _continue_workflow(self, execution_id: UUID) -> None:
        """Continue a paused workflow execution."""
        # Get next step and continue execution
        execution = await self._get_tenant_execution(execution_id)
        if execution and execution.status == WorkflowExecutionStatus.PAUSED:
            execution.status = WorkflowExecutionStatus.RUNNING
            await self.db.flush()
            await self._execute_workflow(execution_id)
    
    # ========================================
    # Condition Evaluation
    # ========================================
    
    async def _evaluate_conditions(
        self,
        conditions: List[Dict[str, Any]],
        data: Dict[str, Any],
        logic: str = "all"
    ) -> bool:
        """Evaluate a list of conditions against data."""
        results = []
        
        for condition in conditions:
            field = condition.get("field")
            operator = condition.get("operator", "equals")
            expected = condition.get("value")
            
            actual = self._get_nested_value(data, field)
            result = self._evaluate_condition(actual, operator, expected)
            results.append(result)
        
        if logic == "all":
            return all(results)
        else:  # any
            return any(results)
    
    def _evaluate_condition(
        self,
        actual: Any,
        operator: str,
        expected: Any
    ) -> bool:
        """Evaluate a single condition."""
        try:
            if operator == "equals":
                return actual == expected
            elif operator == "not_equals":
                return actual != expected
            elif operator == "greater_than":
                return actual > expected
            elif operator == "less_than":
                return actual < expected
            elif operator == "greater_than_or_equal":
                return actual >= expected
            elif operator == "less_than_or_equal":
                return actual <= expected
            elif operator == "contains":
                return expected in str(actual)
            elif operator == "not_contains":
                return expected not in str(actual)
            elif operator == "starts_with":
                return str(actual).startswith(expected)
            elif operator == "ends_with":
                return str(actual).endswith(expected)
            elif operator == "in":
                return actual in expected
            elif operator == "not_in":
                return actual not in expected
            elif operator == "is_null":
                return actual is None
            elif operator == "is_not_null":
                return actual is not None
            elif operator == "between":
                return expected[0] <= actual <= expected[1]
            else:
                return False
        except Exception:
            return False
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get a nested value from a dictionary using dot notation."""
        keys = path.split(".")
        value = data
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        
        return value
    
    # ========================================
    # Pre-built Workflows
    # ========================================
    
    async def create_invoice_approval_workflow(
        self,
        approval_threshold: Decimal = Decimal("10000"),
        approvers: List[str] = None,
        created_by_id: Optional[UUID] = None
    ) -> Workflow:
        """Create invoice approval workflow."""
        workflow = await self.create_workflow(
            code="invoice_approval",
            name="Invoice Approval Workflow",
            model_name="invoice",
            description=f"Requires approval for invoices over {approval_threshold}",
            trigger_type=WorkflowTriggerType.ON_CREATE,
            trigger_config={
                "events": ["invoice_created"],
                "conditions": [
                    {
                        "field": "amount_total",
                        "operator": "greater_than",
                        "value": float(approval_threshold)
                    }
                ]
            },
            steps=[
                {
                    "code": "request_approval",
                    "name": "Request Approval",
                    "step_type": WorkflowStepType.APPROVAL,
                    "sequence": 10,
                    "approvers": {
                        "users": approvers or []
                    }
                },
                {
                    "code": "notify_approved",
                    "name": "Notify on Approval",
                    "step_type": WorkflowStepType.NOTIFICATION,
                    "sequence": 20,
                    "action_config": {
                        "title": "Invoice Approved",
                        "message": "Invoice {{record_data.number}} has been approved."
                    },
                    "conditions": {
                        "previous_step_approved": True
                    }
                }
            ],
            created_by_id=created_by_id
        )
        
        return workflow
    
    async def create_low_stock_alert_workflow(
        self,
        threshold_quantity: Decimal = Decimal("10"),
        recipients: List[str] = None,
        created_by_id: Optional[UUID] = None
    ) -> Workflow:
        """Create low stock alert workflow."""
        workflow = await self.create_workflow(
            code="low_stock_alert",
            name="Low Stock Alert",
            model_name="product",
            description=f"Alert when stock falls below {threshold_quantity}",
            trigger_type=WorkflowTriggerType.ON_UPDATE,
            trigger_config={
                "events": ["stock_low"],
                "conditions": [
                    {
                        "field": "quantity_on_hand",
                        "operator": "less_than_or_equal",
                        "value": float(threshold_quantity)
                    }
                ]
            },
            steps=[
                {
                    "code": "send_alert",
                    "name": "Send Low Stock Alert",
                    "step_type": WorkflowStepType.NOTIFICATION,
                    "sequence": 10,
                    "action_config": {
                        "title": "Low Stock Alert",
                        "message": "Product {{record_data.sku}} - {{record_data.name}} is low on stock. Current: {{record_data.quantity_on_hand}}",
                        "recipients": recipients or []
                    }
                }
            ],
            created_by_id=created_by_id
        )
        
        return workflow
    
    async def create_payment_reminder_workflow(
        self,
        days_before_due: int = 7,
        recipients: List[str] = None,
        created_by_id: Optional[UUID] = None
    ) -> Workflow:
        """Create payment reminder workflow."""
        workflow = await self.create_workflow(
            code="payment_reminder",
            name="Payment Reminder",
            model_name="invoice",
            description=f"Send reminder {days_before_due} days before due date",
            trigger_type=WorkflowTriggerType.SCHEDULED,
            trigger_config={
                "schedule": "0 9 * * *",  # Daily at 9 AM
                "conditions": [
                    {
                        "field": "days_until_due",
                        "operator": "less_than_or_equal",
                        "value": days_before_due
                    },
                    {
                        "field": "state",
                        "operator": "in",
                        "value": ["posted", "partial"]
                    }
                ]
            },
            steps=[
                {
                    "code": "send_reminder",
                    "name": "Send Payment Reminder",
                    "step_type": WorkflowStepType.NOTIFICATION,
                    "sequence": 10,
                    "action_config": {
                        "title": "Payment Reminder",
                        "message": "Invoice {{record_data.number}} is due in {{record_data.days_until_due}} days.",
                        "recipients": recipients or []
                    }
                }
            ],
            created_by_id=created_by_id
        )
        
        return workflow
    
    # ========================================
    # Helper Methods
    # ========================================
    
    def _render_template(self, template: str, context: WorkflowContext) -> str:
        """Render a template string with context variables."""
        if not template:
            return ""
        
        # Simple variable substitution
        result = template
        for key, value in context.record_data.items():
            result = result.replace(f"{{{{record_data.{key}}}}}", str(value) if value else "")
        
        for key, value in context.variables.items():
            result = result.replace(f"{{{{variables.{key}}}}}", str(value) if value else "")
        
        return result
    
    def _render_dict(self, template: Dict[str, Any], context: WorkflowContext) -> Dict[str, Any]:
        """Render a dictionary template with context."""
        result = {}
        for key, value in template.items():
            if isinstance(value, str):
                result[key] = self._render_template(value, context)
            elif isinstance(value, dict):
                result[key] = self._render_dict(value, context)
            else:
                result[key] = value
        return result
    
    async def _send_workflow_notification(
        self,
        workflow: Workflow,
        execution: WorkflowExecution,
        event: str
    ) -> None:
        """Send workflow notification."""
        recipients = workflow.notification_recipients.get("users", [])
        
        for recipient_id in recipients:
            notification = Notification(
                recipient_id=recipient_id,
                title=f"Workflow {event}: {workflow.name}",
                message=f"Workflow '{workflow.name}' has {event} for {execution.record_type}",
                notification_type=NotificationType.INFO,
                source_type="workflow",
                source_id=workflow.id,
                tenant_id=self.tenant_id
            )
            self.db.add(notification)
        
        await self.db.flush()
    
    async def _notify_approvers(
        self,
        step: WorkflowStep,
        context: WorkflowContext,
        approver_ids: List[str]
    ) -> None:
        """Notify approvers of pending approval."""
        for approver_id in approver_ids:
            notification = Notification(
                recipient_id=approver_id,
                title=f"Approval Required: {step.name}",
                message=f"Your approval is required for {context.record_type}",
                notification_type=NotificationType.APPROVAL,
                priority=NotificationPriority.HIGH,
                source_type="workflow_step",
                source_id=step.id,
                action_url=f"/approvals/{context.execution_id}",
                tenant_id=self.tenant_id
            )
            self.db.add(notification)
        
        await self.db.flush()
    
    # ========================================
    # Execution History
    # ========================================
    
    async def get_execution_history(
        self,
        workflow_id: Optional[UUID] = None,
        status: Optional[WorkflowExecutionStatus] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get workflow execution history."""
        query = select(WorkflowExecution).where(
            WorkflowExecution.tenant_id == self.tenant_id
        )
        
        if workflow_id:
            query = query.where(WorkflowExecution.workflow_id == workflow_id)
        if status:
            query = query.where(WorkflowExecution.status == status)
        
        query = query.order_by(desc(WorkflowExecution.created_at)).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        executions = result.scalars().all()
        
        history = []
        for execution in executions:
            workflow = await self._get_tenant_workflow(execution.workflow_id)
            history.append({
                "id": str(execution.id),
                "workflow_id": str(execution.workflow_id),
                "workflow_name": workflow.name if workflow else "Unknown",
                "record_type": execution.record_type,
                "record_id": str(execution.record_id),
                "status": execution.status.value,
                "started_at": execution.started_at,
                "completed_at": execution.completed_at,
                "error_message": execution.error_message,
                "trigger_type": execution.trigger_type.value
            })
        
        return history
