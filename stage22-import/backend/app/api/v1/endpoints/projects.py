"""
Nexus ERP - Projects API Endpoints
==================================

REST API endpoints for Project Management.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel, Field
from decimal import Decimal

from app.core.database import db_manager
from app.core.security import get_current_user

router = APIRouter(prefix="/projects", tags=["Projects"])


# ========================================
# Pydantic Schemas
# ========================================

class ProjectBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    customer_id: Optional[UUID] = None
    manager_id: Optional[UUID] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[float] = None
    color: str = "#3B82F6"


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    customer_id: Optional[UUID] = None
    manager_id: Optional[UUID] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[float] = None
    status: Optional[str] = None
    progress: Optional[float] = None
    color: Optional[str] = None


class ProjectResponse(ProjectBase):
    id: UUID
    status: str = "planning"
    progress: float = 0
    spent: float = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskBase(BaseModel):
    name: str
    description: Optional[str] = None
    project_id: UUID
    assignee_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    planned_hours: Optional[float] = 0
    priority: str = "medium"
    due_date: Optional[date] = None
    tags: List[str] = []


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[UUID] = None
    planned_hours: Optional[float] = None
    spent_hours: Optional[float] = None
    progress: Optional[float] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[date] = None
    tags: Optional[List[str]] = None


class TaskResponse(TaskBase):
    id: UUID
    status: str = "todo"
    progress: float = 0
    spent_hours: float = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TimesheetBase(BaseModel):
    employee_id: UUID
    project_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    date: date
    hours: float
    description: Optional[str] = None
    billable: bool = True


class TimesheetCreate(TimesheetBase):
    pass


class TimesheetUpdate(BaseModel):
    hours: Optional[float] = None
    description: Optional[str] = None
    billable: Optional[bool] = None
    approved: Optional[bool] = None


class TimesheetResponse(TimesheetBase):
    id: UUID
    approved: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


# ========================================
# Project Endpoints
# ========================================

@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    customer_id: Optional[UUID] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """List projects with filtering and pagination."""
    query = select(Project).where(Project.is_deleted == False)
    
    if search:
        query = query.where(
            or_(
                Project.name.ilike(f"%{search}%"),
                Project.code.ilike(f"%{search}%")
            )
        )
    
    if status:
        query = query.where(Project.status == status)
    
    if customer_id:
        query = query.where(Project.customer_id == customer_id)
    
    query = query.order_by(Project.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    projects = result.scalars().all()
    
    return [ProjectResponse(
        id=p.id,
        name=p.name,
        code=p.code,
        description=p.description,
        customer_id=p.customer_id,
        manager_id=p.manager_id,
        start_date=p.start_date,
        end_date=p.end_date,
        budget=float(p.budget) if p.budget else 0,
        color=p.color,
        status=p.status,
        progress=float(p.progress) if p.progress else 0,
        spent=0,  # Would calculate from timesheets
        created_at=p.created_at,
        updated_at=p.updated_at
    ) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Get project by ID."""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.is_deleted == False
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        code=project.code,
        description=project.description,
        customer_id=project.customer_id,
        manager_id=project.manager_id,
        start_date=project.start_date,
        end_date=project.end_date,
        budget=float(project.budget) if project.budget else 0,
        color=project.color,
        status=project.status,
        progress=float(project.progress) if project.progress else 0,
        spent=0,
        created_at=project.created_at,
        updated_at=project.updated_at
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Create a new project."""
    # Check if code exists
    existing = await db.execute(
        select(Project).where(Project.code == data.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Project code already exists")
    
    project = Project(
        name=data.name,
        code=data.code,
        description=data.description,
        customer_id=data.customer_id,
        manager_id=data.manager_id,
        start_date=data.start_date,
        end_date=data.end_date,
        budget=Decimal(str(data.budget)) if data.budget else Decimal("0"),
        color=data.color,
        tenant_id=current_user.tenant_id,
        created_by_id=current_user.id,
        status="planning"
    )
    
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        code=project.code,
        description=project.description,
        customer_id=project.customer_id,
        manager_id=project.manager_id,
        start_date=project.start_date,
        end_date=project.end_date,
        budget=float(project.budget) if project.budget else 0,
        color=project.color,
        status=project.status,
        progress=0,
        spent=0,
        created_at=project.created_at,
        updated_at=project.updated_at
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Update project."""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.is_deleted == False
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "budget" and value is not None:
            value = Decimal(str(value))
        setattr(project, field, value)
    
    await db.commit()
    await db.refresh(project)
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        code=project.code,
        description=project.description,
        customer_id=project.customer_id,
        manager_id=project.manager_id,
        start_date=project.start_date,
        end_date=project.end_date,
        budget=float(project.budget) if project.budget else 0,
        color=project.color,
        status=project.status,
        progress=float(project.progress) if project.progress else 0,
        spent=0,
        created_at=project.created_at,
        updated_at=project.updated_at
    )


