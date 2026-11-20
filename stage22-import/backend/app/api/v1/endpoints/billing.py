"""
Nexus ERP - Billing API Endpoints
==================================

REST API endpoints for subscription billing management.

Features:
- Plan listing and management
- Subscription CRUD operations
- Stripe webhook handling
- Invoice management
- Payment method management
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
import logging
import stripe

from app.core.database import db_manager
from app.core.config import settings
from app.models.tenant import Tenant, Plan, Subscription, BillingInvoice, PlanType, TenantStatus
from app.services.billing_service import BillingService, PLAN_CONFIGS, BillingError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])


# ========================================
# Pydantic Schemas
# ========================================

class PlanResponse(BaseModel):
    """Plan response schema."""
    id: str
    code: str
    name: str
    description: Optional[str]
    plan_type: str
    monthly_price: float
    yearly_price: float
    trial_days: int
    max_users: int
    max_storage_mb: int
    max_products: int
    max_customers: int
    features: dict
    
    class Config:
        from_attributes = True


class SubscriptionCreate(BaseModel):
    """Subscription creation schema."""
    plan_id: UUID
    payment_method_id: str
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|yearly)$")


class SubscriptionResponse(BaseModel):
    """Subscription response schema."""
    id: str
    tenant_id: str
    plan_id: Optional[str]
    status: str
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    cancel_at_period_end: bool
    quantity: int
    unit_price: float
    trial_start: Optional[datetime]
    trial_end: Optional[datetime]
    
    class Config:
        from_attributes = True


class InvoiceResponse(BaseModel):
    """Invoice response schema."""
    id: str
    invoice_number: str
    status: str
    subtotal: float
    tax: float
    discount: float
    total: float
    amount_paid: float
    amount_due: float
    currency: str
    invoice_date: datetime
    due_date: Optional[datetime]
    paid_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class CheckoutSessionCreate(BaseModel):
    """Checkout session creation schema."""
    plan_id: UUID
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|yearly)$")
    success_url: str
    cancel_url: str


class PaymentMethodAttach(BaseModel):
    """Payment method attachment schema."""
    payment_method_id: str
    set_default: bool = True


# ========================================
# Plan Endpoints
# ========================================

@router.get("/plans", response_model=List[PlanResponse])
async def list_plans():
    """
    List all available subscription plans.
    
    Returns:
        List of available plans with features and pricing.
    """
    billing_service = BillingService()
    plans = await billing_service.list_plans()
    
    # Get plans from database
    async with db_manager.get_session() as db:
        result = await db.execute(
            select(Plan).where(Plan.is_active == True, Plan.is_public == True)
        )
        db_plans = result.scalars().all()
        
        # If no plans in DB, return service configs
        if not db_plans:
            return [
                PlanResponse(
                    id=f"plan_{p['type']}",
                    code=p['type'],
                    name=p['name'],
                    description=p['description'],
                    plan_type=p['type'],
                    monthly_price=p['monthly_price'],
                    yearly_price=p['yearly_price'],
                    trial_days=p['trial_days'],
                    max_users=p['max_users'],
                    max_storage_mb=p['max_storage_mb'],
                    max_products=p['max_products'],
                    max_customers=p['max_customers'],
                    features=p['features']
                )
                for p in plans
            ]
        
        return [
            PlanResponse(
                id=str(p.id),
                code=p.code,
                name=p.name,
                description=p.description,
                plan_type=p.plan_type.value,
                monthly_price=float(p.monthly_price),
                yearly_price=float(p.yearly_price),
                trial_days=p.trial_days,
                max_users=p.max_users,
                max_storage_mb=p.max_storage_mb,
                max_products=p.max_products,
                max_customers=p.max_customers,
                features=p.features
            )
            for p in db_plans
        ]


@router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: UUID):
    """
    Get a specific plan by ID.
    
    Args:
        plan_id: Plan UUID
        
    Returns:
        Plan details
    """
    async with db_manager.get_session() as db:
        result = await db.execute(
            select(Plan).where(Plan.id == plan_id)
        )
        plan = result.scalar_one_or_none()
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found"
            )
        
        return PlanResponse(
            id=str(plan.id),
            code=plan.code,
            name=plan.name,
            description=plan.description,
            plan_type=plan.plan_type.value,
            monthly_price=float(plan.monthly_price),
            yearly_price=float(plan.yearly_price),
            trial_days=plan.trial_days,
            max_users=plan.max_users,
            max_storage_mb=plan.max_storage_mb,
            max_products=plan.max_products,
            max_customers=plan.max_customers,
            features=plan.features
        )


# ========================================
# Subscription Endpoints
# ========================================

@router.post("/subscriptions", response_model=dict)
async def create_subscription(
    data: SubscriptionCreate,
    tenant_id: UUID  # In production, get from auth context
):
    """
    Create a new subscription for a tenant.
    
    Args:
        data: Subscription creation data
        tenant_id: Tenant UUID
        
    Returns:
        Subscription details including payment client secret
    """
    billing_service = BillingService()
    
    async with db_manager.get_session() as db:
        # Get tenant
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Get plan
        result = await db.execute(
            select(Plan).where(Plan.id == data.plan_id)
        )
        plan = result.scalar_one_or_none()
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found"
            )
        
        try:
            subscription = await billing_service.create_subscription(
                tenant=tenant,
                plan=plan,
                payment_method_id=data.payment_method_id,
                billing_cycle=data.billing_cycle
            )
            
            # Update tenant status
            tenant.status = TenantStatus.ACTIVE
            tenant.stripe_subscription_id = subscription["subscription_id"]
            await db.commit()
            
            return {
                "success": True,
                "subscription": subscription
            }
            
        except BillingError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )


@router.get("/subscriptions/{tenant_id}", response_model=dict)
async def get_subscription(tenant_id: UUID):
    """
    Get current subscription for a tenant.
    
    Args:
        tenant_id: Tenant UUID
        
    Returns:
        Subscription details
    """
    async with db_manager.get_session() as db:
        result = await db.execute(
            select(Subscription).where(
                Subscription.tenant_id == tenant_id,
                Subscription.status.in_(["active", "trialing"])
            )
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            return {
                "subscription": None,
                "plan": None
            }
        
        # Get plan details
        plan_result = await db.execute(
            select(Plan).where(Plan.id == subscription.plan_id)
        )
        plan = plan_result.scalar_one_or_none()
        
        return {
            "subscription": SubscriptionResponse(
                id=str(subscription.id),
                tenant_id=str(subscription.tenant_id),
                plan_id=str(subscription.plan_id) if subscription.plan_id else None,
                status=subscription.status,
                current_period_start=subscription.current_period_start,
                current_period_end=subscription.current_period_end,
                cancel_at_period_end=subscription.cancel_at_period_end,
                quantity=subscription.quantity,
                unit_price=float(subscription.unit_price),
                trial_start=subscription.trial_start,
                trial_end=subscription.trial_end
            ),
            "plan": PlanResponse(
                id=str(plan.id),
                code=plan.code,
                name=plan.name,
                description=plan.description,
                plan_type=plan.plan_type.value,
                monthly_price=float(plan.monthly_price),
                yearly_price=float(plan.yearly_price),
                trial_days=plan.trial_days,
                max_users=plan.max_users,
                max_storage_mb=plan.max_storage_mb,
                max_products=plan.max_products,
                max_customers=plan.max_customers,
                features=plan.features
            ) if plan else None
        }


@router.post("/subscriptions/{tenant_id}/cancel")
async def cancel_subscription(
    tenant_id: UUID,
    immediately: bool = False,
    reason: Optional[str] = None
):
    """
    Cancel a tenant's subscription.
    
    Args:
        tenant_id: Tenant UUID
        immediately: Cancel now or at period end
        reason: Cancellation reason
        
    Returns:
        Cancelled subscription details
    """
    billing_service = BillingService()
    
    async with db_manager.get_session() as db:
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant or not tenant.stripe_subscription_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )
        
        try:
            subscription = await billing_service.cancel_subscription(
                tenant.stripe_subscription_id,
                immediately=immediately,
                reason=reason
            )
            
            if immediately:
                tenant.status = TenantStatus.CANCELLED
                tenant.cancelled_at = datetime.utcnow()
            
            await db.commit()
            
            return {
                "success": True,
                "subscription": subscription
            }
            
        except BillingError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )


@router.post("/subscriptions/{tenant_id}/reactivate")
async def reactivate_subscription(tenant_id: UUID):
    """
    Reactivate a cancelled subscription.
    
    Args:
        tenant_id: Tenant UUID
        
    Returns:
        Reactivated subscription details
    """
    billing_service = BillingService()
    
    async with db_manager.get_session() as db:
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant or not tenant.stripe_subscription_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No subscription found"
            )
        
        try:
            subscription = await billing_service.reactivate_subscription(
                tenant.stripe_subscription_id
            )
            
            tenant.status = TenantStatus.ACTIVE
            tenant.cancelled_at = None
            await db.commit()
            
            return {
                "success": True,
                "subscription": subscription
            }
            
        except BillingError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )


# ========================================
# Checkout Endpoints
# ========================================

@router.post("/checkout/session")
async def create_checkout_session(
    data: CheckoutSessionCreate,
    tenant_id: UUID  # In production, get from auth context
):
    """
    Create a Stripe checkout session.
    
    Args:
        data: Checkout session data
        tenant_id: Tenant UUID
        
    Returns:
        Checkout session URL
    """
    billing_service = BillingService()
    
    async with db_manager.get_session() as db:
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        result = await db.execute(
            select(Plan).where(Plan.id == data.plan_id)
        )
        plan = result.scalar_one_or_none()
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found"
            )
        
        try:
            session = await billing_service.create_checkout_session(
                tenant=tenant,
                plan=plan,
                success_url=data.success_url,
                cancel_url=data.cancel_url,
                billing_cycle=data.billing_cycle
            )
            
            return {
                "success": True,
                "session_id": session["session_id"],
                "url": session["url"]
            }
            
        except BillingError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )


@router.get("/portal/{tenant_id}")
async def create_portal_session(
    tenant_id: UUID,
    return_url: str
):
    """
    Create a billing portal session for self-service.
    
    Args:
        tenant_id: Tenant UUID
        return_url: URL to return after portal session
        
    Returns:
        Portal session URL
    """
    billing_service = BillingService()
    
    async with db_manager.get_session() as db:
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant or not tenant.stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No customer found"
            )
        
        try:
            session = await billing_service.create_billing_portal_session(
                customer_id=tenant.stripe_customer_id,
                return_url=return_url
            )
            
            return {
                "success": True,
                "url": session["url"]
            }
            
        except BillingError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )


# ========================================
# Invoice Endpoints
# ========================================

@router.get("/invoices/{tenant_id}", response_model=List[InvoiceResponse])
async def list_invoices(
    tenant_id: UUID,
    limit: int = 10,
    starting_after: Optional[str] = None
):
    """
    List invoices for a tenant.
    
    Args:
        tenant_id: Tenant UUID
        limit: Maximum number of invoices
        starting_after: Pagination cursor
        
    Returns:
        List of invoices
    """
    async with db_manager.get_session() as db:
        result = await db.execute(
            select(BillingInvoice)
            .where(BillingInvoice.tenant_id == tenant_id)
            .order_by(BillingInvoice.created_at.desc())
            .limit(limit)
        )
        invoices = result.scalars().all()
        
        return [
            InvoiceResponse(
                id=str(inv.id),
                invoice_number=inv.invoice_number,
                status=inv.status,
                subtotal=float(inv.subtotal),
                tax=float(inv.tax),
                discount=float(inv.discount),
                total=float(inv.total),
                amount_paid=float(inv.amount_paid),
                amount_due=float(inv.amount_due),
                currency=inv.currency,
                invoice_date=inv.invoice_date,
                due_date=inv.due_date,
                paid_at=inv.paid_at
            )
            for inv in invoices
        ]


@router.get("/invoices/{tenant_id}/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(tenant_id: UUID, invoice_id: UUID):
    """
    Get a specific invoice.
    
    Args:
        tenant_id: Tenant UUID
        invoice_id: BillingInvoice UUID
        
    Returns:
        Invoice details
    """
    async with db_manager.get_session() as db:
        result = await db.execute(
            select(BillingInvoice).where(
                BillingInvoice.id == invoice_id,
                BillingInvoice.tenant_id == tenant_id
            )
        )
        invoice = result.scalar_one_or_none()
        
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )
        
        return InvoiceResponse(
            id=str(invoice.id),
            invoice_number=invoice.invoice_number,
            status=invoice.status,
            subtotal=float(invoice.subtotal),
            tax=float(invoice.tax),
            discount=float(invoice.discount),
            total=float(invoice.total),
            amount_paid=float(invoice.amount_paid),
            amount_due=float(invoice.amount_due),
            currency=invoice.currency,
            invoice_date=invoice.invoice_date,
            due_date=invoice.due_date,
            paid_at=invoice.paid_at
        )


# ========================================
# Payment Method Endpoints
# ========================================

@router.get("/payment-methods/{tenant_id}")
async def list_payment_methods(tenant_id: UUID):
    """
    List payment methods for a tenant.
    
    Args:
        tenant_id: Tenant UUID
        
    Returns:
        List of payment methods
    """
    billing_service = BillingService()
    
    async with db_manager.get_session() as db:
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant or not tenant.stripe_customer_id:
            return {"payment_methods": []}
        
        try:
            methods = await billing_service.get_payment_methods(
                tenant.stripe_customer_id
            )
            
            return {
                "payment_methods": methods
            }
            
        except BillingError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )


@router.post("/payment-methods/{tenant_id}/attach")
async def attach_payment_method(
    tenant_id: UUID,
    data: PaymentMethodAttach
):
    """
    Attach a payment method to a tenant.
    
    Args:
        tenant_id: Tenant UUID
        data: Payment method attachment data
        
    Returns:
        Attached payment method details
    """
    billing_service = BillingService()
    
    async with db_manager.get_session() as db:
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Create customer if needed
        if not tenant.stripe_customer_id:
            customer = await billing_service.create_customer(tenant)
            tenant.stripe_customer_id = customer["customer_id"]
            await db.flush()
        
        try:
            method = await billing_service.attach_payment_method(
                customer_id=tenant.stripe_customer_id,
                payment_method_id=data.payment_method_id,
                set_default=data.set_default
            )
            
            await db.commit()
            
            return {
                "success": True,
                "payment_method": method
            }
            
        except BillingError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )


@router.delete("/payment-methods/{payment_method_id}")
async def detach_payment_method(payment_method_id: str):
    """
    Detach a payment method.
    
    Args:
        payment_method_id: Payment method ID
        
    Returns:
        Success status
    """
    billing_service = BillingService()
    
    try:
        await billing_service.detach_payment_method(payment_method_id)
        
        return {
            "success": True,
            "message": "Payment method detached"
        }
        
    except BillingError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ========================================
# Webhook Endpoint
# ========================================

@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Handle Stripe webhook events.
    
    This endpoint receives webhook events from Stripe and processes them
    to update subscription status, handle payments, etc.
    
    Returns:
        Success status
    """
    billing_service = BillingService()
    
    # Get raw body for signature verification
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature"
        )
    
    try:
        # Verify webhook signature
        event = billing_service.verify_webhook_signature(
            payload=payload,
            sig_header=sig_header
        )
        
        # Process event in background
        async with db_manager.get_session() as db:
            result = await billing_service.handle_webhook_event(event, db)
        
        logger.info(f"Processed webhook event: {event['type']}")
        
        return {
            "success": True,
            "event_type": event["type"],
            "result": result
        }
        
    except BillingError as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ========================================
