"""
Nexus ERP - Workflow API Endpoints
===================================

Comprehensive API endpoints for workflow automation including:
- Workflow CRUD operations
- Workflow execution
- Approval management
- Execution history
"""

from datetime import datetime, date
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from decimal import Decimal

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.workflow import (
    Workflow, WorkflowStep, WorkflowStatus,
    WorkflowTriggerType, WorkflowStepType,
    WorkflowExecution, WorkflowExecutionStatus,
    WorkflowApproval, ApprovalDecision
)
from app.services.workflow_service import WorkflowService, TriggerEvent

router = APIRouter(prefix="/workflows", tags=["Workflows"])


# ========================================
# Request/Response Models
# ========================================

class WorkflowStepCreate(BaseModel):
    """Workflow step creation model."""
    code: str
    name: str
    description: Optional[str] = None
    sequence: int = 10
    step_type: str = "action"
    action_type: Optional[str] = None
    action_config: Dict[str, Any] = {}
    conditions: Dict[str, Any] = {}
    approvers: Dict[str, Any] = {}
    timeout_hours: Optional[int] = None
    timeout_action: Optional[str] = None


class WorkflowCreate(BaseModel):
    """Workflow creation model."""
    code: str
    name: str
    model_name: str
    description: Optional[str] = None
    trigger_type: str = "manual"
    trigger_config: Dict[str, Any] = {}
    steps: List[WorkflowStepCreate] = []
    config: Dict[str, Any] = {}
    is_parallel: bool = False
    auto_start: bool = False
    notify_on_start: bool = True
    notify_on_complete: bool = True
    notify_on_error: bool = True


class WorkflowUpdate(BaseModel):
    """Workflow update model."""
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_config: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
    is_parallel: Optional[bool] = None
    auto_start: Optional[bool] = None
    notify_on_start: Optional[bool] = None
    notify_on_complete: Optional[bool] = None
    notify_on_error: Optional[bool] = None
    timeout_hours: Optional[int] = None


class WorkflowExecute(BaseModel):
    """Workflow execution request."""
    record_id: UUID
    record_data: Dict[str, Any] = {}
    manual: bool = True


class ApprovalRequest(BaseModel):
    """Approval request model."""
    comments: Optional[str] = None


# ========================================
# Workflow CRUD
# ========================================

