"""
Nexus ERP - Reports API Endpoints (Enhanced)
=============================================

Comprehensive API endpoints for reporting including:
- Financial statements (Balance Sheet, P&L, Cash Flow)
- Sales analytics
- Inventory reports
- Custom reports
- Scheduled reports
- Export functionality
"""

from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum
import io

from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.user import User
from app.services.reporting_service import (
    ReportingService, ReportPeriod, ReportFormat,
    ComparisonType, ValuationMethodReport
)
from app.services.export_service import ExportService, ExportConfig, ExportColumn

router = APIRouter(prefix="/reports", tags=["Reports"])


# ========================================
# Request/Response Models
# ========================================

class BalanceSheetRequest(BaseModel):
    """Balance sheet request."""
    as_of_date: date
    comparison: Optional[str] = None
    comparison_date: Optional[date] = None
    include_zero_balances: bool = False
    show_details: bool = True


class ProfitLossRequest(BaseModel):
    """Profit & Loss request."""
    date_from: date
    date_to: date
    comparison: Optional[str] = None
    include_zero_balances: bool = False
    show_gross_profit: bool = True
    show_ebitda: bool = True


class CashFlowRequest(BaseModel):
    """Cash flow request."""
    date_from: date
    date_to: date
    method: str = "indirect"
    comparison: Optional[str] = None


class SalesAnalysisRequest(BaseModel):
    """Sales analysis request."""
    date_from: date
    date_to: date
    group_by: str = "product"
    comparison: Optional[str] = None
    include_returns: bool = True
    top_n: int = 10


class InventoryValuationRequest(BaseModel):
    """Inventory valuation request."""
    as_of_date: date
    valuation_method: str = "average"
    warehouse_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    include_zero_quantities: bool = False


class StockMovementRequest(BaseModel):
    """Stock movement request."""
    date_from: date
    date_to: date
    warehouse_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    movement_type: Optional[str] = None


class SlowMovingItemsRequest(BaseModel):
    """Slow moving items request."""
    days_threshold: int = 90
    warehouse_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    min_value: Optional[float] = None


class CustomReportRequest(BaseModel):
    """Custom report request."""
    name: str
    data_sources: List[str]
    columns: List[Dict[str, Any]]
    filters: Dict[str, Any]
    group_by: Optional[str] = None
    order_by: Optional[str] = None
    limit: int = 1000


class ExportRequest(BaseModel):
    """Export request."""
    format: str = "json"  # json, pdf, excel, csv
    report_type: str


# ========================================
# Financial Reports
# ========================================

@router.post(
    "/financial/balance-sheet",
    summary="Balance Sheet Report",
    description="Generate balance sheet as of a specific date"
)
async def get_balance_sheet(
    request: BalanceSheetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("reports.all.view"))
):
    """
    Generate balance sheet report.
    
    Shows assets, liabilities, and equity as of the specified date.
    Optionally includes comparison with previous period.
    """
    service = ReportingService(db, current_user.tenant_id)
    
    comparison = None
    if request.comparison:
        comparison = ComparisonType(request.comparison)
    
    report = await service.get_balance_sheet(
        as_of_date=request.as_of_date,
        comparison=comparison,
        comparison_date=request.comparison_date,
        include_zero_balances=request.include_zero_balances,
        show_details=request.show_details
    )
    
    return report


@router.post(
    "/financial/profit-loss",
    summary="Profit & Loss Report",
    description="Generate profit and loss statement for a period"
)
async def get_profit_loss(
    request: ProfitLossRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("reports.all.view"))
):
    """
    Generate profit & loss statement.
    
    Shows revenue, expenses, and net income for the period.
    Optionally includes comparison with previous period.
    """
    service = ReportingService(db, current_user.tenant_id)
    
    period = ReportPeriod(
        date_from=request.date_from,
        date_to=request.date_to
    )
    
    comparison = None
    if request.comparison:
        comparison = ComparisonType(request.comparison)
    
    report = await service.get_profit_loss(
        period=period,
        comparison=comparison,
        include_zero_balances=request.include_zero_balances,
        show_gross_profit=request.show_gross_profit,
        show_ebitda=request.show_ebitda
    )
    
    return report


@router.post(
    "/financial/cash-flow",
    summary="Cash Flow Statement",
    description="Generate cash flow statement for a period"
)
async def get_cash_flow(
    request: CashFlowRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("reports.all.view"))
):
    """
    Generate cash flow statement.
    
    Shows operating, investing, and financing activities.
    """
    service = ReportingService(db, current_user.tenant_id)
    
    period = ReportPeriod(
        date_from=request.date_from,
        date_to=request.date_to
    )
    
    comparison = None
    if request.comparison:
        comparison = ComparisonType(request.comparison)
    
    report = await service.get_cash_flow(
        period=period,
        method=request.method,
        comparison=comparison
    )
    
    return report


