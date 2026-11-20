"""
Nexus ERP - Settings API Endpoints
==================================

REST API endpoints for system settings and configuration.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

from app.core.database import db_manager
from app.core.security import get_current_user

router = APIRouter(prefix="/settings", tags=["Settings"])


# ========================================
# Pydantic Schemas
# ========================================

class CompanySettingsBase(BaseModel):
    name: str
    legal_name: Optional[str] = None
    tax_id: Optional[str] = None
    registration_number: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    currency: str = "USD"
    timezone: str = "UTC"
    date_format: str = "YYYY-MM-DD"
    fiscal_year_start: int = 1  # Month number


class CompanySettingsUpdate(BaseModel):
    name: Optional[str] = None
    legal_name: Optional[str] = None
    tax_id: Optional[str] = None
    registration_number: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    currency: Optional[str] = None
    timezone: Optional[str] = None
    date_format: Optional[str] = None
    fiscal_year_start: Optional[int] = None
    logo_url: Optional[str] = None


class CompanySettingsResponse(CompanySettingsBase):
    id: UUID
    logo_url: Optional[str] = None
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserSettingsBase(BaseModel):
    language: str = "en"
    theme: str = "light"
    date_format: str = "YYYY-MM-DD"
    number_format: str = "#,##0.00"
    timezone: str = "UTC"
    email_notifications: bool = True
    browser_notifications: bool = False


class UserSettingsUpdate(BaseModel):
    language: Optional[str] = None
    theme: Optional[str] = None
    date_format: Optional[str] = None
    number_format: Optional[str] = None
    timezone: Optional[str] = None
    email_notifications: Optional[bool] = None
    browser_notifications: Optional[bool] = None


class UserSettingsResponse(UserSettingsBase):
    user_id: UUID
    
    class Config:
        from_attributes = True


class RoleBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    permissions: List[str] = []


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None


class RoleResponse(RoleBase):
    id: UUID
    is_system: bool = False
    is_active: bool = True
    user_count: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True


class PlanResponse(BaseModel):
    id: UUID
    code: str
    name: str
    description: Optional[str] = None
    monthly_price: float
    yearly_price: float
    max_users: int
    max_storage_mb: int
    features: Dict[str, Any]
    is_active: bool = True
    
    class Config:
        from_attributes = True


class SubscriptionResponse(BaseModel):
    id: UUID
    plan_id: UUID
    plan_name: str
    status: str
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    
    class Config:
        from_attributes = True


# ========================================
# Company Settings Endpoints
# ========================================

@router.get("/company", response_model=CompanySettingsResponse)
async def get_company_settings(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Get company settings for current tenant."""
    from app.models.tenant import Tenant
    
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return CompanySettingsResponse(
        id=tenant.id,
        name=tenant.name,
        legal_name=tenant.name,
        tax_id=None,
        registration_number=None,
        email=tenant.contact_email,
        phone=tenant.contact_phone,
        website=None,
        address_line1=tenant.address,
        address_line2=None,
        city=tenant.city,
        state=tenant.state,
        country=tenant.country,
        postal_code=tenant.postal_code,
        currency="USD",
        timezone="UTC",
        date_format="YYYY-MM-DD",
        fiscal_year_start=1,
        logo_url=tenant.logo_url,
        updated_at=tenant.updated_at
    )


