"""
Nexus ERP - Customer API Endpoints
==================================

This module provides Customer Relationship Management (CRM) API endpoints
for managing customers, contacts, leads, and opportunities.
"""

from datetime import datetime
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Query,
    Path,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import Optional, List
from uuid import UUID
import logging

from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.user import User
from app.models.crm import (
    Customer,
    Contact,
    CustomerAddress,
    Lead,
    Opportunity,
    CustomerType,
    CustomerStatus,
    LeadStatus,
    OpportunityStage,
)
from app.schemas.crm import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerListResponse,
    ContactCreate,
    ContactUpdate,
    ContactResponse,
    AddressCreate,
    AddressUpdate,
    AddressResponse,
    LeadCreate,
    LeadUpdate,
    LeadResponse,
    LeadListResponse,
    OpportunityCreate,
    OpportunityUpdate,
    OpportunityResponse,
    OpportunityListResponse,
)

router = APIRouter(prefix="/customers", tags=["CRM - Customers"])
logger = logging.getLogger(__name__)


# ========================================
# Customer Endpoints
# ========================================

@router.get(
    "",
    response_model=CustomerListResponse,
    summary="List Customers",
    description="Get paginated list of customers with optional filters",
)
async def list_customers(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query"),
    customer_type: Optional[str] = Query(None, description="Filter by type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    sales_rep_id: Optional[UUID] = Query(None, description="Filter by sales rep"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get paginated list of customers.
    
    - **page**: Page number (starts from 1)
    - **page_size**: Number of items per page
    - **search**: Search in name, email, phone
    - **customer_type**: Filter by customer type
    - **status**: Filter by status
    """
    # Build query
    query = select(Customer).where(Customer.is_deleted == False)
    
    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Customer.name.ilike(search_term),
                Customer.email.ilike(search_term),
                Customer.phone.ilike(search_term),
                Customer.code.ilike(search_term),
            )
        )
    
    if customer_type:
        query = query.where(Customer.customer_type == customer_type)
    
    if status:
        query = query.where(Customer.status == status)
    
    if sales_rep_id:
        query = query.where(Customer.sales_rep_id == sales_rep_id)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(Customer.created_at.desc()).offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    customers = result.scalars().all()
    
    return CustomerListResponse(
        items=[CustomerResponse.model_validate(c) for c in customers],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Customer",
    description="Create a new customer",
)
async def create_customer(
    customer_data: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("crm.customer.create")),
):
    """
    Create a new customer.
    
    Required permission: crm.customer.create
    """
    # Generate customer code if not provided
    if not customer_data.code:
        # Get next code
        result = await db.execute(
            select(func.count()).where(Customer.is_deleted == False)
        )
        count = result.scalar() or 0
        customer_data.code = f"CUST-{count + 1:06d}"
    
    # Check for duplicate code
    result = await db.execute(
        select(Customer).where(
            Customer.code == customer_data.code,
            Customer.is_deleted == False
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Customer with code '{customer_data.code}' already exists"
        )
    
    # Create customer
    customer = Customer(
        **customer_data.model_dump(exclude={"contacts", "addresses"}),
        tenant_id=current_user.tenant_id,
        created_by_id=current_user.id,
    )
    db.add(customer)
    await db.flush()
    
    # Create contacts if provided
    for contact_data in customer_data.contacts:
        contact = Contact(
            **contact_data.model_dump(),
            customer_id=customer.id,
            tenant_id=current_user.tenant_id,
            created_by_id=current_user.id,
        )
        db.add(contact)
    
    # Create addresses if provided
    for address_data in customer_data.addresses:
        address = CustomerAddress(
            **address_data.model_dump(),
            customer_id=customer.id,
            tenant_id=current_user.tenant_id,
            created_by_id=current_user.id,
        )
        db.add(address)
    
    await db.commit()
    await db.refresh(customer)
    
    logger.info(f"Customer created: {customer.code} by user {current_user.id}")
    
    return CustomerResponse.model_validate(customer)


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Get Customer",
    description="Get customer by ID",
)
async def get_customer(
    customer_id: UUID = Path(..., description="Customer ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get customer details by ID."""
    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.is_deleted == False
        )
    )
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    return CustomerResponse.model_validate(customer)