# ========================================
# Sales Analytics
# ========================================

@router.post(
    "/sales/analysis",
    summary="Sales Analysis Report",
    description="Analyze sales by product, customer, region, or time period"
)
async def get_sales_analysis(
    request: SalesAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("reports.all.view"))
):
    """
    Generate sales analysis report.
    
    Provides breakdown by specified dimension with comparison support.
    """
    service = ReportingService(db, current_user.tenant_id)
    
    period = ReportPeriod(
        date_from=request.date_from,
        date_to=request.date_to
    )
    
    comparison = None
    if request.comparison:
        comparison = ComparisonType(request.comparison)
    
    report = await service.get_sales_analysis(
        period=period,
        group_by=request.group_by,
        comparison=comparison,
        include_returns=request.include_returns,
        top_n=request.top_n
    )
    
    return report


@router.get(
    "/sales/by-product",
    summary="Sales by Product",
    description="Get sales breakdown by product"
)
async def get_sales_by_product(
    date_from: date = Query(...),
    date_to: date = Query(...),
    top_n: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("reports.all.view"))
):
    """Get sales breakdown by product."""
    service = ReportingService(db, current_user.tenant_id)
    
    period = ReportPeriod(date_from=date_from, date_to=date_to)
    
    report = await service.get_sales_analysis(
        period=period,
        group_by="product",
        top_n=top_n
    )
    
    return report


@router.get(
    "/sales/by-customer",
    summary="Sales by Customer",
    description="Get sales breakdown by customer"
)
async def get_sales_by_customer(
    date_from: date = Query(...),
    date_to: date = Query(...),
    top_n: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("reports.all.view"))
):
    """Get sales breakdown by customer."""
    service = ReportingService(db, current_user.tenant_id)
    
    period = ReportPeriod(date_from=date_from, date_to=date_to)
    
    report = await service.get_sales_analysis(
        period=period,
        group_by="customer",
        top_n=top_n
    )
    
    return report


@router.get(
    "/sales/by-region",
    summary="Sales by Region",
    description="Get sales breakdown by region"
)
async def get_sales_by_region(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("reports.all.view"))
):
    """Get sales breakdown by region."""
    service = ReportingService(db, current_user.tenant_id)
    
    period = ReportPeriod(date_from=date_from, date_to=date_to)
    
    report = await service.get_sales_analysis(
        period=period,
        group_by="region"
    )
    
    return report


@router.get(
    "/sales/by-salesperson",
    summary="Sales by Salesperson",
    description="Get sales breakdown by salesperson"
)
async def get_sales_by_salesperson(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("reports.all.view"))
):
    """Get sales breakdown by salesperson."""
    service = ReportingService(db, current_user.tenant_id)
    
    period = ReportPeriod(date_from=date_from, date_to=date_to)
    
    report = await service.get_sales_analysis(
        period=period,
        group_by="salesperson"
    )
    
    return report


# ========================================
# Inventory Reports
# ========================================

@router.post(
    "/inventory/valuation",
    summary="Inventory Valuation Report",
    description="Get inventory valuation using FIFO, LIFO, or Average cost"
)
async def get_inventory_valuation(
    request: InventoryValuationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("reports.all.view"))
):
    """
    Generate inventory valuation report.
    
    Supports multiple valuation methods: FIFO, LIFO, Average, Standard.
    """
    service = ReportingService(db, current_user.tenant_id)
    
    report = await service.get_inventory_valuation(
        as_of_date=request.as_of_date,
        valuation_method=ValuationMethodReport(request.valuation_method),
        warehouse_id=request.warehouse_id,
        category_id=request.category_id,
        include_zero_quantities=request.include_zero_quantities
    )
    
    return report


@router.post(
    "/inventory/movement",
    summary="Stock Movement Analysis",
    description="Analyze stock movements for a period"
)
async def get_stock_movement(
    request: StockMovementRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("reports.all.view"))
):
    """
    Generate stock movement analysis.
    
    Shows movements by type, product, and date.
    """
    from app.models.inventory import StockMoveType
    
    service = ReportingService(db, current_user.tenant_id)
    
    period = ReportPeriod(
        date_from=request.date_from,
        date_to=request.date_to
    )
    
    movement_type = None
    if request.movement_type:
        movement_type = StockMoveType(request.movement_type)
    
    report = await service.get_stock_movement_analysis(
        period=period,
        warehouse_id=request.warehouse_id,
        product_id=request.product_id,
        movement_type=movement_type
    )
    
    return report


