"""
Nexus ERP - Integration Service
================================

Handles integration between different modules:
- Inventory to Accounting (stock movements create journal entries)
- Sales to Inventory and Accounting
- Purchases to Inventory and Accounting

This service ensures that business events automatically trigger
the appropriate accounting entries.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import logging

from app.services.inventory_service import InventoryService
from app.services.accounting_service import AccountingService
from app.models.inventory import StockMove, StockMoveType, Product
from app.models.accounting import (
    Account, JournalEntry, MoveType, AccountType, AccountCategory, Partner
)

logger = logging.getLogger(__name__)


class IntegrationService:
    """
    Integration Service
    
    Coordinates between different modules to ensure data consistency
    and automatic accounting entries.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.inventory_svc = InventoryService(db)
        self.accounting_svc = AccountingService(db)

    async def _tenant_record(self, model, record_id: UUID, tenant_id: UUID, label: str):
        if tenant_id is None:
            raise ValueError("tenant_id is required for module integration")
        record = await self.db.scalar(select(model).where(
            model.id == record_id,
            model.tenant_id == tenant_id,
            model.is_deleted == False
        ))
        if record is None:
            logger.warning("%s %s not found in tenant scope", label, record_id)
        return record

    async def _existing_source_entry(self, source_model: str, source_id: UUID, tenant_id: UUID):
        """Return an already-created journal entry for a source document (idempotency guard)."""
        if tenant_id is None:
            raise ValueError("tenant_id is required for source-entry lookup")
        return await self.db.scalar(select(JournalEntry).where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.is_deleted == False,
            JournalEntry.source_model == source_model,
            JournalEntry.source_id == source_id
        ).limit(1))

    @staticmethod
    def _journal_lines_are_balanced(lines: List[Dict[str, Any]]) -> bool:
        debit = sum((Decimal(str(line.get("debit", 0) or 0)) for line in lines), Decimal("0"))
        credit = sum((Decimal(str(line.get("credit", 0) or 0)) for line in lines), Decimal("0"))
        return debit == credit and debit > 0
    
    # ========================================
    # Stock Movement Integration
    # ========================================
    
    async def process_stock_movement_accounting(
        self,
        stock_move: StockMove,
        tenant_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Optional[JournalEntry]:
        """
        Create accounting entries for a stock movement.
        
        This is called after a stock move is processed to update
        the accounting records accordingly.
        
        Args:
            stock_move: The processed stock move
            tenant_id: Tenant ID
            user_id: User ID
            
        Returns:
            Created JournalEntry if applicable
        """
        if tenant_id is None or stock_move.tenant_id != tenant_id or stock_move.is_deleted:
            logger.warning("Stock move is outside the active tenant scope")
            return None
        # Re-resolve the source record within tenant scope and require a completed move.
        stock_move = await self._tenant_record(StockMove, stock_move.id, tenant_id, "Stock move")
        if stock_move is None or stock_move.state.value != "done":
            logger.warning("Stock accounting requires a completed stock move")
            return None
        existing_entry = await self._existing_source_entry("stock_move", stock_move.id, tenant_id)
        if existing_entry:
            logger.info("Accounting entry already exists for stock move %s", stock_move.id)
            return existing_entry
        product = await self._tenant_record(Product, stock_move.product_id, tenant_id, "Product")
        if not product:
            logger.error(f"Product {stock_move.product_id} not found")
            return None
        
        # Get default accounts
        accounts = await self._get_stock_accounts(product, tenant_id)
        
        lines = []
        
        if stock_move.move_type == StockMoveType.IN:
            # Stock receipt: Debit inventory, Credit GR/IR or Cash
            lines = await self._create_stock_in_entry(
                stock_move, product, accounts, tenant_id
            )
        
        elif stock_move.move_type == StockMoveType.OUT:
            # Stock issue: Debit COGS, Credit inventory
            lines = await self._create_stock_out_entry(
                stock_move, product, accounts, tenant_id
            )
        
        elif stock_move.move_type == StockMoveType.INTERNAL:
            # Internal transfer: No accounting entry (same company)
            return None
        
        elif stock_move.move_type == StockMoveType.ADJUSTMENT:
            # Inventory adjustment: Debit/Credit inventory and gain/loss
            lines = await self._create_adjustment_entry(
                stock_move, product, accounts, tenant_id
            )
        
        elif stock_move.move_type == StockMoveType.LOSS:
            # Stock loss: Debit loss expense, Credit inventory
            lines = await self._create_loss_entry(
                stock_move, product, accounts, tenant_id
            )
        
        if not lines:
            return None
        if not self._journal_lines_are_balanced(lines):
            logger.error("Refusing unbalanced stock-movement journal for %s", stock_move.id)
            return None
        
        # Create journal entry
        try:
            entry = await self.accounting_svc.create_journal_entry(
                date=stock_move.date,
                lines=lines,
                description=f"Stock Move: {stock_move.number}",
                ref=stock_move.number,
                move_type=MoveType.ADJUSTMENT,
                source_model="stock_move",
                source_id=stock_move.id,
                tenant_id=tenant_id,
                created_by_id=user_id
            )
            
            # Auto-post the entry
            await self.accounting_svc.post_journal_entry(entry.id, user_id, tenant_id)
            
            return entry
            
        except Exception as e:
            logger.error(f"Failed to create accounting entry for stock move: {e}")
            return None
    
    async def _create_stock_in_entry(
        self,
        stock_move: StockMove,
        product: Product,
        accounts: Dict[str, Account],
        tenant_id: UUID
    ) -> List[Dict[str, Any]]:
        """Create journal lines for stock receipt."""
        amount = stock_move.total_cost
        
        if amount == 0:
            return []
        
        inventory_account = accounts.get("inventory")
        gr_ir_account = accounts.get("gr_ir")
        
        if not inventory_account:
            return []
        
        lines = [
            {
                "account_id": inventory_account.id,
                "debit": amount,
                "credit": Decimal("0"),
                "name": f"Stock Receipt: {product.name}"
            }
        ]
        
        # Credit GR/IR or Cash
        credit_account = gr_ir_account or accounts.get("cash")
        if credit_account:
            lines.append({
                "account_id": credit_account.id,
                "debit": Decimal("0"),
                "credit": amount,
                "name": f"Stock Receipt: {product.name}"
            })
        
        return lines
    
    async def _create_stock_out_entry(
        self,
        stock_move: StockMove,
        product: Product,
        accounts: Dict[str, Account],
        tenant_id: UUID
    ) -> List[Dict[str, Any]]:
        """Create journal lines for stock issue."""
        amount = stock_move.total_cost
        
        if amount == 0:
            return []
        
        cogs_account = accounts.get("cogs")
        inventory_account = accounts.get("inventory")
        
        if not cogs_account or not inventory_account:
            return []
        
        return [
            {
                "account_id": cogs_account.id,
                "debit": amount,
                "credit": Decimal("0"),
                "name": f"Cost of Goods Sold: {product.name}"
            },
            {
                "account_id": inventory_account.id,
                "debit": Decimal("0"),
                "credit": amount,
                "name": f"Stock Issue: {product.name}"
            }
        ]
    
    async def _create_adjustment_entry(
        self,
        stock_move: StockMove,
        product: Product,
        accounts: Dict[str, Account],
        tenant_id: UUID
    ) -> List[Dict[str, Any]]:
        """Create journal lines for inventory adjustment."""
        amount = abs(stock_move.total_cost)
        
        if amount == 0:
            return []
        
        inventory_account = accounts.get("inventory")
        gain_loss_account = accounts.get("inventory_gain_loss")
        
        if not inventory_account or not gain_loss_account:
            return []
        
        if stock_move.total_cost > 0:
            # Positive adjustment: Debit inventory, Credit gain
            return [
                {
                    "account_id": inventory_account.id,
                    "debit": amount,
                    "credit": Decimal("0"),
                    "name": f"Inventory Gain: {product.name}"
                },
                {
                    "account_id": gain_loss_account.id,
                    "debit": Decimal("0"),
                    "credit": amount,
                    "name": f"Inventory Gain: {product.name}"
                }
            ]
        else:
            # Negative adjustment: Debit loss, Credit inventory
            return [
                {
                    "account_id": gain_loss_account.id,
                    "debit": amount,
                    "credit": Decimal("0"),
                    "name": f"Inventory Loss: {product.name}"
                },
                {
                    "account_id": inventory_account.id,
                    "debit": Decimal("0"),
                    "credit": amount,
                    "name": f"Inventory Loss: {product.name}"
                }
            ]
    
    async def _create_loss_entry(
        self,
        stock_move: StockMove,
        product: Product,
        accounts: Dict[str, Account],
        tenant_id: UUID
    ) -> List[Dict[str, Any]]:
        """Create journal lines for stock loss."""
        amount = stock_move.total_cost
        
        if amount == 0:
            return []
        
        loss_account = accounts.get("inventory_loss")
        inventory_account = accounts.get("inventory")
        
        if not loss_account or not inventory_account:
            return []
        
        return [
            {
                "account_id": loss_account.id,
                "debit": amount,
                "credit": Decimal("0"),
                "name": f"Stock Loss: {product.name}"
            },
            {
                "account_id": inventory_account.id,
                "debit": Decimal("0"),
                "credit": amount,
                "name": f"Stock Loss: {product.name}"
            }
        ]
    
    async def _get_stock_accounts(
        self,
        product: Product,
        tenant_id: UUID
    ) -> Dict[str, Account]:
        """
        Get accounts for stock-related transactions.
        
        Priority: Product accounts > Category accounts > Default accounts
        """
        accounts = {}
        
        # Get default accounts
        default_accounts = await self.accounting_svc.get_or_create_default_accounts(tenant_id)
        
        # Inventory account
        if product.asset_account_id:
            accounts["inventory"] = await self._tenant_record(Account, product.asset_account_id, tenant_id, "Account")
        elif product.category and product.category.asset_account_id:
            accounts["inventory"] = await self._tenant_record(Account, product.category.asset_account_id, tenant_id, "Account")
        else:
            accounts["inventory"] = default_accounts.get("1200")  # Inventory
        
        # COGS account
        if product.expense_account_id:
            accounts["cogs"] = await self._tenant_record(Account, product.expense_account_id, tenant_id, "Account")
        elif product.category and product.category.expense_account_id:
            accounts["cogs"] = await self._tenant_record(Account, product.category.expense_account_id, tenant_id, "Account")
        else:
            accounts["cogs"] = default_accounts.get("5000")  # COGS
        
        # Revenue account
        if product.income_account_id:
            accounts["revenue"] = await self._tenant_record(Account, product.income_account_id, tenant_id, "Account")
        elif product.category and product.category.income_account_id:
            accounts["revenue"] = await self._tenant_record(Account, product.category.income_account_id, tenant_id, "Account")
        else:
            accounts["revenue"] = default_accounts.get("4000")  # Sales Revenue
        
        # Additional accounts
        accounts["cash"] = default_accounts.get("1000")  # Cash
        accounts["payable"] = default_accounts.get("2000")  # AP
        accounts["gr_ir"] = default_accounts.get("1900") if "1900" in default_accounts else None
        
        # Get or create inventory gain/loss account
        gain_loss = await self.accounting_svc.get_account_by_code("1290", tenant_id)
        if not gain_loss:
            gain_loss = await self.accounting_svc.create_account(
                code="1290",
                name="Inventory Gain/Loss",
                account_type=AccountType.EXPENSE,
                category=AccountCategory.OPERATING_EXPENSE,
                tenant_id=tenant_id
            )
        accounts["inventory_gain_loss"] = gain_loss
        accounts["inventory_loss"] = gain_loss
        
        return accounts
    
    # ========================================
    # Sales Integration
    # ========================================
    
    async def process_sale_accounting(
        self,
        invoice_id: UUID,
        tenant_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Optional[JournalEntry]:
        """
        Create accounting entries for a sales invoice.
        
        This includes:
        - Revenue recognition (Debit: AR, Credit: Revenue)
        - Tax payable entry
        - COGS entry when goods are delivered
        
        Args:
            invoice_id: Invoice ID
            tenant_id: Tenant ID
            user_id: User ID
            
        Returns:
            Created journal entry
        """
        from app.models.sales import Invoice, InvoiceLine, InvoiceType, InvoiceState
        
        # Get invoice
        invoice = await self._tenant_record(Invoice, invoice_id, tenant_id, "Invoice")
        if not invoice or invoice.state != InvoiceState.POSTED:
            logger.warning(f"Invoice {invoice_id} not found or not posted")
            return None
        existing_entry = await self._existing_source_entry("invoice", invoice.id, tenant_id)
        if existing_entry:
            return existing_entry
        
        # Skip if already has journal entry
        if invoice.journal_entry_id:
            logger.info(f"Invoice {invoice_id} already has journal entry")
            return None
        
        # Get accounts
        partner = await self._tenant_record(Partner, invoice.partner_id, tenant_id, "Partner")
        
        # Get receivable account
        receivable_account_id = None
        if partner and partner.receivable_account_id:
            receivable_account_id = partner.receivable_account_id
        else:
            receivable_account = await self.accounting_svc.get_account_by_code("1300", tenant_id)
            receivable_account_id = receivable_account.id if receivable_account else None
        
        # Get default accounts
        default_accounts = await self.accounting_svc.get_or_create_default_accounts(tenant_id)
        tax_payable_account = default_accounts.get("2300")  # Sales Tax Payable
        
        # Build journal lines
        lines = []
        
        # 1. Debit Accounts Receivable
        if receivable_account_id:
            lines.append({
                "account_id": receivable_account_id,
                "debit": invoice.amount_total,
                "credit": Decimal("0"),
                "partner_id": invoice.partner_id,
                "partner_type": "customer",
                "name": f"Invoice {invoice.number}"
            })
        
        # 2. Credit Revenue accounts (by line)
        revenue_by_account = {}
        for line in invoice.lines:
            account_id = line.account_id
            if account_id not in revenue_by_account:
                revenue_by_account[account_id] = Decimal("0")
            revenue_by_account[account_id] += line.subtotal
        
        for account_id, amount in revenue_by_account.items():
            lines.append({
                "account_id": account_id,
                "debit": Decimal("0"),
                "credit": amount,
                "name": f"Revenue - Invoice {invoice.number}"
            })
        
        # 3. Credit Tax Payable
        if invoice.amount_tax > 0 and tax_payable_account:
            lines.append({
                "account_id": tax_payable_account.id,
                "debit": Decimal("0"),
                "credit": invoice.amount_tax,
                "name": f"Tax - Invoice {invoice.number}"
            })
        
        # Create journal entry
        try:
            entry = await self.accounting_svc.create_journal_entry(
                date=invoice.date_posted or invoice.date_invoice,
                lines=lines,
                description=f"Sales Invoice: {invoice.number}",
                ref=invoice.number,
                move_type=MoveType.SALES,
                source_model="invoice",
                source_id=invoice.id,
                tenant_id=tenant_id,
                created_by_id=user_id
            )
            
            # Auto-post
            await self.accounting_svc.post_journal_entry(entry.id, user_id, tenant_id)
            
            # Link to invoice
            invoice.journal_entry_id = entry.id
            await self.db.flush()
            
            logger.info(f"Created journal entry {entry.number} for invoice {invoice.number}")
            return entry
            
        except Exception as e:
            logger.error(f"Failed to create accounting entry for invoice: {e}")
            return None
    
    async def process_cogs_for_sale(
        self,
        sale_order_id: UUID,
        tenant_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Optional[JournalEntry]:
        """
        Create COGS entry for delivered goods from a sale order.
        
        Debit: Cost of Goods Sold
        Credit: Inventory
        
        Args:
            sale_order_id: Sale order ID
            tenant_id: Tenant ID
            user_id: User ID
            
        Returns:
            Created journal entry
        """
        from app.models.sales import SaleOrder, SaleOrderLine
        
        order = await self._tenant_record(SaleOrder, sale_order_id, tenant_id, "Sales order")
        if not order:
            return None
        
        lines = []
        total_cogs = Decimal("0")
        
        for line in order.lines:
            if not line.product_id:
                continue
            
            product = await self._tenant_record(Product, line.product_id, tenant_id, "Product")
            if not product or not product.is_stockable:
                continue
            
            # Calculate COGS
            cost = product.average_cost or product.cost_price
            cogs_amount = cost * line.quantity_delivered
            
            if cogs_amount <= 0:
                continue
            
            total_cogs += cogs_amount
            
            # Get accounts
            accounts = await self._get_stock_accounts(product, tenant_id)
            cogs_account = accounts.get("cogs")
            inventory_account = accounts.get("inventory")
            
            if cogs_account and inventory_account:
                lines.extend([
                    {
                        "account_id": cogs_account.id,
                        "debit": cogs_amount,
                        "credit": Decimal("0"),
                        "name": f"COGS: {product.name}"
                    },
                    {
                        "account_id": inventory_account.id,
                        "debit": Decimal("0"),
                        "credit": cogs_amount,
                        "name": f"Inventory: {product.name}"
                    }
                ])
        
        if not lines:
            return None
        
        try:
            entry = await self.accounting_svc.create_journal_entry(
                date=date.today(),
                lines=lines,
                description=f"COGS for Sale Order: {order.number}",
                ref=order.number,
                move_type=MoveType.SALES,
                source_model="sale_order",
                source_id=order.id,
                tenant_id=tenant_id,
                created_by_id=user_id
            )
            
            await self.accounting_svc.post_journal_entry(entry.id, user_id, tenant_id)
            return entry
            
        except Exception as e:
            logger.error(f"Failed to create COGS entry: {e}")
            return None
    
    # ========================================
    # Purchase Integration
    # ========================================
    
    async def process_purchase_accounting(
        self,
        purchase_order_id: UUID,
        receipt_id: UUID,
        tenant_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Optional[JournalEntry]:
        """
        Create accounting entries for a purchase receipt.
        
        This creates:
        - GR/IR entry: Debit Inventory, Credit GR/IR Clearing
        - When invoice is posted: Debit GR/IR, Credit AP
        
        Args:
            purchase_order_id: Purchase order ID
            receipt_id: Receipt ID
            tenant_id: Tenant ID
            user_id: User ID
            
        Returns:
            Created journal entry
        """
        from app.models.purchase import Receipt, ReceiptLine, ReceiptState, PurchaseOrder

        receipt = await self._tenant_record(Receipt, receipt_id, tenant_id, "Receipt")
        if not receipt:
            logger.error(f"Receipt {receipt_id} not found")
            return None
        if receipt.state != ReceiptState.DONE:
            raise ValueError("Purchase receipt must be completed before accounting")
        if receipt.purchase_order_id is not None:
            purchase_order = await self._tenant_record(
                PurchaseOrder, receipt.purchase_order_id, tenant_id, "Purchase order"
            )
            if purchase_order_id != purchase_order.id:
                raise ValueError("Receipt does not belong to the supplied purchase order")
        elif purchase_order_id is not None:
            raise ValueError("Receipt is not linked to the supplied purchase order")
        existing_entry = await self._existing_source_entry("receipt", receipt.id, tenant_id)
        if existing_entry:
            return existing_entry
        
        # Get accounts
        default_accounts = await self.accounting_svc.get_or_create_default_accounts(tenant_id)
        
        # GR/IR account (Goods Received/Invoice Received clearing)
        gr_ir_account = default_accounts.get("1900")
        if not gr_ir_account:
            gr_ir_account = await self.accounting_svc.get_account_by_code("1900", tenant_id)
        
        # Fetch receipt lines explicitly within the tenant boundary; do not rely on
        # an implicitly lazy-loaded relationship for financial source documents.
        receipt_lines_result = await self.db.execute(select(ReceiptLine).where(
            ReceiptLine.receipt_id == receipt.id,
            ReceiptLine.tenant_id == tenant_id,
            ReceiptLine.is_deleted == False
        ).order_by(ReceiptLine.sequence))
        receipt_lines = receipt_lines_result.scalars().all()

        # Build journal lines. A stockable receipt must never silently skip
        # inventory or clearing accounts, otherwise the goods receipt could be
        # committed without the corresponding accrual.
        lines = []
        has_stockable_receipt_line = False
        
        for rline in receipt_lines:
            if not rline.product_id:
                continue
            
            product = await self._tenant_record(Product, rline.product_id, tenant_id, "Product")
            if not product or not product.is_stockable:
                continue
            has_stockable_receipt_line = True
            
            # Get cost from stock move
            unit_cost = product.cost_price
            if rline.stock_move_id:
                move = await self._tenant_record(StockMove, rline.stock_move_id, tenant_id, "Stock move")
                if move:
                    unit_cost = move.unit_cost
            
            amount = unit_cost * rline.quantity
            
            if amount <= 0:
                raise ValueError(f"Receipt line for {product.name} has no positive inventory valuation")
            
            # Get inventory account
            accounts = await self._get_stock_accounts(product, tenant_id)
            inventory_account = accounts.get("inventory")
            if inventory_account is None:
                raise ValueError(f"A tenant-owned inventory account is required for {product.name}")
            if gr_ir_account is None:
                raise ValueError("A tenant-owned GR/IR clearing account (1900) is required")
            lines.extend([
                {
                    "account_id": inventory_account.id,
                    "debit": amount,
                    "credit": Decimal("0"),
                    "name": f"Receipt: {product.name}"
                },
                {
                    "account_id": gr_ir_account.id,
                    "debit": Decimal("0"),
                    "credit": amount,
                    "name": f"GR/IR: {product.name}"
                },
            ])
        
        if not lines:
            if has_stockable_receipt_line:
                raise ValueError("Stockable goods receipt did not produce accounting lines")
            return None
        
        try:
            entry = await self.accounting_svc.create_journal_entry(
                date=receipt.date,
                lines=lines,
                description=f"Goods Receipt: {receipt.number}",
                ref=receipt.number,
                move_type=MoveType.PURCHASE,
                source_model="receipt",
                source_id=receipt.id,
                tenant_id=tenant_id,
                created_by_id=user_id
            )
            
            await self.accounting_svc.post_journal_entry(entry.id, user_id, tenant_id)
            
            logger.info(f"Created journal entry {entry.number} for receipt {receipt.number}")
            return entry
            
        except Exception:
            logger.exception("Failed to create accounting entry for receipt %s", receipt.number)
            raise
    
    async def process_vendor_bill_accounting(
        self,
        invoice_id: UUID,
        tenant_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Optional[JournalEntry]:
        """Create and post a balanced journal entry for a vendor bill.

        Bills linked to a completed receipt debit GR/IR. Standalone bills debit
        the expense/inventory accounts selected on their invoice lines.
        """
        from app.models.purchase import (
            PurchaseInvoice, PurchaseInvoiceLine, PurchaseInvoiceState,
            Receipt, ReceiptState,
        )

        invoice = await self._tenant_record(
            PurchaseInvoice, invoice_id, tenant_id, "Purchase invoice"
        )
        if not invoice or invoice.state != PurchaseInvoiceState.POSTED:
            raise ValueError("Purchase invoice must be posted before accounting")

        existing_entry = await self._existing_source_entry(
            "purchase_invoice", invoice.id, tenant_id
        )
        if existing_entry:
            invoice.journal_entry_id = existing_entry.id
            return existing_entry
        if invoice.journal_entry_id:
            linked_entry = await self._tenant_record(
                JournalEntry, invoice.journal_entry_id, tenant_id, "Vendor bill journal entry"
            )
            if linked_entry:
                return linked_entry
            raise ValueError("Vendor bill references a missing or foreign journal entry")

        partner = await self._tenant_record(
            Partner, invoice.partner_id, tenant_id, "Supplier"
        )
        if partner is None:
            raise ValueError("Vendor bill supplier is unavailable")

        line_result = await self.db.execute(select(PurchaseInvoiceLine).where(
            PurchaseInvoiceLine.invoice_id == invoice.id,
            PurchaseInvoiceLine.tenant_id == tenant_id,
            PurchaseInvoiceLine.is_deleted == False,
        ).order_by(PurchaseInvoiceLine.sequence))
        invoice_lines = list(line_result.scalars().all())
        if not invoice_lines:
            raise ValueError("Vendor bill has no active invoice lines")

        # Resolve all accounting references inside the active tenant.
        payable = None
        if partner.payable_account_id:
            payable = await self._tenant_record(
                Account, partner.payable_account_id, tenant_id, "Payables account"
            )
        if payable is None and invoice.account_id:
            payable = await self._tenant_record(
                Account, invoice.account_id, tenant_id, "Payables account"
            )
        if payable is None:
            payable = await self.accounting_svc.get_account_by_code("2000", tenant_id)
        if payable is None:
            raise ValueError("A tenant-owned accounts-payable account is required")

        debit_by_account: Dict[UUID, Decimal] = {}
        if invoice.receipt_id:
            receipt = await self._tenant_record(
                Receipt, invoice.receipt_id, tenant_id, "Receipt"
            )
            if receipt is None or receipt.state != ReceiptState.DONE:
                raise ValueError("A linked receipt must be completed before vendor bill posting")
            if receipt.partner_id != invoice.partner_id:
                raise ValueError("Receipt supplier does not match vendor bill")
            if invoice.purchase_order_id and receipt.purchase_order_id != invoice.purchase_order_id:
                raise ValueError("Receipt and vendor bill purchase orders do not match")
            gr_ir = await self.accounting_svc.get_account_by_code("1900", tenant_id)
            if gr_ir is None:
                raise ValueError("A tenant-owned GR/IR clearing account (1900) is required")
            debit_by_account[gr_ir.id] = Decimal(str(invoice.amount_untaxed))
        else:
            for line in invoice_lines:
                if line.account_id is None:
                    raise ValueError(f"Vendor bill line {line.id} has no debit account")
                account = await self._tenant_record(
                    Account, line.account_id, tenant_id, "Vendor bill line account"
                )
                debit_by_account[account.id] = debit_by_account.get(
                    account.id, Decimal("0")
                ) + Decimal(str(line.subtotal))

        journal_lines: List[Dict[str, Any]] = []
        for account_id, amount in debit_by_account.items():
            if amount < 0:
                raise ValueError("Vendor bill debit amounts cannot be negative")
            if amount:
                journal_lines.append({
                    "account_id": account_id,
                    "debit": amount,
                    "credit": Decimal("0"),
                    "name": f"Vendor Bill: {invoice.number}",
                })

        tax_amount = Decimal(str(invoice.amount_tax or 0))
        if tax_amount < 0:
            raise ValueError("Vendor bill tax cannot be negative")
        if tax_amount:
            tax_account = await self.accounting_svc.get_account_by_code("1400", tenant_id)
            if tax_account is None:
                raise ValueError("A tenant-owned recoverable-tax account (1400) is required")
            journal_lines.append({
                "account_id": tax_account.id,
                "debit": tax_amount,
                "credit": Decimal("0"),
                "name": f"Recoverable tax: {invoice.number}",
            })

        total = Decimal(str(invoice.amount_total))
        journal_lines.append({
            "account_id": payable.id,
            "debit": Decimal("0"),
            "credit": total,
            "partner_id": invoice.partner_id,
            "partner_type": "supplier",
            "name": f"Accounts payable: {invoice.number}",
        })
        if not self._journal_lines_are_balanced(journal_lines):
            raise ValueError(
                "Vendor bill journal is not balanced; verify line totals, tax, GR/IR and payable setup"
            )

        entry = await self.accounting_svc.create_journal_entry(
            date=invoice.date_posted or invoice.date_invoice,
            lines=journal_lines,
            description=f"Vendor Bill: {invoice.number}",
            ref=invoice.supplier_invoice_number or invoice.number,
            move_type=MoveType.PURCHASE,
            source_model="purchase_invoice",
            source_id=invoice.id,
            tenant_id=tenant_id,
            created_by_id=user_id,
        )
        await self.accounting_svc.post_journal_entry(entry.id, user_id, tenant_id)
        invoice.journal_entry_id = entry.id
        await self.db.flush()
        logger.info("Created journal entry %s for vendor bill %s", entry.number, invoice.number)
        return entry

    # ========================================
    # Event Handlers
    # ========================================
    
    async def on_stock_move_processed(
        self,
        move_id: UUID,
        tenant_id: UUID,
        user_id: Optional[UUID] = None
    ):
        """
        Event handler called when a stock move is processed.
        
        This is the main integration point for inventory-to-accounting.
        
        Args:
            move_id: Stock move ID
            tenant_id: Tenant ID
            user_id: User ID
        """
        stock_move = await self._tenant_record(StockMove, move_id, tenant_id, "Stock move")
        if not stock_move:
            logger.error(f"Stock move {move_id} not found")
            return
        
        # Create accounting entry
        entry = await self.process_stock_movement_accounting(
            stock_move, tenant_id, user_id
        )
        
        if entry:
            logger.info(
                f"Created journal entry {entry.number} for stock move {stock_move.number}"
            )
    
    async def on_product_created(
        self,
        product_id: UUID,
        tenant_id: UUID
    ):
        """
        Event handler called when a product is created.
        
        Ensures the product has appropriate account links.
        
        Args:
            product_id: Product ID
            tenant_id: Tenant ID
        """
        product = await self._tenant_record(Product, product_id, tenant_id, "Product")
        if not product:
            return
        
        # Get default accounts if not set
        if product.is_stockable:
            accounts = await self._get_stock_accounts(product, tenant_id)
            
            if not product.asset_account_id and accounts.get("inventory"):
                product.asset_account_id = accounts["inventory"].id
            
            if not product.expense_account_id and accounts.get("cogs"):
                product.expense_account_id = accounts["cogs"].id
            
            if not product.income_account_id and accounts.get("revenue"):
                product.income_account_id = accounts["revenue"].id
            
            await self.db.flush()
    
    # ========================================
    # Manufacturing Integration
    # ========================================
    
    async def process_manufacturing_accounting(
        self,
        mo_id: UUID,
        tenant_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Optional[JournalEntry]:
        """
        Create accounting entries for manufacturing order.
        
        This creates:
        1. Material consumption entry (Debit: WIP - Credit: Inventory)
        2. Finished goods entry (Debit: Inventory - Credit: WIP)
        
        Args:
            mo_id: Manufacturing order ID
            tenant_id: Tenant ID
            user_id: User ID
            
        Returns:
            Created journal entry
        """
        from app.models.manufacturing import ManufacturingOrder, MOLine, MOFinish, MOState
        
        if tenant_id is None:
            raise ValueError("tenant_id is required for manufacturing accounting")
        mo = await self.db.scalar(select(ManufacturingOrder).options(
            selectinload(ManufacturingOrder.material_lines),
            selectinload(ManufacturingOrder.finished_lines)
        ).where(
            ManufacturingOrder.id == mo_id,
            ManufacturingOrder.tenant_id == tenant_id,
            ManufacturingOrder.is_deleted == False
        ))
        if not mo or mo.state != MOState.DONE:
            logger.warning(f"MO {mo_id} not found or not completed")
            return None
        existing_entry = await self._existing_source_entry("manufacturing_order", mo.id, tenant_id)
        if existing_entry:
            logger.info("Accounting entry already exists for manufacturing order %s", mo.id)
            return existing_entry
        
        default_accounts = await self.accounting_svc.get_or_create_default_accounts(tenant_id)
        
        # Get WIP (Work in Progress) account
        wip_account = await self.accounting_svc.get_account_by_code("1400", tenant_id)
        if not wip_account:
            # Create WIP account if not exists
            from app.models.accounting import AccountType, AccountCategory
            wip_account = await self.accounting_svc.create_account(
                code="1400",
                name="Work in Progress",
                account_type=AccountType.ASSET,
                category=AccountCategory.INVENTORY,
                tenant_id=tenant_id
            )
        
        # Build journal lines
        lines = []
        
        # 1. Material consumption entry
        for material_line in mo.material_lines:
            if material_line.total_cost <= 0:
                continue
            
            product = await self._tenant_record(Product, material_line.product_id, tenant_id, "Product")
            accounts = await self._get_stock_accounts(product, tenant_id) if product else {}
            inventory_account = accounts.get("inventory")
            
            if inventory_account and wip_account:
                # Debit WIP
                lines.append({
                    "account_id": wip_account.id,
                    "debit": material_line.total_cost,
                    "credit": Decimal("0"),
                    "name": f"Material: {product.name if product else 'Unknown'}"
                })
                
                # Credit Inventory
                lines.append({
                    "account_id": inventory_account.id,
                    "debit": Decimal("0"),
                    "credit": material_line.total_cost,
                    "name": f"Material consumed: {product.name if product else 'Unknown'}"
                })
        
        # 2. Labor and overhead costs
        if mo.labor_cost > 0:
            labor_account = default_accounts.get("6000")  # Labor expense
            
            lines.append({
                "account_id": wip_account.id,
                "debit": mo.labor_cost,
                "credit": Decimal("0"),
                "name": "Labor cost applied"
            })
            
            if labor_account:
                lines.append({
                    "account_id": labor_account.id,
                    "debit": Decimal("0"),
                    "credit": mo.labor_cost,
                    "name": "Labor cost"
                })
        
        if mo.overhead_cost > 0:
            overhead_account = default_accounts.get("6100")  # Overhead
            
            lines.append({
                "account_id": wip_account.id,
                "debit": mo.overhead_cost,
                "credit": Decimal("0"),
                "name": "Overhead applied"
            })
            
            if overhead_account:
                lines.append({
                    "account_id": overhead_account.id,
                    "debit": Decimal("0"),
                    "credit": mo.overhead_cost,
                    "name": "Manufacturing overhead"
                })
        
        # 3. Finished goods entry
        for finish_line in mo.finished_lines:
            if finish_line.total_cost <= 0:
                continue
            
            product = await self._tenant_record(Product, finish_line.product_id, tenant_id, "Product")
            accounts = await self._get_stock_accounts(product, tenant_id) if product else {}
            finished_goods_account = accounts.get("inventory")
            
            if finished_goods_account and wip_account:
                # Debit Finished Goods Inventory
                lines.append({
                    "account_id": finished_goods_account.id,
                    "debit": finish_line.total_cost,
                    "credit": Decimal("0"),
                    "name": f"Finished goods: {product.name if product else 'Unknown'}"
                })
                
                # Credit WIP
                lines.append({
                    "account_id": wip_account.id,
                    "debit": Decimal("0"),
                    "credit": finish_line.total_cost,
                    "name": f"Production completed: {product.name if product else 'Unknown'}"
                })
        
        if not lines:
            return None
        if not self._journal_lines_are_balanced(lines):
            logger.error("Refusing unbalanced manufacturing journal for %s", mo.id)
            return None
        
        try:
            entry = await self.accounting_svc.create_journal_entry(
                date=mo.date_finished.date() if mo.date_finished else date.today(),
                lines=lines,
                description=f"Manufacturing Order: {mo.number}",
                ref=mo.number,
                move_type=MoveType.ADJUSTMENT,
                source_model="manufacturing_order",
                source_id=mo.id,
                tenant_id=tenant_id,
                created_by_id=user_id
            )
            
            await self.accounting_svc.post_journal_entry(entry.id, user_id, tenant_id)
            
            logger.info(f"Created journal entry {entry.number} for MO {mo.number}")
            return entry
            
        except Exception as e:
            logger.error(f"Failed to create accounting entry for MO: {e}")
            return None
    
    # ========================================
    # Reconciliation Helpers
    # ========================================
    
    async def reconcile_stock_and_accounts(
        self,
        warehouse_id: Optional[UUID] = None,
        tenant_id: UUID = None
    ) -> Dict[str, Any]:
        """
        Reconcile stock quantities with accounting balances.
        
        Compares inventory account balance with sum of stock values.
        
        Args:
            warehouse_id: Filter by warehouse (optional)
            tenant_id: Tenant ID
            
        Returns:
            Reconciliation report
        """
        # Get inventory account balance
        inventory_account = await self.accounting_svc.get_account_by_code("1200", tenant_id)
        
        account_balance = Decimal("0")
        if inventory_account:
            account_balance = inventory_account.balance
        
        # Get stock value
        stock_valuation = await self.inventory_svc.get_stock_valuation_report(
            warehouse_id=warehouse_id,
            tenant_id=tenant_id
        )
        
        stock_value = sum(
            Decimal(str(item.get("value", 0))) 
            for item in stock_valuation
        )
        
        difference = account_balance - stock_value
        
        return {
            "inventory_account_balance": account_balance,
            "stock_value": stock_value,
            "difference": difference,
            "is_reconciled": abs(difference) < Decimal("0.01"),
            "stock_details": stock_valuation[:10],  # First 10 items
            "generated_at": datetime.utcnow()
        }