# Trial Endpoints
# ========================================

@router.post("/trials/{tenant_id}/start")
async def start_trial(
    tenant_id: UUID,
    plan_type: str = "pro"
):
    """
    Start a trial period for a tenant.
    
    Args:
        tenant_id: Tenant UUID
        plan_type: Plan type for trial
        
    Returns:
        Trial details
    """
    billing_service = BillingService()
    
    async with db_manager.get_session() as db:
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Get plan
        result = await db.execute(
            select(Plan).where(Plan.plan_type == PlanType(plan_type))
        )
        plan = result.scalar_one_or_none()
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found"
            )
        
        try:
            trial = await billing_service.start_trial(tenant, plan)
            await db.commit()
            
            return {
                "success": True,
                "trial": trial
            }
            
        except BillingError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )


@router.post("/trials/{tenant_id}/extend")
async def extend_trial(
    tenant_id: UUID,
    additional_days: int = 7
):
    """
    Extend a trial period.
    
    Args:
        tenant_id: Tenant UUID
        additional_days: Days to extend
        
    Returns:
        Updated trial details
    """
    billing_service = BillingService()
    
    async with db_manager.get_session() as db:
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        try:
            trial = await billing_service.extend_trial(tenant, additional_days)
            await db.commit()
            
            return {
                "success": True,
                "trial": trial
            }
            
        except BillingError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