@router.delete("/{project_id}")
async def delete_project(
    project_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Delete project."""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.is_deleted == False
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.is_deleted = True
    project.deleted_at = datetime.utcnow()
    
    await db.commit()
    
    return {"success": True, "message": "Project deleted"}


# ========================================
# Task Endpoints
# ========================================

@router.get("/{project_id}/tasks", response_model=List[TaskResponse])
async def list_project_tasks(
    project_id: UUID,
    status: Optional[str] = None,
    assignee_id: Optional[UUID] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """List tasks for a project."""
    query = select(ProjectTask).where(ProjectTask.project_id == project_id)
    
    if status:
        query = query.where(ProjectTask.status == status)
    
    if assignee_id:
        query = query.where(ProjectTask.assignee_id == assignee_id)
    
    query = query.order_by(ProjectTask.created_at.desc())
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return [TaskResponse(
        id=t.id,
        name=t.name,
        description=t.description,
        project_id=t.project_id,
        assignee_id=t.assignee_id,
        parent_id=t.parent_id,
        planned_hours=float(t.planned_hours) if t.planned_hours else 0,
        priority=t.priority,
        due_date=t.due_date,
        tags=t.tags or [],
        status=t.status,
        progress=float(t.progress) if t.progress else 0,
        spent_hours=float(t.spent_hours) if t.spent_hours else 0,
        created_at=t.created_at,
        updated_at=t.updated_at
    ) for t in tasks]


@router.get("/tasks/all", response_model=List[TaskResponse])
async def list_all_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    assignee_id: Optional[UUID] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """List all tasks across projects."""
    query = select(ProjectTask)
    
    if status:
        query = query.where(ProjectTask.status == status)
    
    if assignee_id:
        query = query.where(ProjectTask.assignee_id == assignee_id)
    
    query = query.order_by(ProjectTask.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return [TaskResponse(
        id=t.id,
        name=t.name,
        description=t.description,
        project_id=t.project_id,
        assignee_id=t.assignee_id,
        parent_id=t.parent_id,
        planned_hours=float(t.planned_hours) if t.planned_hours else 0,
        priority=t.priority,
        due_date=t.due_date,
        tags=t.tags or [],
        status=t.status,
        progress=float(t.progress) if t.progress else 0,
        spent_hours=float(t.spent_hours) if t.spent_hours else 0,
        created_at=t.created_at,
        updated_at=t.updated_at
    ) for t in tasks]


@router.post("/{project_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    project_id: UUID,
    data: TaskCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Create a new task."""
    task = ProjectTask(
        name=data.name,
        description=data.description,
        project_id=project_id,
        assignee_id=data.assignee_id,
        parent_id=data.parent_id,
        planned_hours=Decimal(str(data.planned_hours)) if data.planned_hours else Decimal("0"),
        priority=data.priority,
        due_date=data.due_date,
        tags=data.tags,
        tenant_id=current_user.tenant_id,
        status="todo"
    )
    
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    return TaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        project_id=task.project_id,
        assignee_id=task.assignee_id,
        parent_id=task.parent_id,
        planned_hours=float(task.planned_hours) if task.planned_hours else 0,
        priority=task.priority,
        due_date=task.due_date,
        tags=task.tags or [],
        status=task.status,
        progress=0,
        spent_hours=0,
        created_at=task.created_at,
        updated_at=task.updated_at
    )