@router.post(
    "",
    summary="Create Workflow",
    description="Create a new workflow definition"
)
async def create_workflow(
    request: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new workflow.
    
    Define workflow with triggers, steps, and configuration.
    """
    service = WorkflowService(db, current_user.tenant_id)
    
    # Convert trigger type
    trigger_type = WorkflowTriggerType(request.trigger_type)
    
    # Convert steps
    steps_data = [step.dict() for step in request.steps]
    
    workflow = await service.create_workflow(
        code=request.code,
        name=request.name,
        model_name=request.model_name,
        description=request.description,
        trigger_type=trigger_type,
        trigger_config=request.trigger_config,
        steps=steps_data,
        config=request.config,
        created_by_id=current_user.id
    )
    
    return {
        "id": str(workflow.id),
        "code": workflow.code,
        "name": workflow.name,
        "model_name": workflow.model_name,
        "status": workflow.status.value,
        "trigger_type": workflow.trigger_type.value,
        "step_count": len(workflow.steps),
        "created_at": workflow.created_at
    }


@router.get(
    "",
    summary="List Workflows",
    description="Get list of workflows with optional filters"
)
async def list_workflows(
    status: Optional[str] = None,
    model_name: Optional[str] = None,
    trigger_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of workflows."""
    service = WorkflowService(db, current_user.tenant_id)
    
    status_enum = WorkflowStatus(status) if status else None
    trigger_enum = WorkflowTriggerType(trigger_type) if trigger_type else None
    
    workflows = await service.get_workflows(
        status=status_enum,
        model_name=model_name,
        trigger_type=trigger_enum,
        skip=skip,
        limit=limit
    )
    
    return {
        "workflows": [
            {
                "id": str(w.id),
                "code": w.code,
                "name": w.name,
                "model_name": w.model_name,
                "status": w.status.value,
                "trigger_type": w.trigger_type.value,
                "total_executions": w.total_executions,
                "successful_executions": w.successful_executions,
                "failed_executions": w.failed_executions,
                "last_execution_at": w.last_execution_at,
                "created_at": w.created_at
            }
            for w in workflows
        ],
        "count": len(workflows)
    }


@router.get(
    "/{workflow_id}",
    summary="Get Workflow",
    description="Get workflow details with steps"
)
async def get_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get workflow by ID with steps."""
    service = WorkflowService(db, current_user.tenant_id)
    
    workflow = await service.get_workflow(workflow_id, include_steps=True)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return {
        "id": str(workflow.id),
        "code": workflow.code,
        "name": workflow.name,
        "description": workflow.description,
        "model_name": workflow.model_name,
        "status": workflow.status.value,
        "version": workflow.version,
        "trigger_type": workflow.trigger_type.value,
        "trigger_config": workflow.trigger_config,
        "is_parallel": workflow.is_parallel,
        "auto_start": workflow.auto_start,
        "timeout_hours": workflow.timeout_hours,
        "notify_on_start": workflow.notify_on_start,
        "notify_on_complete": workflow.notify_on_complete,
        "notify_on_error": workflow.notify_on_error,
        "notification_recipients": workflow.notification_recipients,
        "config": workflow.config,
        "statistics": {
            "total_executions": workflow.total_executions,
            "successful_executions": workflow.successful_executions,
            "failed_executions": workflow.failed_executions,
            "last_execution_at": workflow.last_execution_at
        },
        "steps": [
            {
                "id": str(s.id),
                "code": s.code,
                "name": s.name,
                "description": s.description,
                "sequence": s.sequence,
                "step_type": s.step_type.value,
                "action_type": s.action_type,
                "action_config": s.action_config,
                "conditions": s.conditions,
                "approvers": s.approvers,
                "timeout_hours": s.timeout_hours,
                "timeout_action": s.timeout_action
            }
            for s in workflow.steps
        ],
        "created_at": workflow.created_at,
        "updated_at": workflow.updated_at
    }


@router.put(
    "/{workflow_id}",
    summary="Update Workflow",
    description="Update workflow definition"
)
async def update_workflow(
    workflow_id: UUID,
    request: WorkflowUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update workflow."""
    service = WorkflowService(db, current_user.tenant_id)
    
    update_data = request.dict(exclude_unset=True)
    if "trigger_type" in update_data:
        update_data["trigger_type"] = WorkflowTriggerType(update_data["trigger_type"])
    
    workflow = await service.update_workflow(workflow_id, **update_data)
    
    return {
        "id": str(workflow.id),
        "code": workflow.code,
        "name": workflow.name,
        "status": workflow.status.value,
        "updated_at": workflow.updated_at
    }


@router.delete(
    "/{workflow_id}",
    summary="Delete Workflow",
    description="Delete a workflow"
)
async def delete_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a workflow."""
    workflow = await db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if workflow.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    workflow.is_deleted = True
    await db.flush()
    
    return {"message": "Workflow deleted"}


# ========================================
# Workflow Activation
# ========================================

@router.post(
    "/{workflow_id}/activate",
    summary="Activate Workflow",
    description="Activate a workflow for automatic triggering"
)
async def activate_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Activate a workflow."""
    service = WorkflowService(db, current_user.tenant_id)
    
    workflow = await service.activate_workflow(workflow_id)
    
    return {
        "id": str(workflow.id),
        "status": workflow.status.value,
        "message": "Workflow activated successfully"
    }


@router.post(
    "/{workflow_id}/deactivate",
    summary="Deactivate Workflow",
    description="Deactivate a workflow"
)
async def deactivate_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deactivate a workflow."""
    service = WorkflowService(db, current_user.tenant_id)
    
    workflow = await service.deactivate_workflow(workflow_id)
    
    return {
        "id": str(workflow.id),
        "status": workflow.status.value,
        "message": "Workflow deactivated successfully"
    }


# ========================================
# Workflow Execution
# ========================================

@router.post(
    "/{workflow_id}/execute",
    summary="Execute Workflow",
    description="Manually execute a workflow"
)
async def execute_workflow(
    workflow_id: UUID,
    request: WorkflowExecute,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Execute a workflow manually.
    
    Starts the workflow for the specified record.
    """
    service = WorkflowService(db, current_user.tenant_id)
    
    # Get workflow
    workflow = await service.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if workflow.status != WorkflowStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail="Workflow must be active to execute"
        )
    
    # Trigger workflow
    executions = await service.trigger_workflow(
        event=TriggerEvent(workflow.model_name + "_manual"),
        record_type=workflow.model_name,
        record_id=request.record_id,
        record_data=request.record_data,
        user_id=current_user.id,
        manual=True
    )
    
    return {
        "workflow_id": str(workflow_id),
        "executions": [
            {
                "id": str(e.id),
                "status": e.status.value,
                "started_at": e.started_at
            }
            for e in executions
        ]
    }


