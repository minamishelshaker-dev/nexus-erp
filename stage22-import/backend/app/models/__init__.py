"""
Nexus ERP Database Models Package
==================================

This package contains all SQLAlchemy models for the ERP system.

Modules:
- base: Base model with common fields and mixins
- user: User, Role, Permission models
- crm: Customer, Lead, Opportunity models
- accounting: Chart of Accounts, Journal Entries, Financial Reports
- inventory: Product, Warehouse, Stock Move, Inventory Adjustment
- sales: Quotation, Sale Order, Invoice, Payment
- purchase: Purchase Order, Receipt, Purchase Invoice
- ai: Forecast, ChatSession, OCRResult, AIModelConfig
- manufacturing: BOM, WorkCenter, ManufacturingOrder
"""

from app.models.base import BaseModel, TenantMixin, TimestampMixin, SoftDeleteMixin, AuditMixin

# User and Auth
from app.models.user import User, Role, Permission, UserRole, RolePermission

# CRM
from app.models.crm import Customer, Lead, Opportunity, CustomerInteraction as Interaction

# Accounting
from app.models.accounting import (
    Account, AccountType, AccountCategory,
    JournalEntry, JournalItem, EntryState, MoveType,
    Journal, FiscalYear, FiscalPeriod,
    AnalyticAccount, AnalyticLine,
    Reconciliation, Partner, Currency, BankStatement, BankStatementLine, BankStatementState
)

# Inventory
from app.models.inventory import (
    Product, ProductType, ProductStatus, ProductCategory,
    UnitOfMeasure, UOMCategory,
    Warehouse, StockLocation, StockQuantity,
    StockMove, StockMoveType, StockMoveState,
    InventoryAdjustment, AdjustmentLine, AdjustmentState,
    StockLot, StockValuation,
    ValuationMethod
)

# Sales
from app.models.sales import (
    Quotation, QuotationLine, QuotationState,
    SaleOrder, SaleOrderLine, SaleOrderState,
    Invoice, InvoiceLine, InvoiceType, InvoiceState,
    Payment, PaymentInvoice, PaymentReconciliation, PaymentType, PaymentState,
    SalesTeam
)

# Purchase
from app.models.purchase import (
    PurchaseOrder, PurchaseOrderLine, PurchaseOrderState,
    Receipt, ReceiptLine, ReceiptState,
    PurchaseInvoice, PurchaseInvoiceLine, PurchaseInvoiceState,
    SupplierInfo, SupplierPayment, SupplierPaymentAllocation, SupplierPaymentState
)

# AI
from app.models.ai import (
    Forecast, ForecastType, ForecastMethod,
    ChatSession, ChatMessage, ChatMessageType,
    OCRResult, OCRStatus,
    AIModelConfig,
    ProductRecommendation,
    AnomalyDetection
)

# Manufacturing
from app.models.manufacturing import (
    BillOfMaterial, BOMLine, BOMOperation, BOMType, BOMState,
    WorkCenter, WorkCenterState,
    Routing, RoutingStep,
    ManufacturingOrder, MOLine, MOFinish, MOOperation, MOState,
    ProductionPlan, ProductionPlanLine
)

__all__ = [
    # Base
    "BaseModel",
    "TenantMixin",
    "TimestampMixin",
    "SoftDeleteMixin",
    "AuditMixin",
    
    # User & Auth
    "User",
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
    
    # CRM
    "Customer",
    "Lead",
    "Opportunity",
    "Interaction",
    
    # Accounting
    "Account",
    "AccountType",
    "AccountCategory",
    "JournalEntry",
    "JournalItem",
    "EntryState",
    "MoveType",
    "Journal",
    "FiscalYear",
    "FiscalPeriod",
    "AnalyticAccount",
    "AnalyticLine",
    "Reconciliation",
    "BankStatement",
    "BankStatementLine",
    "BankStatementState",
    "Partner",
    "Currency",
    
    # Inventory
    "Product",
    "ProductType",
    "ProductStatus",
    "ProductCategory",
    "UnitOfMeasure",
    "UOMCategory",
    "Warehouse",
    "StockLocation",
    "StockQuantity",
    "StockMove",
    "StockMoveType",
    "StockMoveState",
    "InventoryAdjustment",
    "AdjustmentLine",
    "AdjustmentState",
    "StockLot",
    "StockValuation",
    "ValuationMethod",
    
    # Sales
    "Quotation",
    "QuotationLine",
    "QuotationState",
    "SaleOrder",
    "SaleOrderLine",
    "SaleOrderState",
    "Invoice",
    "InvoiceLine",
    "InvoiceType",
    "InvoiceState",
    "Payment",
    "PaymentInvoice",
    "PaymentReconciliation",
    "PaymentType",
    "PaymentState",
    "SalesTeam",
    
    # Purchase
    "PurchaseOrder",
    "PurchaseOrderLine",
    "PurchaseOrderState",
    "Receipt",
    "ReceiptLine",
    "ReceiptState",
    "PurchaseInvoice",
    "PurchaseInvoiceLine",
    "PurchaseInvoiceState",
    "SupplierInfo",
    
    # AI
    "Forecast",
    "ForecastType",
    "ForecastMethod",
    "ChatSession",
    "ChatMessage",
    "ChatMessageType",
    "OCRResult",
    "OCRStatus",
    "AIModelConfig",
    "ProductRecommendation",
    "AnomalyDetection",
    
    # Manufacturing
    "BillOfMaterial",
    "BOMLine",
    "BOMOperation",
    "BOMType",
    "BOMState",
    "WorkCenter",
    "WorkCenterState",
    "Routing",
    "RoutingStep",
    "ManufacturingOrder",
    "MOLine",
    "MOFinish",
    "MOOperation",
    "MOState",
    "ProductionPlan",
    "ProductionPlanLine",
]

# Register the remaining model modules on the shared declarative metadata.
# These modules are imported explicitly because Alembic and create_all must
# see every mapped table, even when a model is not re-exported above.
from app.models import activity as _activity  # noqa: F401,E402
from app.models import company as _company  # noqa: F401,E402
from app.models import notification as _notification  # noqa: F401,E402
from app.models import workflow as _workflow  # noqa: F401,E402
from app.models import tenant as _tenant  # noqa: F401,E402

# Commercial reference/master data models used by CRM and user administration.
from app.models import reference as _reference  # noqa: F401,E402