@router.put(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Update Customer",
    description="Update customer information",
)
async def update_customer(
    customer_id: UUID,
    customer_data: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("crm.customer.update")),
):
    """Update customer information."""
    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.is_deleted == False
        )
    )
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    # Update fields
    update_data = customer_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)
    
    customer.updated_by_id = current_user.id
    customer.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(customer)
    
    logger.info(f"Customer updated: {customer.code} by user {current_user.id}")
    
    return CustomerResponse.model_validate(customer)


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Customer",
    description="Soft delete a customer",
)
async def delete_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("crm.customer.delete")),
):
    """Soft delete a customer."""
    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.is_deleted == False
        )
    )
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    customer.soft_delete(current_user.id)
    await db.commit()
    
    logger.info(f"Customer deleted: {customer.code} by user {current_user.id}")


# ========================================
# Contact Endpoints
# ========================================

@router.get(
    "/{customer_id}/contacts",
    response_model=List[ContactResponse],
    summary="List Customer Contacts",
)
async def list_contacts(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all contacts for a customer."""
    result = await db.execute(
        select(Contact).where(
            Contact.customer_id == customer_id,
            Contact.is_deleted == False
        ).order_by(Contact.is_primary.desc(), Contact.created_at)
    )
    contacts = result.scalars().all()
    return [ContactResponse.model_validate(c) for c in contacts]


@router.post(
    "/{customer_id}/contacts",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Contact",
)
async def create_contact(
    customer_id: UUID,
    contact_data: ContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("crm.customer.update")),
):
    """Create a new contact for a customer."""
    # Verify customer exists
    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.is_deleted == False
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    contact = Contact(
        **contact_data.model_dump(),
        customer_id=customer_id,
        tenant_id=current_user.tenant_id,
        created_by_id=current_user.id,
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    
    return ContactResponse.model_validate(contact)


@router.put(
    "/{customer_id}/contacts/{contact_id}",
    response_model=ContactResponse,
    summary="Update Contact",
)
async def update_contact(
    customer_id: UUID,
    contact_id: UUID,
    contact_data: ContactUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("crm.customer.update")),
):
    """Update a contact."""
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.customer_id == customer_id,
            Contact.is_deleted == False
        )
    )
    contact = result.scalar_one_or_none()
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )
    
    update_data = contact_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contact, field, value)
    
    contact.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(contact)
    
    return ContactResponse.model_validate(contact)


@router.delete(
    "/{customer_id}/contacts/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Contact",
)
async def delete_contact(
    customer_id: UUID,
    contact_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("crm.customer.update")),
):
    """Delete a contact."""
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.customer_id == customer_id,
            Contact.is_deleted == False
        )
    )
    contact = result.scalar_one_or_none()
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )
    
    contact.soft_delete(current_user.id)
    await db.commit()


# ========================================
# Address Endpoints
# ========================================

@router.get(
    "/{customer_id}/addresses",
    response_model=List[AddressResponse],
    summary="List Customer Addresses",
)
async def list_addresses(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all addresses for a customer."""
    result = await db.execute(
        select(CustomerAddress).where(
            CustomerAddress.customer_id == customer_id,
            CustomerAddress.is_deleted == False
        ).order_by(CustomerAddress.is_default.desc())
    )
    addresses = result.scalars().all()
    return [AddressResponse.model_validate(a) for a in addresses]


@router.post(
    "/{customer_id}/addresses",
    response_model=AddressResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Address",
)
async def create_address(
    customer_id: UUID,
    address_data: AddressCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("crm.customer.update")),
):
    """Create a new address for a customer."""
    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.is_deleted == False
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    address = CustomerAddress(
        **address_data.model_dump(),
        customer_id=customer_id,
        tenant_id=current_user.tenant_id,
        created_by_id=current_user.id,
    )
    db.add(address)
    await db.commit()
    await db.refresh(address)
    
    return AddressResponse.model_validate(address)
