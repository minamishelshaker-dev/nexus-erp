"""
Nexus ERP - HR API Endpoints
============================

REST API endpoints for Human Resources management.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel, Field

from app.core.database import db_manager
from app.core.security import get_current_user

router = APIRouter(prefix="/hr", tags=["Human Resources"])


# ========================================
# Pydantic Schemas
# ========================================

class EmployeeBase(BaseModel):
    employee_number: str
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    hire_date: Optional[date] = None
    employment_type: str = "full_time"
    salary: Optional[float] = None
    address: Optional[str] = None


class EmployeeCreate(EmployeeBase):
    manager_id: Optional[UUID] = None
    user_id: Optional[UUID] = None


class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    manager_id: Optional[UUID] = None
    hire_date: Optional[date] = None
    employment_type: Optional[str] = None
    salary: Optional[float] = None
    status: Optional[str] = None
    address: Optional[str] = None


class EmployeeResponse(EmployeeBase):
    id: UUID
    full_name: str
    manager_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    status: str = "active"
    salary_currency: str = "USD"
    termination_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AttendanceBase(BaseModel):
    employee_id: UUID
    date: date
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    status: str = "present"
    notes: Optional[str] = None


class AttendanceCreate(AttendanceBase):
    pass


class AttendanceUpdate(BaseModel):
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class AttendanceResponse(AttendanceBase):
    id: UUID
    hours_worked: float = 0
    overtime_hours: float = 0
    created_at: datetime

    class Config:
        from_attributes = True


class PayrollRunBase(BaseModel):
    period_start: date
    period_end: date
    description: Optional[str] = None


class PayrollRunCreate(PayrollRunBase):
    pass


class PayrollRunResponse(PayrollRunBase):
    id: UUID
    status: str = "draft"
    total_gross: float = 0
    total_deductions: float = 0
    total_net: float = 0
    employee_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class PayslipResponse(BaseModel):
    id: UUID
    employee_id: UUID
    employee_name: str
    payroll_run_id: UUID
    period_start: date
    period_end: date
    base_salary: float
    allowances: float = 0
    overtime: float = 0
    deductions: float = 0
    tax: float = 0
    net_salary: float
    status: str = "draft"

    class Config:
        from_attributes = True


# ========================================
# Employee Endpoints
# ========================================

@router.get("/employees", response_model=List[EmployeeResponse])
async def list_employees(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    department: Optional[str] = None,
    status: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """List employees with filtering and pagination."""
    query = select(Employee).where(Employee.is_deleted == False)
    
    if search:
        query = query.where(
            or_(
                Employee.first_name.ilike(f"%{search}%"),
                Employee.last_name.ilike(f"%{search}%"),
                Employee.employee_number.ilike(f"%{search}%"),
                Employee.email.ilike(f"%{search}%")
            )
        )
    
    if department:
        query = query.where(Employee.department == department)
    
    if status:
        query = query.where(Employee.status == status)
    
    query = query.order_by(Employee.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    employees = result.scalars().all()
    
    return [
        EmployeeResponse(
            id=e.id,
            employee_number=e.employee_number,
            first_name=e.first_name,
            last_name=e.last_name,
            full_name=f"{e.first_name} {e.last_name}",
            email=e.email,
            phone=e.phone,
            department=e.department,
            position=e.position,
            hire_date=e.hire_date,
            employment_type=e.employment_type,
            salary=float(e.salary) if e.salary else None,
            address=e.address,
            manager_id=e.manager_id,
            user_id=e.user_id,
            status=e.status,
            termination_date=e.termination_date,
            created_at=e.created_at,
            updated_at=e.updated_at
        )
        for e in employees
    ]


@router.get("/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Get employee by ID."""
    result = await db.execute(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.is_deleted == False
        )
    )
    employee = result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return EmployeeResponse(
        id=employee.id,
        employee_number=employee.employee_number,
        first_name=employee.first_name,
        last_name=employee.last_name,
        full_name=f"{employee.first_name} {employee.last_name}",
        email=employee.email,
        phone=employee.phone,
        department=employee.department,
        position=employee.position,
        hire_date=employee.hire_date,
        employment_type=employee.employment_type,
        salary=float(employee.salary) if employee.salary else None,
        address=employee.address,
        manager_id=employee.manager_id,
        user_id=employee.user_id,
        status=employee.status,
        termination_date=employee.termination_date,
        created_at=employee.created_at,
        updated_at=employee.updated_at
    )