@router.post(
    "/inventory/slow-moving",
    summary="Slow Moving Items Report",
    description="Identify slow-moving inventory items"
)
async def get_slow_moving_items(
    request: SlowMovingItemsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("reports.all.view"))
):
    """
    Identify slow-moving inventory items.
    
    Items with no movement for the specified days threshold.
    """
    from decimal import Decimal
    
    service = ReportingService(db, current_user.tenant_id)
    
    min_value = Decimal(str(request.min_value)) if request.min_value else None
    
    report = await service.get_slow_moving_items(
        days_threshold=request.days_threshold,
        warehouse_id=request.warehouse_id,
        category_id=request.category_id,
        min_value=min_value
    )
    
    return report


@router.get(
    "/inventory/low-stock",
    summary="Low Stock Report",
    description="Get items below reorder point"
)
async def get_low_stock(
    warehouse_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("reports.all.view"))
):
    """Get items below reorder point."""
    from sqlalchemy import select
    from app.models.inventory import Product, Warehouse

    if warehouse_id is not None:
        warehouse = await db.scalar(select(Warehouse).where(
            Warehouse.id == warehouse_id,
            Warehouse.tenant_id == current_user.tenant_id,
            Warehouse.is_deleted == False
        ))
        if warehouse is None:
            raise HTTPException(status_code=404, detail="Warehouse not found")
        raise HTTPException(status_code=400, detail="Warehouse-specific low-stock calculation is not implemented yet")
    
    query = select(Product).where(
        Product.tenant_id == current_user.tenant_id,
        Product.is_deleted == False,
        Product.is_stockable == True,
        Product.quantity_on_hand <= Product.reorder_point,
        Product.reorder_point > 0
    )
    
    result = await db.execute(query)
    products = result.scalars().all()
    
    return {
        "report_type": "low_stock",
        "generated_at": datetime.utcnow(),
        "warehouse_filter": str(warehouse_id) if warehouse_id else None,
        "items": [
            {
                "product_id": str(p.id),
                "sku": p.sku,
                "name": p.name,
                "quantity_on_hand": p.quantity_on_hand,
                "reorder_point": p.reorder_point,
                "reorder_quantity": p.reorder_quantity,
                "shortage": p.reorder_point - p.quantity_on_hand
            }
            for p in products
        ],
        "total_items": len(products)
    }


# ========================================
# Custom Reports
# ========================================

@router.post(
    "/custom",
    summary="Custom Report Builder",
    description="Build a custom report from specified data sources"
)
async def build_custom_report(
    request: CustomReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("reports.all.view"))
):
    """
    Build a custom report.
    
    Specify data sources, columns, filters, and grouping.
    """
    service = ReportingService(db, current_user.tenant_id)
    
    try:
        report = await service.build_custom_report(
            name=request.name,
            data_sources=request.data_sources,
            columns=request.columns,
            filters=request.filters,
            group_by=request.group_by,
            order_by=request.order_by,
            limit=request.limit
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    
    return report


# ========================================
# Scheduled Reports
# ========================================

@router.get(
    "/scheduled",
    summary="Scheduled Reports",
    description="Get list of scheduled reports"
)
async def get_scheduled_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("reports.all.view"))
):
    """Get list of scheduled reports."""
    service = ReportingService(db, current_user.tenant_id)
    
    reports = await service.get_scheduled_reports()
    
    return {
        "scheduled_reports": [
            {
                "id": str(r.id),
                "name": r.name,
                "report_type": r.report_type,
                "schedule": r.schedule,
                "format": r.format.value,
                "recipients": r.recipients,
                "is_active": r.is_active,
                "last_run": r.last_run,
                "next_run": r.next_run
            }
            for r in reports
        ]
    }


@router.post(
    "/scheduled",
    summary="Create Scheduled Report",
    description="Schedule a recurring report"
)
async def create_scheduled_report(
    name: str,
    report_type: str,
    schedule: str,  # cron expression
    format: str,
    recipients: List[str],
    parameters: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("reports.all.schedule"))
):
    """Create a new scheduled report."""
    service = ReportingService(db, current_user.tenant_id)
    
    report = await service.create_scheduled_report(
        name=name,
        report_type=report_type,
        schedule=schedule,
        recipients=recipients,
        format=ReportFormat(format),
        parameters=parameters
    )
    
    return {
        "id": str(report.id),
        "name": report.name,
        "schedule": report.schedule,
        "is_active": report.is_active
    }


# ========================================
# Export Endpoints
# ========================================