@router.put("/company", response_model=CompanySettingsResponse)
async def update_company_settings(
    data: CompanySettingsUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Update company settings."""
    from app.models.tenant import Tenant
    
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Update tenant fields
    if data.name:
        tenant.name = data.name
    if data.email:
        tenant.contact_email = data.email
    if data.phone:
        tenant.contact_phone = data.phone
    if data.address_line1:
        tenant.address = data.address_line1
    if data.city:
        tenant.city = data.city
    if data.state:
        tenant.state = data.state
    if data.country:
        tenant.country = data.country
    if data.postal_code:
        tenant.postal_code = data.postal_code
    if data.logo_url:
        tenant.logo_url = data.logo_url
    
    await db.commit()
    await db.refresh(tenant)
    
    return CompanySettingsResponse(
        id=tenant.id,
        name=tenant.name,
        legal_name=tenant.name,
        tax_id=None,
        registration_number=None,
        email=tenant.contact_email,
        phone=tenant.contact_phone,
        website=None,
        address_line1=tenant.address,
        address_line2=None,
        city=tenant.city,
        state=tenant.state,
        country=tenant.country,
        postal_code=tenant.postal_code,
        currency="USD",
        timezone="UTC",
        date_format="YYYY-MM-DD",
        fiscal_year_start=1,
        logo_url=tenant.logo_url,
        updated_at=tenant.updated_at
    )


# ========================================
# User Settings Endpoints
# ========================================

@router.get("/user", response_model=UserSettingsResponse)
async def get_user_settings(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Get current user's settings."""
    from app.models.user import User
    
    result = await db.execute(
        select(User).where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    
    preferences = user.preferences or {}
    
    return UserSettingsResponse(
        user_id=user.id,
        language=preferences.get("language", "en"),
        theme=preferences.get("theme", "light"),
        date_format=preferences.get("date_format", "YYYY-MM-DD"),
        number_format=preferences.get("number_format", "#,##0.00"),
        timezone=preferences.get("timezone", "UTC"),
        email_notifications=preferences.get("email_notifications", True),
        browser_notifications=preferences.get("browser_notifications", False)
    )


@router.put("/user", response_model=UserSettingsResponse)
async def update_user_settings(
    data: UserSettingsUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Update current user's settings."""
    from app.models.user import User
    
    result = await db.execute(
        select(User).where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    
    preferences = user.preferences or {}
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        preferences[field] = value
    
    user.preferences = preferences
    
    await db.commit()
    await db.refresh(user)
    
    return UserSettingsResponse(
        user_id=user.id,
        language=preferences.get("language", "en"),
        theme=preferences.get("theme", "light"),
        date_format=preferences.get("date_format", "YYYY-MM-DD"),
        number_format=preferences.get("number_format", "#,##0.00"),
        timezone=preferences.get("timezone", "UTC"),
        email_notifications=preferences.get("email_notifications", True),
        browser_notifications=preferences.get("browser_notifications", False)
    )


# ========================================
# User Management Endpoints
# ========================================

@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """List users in tenant."""
    from app.models.user import User
    
    query = select(User).where(User.tenant_id == current_user.tenant_id)
    
    if search:
        query = query.where(
            or_(
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.username.ilike(f"%{search}%")
            )
        )
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    
    query = query.order_by(User.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return {
        "items": [
            {
                "id": str(u.id),
                "username": u.username,
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "full_name": f"{u.first_name} {u.last_name}",
                "is_active": u.is_active,
                "is_verified": u.is_verified,
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "created_at": u.created_at.isoformat()
            }
            for u in users
        ],
        "total": len(users),  # Would need count query for actual total
        "page": page,
        "page_size": page_size
    }


@router.post("/users")
async def create_user(
    username: str,
    email: str,
    password: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    role_ids: Optional[List[UUID]] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Create a new user in tenant."""
    from app.models.user import User
    from app.core.security import get_password_hash
    
    # Check if username/email exists
    existing = await db.execute(
        select(User).where(
            or_(User.username == username, User.email == email)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    user = User(
        username=username,
        email=email,
        password_hash=get_password_hash(password),
        first_name=first_name,
        last_name=last_name,
        tenant_id=current_user.tenant_id,
        is_active=True
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return {
        "success": True,
        "id": str(user.id),
        "username": user.username,
        "email": user.email
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: UUID,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
    is_active: Optional[bool] = None,
    role_ids: Optional[List[UUID]] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Update a user."""
    from app.models.user import User
    
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if first_name is not None:
        user.first_name = first_name
    if last_name is not None:
        user.last_name = last_name
    if email is not None:
        user.email = email
    if is_active is not None:
        user.is_active = is_active
    
    await db.commit()
    
    return {"success": True, "message": "User updated"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Delete a user."""
    from app.models.user import User
    
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.delete(user)
    await db.commit()
    
    return {"success": True, "message": "User deleted"}


# ========================================
# Role Management Endpoints
# ========================================

@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """List all roles."""
    from app.models.user import Role
    
    result = await db.execute(
        select(Role).order_by(Role.name)
    )
    roles = result.scalars().all()
    
    return [
        RoleResponse(
            id=r.id,
            name=r.name,
            code=r.code,
            description=r.description,
            permissions=r.permissions or [],
            is_system=r.is_system,
            is_active=True,
            user_count=0,  # Would need count query
            created_at=r.created_at
        )
        for r in roles
    ]


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    data: RoleCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Create a new role."""
    from app.models.user import Role
    
    # Check if code exists
    existing = await db.execute(
        select(Role).where(Role.code == data.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Role code already exists")
    
    role = Role(
        name=data.name,
        code=data.code,
        description=data.description,
        permissions=data.permissions,
        tenant_id=current_user.tenant_id
    )
    
    db.add(role)
    await db.commit()
    await db.refresh(role)
    
    return RoleResponse(
        id=role.id,
        name=role.name,
        code=role.code,
        description=role.description,
        permissions=role.permissions or [],
        is_system=False,
        is_active=True,
        user_count=0,
        created_at=role.created_at
    )


# ========================================
# Plan & Subscription Endpoints
# ========================================

@router.get("/plans", response_model=List[PlanResponse])
async def list_plans(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """List available subscription plans."""
    from app.models.tenant import Plan
    
    result = await db.execute(
        select(Plan).where(Plan.is_active == True).order_by(Plan.monthly_price)
    )
    plans = result.scalars().all()
    
    return [
        PlanResponse(
            id=p.id,
            code=p.code,
            name=p.name,
            description=p.description,
            monthly_price=float(p.monthly_price),
            yearly_price=float(p.yearly_price),
            max_users=p.max_users,
            max_storage_mb=p.max_storage_mb,
            features=p.features or {},
            is_active=p.is_active
        )
        for p in plans
    ]


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Get current subscription details."""
    from app.models.tenant import Tenant, Subscription
    
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Get subscription
    sub_result = await db.execute(
        select(Subscription).where(Subscription.tenant_id == tenant.id)
    )
    subscription = sub_result.scalar_one_or_none()
    
    if subscription:
        return SubscriptionResponse(
            id=subscription.id,
            plan_id=subscription.plan_id,
            plan_name=tenant.plan_type.value if tenant.plan_type else "basic",
            status=subscription.status,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            cancel_at_period_end=subscription.cancel_at_period_end
        )
    
    return SubscriptionResponse(
        id=UUID("00000000-0000-0000-0000-000000000000"),
        plan_id=UUID("00000000-0000-0000-0000-000000000000"),
        plan_name=tenant.plan_type.value if tenant.plan_type else "basic",
        status="active" if tenant.is_active else "inactive"
    )


# ========================================
# Available Options Endpoints
# ========================================

@router.get("/currencies")
async def list_currencies():
    """List available currencies."""
    return [
        {"code": "USD", "name": "US Dollar", "symbol": "$"},
        {"code": "EUR", "name": "Euro", "symbol": "€"},
        {"code": "GBP", "name": "British Pound", "symbol": "£"},
        {"code": "SAR", "name": "Saudi Riyal", "symbol": "ر.س"},
        {"code": "AED", "name": "UAE Dirham", "symbol": "د.إ"},
        {"code": "EGP", "name": "Egyptian Pound", "symbol": "ج.م"},
        {"code": "JPY", "name": "Japanese Yen", "symbol": "¥"},
        {"code": "CNY", "name": "Chinese Yuan", "symbol": "¥"},
    ]


@router.get("/timezones")
async def list_timezones():
    """List available timezones."""
    return [
        {"code": "UTC", "name": "UTC"},
        {"code": "America/New_York", "name": "Eastern Time (US)"},
        {"code": "America/Los_Angeles", "name": "Pacific Time (US)"},
        {"code": "Europe/London", "name": "London"},
        {"code": "Europe/Paris", "name": "Paris"},
        {"code": "Asia/Dubai", "name": "Dubai"},
        {"code": "Asia/Riyadh", "name": "Riyadh"},
        {"code": "Asia/Cairo", "name": "Cairo"},
        {"code": "Asia/Shanghai", "name": "Shanghai"},
        {"code": "Asia/Tokyo", "name": "Tokyo"},
    ]


@router.get("/languages")
async def list_languages():
    """List available languages."""
    return [
        {"code": "en", "name": "English"},
        {"code": "ar", "name": "العربية"},
        {"code": "fr", "name": "Français"},
        {"code": "es", "name": "Español"},
        {"code": "de", "name": "Deutsch"},
        {"code": "zh", "name": "中文"},
        {"code": "ja", "name": "日本語"},
    ]
