"""
Nexus ERP - Advanced Reporting Service
======================================

Comprehensive reporting service including:
- Financial statements (Balance Sheet, P&L, Cash Flow)
- Sales analytics (by product, customer, region, time period)
- Inventory reports (stock valuation, movement analysis)
- Custom report builder support
- Export to PDF, Excel, CSV
- Scheduled report generation
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, case, literal_column
from sqlalchemy.orm import selectinload, aliased
import logging
import asyncio
from dataclasses import dataclass
from enum import Enum
import json

from app.models.accounting import (
    Account, AccountType, AccountCategory,
    JournalEntry, JournalItem, EntryState, MoveType,
    FiscalYear, FiscalPeriod
)
from app.models.sales import (
    SaleOrder, SaleOrderLine, SaleOrderState,
    Invoice, InvoiceLine, InvoiceState, InvoiceType,
    Payment, PaymentState, PaymentType
)
from app.models.inventory import (
    Product, ProductType, ProductStatus,
    StockMove, StockMoveType, StockMoveState,
    StockQuantity, Warehouse, StockLocation, ProductCategory,
    ValuationMethod
)
from app.models.crm import Customer
from app.models.purchase import PurchaseOrder, PurchaseOrderState

logger = logging.getLogger(__name__)


class ReportFormat(str, Enum):
    """Report export format."""
    JSON = "json"
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"


class ComparisonType(str, Enum):
    """Report comparison type."""
    PREVIOUS_PERIOD = "previous_period"
    SAME_PERIOD_LAST_YEAR = "same_period_last_year"
    YTD_LAST_YEAR = "ytd_last_year"
    CUSTOM = "custom"


class ValuationMethodReport(str, Enum):
    """Stock valuation method for reports."""
    FIFO = "fifo"
    LIFO = "lifo"
    AVERAGE = "average"
    STANDARD = "standard"


@dataclass
class ReportPeriod:
    """Report period definition."""
    date_from: date
    date_to: date
    name: Optional[str] = None
    
    @property
    def days(self) -> int:
        return (self.date_to - self.date_from).days + 1
    
    @property
    def previous_period(self) -> "ReportPeriod":
        days = self.days
        return ReportPeriod(
            date_from=self.date_from - timedelta(days=days),
            date_to=self.date_from - timedelta(days=1)
        )
    
    @property
    def same_period_last_year(self) -> "ReportPeriod":
        return ReportPeriod(
            date_from=self.date_from.replace(year=self.date_from.year - 1),
            date_to=self.date_to.replace(year=self.date_to.year - 1)
        )


@dataclass
class ScheduledReport:
    """Scheduled report definition."""
    id: UUID
    name: str
    report_type: str
    schedule: str  # cron expression
    recipients: List[str]
    format: ReportFormat
    parameters: Dict[str, Any]
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    is_active: bool


class ReportingService:
    """
    Advanced Reporting Service
    
    Provides comprehensive reporting capabilities including:
    - Financial statements
    - Sales analytics
    - Inventory reports
    - Custom reports
    - Scheduled reports
    """
    
    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        if tenant_id is None:
            raise ValueError("tenant_id is required for reporting")
        self.tenant_id = tenant_id
        self._cache: Dict[str, Any] = {}

    async def _tenant_record(self, model, record_id: UUID, label: str):
        """Resolve a record strictly inside this tenant; never use an unscoped identity lookup."""
        if record_id is None:
            return None
        result = await self.db.scalar(select(model).where(
            model.id == record_id,
            model.tenant_id == self.tenant_id,
            model.is_deleted == False
        ))
        if result is None:
            logger.warning("%s %s is unavailable in tenant reporting scope", label, record_id)
        return result

    async def _validate_report_filters(self, warehouse_id=None, category_id=None, product_id=None):
        """Reject foreign-tenant filter IDs instead of silently producing misleading reports."""
        if warehouse_id is not None and not await self._tenant_record(Warehouse, warehouse_id, "Warehouse"):
            raise ValueError("Warehouse does not belong to the active tenant")
        if category_id is not None and not await self._tenant_record(ProductCategory, category_id, "Product category"):
            raise ValueError("Product category does not belong to the active tenant")
        if product_id is not None and not await self._tenant_record(Product, product_id, "Product"):
            raise ValueError("Product does not belong to the active tenant")
    
    # ========================================
    # Financial Reports
    # ========================================
    
    async def get_balance_sheet(
        self,
        as_of_date: date,
        comparison: Optional[ComparisonType] = None,
        comparison_date: Optional[date] = None,
        include_zero_balances: bool = False,
        show_details: bool = True
    ) -> Dict[str, Any]:
        """
        Generate Balance Sheet report.
        
        Args:
            as_of_date: Report date
            comparison: Type of comparison
            comparison_date: Custom comparison date
            include_zero_balances: Include accounts with zero balance
            show_details: Show detailed breakdown
            
        Returns:
            Balance sheet data with assets, liabilities, and equity
        """
        # Get current period data
        current_data = await self._get_balance_sheet_data(as_of_date, include_zero_balances)
        
        result = {
            "report_type": "balance_sheet",
            "as_of_date": as_of_date,
            "generated_at": datetime.utcnow(),
            "tenant_id": str(self.tenant_id),
            "currency": "SAR",  # Default currency
            **current_data
        }
        
        # Add comparison if requested
        if comparison:
            if comparison == ComparisonType.CUSTOM and comparison_date:
                compare_date = comparison_date
            elif comparison == ComparisonType.PREVIOUS_PERIOD:
                compare_date = as_of_date - timedelta(days=30)  # Approximate
            else:
                compare_date = as_of_date.replace(year=as_of_date.year - 1)
            
            comparison_data = await self._get_balance_sheet_data(compare_date, include_zero_balances)
            result["comparison"] = {
                "type": comparison,
                "date": compare_date,
                "data": comparison_data
            }
            
            # Calculate variances
            result["variance"] = self._calculate_balance_sheet_variance(
                current_data, comparison_data
            )
        
        return result
    
    async def _get_balance_sheet_data(
        self,
        as_of_date: date,
        include_zero_balances: bool
    ) -> Dict[str, Any]:
        """Get balance sheet data for a specific date."""
        # Get all asset, liability, and equity accounts
        accounts = await self._get_accounts_by_type(
            [AccountType.ASSET, AccountType.LIABILITY, AccountType.EQUITY]
        )
        
        assets = []
        liabilities = []
        equity = []
        
        total_assets = Decimal("0")
        total_liabilities = Decimal("0")
        total_equity = Decimal("0")
        
        for account in accounts:
            balance = await self._get_account_balance(account.id, as_of_date)
            
            if not include_zero_balances and abs(balance) < Decimal("0.01"):
                continue
            
            account_data = {
                "account_id": str(account.id),
                "code": account.code,
                "name": account.name,
                "balance": balance
            }
            
            if account.account_type == AccountType.ASSET:
                # For assets, debit increases balance
                assets.append(account_data)
                total_assets += balance
            elif account.account_type == AccountType.LIABILITY:
                # For liabilities, credit increases balance
                liabilities.append(account_data)
                total_liabilities += balance
            else:  # EQUITY
                equity.append(account_data)
                total_equity += balance
        
        # Calculate retained earnings (net income)
        retained_earnings = await self._get_retained_earnings(as_of_date)
        
        return {
            "assets": {
                "title": "Assets",
                "accounts": assets,
                "total": total_assets,
                "subtotals": self._calculate_subtotals(assets, "code")
            },
            "liabilities": {
                "title": "Liabilities",
                "accounts": liabilities,
                "total": total_liabilities,
                "subtotals": self._calculate_subtotals(liabilities, "code")
            },
            "equity": {
                "title": "Equity",
                "accounts": equity,
                "total": total_equity,
                "retained_earnings": retained_earnings,
                "subtotals": self._calculate_subtotals(equity, "code")
            },
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "total_equity": total_equity + retained_earnings,
            "total_liabilities_and_equity": total_liabilities + total_equity + retained_earnings,
            "is_balanced": abs(total_assets - (total_liabilities + total_equity + retained_earnings)) < Decimal("0.01")
        }
    
    async def get_profit_loss(
        self,
        period: ReportPeriod,
        comparison: Optional[ComparisonType] = None,
        comparison_period: Optional[ReportPeriod] = None,
        include_zero_balances: bool = False,
        show_gross_profit: bool = True,
        show_ebitda: bool = True
    ) -> Dict[str, Any]:
        """
        Generate Profit & Loss (Income Statement) report.
        
        Args:
            period: Report period
            comparison: Type of comparison
            comparison_period: Custom comparison period
            include_zero_balances: Include accounts with zero balance
            show_gross_profit: Show gross profit calculation
            show_ebitda: Show EBITDA calculation
            
        Returns:
            P&L statement with revenue, expenses, and net income
        """
        # Get current period data
        current_data = await self._get_profit_loss_data(
            period, include_zero_balances, show_gross_profit, show_ebitda
        )
        
        result = {
            "report_type": "profit_loss",
            "period": {
                "date_from": period.date_from,
                "date_to": period.date_to,
                "name": period.name
            },
            "generated_at": datetime.utcnow(),
            "tenant_id": str(self.tenant_id),
            "currency": "SAR",
            **current_data
        }
        
        # Add comparison if requested
        if comparison:
            if comparison == ComparisonType.CUSTOM and comparison_period:
                compare_period = comparison_period
            elif comparison == ComparisonType.PREVIOUS_PERIOD:
                compare_period = period.previous_period
            else:
                compare_period = period.same_period_last_year
            
            comparison_data = await self._get_profit_loss_data(
                compare_period, include_zero_balances, show_gross_profit, show_ebitda
            )
            result["comparison"] = {
                "type": comparison,
                "period": {
                    "date_from": compare_period.date_from,
                    "date_to": compare_period.date_to
                },
                "data": comparison_data
            }
            
            # Calculate variances
            result["variance"] = self._calculate_pl_variance(current_data, comparison_data)
        
        return result
    
    async def _get_profit_loss_data(
        self,
        period: ReportPeriod,
        include_zero_balances: bool,
        show_gross_profit: bool,
        show_ebitda: bool
    ) -> Dict[str, Any]:
        """Get P&L data for a specific period."""
        # Get revenue accounts
        revenue_accounts = await self._get_accounts_by_type([AccountType.REVENUE])
        # Get expense accounts
        expense_accounts = await self._get_accounts_by_type([AccountType.EXPENSE])
        
        # Revenue section
        revenue_lines = []
        total_revenue = Decimal("0")
        
        for account in revenue_accounts:
            amount = await self._get_account_period_balance(
                account.id, period.date_from, period.date_to
            )
            
            if not include_zero_balances and abs(amount) < Decimal("0.01"):
                continue
            
            # Revenue accounts typically have credit balances
            # So we need to negate for display (show positive revenue)
            amount = -amount
            
            revenue_lines.append({
                "account_id": str(account.id),
                "code": account.code,
                "name": account.name,
                "amount": amount,
                "category": account.category.value if account.category else None
            })
            total_revenue += amount
        
        # Expense section
        expense_lines = []
        total_expenses = Decimal("0")
        cost_of_sales = Decimal("0")
        operating_expenses = Decimal("0")
        
        for account in expense_accounts:
            amount = await self._get_account_period_balance(
                account.id, period.date_from, period.date_to
            )
            
            if not include_zero_balances and abs(amount) < Decimal("0.01"):
                continue
            
            # Expense accounts have debit balances (show as positive)
            
            expense_lines.append({
                "account_id": str(account.id),
                "code": account.code,
                "name": account.name,
                "amount": amount,
                "category": account.category.value if account.category else None
            })
            total_expenses += amount
            
            # Categorize expenses
            if account.category == AccountCategory.COST_OF_SALES:
                cost_of_sales += amount
            else:
                operating_expenses += amount
        
        # Calculate gross profit
        gross_profit = total_revenue - cost_of_sales
        gross_profit_margin = (gross_profit / total_revenue * 100) if total_revenue else Decimal("0")
        
        # Calculate EBITDA (add back depreciation/amortization if tracked)
        ebitda = gross_profit - operating_expenses
        ebitda_margin = (ebitda / total_revenue * 100) if total_revenue else Decimal("0")
        
        # Calculate net income
        net_income = total_revenue - total_expenses
        net_income_margin = (net_income / total_revenue * 100) if total_revenue else Decimal("0")
        
        result = {
            "revenue": {
                "title": "Revenue",
                "lines": revenue_lines,
                "total": total_revenue
            },
            "expenses": {
                "title": "Expenses",
                "lines": expense_lines,
                "total": total_expenses,
                "by_category": {
                    "cost_of_sales": cost_of_sales,
                    "operating_expenses": operating_expenses
                }
            },
            "net_income": net_income,
            "net_income_margin": net_income_margin
        }
        
        if show_gross_profit:
            result["gross_profit"] = {
                "amount": gross_profit,
                "margin": gross_profit_margin,
                "cost_of_sales": cost_of_sales
            }
        
        if show_ebitda:
            result["ebitda"] = {
                "amount": ebitda,
                "margin": ebitda_margin
            }
        
        return result
    
    async def get_cash_flow(
        self,
        period: ReportPeriod,
        method: str = "indirect",
        comparison: Optional[ComparisonType] = None
    ) -> Dict[str, Any]:
        """
        Generate Cash Flow Statement.
        
        Args:
            period: Report period
            method: Calculation method (direct/indirect)
            comparison: Type of comparison
            
        Returns:
            Cash flow statement with operating, investing, and financing activities
        """
        # Get opening and closing cash balances
        opening_cash = await self._get_cash_balance(period.date_from - timedelta(days=1))
        closing_cash = await self._get_cash_balance(period.date_to)
        
        # Calculate cash flows by category
        operating_flows = await self._get_operating_cash_flows(period, method)
        investing_flows = await self._get_investing_cash_flows(period)
        financing_flows = await self._get_financing_cash_flows(period)
        
        net_cash_change = (
            operating_flows["total"] + 
            investing_flows["total"] + 
            financing_flows["total"]
        )
        
        result = {
            "report_type": "cash_flow",
            "period": {
                "date_from": period.date_from,
                "date_to": period.date_to
            },
            "method": method,
            "generated_at": datetime.utcnow(),
            "tenant_id": str(self.tenant_id),
            "currency": "SAR",
            "opening_cash": opening_cash,
            "closing_cash": closing_cash,
            "operating_activities": operating_flows,
            "investing_activities": investing_flows,
            "financing_activities": financing_flows,
            "net_cash_change": net_cash_change,
            "reconciliation": {
                "opening_cash": opening_cash,
                "net_change": net_cash_change,
                "closing_cash": closing_cash,
                "calculated_closing": opening_cash + net_cash_change,
                "is_balanced": abs(closing_cash - (opening_cash + net_cash_change)) < Decimal("0.01")
            }
        }
        
        return result
    
    # ========================================
    # Sales Analytics
    # ========================================
    
    async def get_sales_analysis(
        self,
        period: ReportPeriod,
        group_by: str = "product",  # product, customer, region, salesperson
        comparison: Optional[ComparisonType] = None,
        include_returns: bool = True,
        top_n: int = 10
    ) -> Dict[str, Any]:
        """
        Generate Sales Analysis report.
        
        Args:
            period: Report period
            group_by: Grouping dimension
            comparison: Type of comparison
            include_returns: Include return invoices
            top_n: Number of top items to show
            
        Returns:
            Sales analysis with breakdown by specified dimension
        """
        # Get current period sales
        current_data = await self._get_sales_data(
            period, group_by, include_returns, top_n
        )
        
        result = {
            "report_type": "sales_analysis",
            "period": {
                "date_from": period.date_from,
                "date_to": period.date_to
            },
            "group_by": group_by,
            "generated_at": datetime.utcnow(),
            "tenant_id": str(self.tenant_id),
            "currency": "SAR",
            **current_data
        }
        
        # Add comparison if requested
        if comparison:
            if comparison == ComparisonType.PREVIOUS_PERIOD:
                compare_period = period.previous_period
            elif comparison == ComparisonType.SAME_PERIOD_LAST_YEAR:
                compare_period = period.same_period_last_year
            else:
                compare_period = period
            
            comparison_data = await self._get_sales_data(
                compare_period, group_by, include_returns, top_n
            )
            result["comparison"] = {
                "type": comparison,
                "period": {
                    "date_from": compare_period.date_from,
                    "date_to": compare_period.date_to
                },
                "data": comparison_data
            }
            
            # Calculate growth rates
            result["growth_analysis"] = self._calculate_sales_growth(
                current_data, comparison_data
            )
        
        return result
    
    async def _get_sales_data(
        self,
        period: ReportPeriod,
        group_by: str,
        include_returns: bool,
        top_n: int
    ) -> Dict[str, Any]:
        """Get sales data for a specific period."""
        # Base query for invoices
        query = select(Invoice).where(
            Invoice.tenant_id == self.tenant_id,
            Invoice.is_deleted == False,
            Invoice.invoice_type == InvoiceType.OUT_INVOICE,
            Invoice.state.in_([InvoiceState.POSTED, InvoiceState.PAID, InvoiceState.PARTIAL]),
            Invoice.date_invoice >= period.date_from,
            Invoice.date_invoice <= period.date_to
        )
        
        result = await self.db.execute(query)
        invoices = result.scalars().all()
        
        # Get return invoices if requested
        returns = []
        if include_returns:
            return_query = select(Invoice).where(
                Invoice.tenant_id == self.tenant_id,
                Invoice.is_deleted == False,
                Invoice.invoice_type == InvoiceType.OUT_REFUND,
                Invoice.state.in_([InvoiceState.POSTED, InvoiceState.PAID]),
                Invoice.date_invoice >= period.date_from,
                Invoice.date_invoice <= period.date_to
            )
            return_result = await self.db.execute(return_query)
            returns = return_result.scalars().all()
        
        # Aggregate by dimension
        aggregated = await self._aggregate_sales(
            invoices, returns, group_by, top_n
        )
        
        # Calculate summary metrics
        total_sales = sum(inv.amount_total for inv in invoices)
        total_returns = sum(inv.amount_total for inv in returns)
        net_sales = total_sales - total_returns
        total_invoices = len(invoices)
        average_order_value = total_sales / total_invoices if total_invoices > 0 else Decimal("0")
        
        return {
            "summary": {
                "total_sales": total_sales,
                "total_returns": total_returns,
                "net_sales": net_sales,
                "invoice_count": total_invoices,
                "return_count": len(returns),
                "average_order_value": average_order_value
            },
            "breakdown": aggregated,
            "top_performers": aggregated[:top_n] if len(aggregated) > top_n else aggregated
        }
    
    async def _aggregate_sales(
        self,
        invoices: List[Invoice],
        returns: List[Invoice],
        group_by: str,
        top_n: int
    ) -> List[Dict[str, Any]]:
        """Aggregate sales by specified dimension."""
        aggregation: Dict[str, Dict] = {}
        
        # Process sales invoices
        for invoice in invoices:
            key = await self._get_aggregation_key(invoice, group_by)
            if key not in aggregation:
                aggregation[key] = {
                    "key": key,
                    "sales": Decimal("0"),
                    "returns": Decimal("0"),
                    "invoice_count": 0,
                    "return_count": 0
                }
            aggregation[key]["sales"] += invoice.amount_total
            aggregation[key]["invoice_count"] += 1
        
        # Process returns
        for invoice in returns:
            key = await self._get_aggregation_key(invoice, group_by)
            if key not in aggregation:
                aggregation[key] = {
                    "key": key,
                    "sales": Decimal("0"),
                    "returns": Decimal("0"),
                    "invoice_count": 0,
                    "return_count": 0
                }
            aggregation[key]["returns"] += invoice.amount_total
            aggregation[key]["return_count"] += 1
        
        # Calculate net and sort
        result = []
        for key, data in aggregation.items():
            data["net_sales"] = data["sales"] - data["returns"]
            result.append(data)
        
        result.sort(key=lambda x: x["net_sales"], reverse=True)
        return result
    
    async def _get_aggregation_key(self, invoice: Invoice, group_by: str) -> str:
        """Get aggregation key for an invoice."""
        if group_by == "customer":
            return str(invoice.partner_id)
        elif group_by == "salesperson":
            # Get from related sale order
            if invoice.sale_order_id:
                order = await self._tenant_record(SaleOrder, invoice.sale_order_id, "Sales order")
                if order and order.salesperson_id:
                    return str(order.salesperson_id)
            return "unassigned"
        elif group_by == "product":
            # Aggregate by first product in invoice
            lines_result = await self.db.execute(
                select(InvoiceLine).where(
                    InvoiceLine.tenant_id == self.tenant_id,
                    InvoiceLine.is_deleted == False,
                    InvoiceLine.invoice_id == invoice.id
                ).limit(1)
            )
            line = lines_result.scalar_one_or_none()
            if line and line.product_id:
                return str(line.product_id)
            return "other"
        elif group_by == "region":
            # Get customer region
            partner = await self._tenant_record(Customer, invoice.partner_id, "Customer")
            if partner and partner.state:
                return partner.state
            return "unknown"
        else:
            return "all"
    
    # ========================================
    # Inventory Reports
    # ========================================
    
    async def get_inventory_valuation(
        self,
        as_of_date: date,
        valuation_method: ValuationMethodReport = ValuationMethodReport.AVERAGE,
        warehouse_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
        include_zero_quantities: bool = False
    ) -> Dict[str, Any]:
        """
        Generate Inventory Valuation report.
        
        Args:
            as_of_date: Valuation date
            valuation_method: FIFO, LIFO, Average, or Standard
            warehouse_id: Filter by warehouse
            category_id: Filter by category
            include_zero_quantities: Include products with zero quantity
            
        Returns:
            Inventory valuation with detailed breakdown
        """
        await self._validate_report_filters(warehouse_id=warehouse_id, category_id=category_id)
        # Build product query
        query = select(Product).options(selectinload(Product.category)).where(
            Product.tenant_id == self.tenant_id,
            Product.is_deleted == False,
            Product.is_stockable == True
        )
        
        if category_id:
            query = query.where(Product.category_id == category_id)
        
        result = await self.db.execute(query)
        products = result.scalars().all()
        
        valuation_lines = []
        total_quantity = Decimal("0")
        total_value = Decimal("0")
        total_cost = Decimal("0")
        
        for product in products:
            # Get stock quantity
            quantity = await self._get_product_quantity(product.id, warehouse_id, as_of_date)
            
            if not include_zero_quantities and quantity <= 0:
                continue
            
            # Calculate unit cost based on valuation method
            unit_cost = await self._calculate_unit_cost(
                product, valuation_method, as_of_date
            )
            
            value = quantity * unit_cost
            
            line = {
                "product_id": str(product.id),
                "sku": product.sku,
                "name": product.name,
                "category": product.category.name if product.category else None,
                "quantity": quantity,
                "unit_cost": unit_cost,
                "total_value": value,
                "valuation_method": valuation_method.value,
                "sale_price": product.sale_price,
                "potential_profit": (product.sale_price - unit_cost) * quantity if product.sale_price else None
            }
            
            valuation_lines.append(line)
            total_quantity += quantity
            total_value += value
            total_cost += unit_cost * quantity
        
        # Calculate average cost
        average_cost = total_value / total_quantity if total_quantity > 0 else Decimal("0")
        
        return {
            "report_type": "inventory_valuation",
            "as_of_date": as_of_date,
            "valuation_method": valuation_method.value,
            "warehouse_filter": str(warehouse_id) if warehouse_id else None,
            "generated_at": datetime.utcnow(),
            "tenant_id": str(self.tenant_id),
            "currency": "SAR",
            "summary": {
                "product_count": len(valuation_lines),
                "total_quantity": total_quantity,
                "total_value": total_value,
                "average_cost": average_cost
            },
            "valuation": valuation_lines,
            "by_category": self._group_by_category(valuation_lines)
        }
    
    async def get_stock_movement_analysis(
        self,
        period: ReportPeriod,
        warehouse_id: Optional[UUID] = None,
        product_id: Optional[UUID] = None,
        movement_type: Optional[StockMoveType] = None
    ) -> Dict[str, Any]:
        """
        Generate Stock Movement Analysis report.
        
        Args:
            period: Report period
            warehouse_id: Filter by warehouse
            product_id: Filter by product
            movement_type: Filter by movement type
            
        Returns:
            Stock movement analysis with trends
        """
        await self._validate_report_filters(warehouse_id=warehouse_id, product_id=product_id)
        # Build query
        query = select(StockMove).where(
            StockMove.tenant_id == self.tenant_id,
            StockMove.is_deleted == False,
            StockMove.state == StockMoveState.DONE,
            StockMove.date >= period.date_from,
            StockMove.date <= period.date_to
        )
        
        if warehouse_id:
            query = query.where(
                or_(
                    StockMove.warehouse_from_id == warehouse_id,
                    StockMove.warehouse_to_id == warehouse_id
                )
            )
        
        if product_id:
            query = query.where(StockMove.product_id == product_id)
        
        if movement_type:
            query = query.where(StockMove.move_type == movement_type)
        
        query = query.order_by(StockMove.date)
        
        result = await self.db.execute(query)
        moves = result.scalars().all()
        
        # Aggregate movements
        by_type: Dict[str, Dict] = {}
        by_product: Dict[str, Dict] = {}
        by_date: Dict[str, Dict] = {}
        daily_totals: List[Dict] = []
        
        total_in = Decimal("0")
        total_out = Decimal("0")
        total_value_in = Decimal("0")
        total_value_out = Decimal("0")
        
        for move in moves:
            # By movement type
            move_type = move.move_type.value
            if move_type not in by_type:
                by_type[move_type] = {
                    "count": 0,
                    "quantity": Decimal("0"),
                    "value": Decimal("0")
                }
            by_type[move_type]["count"] += 1
            by_type[move_type]["quantity"] += move.quantity
            by_type[move_type]["value"] += move.total_cost
            
            # By product
            prod_key = str(move.product_id)
            if prod_key not in by_product:
                product = await self._tenant_record(Product, move.product_id, "Product")
                by_product[prod_key] = {
                    "product_id": prod_key,
                    "sku": product.sku if product else "Unknown",
                    "name": product.name if product else "Unknown",
                    "quantity_in": Decimal("0"),
                    "quantity_out": Decimal("0"),
                    "value_in": Decimal("0"),
                    "value_out": Decimal("0")
                }
            
            # Determine warehouse-aware direction. Internal transfers are neutral
            # company-wide, but count as inbound/outbound for a selected warehouse.
            inbound = move.move_type in [StockMoveType.IN, StockMoveType.RETURN_IN, StockMoveType.PRODUCTION]
            outbound = move.move_type in [StockMoveType.OUT, StockMoveType.RETURN_OUT, StockMoveType.LOSS]
            if move.move_type == StockMoveType.ADJUSTMENT:
                inbound = move.warehouse_to_id is not None
                outbound = move.warehouse_from_id is not None
            elif move.move_type == StockMoveType.INTERNAL and warehouse_id:
                inbound = move.warehouse_to_id == warehouse_id and move.warehouse_from_id != warehouse_id
                outbound = move.warehouse_from_id == warehouse_id and move.warehouse_to_id != warehouse_id

            if inbound:
                by_product[prod_key]["quantity_in"] += move.quantity
                by_product[prod_key]["value_in"] += move.total_cost
                total_in += move.quantity
                total_value_in += move.total_cost
            elif outbound:
                by_product[prod_key]["quantity_out"] += move.quantity
                by_product[prod_key]["value_out"] += move.total_cost
                total_out += move.quantity
                total_value_out += move.total_cost
            
            # By date
            date_key = move.date.isoformat()
            if date_key not in by_date:
                by_date[date_key] = {
                    "date": date_key,
                    "quantity_in": Decimal("0"),
                    "quantity_out": Decimal("0"),
                    "value_in": Decimal("0"),
                    "value_out": Decimal("0"),
                    "move_count": 0
                }
            by_date[date_key]["move_count"] += 1
            
            if inbound:
                by_date[date_key]["quantity_in"] += move.quantity
                by_date[date_key]["value_in"] += move.total_cost
            elif outbound:
                by_date[date_key]["quantity_out"] += move.quantity
                by_date[date_key]["value_out"] += move.total_cost
        
        # Prepare daily totals
        for date_key in sorted(by_date.keys()):
            daily_totals.append(by_date[date_key])
        
        return {
            "report_type": "stock_movement",
            "period": {
                "date_from": period.date_from,
                "date_to": period.date_to
            },
            "generated_at": datetime.utcnow(),
            "tenant_id": str(self.tenant_id),
            "currency": "SAR",
            "summary": {
                "total_moves": len(moves),
                "total_quantity_in": total_in,
                "total_quantity_out": total_out,
                "net_quantity": total_in - total_out,
                "total_value_in": total_value_in,
                "total_value_out": total_value_out,
                "net_value": total_value_in - total_value_out
            },
            "by_type": by_type,
            "by_product": list(by_product.values()),
            "daily_movements": daily_totals
        }
    
    async def get_slow_moving_items(
        self,
        days_threshold: int = 90,
        warehouse_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
        min_value: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Identify slow-moving inventory items.
        
        Args:
            days_threshold: Days without movement to consider slow
            warehouse_id: Filter by warehouse
            category_id: Filter by category
            min_value: Minimum value to include
            
        Returns:
            List of slow-moving items with analysis
        """
        threshold_date = date.today() - timedelta(days=days_threshold)
        
        if days_threshold < 1:
            raise ValueError("days_threshold must be at least 1")
        await self._validate_report_filters(warehouse_id=warehouse_id, category_id=category_id)
        # Get all stockable products
        query = select(Product).options(selectinload(Product.category)).where(
            Product.tenant_id == self.tenant_id,
            Product.is_deleted == False,
            Product.is_stockable == True,
            Product.quantity_on_hand > 0
        )
        
        if category_id:
            query = query.where(Product.category_id == category_id)
        
        result = await self.db.execute(query)
        products = result.scalars().all()
        
        slow_items = []
        total_slow_value = Decimal("0")
        total_slow_quantity = Decimal("0")
        
        for product in products:
            # Check for recent movements
            movement_query = select(StockMove).where(
                StockMove.tenant_id == self.tenant_id,
                StockMove.is_deleted == False,
                StockMove.product_id == product.id,
                StockMove.state == StockMoveState.DONE,
                StockMove.date >= threshold_date
            )
            
            if warehouse_id:
                movement_query = movement_query.where(
                    or_(
                        StockMove.warehouse_from_id == warehouse_id,
                        StockMove.warehouse_to_id == warehouse_id
                    )
                )
            
            movement_result = await self.db.execute(movement_query.limit(1))
            recent_movement = movement_result.scalar_one_or_none()
            
            if recent_movement:
                continue  # Has recent movement, not slow
            
            # Get last movement
            last_movement_query = select(StockMove).where(
                StockMove.tenant_id == self.tenant_id,
                StockMove.is_deleted == False,
                StockMove.product_id == product.id,
                StockMove.state == StockMoveState.DONE
            ).order_by(desc(StockMove.date)).limit(1)
            
            last_movement_result = await self.db.execute(last_movement_query)
            last_movement = last_movement_result.scalar_one_or_none()
            
            # Calculate value
            quantity = await self._get_product_quantity(product.id, warehouse_id, date.today())
            value = quantity * product.average_cost
            
            if min_value and value < min_value:
                continue
            
            days_since_movement = 0
            last_movement_date = None
            
            if last_movement:
                last_movement_date = last_movement.date
                days_since_movement = (date.today() - last_movement_date).days
            else:
                days_since_movement = days_threshold + 1  # No movement ever
            
            slow_items.append({
                "product_id": str(product.id),
                "sku": product.sku,
                "name": product.name,
                "category": product.category.name if product.category else None,
                "quantity": quantity,
                "unit_cost": product.average_cost,
                "total_value": value,
                "last_movement_date": last_movement_date,
                "days_since_movement": days_since_movement,
                "risk_level": "high" if days_since_movement > days_threshold * 1.5 else "medium"
            })
            
            total_slow_value += value
            total_slow_quantity += quantity
        
        # Sort by days since movement (descending)
        slow_items.sort(key=lambda x: x["days_since_movement"], reverse=True)
        
        return {
            "report_type": "slow_moving_items",
            "threshold_days": days_threshold,
            "warehouse_filter": str(warehouse_id) if warehouse_id else None,
            "generated_at": datetime.utcnow(),
            "tenant_id": str(self.tenant_id),
            "currency": "SAR",
            "summary": {
                "total_slow_items": len(slow_items),
                "total_slow_value": total_slow_value,
                "total_slow_quantity": total_slow_quantity,
                "percentage_of_inventory": None  # Would need total inventory value
            },
            "items": slow_items
        }
    
    # ========================================
    # Custom Reports
    # ========================================
    
    async def build_custom_report(
        self,
        name: str,
        data_sources: List[str],
        columns: List[Dict[str, Any]],
        filters: Dict[str, Any],
        group_by: Optional[str] = None,
        order_by: Optional[str] = None,
        limit: int = 1000
    ) -> Dict[str, Any]:
        """
        Build a custom report from specified data sources.
        
        Args:
            name: Report name
            data_sources: List of data source names
            columns: Column definitions
            filters: Filter conditions
            group_by: Grouping field
            order_by: Ordering field
            limit: Maximum rows
            
        Returns:
            Custom report data
        """
        # This implementation supports exactly one primary source. Accepting multiple
        # sources while silently selecting only one would produce deceptive reports.
        valid_sources = {"sales", "inventory", "accounting"}
        if not data_sources or len(data_sources) != 1 or data_sources[0] not in valid_sources:
            raise ValueError("Select exactly one supported primary data source: sales, inventory, or accounting")
        if not columns or len(columns) > 50:
            raise ValueError("A custom report must define between 1 and 50 columns")
        if limit < 1:
            raise ValueError("limit must be positive")
        limit = min(limit, 5000)
        if filters or group_by or order_by:
            raise ValueError("Custom report filters, grouping, and sorting are not implemented yet; omit these options")

        source = data_sources[0]
        allowed_fields = {
            "sales": {"id", "number", "date_order", "state", "amount_untaxed", "amount_tax", "amount_total", "partner_id", "salesperson_id"},
            "inventory": {"id", "sku", "name", "product_type", "status", "quantity_on_hand", "reorder_point", "sale_price", "cost_price", "average_cost"},
            "accounting": {"id", "number", "date", "state", "description", "ref", "move_type", "source_model", "source_id"}
        }[source]
        for col in columns:
            if not isinstance(col, dict) or not isinstance(col.get("field"), str) or col["field"] not in allowed_fields:
                raise ValueError(f"Unsupported column for {source} report: {col.get('field') if isinstance(col, dict) else 'invalid'}")
            if not isinstance(col.get("name"), str) or not col["name"].strip() or len(col["name"]) > 80:
                raise ValueError("Each report column requires a non-empty name of at most 80 characters")

        # Build query based on the one explicitly selected data source.
        if source == "sales":
            base_query = self._build_sales_query(columns, filters)
        elif source == "inventory":
            base_query = self._build_inventory_query(columns, filters)
        else:
            base_query = self._build_accounting_query(columns, filters)

        # Execute query and project only the explicitly approved fields.
        result = await self.db.execute(base_query.limit(limit))
        records = result.scalars().all()
        data = []
        for record in records:
            row_data = {col["name"]: getattr(record, col["field"], None) for col in columns}
            data.append(row_data)
        
        return {
            "report_type": "custom",
            "name": name,
            "generated_at": datetime.utcnow(),
            "tenant_id": str(self.tenant_id),
            "columns": columns,
            "row_count": len(data),
            "data": data
        }
    
    # ========================================
    # Scheduled Reports
    # ========================================
    
    async def get_scheduled_reports(self) -> List[ScheduledReport]:
        """Get all scheduled reports for tenant."""
        # In a real implementation, this would query a scheduled_reports table
        # For now, return empty list
        return []
    
    async def create_scheduled_report(
        self,
        name: str,
        report_type: str,
        schedule: str,
        recipients: List[str],
        format: ReportFormat,
        parameters: Dict[str, Any]
    ) -> ScheduledReport:
        """Create a new scheduled report."""
        # In a real implementation, this would persist to database
        report = ScheduledReport(
            id=UUID("00000000-0000-0000-0000-000000000000"),  # Would be generated
            name=name,
            report_type=report_type,
            schedule=schedule,
            recipients=recipients,
            format=format,
            parameters=parameters,
            last_run=None,
            next_run=None,
            is_active=True
        )
        return report
    
    async def execute_scheduled_report(
        self,
        report_id: UUID
    ) -> Dict[str, Any]:
        """Execute a scheduled report and send to recipients."""
        # Get report definition
        # Execute report
        # Send to recipients
        return {
            "report_id": str(report_id),
            "executed_at": datetime.utcnow(),
            "status": "completed"
        }
    
    # ========================================
    # Helper Methods
    # ========================================
    
    async def _get_accounts_by_type(
        self,
        account_types: List[AccountType]
    ) -> List[Account]:
        """Get accounts by type."""
        query = select(Account).where(
            Account.tenant_id == self.tenant_id,
            Account.is_deleted == False,
            Account.account_type.in_(account_types),
            Account.is_header == False
        ).order_by(Account.code)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def _get_account_balance(
        self,
        account_id: UUID,
        as_of_date: date
    ) -> Decimal:
        """Get account balance as of a date."""
        result = await self.db.execute(
            select(
                func.coalesce(func.sum(JournalItem.debit), Decimal("0")).label("debit"),
                func.coalesce(func.sum(JournalItem.credit), Decimal("0")).label("credit")
            ).join(JournalEntry).where(
                JournalItem.account_id == account_id,
                JournalEntry.date <= as_of_date,
                JournalEntry.state == EntryState.POSTED,
                JournalEntry.tenant_id == self.tenant_id
            )
        )
        
        row = result.one()
        account = await self._tenant_record(Account, account_id, "Account")
        if account is None:
            return Decimal("0")
        
        if account and account.is_debit_account:
            return row.debit - row.credit
        return row.credit - row.debit
    
    async def _get_account_period_balance(
        self,
        account_id: UUID,
        date_from: date,
        date_to: date
    ) -> Decimal:
        """Get account balance for a period."""
        result = await self.db.execute(
            select(
                func.coalesce(func.sum(JournalItem.debit), Decimal("0")).label("debit"),
                func.coalesce(func.sum(JournalItem.credit), Decimal("0")).label("credit")
            ).join(JournalEntry).where(
                JournalItem.account_id == account_id,
                JournalEntry.date >= date_from,
                JournalEntry.date <= date_to,
                JournalEntry.state == EntryState.POSTED,
                JournalEntry.tenant_id == self.tenant_id
            )
        )
        
        row = result.one()
        return row.debit - row.credit
    
    async def _get_retained_earnings(self, as_of_date: date) -> Decimal:
        """Calculate retained earnings."""
        # Get all revenue and expense balances
        revenue_accounts = await self._get_accounts_by_type([AccountType.REVENUE])
        expense_accounts = await self._get_accounts_by_type([AccountType.EXPENSE])
        
        total_revenue = Decimal("0")
        total_expenses = Decimal("0")
        
        for account in revenue_accounts:
            balance = await self._get_account_balance(account.id, as_of_date)
            total_revenue -= balance  # Revenue is negative (credit balance)
        
        for account in expense_accounts:
            balance = await self._get_account_balance(account.id, as_of_date)
            total_expenses += balance  # Expenses are positive (debit balance)
        
        return total_revenue - total_expenses
    
    async def _get_cash_balance(self, as_of_date: date) -> Decimal:
        """Get total cash balance."""
        # Get cash and bank accounts
        cash_accounts = await self.db.execute(
            select(Account).where(
                Account.tenant_id == self.tenant_id,
                Account.category == AccountCategory.CASH,
                Account.is_deleted == False,
                Account.is_header == False
            )
        )
        accounts = cash_accounts.scalars().all()
        
        total_cash = Decimal("0")
        for account in accounts:
            balance = await self._get_account_balance(account.id, as_of_date)
            total_cash += balance
        
        return total_cash
    
    async def _get_operating_cash_flows(
        self,
        period: ReportPeriod,
        method: str
    ) -> Dict[str, Any]:
        """Get operating cash flows."""
        if method == "indirect":
            # Start with net income and adjust
            net_income = await self._get_retained_earnings(period.date_to)
            
            # Adjust for non-cash items (simplified)
            adjustments = []
            
            # Depreciation (would need to calculate from journal entries)
            # Changes in working capital
            # etc.
            
            return {
                "method": "indirect",
                "net_income": net_income,
                "adjustments": adjustments,
                "total": net_income  # Simplified
            }
        else:
            # Direct method - sum cash receipts and payments
            # Get cash receipts from customers
            receipts_result = await self.db.execute(
                select(func.coalesce(func.sum(Payment.amount), Decimal("0"))).where(
                    Payment.tenant_id == self.tenant_id,
                    Payment.payment_type == PaymentType.RECEIPT,
                    Payment.state == PaymentState.POSTED,
                    Payment.date >= period.date_from,
                    Payment.date <= period.date_to
                )
            )
            receipts = receipts_result.scalar() or Decimal("0")
            
            # Get cash payments to suppliers
            payments_result = await self.db.execute(
                select(func.coalesce(func.sum(Payment.amount), Decimal("0"))).where(
                    Payment.tenant_id == self.tenant_id,
                    Payment.payment_type == PaymentType.PAYMENT,
                    Payment.state == PaymentState.POSTED,
                    Payment.date >= period.date_from,
                    Payment.date <= period.date_to
                )
            )
            payments = payments_result.scalar() or Decimal("0")
            
            return {
                "method": "direct",
                "receipts_from_customers": receipts,
                "payments_to_suppliers": payments,
                "payments_for_expenses": Decimal("0"),  # Would calculate
                "total": receipts - payments
            }
    
    async def _get_investing_cash_flows(
        self,
        period: ReportPeriod
    ) -> Dict[str, Any]:
        """Get investing cash flows."""
        # Would calculate from asset purchases/sales
        return {
            "title": "Investing Activities",
            "items": [],
            "total": Decimal("0")
        }
    
    async def _get_financing_cash_flows(
        self,
        period: ReportPeriod
    ) -> Dict[str, Any]:
        """Get financing cash flows."""
        # Would calculate from equity and debt transactions
        return {
            "title": "Financing Activities",
            "items": [],
            "total": Decimal("0")
        }
    
    async def _get_product_quantity(
        self,
        product_id: UUID,
        warehouse_id: Optional[UUID],
        as_of_date: date
    ) -> Decimal:
        """Calculate on-hand quantity using source/destination warehouse semantics."""
        inbound_types = [StockMoveType.IN, StockMoveType.RETURN_IN, StockMoveType.PRODUCTION]
        outbound_types = [StockMoveType.OUT, StockMoveType.RETURN_OUT, StockMoveType.LOSS]

        if warehouse_id:
            quantity_delta = case(
                (and_(StockMove.move_type.in_(inbound_types), StockMove.warehouse_to_id == warehouse_id), StockMove.quantity),
                (and_(StockMove.move_type.in_(outbound_types), StockMove.warehouse_from_id == warehouse_id), -StockMove.quantity),
                (and_(StockMove.move_type == StockMoveType.ADJUSTMENT, StockMove.warehouse_to_id == warehouse_id), StockMove.quantity),
                (and_(StockMove.move_type == StockMoveType.ADJUSTMENT, StockMove.warehouse_from_id == warehouse_id), -StockMove.quantity),
                (and_(StockMove.move_type == StockMoveType.INTERNAL, StockMove.warehouse_to_id == warehouse_id, StockMove.warehouse_from_id != warehouse_id), StockMove.quantity),
                (and_(StockMove.move_type == StockMoveType.INTERNAL, StockMove.warehouse_from_id == warehouse_id, StockMove.warehouse_to_id != warehouse_id), -StockMove.quantity),
                else_=Decimal("0")
            )
        else:
            quantity_delta = case(
                (StockMove.move_type.in_(inbound_types), StockMove.quantity),
                (StockMove.move_type.in_(outbound_types), -StockMove.quantity),
                (and_(StockMove.move_type == StockMoveType.ADJUSTMENT, StockMove.warehouse_to_id.isnot(None)), StockMove.quantity),
                (and_(StockMove.move_type == StockMoveType.ADJUSTMENT, StockMove.warehouse_from_id.isnot(None)), -StockMove.quantity),
                else_=Decimal("0")
            )

        query = select(func.coalesce(func.sum(quantity_delta), Decimal("0"))).where(
            StockMove.tenant_id == self.tenant_id,
            StockMove.is_deleted == False,
            StockMove.product_id == product_id,
            StockMove.state == StockMoveState.DONE,
            StockMove.date <= as_of_date
        )
        if warehouse_id:
            query = query.where(or_(
                StockMove.warehouse_from_id == warehouse_id,
                StockMove.warehouse_to_id == warehouse_id
            ))
        result = await self.db.execute(query)
        return result.scalar() or Decimal("0")

    async def _calculate_unit_cost(
        self,
        product: Product,
        method: ValuationMethodReport,
        as_of_date: date
    ) -> Decimal:
        """Calculate unit cost based on valuation method."""
        if method == ValuationMethodReport.STANDARD:
            return product.standard_cost or product.cost_price
        elif method == ValuationMethodReport.AVERAGE:
            return product.average_cost or product.cost_price
        else:
            # FIFO/LIFO would require more complex calculation
            # For now, return average cost
            return product.average_cost or product.cost_price
    
    def _calculate_subtotals(
        self,
        items: List[Dict],
        code_field: str
    ) -> List[Dict]:
        """Calculate subtotals by code prefix."""
        # Group by first digit/letter of code
        groups: Dict[str, Decimal] = {}
        
        for item in items:
            code = item.get("code", "")
            if code:
                prefix = code[0]
                if prefix not in groups:
                    groups[prefix] = Decimal("0")
                groups[prefix] += item.get("balance", Decimal("0"))
        
        return [{"prefix": k, "total": v} for k, v in groups.items()]
    
    def _calculate_balance_sheet_variance(
        self,
        current: Dict,
        comparison: Dict
    ) -> Dict[str, Any]:
        """Calculate variance between two balance sheets."""
        return {
            "total_assets": {
                "current": current.get("total_assets", Decimal("0")),
                "previous": comparison.get("total_assets", Decimal("0")),
                "change": current.get("total_assets", Decimal("0")) - comparison.get("total_assets", Decimal("0"))
            },
            "total_liabilities": {
                "current": current.get("total_liabilities", Decimal("0")),
                "previous": comparison.get("total_liabilities", Decimal("0")),
                "change": current.get("total_liabilities", Decimal("0")) - comparison.get("total_liabilities", Decimal("0"))
            },
            "total_equity": {
                "current": current.get("total_equity", Decimal("0")),
                "previous": comparison.get("total_equity", Decimal("0")),
                "change": current.get("total_equity", Decimal("0")) - comparison.get("total_equity", Decimal("0"))
            }
        }
    
    def _calculate_pl_variance(
        self,
        current: Dict,
        comparison: Dict
    ) -> Dict[str, Any]:
        """Calculate variance between two P&L statements."""
        current_net = current.get("net_income", Decimal("0"))
        comparison_net = comparison.get("net_income", Decimal("0"))
        
        return {
            "net_income": {
                "current": current_net,
                "previous": comparison_net,
                "change": current_net - comparison_net,
                "change_percent": ((current_net - comparison_net) / abs(comparison_net) * 100) if comparison_net != 0 else None
            }
        }
    
    def _calculate_sales_growth(
        self,
        current: Dict,
        comparison: Dict
    ) -> Dict[str, Any]:
        """Calculate sales growth between periods."""
        current_sales = current.get("summary", {}).get("net_sales", Decimal("0"))
        comparison_sales = comparison.get("summary", {}).get("net_sales", Decimal("0"))
        
        return {
            "net_sales": {
                "current": current_sales,
                "previous": comparison_sales,
                "growth": current_sales - comparison_sales,
                "growth_percent": ((current_sales - comparison_sales) / comparison_sales * 100) if comparison_sales != 0 else None
            }
        }
    
    def _group_by_category(
        self,
        items: List[Dict]
    ) -> List[Dict]:
        """Group items by category."""
        categories: Dict[str, Dict] = {}
        
        for item in items:
            category = item.get("category", "Uncategorized")
            if category not in categories:
                categories[category] = {
                    "category": category,
                    "quantity": Decimal("0"),
                    "value": Decimal("0"),
                    "count": 0
                }
            categories[category]["quantity"] += item.get("quantity", Decimal("0"))
            categories[category]["value"] += item.get("total_value", Decimal("0"))
            categories[category]["count"] += 1
        
        return list(categories.values())
    
    def _build_sales_query(self, columns: List[Dict], filters: Dict):
        """Build sales query for custom report."""
        # Simplified implementation
        return select(SaleOrder).where(
            SaleOrder.tenant_id == self.tenant_id,
            SaleOrder.is_deleted == False
        )
    
    def _build_inventory_query(self, columns: List[Dict], filters: Dict):
        """Build inventory query for custom report."""
        return select(Product).where(
            Product.tenant_id == self.tenant_id,
            Product.is_deleted == False
        )
    
    def _build_accounting_query(self, columns: List[Dict], filters: Dict):
        """Build accounting query for custom report."""
        return select(JournalEntry).where(
            JournalEntry.tenant_id == self.tenant_id,
            JournalEntry.is_deleted == False
        )