@router.post(
    "/export/balance-sheet",
    summary="Export Balance Sheet",
    description="Export balance sheet to PDF, Excel, or CSV"
)
async def export_balance_sheet(
    request: BalanceSheetRequest,
    format: str = Query("pdf", regex="^(pdf|excel|csv|json)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("reports.all.export"))
):
    """Export balance sheet report."""
    reporting = ReportingService(db, current_user.tenant_id)
    export = ExportService(current_user.tenant_id)
    
    # Generate report
    report_data = await reporting.get_balance_sheet(
        as_of_date=request.as_of_date,
        include_zero_balances=request.include_zero_balances
    )
    
    # Export
    file_buffer = await export.export_balance_sheet(
        report_data,
        ReportFormat(format),
        current_user.tenant.company.name if hasattr(current_user, 'tenant') else None
    )
    
    # Determine content type and filename
    content_types = {
        "pdf": "application/pdf",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "csv": "text/csv",
        "json": "application/json"
    }
    extensions = {"pdf": "pdf", "excel": "xlsx", "csv": "csv", "json": "json"}
    
    filename = f"balance_sheet_{request.as_of_date}.{extensions[format]}"
    
    return StreamingResponse(
        file_buffer,
        media_type=content_types[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.post(
    "/export/profit-loss",
    summary="Export Profit & Loss",
    description="Export P&L statement to PDF, Excel, or CSV"
)
async def export_profit_loss(
    request: ProfitLossRequest,
    format: str = Query("pdf", regex="^(pdf|excel|csv|json)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("reports.all.export"))
):
    """Export profit & loss statement."""
    reporting = ReportingService(db, current_user.tenant_id)
    export = ExportService(current_user.tenant_id)
    
    period = ReportPeriod(date_from=request.date_from, date_to=request.date_to)
    
    report_data = await reporting.get_profit_loss(
        period=period,
        include_zero_balances=request.include_zero_balances
    )
    
    file_buffer = await export.export_profit_loss(
        report_data,
        ReportFormat(format)
    )
    
    content_types = {
        "pdf": "application/pdf",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "csv": "text/csv",
        "json": "application/json"
    }
    extensions = {"pdf": "pdf", "excel": "xlsx", "csv": "csv", "json": "json"}
    
    filename = f"profit_loss_{request.date_from}_{request.date_to}.{extensions[format]}"
    
    return StreamingResponse(
        file_buffer,
        media_type=content_types[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.post(
    "/export/sales-analysis",
    summary="Export Sales Analysis",
    description="Export sales analysis to PDF, Excel, or CSV"
)
async def export_sales_analysis(
    request: SalesAnalysisRequest,
    format: str = Query("excel", regex="^(pdf|excel|csv|json)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("reports.all.export"))
):
    """Export sales analysis report."""
    reporting = ReportingService(db, current_user.tenant_id)
    export = ExportService(current_user.tenant_id)
    
    period = ReportPeriod(date_from=request.date_from, date_to=request.date_to)
    
    report_data = await reporting.get_sales_analysis(
        period=period,
        group_by=request.group_by
    )
    
    file_buffer = await export.export_sales_analysis(
        report_data,
        ReportFormat(format)
    )
    
    content_types = {
        "pdf": "application/pdf",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "csv": "text/csv",
        "json": "application/json"
    }
    extensions = {"pdf": "pdf", "excel": "xlsx", "csv": "csv", "json": "json"}
    
    filename = f"sales_analysis_{request.date_from}_{request.date_to}.{extensions[format]}"
    
    return StreamingResponse(
        file_buffer,
        media_type=content_types[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.post(
    "/export/inventory-valuation",
    summary="Export Inventory Valuation",
    description="Export inventory valuation to PDF, Excel, or CSV"
)
async def export_inventory_valuation(
    request: InventoryValuationRequest,
    format: str = Query("excel", regex="^(pdf|excel|csv|json)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("reports.all.export"))
):
    """Export inventory valuation report."""
    reporting = ReportingService(db, current_user.tenant_id)
    export = ExportService(current_user.tenant_id)
    
    report_data = await reporting.get_inventory_valuation(
        as_of_date=request.as_of_date,
        valuation_method=ValuationMethodReport(request.valuation_method)
    )
    
    file_buffer = await export.export_inventory_valuation(
        report_data,
        ReportFormat(format)
    )
    
    content_types = {
        "pdf": "application/pdf",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "csv": "text/csv",
        "json": "application/json"
    }
    extensions = {"pdf": "pdf", "excel": "xlsx", "csv": "csv", "json": "json"}
    
    filename = f"inventory_valuation_{request.as_of_date}.{extensions[format]}"
    
    return StreamingResponse(
        file_buffer,
        media_type=content_types[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
