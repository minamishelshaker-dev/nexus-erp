"""
Nexus ERP - Purchase Service
=============================

Business logic for the Purchase module including:
- Purchase order management
- Receipt processing
- Purchase invoice handling
- Integration with inventory and accounting
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
import logging
import uuid

from app.models.purchase import (
    PurchaseOrder, PurchaseOrderLine, PurchaseOrderState,
    Receipt, ReceiptLine, ReceiptState,
    PurchaseInvoice, PurchaseInvoiceLine, PurchaseInvoiceState,
    SupplierInfo, SupplierPayment, SupplierPaymentAllocation, SupplierPaymentState
)
from app.models.sales import Invoice, InvoiceLine, InvoiceType, InvoiceState
from app.models.accounting import Partner, Account, Journal, MoveType
from app.models.inventory import (
    Product, StockMove, StockMoveType, StockMoveState,
    StockLocation, Warehouse, StockLot
)
from app.services.integration_service import IntegrationService
from app.services.inventory_service import InventoryService
from app.services.accounting_service import AccountingService

logger = logging.getLogger(__name__)


class PurchaseService:
    """
    Purchase Service
    
    Handles all purchasing-related business logic.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.integration_svc = IntegrationService(db)
        self.inventory_svc = InventoryService(db)
        self.accounting_svc = AccountingService(db)

    async def _get_tenant_record(self, model, record_id: Optional[UUID], tenant_id: UUID, label: str):
        """Fetch a tenant-owned row; never trust a client-supplied foreign key."""
        if record_id is None:
            return None
        result = await self.db.execute(
            select(model).where(
                model.id == record_id,
                model.tenant_id == tenant_id,
                model.is_deleted == False
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise ValueError(f"{label} not found")
        return record
    
    # ========================================
    # Purchase Order Management
    # ========================================
    
    async def create_purchase_order(
        self,
        tenant_id: UUID,
        data: Dict[str, Any],
        user_id: Optional[UUID] = None
    ) -> PurchaseOrder:
        """
        Create a new purchase order.
        
        Args:
            tenant_id: Tenant ID
            data: Order data including lines
            user_id: Creating user ID
            
        Returns:
            Created purchase order
        """
        # Validate tenant-owned references before persisting the order.
        await self._get_tenant_record(Partner, data.get("partner_id"), tenant_id, "Supplier")
        await self._get_tenant_record(Warehouse, data.get("warehouse_id"), tenant_id, "Warehouse")
        # Generate order number
        number = await self._generate_po_number(tenant_id)
        
        order = PurchaseOrder(
            tenant_id=tenant_id,
            number=number,
            name=data.get("name", f"PO {number}"),
            partner_id=data["partner_id"],
            partner_ref=data.get("partner_ref"),
            date_order=data.get("date_order", date.today()),
            date_planned=data.get("date_planned"),
            state=PurchaseOrderState.DRAFT,
            warehouse_id=data.get("warehouse_id"),
            purchaser_id=data.get("purchaser_id"),
            payment_term_id=data.get("payment_term_id"),
            incoterm_id=data.get("incoterm_id"),
            currency_id=data.get("currency_id"),
            exchange_rate=data.get("exchange_rate", Decimal("1")),
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
                product = await self._get_tenant_record(Product, line_data["product_id"], tenant_id, "Product")
            
            line = PurchaseOrderLine(
                tenant_id=tenant_id,
                order_id=order.id,
                product_id=line_data.get("product_id"),
                description=line_data["description"],
                quantity=Decimal(str(line_data["quantity"])),
                uom_id=line_data.get("uom_id") or (product.uom_id if product else None),
                price_unit=Decimal(str(line_data["price_unit"])),
                discount=Decimal(str(line_data.get("discount", 0))),
                tax_ids=line_data.get("tax_ids", []),
                date_planned=line_data.get("date_planned"),
                analytic_account_id=line_data.get("analytic_account_id"),
                notes=line_data.get("notes")
            )
            line.calculate_subtotal()
            self.db.add(line)
        
        await self.db.flush()
        order.calculate_totals()
        
        await self.db.commit()
        await self.db.refresh(order)
        
        return order
    
    async def confirm_purchase_order(
        self,
        order_id: UUID,
        tenant_id: UUID,
        approve: bool = False,
        user_id: Optional[UUID] = None
    ) -> PurchaseOrder:
        """
        Confirm a purchase order.
        
        Args:
            order_id: Order ID
            tenant_id: Tenant ID
            approve: Also approve the order
            user_id: Confirming user ID
            
        Returns:
            Confirmed order
        """
        order = await self._get_purchase_order(order_id, tenant_id)
        
        if order.state != PurchaseOrderState.DRAFT:
            raise ValueError("Only draft orders can be confirmed")
        
        order.state = PurchaseOrderState.CONFIRMED if not approve else PurchaseOrderState.APPROVED
        order.date_confirm = date.today()
        order.confirmed_at = datetime.utcnow()
        order.confirmed_by_id = user_id
        
        if approve:
            order.date_approve = date.today()
            order.approved_by_id = user_id
        
        await self.db.commit()
        return order
    
    async def approve_purchase_order(
        self,
        order_id: UUID,
        tenant_id: UUID,
        user_id: Optional[UUID] = None
    ) -> PurchaseOrder:
        """Approve a confirmed purchase order."""
        order = await self._get_purchase_order(order_id, tenant_id)
        
        if order.state != PurchaseOrderState.CONFIRMED:
            raise ValueError("Only confirmed orders can be approved")
        
        order.state = PurchaseOrderState.APPROVED
        order.date_approve = date.today()
        order.approved_by_id = user_id
        
        await self.db.commit()
        return order
    
    async def cancel_purchase_order(
        self,
        order_id: UUID,
        tenant_id: UUID,
        reason: Optional[str] = None,
        user_id: Optional[UUID] = None
    ) -> PurchaseOrder:
        """Cancel a purchase order."""
        order = await self._get_purchase_order(order_id, tenant_id)
        
        if order.state == PurchaseOrderState.DONE:
            raise ValueError("Cannot cancel completed orders")
        
        if order.amount_billed > 0:
            raise ValueError("Cannot cancel order with invoices")
        
        # Check for receipts
        if order.receipts:
            for receipt in order.receipts:
                if receipt.state != ReceiptState.CANCELLED:
                    raise ValueError("Cannot cancel order with active receipts")
        
        order.state = PurchaseOrderState.CANCELLED
        order.notes = (order.notes or "") + f"\nCancelled: {reason or 'No reason provided'}"
        
        await self.db.commit()
        return order
    
    # ========================================
    # Receipt Management
    # ========================================
    
    async def create_receipt(
        self,
        tenant_id: UUID,
        data: Dict[str, Any],
        user_id: Optional[UUID] = None
    ) -> Receipt:
        """
        Create a new receipt.
        
        Args:
            tenant_id: Tenant ID
            data: Receipt data including lines
            user_id: Creating user ID
            
        Returns:
            Created receipt
        """
        await self._get_tenant_record(Partner, data.get("partner_id"), tenant_id, "Supplier")
        await self._get_tenant_record(PurchaseOrder, data.get("purchase_order_id"), tenant_id, "Purchase order")
        await self._get_tenant_record(Warehouse, data.get("warehouse_id"), tenant_id, "Warehouse")
        await self._get_tenant_record(StockLocation, data.get("location_id"), tenant_id, "Stock location")
        # Generate receipt number
        number = await self._generate_receipt_number(tenant_id)
        
        receipt = Receipt(
            tenant_id=tenant_id,
            number=number,
            name=data.get("name", f"Receipt {number}"),
            purchase_order_id=data.get("purchase_order_id"),
            partner_id=data["partner_id"],
            date=data.get("date", date.today()),
            state=ReceiptState.DRAFT,
            warehouse_id=data.get("warehouse_id"),
            location_id=data.get("location_id"),
            notes=data.get("notes"),
            created_by_id=user_id
        )
        
        self.db.add(receipt)
        await self.db.flush()
        
        # Create lines
        for line_data in data.get("lines", []):
            await self._get_tenant_record(Product, line_data.get("product_id"), tenant_id, "Product")
            purchase_line = await self._get_tenant_record(PurchaseOrderLine, line_data.get("purchase_line_id"), tenant_id, "Purchase order line")
            if purchase_line and data.get("purchase_order_id") and purchase_line.order_id != data["purchase_order_id"]:
                raise ValueError("Receipt line does not belong to the selected purchase order")
            await self._get_tenant_record(StockLot, line_data.get("lot_id"), tenant_id, "Stock lot")
            line = ReceiptLine(
                tenant_id=tenant_id,
                receipt_id=receipt.id,
                purchase_line_id=line_data.get("purchase_line_id"),
                product_id=line_data["product_id"],
                description=line_data.get("description"),
                quantity=Decimal(str(line_data["quantity"])),
                uom_id=line_data.get("uom_id"),
                lot_id=line_data.get("lot_id"),
                lot_name=line_data.get("lot_name"),
                expiration_date=line_data.get("expiration_date"),
                notes=line_data.get("notes")
            )
            self.db.add(line)
        
        await self.db.commit()
        await self.db.refresh(receipt)
        
        return receipt
    
    async def create_receipt_from_order(
        self,
        order_id: UUID,
        tenant_id: UUID,
        lines: Optional[List[Dict]] = None,
        warehouse_id: Optional[UUID] = None,
        location_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None
    ) -> Receipt:
        """
        Create receipt from purchase order.
        
        Args:
            order_id: Purchase order ID
            tenant_id: Tenant ID
            lines: Optional specific quantities to receive
            warehouse_id: Override warehouse
            location_id: Override location
            user_id: Creating user ID
            
        Returns:
            Created receipt
        """
        order = await self._get_purchase_order(order_id, tenant_id)
        
        if order.state not in (PurchaseOrderState.CONFIRMED, PurchaseOrderState.APPROVED):
            raise ValueError("Order must be confirmed or approved to create receipt")
        
        number = await self._generate_receipt_number(tenant_id)
        
        # Get default location
        if not warehouse_id:
            warehouse_id = order.warehouse_id
        if not location_id and warehouse_id:
            # Get default input location for warehouse
            result = await self.db.execute(
                select(StockLocation).where(
                    StockLocation.warehouse_id == warehouse_id,
                    StockLocation.tenant_id == tenant_id,
                    StockLocation.is_deleted == False,
                    StockLocation.location_type == "input"
                )
            )
            default_location = result.scalar_one_or_none()
            location_id = default_location.id if default_location else None
        
        receipt = Receipt(
            tenant_id=tenant_id,
            number=number,
            name=f"Receipt for {order.number}",
            purchase_order_id=order.id,
            partner_id=order.partner_id,
            date=date.today(),
            state=ReceiptState.DRAFT,
            warehouse_id=warehouse_id,
            location_id=location_id,
            origin=order.number,
            created_by_id=user_id
        )
        
        self.db.add(receipt)
        await self.db.flush()
        
        # Create lines from order
        for po_line in order.lines:
            quantity_to_receive = po_line.quantity - po_line.quantity_received
            
            # Check if specific quantity provided
            if lines:
                line_data = next(
                    (l for l in lines if l.get("purchase_line_id") == str(po_line.id)),
                    None
                )
                if line_data:
                    quantity_to_receive = min(
                        Decimal(str(line_data.get("quantity", 0))),
                        quantity_to_receive
                    )
            
            if quantity_to_receive <= 0:
                continue
            
            receipt_line = ReceiptLine(
                tenant_id=tenant_id,
                receipt_id=receipt.id,
                purchase_line_id=po_line.id,
                product_id=po_line.product_id,
                description=po_line.description,
                quantity=quantity_to_receive,
                uom_id=po_line.uom_id
            )
            self.db.add(receipt_line)
        
        await self.db.commit()
        await self.db.refresh(receipt)
        
        return receipt
    
    async def confirm_receipt(
        self,
        receipt_id: UUID,
        tenant_id: UUID,
        date_done: Optional[date] = None,
        create_invoice: bool = False,
        user_id: Optional[UUID] = None
    ) -> Receipt:
        """
        Confirm a receipt - process the goods receipt.
        
        This will:
        1. Create stock moves for incoming goods
        2. Update inventory quantities
        3. Create accounting entries
        4. Optionally create invoice
        
        Args:
            receipt_id: Receipt ID
            tenant_id: Tenant ID
            date_done: Completion date
            create_invoice: Create vendor bill
            user_id: Confirming user ID
            
        Returns:
            Confirmed receipt
        """
        receipt = await self._get_receipt(receipt_id, tenant_id)
        
        if receipt.state != ReceiptState.DRAFT:
            raise ValueError("Only draft receipts can be confirmed")
        
        receipt.state = ReceiptState.DONE
        receipt.date_done = date_done or date.today()
        receipt.confirmed_at = datetime.utcnow()
        receipt.confirmed_by_id = user_id
        
        # Create stock moves for each line
        for line in receipt.lines:
            await self._create_stock_move_for_receipt_line(
                receipt, line, tenant_id, user_id
            )
            
            # Update purchase line received quantity
            if line.purchase_line_id:
                po_line = await self._get_tenant_record(PurchaseOrderLine, line.purchase_line_id, tenant_id, "Purchase order line")
                if po_line:
                    po_line.quantity_received += line.quantity
        
        # Update purchase order receipt status
        if receipt.purchase_order_id:
            await self._update_po_receipt_status(receipt.purchase_order_id, tenant_id)
        
        # Create accounting entries
        await self.integration_svc.process_purchase_accounting(
            receipt.purchase_order_id, receipt.id, tenant_id, user_id
        )
        
        # Create invoice if requested
        if create_invoice:
            await self._create_invoice_from_receipt(receipt, tenant_id, user_id)
        
        await self.db.commit()
        return receipt
    
    async def cancel_receipt(
        self,
        receipt_id: UUID,
        tenant_id: UUID,
        reason: Optional[str] = None,
        user_id: Optional[UUID] = None
    ) -> Receipt:
        """Cancel a receipt."""
        receipt = await self._get_receipt(receipt_id, tenant_id)
        
        if receipt.state == ReceiptState.DONE:
            raise ValueError("Cannot cancel completed receipts")
        
        receipt.state = ReceiptState.CANCELLED
        receipt.notes = (receipt.notes or "") + f"\nCancelled: {reason or 'No reason provided'}"
        
        await self.db.commit()
        return receipt
    
    # ========================================
    # Purchase Invoice Management
    # ========================================
    
    async def create_purchase_invoice(
        self,
        tenant_id: UUID,
        data: Dict[str, Any],
        user_id: Optional[UUID] = None
    ) -> PurchaseInvoice:
        """Create a new purchase invoice (vendor bill)."""
        await self._get_tenant_record(Partner, data.get("partner_id"), tenant_id, "Supplier")
        await self._get_tenant_record(PurchaseOrder, data.get("purchase_order_id"), tenant_id, "Purchase order")
        await self._get_tenant_record(Receipt, data.get("receipt_id"), tenant_id, "Receipt")
        await self._get_tenant_record(Journal, data.get("journal_id"), tenant_id, "Journal")
        await self._get_tenant_record(Account, data.get("account_id"), tenant_id, "Payables account")
        number = await self._generate_pi_number(tenant_id)
        
        invoice = PurchaseInvoice(
            tenant_id=tenant_id,
            number=number,
            name=data.get("name", f"Bill {number}"),
            supplier_invoice_number=data.get("supplier_invoice_number"),
            partner_id=data["partner_id"],
            date_invoice=data.get("date_invoice", date.today()),
            date_due=data.get("date_due"),
            state=PurchaseInvoiceState.DRAFT,
            purchase_order_id=data.get("purchase_order_id"),
            receipt_id=data.get("receipt_id"),
            origin=data.get("origin"),
            payment_term_id=data.get("payment_term_id"),
            currency_id=data.get("currency_id"),
            exchange_rate=data.get("exchange_rate", Decimal("1")),
            journal_id=data.get("journal_id"),
            account_id=data.get("account_id"),
            notes=data.get("notes"),
            created_by_id=user_id
        )
        
        self.db.add(invoice)
        await self.db.flush()
        
        # Create lines
        for line_data in data.get("lines", []):
            await self._get_tenant_record(Product, line_data.get("product_id"), tenant_id, "Product")
            await self._get_tenant_record(Account, line_data.get("account_id"), tenant_id, "Expense account")
            line = PurchaseInvoiceLine(
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
            invoice.lines.append(line)
            self.db.add(line)
        
        await self.db.flush()
        invoice.calculate_totals()
        
        await self.db.commit()
        await self.db.refresh(invoice)
        
        return invoice
    
    async def create_invoice_from_receipt(
        self,
        receipt_id: UUID,
        tenant_id: UUID,
        date_invoice: Optional[date] = None,
        user_id: Optional[UUID] = None
    ) -> PurchaseInvoice:
        """Create purchase invoice from receipt."""
        receipt = await self._get_receipt(receipt_id, tenant_id)
        return await self._create_invoice_from_receipt(receipt, tenant_id, user_id, date_invoice)
    
    async def post_purchase_invoice(
        self,
        invoice_id: UUID,
        tenant_id: UUID,
        date_posted: Optional[date] = None,
        user_id: Optional[UUID] = None
    ) -> PurchaseInvoice:
        """Post a purchase invoice."""
        invoice = await self._get_purchase_invoice(invoice_id, tenant_id)
        
        if invoice.state != PurchaseInvoiceState.DRAFT:
            raise ValueError("Only draft invoices can be posted")
        
        # Validate source links before changing the state. A vendor bill must not
        # silently post against another supplier's order or receipt.
        if invoice.purchase_order_id:
            locked_order_result = await self.db.execute(
                select(PurchaseOrder).where(
                    PurchaseOrder.id == invoice.purchase_order_id,
                    PurchaseOrder.tenant_id == tenant_id,
                    PurchaseOrder.is_deleted == False,
                ).with_for_update()
            )
            order = locked_order_result.scalar_one_or_none()
            if order is None:
                raise ValueError("Purchase order not found")
            if order.partner_id != invoice.partner_id:
                raise ValueError("Purchase order supplier does not match vendor bill")
        receipt = None
        receipt_lines = []
        if invoice.receipt_id:
            locked_receipt_result = await self.db.execute(
                select(Receipt).where(
                    Receipt.id == invoice.receipt_id,
                    Receipt.tenant_id == tenant_id,
                    Receipt.is_deleted == False,
                ).with_for_update()
            )
            receipt = locked_receipt_result.scalar_one_or_none()
            if receipt is None:
                raise ValueError("Receipt not found")
            if receipt.partner_id != invoice.partner_id:
                raise ValueError("Receipt supplier does not match vendor bill")
            if receipt.state != ReceiptState.DONE:
                raise ValueError("Vendor bill cannot reference an incomplete receipt")
            if receipt.purchase_order_id != invoice.purchase_order_id:
                raise ValueError("Receipt and vendor bill must reference the same purchase order")
            receipt_result = await self.db.execute(
                select(ReceiptLine).where(
                    ReceiptLine.receipt_id == receipt.id,
                    ReceiptLine.tenant_id == tenant_id,
                    ReceiptLine.is_deleted == False,
                ).order_by(ReceiptLine.sequence)
            )
            receipt_lines = list(receipt_result.scalars().all())
            if not receipt_lines:
                raise ValueError("A linked receipt must contain active receipt lines")

        if not invoice.lines:
            raise ValueError("Cannot post a vendor bill without invoice lines")
        # Recalculate from persisted, tenant-owned lines immediately before posting;
        # do not trust totals that may be stale after an edit.
        invoice.calculate_totals()
        if invoice.amount_total <= 0 or invoice.amount_residual < 0:
            raise ValueError("Vendor bill total must be positive and residual cannot be negative")

        # Three-way quantity control: receipt-backed bills cannot exceed the
        # completed, not-yet-invoiced quantities on their receipt.
        billed_allocation = []
        if receipt is not None:
            received_by_product: Dict[UUID, Decimal] = {}
            for rline in receipt_lines:
                received_by_product[rline.product_id] = received_by_product.get(rline.product_id, Decimal("0")) + Decimal(str(rline.quantity_done or rline.quantity))
            previous_result = await self.db.execute(
                select(PurchaseInvoiceLine.product_id, func.sum(PurchaseInvoiceLine.quantity))
                .join(PurchaseInvoice, PurchaseInvoice.id == PurchaseInvoiceLine.invoice_id)
                .where(
                    PurchaseInvoice.receipt_id == receipt.id,
                    PurchaseInvoice.tenant_id == tenant_id,
                    PurchaseInvoice.is_deleted == False,
                    PurchaseInvoice.state.in_([PurchaseInvoiceState.POSTED, PurchaseInvoiceState.PAID]),
                    PurchaseInvoice.id != invoice.id,
                    PurchaseInvoiceLine.tenant_id == tenant_id,
                    PurchaseInvoiceLine.is_deleted == False,
                ).group_by(PurchaseInvoiceLine.product_id)
            )
            previously_billed = {pid: Decimal(str(qty or 0)) for pid, qty in previous_result.all()}
            invoice_qty_by_product: Dict[UUID, Decimal] = {}
            for inv_line in invoice.lines:
                if inv_line.product_id is None:
                    raise ValueError("Receipt-backed invoice lines must reference a product")
                qty = Decimal(str(inv_line.quantity))
                if qty <= 0:
                    raise ValueError("Vendor bill quantities must be positive")
                invoice_qty_by_product[inv_line.product_id] = invoice_qty_by_product.get(inv_line.product_id, Decimal("0")) + qty
            for product_id, invoice_qty in invoice_qty_by_product.items():
                available_qty = received_by_product.get(product_id, Decimal("0")) - previously_billed.get(product_id, Decimal("0"))
                if invoice_qty > available_qty:
                    raise ValueError(f"Vendor bill quantity for product {product_id} exceeds unbilled received quantity ({invoice_qty} > {max(available_qty, Decimal('0'))})")
            remaining_by_product = dict(invoice_qty_by_product)
            allocated_by_po_line: Dict[UUID, Decimal] = {}
            for rline in receipt_lines:
                if not rline.purchase_line_id:
                    continue
                remaining = remaining_by_product.get(rline.product_id, Decimal("0"))
                if remaining <= 0:
                    continue
                po_line = await self._get_tenant_record(PurchaseOrderLine, rline.purchase_line_id, tenant_id, "Purchase order line")
                if po_line.product_id != rline.product_id:
                    raise ValueError("Receipt line product does not match its purchase order line")
                already_allocated = allocated_by_po_line.get(po_line.id, Decimal("0"))
                order_remaining = max(
                    Decimal(str(po_line.quantity or 0))
                    - Decimal(str(po_line.quantity_billed or 0))
                    - already_allocated,
                    Decimal("0"),
                )
                allocation = min(
                    remaining,
                    Decimal(str(rline.quantity_done or rline.quantity)),
                    order_remaining,
                )
                if allocation > 0:
                    billed_allocation.append((po_line, allocation))
                    allocated_by_po_line[po_line.id] = already_allocated + allocation
                    remaining_by_product[rline.product_id] = remaining - allocation
            if invoice.purchase_order_id and any(qty > 0 for qty in remaining_by_product.values()):
                raise ValueError("Receipt quantities cannot be allocated to the linked purchase order lines")

        invoice.date_posted = date_posted or date.today()
        invoice.posted_at = datetime.utcnow()
        invoice.posted_by_id = user_id
        invoice.state = PurchaseInvoiceState.POSTED

        # Posting and journal creation share the same database transaction.
        # The integration service raises on incomplete/unbalanced accounting data;
        # never commit a posted bill without its journal entry.
        entry = await self.integration_svc.process_vendor_bill_accounting(
            invoice.id, tenant_id, user_id
        )
        if entry is None:
            raise ValueError("Vendor bill accounting entry could not be created")

        for po_line, quantity in billed_allocation:
            po_line.quantity_billed = Decimal(str(po_line.quantity_billed or 0)) + quantity
        if invoice.purchase_order_id:
            await self._update_po_invoice_status(invoice.purchase_order_id, tenant_id)

        await self.db.commit()
        await self.db.refresh(invoice)
        return invoice
    
    async def register_supplier_payment(
        self,
        tenant_id: UUID,
        supplier_id: UUID,
        payment_date: date,
        amount: Decimal,
        journal_id: UUID,
        bank_account_id: UUID,
        allocations: List[Dict[str, Any]],
        user_id: Optional[UUID] = None,
        reference: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> SupplierPayment:
        """Post a supplier payment and allocate it to posted vendor bills atomically.

        This first release deliberately requires 100% allocation to existing bills.
        Supplier advances, overpayments, FX differences and bank-statement matching
        are rejected/deferred until their dedicated accounts and workflows exist.
        """
        amount = Decimal(str(amount))
        if not amount.is_finite() or amount <= 0:
            raise ValueError("Supplier payment amount must be a positive finite value")
        if not allocations:
            raise ValueError("At least one vendor bill allocation is required")

        supplier = await self._get_tenant_record(Partner, supplier_id, tenant_id, "Supplier")
        if supplier is None:
            raise ValueError("Supplier not found")
        if not supplier.payable_account_id:
            raise ValueError("Supplier must have a payable account configured")
        payable = await self._get_tenant_record(Account, supplier.payable_account_id, tenant_id, "Supplier payable account")
        bank = await self._get_tenant_record(Account, bank_account_id, tenant_id, "Bank/cash account")
        journal = await self._get_tenant_record(Journal, journal_id, tenant_id, "Payment journal")
        if payable.is_header or bank.is_header:
            raise ValueError("Payment accounts must be posting accounts, not header accounts")
        if payable.id == bank.id:
            raise ValueError("Payable and bank/cash accounts must be different")

        # Normalize and combine duplicate invoice allocations before locking.
        normalized: Dict[UUID, Decimal] = {}
        for item in allocations:
            invoice_id = item.get("invoice_id")
            allocation_amount = Decimal(str(item.get("amount", "0")))
            if not invoice_id or not allocation_amount.is_finite() or allocation_amount <= 0:
                raise ValueError("Each allocation requires an invoice and a positive finite amount")
            normalized[invoice_id] = normalized.get(invoice_id, Decimal("0")) + allocation_amount
        if sum(normalized.values(), Decimal("0")) != amount:
            raise ValueError("Payment amount must equal the total allocated to vendor bills; advances and unallocated balances are not enabled")

        invoices = []
        # Stable ordering avoids deadlocks when concurrent payments cover the same bills.
        for invoice_id in sorted(normalized, key=str):
            invoice = await self.db.scalar(select(PurchaseInvoice).where(
                PurchaseInvoice.id == invoice_id,
                PurchaseInvoice.tenant_id == tenant_id,
                PurchaseInvoice.is_deleted == False,
            ).with_for_update())
            if invoice is None:
                raise ValueError("Vendor bill not found")
            if invoice.partner_id != supplier_id:
                raise ValueError("All allocated vendor bills must belong to the selected supplier")
            if invoice.state not in (PurchaseInvoiceState.POSTED, PurchaseInvoiceState.PARTIAL):
                raise ValueError("Payments can only be allocated to posted or partially paid vendor bills")
            residual = Decimal(str(invoice.amount_residual or 0))
            if normalized[invoice_id] > residual:
                raise ValueError(f"Allocation exceeds the outstanding balance of vendor bill {invoice.number}")
            if invoice.currency_id and any(i.currency_id != invoice.currency_id for i in invoices):
                raise ValueError("Multi-currency allocations are not supported in this payment")
            invoices.append(invoice)

        if len({invoice.currency_id for invoice in invoices}) > 1:
            raise ValueError("A single supplier payment cannot allocate across different currencies")

        payment_number = f"SP-{payment_date:%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"
        payment = SupplierPayment(
            tenant_id=tenant_id, number=payment_number, partner_id=supplier_id,
            payment_date=payment_date, amount=amount, currency_id=invoices[0].currency_id,
            journal_id=journal.id, bank_account_id=bank.id, reference=reference,
            notes=notes, state=SupplierPaymentState.POSTED.value,
            posted_at=datetime.utcnow(), posted_by_id=user_id, created_by_id=user_id,
        )
        self.db.add(payment)
        await self.db.flush()

        for invoice in invoices:
            allocated = normalized[invoice.id]
            self.db.add(SupplierPaymentAllocation(
                tenant_id=tenant_id, payment_id=payment.id, invoice_id=invoice.id,
                amount=allocated, created_by_id=user_id,
            ))
            invoice.amount_paid = Decimal(str(invoice.amount_paid or 0)) + allocated
            invoice.amount_residual = Decimal(str(invoice.amount_total)) - invoice.amount_paid
            if invoice.amount_residual < 0:
                raise ValueError("Vendor bill residual cannot become negative")
            invoice.state = (PurchaseInvoiceState.PAID if invoice.amount_residual == 0
                             else PurchaseInvoiceState.PARTIAL)

        entry = await self.accounting_svc.create_journal_entry(
            date=payment_date,
            lines=[
                {"account_id": payable.id, "debit": amount, "credit": Decimal("0"),
                 "partner_id": supplier_id, "partner_type": "supplier",
                 "name": f"Supplier payment {payment_number}"},
                {"account_id": bank.id, "debit": Decimal("0"), "credit": amount,
                 "partner_id": supplier_id, "partner_type": "supplier",
                 "name": f"Supplier payment {payment_number}"},
            ],
            description=f"Supplier Payment: {payment_number}", ref=reference or payment_number,
            move_type=MoveType.PAYMENT, journal_id=journal.id,
            source_model="supplier_payment", source_id=payment.id,
            tenant_id=tenant_id, created_by_id=user_id,
        )
        await self.accounting_svc.post_journal_entry(entry.id, user_id, tenant_id)
        payment.journal_entry_id = entry.id
        await self.db.commit()
        await self.db.refresh(payment)
        return payment

    async def cancel_supplier_payment(
        self,
        payment_id: UUID,
        tenant_id: UUID,
        user_id: Optional[UUID],
        reversal_date: Optional[date],
        reason: str,
    ) -> SupplierPayment:
        """Cancel a posted supplier payment through a posted accounting reversal.

        The payment, its allocations, affected vendor bills and reversal are
        changed in one transaction. Historical allocation rows are retained.
        """
        reason = (reason or "").strip()
        if len(reason) < 3:
            raise ValueError("A meaningful cancellation reason is required")

        payment = await self.db.scalar(select(SupplierPayment).where(
            SupplierPayment.id == payment_id,
            SupplierPayment.tenant_id == tenant_id,
            SupplierPayment.is_deleted == False,
        ).with_for_update())
        if payment is None:
            raise ValueError("Supplier payment not found")
        if payment.state != SupplierPaymentState.POSTED.value:
            raise ValueError("Only posted supplier payments can be cancelled")
        if payment.journal_entry_id is None:
            raise ValueError("Supplier payment has no accounting entry; cancellation is unsafe")

        allocation_result = await self.db.execute(
            select(SupplierPaymentAllocation).where(
                SupplierPaymentAllocation.payment_id == payment.id,
                SupplierPaymentAllocation.tenant_id == tenant_id,
                SupplierPaymentAllocation.is_deleted == False,
            ).order_by(SupplierPaymentAllocation.invoice_id)
        )
        allocations = allocation_result.scalars().all()
        if not allocations:
            raise ValueError("Supplier payment has no active bill allocations")
        allocated_total = sum((Decimal(str(a.amount)) for a in allocations), Decimal("0"))
        if allocated_total != Decimal(str(payment.amount)):
            raise ValueError("Payment allocations do not reconcile to the payment amount")

        # Lock all affected bills in deterministic order before restoring balances.
        invoices = {}
        for invoice_id in sorted({a.invoice_id for a in allocations}, key=str):
            invoice = await self.db.scalar(select(PurchaseInvoice).where(
                PurchaseInvoice.id == invoice_id,
                PurchaseInvoice.tenant_id == tenant_id,
                PurchaseInvoice.is_deleted == False,
            ).with_for_update())
            if invoice is None:
                raise ValueError("An allocated vendor bill no longer exists")
            if invoice.partner_id != payment.partner_id:
                raise ValueError("An allocated vendor bill belongs to a different supplier")
            invoices[invoice_id] = invoice

        # Reverse first; the accounting service validates source state and
        # prevents a second reversal. No commit occurs inside that service.
        reversal = await self.accounting_svc.reverse_journal_entry(
            payment.journal_entry_id,
            reversal_date=reversal_date or date.today(),
            reason=f"Supplier payment cancellation: {reason}",
            user_id=user_id,
            tenant_id=tenant_id,
        )

        for allocation in allocations:
            invoice = invoices[allocation.invoice_id]
            paid = Decimal(str(invoice.amount_paid or 0))
            allocated = Decimal(str(allocation.amount))
            if allocated > paid:
                raise ValueError("Payment allocation exceeds the bill's recorded paid amount")
            invoice.amount_paid = paid - allocated
            invoice.amount_residual = Decimal(str(invoice.amount_total or 0)) - invoice.amount_paid
            if invoice.amount_residual < 0:
                raise ValueError("Vendor bill residual became negative during cancellation")
            if invoice.state != PurchaseInvoiceState.CANCELLED:
                invoice.state = (PurchaseInvoiceState.POSTED if invoice.amount_paid == 0
                                 else PurchaseInvoiceState.PARTIAL)
            allocation.is_deleted = True
            allocation.deleted_at = datetime.utcnow()
            allocation.deleted_by_id = user_id

        payment.reversal_journal_entry_id = reversal.id
        payment.state = SupplierPaymentState.CANCELLED.value
        payment.notes = ((payment.notes + "\n") if payment.notes else "") + (
            f"Cancelled: {reason}; reversal journal: {reversal.number}"
        )
        payment.updated_by_id = user_id
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(payment)
        return payment

    # ========================================
    # List/Query Methods
    # ========================================
    
    async def list_purchase_orders(
        self,
        tenant_id: UUID,
        state: Optional[PurchaseOrderState] = None,
        partner_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[PurchaseOrder], int]:
        """List purchase orders with filters."""
        query = select(PurchaseOrder).where(
            PurchaseOrder.tenant_id == tenant_id,
            PurchaseOrder.is_deleted == False
        )
        
        if state:
            query = query.where(PurchaseOrder.state == state)
        if partner_id:
            query = query.where(PurchaseOrder.partner_id == partner_id)
        if date_from:
            query = query.where(PurchaseOrder.date_order >= date_from)
        if date_to:
            query = query.where(PurchaseOrder.date_order <= date_to)
        
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)
        
        query = query.order_by(PurchaseOrder.date_order.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        orders = result.scalars().all()
        
        return list(orders), total or 0
    
    async def list_receipts(
        self,
        tenant_id: UUID,
        state: Optional[ReceiptState] = None,
        partner_id: Optional[UUID] = None,
        purchase_order_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[Receipt], int]:
        """List receipts with filters."""
        query = select(Receipt).where(
            Receipt.tenant_id == tenant_id,
            Receipt.is_deleted == False
        )
        
        if state:
            query = query.where(Receipt.state == state)
        if partner_id:
            query = query.where(Receipt.partner_id == partner_id)
        if purchase_order_id:
            query = query.where(Receipt.purchase_order_id == purchase_order_id)
        if date_from:
            query = query.where(Receipt.date >= date_from)
        if date_to:
            query = query.where(Receipt.date <= date_to)
        
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)
        
        query = query.order_by(Receipt.date.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        receipts = result.scalars().all()
        
        return list(receipts), total or 0
    
    async def list_purchase_invoices(
        self,
        tenant_id: UUID,
        state: Optional[PurchaseInvoiceState] = None,
        partner_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[PurchaseInvoice], int]:
        """List purchase invoices with filters."""
        query = select(PurchaseInvoice).where(
            PurchaseInvoice.tenant_id == tenant_id,
            PurchaseInvoice.is_deleted == False
        )
        
        if state:
            query = query.where(PurchaseInvoice.state == state)
        if partner_id:
            query = query.where(PurchaseInvoice.partner_id == partner_id)
        if date_from:
            query = query.where(PurchaseInvoice.date_invoice >= date_from)
        if date_to:
            query = query.where(PurchaseInvoice.date_invoice <= date_to)
        
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)
        
        query = query.order_by(PurchaseInvoice.date_invoice.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        invoices = result.scalars().all()
        
        return list(invoices), total or 0
    
    # ========================================
    # Private Helper Methods
    # ========================================
    
    async def _get_purchase_order(self, order_id: UUID, tenant_id: UUID) -> PurchaseOrder:
        """Get purchase order by ID."""
        result = await self.db.execute(
            select(PurchaseOrder)
            .options(selectinload(PurchaseOrder.lines))
            .where(
                PurchaseOrder.id == order_id,
                PurchaseOrder.tenant_id == tenant_id,
                PurchaseOrder.is_deleted == False
            )
        )
        order = result.scalar_one_or_none()
        if not order:
            raise ValueError(f"Purchase order {order_id} not found")
        return order
    
    async def _get_receipt(self, receipt_id: UUID, tenant_id: UUID) -> Receipt:
        """Get receipt by ID."""
        result = await self.db.execute(
            select(Receipt)
            .options(selectinload(Receipt.lines))
            .where(
                Receipt.id == receipt_id,
                Receipt.tenant_id == tenant_id,
                Receipt.is_deleted == False
            )
        )
        receipt = result.scalar_one_or_none()
        if not receipt:
            raise ValueError(f"Receipt {receipt_id} not found")
        return receipt
    
    async def _get_purchase_invoice(self, invoice_id: UUID, tenant_id: UUID) -> PurchaseInvoice:
        """Get purchase invoice by ID."""
        result = await self.db.execute(
            select(PurchaseInvoice)
            .options(selectinload(PurchaseInvoice.lines))
            .where(
                PurchaseInvoice.id == invoice_id,
                PurchaseInvoice.tenant_id == tenant_id,
                PurchaseInvoice.is_deleted == False
            )
        )
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise ValueError(f"Purchase invoice {invoice_id} not found")
        return invoice
    
    async def _create_stock_move_for_receipt_line(
        self,
        receipt: Receipt,
        line: ReceiptLine,
        tenant_id: UUID,
        user_id: Optional[UUID] = None
    ):
        """Create and process an incoming stock move through InventoryService."""
        product = await self._get_tenant_record(Product, line.product_id, tenant_id, "Product")
        if not product.is_stockable:
            return
        if receipt.warehouse_id is None or receipt.location_id is None:
            raise ValueError("A warehouse and receiving stock location are required for stockable products")

        unit_cost = product.cost_price
        if line.purchase_line_id:
            po_line = await self._get_tenant_record(
                PurchaseOrderLine, line.purchase_line_id, tenant_id, "Purchase order line"
            )
            unit_cost = po_line.price_unit

        move = await self.inventory_svc.create_stock_move(
            product_id=line.product_id,
            quantity=line.quantity,
            uom_id=line.uom_id or product.uom_id,
            move_type=StockMoveType.IN,
            warehouse_to_id=receipt.warehouse_id,
            location_to_id=receipt.location_id,
            unit_cost=unit_cost,
            move_date=receipt.date,
            reference=receipt.number,
            reference_id=receipt.id,
            reference_type="receipt",
            partner_id=receipt.partner_id,
            lot_id=line.lot_id,
            serial_number=line.lot_name,
            notes=f"Receipt: {receipt.number}",
            tenant_id=tenant_id,
            created_by_id=user_id,
            auto_confirm=False
        )
        await self.inventory_svc.confirm_stock_move(move.id, tenant_id, line.quantity)
        await self.inventory_svc.process_stock_move(move.id, tenant_id)
        line.stock_move_id = move.id

    async def _update_po_receipt_status(self, order_id: UUID, tenant_id: UUID):
        """Update purchase order receipt status."""
        order = await self._get_tenant_record(PurchaseOrder, order_id, tenant_id, "Purchase order")
        if not order:
            return
        
        total_qty = sum(line.quantity for line in order.lines)
        received_qty = sum(line.quantity_received for line in order.lines)
        
        if received_qty >= total_qty:
            order.receipt_status = "done"
            order.state = PurchaseOrderState.DONE
            order.done_at = datetime.utcnow()
        elif received_qty > 0:
            order.receipt_status = "partial"
    
    async def _create_invoice_from_receipt(
        self,
        receipt: Receipt,
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        date_invoice: Optional[date] = None
    ) -> PurchaseInvoice:
        """Create purchase invoice from receipt."""
        number = await self._generate_pi_number(tenant_id)
        
        # Get payable account
        partner = await self._get_tenant_record(Partner, receipt.partner_id, tenant_id, "Supplier")
        account_id = partner.payable_account_id if partner else None
        if account_id:
            await self._get_tenant_record(Account, account_id, tenant_id, "Supplier payable account")
        
        invoice = PurchaseInvoice(
            tenant_id=tenant_id,
            number=number,
            name=f"Bill for {receipt.number}",
            partner_id=receipt.partner_id,
            date_invoice=date_invoice or date.today(),
            state=PurchaseInvoiceState.DRAFT,
            purchase_order_id=receipt.purchase_order_id,
            receipt_id=receipt.id,
            origin=receipt.number,
            account_id=account_id,
            notes=receipt.notes,
            created_by_id=user_id
        )
        
        self.db.add(invoice)
        await self.db.flush()
        
        # Create lines from receipt
        for line in receipt.lines:
            product = await self._get_tenant_record(Product, line.product_id, tenant_id, "Product")
            
            # Get expense/asset account for product
            account_id = None
            if product:
                account_id = product.expense_account_id or product.asset_account_id
            
            if not account_id:
                account_id = await self._get_default_account(
                    "asset" if product and product.is_stockable else "expense", tenant_id
                )
            await self._get_tenant_record(Account, account_id, tenant_id, "Invoice debit account")
            
            # Get price from purchase line
            price_unit = product.cost_price if product else Decimal("0")
            if line.purchase_line_id:
                po_line = await self._get_tenant_record(PurchaseOrderLine, line.purchase_line_id, tenant_id, "Purchase order line")
                if po_line:
                    price_unit = po_line.price_unit
            
            invoice_line = PurchaseInvoiceLine(
                tenant_id=tenant_id,
                invoice_id=invoice.id,
                product_id=line.product_id,
                description=line.description or (product.name if product else ""),
                quantity=line.quantity,
                uom_id=line.uom_id,
                price_unit=price_unit,
                account_id=account_id
            )
            invoice_line.calculate_subtotal()
            invoice.lines.append(invoice_line)
            self.db.add(invoice_line)
            
            # Draft invoices do not consume the PO's billed quantity; this is
            # recorded only after successful accounting posting.

        await self.db.flush()
        invoice.calculate_totals()
        
        # PO invoice status is updated only after successful posting.

        return invoice
    
    async def _update_po_invoice_status(self, order_id: UUID, tenant_id: UUID):
        """Update purchase order invoice status using explicitly tenant-scoped lines."""
        order = await self._get_tenant_record(PurchaseOrder, order_id, tenant_id, "Purchase order")
        line_result = await self.db.execute(
            select(PurchaseOrderLine).where(
                PurchaseOrderLine.order_id == order_id,
                PurchaseOrderLine.tenant_id == tenant_id,
                PurchaseOrderLine.is_deleted == False,
            )
        )
        lines = list(line_result.scalars().all())
        total_qty = sum((Decimal(str(line.quantity or 0)) for line in lines), Decimal("0"))
        billed_qty = sum((Decimal(str(line.quantity_billed or 0)) for line in lines), Decimal("0"))

        if order is None:
            return
        if total_qty > 0 and billed_qty >= total_qty:
            order.invoice_status = "invoiced"
        elif billed_qty > 0:
            order.invoice_status = "partial"
        else:
            order.invoice_status = "no"

        order.amount_billed = sum(
            (Decimal(str(line.quantity_billed or 0)) * Decimal(str(line.price_unit or 0)) for line in lines),
            Decimal("0"),
        )
    
    async def _get_default_account(self, account_type: str, tenant_id: UUID) -> UUID:
        """Resolve a real tenant-owned fallback account; never return a sentinel UUID."""
        defaults = await self.integration_svc.accounting_svc.get_or_create_default_accounts(tenant_id)
        account_code = "1200" if account_type == "asset" else "6000"
        account = defaults.get(account_code)
        if account is None or account.tenant_id != tenant_id:
            raise ValueError(f"A tenant-owned default {account_type} account is required")
        return account.id
    
    async def _generate_po_number(self, tenant_id: UUID) -> str:
        """Generate unique PO number."""
        prefix = "PO"
        today = date.today()
        year_month = today.strftime("%Y%m")
        
        count = await self.db.scalar(
            select(func.count()).select_from(PurchaseOrder).where(
                PurchaseOrder.tenant_id == tenant_id,
                PurchaseOrder.number.like(f"{prefix}{year_month}%")
            )
        )
        
        return f"{prefix}{year_month}{(count + 1):04d}"
    
    async def _generate_receipt_number(self, tenant_id: UUID) -> str:
        """Generate unique receipt number."""
        prefix = "RC"
        today = date.today()
        year_month = today.strftime("%Y%m")
        
        count = await self.db.scalar(
            select(func.count()).select_from(Receipt).where(
                Receipt.tenant_id == tenant_id,
                Receipt.number.like(f"{prefix}{year_month}%")
            )
        )
        
        return f"{prefix}{year_month}{(count + 1):04d}"
    
    async def _generate_pi_number(self, tenant_id: UUID) -> str:
        """Generate unique purchase invoice number."""
        prefix = "PI"
        today = date.today()
        year_month = today.strftime("%Y%m")
        
        count = await self.db.scalar(
            select(func.count()).select_from(PurchaseInvoice).where(
                PurchaseInvoice.tenant_id == tenant_id,
                PurchaseInvoice.number.like(f"{prefix}{year_month}%")
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
