"""
Nexus ERP - Workflow Automation Models
=======================================

This module implements workflow automation for business processes,
including approval workflows, trigger-based automation, and conditional logic.

Features:
- Visual workflow builder
- Multi-step approval workflows
- Trigger-based automation (events, scheduled)
- Conditional branching logic
- Email notifications
- Audit trail of all workflow executions
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Numeric,
    UniqueConstraint,
    Index,
    Enum as SQLEnum,
    CheckConstraint,
    Integer,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional, List, Dict, Any
import enum
import uuid

from app.models.base import BaseModel, TenantMixin


class WorkflowStatus(str, enum.Enum):
    """Workflow definition status."""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class WorkflowTriggerType(str, enum.Enum):
    """Workflow trigger types."""
    MANUAL = "manual"              # Manually triggered
    ON_CREATE = "on_create"        # Triggered when record is created
    ON_UPDATE = "on_update"        # Triggered when record is updated
    ON_DELETE = "on_delete"        # Triggered when record is deleted
    ON_STATE_CHANGE = "on_state_change"  # Triggered on status change
    SCHEDULED = "scheduled"        # Scheduled/cron-based
    ON_APPROVAL = "on_approval"    # Triggered on approval action
    ON_FIELD_CHANGE = "on_field_change"  # Triggered when specific field changes


class WorkflowStepType(str, enum.Enum):
    """Workflow step types."""
    APPROVAL = "approval"          # Requires approval
    NOTIFICATION = "notification"  # Send notification
    ACTION = "action"              # Execute action
    CONDITION = "condition"        # Conditional branch
    PARALLEL = "parallel"          # Parallel execution
    WAIT = "wait"                  # Wait for time/event
    WEBHOOK = "webhook"            # Call external webhook
    SCRIPT = "script"              # Execute custom script


class WorkflowExecutionStatus(str, enum.Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"              # Waiting for input/approval


class WorkflowStepExecutionStatus(str, enum.Enum):
    """Workflow step execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"            # Waiting for approval/input
    CANCELLED = "cancelled"


class ApprovalDecision(str, enum.Enum):
    """Approval decision options."""
    APPROVED = "approved"
    REJECTED = "rejected"
    RETURNED = "returned"          # Return for revision
    DELEGATED = "delegated"        # Delegate to another user


class Workflow(BaseModel, TenantMixin):
    """
    Workflow Definition Model
    
    Defines a workflow with its triggers, steps, and configuration.
    """
    
    __tablename__ = "workflows"
    __table_args__ = (
        Index("ix_workflows_tenant", "tenant_id"),
        Index("ix_workflows_status", "status"),
        Index("ix_workflows_model", "model_name"),
        UniqueConstraint("code", "tenant_id", name="uq_workflow_code"),
    )
    
    # Basic Information
    code: str = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Unique workflow code"
    )
    
    name: str = Column(
        String(200),
        nullable=False,
        doc="Workflow name"
    )
    
    description: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Workflow description"
    )
    
    # Target Model
    model_name: str = Column(
        String(100),
        nullable=False,
        doc="Target model (e.g., 'sale_order', 'purchase_order', 'invoice')"
    )
    
    # Status
    status: WorkflowStatus = Column(
        SQLEnum(WorkflowStatus),
        default=WorkflowStatus.DRAFT,
        nullable=False,
        doc="Workflow status"
    )
    
    version: int = Column(
        Integer,
        default=1,
        nullable=False,
        doc="Workflow version number"
    )
    
    # Trigger Configuration
    trigger_type: WorkflowTriggerType = Column(
        SQLEnum(WorkflowTriggerType),
        default=WorkflowTriggerType.MANUAL,
        nullable=False,
        doc="How workflow is triggered"
    )
    
    trigger_config: Dict[str, Any] = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Trigger configuration (conditions, schedule, etc.)"
    )
    
    # Workflow Configuration
    is_parallel: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether steps can execute in parallel"
    )
    
    auto_start: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Auto-start when trigger conditions are met"
    )
    
    allow_restart: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Allow restarting completed/failed workflows"
    )
    
    max_executions: Optional[int] = Column(
        Integer,
        nullable=True,
        doc="Maximum concurrent executions (null = unlimited)"
    )
    
    timeout_hours: Optional[int] = Column(
        Integer,
        nullable=True,
        doc="Workflow timeout in hours"
    )
    
    # Notification Settings
    notify_on_start: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Send notification when workflow starts"
    )
    
    notify_on_complete: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Send notification when workflow completes"
    )
    
    notify_on_error: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Send notification on workflow error"
    )
    
    notification_recipients: Dict[str, Any] = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Notification recipient configuration"
    )
    
    # Additional Configuration
    config: Dict[str, Any] = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Additional workflow configuration"
    )
    
    # Statistics
    total_executions: int = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total number of executions"
    )
    
    successful_executions: int = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of successful executions"
    )
    
    failed_executions: int = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of failed executions"
    )
    
    last_execution_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Last execution timestamp"
    )
    
    # Relationships
    steps: Mapped[List["WorkflowStep"]] = relationship(
        "WorkflowStep",
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="WorkflowStep.sequence",
        lazy="selectin"
    )
    
    executions: Mapped[List["WorkflowExecution"]] = relationship(
        "WorkflowExecution",
        back_populates="workflow",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )


