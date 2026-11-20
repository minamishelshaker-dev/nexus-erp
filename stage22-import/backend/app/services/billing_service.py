"""
Nexus ERP - Billing Service
===========================

This module provides Stripe integration for subscription billing.

Features:
- Customer creation and management
- Subscription management with plan upgrades/downgrades
- Invoice handling and PDF generation
- Webhook event processing
- Usage tracking for metered billing
- Trial period handling
- Plan management (Basic, Pro, Enterprise)
- Payment method management
- Proration handling
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID
import logging
import json
import asyncio
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
import stripe

from app.core.config import settings
from app.models.tenant import Tenant, TenantStatus, Subscription, Plan, BillingInvoice, PlanType

logger = logging.getLogger(__name__)


# ========================================
# Plan Definitions
# ========================================

PLAN_CONFIGS = {
    PlanType.BASIC: {
        "name": "Basic",
        "description": "Perfect for small businesses getting started",
        "monthly_price": 29,
        "yearly_price": 290,  # ~17% discount
        "trial_days": 14,
        "max_users": 5,
        "max_storage_mb": 1024,
        "max_products": 100,
        "max_customers": 500,
        "api_calls_limit": 10000,
        "features": {
            "inventory": True,
            "sales": True,
            "purchase": True,
            "accounting": True,
            "crm": True,
            "manufacturing": False,
            "ai_features": False,
            "api_access": False,
            "custom_reports": False,
            "multi_warehouse": False,
            "advanced_analytics": False,
            "workflow_automation": False,
        }
    },
    PlanType.PRO: {
        "name": "Professional",
        "description": "Ideal for growing businesses",
        "monthly_price": 79,
        "yearly_price": 790,  # ~17% discount
        "trial_days": 14,
        "max_users": 25,
        "max_storage_mb": 10240,
        "max_products": 1000,
        "max_customers": 5000,
        "api_calls_limit": 100000,
        "features": {
            "inventory": True,
            "sales": True,
            "purchase": True,
            "accounting": True,
            "crm": True,
            "manufacturing": True,
            "ai_features": True,
            "api_access": True,
            "custom_reports": True,
            "multi_warehouse": True,
            "advanced_analytics": True,
            "workflow_automation": True,
        }
    },
    PlanType.ENTERPRISE: {
        "name": "Enterprise",
        "description": "For large organizations with custom needs",
        "monthly_price": 199,
        "yearly_price": 1990,  # ~17% discount
        "trial_days": 30,
        "max_users": -1,  # Unlimited
        "max_storage_mb": -1,  # Unlimited
        "max_products": -1,  # Unlimited
        "max_customers": -1,  # Unlimited
        "api_calls_limit": -1,  # Unlimited
        "features": {
            "inventory": True,
            "sales": True,
            "purchase": True,
            "accounting": True,
            "crm": True,
            "manufacturing": True,
            "ai_features": True,
            "api_access": True,
            "custom_reports": True,
            "multi_warehouse": True,
            "advanced_analytics": True,
            "workflow_automation": True,
            "white_label": True,
            "dedicated_support": True,
            "custom_integrations": True,
            "sla": True,
            "sso": True,
            "audit_logs": True,
            "data_export": True,
        }
    }
}


class BillingService:
    """
    Billing Service for Stripe integration.
    
    Handles all Stripe-related operations including:
    - Customer management
    - Subscription management with upgrades/downgrades
    - Payment processing
    - Webhook handling
    - Plan management
    - Trial period handling
    """
    
    def __init__(self):
        """Initialize Stripe with API key."""
        stripe.api_key = getattr(settings, 'STRIPE_API_KEY', None)
        self.webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
        
        # Create plan products and prices in Stripe if needed
        self._ensure_plans_exist()
    
    def _ensure_plans_exist(self):
        """
        Ensure that plan products and prices exist in Stripe.
        
        This is called during initialization to set up billing.
        """
        if not stripe.api_key:
            logger.warning("Stripe API key not configured, skipping plan setup")
            return
        
        try:
            # Check if products exist, create if not
            for plan_type, config in PLAN_CONFIGS.items():
                product_name = f"Nexus ERP {config['name']}"
                
                # Try to find existing product
                products = stripe.Product.list(
                    active=True,
                    limit=100
                )
                
                existing = None
                for p in products.data:
                    if p.metadata.get("plan_type") == plan_type.value:
                        existing = p
                        break
                
                if not existing:
                    logger.info(f"Creating Stripe product for {plan_type.value}")
                    stripe.Product.create(
                        name=product_name,
                        description=config["description"],
                        metadata={"plan_type": plan_type.value}
                    )
                    
        except stripe.error.StripeError as e:
            logger.error(f"Error ensuring plans exist: {e}")
    
    # ========================================
    # Customer Management
    # ========================================
    
    async def create_customer(
        self,
        tenant: Tenant,
        payment_method_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe customer for a tenant.
        
        Args:
            tenant: Tenant model instance
            payment_method_id: Optional payment method to attach
            
        Returns:
            Dict with customer details
        """
        try:
            customer_data = {
                "email": tenant.contact_email,
                "name": tenant.name,
                "metadata": {
                    "tenant_id": str(tenant.id),
                    "tenant_slug": tenant.slug,
                }
            }
            
            if payment_method_id:
                customer_data["payment_method"] = payment_method_id
                customer_data["invoice_settings"] = {
                    "default_payment_method": payment_method_id
                }
            
            customer = stripe.Customer.create(**customer_data)
            
            logger.info(f"Created Stripe customer {customer.id} for tenant {tenant.id}")
            
            return {
                "customer_id": customer.id,
                "email": customer.email,
                "name": customer.name,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe customer creation error: {e}")
            raise BillingError(f"Failed to create customer: {str(e)}")
    
    async def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Get Stripe customer details.
        
        Args:
            customer_id: Stripe customer ID
            
        Returns:
            Customer dict or None
        """
        try:
            customer = stripe.Customer.retrieve(customer_id)
            return {
                "id": customer.id,
                "email": customer.email,
                "name": customer.name,
                "default_payment_method": customer.invoice_settings.default_payment_method if customer.invoice_settings else None,
            }
        except stripe.error.InvalidRequestError:
            return None
        except stripe.error.StripeError as e:
            logger.error(f"Stripe customer retrieval error: {e}")
            raise BillingError(f"Failed to get customer: {str(e)}")
    
    async def update_customer(
        self,
        customer_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update Stripe customer details.
        
        Args:
            customer_id: Stripe customer ID
            **kwargs: Fields to update
            
        Returns:
            Updated customer dict
        """
        try:
            customer = stripe.Customer.modify(customer_id, **kwargs)
            return {
                "id": customer.id,
                "email": customer.email,
                "name": customer.name,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe customer update error: {e}")
            raise BillingError(f"Failed to update customer: {str(e)}")
    
    async def delete_customer(self, customer_id: str) -> bool:
        """
        Delete a Stripe customer.
        
        Args:
            customer_id: Stripe customer ID
            
        Returns:
            True if successful
        """
        try:
            stripe.Customer.delete(customer_id)
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Stripe customer deletion error: {e}")
            raise BillingError(f"Failed to delete customer: {str(e)}")
    
    # ========================================
    # Subscription Management
    # ========================================
    
    async def create_subscription(
        self,
        tenant: Tenant,
        plan: Plan,
        payment_method_id: str,
        billing_cycle: str = "monthly",
        trial_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a subscription for a tenant.
        
        Args:
            tenant: Tenant model instance
            plan: Plan model instance
            payment_method_id: Payment method ID
            billing_cycle: "monthly" or "yearly"
            trial_days: Override trial days
            
        Returns:
            Subscription details
        """
        try:
            # Create customer if needed
            if not tenant.stripe_customer_id:
                customer = await self.create_customer(tenant, payment_method_id)
                tenant.stripe_customer_id = customer["customer_id"]
            else:
                # Attach payment method to existing customer
                stripe.PaymentMethod.attach(
                    payment_method_id,
                    customer=tenant.stripe_customer_id
                )
                stripe.Customer.modify(
                    tenant.stripe_customer_id,
                    invoice_settings={
                        "default_payment_method": payment_method_id
                    }
                )
            
            # Get price ID based on billing cycle
            price_id = (
                plan.stripe_price_id_yearly if billing_cycle == "yearly"
                else plan.stripe_price_id_monthly
            )
            
            if not price_id:
                raise BillingError("Plan not configured for billing")
            
            # Create subscription
            subscription_data = {
                "customer": tenant.stripe_customer_id,
                "items": [{"price": price_id}],
                "payment_behavior": "default_incomplete",
                "expand": ["latest_invoice.payment_intent"],
                "metadata": {
                    "tenant_id": str(tenant.id),
                    "plan_id": str(plan.id),
                }
            }
            
            # Handle trial
            if trial_days is not None and trial_days > 0:
                subscription_data["trial_period_days"] = trial_days
            elif plan.trial_days > 0:
                subscription_data["trial_period_days"] = plan.trial_days
            
            subscription = stripe.Subscription.create(**subscription_data)
            
            logger.info(f"Created subscription {subscription.id} for tenant {tenant.id}")
            
            return {
                "subscription_id": subscription.id,
                "status": subscription.status,
                "current_period_start": datetime.fromtimestamp(subscription.current_period_start),
                "current_period_end": datetime.fromtimestamp(subscription.current_period_end),
                "trial_start": datetime.fromtimestamp(subscription.trial_start) if subscription.trial_start else None,
                "trial_end": datetime.fromtimestamp(subscription.trial_end) if subscription.trial_end else None,
                "client_secret": subscription.latest_invoice.payment_intent.client_secret if subscription.latest_invoice else None,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription creation error: {e}")
            raise BillingError(f"Failed to create subscription: {str(e)}")
    
    async def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """
        Get subscription details.
        
        Args:
            subscription_id: Stripe subscription ID
            
        Returns:
            Subscription dict or None
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return self._parse_subscription(subscription)
        except stripe.error.InvalidRequestError:
            return None
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription retrieval error: {e}")
            raise BillingError(f"Failed to get subscription: {str(e)}")
    
    async def update_subscription(
        self,
        subscription_id: str,
        new_price_id: Optional[str] = None,
        quantity: Optional[int] = None,
        proration_behavior: str = "create_prorations",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update a subscription (plan change, seat update, etc.).
        
        Args:
            subscription_id: Stripe subscription ID
            new_price_id: New price ID for plan change
            quantity: New quantity
            proration_behavior: How to handle proration
            **kwargs: Other subscription parameters
            
        Returns:
            Updated subscription dict
        """
        try:
            update_data = {
                "proration_behavior": proration_behavior,
                "metadata": kwargs.get("metadata", {})
            }
            
            if new_price_id:
                subscription = stripe.Subscription.retrieve(subscription_id)
                update_data["items"] = [{
                    "id": subscription["items"]["data"][0].id,
                    "price": new_price_id
                }]
            
            if quantity is not None:
                if "items" not in update_data:
                    subscription = stripe.Subscription.retrieve(subscription_id)
                    update_data["items"] = [{
                        "id": subscription["items"]["data"][0].id,
                        "quantity": quantity
                    }]
                else:
                    update_data["items"][0]["quantity"] = quantity
            
            subscription = stripe.Subscription.modify(subscription_id, **update_data)
            return self._parse_subscription(subscription)
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription update error: {e}")
            raise BillingError(f"Failed to update subscription: {str(e)}")
    
    async def cancel_subscription(
        self,
        subscription_id: str,
        immediately: bool = False,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            immediately: Cancel now or at period end
            reason: Cancellation reason for records
            
        Returns:
            Cancelled subscription dict
        """
        try:
            if immediately:
                subscription = stripe.Subscription.delete(
                    subscription_id,
                    cancellation_details={"reason": reason} if reason else None
                )
            else:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True,
                    cancellation_details={"reason": reason} if reason else None
                )
            
            return self._parse_subscription(subscription)
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription cancellation error: {e}")
            raise BillingError(f"Failed to cancel subscription: {str(e)}")
    
    async def reactivate_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """
        Reactivate a cancelled subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            
        Returns:
            Reactivated subscription dict
        """
        try:
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=False
            )
            return self._parse_subscription(subscription)
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription reactivation error: {e}")
            raise BillingError(f"Failed to reactivate subscription: {str(e)}")
    
    async def upgrade_plan(
        self,
        tenant: Tenant,
        new_plan: Plan,
        billing_cycle: str = "monthly"
    ) -> Dict[str, Any]:
        """
        Upgrade a tenant's plan with proration.
        
        Args:
            tenant: Tenant model instance
            new_plan: New plan to upgrade to
            billing_cycle: "monthly" or "yearly"
            
        Returns:
            Updated subscription dict
        """
        if not tenant.stripe_subscription_id:
            raise BillingError("No active subscription to upgrade")
        
        price_id = (
            new_plan.stripe_price_id_yearly if billing_cycle == "yearly"
            else new_plan.stripe_price_id_monthly
        )
        
        if not price_id:
            raise BillingError("New plan not configured for billing")
        
        return await self.update_subscription(
            tenant.stripe_subscription_id,
            new_price_id=price_id,
            proration_behavior="always_invoice"  # Charge immediately for upgrades
        )
    
    async def downgrade_plan(
        self,
        tenant: Tenant,
        new_plan: Plan,
        billing_cycle: str = "monthly"
    ) -> Dict[str, Any]:
        """
        Downgrade a tenant's plan at period end.
        
        Args:
            tenant: Tenant model instance
            new_plan: New plan to downgrade to
            billing_cycle: "monthly" or "yearly"
            
        Returns:
            Updated subscription dict
        """
        if not tenant.stripe_subscription_id:
            raise BillingError("No active subscription to downgrade")
        
        price_id = (
            new_plan.stripe_price_id_yearly if billing_cycle == "yearly"
            else new_plan.stripe_price_id_monthly
        )
        
        if not price_id:
            raise BillingError("New plan not configured for billing")
        
        # Downgrades apply at the end of the billing period
        return await self.update_subscription(
            tenant.stripe_subscription_id,
            new_price_id=price_id,
            proration_behavior="none"  # No proration for downgrades
        )
    
    # ========================================
    # Invoice Management
    # ========================================
    
    async def get_invoices(
        self,
        customer_id: str,
        limit: int = 10,
        starting_after: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get invoices for a customer.
        
        Args:
            customer_id: Stripe customer ID
            limit: Maximum number of invoices
            starting_after: Pagination cursor
            
        Returns:
            List of invoice dicts
        """
        try:
            params = {
                "customer": customer_id,
                "limit": limit
            }
            if starting_after:
                params["starting_after"] = starting_after
            
            invoices = stripe.Invoice.list(**params)
            
            return [self._parse_invoice(inv) for inv in invoices.data]
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe invoice list error: {e}")
            raise BillingError(f"Failed to get invoices: {str(e)}")
    
    async def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """
        Get invoice details.
        
        Args:
            invoice_id: Stripe invoice ID
            
        Returns:
            Invoice dict or None
        """
        try:
            invoice = stripe.Invoice.retrieve(invoice_id)
            return self._parse_invoice(invoice)
        except stripe.error.InvalidRequestError:
            return None
        except stripe.error.StripeError as e:
            logger.error(f"Stripe invoice retrieval error: {e}")
            raise BillingError(f"Failed to get invoice: {str(e)}")
    
    async def get_upcoming_invoice(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Get upcoming invoice for a customer.
        
        Args:
            customer_id: Stripe customer ID
            
        Returns:
            Upcoming invoice dict or None
        """
        try:
            invoice = stripe.Invoice.upcoming(customer=customer_id)
            return self._parse_invoice(invoice)
        except stripe.error.InvalidRequestError:
            return None
        except stripe.error.StripeError as e:
            logger.error(f"Stripe upcoming invoice error: {e}")
            raise BillingError(f"Failed to get upcoming invoice: {str(e)}")
    
    async def pay_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """
        Manually pay an invoice.
        
        Args:
            invoice_id: Stripe invoice ID
            
        Returns:
            Paid invoice dict
        """
        try:
            invoice = stripe.Invoice.pay(invoice_id)
            return self._parse_invoice(invoice)
        except stripe.error.StripeError as e:
            logger.error(f"Stripe invoice payment error: {e}")
            raise BillingError(f"Failed to pay invoice: {str(e)}")
    
    async def void_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """
        Void an invoice.
        
        Args:
            invoice_id: Stripe invoice ID
            
        Returns:
            Voided invoice dict
        """
        try:
            invoice = stripe.Invoice.void_invoice(invoice_id)
            return self._parse_invoice(invoice)
        except stripe.error.StripeError as e:
            logger.error(f"Stripe invoice void error: {e}")
            raise BillingError(f"Failed to void invoice: {str(e)}")
    
    # ========================================
    # Payment Method Management
    # ========================================
    
    async def get_payment_methods(self, customer_id: str) -> List[Dict[str, Any]]:
        """
        Get payment methods for a customer.
        
        Args:
            customer_id: Stripe customer ID
            
        Returns:
            List of payment method dicts
        """
        try:
            methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type="card"
            )
            
            return [
                {
                    "id": method.id,
                    "type": method.type,
                    "card": {
                        "brand": method.card.brand,
                        "last4": method.card.last4,
                        "exp_month": method.card.exp_month,
                        "exp_year": method.card.exp_year,
                    } if method.card else None,
                    "is_default": method.id == method.customer.invoice_settings.default_payment_method if hasattr(method, 'customer') else False,
                }
                for method in methods.data
            ]
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe payment method list error: {e}")
            raise BillingError(f"Failed to get payment methods: {str(e)}")
    
    async def attach_payment_method(
        self,
        customer_id: str,
        payment_method_id: str,
        set_default: bool = True
    ) -> Dict[str, Any]:
        """
        Attach a payment method to a customer.
        
        Args:
            customer_id: Stripe customer ID
            payment_method_id: Payment method ID
            set_default: Set as default payment method
            
        Returns:
            Payment method dict
        """
        try:
            method = stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id
            )
            
            if set_default:
                stripe.Customer.modify(
                    customer_id,
                    invoice_settings={
                        "default_payment_method": payment_method_id
                    }
                )
            
            return {
                "id": method.id,
                "type": method.type,
                "card": {
                    "brand": method.card.brand,
                    "last4": method.card.last4,
                } if method.card else None,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe payment method attach error: {e}")
            raise BillingError(f"Failed to attach payment method: {str(e)}")
    
    async def detach_payment_method(self, payment_method_id: str) -> bool:
        """
        Detach a payment method.
        
        Args:
            payment_method_id: Payment method ID
            
        Returns:
            True if successful
        """
        try:
            stripe.PaymentMethod.detach(payment_method_id)
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Stripe payment method detach error: {e}")
            raise BillingError(f"Failed to detach payment method: {str(e)}")
    
    async def set_default_payment_method(
        self,
        customer_id: str,
        payment_method_id: str
    ) -> bool:
        """
        Set the default payment method for a customer.
        
        Args:
            customer_id: Stripe customer ID
            payment_method_id: Payment method ID
            
        Returns:
            True if successful
        """
        try:
            stripe.Customer.modify(
                customer_id,
                invoice_settings={
                    "default_payment_method": payment_method_id
                }
            )
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Stripe set default payment method error: {e}")
            raise BillingError(f"Failed to set default payment method: {str(e)}")
    
    # ========================================
    # Checkout and Portal
    # ========================================
    
    async def create_checkout_session(
        self,
        tenant: Tenant,
        plan: Plan,
        success_url: str,
        cancel_url: str,
        billing_cycle: str = "monthly"
    ) -> Dict[str, Any]:
        """
        Create a Stripe Checkout session.
        
        Args:
            tenant: Tenant model instance
            plan: Plan model instance
            success_url: URL to redirect on success
            cancel_url: URL to redirect on cancel
            billing_cycle: "monthly" or "yearly"
            
        Returns:
            Checkout session details
        """
        try:
            # Create customer if needed
            if not tenant.stripe_customer_id:
                customer = await self.create_customer(tenant)
                tenant.stripe_customer_id = customer["customer_id"]
            
            price_id = (
                plan.stripe_price_id_yearly if billing_cycle == "yearly"
                else plan.stripe_price_id_monthly
            )
            
            session = stripe.checkout.Session.create(
                customer=tenant.stripe_customer_id,
                payment_method_types=["card"],
                line_items=[{
                    "price": price_id,
                    "quantity": 1,
                }],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "tenant_id": str(tenant.id),
                    "plan_id": str(plan.id),
                },
                subscription_data={
                    "trial_period_days": plan.trial_days if plan.trial_days > 0 else None,
                    "metadata": {
                        "tenant_id": str(tenant.id),
                        "plan_id": str(plan.id),
                    }
                }
            )
            
            return {
                "session_id": session.id,
                "url": session.url,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe checkout session error: {e}")
            raise BillingError(f"Failed to create checkout session: {str(e)}")
    
    async def create_billing_portal_session(
        self,
        customer_id: str,
        return_url: str
    ) -> Dict[str, Any]:
        """
        Create a billing portal session.
        
        Args:
            customer_id: Stripe customer ID
            return_url: URL to return after portal session
            
        Returns:
            Portal session details
        """
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            
            return {
                "url": session.url,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe billing portal error: {e}")
            raise BillingError(f"Failed to create billing portal session: {str(e)}")
    
    # ========================================
    # Trial Period Handling
    # ========================================
    
    async def start_trial(
        self,
        tenant: Tenant,
        plan: Plan,
        days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Start a trial period for a tenant.
        
        Args:
            tenant: Tenant model instance
            plan: Plan model instance
            days: Trial duration in days (uses plan default if not specified)
            
        Returns:
            Trial details
        """
        trial_days = days or plan.trial_days or 14
        
        # Update tenant status
        tenant.status = TenantStatus.TRIAL
        tenant.plan_type = plan.plan_type
        tenant.trial_start = datetime.utcnow()
        tenant.trial_end = datetime.utcnow() + timedelta(days=trial_days)
        
        # Apply plan limits
        tenant.apply_plan_limits()
        
        return {
            "trial_start": tenant.trial_start,
            "trial_end": tenant.trial_end,
            "trial_days": trial_days,
            "plan_type": plan.plan_type.value,
        }
    
    async def end_trial(
        self,
        tenant: Tenant,
        payment_method_id: str
    ) -> Dict[str, Any]:
        """
        End trial and convert to paid subscription.
        
        Args:
            tenant: Tenant model instance
            payment_method_id: Payment method to use
            
        Returns:
            Subscription details
        """
        # Get the plan
        from app.core.database import db_manager
        from sqlalchemy import text
        
        async with db_manager.get_session() as db:
            result = await db.execute(
                text("SELECT * FROM plans WHERE plan_type = :plan_type"),
                {"plan_type": tenant.plan_type.value}
            )
            plan_row = result.fetchone()
            
            if not plan_row:
                raise BillingError("Plan not found")
        
        # Create subscription without trial
        plan = Plan(
            id=plan_row.id,
            plan_type=tenant.plan_type,
            stripe_price_id_monthly=plan_row.stripe_price_id_monthly,
            stripe_price_id_yearly=plan_row.stripe_price_id_yearly,
            trial_days=0  # No trial, converting from trial
        )
        
        return await self.create_subscription(
            tenant=tenant,
            plan=plan,
            payment_method_id=payment_method_id,
            billing_cycle="monthly"
        )
    
    async def extend_trial(
        self,
        tenant: Tenant,
        additional_days: int
    ) -> Dict[str, Any]:
        """
        Extend a trial period.
        
        Args:
            tenant: Tenant model instance
            additional_days: Days to extend
            
        Returns:
            Updated trial details
        """
        if not tenant.trial_end:
            raise BillingError("No active trial to extend")
        
        tenant.trial_end = tenant.trial_end + timedelta(days=additional_days)
        
        return {
            "trial_end": tenant.trial_end,
            "additional_days": additional_days,
        }
    
    # ========================================
    # Webhook Handling
    # ========================================
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        sig_header: str
    ) -> Dict[str, Any]:
        """
        Verify and parse webhook signature.
        
        Args:
            payload: Raw request body
            sig_header: Stripe-Signature header
            
        Returns:
            Parsed event dict
        """
        try:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                self.webhook_secret
            )
            return event
        except ValueError as e:
            raise BillingError(f"Invalid payload: {str(e)}")
        except stripe.error.SignatureVerificationError as e:
            raise BillingError(f"Invalid signature: {str(e)}")
    
    async def handle_webhook_event(
        self,
        event: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Handle Stripe webhook event.
        
        Args:
            event: Stripe event dict
            db: Database session
            
        Returns:
            Processing result
        """
        event_type = event["type"]
        data = event["data"]["object"]
        
        handlers = {
            "customer.subscription.created": self._handle_subscription_created,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            "invoice.paid": self._handle_invoice_paid,
            "invoice.payment_failed": self._handle_invoice_payment_failed,
            "invoice.payment_succeeded": self._handle_invoice_payment_succeeded,
            "customer.created": self._handle_customer_created,
            "customer.updated": self._handle_customer_updated,
            "customer.deleted": self._handle_customer_deleted,
            "checkout.session.completed": self._handle_checkout_completed,
            "payment_method.attached": self._handle_payment_method_attached,
            "payment_method.detached": self._handle_payment_method_detached,
        }
        
        handler = handlers.get(event_type)
        if handler:
            try:
                result = await handler(data, db)
                logger.info(f"Processed webhook event: {event_type}")
                return result
            except Exception as e:
                logger.error(f"Error processing webhook {event_type}: {e}")
                raise
        else:
            logger.debug(f"Unhandled webhook event type: {event_type}")
            return {"status": "ignored", "event_type": event_type}
    
    # ========================================
    # Plan Management
    # ========================================
    
    async def get_plan_config(self, plan_type: PlanType) -> Dict[str, Any]:
        """
        Get plan configuration.
        
        Args:
            plan_type: Plan type enum
            
        Returns:
            Plan configuration dict
        """
        return PLAN_CONFIGS.get(plan_type, PLAN_CONFIGS[PlanType.BASIC])
    
    async def list_plans(self) -> List[Dict[str, Any]]:
        """
        List all available plans.
        
        Returns:
            List of plan configurations
        """
        plans = []
        for plan_type, config in PLAN_CONFIGS.items():
            plans.append({
                "type": plan_type.value,
                "name": config["name"],
                "description": config["description"],
                "monthly_price": config["monthly_price"],
                "yearly_price": config["yearly_price"],
                "trial_days": config["trial_days"],
                "features": config["features"],
                "limits": {
                    "max_users": config["max_users"],
                    "max_storage_mb": config["max_storage_mb"],
                    "max_products": config["max_products"],
                    "max_customers": config["max_customers"],
                    "api_calls_limit": config["api_calls_limit"],
                }
            })
        return plans
    
    async def calculate_upgrade_cost(
        self,
        tenant: Tenant,
        new_plan_type: PlanType,
        billing_cycle: str = "monthly"
    ) -> Dict[str, Any]:
        """
        Calculate the cost to upgrade to a new plan.
        
        Args:
            tenant: Tenant model instance
            new_plan_type: New plan type
            billing_cycle: "monthly" or "yearly"
            
        Returns:
            Cost calculation details
        """
        current_plan = PLAN_CONFIGS[tenant.plan_type]
        new_plan = PLAN_CONFIGS[new_plan_type]
        
        current_price = current_plan["monthly_price"] if billing_cycle == "monthly" else current_plan["yearly_price"]
        new_price = new_plan["monthly_price"] if billing_cycle == "monthly" else new_plan["yearly_price"]
        
        # Calculate prorated amount
        now = datetime.utcnow()
        
        if tenant.subscription_end:
            days_remaining = (tenant.subscription_end - now).days
            total_days = (tenant.subscription_end - tenant.subscription_start).days if tenant.subscription_start else 30
            
            unused_amount = (current_price * days_remaining / total_days) if total_days > 0 else 0
            prorated_new_amount = (new_price * days_remaining / total_days) if total_days > 0 else new_price
            
            upgrade_cost = max(0, prorated_new_amount - unused_amount)
        else:
            upgrade_cost = new_price - current_price
        
        return {
            "current_plan": tenant.plan_type.value,
            "new_plan": new_plan_type.value,
            "current_price": current_price,
            "new_price": new_price,
            "prorated_upgrade_cost": round(upgrade_cost, 2),
            "billing_cycle": billing_cycle,
        }
    
    # ========================================
    # Helper Methods
    # ========================================
    
    def _parse_subscription(self, subscription) -> Dict[str, Any]:
        """Parse Stripe subscription object."""
        return {
            "id": subscription.id,
            "status": subscription.status,
            "current_period_start": datetime.fromtimestamp(subscription.current_period_start),
            "current_period_end": datetime.fromtimestamp(subscription.current_period_end),
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "trial_start": datetime.fromtimestamp(subscription.trial_start) if subscription.trial_start else None,
            "trial_end": datetime.fromtimestamp(subscription.trial_end) if subscription.trial_end else None,
            "customer_id": subscription.customer,
            "plan_id": subscription.plan.id if subscription.plan else None,
            "quantity": subscription.quantity,
        }
    
    def _parse_invoice(self, invoice) -> Dict[str, Any]:
        """Parse Stripe invoice object."""
        return {
            "id": invoice.id,
            "number": invoice.number,
            "status": invoice.status,
            "total": invoice.total / 100,  # Convert cents to dollars
            "currency": invoice.currency.upper(),
            "created": datetime.fromtimestamp(invoice.created),
            "due_date": datetime.fromtimestamp(invoice.due_date) if invoice.due_date else None,
            "paid_at": datetime.fromtimestamp(invoice.status_transitions.paid_at) if invoice.status_transitions and invoice.status_transitions.paid_at else None,
            "invoice_pdf": invoice.invoice_pdf,
            "hosted_invoice_url": invoice.hosted_invoice_url,
        }
    
    # ========================================
    # Webhook Handlers
    # ========================================
    
    async def _handle_subscription_created(self, data: dict, db: AsyncSession) -> dict:
        """Handle subscription.created webhook."""
        tenant_id = data.get("metadata", {}).get("tenant_id")
        if tenant_id:
            result = await db.execute(
                select(Tenant).where(Tenant.id == UUID(tenant_id))
            )
            tenant = result.scalar_one_or_none()
            if tenant:
                tenant.stripe_subscription_id = data["id"]
                tenant.status = TenantStatus.ACTIVE
                tenant.subscription_start = datetime.fromtimestamp(data["current_period_start"])
                tenant.subscription_end = datetime.fromtimestamp(data["current_period_end"])
                
                if data.get("trial_end"):
                    tenant.trial_end = datetime.fromtimestamp(data["trial_end"])
                
                await db.commit()
        return {"status": "processed"}
    
    async def _handle_subscription_updated(self, data: dict, db: AsyncSession) -> dict:
        """Handle subscription.updated webhook."""
        subscription_id = data["id"]
        result = await db.execute(
            select(Tenant).where(Tenant.stripe_subscription_id == subscription_id)
        )
        tenant = result.scalar_one_or_none()
        
        if tenant:
            status_map = {
                "active": TenantStatus.ACTIVE,
                "past_due": TenantStatus.PAST_DUE,
                "canceled": TenantStatus.CANCELLED,
                "unpaid": TenantStatus.SUSPENDED,
                "trialing": TenantStatus.TRIAL,
            }
            tenant.status = status_map.get(data["status"], TenantStatus.ACTIVE)
            
            tenant.subscription_start = datetime.fromtimestamp(data["current_period_start"])
            tenant.subscription_end = datetime.fromtimestamp(data["current_period_end"])
            
            if data["cancel_at_period_end"]:
                tenant.status = TenantStatus.CANCELLED
                tenant.cancelled_at = datetime.utcnow()
            
            await db.commit()
        
        return {"status": "processed"}
    
    async def _handle_subscription_deleted(self, data: dict, db: AsyncSession) -> dict:
        """Handle subscription.deleted webhook."""
        subscription_id = data["id"]
        result = await db.execute(
            select(Tenant).where(Tenant.stripe_subscription_id == subscription_id)
        )
        tenant = result.scalar_one_or_none()
        
        if tenant:
            tenant.status = TenantStatus.CANCELLED
            tenant.stripe_subscription_id = None
            tenant.cancelled_at = datetime.utcnow()
            await db.commit()
        
        return {"status": "processed"}
    
    async def _handle_invoice_paid(self, data: dict, db: AsyncSession) -> dict:
        """Handle invoice.paid webhook."""
        return await self._process_invoice(data, db, "paid")
    
    async def _handle_invoice_payment_succeeded(self, data: dict, db: AsyncSession) -> dict:
        """Handle invoice.payment_succeeded webhook."""
        return await self._process_invoice(data, db, "paid")
    
    async def _handle_invoice_payment_failed(self, data: dict, db: AsyncSession) -> dict:
        """Handle invoice.payment_failed webhook."""
        customer_id = data["customer"]
        result = await db.execute(
            select(Tenant).where(Tenant.stripe_customer_id == customer_id)
        )
        tenant = result.scalar_one_or_none()
        
        if tenant:
            tenant.status = TenantStatus.PAST_DUE
            
            # Log payment failure
            invoice = BillingInvoice(
                tenant_id=tenant.id,
                stripe_invoice_id=data["id"],
                invoice_number=data.get("number", ""),
                status="failed",
                subtotal=Decimal(str(data["subtotal"])) / 100,
                total=Decimal(str(data["total"])) / 100,
                currency=data["currency"].upper(),
                invoice_date=datetime.fromtimestamp(data["created"]),
            )
            db.add(invoice)
            await db.commit()
        
        return {"status": "processed"}
    
    async def _process_invoice(self, data: dict, db: AsyncSession, status: str) -> dict:
        """Process invoice and create record."""
        customer_id = data["customer"]
        result = await db.execute(
            select(Tenant).where(Tenant.stripe_customer_id == customer_id)
        )
        tenant = result.scalar_one_or_none()
        
        if tenant:
            # Create invoice record
            invoice = BillingInvoice(
                tenant_id=tenant.id,
                stripe_invoice_id=data["id"],
                invoice_number=data["number"],
                status=status,
                subtotal=Decimal(str(data["subtotal"])) / 100,
                tax=Decimal(str(data.get("tax", 0))) / 100,
                total=Decimal(str(data["total"])) / 100,
                currency=data["currency"].upper(),
                invoice_date=datetime.fromtimestamp(data["created"]),
                paid_at=datetime.utcnow() if status == "paid" else None,
                line_items=data.get("lines", {}).get("data", []),
            )
            db.add(invoice)
            
            # Update tenant status if needed
            if tenant.status == TenantStatus.PAST_DUE:
                tenant.status = TenantStatus.ACTIVE
            
            await db.commit()
        
        return {"status": "processed"}
    
    async def _handle_customer_created(self, data: dict, db: AsyncSession) -> dict:
        """Handle customer.created webhook."""
        tenant_id = data.get("metadata", {}).get("tenant_id")
        if tenant_id:
            result = await db.execute(
                select(Tenant).where(Tenant.id == UUID(tenant_id))
            )
            tenant = result.scalar_one_or_none()
            if tenant and not tenant.stripe_customer_id:
                tenant.stripe_customer_id = data["id"]
                await db.commit()
        return {"status": "processed"}
    
    async def _handle_customer_updated(self, data: dict, db: AsyncSession) -> dict:
        """Handle customer.updated webhook."""
        return {"status": "processed"}
    
    async def _handle_customer_deleted(self, data: dict, db: AsyncSession) -> dict:
        """Handle customer.deleted webhook."""
        customer_id = data["id"]
        result = await db.execute(
            select(Tenant).where(Tenant.stripe_customer_id == customer_id)
        )
        tenant = result.scalar_one_or_none()
        
        if tenant:
            tenant.stripe_customer_id = None
            tenant.stripe_subscription_id = None
            tenant.status = TenantStatus.CANCELLED
            await db.commit()
        
        return {"status": "processed"}
    
    async def _handle_checkout_completed(self, data: dict, db: AsyncSession) -> dict:
        """Handle checkout.session.completed webhook."""
        tenant_id = data.get("metadata", {}).get("tenant_id")
        subscription_id = data.get("subscription")
        
        if tenant_id and subscription_id:
            result = await db.execute(
                select(Tenant).where(Tenant.id == UUID(tenant_id))
            )
            tenant = result.scalar_one_or_none()
            if tenant:
                tenant.stripe_subscription_id = subscription_id
                tenant.status = TenantStatus.ACTIVE
                await db.commit()
        
        return {"status": "processed"}
    
    async def _handle_payment_method_attached(self, data: dict, db: AsyncSession) -> dict:
        """Handle payment_method.attached webhook."""
        customer_id = data.get("customer")
        if customer_id:
            result = await db.execute(
                select(Tenant).where(Tenant.stripe_customer_id == customer_id)
            )
            tenant = result.scalar_one_or_none()
            if tenant:
                # Payment method attached, no action needed
                pass
        return {"status": "processed"}
    
    async def _handle_payment_method_detached(self, data: dict, db: AsyncSession) -> dict:
        """Handle payment_method.detached webhook."""
        return {"status": "processed"}


class BillingError(Exception):
    """Custom exception for billing errors."""
    pass


# ========================================
# Usage Tracking
# ========================================

class UsageTracker:
    """
    Track usage for metered billing.
    
    Records usage metrics for each tenant that can be
    reported to Stripe for metered billing.
    """
    
    @staticmethod
    async def record_usage(
        db: AsyncSession,
        tenant_id: UUID,
        metric: str,
        quantity: int = 1
    ):
        """
        Record usage for a tenant.
        
        Args:
            db: Database session
            tenant_id: Tenant UUID
            metric: Metric name (e.g., "api_calls", "storage_mb")
            quantity: Quantity to add
        """
        from sqlalchemy import text
        
        await db.execute(
            text("""
                INSERT INTO tenant_usage (tenant_id, metric, quantity, recorded_at)
                VALUES (:tenant_id, :metric, :quantity, NOW())
            """),
            {
                "tenant_id": str(tenant_id),
                "metric": metric,
                "quantity": quantity
            }
        )
        await db.commit()
    
    @staticmethod
    async def get_usage(
        db: AsyncSession,
        tenant_id: UUID,
        metric: str,
        period_start: datetime,
        period_end: datetime
    ) -> int:
        """
        Get total usage for a period.
        
        Args:
            db: Database session
            tenant_id: Tenant UUID
            metric: Metric name
            period_start: Period start date
            period_end: Period end date
            
        Returns:
            Total usage quantity
        """
        from sqlalchemy import text
        
        result = await db.execute(
            text("""
                SELECT COALESCE(SUM(quantity), 0) as total
                FROM tenant_usage
                WHERE tenant_id = :tenant_id
                AND metric = :metric
                AND recorded_at >= :period_start
                AND recorded_at < :period_end
            """),
            {
                "tenant_id": str(tenant_id),
                "metric": metric,
                "period_start": period_start,
                "period_end": period_end
            }
        )
        row = result.fetchone()
        return row.total if row else 0
    
    @staticmethod
    async def increment_api_calls(db: AsyncSession, tenant_id: UUID):
        """Increment API call count for tenant."""
        # Update tenant's API calls counter
        await db.execute(
            text("""
                UPDATE tenants 
                SET api_calls_used = api_calls_used + 1 
                WHERE id = :tenant_id
            """),
            {"tenant_id": str(tenant_id)}
        )
        await db.commit()
    
    @staticmethod
    async def check_api_limit(db: AsyncSession, tenant_id: UUID) -> bool:
        """Check if tenant has exceeded API limit."""
        result = await db.execute(
            text("""
                SELECT api_calls_used, api_calls_limit 
                FROM tenants 
                WHERE id = :tenant_id
            """),
            {"tenant_id": str(tenant_id)}
        )
        row = result.fetchone()
        
        if row:
            # -1 means unlimited
            if row.api_calls_limit == -1:
                return True
            return row.api_calls_used < row.api_calls_limit
        
        return False


# Global billing service instance
billing_service = BillingService()
