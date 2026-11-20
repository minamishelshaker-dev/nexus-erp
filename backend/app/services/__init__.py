"""
Nexus ERP - Services Package
============================

This package contains all business logic services for the ERP system.

Services:
- accounting_service: Chart of accounts, journal entries, financial reports
- sales_service: Quotations, orders, invoices, payments
- inventory_service: Products, stock movements, inventory valuation
- purchase_service: Purchase orders, receipts, supplier invoices
- manufacturing_service: BOMs, work orders, production
- billing_service: Subscription billing, invoicing
- integration_service: External system integrations
- reporting_service: Financial statements, analytics, custom reports
- workflow_service: Workflow automation, approvals, triggers
- notification_service: Multi-channel notifications
- export_service: PDF, Excel, CSV export generation

AI Services (ai/):
- core: AI service base functionality
- llm_provider: LLM integration
- forecasting_service: Demand forecasting
- anomaly_service: Anomaly detection
- nl_query_service: Natural language queries
- assistant_service: AI assistant
- chatbot_service: Chatbot integration
- ocr_service: Document OCR
"""

from app.services.accounting_service import AccountingService
from app.services.sales_service import SalesService
from app.services.inventory_service import InventoryService
from app.services.purchase_service import PurchaseService
from app.services.manufacturing_service import ManufacturingService
from app.services.billing_service import BillingService
from app.services.integration_service import IntegrationService

__all__ = [
    "AccountingService",
    "SalesService",
    "InventoryService",
    "PurchaseService",
    "ManufacturingService",
    "BillingService",
    "IntegrationService",
]
