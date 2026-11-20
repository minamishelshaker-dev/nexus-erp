"""
Nexus ERP Pydantic Schemas Package
===================================

This package contains all Pydantic schemas for API validation and serialization.
"""

# User schemas
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserListResponse,
    RoleCreate, RoleResponse, PermissionResponse
)

# CRM schemas
from app.schemas.crm import (
    CustomerCreate, CustomerUpdate, CustomerResponse, CustomerListResponse,
    LeadCreate, LeadUpdate, LeadResponse
)

# Accounting schemas
from app.schemas.accounting import (
    AccountCreate, AccountUpdate, AccountResponse, AccountListResponse,
    JournalEntryCreate, JournalEntryUpdate, JournalEntryResponse,
    JournalItemCreate, JournalItemResponse,
    TrialBalanceResponse, IncomeStatementResponse, BalanceSheetResponse
)

# Inventory schemas
from app.schemas.inventory import (
    ProductCreate, ProductUpdate, ProductResponse, ProductListResponse,
    WarehouseCreate, WarehouseResponse,
    StockMoveCreate, StockMoveResponse, StockMoveListResponse,
    InventoryAdjustmentCreate, InventoryAdjustmentResponse
)

# Sales schemas
from app.schemas.sales import (
    QuotationCreate, QuotationUpdate, QuotationResponse, QuotationListResponse,
    QuotationLineCreate, QuotationLineResponse,
    SaleOrderCreate, SaleOrderUpdate, SaleOrderResponse, SaleOrderListResponse,
    SaleOrderLineCreate, SaleOrderLineResponse,
    InvoiceCreate, InvoiceUpdate, InvoiceResponse, InvoiceListResponse,
    InvoiceLineCreate, InvoiceLineResponse,
    PaymentCreate, PaymentUpdate, PaymentResponse, PaymentListResponse,
    QuotationSendRequest, QuotationConfirmRequest,
    SaleOrderConfirmRequest, InvoicePostRequest, PaymentRegisterRequest
)

# Purchase schemas
from app.schemas.purchase import (
    PurchaseOrderCreate, PurchaseOrderUpdate, PurchaseOrderResponse, PurchaseOrderListResponse,
    PurchaseOrderLineCreate, PurchaseOrderLineResponse,
    ReceiptCreate, ReceiptUpdate, ReceiptResponse, ReceiptListResponse,
    ReceiptLineCreate, ReceiptLineResponse,
    PurchaseInvoiceCreate, PurchaseInvoiceUpdate, PurchaseInvoiceResponse, PurchaseInvoiceListResponse,
    PurchaseInvoiceLineCreate, PurchaseInvoiceLineResponse,
    PurchaseOrderConfirmRequest, ReceiptConfirmRequest,
    PurchaseInvoicePostRequest, CreateReceiptFromPORequest
)

__all__ = [
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserListResponse",
    "RoleCreate",
    "RoleResponse",
    "PermissionResponse",
    
    # CRM
    "CustomerCreate",
    "CustomerUpdate",
    "CustomerResponse",
    "CustomerListResponse",
    "LeadCreate",
    "LeadUpdate",
    "LeadResponse",
    
    # Accounting
    "AccountCreate",
    "AccountUpdate",
    "AccountResponse",
    "AccountListResponse",
    "JournalEntryCreate",
    "JournalEntryUpdate",
    "JournalEntryResponse",
    "JournalItemCreate",
    "JournalItemResponse",
    "TrialBalanceResponse",
    "IncomeStatementResponse",
    "BalanceSheetResponse",
    
    # Inventory
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    "ProductListResponse",
    "WarehouseCreate",
    "WarehouseResponse",
    "StockMoveCreate",
    "StockMoveResponse",
    "StockMoveListResponse",
    "InventoryAdjustmentCreate",
    "InventoryAdjustmentResponse",
    
    # Sales
    "QuotationCreate",
    "QuotationUpdate",
    "QuotationResponse",
    "QuotationListResponse",
    "QuotationLineCreate",
    "QuotationLineResponse",
    "SaleOrderCreate",
    "SaleOrderUpdate",
    "SaleOrderResponse",
    "SaleOrderListResponse",
    "SaleOrderLineCreate",
    "SaleOrderLineResponse",
    "InvoiceCreate",
    "InvoiceUpdate",
    "InvoiceResponse",
    "InvoiceListResponse",
    "InvoiceLineCreate",
    "InvoiceLineResponse",
    "PaymentCreate",
    "PaymentUpdate",
    "PaymentResponse",
    "PaymentListResponse",
    "QuotationSendRequest",
    "QuotationConfirmRequest",
    "SaleOrderConfirmRequest",
    "InvoicePostRequest",
    "PaymentRegisterRequest",
    
    # Purchase
    "PurchaseOrderCreate",
    "PurchaseOrderUpdate",
    "PurchaseOrderResponse",
    "PurchaseOrderListResponse",
    "PurchaseOrderLineCreate",
    "PurchaseOrderLineResponse",
    "ReceiptCreate",
    "ReceiptUpdate",
    "ReceiptResponse",
    "ReceiptListResponse",
    "ReceiptLineCreate",
    "ReceiptLineResponse",
    "PurchaseInvoiceCreate",
    "PurchaseInvoiceUpdate",
    "PurchaseInvoiceResponse",
    "PurchaseInvoiceListResponse",
    "PurchaseInvoiceLineCreate",
    "PurchaseInvoiceLineResponse",
    "PurchaseOrderConfirmRequest",
    "ReceiptConfirmRequest",
    "PurchaseInvoicePostRequest",
    "CreateReceiptFromPORequest",
]
