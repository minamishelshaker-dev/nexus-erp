"""
Nexus ERP - Sales Service
==========================

Business logic for the Sales module including:
- Quotation management
- Sale order processing
- Invoice generation
- Payment registration
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
import logging

from app.models.sales import (
    Quotation, QuotationLine, QuotationState,
    SaleOrder, SaleOrderLine, SaleOrderState,
    Invoice, InvoiceLine, InvoiceType, InvoiceState,
    Payment, PaymentInvoice, PaymentType, PaymentState
)
from app.models.accounting import Partner, Account, Journal
from app.models.inventory import Product, StockMove, StockMoveType, StockMoveState
from app.services.integration_service import IntegrationService
from app.services.inventory_service import InventoryService

logger = logging.getLogger(__name__)


class SalesService:
    """
    Sales Service
    
    Handles all sales-related business logic.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.integration_svc = IntegrationService(db)
        self.inventory_svc = InventoryService(db)
    
    # ========================================
    # Quotation Management
    # ========================================
    
    async def create_quotation(
        self,
        tenant_id: UUID,
        data: Dict[str, Any],
        user_id: Optional[UUID] = None
    ) -> Quotation:
        """
        Create a new quotation.
        
        Args:
            tenant_id: Tenant ID
            data: Quotation data including lines
            user_id: Creating user ID
            
        Returns:
            Created quotation
        """
        # Generate quotation number
        number = await self._generate_quotation_number(tenant_id)
        
        # Create quotation
        quotation = Quotation(
            tenant_id=tenant_id,
            number=number,
            name=data.get("name", f"Quotation {number}"),
            partner_id=data["partner_id"],
            partner_shipping_id=data.get("partner_shipping_id"),
            partner_invoice_id=data.get("partner_invoice_id"),
            date=data.get("date", date.today()),
            valid_until=data.get("valid_until"),
            state=QuotationState.DRAFT,
            warehouse_id=data.get("warehouse_id"),
            salesperson_id=data.get("salesperson_id"),
            team_id=data.get("team_id"),
            payment_term_id=data.get("payment_term_id"),
            currency_id=data.get("currency_id"),
            exchange_rate=data.get("exchange_rate", Decimal("1")),
            notes=data.get("notes"),
            terms_conditions=data.get("terms_conditions"),
            created_by_id=user_id
        )
        
        self.db.add(quotation)
        await self.db.flush()
        
        # Create lines
        for line_data in data.get("lines", []):
            line = QuotationLine(
                tenant_id=tenant_id,
                quotation_id=quotation.id,
                product_id=line_data.get("product_id"),
                description=line_data["description"],
                quantity=Decimal(str(line_data["quantity"])),
                uom_id=line_data.get("uom_id"),
                price_unit=Decimal(str(line_data["price_unit"])),
                discount=Decimal(str(line_data.get("discount", 0))),
                tax_ids=line_data.get("tax_ids", []),
                date_planned=line_data.get("date_planned"),
                notes=line_data.get("notes")
            )
            line.calculate_subtotal()
            self.db.add(line)
        
        await self.db.flush()
        
        # Calculate totals
        quotation.calculate_totals()
        
        await self.db.commit()
        await self.db.refresh(quotation)
        
        return quotation
    
    async def send_quotation(
        self,
        quotation_id: UUID,
        tenant_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Quotation:
        """Mark quotation as sent."""
        quotation = await self._get_quotation(quotation_id, tenant_id)
        
        if quotation.state != QuotationState.DRAFT:
            raise ValueError("Only draft quotations can be sent")
        
        quotation.state = QuotationState.SENT
        quotation.sent_at = datetime.utcnow()
        
        await self.db.commit()
        return quotation
    
    async def confirm_quotation(
        self,
        quotation_id: UUID,
        tenant_id: UUID,
        create_order: bool = True,
        user_id: Optional[UUID] = None
    ) -> SaleOrder:
        """
        Confirm quotation and optionally create sale order.
        
        Args:
            quotation_id: Quotation ID
            tenant_id: Tenant ID
            create_order: Whether to create a sale order
            user_id: Confirming user ID
            
        Returns:
            Created sale order if create_order=True
        """
        quotation = await self._get_quotation(quotation_id, tenant_id)
        
        if quotation.state not in (QuotationState.DRAFT, QuotationState.SENT):
            raise ValueError("Quotation cannot be confirmed in current state")
        
        quotation.state = QuotationState.ACCEPTED
        quotation.accepted_at = datetime.utcnow()
        
        if create_order:
            # Create sale order from quotation
            order = await self._create_order_from_quotation(quotation, user_id)
            await self.db.commit()
            return order
        
        await self.db.commit()
        return None
    
    async def cancel_quotation(
        self,
        quotation_id: UUID,
        tenant_id: UUID,
        reason: Optional[str] = None,
        user_id: Optional[UUID] = None
    ) -> Quotation:
        """Cancel a quotation."""
        quotation = await self._get_quotation(quotation_id, tenant_id)
        
        if quotation.state == QuotationState.ACCEPTED:
            raise ValueError("Cannot cancel accepted quotation")
        
        quotation.state = QuotationState.CANCELLED
        quotation.internal_notes = (quotation.internal_notes or "") + f"\nCancelled: {reason or 'No reason provided'}"
        
        await self.db.commit()
        return quotation
    
    # ========================================
    # Sale Order Management
    # ========================================
    
    async def create_sale_order(
        self,
        tenant_id: UUID,
        data: Dict[str, Any],
        user_id: Optional[UUID] = None
    ) -> SaleOrder:
        """
        Create a new sale order.
        
        Args:
            tenant_id: Tenant ID
            data: Order data including lines
            user_id: Creating user ID
            
        Returns:
            Created sale order
        """
        # Generate order number
        number = await self._generate_sale_order_number(tenant_id)
        
        # Create order
        order = SaleOrder(
            tenant_id=tenant_id,
            number=number,
            name=data.get("name", f"SO {number}"),
            quotation_id=data.get("quotation_id"),
            partner_id=data["partner_id"],
            partner_shipping_id=data.get("partner_shipping_id"),
            partner_invoice_id=data.get("partner_invoice_id"),
            date_order=data.get("date_order", date.today()),
            date_planned=data.get("date_planned"),
            state=SaleOrderState.DRAFT,
            warehouse_id=data.get("warehouse_id"),
            salesperson_id=data.get("salesperson_id"),
            team_id=data.get("team_id"),
            payment_term_id=data.get("payment_term_id"),
            currency_id=data.get("currency_id"),
            exchange_rate=data.get("exchange_rate", Decimal("1")),
            origin=data.get("origin"),
            notes=data.get("notes"),
            terms_conditions=data.get("terms_conditions"),
            created_by_id=user_id
        )
        
        self.db.add(order)
        await self.db.flush()
        
        # Create lines
        for line_data in data.get("lines", []):
            product = None
            if line_data.get("product_id"):
                product = await self.db.get(Product, line_data["product_id"])
            
            line = SaleOrderLine(
                tenant_id=tenant_id,
                order_id=order.id,
                product_id=line_data.get("product_id"),
                description=line_data["description"],
                quantity=Decimal(str(line_data["quantity"])),
                uom_id=line_data.get("uom_id"),
                price_unit=Decimal(str(line_data["price_unit"])),
                cost_price=product.cost_price if product else Decimal("0"),
                discount=Decimal(str(line_data.get("discount", 0))),
                tax_ids=line_data.get("tax_ids", []),
                date_planned=line_data.get("date_planned"),
                analytic_account_id=line_data.get("analytic_account_id"),
                notes=line_data.get("notes")
            )
            line.calculate_subtotal()
            self.db.add(line)
        
        await self.db.flush()
        
        # Calculate totals
        order.calculate_totals()
        
        await self.db.commit()
        await self.db.refresh(order)
        
        return order
    
    async def confirm_sale_order(
        self,
        order_id: UUID,
        tenant_id: UUID,
        create_delivery: bool = True,
        create_invoice: bool = False,
        user_id: Optional[UUID] = None
    ) -> SaleOrder:
        """
        Confirm a sale order.
        
        This will:
        1. Update order state to CONFIRMED
        2. Create stock moves for delivery (if create_delivery)
        3. Create invoice (if create_invoice)
        
        Args:
            order_id: Order ID
            tenant_id: Tenant ID
            create_delivery: Create stock moves
            create_invoice: Create invoice
            user_id: Confirming user ID
            
        Returns:
            Confirmed order
        """
        order = await self._get_sale_order(order_id, tenant_id)
        
        if order.state != SaleOrderState.DRAFT:
            raise ValueError("Only draft orders can be confirmed")
        
        order.state = SaleOrderState.CONFIRMED
        order.date_confirm = date.today()
        order.confirmed_at = datetime.utcnow()
        order.confirmed_by_id = user_id
        
        # Create stock moves for delivery
        if create_delivery:
            await self._create_stock_moves_for_order(order, tenant_id, user_id)
        
        # Create invoice if requested
        if create_invoice:
            await self._create_invoice_from_order(order, tenant_id, user_id)
        
        await self.db.commit()
        return order
    
    async def cancel_sale_order(
        self,
        order_id: UUID,
        tenant_id: UUID,
        reason: Optional[str] = None,
        user_id: Optional[UUID] = None
    ) -> SaleOrder:
        """Cancel a sale order."""
        order = await self._get_sale_order(order_id, tenant_id)
        
        if order.state == SaleOrderState.DONE:
            raise ValueError("Cannot cancel completed orders")
        
        if order.amount_invoiced > 0:
            raise ValueError("Cannot cancel order with invoices")
        
        # Cancel any related stock moves
        for move in order.stock_moves:
            if move.state == StockMoveState.DRAFT:
                move.state = StockMoveState.CANCELLED
        
        order.state = SaleOrderState.CANCELLED
        order.notes = (order.notes or "") + f"\nCancelled: {reason or 'No reason provided'}"
        
        await self.db.commit()
        return order
    
    async def deliver_order(
        self,
        order_id: UUID,
        tenant_id: UUID,
        user_id: Optional[UUID] = None
    ) -> SaleOrder:
        """Mark order as fully delivered."""
        order = await self._get_sale_order(order_id, tenant_id)
        
        order.delivery_status = "done"
        
        # Check if all done
        if order.delivery_status == "done" and order.invoice_status == "invoiced":
            order.state = SaleOrderState.DONE
            order.done_at = datetime.utcnow()
        
        await self.db.commit()
        return order
    
    # ========================================
    # Invoice Management
    # ========================================
    
    async def create_invoice(
        self,
        tenant_id: UUID,
        data: Dict[str, Any],
        user_id: Optional[UUID] = None
    ) -> Invoice:
        """Create a new invoice."""
        # Generate invoice number
        number = await self._generate_invoice_number(tenant_id)
        
        invoice = Invoice(
            tenant_id=tenant_id,
            number=number,
            name=data.get("name", f"Invoice {number}"),
            invoice_type=InvoiceType(data.get("invoice_type", "out_invoice")),
            sale_order_id=data.get("sale_order_id"),
            purchase_order_id=data.get("purchase_order_id"),
            origin=data.get("origin"),
            partner_id=data["partner_id"],
            partner_shipping_id=data.get("partner_shipping_id"),
            date_invoice=data.get("date_invoice", date.today()),
            date_due=data.get("date_due"),
            state=InvoiceState.DRAFT,
            payment_term_id=data.get("payment_term_id"),
            currency_id=data.get("currency_id"),
            exchange_rate=data.get("exchange_rate", Decimal("1")),
            journal_id=data.get("journal_id"),
            account_id=data.get("account_id"),
            notes=data.get("notes"),
            terms_conditions=data.get("terms_conditions"),
            created_by_id=user_id
        )
        
        self.db.add(invoice)
        await self.db.flush()
        
        # Create lines
        for line_data in data.get("lines", []):
            line = InvoiceLine(
                tenant_id=tenant_id,
                invoice_id=invoice.id,
                product_id=line_data.get("product_id"),
                description=line_data["description"],
                quantity=Decimal(str(line_data["quantity"])),
                uom_id=line_data.get("uom_id"),
                price_unit=Decimal(str(line_data["price_unit"])),
                discount=Decimal(str(line_data.get("discount", 0))),
                tax_ids=line_data.get("tax_ids", []),
                account_id=line_data["account_id"],
                analytic_account_id=line_data.get("analytic_account_id"),
                notes=line_data.get("notes")
            )
            line.calculate_subtotal()
            self.db.add(line)
        
        await self.db.flush()
        invoice.calculate_totals()
        
        await self.db.commit()
        await self.db.refresh(invoice)
        
        return invoice
    
    async def create_invoice_from_order(
        self,
        order_id: UUID,
        tenant_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Invoice:
        """Create invoice from a sale order."""
        order = await self._get_sale_order(order_id, tenant_id)
        
        if order.state == SaleOrderState.DRAFT:
            raise ValueError("Cannot invoice draft orders")
        
        return await self._create_invoice_from_order(order, tenant_id, user_id)
    
    async def post_invoice(
        self,
        invoice_id: UUID,
        tenant_id: UUID,
        date_posted: Optional[date] = None,
        user_id: Optional[UUID] = None
    ) -> Invoice:
        """
        Post an invoice.
        
        This creates the accounting entries.
        """
        invoice = await self._get_invoice(invoice_id, tenant_id)
        
        if invoice.state != InvoiceState.DRAFT:
            raise ValueError("Only draft invoices can be posted")
        
        invoice.state = InvoiceState.POSTED
        invoice.date_posted = date_posted or date.today()
        invoice.posted_at = datetime.utcnow()
        invoice.posted_by_id = user_id
        
        # Create accounting entries via integration service
        await self.integration_svc.process_sale_accounting(
            invoice.id, tenant_id, user_id
        )
        
        await self.db.commit()
        return invoice
    
    async def register_payment(
        self,
        invoice_id: UUID,
        tenant_id: UUID,
        amount: Decimal,
        date: date,
        journal_id: UUID,
        payment_method_id: Optional[UUID] = None,
        reference: Optional[str] = None,
        user_id: Optional[UUID] = None
    ) -> Payment:
        """Register a payment for an invoice."""
        invoice = await self._get_invoice(invoice_id, tenant_id)
        
        if invoice.state not in (InvoiceState.POSTED, InvoiceState.PARTIAL):
            raise ValueError("Cannot register payment on this invoice")
        
        # Generate payment number
        number = await self._generate_payment_number(tenant_id)
        
        payment = Payment(
            tenant_id=tenant_id,
            number=number,
            name=f"Payment {number}",
            payment_type=PaymentType.RECEIPT if invoice.is_customer_invoice else PaymentType.PAYMENT,
            partner_id=invoice.partner_id,
            date=date,
            amount=amount,
            journal_id=journal_id,
            payment_method_id=payment_method_id,
            reference=reference,
            state=PaymentState.POSTED,
            posted_at=datetime.utcnow(),
            posted_by_id=user_id,
            created_by_id=user_id
        )
        
        self.db.add(payment)
        await self.db.flush()
        
        # Link payment to invoice
        payment_invoice = PaymentInvoice(
            tenant_id=tenant_id,
            payment_id=payment.id,
            invoice_id=invoice.id,
            amount=amount
        )
        self.db.add(payment_invoice)
        
        # Update invoice
        invoice.amount_paid += amount
        invoice.amount_residual = invoice.amount_total - invoice.amount_paid
        
        if invoice.amount_residual <= 0:
            invoice.state = InvoiceState.PAID
        elif invoice.amount_paid > 0:
            invoice.state = InvoiceState.PARTIAL
        
        # Create accounting entry for payment
        # TODO: Implement payment accounting
        
        await self.db.commit()
        await self.db.refresh(payment)
        
        return payment
    
    # ========================================
    # List/Query Methods
    # ========================================
    
    async def list_quotations(
        self,
        tenant_id: UUID,
        state: Optional[QuotationState] = None,
        partner_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[Quotation], int]:
        """List quotations with filters."""
        query = select(Quotation).where(
            Quotation.tenant_id == tenant_id,
            Quotation.is_deleted == False
        )
        
        if state:
            query = query.where(Quotation.state == state)
        if partner_id:
            query = query.where(Quotation.partner_id == partner_id)
        if date_from:
            query = query.where(Quotation.date >= date_from)
        if date_to:
            query = query.where(Quotation.date <= date_to)
        
        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)
        
        # Paginate
        query = query.order_by(Quotation.date.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        quotations = result.scalars().all()
        
        return list(quotations), total or 0
    
    async def list_sale_orders(
        self,
        tenant_id: UUID,
        state: Optional[SaleOrderState] = None,
        partner_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[SaleOrder], int]:
        """List sale orders with filters."""
        query = select(SaleOrder).where(
            SaleOrder.tenant_id == tenant_id,
            SaleOrder.is_deleted == False
        )
        
        if state:
            query = query.where(SaleOrder.state == state)
        if partner_id:
            query = query.where(SaleOrder.partner_id == partner_id)
        if date_from:
            query = query.where(SaleOrder.date_order >= date_from)
        if date_to:
            query = query.where(SaleOrder.date_order <= date_to)
        
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)
        
        query = query.order_by(SaleOrder.date_order.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        orders = result.scalars().all()
        
        return list(orders), total or 0
    
    async def list_invoices(
        self,
        tenant_id: UUID,
        invoice_type: Optional[InvoiceType] = None,
        state: Optional[InvoiceState] = None,
        partner_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[Invoice], int]:
        """List invoices with filters."""
        query = select(Invoice).where(
            Invoice.tenant_id == tenant_id,
            Invoice.is_deleted == False
        )
        
        if invoice_type:
            query = query.where(Invoice.invoice_type == invoice_type)
        if state:
            query = query.where(Invoice.state == state)
        if partner_id:
            query = query.where(Invoice.partner_id == partner_id)
        if date_from:
            query = query.where(Invoice.date_invoice >= date_from)
        if date_to:
            query = query.where(Invoice.date_invoice <= date_to)
        
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)
        
        query = query.order_by(Invoice.date_invoice.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        invoices = result.scalars().all()
        
        return list(invoices), total or 0
    
    # ========================================
    # Private Helper Methods
    # ========================================
    
    async def _get_quotation(self, quotation_id: UUID, tenant_id: UUID) -> Quotation:
        """Get quotation by ID."""
        result = await self.db.execute(
            select(Quotation)
            .options(selectinload(Quotation.lines))
            .where(
                Quotation.id == quotation_id,
                Quotation.tenant_id == tenant_id
            )
        )
        quotation = result.scalar_one_or_none()
        if not quotation:
            raise ValueError(f"Quotation {quotation_id} not found")
        return quotation
    
    async def _get_sale_order(self, order_id: UUID, tenant_id: UUID) -> SaleOrder:
        """Get sale order by ID."""
        result = await self.db.execute(
            select(SaleOrder)
            .options(selectinload(SaleOrder.lines))
            .where(
                SaleOrder.id == order_id,
                SaleOrder.tenant_id == tenant_id
            )
        )
        order = result.scalar_one_or_none()
        if not order:
            raise ValueError(f"Sale order {order_id} not found")
        return order
    
    async def _get_invoice(self, invoice_id: UUID, tenant_id: UUID) -> Invoice:
        """Get invoice by ID."""
        result = await self.db.execute(
            select(Invoice)
            .options(selectinload(Invoice.lines))
            .where(
                Invoice.id == invoice_id,
                Invoice.tenant_id == tenant_id
            )
        )
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        return invoice
    
    async def _create_order_from_quotation(
        self,
        quotation: Quotation,
        user_id: Optional[UUID] = None
    ) -> SaleOrder:
        """Create sale order from quotation."""
        number = await self._generate_sale_order_number(quotation.tenant_id)
        
        order = SaleOrder(
            tenant_id=quotation.tenant_id,
            number=number,
            name=f"SO from {quotation.number}",
            quotation_id=quotation.id,
            partner_id=quotation.partner_id,
            partner_shipping_id=quotation.partner_shipping_id,
            partner_invoice_id=quotation.partner_invoice_id,
            date_order=date.today(),
            state=SaleOrderState.DRAFT,
            warehouse_id=quotation.warehouse_id,
            salesperson_id=quotation.salesperson_id,
            team_id=quotation.team_id,
            payment_term_id=quotation.payment_term_id,
            currency_id=quotation.currency_id,
            exchange_rate=quotation.exchange_rate,
            origin=quotation.number,
            notes=quotation.notes,
            terms_conditions=quotation.terms_conditions,
            created_by_id=user_id
        )
        
        self.db.add(order)
        await self.db.flush()
        
        # Copy lines
        for qline in quotation.lines:
            line = SaleOrderLine(
                tenant_id=quotation.tenant_id,
                order_id=order.id,
                product_id=qline.product_id,
                description=qline.description,
                quantity=qline.quantity,
                uom_id=qline.uom_id,
                price_unit=qline.price_unit,
                discount=qline.discount,
                tax_ids=qline.tax_ids,
                date_planned=qline.date_planned,
                notes=qline.notes
            )
            line.calculate_subtotal()
            self.db.add(line)
        
        await self.db.flush()
        order.calculate_totals()
        
        return order
    
    async def _create_stock_moves_for_order(
        self,
        order: SaleOrder,
        tenant_id: UUID,
        user_id: Optional[UUID] = None
    ):
        """Create stock moves for sale order delivery."""
        for line in order.lines:
            if not line.product_id:
                continue
            
            product = await self.db.get(Product, line.product_id)
            if not product or not product.is_stockable:
                continue
            
            move_number = await self._generate_stock_move_number(tenant_id)
            
            move = StockMove(
                tenant_id=tenant_id,
                number=move_number,
                reference=order.number,
                reference_id=order.id,
                reference_type="sale_order",
                product_id=line.product_id,
                quantity=line.quantity,
                uom_id=line.uom_id or product.uom_id,
                move_type=StockMoveType.OUT,
                state=StockMoveState.CONFIRMED,
                date=date.today(),
                partner_id=order.partner_id,
                partner_type="customer",
                unit_cost=product.average_cost or product.cost_price,
                total_cost=(product.average_cost or product.cost_price) * line.quantity,
                notes=f"Sale Order: {order.number}"
            )
            
            self.db.add(move)
    
    async def _create_invoice_from_order(
        self,
        order: SaleOrder,
        tenant_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Invoice:
        """Create invoice from sale order."""
        number = await self._generate_invoice_number(tenant_id)
        
        # Get receivable account
        partner = await self.db.get(Partner, order.partner_id)
        account_id = partner.receivable_account_id if partner else None
        
        invoice = Invoice(
            tenant_id=tenant_id,
            number=number,
            name=f"Invoice for {order.number}",
            invoice_type=InvoiceType.OUT_INVOICE,
            sale_order_id=order.id,
            origin=order.number,
            partner_id=order.partner_id,
            partner_shipping_id=order.partner_shipping_id,
            date_invoice=date.today(),
            state=InvoiceState.DRAFT,
            payment_term_id=order.payment_term_id,
            currency_id=order.currency_id,
            exchange_rate=order.exchange_rate,
            account_id=account_id,
            notes=order.notes,
            created_by_id=user_id
        )
        
        self.db.add(invoice)
        await self.db.flush()
        
        # Create invoice lines
        for line in order.lines:
            product = None
            if line.product_id:
                product = await self.db.get(Product, line.product_id)
            
            # Get income account for product
            income_account_id = None
            if product:
                income_account_id = product.income_account_id
            
            if not income_account_id:
                # Get default income account
                income_account_id = await self._get_default_account("income", tenant_id)
            
            invoice_line = InvoiceLine(
                tenant_id=tenant_id,
                invoice_id=invoice.id,
                product_id=line.product_id,
                description=line.description,
                quantity=line.quantity,
                uom_id=line.uom_id,
                price_unit=line.price_unit,
                discount=line.discount,
                tax_ids=line.tax_ids,
                account_id=income_account_id,
                analytic_account_id=line.analytic_account_id
            )
            invoice_line.calculate_subtotal()
            self.db.add(invoice_line)
            
            # Update order line invoiced quantity
            line.quantity_invoiced += line.quantity
        
        await self.db.flush()
        invoice.calculate_totals()
        
        # Update order
        order.amount_invoiced += invoice.amount_total
        order.amount_residual = order.amount_total - order.amount_invoiced
        order.invoice_status = "invoiced" if order.amount_invoiced >= order.amount_total else "partial"
        
        return invoice
    
    async def _get_default_account(self, account_type: str, tenant_id: UUID) -> UUID:
        """Get default account by type."""
        # This should be replaced with proper default account logic
        # For now, return a placeholder
        return UUID("00000000-0000-0000-0000-000000000000")
    
    async def _generate_quotation_number(self, tenant_id: UUID) -> str:
        """Generate unique quotation number."""
        prefix = "QT"
        today = date.today()
        year_month = today.strftime("%Y%m")
        
        # Get count for this month
        count = await self.db.scalar(
            select(func.count()).select_from(Quotation).where(
                Quotation.tenant_id == tenant_id,
                Quotation.number.like(f"{prefix}{year_month}%")
            )
        )
        
        return f"{prefix}{year_month}{(count + 1):04d}"
    
    async def _generate_sale_order_number(self, tenant_id: UUID) -> str:
        """Generate unique sale order number."""
        prefix = "SO"
        today = date.today()
        year_month = today.strftime("%Y%m")
        
        count = await self.db.scalar(
            select(func.count()).select_from(SaleOrder).where(
                SaleOrder.tenant_id == tenant_id,
                SaleOrder.number.like(f"{prefix}{year_month}%")
            )
        )
        
        return f"{prefix}{year_month}{(count + 1):04d}"
    
    async def _generate_invoice_number(self, tenant_id: UUID) -> str:
        """Generate unique invoice number."""
        prefix = "INV"
        today = date.today()
        year_month = today.strftime("%Y%m")
        
        count = await self.db.scalar(
            select(func.count()).select_from(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.number.like(f"{prefix}{year_month}%")
            )
        )
        
        return f"{prefix}{year_month}{(count + 1):04d}"
    
    async def _generate_payment_number(self, tenant_id: UUID) -> str:
        """Generate unique payment number."""
        prefix = "PAY"
        today = date.today()
        year_month = today.strftime("%Y%m")
        
        count = await self.db.scalar(
            select(func.count()).select_from(Payment).where(
                Payment.tenant_id == tenant_id,
                Payment.number.like(f"{prefix}{year_month}%")
            )
        )
        
        return f"{prefix}{year_month}{(count + 1):04d}"
    
    async def _generate_stock_move_number(self, tenant_id: UUID) -> str:
        """Generate unique stock move number."""
        prefix = "SM"
        today = date.today()
        year_month = today.strftime("%Y%m")
        
        count = await self.db.scalar(
            select(func.count()).select_from(StockMove).where(
                StockMove.tenant_id == tenant_id,
                StockMove.number.like(f"{prefix}{year_month}%")
            )
        )
        
        return f"{prefix}{year_month}{(count + 1):04d}"