@router.post("/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    data: EmployeeCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Create a new employee."""
    # Check if employee number exists
    existing = await db.execute(
        select(Employee).where(Employee.employee_number == data.employee_number)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Employee number already exists")
    
    employee = Employee(
        employee_number=data.employee_number,
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        phone=data.phone,
        department=data.department,
        position=data.position,
        hire_date=data.hire_date,
        employment_type=data.employment_type,
        salary=data.salary,
        address=data.address,
        manager_id=data.manager_id,
        user_id=data.user_id,
        tenant_id=current_user.tenant_id,
        status="active"
    )
    
    db.add(employee)
    await db.commit()
    await db.refresh(employee)
    
    return EmployeeResponse(
        id=employee.id,
        employee_number=employee.employee_number,
        first_name=employee.first_name,
        last_name=employee.last_name,
        full_name=f"{employee.first_name} {employee.last_name}",
        email=employee.email,
        phone=employee.phone,
        department=employee.department,
        position=employee.position,
        hire_date=employee.hire_date,
        employment_type=employee.employment_type,
        salary=float(employee.salary) if employee.salary else None,
        address=employee.address,
        manager_id=employee.manager_id,
        user_id=employee.user_id,
        status=employee.status,
        termination_date=employee.termination_date,
        created_at=employee.created_at,
        updated_at=employee.updated_at
    )


@router.put("/employees/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: UUID,
    data: EmployeeUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Update employee."""
    result = await db.execute(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.is_deleted == False
        )
    )
    employee = result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)
    
    await db.commit()
    await db.refresh(employee)
    
    return EmployeeResponse(
        id=employee.id,
        employee_number=employee.employee_number,
        first_name=employee.first_name,
        last_name=employee.last_name,
        full_name=f"{employee.first_name} {employee.last_name}",
        email=employee.email,
        phone=employee.phone,
        department=employee.department,
        position=employee.position,
        hire_date=employee.hire_date,
        employment_type=employee.employment_type,
        salary=float(employee.salary) if employee.salary else None,
        address=employee.address,
        manager_id=employee.manager_id,
        user_id=employee.user_id,
        status=employee.status,
        termination_date=employee.termination_date,
        created_at=employee.created_at,
        updated_at=employee.updated_at
    )


@router.delete("/employees/{employee_id}")
async def delete_employee(
    employee_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Soft delete employee."""
    result = await db.execute(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.is_deleted == False
        )
    )
    employee = result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    employee.is_deleted = True
    employee.deleted_at = datetime.utcnow()
    
    await db.commit()
    
    return {"success": True, "message": "Employee deleted"}


# ========================================
# Attendance Endpoints
# ========================================

@router.get("/attendance", response_model=List[AttendanceResponse])
async def list_attendance(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    employee_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """List attendance records."""
    query = select(AttendanceRecord)
    
    if employee_id:
        query = query.where(AttendanceRecord.employee_id == employee_id)
    
    if date_from:
        query = query.where(AttendanceRecord.date >= date_from)
    
    if date_to:
        query = query.where(AttendanceRecord.date <= date_to)
    
    query = query.order_by(AttendanceRecord.date.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    records = result.scalars().all()
    
    return [AttendanceResponse(
        id=r.id,
        employee_id=r.employee_id,
        date=r.date,
        check_in=r.check_in,
        check_out=r.check_out,
        status=r.status,
        notes=r.notes,
        hours_worked=float(r.hours_worked),
        overtime_hours=float(r.overtime_hours),
        created_at=r.created_at
    ) for r in records]


@router.post("/attendance/check-in")
async def check_in(
    employee_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Record check-in."""
    today = date.today()
    now = datetime.utcnow()
    
    # Check if already checked in
    existing = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.employee_id == employee_id,
            AttendanceRecord.date == today
        )
    )
    record = existing.scalar_one_or_none()
    
    if record and record.check_in:
        raise HTTPException(status_code=400, detail="Already checked in today")
    
    if not record:
        record = AttendanceRecord(
            employee_id=employee_id,
            date=today,
            check_in=now,
            status="present",
            tenant_id=current_user.tenant_id
        )
        db.add(record)
    else:
        record.check_in = now
        record.status = "present"
    
    await db.commit()
    
    return {"success": True, "check_in": now, "message": "Check-in recorded"}


@router.post("/attendance/check-out")
async def check_out(
    employee_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Record check-out."""
    today = date.today()
    now = datetime.utcnow()
    
    result = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.employee_id == employee_id,
            AttendanceRecord.date == today
        )
    )
    record = result.scalar_one_or_none()
    
    if not record or not record.check_in:
        raise HTTPException(status_code=400, detail="No check-in record found for today")
    
    if record.check_out:
        raise HTTPException(status_code=400, detail="Already checked out today")
    
    record.check_out = now
    
    # Calculate hours worked
    if record.check_in:
        diff = now - record.check_in
        hours = diff.total_seconds() / 3600
        record.hours_worked = hours
        
        # Calculate overtime (assuming 8 hour workday)
        if hours > 8:
            record.overtime_hours = hours - 8
    
    await db.commit()
    
    return {
        "success": True,
        "check_out": now,
        "hours_worked": float(record.hours_worked),
        "message": "Check-out recorded"
    }


# ========================================
# Payroll Endpoints
# ========================================

@router.get("/departments")
async def list_departments(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """List all departments."""
    result = await db.execute(
        select(Employee.department, func.count(Employee.id).label("count"))
        .where(Employee.is_deleted == False)
        .group_by(Employee.department)
    )
    departments = result.all()
    
    return [
        {"name": d.department or "Unassigned", "employee_count": d.count}
        for d in departments
    ]


@router.get("/payroll/runs", response_model=List[PayrollRunResponse])
async def list_payroll_runs(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """List payroll runs."""
    # Placeholder - would need PayrollRun model
    return []


@router.post("/payroll/runs", response_model=PayrollRunResponse)
async def create_payroll_run(
    data: PayrollRunCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Create a new payroll run."""
    # Placeholder - would need PayrollRun model
    return PayrollRunResponse(
        id=UUID("00000000-0000-0000-0000-000000000000"),
        period_start=data.period_start,
        period_end=data.period_end,
        description=data.description,
        status="draft"
    )


# ========================================
# Import models
# ========================================

from app.models.user import User
# Note: These would be defined in a separate HR models file
# For now, using placeholder models

class Employee:
    """Placeholder Employee model."""
    pass

class AttendanceRecord:
    """Placeholder AttendanceRecord model."""
    pass