@router.get(
    "/{workflow_id}/history",
    summary="Workflow Execution History",
    description="Get execution history for a workflow"
)
async def get_workflow_history(
    workflow_id: UUID,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get execution history for a workflow."""
    service = WorkflowService(db, current_user.tenant_id)
    
    status_enum = WorkflowExecutionStatus(status) if status else None
    
    history = await service.get_execution_history(
        workflow_id=workflow_id,
        status=status_enum,
        skip=skip,
        limit=limit
    )
    
    return {
        "workflow_id": str(workflow_id),
        "executions": history,
        "count": len(history)
    }


@router.get(
    "/executions/{execution_id}",
    summary="Get Execution Details",
    description="Get details of a workflow execution"
)
async def get_execution_details(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get details of a workflow execution."""
    execution = await db.get(WorkflowExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    if execution.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get step executions
    from sqlalchemy import select
    steps_result = await db.execute(
        select(WorkflowStepExecution).where(
            WorkflowStepExecution.execution_id == execution_id
        ).order_by(WorkflowStepExecution.started_at)
    )
    step_executions = steps_result.scalars().all()
    
    # Get approvals
    approvals_result = await db.execute(
        select(WorkflowApproval).where(
            WorkflowApproval.execution_id == execution_id
        )
    )
    approvals = approvals_result.scalars().all()
    
    return {
        "id": str(execution.id),
        "workflow_id": str(execution.workflow_id),
        "record_type": execution.record_type,
        "record_id": str(execution.record_id),
        "status": execution.status.value,
        "trigger_type": execution.trigger_type.value,
        "started_at": execution.started_at,
        "completed_at": execution.completed_at,
        "error_message": execution.error_message,
        "error_details": execution.error_details,
        "input_data": execution.input_data,
        "output_data": execution.output_data,
        "context": execution.context,
        "step_executions": [
            {
                "id": str(se.id),
                "step_id": str(se.step_id),
                "status": se.status.value,
                "started_at": se.started_at,
                "completed_at": se.completed_at,
                "error_message": se.error_message,
                "output_data": se.output_data
            }
            for se in step_executions
        ],
        "approvals": [
            {
                "id": str(a.id),
                "approver_id": str(a.approver_id),
                "decision": a.decision.value if a.decision else None,
                "comments": a.comments,
                "decided_at": a.decided_at
            }
            for a in approvals
        ]
    }


# ========================================
# Approval Management
# ========================================

@router.get(
    "/approvals/pending",
    summary="Get Pending Approvals",
    description="Get pending approvals for current user"
)
async def get_pending_approvals(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get pending approvals for the current user."""
    service = WorkflowService(db, current_user.tenant_id)
    
    approvals = await service.get_pending_approvals(
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    
    return {
        "approvals": approvals,
        "count": len(approvals)
    }


@router.post(
    "/approvals/{approval_id}/approve",
    summary="Approve",
    description="Approve a workflow step"
)
async def approve_workflow(
    approval_id: UUID,
    request: ApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve a workflow step."""
    service = WorkflowService(db, current_user.tenant_id)
    
    approval = await service.approve(
        approval_id=approval_id,
        user_id=current_user.id,
        comments=request.comments
    )
    
    return {
        "id": str(approval.id),
        "decision": approval.decision.value,
        "comments": approval.comments,
        "decided_at": approval.decided_at,
        "message": "Approved successfully"
    }


@router.post(
    "/approvals/{approval_id}/reject",
    summary="Reject",
    description="Reject a workflow step"
)
async def reject_workflow(
    approval_id: UUID,
    request: ApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject a workflow step."""
    service = WorkflowService(db, current_user.tenant_id)
    
    approval = await service.reject(
        approval_id=approval_id,
        user_id=current_user.id,
        comments=request.comments
    )
    
    return {
        "id": str(approval.id),
        "decision": approval.decision.value,
        "comments": approval.comments,
        "decided_at": approval.decided_at,
        "message": "Rejected"
    }


# ========================================
# Pre-built Workflows
# ========================================

@router.post(
    "/templates/invoice-approval",
    summary="Create Invoice Approval Workflow",
    description="Create pre-built invoice approval workflow"
)
async def create_invoice_approval_template(
    approval_threshold: float = 10000,
    approvers: List[str] = [],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create invoice approval workflow from template."""
    from decimal import Decimal
    
    service = WorkflowService(db, current_user.tenant_id)
    
    workflow = await service.create_invoice_approval_workflow(
        approval_threshold=Decimal(str(approval_threshold)),
        approvers=approvers,
        created_by_id=current_user.id
    )
    
    return {
        "id": str(workflow.id),
        "code": workflow.code,
        "name": workflow.name,
        "status": workflow.status.value,
        "message": "Invoice approval workflow created"
    }


@router.post(
    "/templates/low-stock-alert",
    summary="Create Low Stock Alert Workflow",
    description="Create pre-built low stock alert workflow"
)
async def create_low_stock_alert_template(
    threshold_quantity: float = 10,
    recipients: List[str] = [],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create low stock alert workflow from template."""
    from decimal import Decimal
    
    service = WorkflowService(db, current_user.tenant_id)
    
    workflow = await service.create_low_stock_alert_workflow(
        threshold_quantity=Decimal(str(threshold_quantity)),
        recipients=recipients,
        created_by_id=current_user.id
    )
    
    return {
        "id": str(workflow.id),
        "code": workflow.code,
        "name": workflow.name,
        "status": workflow.status.value,
        "message": "Low stock alert workflow created"
    }


@router.post(
    "/templates/payment-reminder",
    summary="Create Payment Reminder Workflow",
    description="Create pre-built payment reminder workflow"
)
async def create_payment_reminder_template(
    days_before_due: int = 7,
    recipients: List[str] = [],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create payment reminder workflow from template."""
    service = WorkflowService(db, current_user.tenant_id)
    
    workflow = await service.create_payment_reminder_workflow(
        days_before_due=days_before_due,
        recipients=recipients,
        created_by_id=current_user.id
    )
    
    return {
        "id": str(workflow.id),
        "code": workflow.code,
        "name": workflow.name,
        "status": workflow.status.value,
        "message": "Payment reminder workflow created"
    }


# ========================================
# Execution History
# ========================================

@router.get(
    "/history/all",
    summary="All Execution History",
    description="Get all workflow execution history"
)
async def get_all_execution_history(
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all execution history."""
    service = WorkflowService(db, current_user.tenant_id)
    
    status_enum = WorkflowExecutionStatus(status) if status else None
    
    history = await service.get_execution_history(
        status=status_enum,
        skip=skip,
        limit=limit
    )
    
    return {
        "executions": history,
        "count": len(history)
    }