class WorkflowStep(BaseModel):
    """
    Workflow Step Model
    
    Represents a single step in a workflow.
    """
    
    __tablename__ = "workflow_steps"
    __table_args__ = (
        Index("ix_workflow_steps_workflow", "workflow_id"),
        Index("ix_workflow_steps_sequence", "workflow_id", "sequence"),
        CheckConstraint(
            "sequence >= 0",
            name="ck_workflow_step_sequence"
        ),
    )
    
    workflow_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        doc="Parent workflow"
    )
    
    # Step Identification
    code: str = Column(
        String(50),
        nullable=False,
        doc="Step code (unique within workflow)"
    )
    
    name: str = Column(
        String(200),
        nullable=False,
        doc="Step name"
    )
    
    description: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Step description"
    )
    
    sequence: int = Column(
        Integer,
        nullable=False,
        doc="Step sequence/order"
    )
    
    # Step Type
    step_type: WorkflowStepType = Column(
        SQLEnum(WorkflowStepType),
        default=WorkflowStepType.ACTION,
        nullable=False,
        doc="Type of step"
    )
    
    # Approval Configuration (for approval steps)
    approval_type: Optional[str] = Column(
        String(50),
        nullable=True,
        doc="Approval type: 'any', 'all', 'percentage', 'sequential'"
    )
    
    approval_percentage: Optional[float] = Column(
        Numeric(5, 2),
        nullable=True,
        doc="Percentage of approvers required (if type is 'percentage')"
    )
    
    approvers: Dict[str, Any] = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Approver configuration (users, roles, groups, dynamic)"
    )
    
    allow_delegate: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Allow delegation of approval"
    )
    
    allow_reject: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Allow rejection"
    )
    
    allow_return: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Allow returning for revision"
    )
    
    # Action Configuration (for action steps)
    action_type: Optional[str] = Column(
        String(50),
        nullable=True,
        doc="Action type: 'update_field', 'send_email', 'create_record', etc."
    )
    
    action_config: Dict[str, Any] = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Action configuration"
    )
    
    # Condition Configuration (for condition steps)
    condition_type: Optional[str] = Column(
        String(50),
        nullable=True,
        doc="Condition type: 'all', 'any', 'expression'"
    )
    
    conditions: Dict[str, Any] = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Condition expressions"
    )
    
    # Next Steps
    next_step_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_steps.id", ondelete="SET NULL"),
        nullable=True,
        doc="Next step on success"
    )
    
    else_step_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_steps.id", ondelete="SET NULL"),
        nullable=True,
        doc="Next step on failure/else (for conditions)"
    )
    
    # Notification
    notify_approvers: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Send notification to approvers"
    )
    
    notification_template: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Email template for notifications"
    )
    
    # Timeout
    timeout_hours: Optional[int] = Column(
        Integer,
        nullable=True,
        doc="Step timeout in hours"
    )
    
    timeout_action: Optional[str] = Column(
        String(50),
        nullable=True,
        doc="Action on timeout: 'approve', 'reject', 'escalate'"
    )
    
    timeout_step_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_steps.id", ondelete="SET NULL"),
        nullable=True,
        doc="Step to execute on timeout"
    )
    
    # Relationships
    workflow: Mapped["Workflow"] = relationship(
        "Workflow",
        back_populates="steps"
    )
    
    executions: Mapped[List["WorkflowStepExecution"]] = relationship(
        "WorkflowStepExecution",
        back_populates="step",
        cascade="all, delete-orphan"
    )


class WorkflowExecution(BaseModel, TenantMixin):
    """
    Workflow Execution Model
    
    Tracks an instance of a workflow execution.
    """
    
    __tablename__ = "workflow_executions"
    __table_args__ = (
        Index("ix_workflow_executions_workflow", "workflow_id"),
        Index("ix_workflow_executions_status", "status"),
        Index("ix_workflow_executions_record", "record_type", "record_id"),
        Index("ix_workflow_executions_tenant", "tenant_id"),
    )
    
    workflow_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        doc="Workflow being executed"
    )
    
    # Target Record
    record_type: str = Column(
        String(100),
        nullable=False,
        doc="Type of record being processed"
    )
    
    record_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        nullable=False,
        doc="ID of record being processed"
    )
    
    # Execution State
    status: WorkflowExecutionStatus = Column(
        SQLEnum(WorkflowExecutionStatus),
        default=WorkflowExecutionStatus.PENDING,
        nullable=False,
        doc="Execution status"
    )
    
    current_step_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_steps.id", ondelete="SET NULL"),
        nullable=True,
        doc="Current step being executed"
    )
    
    # Context & Variables
    context: Dict[str, Any] = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Execution context and variables"
    )
    
    input_data: Dict[str, Any] = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Input data for workflow"
    )
    
    output_data: Dict[str, Any] = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Output data from workflow"
    )
    
    # Timing
    started_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When execution started"
    )
    
    completed_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When execution completed"
    )
    
    # Error Information
    error_message: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Error message if failed"
    )
    
    error_details: Dict[str, Any] = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Detailed error information"
    )
    
    # Trigger Information
    triggered_by_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User who triggered the workflow"
    )
    
    trigger_type: WorkflowTriggerType = Column(
        SQLEnum(WorkflowTriggerType),
        default=WorkflowTriggerType.MANUAL,
        nullable=False,
        doc="How this execution was triggered"
    )
    
    # Relationships
    workflow: Mapped["Workflow"] = relationship(
        "Workflow",
        back_populates="executions"
    )
    
    current_step: Mapped[Optional["WorkflowStep"]] = relationship(
        "WorkflowStep",
        foreign_keys=[current_step_id]
    )
    
    step_executions: Mapped[List["WorkflowStepExecution"]] = relationship(
        "WorkflowStepExecution",
        back_populates="execution",
        cascade="all, delete-orphan",
        order_by="WorkflowStepExecution.started_at"
    )
    
    approvals: Mapped[List["WorkflowApproval"]] = relationship(
        "WorkflowApproval",
        back_populates="execution",
        cascade="all, delete-orphan"
    )