@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    data: TaskUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Update task."""
    result = await db.execute(
        select(ProjectTask).where(ProjectTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field in ["planned_hours", "spent_hours"] and value is not None:
            value = Decimal(str(value))
        setattr(task, field, value)
    
    await db.commit()
    await db.refresh(task)
    
    return TaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        project_id=task.project_id,
        assignee_id=task.assignee_id,
        parent_id=task.parent_id,
        planned_hours=float(task.planned_hours) if task.planned_hours else 0,
        priority=task.priority,
        due_date=task.due_date,
        tags=task.tags or [],
        status=task.status,
        progress=float(task.progress) if task.progress else 0,
        spent_hours=float(task.spent_hours) if task.spent_hours else 0,
        created_at=task.created_at,
        updated_at=task.updated_at
    )


# ========================================
# Timesheet Endpoints
# ========================================

@router.get("/timesheets", response_model=List[TimesheetResponse])
async def list_timesheets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    employee_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """List timesheets."""
    query = select(Timesheet)
    
    if employee_id:
        query = query.where(Timesheet.employee_id == employee_id)
    
    if project_id:
        query = query.where(Timesheet.project_id == project_id)
    
    if date_from:
        query = query.where(Timesheet.date >= date_from)
    
    if date_to:
        query = query.where(Timesheet.date <= date_to)
    
    query = query.order_by(Timesheet.date.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    timesheets = result.scalars().all()
    
    return [TimesheetResponse(
        id=t.id,
        employee_id=t.employee_id,
        project_id=t.project_id,
        task_id=t.task_id,
        date=t.date,
        hours=float(t.hours),
        description=t.description,
        billable=t.billable,
        approved=t.approved,
        created_at=t.created_at
    ) for t in timesheets]


@router.post("/timesheets", response_model=TimesheetResponse, status_code=status.HTTP_201_CREATED)
async def create_timesheet(
    data: TimesheetCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Create a timesheet entry."""
    timesheet = Timesheet(
        employee_id=data.employee_id,
        project_id=data.project_id,
        task_id=data.task_id,
        date=data.date,
        hours=Decimal(str(data.hours)),
        description=data.description,
        billable=data.billable,
        tenant_id=current_user.tenant_id
    )
    
    db.add(timesheet)
    await db.commit()
    await db.refresh(timesheet)
    
    return TimesheetResponse(
        id=timesheet.id,
        employee_id=timesheet.employee_id,
        project_id=timesheet.project_id,
        task_id=timesheet.task_id,
        date=timesheet.date,
        hours=float(timesheet.hours),
        description=timesheet.description,
        billable=timesheet.billable,
        approved=timesheet.approved,
        created_at=timesheet.created_at
    )


@router.put("/timesheets/{timesheet_id}", response_model=TimesheetResponse)
async def update_timesheet(
    timesheet_id: UUID,
    data: TimesheetUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Update timesheet."""
    result = await db.execute(
        select(Timesheet).where(Timesheet.id == timesheet_id)
    )
    timesheet = result.scalar_one_or_none()
    
    if not timesheet:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "hours" and value is not None:
            value = Decimal(str(value))
        setattr(timesheet, field, value)
    
    await db.commit()
    await db.refresh(timesheet)
    
    return TimesheetResponse(
        id=timesheet.id,
        employee_id=timesheet.employee_id,
        project_id=timesheet.project_id,
        task_id=timesheet.task_id,
        date=timesheet.date,
        hours=float(timesheet.hours),
        description=timesheet.description,
        billable=timesheet.billable,
        approved=timesheet.approved,
        created_at=timesheet.created_at
    )


# ========================================
# Import models
# ========================================

from app.models.user import User
# Note: These would be defined in separate model files
# For now, using placeholder models

class Project:
    """Placeholder Project model."""
    pass

class ProjectTask:
    """Placeholder ProjectTask model."""
    pass

class Timesheet:
    """Placeholder Timesheet model."""
    pass
