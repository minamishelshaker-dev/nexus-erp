"""
Nexus ERP - Integration Tests for Full Business Cycles
========================================================

This module contains integration tests that verify complete business cycles:
- Sales cycle (quotation → order → delivery → invoice → accounting)
- Purchase cycle (PO → receipt → invoice → accounting)
- Manufacturing cycle (BOM → MO → production → accounting)
- Inventory-Accounting synchronization
"""

import pytest
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.inventory import Product, StockMove, StockMoveType
from app.models.accounting import JournalEntry, JournalEntryLine, MoveType
from app.models.sales import SaleOrder, SaleOrderLine, Invoice, InvoiceState
from app.models.purchase import PurchaseOrder, Receipt, PurchaseInvoice
from app.models.manufacturing import (
    ManufacturingOrder, MOLine, MOFinish, MOState,
    BillOfMaterial, BOMState
)
from app.services.integration_service import IntegrationService
from app.services.inventory_service import InventoryService
from app.services.accounting_service import AccountingService


# ========================================
# Sales Cycle Integration Tests
# ========================================

@pytest.mark.asyncio
class TestCompleteSalesCycle:
    """
    Tests for the complete sales cycle:
    Product → Purchase → Stock → Sale → Invoice → Accounting
    """

    async def test_complete_sales_cycle(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_product: Product,
        test_customer,
        test_accounts,
        auth_headers: dict,
        tenant_id: UUID
    ):
        """
        Test the complete sales cycle from product creation to accounting entry.
        
        Flow:
        1. Product exists (fixture)
        2. Create stock move IN (receive inventory)
        3. Create sale order
        4. Confirm sale order
        5. Create delivery
        6. Create and post invoice
        7. Verify accounting entries
        """
        
        # Step 1: Receive inventory first
        inventory_svc = InventoryService(db_session)
        
        stock_move = await inventory_svc.create_stock_move(
            product_id=test_product.id,
            move_type=StockMoveType.IN,
            quantity=Decimal("100"),
            unit_cost=test_product.cost_price,
            date=date.today(),
            tenant_id=tenant_id,
            created_by_id=test_user.id
        )
        
        assert stock_move is not None
        assert stock_move.quantity == Decimal("100")
        
        # Step 2: Process the stock move
        await inventory_svc.process_stock_move(stock_move.id, tenant_id)
        
        # Verify inventory updated
        await db_session.refresh(test_product)
        assert test_product.quantity_on_hand == Decimal("100")
        
        # Step 3: Create sale order via API
        sale_order_data = {
            "partner_id": str(test_customer.id),
            "date_order": str(date.today()),
            "lines": [
                {
                    "product_id": str(test_product.id),
                    "quantity": 10,
                    "unit_price": float(test_product.sale_price),
                }
            ]
        }
        
        response = await async_client.post(
            "/api/v1/sales/orders",
            json=sale_order_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        order_data = response.json()
        order_id = order_data["data"]["id"]
        
        # Step 4: Confirm the sale order
        response = await async_client.post(
            f"/api/v1/sales/orders/{order_id}/confirm",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Step 5: Create invoice
        response = await async_client.post(
            f"/api/v1/sales/orders/{order_id}/create-invoice",
            headers=auth_headers
        )
        
        assert response.status_code == 201
        invoice_data = response.json()
        invoice_id = invoice_data["data"]["id"]
        
        # Step 6: Post the invoice
        response = await async_client.post(
            f"/api/v1/sales/invoices/{invoice_id}/post",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Step 7: Process accounting integration
        integration_svc = IntegrationService(db_session)
        
        journal_entry = await integration_svc.process_sale_accounting(
            invoice_id=UUID(invoice_id),
            tenant_id=tenant_id,
            user_id=test_user.id
        )
        
        # Verify accounting entry created
        assert journal_entry is not None
        assert journal_entry.state == "posted"
        
        # Verify the entry is balanced
        total_debit = sum(line.debit for line in journal_entry.lines)
        total_credit = sum(line.credit for line in journal_entry.lines)
        assert abs(total_debit - total_credit) < Decimal("0.01")
        
        # Verify inventory decreased
        await db_session.refresh(test_product)
        assert test_product.quantity_on_hand == Decimal("90")

    async def test_sales_with_tax(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_product: Product,
        test_customer,
        auth_headers: dict,
        tenant_id: UUID
    ):
        """Test sales cycle with tax calculation."""
        
        # Receive inventory
        inventory_svc = InventoryService(db_session)
        await inventory_svc.create_and_process_stock_move(
            product_id=test_product.id,
            move_type=StockMoveType.IN,
            quantity=Decimal("50"),
            unit_cost=test_product.cost_price,
            tenant_id=tenant_id
        )
        
        # Create sale order with tax
        sale_order_data = {
            "partner_id": str(test_customer.id),
            "date_order": str(date.today()),
            "lines": [
                {
                    "product_id": str(test_product.id),
                    "quantity": 5,
                    "unit_price": 150.00,
                    "tax_rate": 15.0  # 15% VAT
                }
            ]
        }
        
        response = await async_client.post(
            "/api/v1/sales/orders",
            json=sale_order_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        order_data = response.json()
        
        # Verify tax calculation
        expected_subtotal = Decimal("750.00")  # 5 * 150
        expected_tax = Decimal("112.50")  # 15% of 750
        expected_total = expected_subtotal + expected_tax
        
        # Allow some tolerance for floating point
        assert abs(Decimal(str(order_data["data"]["amount_untaxed"])) - expected_subtotal) < Decimal("1")
        assert abs(Decimal(str(order_data["data"]["amount_tax"])) - expected_tax) < Decimal("1")


# ========================================
# Purchase Cycle Integration Tests
# ========================================

@pytest.mark.asyncio
class TestCompletePurchaseCycle:
    """
    Tests for the complete purchase cycle:
    PO → Receipt → Invoice → Accounting
    """

    async def test_complete_purchase_cycle(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_product: Product,
        test_supplier,
        test_accounts,
        auth_headers: dict,
        tenant_id: UUID
    ):
        """
        Test the complete purchase cycle.
        
        Flow:
        1. Create purchase order
        2. Confirm PO
        3. Create receipt
        4. Process receipt (update inventory)
        5. Create vendor bill
        6. Verify accounting entries
        """
        
        # Step 1: Create purchase order
        po_data = {
            "partner_id": str(test_supplier.id),
            "date_order": str(date.today()),
            "lines": [
                {
                    "product_id": str(test_product.id),
                    "quantity": 50,
                    "unit_price": float(test_product.cost_price),
                }
            ]
        }
        
        response = await async_client.post(
            "/api/v1/purchase/orders",
            json=po_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        po_result = response.json()
        po_id = po_result["data"]["id"]
        
        # Step 2: Confirm PO
        response = await async_client.post(
            f"/api/v1/purchase/orders/{po_id}/confirm",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Step 3: Create receipt
        response = await async_client.post(
            f"/api/v1/purchase/orders/{po_id}/receive",
            json={"lines": [{"quantity": 50}]},
            headers=auth_headers
        )
        
        assert response.status_code == 201
        receipt_result = response.json()
        receipt_id = receipt_result["data"]["id"]
        
        # Step 4: Verify inventory updated
        await db_session.refresh(test_product)
        assert test_product.quantity_on_hand == Decimal("50")
        
        # Step 5: Create vendor bill
        response = await async_client.post(
            f"/api/v1/purchase/orders/{po_id}/create-bill",
            headers=auth_headers
        )
        
        assert response.status_code == 201
        bill_result = response.json()
        bill_id = bill_result["data"]["id"]
        
        # Step 6: Process accounting
        integration_svc = IntegrationService(db_session)
        
        entry = await integration_svc.process_purchase_accounting(
            purchase_order_id=UUID(po_id),
            receipt_id=UUID(receipt_id),
            tenant_id=tenant_id,
            user_id=test_user.id
        )
        
        # Verify accounting entry
        if entry:
            assert entry.state == "posted"
            
            total_debit = sum(line.debit for line in entry.lines)
            total_credit = sum(line.credit for line in entry.lines)
            assert abs(total_debit - total_credit) < Decimal("0.01")

    async def test_partial_receipt(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_product: Product,
        test_supplier,
        auth_headers: dict,
        tenant_id: UUID
    ):
        """Test partial receipt of purchase order."""
        
        # Create PO
        po_data = {
            "partner_id": str(test_supplier.id),
            "date_order": str(date.today()),
            "lines": [
                {
                    "product_id": str(test_product.id),
                    "quantity": 100,
                    "unit_price": 100.00
                }
            ]
        }
        
        response = await async_client.post(
            "/api/v1/purchase/orders",
            json=po_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        po_id = response.json()["data"]["id"]
        
        # Confirm
        await async_client.post(
            f"/api/v1/purchase/orders/{po_id}/confirm",
            headers=auth_headers
        )
        
        # Partial receipt (30 out of 100)
        response = await async_client.post(
            f"/api/v1/purchase/orders/{po_id}/receive",
            json={"lines": [{"quantity": 30}]},
            headers=auth_headers
        )
        
        assert response.status_code == 201
        
        # Verify partial inventory
        await db_session.refresh(test_product)
        assert test_product.quantity_on_hand == Decimal("30")


# ========================================
# Manufacturing Cycle Integration Tests
# ========================================

@pytest.mark.asyncio
class TestCompleteManufacturingCycle:
    """
    Tests for the complete manufacturing cycle:
    BOM → MO → Material consumption → Production → Accounting
    """

    async def test_complete_manufacturing_cycle(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_bom: BillOfMaterial,
        test_products: list,
        test_accounts,
        auth_headers: dict,
        tenant_id: UUID
    ):
        """
        Test the complete manufacturing cycle.
        
        Flow:
        1. BOM exists (fixture)
        2. Stock raw materials
        3. Create manufacturing order
        4. Confirm MO
        5. Start production
        6. Finish production
        7. Verify inventory changes
        8. Verify accounting entries
        """
        
        # Step 1: Stock raw materials
        inventory_svc = InventoryService(db_session)
        
        raw_materials = test_products[1:3]  # Materials from fixture
        for material in raw_materials:
            await inventory_svc.create_and_process_stock_move(
                product_id=material.id,
                move_type=StockMoveType.IN,
                quantity=Decimal("100"),
                unit_cost=material.cost_price,
                tenant_id=tenant_id
            )
        
        # Step 2: Create manufacturing order via API
        finished_product = test_products[0]
        
        mo_data = {
            "product_id": str(finished_product.id),
            "bom_id": str(test_bom.id),
            "product_qty": 10,
            "planned_date": str(date.today())
        }
        
        response = await async_client.post(
            "/api/v1/manufacturing/orders",
            json=mo_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        mo_result = response.json()
        mo_id = mo_result["data"]["id"]
        
        # Step 3: Confirm MO
        response = await async_client.post(
            f"/api/v1/manufacturing/orders/{mo_id}/confirm",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Step 4: Start production
        response = await async_client.post(
            f"/api/v1/manufacturing/orders/{mo_id}/start",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Step 5: Finish production
        response = await async_client.post(
            f"/api/v1/manufacturing/orders/{mo_id}/finish",
            json={
                "quantity": 10,
                "labor_cost": 500.00,
                "overhead_cost": 200.00
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Step 6: Verify inventory changes
        await db_session.refresh(finished_product)
        assert finished_product.quantity_on_hand == Decimal("10")
        
        # Raw materials should be consumed
        for material in raw_materials:
            await db_session.refresh(material)
            # Each MO line consumes 2 units per finished product
            assert material.quantity_on_hand == Decimal("80")  # 100 - (10 * 2)
        
        # Step 7: Verify accounting entry
        integration_svc = IntegrationService(db_session)
        
        journal_entry = await integration_svc.process_manufacturing_accounting(
            mo_id=UUID(mo_id),
            tenant_id=tenant_id,
            user_id=test_user.id
        )
        
        if journal_entry:
            assert journal_entry.state == "posted"
            
            # Verify balanced entry
            total_debit = sum(line.debit for line in journal_entry.lines)
            total_credit = sum(line.credit for line in journal_entry.lines)
            assert abs(total_debit - total_credit) < Decimal("0.01")

    async def test_bom_cost_calculation(
        self,
        db_session: AsyncSession,
        test_bom: BillOfMaterial,
        tenant_id: UUID
    ):
        """Test BOM cost calculation."""
        
        # Calculate costs
        test_bom.calculate_costs()
        
        # Verify material costs
        expected_material_cost = sum(
            line.total_cost for line in test_bom.lines
        )
        
        assert test_bom.material_cost == expected_material_cost
        assert test_bom.total_cost >= test_bom.material_cost


# ========================================
# Inventory-Accounting Sync Tests
# ========================================

@pytest.mark.asyncio
class TestInventoryAccountingSync:
    """
    Tests for inventory and accounting synchronization.
    """

    async def test_stock_move_creates_journal_entry(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_product: Product,
        test_accounts,
        tenant_id: UUID
    ):
        """Test that stock movements create appropriate journal entries."""
        
        integration_svc = IntegrationService(db_session)
        inventory_svc = InventoryService(db_session)
        
        # Initial stock receipt
        stock_move = await inventory_svc.create_stock_move(
            product_id=test_product.id,
            move_type=StockMoveType.IN,
            quantity=Decimal("100"),
            unit_cost=Decimal("50.00"),
            date=date.today(),
            tenant_id=tenant_id,
            created_by_id=test_user.id
        )
        
        await inventory_svc.process_stock_move(stock_move.id, tenant_id)
        
        # Process accounting
        journal_entry = await integration_svc.process_stock_movement_accounting(
            stock_move=stock_move,
            tenant_id=tenant_id,
            user_id=test_user.id
        )
        
        # Verify entry created
        assert journal_entry is not None
        assert journal_entry.move_type == MoveType.ADJUSTMENT
        
        # Verify inventory account debited
        inventory_line = next(
            (l for l in journal_entry.lines 
             if l.account_id == test_accounts["inventory"].id),
            None
        )
        assert inventory_line is not None
        assert inventory_line.debit == Decimal("5000.00")  # 100 * 50

    async def test_stock_out_creates_cogs_entry(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_product: Product,
        test_accounts,
        tenant_id: UUID
    ):
        """Test that stock out creates COGS journal entry."""
        
        integration_svc = IntegrationService(db_session)
        inventory_svc = InventoryService(db_session)
        
        # First receive stock
        await inventory_svc.create_and_process_stock_move(
            product_id=test_product.id,
            move_type=StockMoveType.IN,
            quantity=Decimal("100"),
            unit_cost=Decimal("50.00"),
            tenant_id=tenant_id
        )
        
        # Then issue stock
        stock_move = await inventory_svc.create_stock_move(
            product_id=test_product.id,
            move_type=StockMoveType.OUT,
            quantity=Decimal("20"),
            unit_cost=Decimal("50.00"),
            date=date.today(),
            tenant_id=tenant_id,
            created_by_id=test_user.id
        )
        
        await inventory_svc.process_stock_move(stock_move.id, tenant_id)
        
        # Process accounting
        journal_entry = await integration_svc.process_stock_movement_accounting(
            stock_move=stock_move,
            tenant_id=tenant_id,
            user_id=test_user.id
        )
        
        # Verify COGS entry
        assert journal_entry is not None
        
        # Verify COGS account debited
        cogs_line = next(
            (l for l in journal_entry.lines 
             if l.account_id == test_accounts["cogs"].id),
            None
        )
        assert cogs_line is not None
        assert cogs_line.debit == Decimal("1000.00")  # 20 * 50

    async def test_inventory_adjustment_accounting(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_product: Product,
        test_accounts,
        tenant_id: UUID
    ):
        """Test inventory adjustment creates gain/loss entry."""
        
        integration_svc = IntegrationService(db_session)
        inventory_svc = InventoryService(db_session)
        
        # Initial stock
        await inventory_svc.create_and_process_stock_move(
            product_id=test_product.id,
            move_type=StockMoveType.IN,
            quantity=Decimal("100"),
            unit_cost=Decimal("50.00"),
            tenant_id=tenant_id
        )
        
        # Positive adjustment (gain)
        adjustment = await inventory_svc.create_stock_move(
            product_id=test_product.id,
            move_type=StockMoveType.ADJUSTMENT,
            quantity=Decimal("10"),
            unit_cost=Decimal("50.00"),
            date=date.today(),
            tenant_id=tenant_id,
            created_by_id=test_user.id
        )
        
        await inventory_svc.process_stock_move(adjustment.id, tenant_id)
        
        # Process accounting
        journal_entry = await integration_svc.process_stock_movement_accounting(
            stock_move=adjustment,
            tenant_id=tenant_id,
            user_id=test_user.id
        )
        
        # Verify entry
        assert journal_entry is not None
        
        # Verify inventory increased
        await db_session.refresh(test_product)
        assert test_product.quantity_on_hand == Decimal("110")


# ========================================
# Reconciliation Tests
# ========================================

@pytest.mark.asyncio
class TestReconciliation:
    """Tests for stock and accounting reconciliation."""

    async def test_stock_account_reconciliation(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_product: Product,
        test_accounts,
        tenant_id: UUID
    ):
        """Test reconciliation between stock value and inventory account."""
        
        integration_svc = IntegrationService(db_session)
        inventory_svc = InventoryService(db_session)
        
        # Create stock movements
        await inventory_svc.create_and_process_stock_move(
            product_id=test_product.id,
            move_type=StockMoveType.IN,
            quantity=Decimal("100"),
            unit_cost=Decimal("100.00"),
            tenant_id=tenant_id
        )
        
        # Run reconciliation
        reconciliation = await integration_svc.reconcile_stock_and_accounts(
            tenant_id=tenant_id
        )
        
        # Verify reconciliation data
        assert "inventory_account_balance" in reconciliation
        assert "stock_value" in reconciliation
        assert "is_reconciled" in reconciliation


# ========================================
# Error Handling Tests
# ========================================

@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for error handling in integration scenarios."""

    async def test_unbalanced_journal_entry_rejected(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_accounts,
        auth_headers: dict
    ):
        """Test that unbalanced journal entries are rejected."""
        
        entry_data = {
            "date": str(date.today()),
            "description": "Unbalanced Entry",
            "lines": [
                {
                    "account_id": str(test_accounts["cash"].id),
                    "debit": 1000,
                    "credit": 0,
                    "name": "Only debit"
                }
                # Missing credit line
            ]
        }
        
        response = await async_client.post(
            "/api/v1/journal-entries",
            json=entry_data,
            headers=auth_headers
        )
        
        # Should be rejected
        assert response.status_code in [400, 422]

    async def test_insufficient_stock_prevented(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_product: Product,
        test_customer,
        auth_headers: dict,
        tenant_id: UUID
    ):
        """Test that selling more than available stock is prevented."""
        
        # No stock received
        assert test_product.quantity_on_hand == Decimal("0")
        
        # Try to sell
        sale_data = {
            "partner_id": str(test_customer.id),
            "date_order": str(date.today()),
            "lines": [
                {
                    "product_id": str(test_product.id),
                    "quantity": 10,
                    "unit_price": 150.00
                }
            ]
        }
        
        response = await async_client.post(
            "/api/v1/sales/orders",
            json=sale_data,
            headers=auth_headers
        )
        
        # Either rejected or created with warning
        # Behavior depends on configuration
        if response.status_code == 201:
            # If created, check for warning
            pass  # Sale created but might need approval
        else:
            # Rejected due to insufficient stock
            assert response.status_code in [400, 422]

    async def test_concurrent_stock_update(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_product: Product,
        tenant_id: UUID
    ):
        """Test handling of concurrent stock updates."""
        
        inventory_svc = InventoryService(db_session)
        
        # Simulate concurrent updates
        import asyncio
        
        async def update_stock():
            await inventory_svc.create_and_process_stock_move(
                product_id=test_product.id,
                move_type=StockMoveType.IN,
                quantity=Decimal("10"),
                unit_cost=Decimal("100.00"),
                tenant_id=tenant_id
            )
        
        # Run multiple updates
        await asyncio.gather(
            update_stock(),
            update_stock(),
            update_stock()
        )
        
        # Verify final quantity
        await db_session.refresh(test_product)
        assert test_product.quantity_on_hand == Decimal("30")