class WorkflowStepExecution(BaseModel):
    """
    Workflow Step Execution Model
    
    Tracks execution of a single step within a workflow.
    """
    
    __tablename__ = "workflow_step_executions"
    __table_args__ = (
        Index("ix_workflow_step_executions_execution", "execution_id"),
        Index("ix_workflow_step_executions_step", "step_id"),
        Index("ix_workflow_step_executions_status", "status"),
    )
    
    execution_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_executions.id", ondelete="CASCADE"),
        nullable=False
    )
    
    step_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_steps.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Execution State
    status: WorkflowStepExecutionStatus = Column(
        SQLEnum(WorkflowStepExecutionStatus),
        default=WorkflowStepExecutionStatus.PENDING,
        nullable=False,
        doc="Step execution status"
    )
    
    # Timing
    started_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When step started"
    )
    
    completed_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When step completed"
    )
    
    # Retry Information
    retry_count: int = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of retry attempts"
    )
    
    # Data
    input_data: Dict[str, Any] = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Input data for step"
    )
    
    output_data: Dict[str, Any] = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Output data from step"
    )
    
    # Error Information
    error_message: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Error message if failed"
    )
    
    error_details: Dict[str, Any] = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Detailed error information"
    )
    
    # Relationships
    execution: Mapped["WorkflowExecution"] = relationship(
        "WorkflowExecution",
        back_populates="step_executions"
    )
    
    step: Mapped["WorkflowStep"] = relationship(
        "WorkflowStep",
        back_populates="executions"
    )


class WorkflowApproval(BaseModel):
    """
    Workflow Approval Model
    
    Records approval decisions made during workflow execution.
    """
    
    __tablename__ = "workflow_approvals"
    __table_args__ = (
        Index("ix_workflow_approvals_execution", "execution_id"),
        Index("ix_workflow_approvals_step", "step_id"),
        Index("ix_workflow_approvals_approver", "approver_id"),
        UniqueConstraint("execution_id", "step_id", "approver_id", name="uq_approval"),
    )
    
    execution_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_executions.id", ondelete="CASCADE"),
        nullable=False
    )
    
    step_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_steps.id", ondelete="CASCADE"),
        nullable=True
    )
    
    # Approver
    approver_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="User who made the decision"
    )
    
    # Decision
    decision: Optional[ApprovalDecision] = Column(
        SQLEnum(ApprovalDecision),
        nullable=True,
        doc="Approval decision; null while pending"
    )
    
    # Comments
    comments: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Approval comments"
    )
    
    # Timestamps
    decided_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When decision was made; null while pending"
    )
    
    # Delegation
    delegated_from_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Original approver if delegated"
    )
    
    # Additional Data
    metadata_json: Dict[str, Any] = Column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
        doc="Additional metadata"
    )
    
    # Relationships
    execution: Mapped["WorkflowExecution"] = relationship(
        "WorkflowExecution",
        back_populates="approvals"
    )
    
    step: Mapped["WorkflowStep"] = relationship(
        "WorkflowStep"
    )


class WorkflowTemplate(BaseModel, TenantMixin):
    """
    Workflow Template Model
    
    Pre-defined workflow templates that can be customized and deployed.
    """
    
    __tablename__ = "workflow_templates"
    __table_args__ = (
        Index("ix_workflow_templates_tenant", "tenant_id"),
        Index("ix_workflow_templates_category", "category"),
    )
    
    # Template Information
    code: str = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Template code"
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
        doc="Template category (approval, automation, notification)"
    )
    
    # Target Model
    model_name: str = Column(
        String(100),
        nullable=False,
        doc="Target model for this template"
    )
    
    # Template Definition
    workflow_definition: Dict[str, Any] = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Complete workflow definition (steps, config)"
    )
    
    # Metadata
    is_system: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="System template (cannot be deleted)"
    )
    
    is_active: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether template is active"
    )
    
    usage_count: int = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of times used to create workflows"
    )
