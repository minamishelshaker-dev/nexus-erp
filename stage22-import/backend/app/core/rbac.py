"""
Nexus ERP - Role-Based Access Control (RBAC)
=============================================

This module provides comprehensive role-based access control for the ERP system.
Implements permission definitions, role management, and access checking.

Features:
- Permission definitions (module.resource.action format)
- Role definitions with permission mappings
- require_permission() decorator
- check_access() function
- Dynamic permission checking
- Tenant-scoped roles
"""

from typing import Optional, List, Dict, Set, Callable, Any
from functools import wraps
from enum import Enum
import logging
import asyncio

from fastapi import HTTPException, status, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.security import get_current_user
from app.core.database import get_db
from app.models.user import User, Role, Permission

logger = logging.getLogger(__name__)


# ========================================
# Permission Definitions
# ========================================

class PermissionCode:
    """
    Permission code constants.
    
    Format: module.resource.action
    
    Modules:
    - inventory: Inventory management
    - sales: Sales and quotations
    - purchase: Purchase orders
    - accounting: Financial accounting
    - crm: Customer relationship management
    - manufacturing: Manufacturing operations
    - users: User management
    - reports: Reporting
    - settings: System settings
    - admin: Administrative functions
    """
    
    # ========================================
    # Inventory Permissions
    # ========================================
    INVENTORY_VIEW = "inventory.products.view"
    INVENTORY_CREATE = "inventory.products.create"
    INVENTORY_UPDATE = "inventory.products.update"
    INVENTORY_DELETE = "inventory.products.delete"
    INVENTORY_EXPORT = "inventory.products.export"
    INVENTORY_IMPORT = "inventory.products.import"
    
    INVENTORY_WAREHOUSE_VIEW = "inventory.warehouse.view"
    INVENTORY_WAREHOUSE_CREATE = "inventory.warehouse.create"
    INVENTORY_WAREHOUSE_UPDATE = "inventory.warehouse.update"
    INVENTORY_WAREHOUSE_DELETE = "inventory.warehouse.delete"
    
    INVENTORY_STOCK_VIEW = "inventory.stock.view"
    INVENTORY_STOCK_ADJUST = "inventory.stock.adjust"
    INVENTORY_STOCK_TRANSFER = "inventory.stock.transfer"
    
    INVENTORY_MOVEMENTS_VIEW = "inventory.movements.view"
    INVENTORY_MOVEMENTS_CREATE = "inventory.movements.create"
    
    # ========================================
    # Sales Permissions
    # ========================================
    SALES_VIEW = "sales.orders.view"
    SALES_CREATE = "sales.orders.create"
    SALES_UPDATE = "sales.orders.update"
    SALES_DELETE = "sales.orders.delete"
    SALES_APPROVE = "sales.orders.approve"
    SALES_CANCEL = "sales.orders.cancel"
    
    SALES_QUOTATION_VIEW = "sales.quotations.view"
    SALES_QUOTATION_CREATE = "sales.quotations.create"
    SALES_QUOTATION_UPDATE = "sales.quotations.update"
    SALES_QUOTATION_DELETE = "sales.quotations.delete"
    SALES_QUOTATION_CONVERT = "sales.quotations.convert"
    
    SALES_INVOICE_VIEW = "sales.invoices.view"
    SALES_INVOICE_CREATE = "sales.invoices.create"
    SALES_INVOICE_UPDATE = "sales.invoices.update"
    SALES_INVOICE_DELETE = "sales.invoices.delete"
    
    # ========================================
    # Purchase Permissions
    # ========================================
    PURCHASE_VIEW = "purchase.orders.view"
    PURCHASE_CREATE = "purchase.orders.create"
    PURCHASE_UPDATE = "purchase.orders.update"
    PURCHASE_DELETE = "purchase.orders.delete"
    PURCHASE_APPROVE = "purchase.orders.approve"
    PURCHASE_CANCEL = "purchase.orders.cancel"
    
    PURCHASE_RFQ_VIEW = "purchase.rfq.view"
    PURCHASE_RFQ_CREATE = "purchase.rfq.create"
    PURCHASE_RFQ_UPDATE = "purchase.rfq.update"
    PURCHASE_RFQ_DELETE = "purchase.rfq.delete"
    
    PURCHASE_RECEIPT_VIEW = "purchase.receipt.view"
    PURCHASE_RECEIPT_CREATE = "purchase.receipt.create"
    PURCHASE_INVOICE_VIEW = "purchase.invoice.read"
    PURCHASE_INVOICE_CREATE = "purchase.invoice.create"
    PURCHASE_INVOICE_UPDATE = "purchase.invoice.update"
    
    # ========================================
    # Accounting Permissions
    # ========================================
    ACCOUNTING_VIEW = "accounting.accounts.view"
    ACCOUNTING_CREATE = "accounting.accounts.create"
    ACCOUNTING_UPDATE = "accounting.accounts.update"
    ACCOUNTING_DELETE = "accounting.accounts.delete"
    
    ACCOUNTING_JOURNAL_VIEW = "accounting.journal.view"
    ACCOUNTING_JOURNAL_CREATE = "accounting.journal.create"
    ACCOUNTING_JOURNAL_UPDATE = "accounting.journal.update"
    ACCOUNTING_JOURNAL_DELETE = "accounting.journal.delete"
    ACCOUNTING_JOURNAL_POST = "accounting.journal.post"
    ACCOUNTING_JOURNAL_REVERSE = "accounting.journal.reverse"
    
    ACCOUNTING_REPORT_VIEW = "accounting.reports.view"
    ACCOUNTING_REPORT_EXPORT = "accounting.reports.export"
    
    ACCOUNTING_PERIOD_OPEN = "accounting.period.open"
    ACCOUNTING_PERIOD_CLOSE = "accounting.period.close"
    
    # ========================================
    # CRM Permissions
    # ========================================
    CRM_CUSTOMER_VIEW = "crm.customers.view"
    CRM_CUSTOMER_CREATE = "crm.customers.create"
    CRM_CUSTOMER_UPDATE = "crm.customers.update"
    CRM_CUSTOMER_DELETE = "crm.customers.delete"
    CRM_CUSTOMER_EXPORT = "crm.customers.export"
    
    CRM_LEAD_VIEW = "crm.leads.view"
    CRM_LEAD_CREATE = "crm.leads.create"
    CRM_LEAD_UPDATE = "crm.leads.update"
    CRM_LEAD_DELETE = "crm.leads.delete"
    CRM_LEAD_CONVERT = "crm.leads.convert"
    
    CRM_OPPORTUNITY_VIEW = "crm.opportunities.view"
    CRM_OPPORTUNITY_CREATE = "crm.opportunities.create"
    CRM_OPPORTUNITY_UPDATE = "crm.opportunities.update"
    CRM_OPPORTUNITY_DELETE = "crm.opportunities.delete"
    
    # ========================================
    # Manufacturing Permissions
    # ========================================
    MANUFACTURING_VIEW = "manufacturing.orders.view"
    MANUFACTURING_CREATE = "manufacturing.orders.create"
    MANUFACTURING_UPDATE = "manufacturing.orders.update"
    MANUFACTURING_DELETE = "manufacturing.orders.delete"
    MANUFACTURING_APPROVE = "manufacturing.orders.approve"
    MANUFACTURING_CANCEL = "manufacturing.orders.cancel"
    
    MANUFACTURING_BOM_VIEW = "manufacturing.bom.view"
    MANUFACTURING_BOM_CREATE = "manufacturing.bom.create"
    MANUFACTURING_BOM_UPDATE = "manufacturing.bom.update"
    MANUFACTURING_BOM_DELETE = "manufacturing.bom.delete"
    
    MANUFACTURING_WORKCENTER_VIEW = "manufacturing.workcenter.view"
    MANUFACTURING_WORKCENTER_MANAGE = "manufacturing.workcenter.manage"
    
    # ========================================
    # User Management Permissions
    # ========================================
    USERS_VIEW = "users.users.view"
    USERS_CREATE = "users.users.create"
    USERS_UPDATE = "users.users.update"
    USERS_DELETE = "users.users.delete"
    USERS_IMPERSONATE = "users.users.impersonate"
    
    USERS_ROLE_VIEW = "users.roles.view"
    USERS_ROLE_CREATE = "users.roles.create"
    USERS_ROLE_UPDATE = "users.roles.update"
    USERS_ROLE_DELETE = "users.roles.delete"
    
    # ========================================
    # Reports Permissions
    # ========================================
    REPORTS_VIEW = "reports.all.view"
    REPORTS_EXPORT = "reports.all.export"
    REPORTS_SCHEDULE = "reports.all.schedule"
    REPORTS_DASHBOARD_MANAGE = "reports.dashboard.manage"
    
    # ========================================
    # Settings Permissions
    # ========================================
    SETTINGS_VIEW = "settings.general.view"
    SETTINGS_UPDATE = "settings.general.update"
    
    SETTINGS_COMPANY_VIEW = "settings.company.view"
    SETTINGS_COMPANY_UPDATE = "settings.company.update"
    
    SETTINGS_INTEGRATION_VIEW = "settings.integrations.view"
    SETTINGS_INTEGRATION_MANAGE = "settings.integrations.manage"
    
    # ========================================
    # Admin Permissions
    # ========================================
    ADMIN_FULL_ACCESS = "admin.full.access"
    ADMIN_TENANT_MANAGE = "admin.tenant.manage"
    ADMIN_BILLING_MANAGE = "admin.billing.manage"
    ADMIN_AUDIT_VIEW = "admin.audit.view"
    ADMIN_BACKUP_MANAGE = "admin.backup.manage"


# ========================================
# Role Definitions
# ========================================

class RoleCode:
    """Role code constants."""
    
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    ACCOUNTANT = "accountant"
    SALES_MANAGER = "sales_manager"
    SALES_REP = "sales_rep"
    PURCHASE_MANAGER = "purchase_manager"
    PURCHASE_REP = "purchase_rep"
    INVENTORY_MANAGER = "inventory_manager"
    INVENTORY_CLERK = "inventory_clerk"
    CRM_MANAGER = "crm_manager"
    CRM_REP = "crm_rep"
    MANUFACTURING_MANAGER = "manufacturing_manager"
    PRODUCTION_SUPERVISOR = "production_supervisor"
    VIEWER = "viewer"


# ========================================
# Role Permission Mappings
# ========================================

ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    # Super Admin - Full access
    RoleCode.SUPER_ADMIN: {
        PermissionCode.ADMIN_FULL_ACCESS,
    },
    
    # Admin - Almost full access within tenant
    RoleCode.ADMIN: {
        # Inventory
        PermissionCode.INVENTORY_VIEW,
        PermissionCode.INVENTORY_CREATE,
        PermissionCode.INVENTORY_UPDATE,
        PermissionCode.INVENTORY_DELETE,
        PermissionCode.INVENTORY_EXPORT,
        PermissionCode.INVENTORY_IMPORT,
        PermissionCode.INVENTORY_WAREHOUSE_VIEW,
        PermissionCode.INVENTORY_WAREHOUSE_CREATE,
        PermissionCode.INVENTORY_WAREHOUSE_UPDATE,
        PermissionCode.INVENTORY_WAREHOUSE_DELETE,
        PermissionCode.INVENTORY_STOCK_VIEW,
        PermissionCode.INVENTORY_STOCK_ADJUST,
        PermissionCode.INVENTORY_STOCK_TRANSFER,
        PermissionCode.INVENTORY_MOVEMENTS_VIEW,
        PermissionCode.INVENTORY_MOVEMENTS_CREATE,
        
        # Sales
        PermissionCode.SALES_VIEW,
        PermissionCode.SALES_CREATE,
        PermissionCode.SALES_UPDATE,
        PermissionCode.SALES_DELETE,
        PermissionCode.SALES_APPROVE,
        PermissionCode.SALES_CANCEL,
        PermissionCode.SALES_QUOTATION_VIEW,
        PermissionCode.SALES_QUOTATION_CREATE,
        PermissionCode.SALES_QUOTATION_UPDATE,
        PermissionCode.SALES_QUOTATION_DELETE,
        PermissionCode.SALES_QUOTATION_CONVERT,
        PermissionCode.SALES_INVOICE_VIEW,
        PermissionCode.SALES_INVOICE_CREATE,
        PermissionCode.SALES_INVOICE_UPDATE,
        PermissionCode.SALES_INVOICE_DELETE,
        
        # Purchase
        PermissionCode.PURCHASE_VIEW,
        PermissionCode.PURCHASE_CREATE,
        PermissionCode.PURCHASE_UPDATE,
        PermissionCode.PURCHASE_DELETE,
        PermissionCode.PURCHASE_APPROVE,
        PermissionCode.PURCHASE_CANCEL,
        PermissionCode.PURCHASE_RFQ_VIEW,
        PermissionCode.PURCHASE_RFQ_CREATE,
        PermissionCode.PURCHASE_RFQ_UPDATE,
        PermissionCode.PURCHASE_RFQ_DELETE,
        PermissionCode.PURCHASE_RECEIPT_VIEW,
        PermissionCode.PURCHASE_RECEIPT_CREATE,
        PermissionCode.PURCHASE_INVOICE_VIEW,
        PermissionCode.PURCHASE_INVOICE_CREATE,
        PermissionCode.PURCHASE_INVOICE_UPDATE,
        
        # Accounting
        PermissionCode.ACCOUNTING_VIEW,
        PermissionCode.ACCOUNTING_CREATE,
        PermissionCode.ACCOUNTING_UPDATE,
        PermissionCode.ACCOUNTING_DELETE,
        PermissionCode.ACCOUNTING_JOURNAL_VIEW,
        PermissionCode.ACCOUNTING_JOURNAL_CREATE,
        PermissionCode.ACCOUNTING_JOURNAL_UPDATE,
        PermissionCode.ACCOUNTING_JOURNAL_DELETE,
        PermissionCode.ACCOUNTING_JOURNAL_POST,
        PermissionCode.ACCOUNTING_JOURNAL_REVERSE,
        PermissionCode.ACCOUNTING_REPORT_VIEW,
        PermissionCode.ACCOUNTING_REPORT_EXPORT,
        PermissionCode.ACCOUNTING_PERIOD_OPEN,
        PermissionCode.ACCOUNTING_PERIOD_CLOSE,
        
        # CRM
        PermissionCode.CRM_CUSTOMER_VIEW,
        PermissionCode.CRM_CUSTOMER_CREATE,
        PermissionCode.CRM_CUSTOMER_UPDATE,
        PermissionCode.CRM_CUSTOMER_DELETE,
        PermissionCode.CRM_CUSTOMER_EXPORT,
        PermissionCode.CRM_LEAD_VIEW,
        PermissionCode.CRM_LEAD_CREATE,
        PermissionCode.CRM_LEAD_UPDATE,
        PermissionCode.CRM_LEAD_DELETE,
        PermissionCode.CRM_LEAD_CONVERT,
        PermissionCode.CRM_OPPORTUNITY_VIEW,
        PermissionCode.CRM_OPPORTUNITY_CREATE,
        PermissionCode.CRM_OPPORTUNITY_UPDATE,
        PermissionCode.CRM_OPPORTUNITY_DELETE,
        
        # Manufacturing
        PermissionCode.MANUFACTURING_VIEW,
        PermissionCode.MANUFACTURING_CREATE,
        PermissionCode.MANUFACTURING_UPDATE,
        PermissionCode.MANUFACTURING_DELETE,
        PermissionCode.MANUFACTURING_APPROVE,
        PermissionCode.MANUFACTURING_CANCEL,
        PermissionCode.MANUFACTURING_BOM_VIEW,
        PermissionCode.MANUFACTURING_BOM_CREATE,
        PermissionCode.MANUFACTURING_BOM_UPDATE,
        PermissionCode.MANUFACTURING_BOM_DELETE,
        PermissionCode.MANUFACTURING_WORKCENTER_VIEW,
        PermissionCode.MANUFACTURING_WORKCENTER_MANAGE,
        
        # Users
        PermissionCode.USERS_VIEW,
        PermissionCode.USERS_CREATE,
        PermissionCode.USERS_UPDATE,
        PermissionCode.USERS_DELETE,
        PermissionCode.USERS_ROLE_VIEW,
        PermissionCode.USERS_ROLE_CREATE,
        PermissionCode.USERS_ROLE_UPDATE,
        PermissionCode.USERS_ROLE_DELETE,
        
        # Reports
        PermissionCode.REPORTS_VIEW,
        PermissionCode.REPORTS_EXPORT,
        PermissionCode.REPORTS_SCHEDULE,
        PermissionCode.REPORTS_DASHBOARD_MANAGE,
        
        # Settings
        PermissionCode.SETTINGS_VIEW,
        PermissionCode.SETTINGS_UPDATE,
        PermissionCode.SETTINGS_COMPANY_VIEW,
        PermissionCode.SETTINGS_COMPANY_UPDATE,
        PermissionCode.SETTINGS_INTEGRATION_VIEW,
        PermissionCode.SETTINGS_INTEGRATION_MANAGE,
        
        # Admin
        PermissionCode.ADMIN_AUDIT_VIEW,
        PermissionCode.ADMIN_BILLING_MANAGE,
    },
    
    # Manager - Department management
    RoleCode.MANAGER: {
        PermissionCode.INVENTORY_VIEW,
        PermissionCode.INVENTORY_CREATE,
        PermissionCode.INVENTORY_UPDATE,
        PermissionCode.INVENTORY_EXPORT,
        PermissionCode.INVENTORY_WAREHOUSE_VIEW,
        PermissionCode.INVENTORY_STOCK_VIEW,
        PermissionCode.INVENTORY_STOCK_ADJUST,
        
        PermissionCode.SALES_VIEW,
        PermissionCode.SALES_CREATE,
        PermissionCode.SALES_UPDATE,
        PermissionCode.SALES_APPROVE,
        PermissionCode.SALES_QUOTATION_VIEW,
        PermissionCode.SALES_QUOTATION_CREATE,
        PermissionCode.SALES_QUOTATION_UPDATE,
        PermissionCode.SALES_QUOTATION_CONVERT,
        PermissionCode.SALES_INVOICE_VIEW,
        PermissionCode.SALES_INVOICE_CREATE,
        
        PermissionCode.PURCHASE_VIEW,
        PermissionCode.PURCHASE_CREATE,
        PermissionCode.PURCHASE_UPDATE,
        PermissionCode.PURCHASE_APPROVE,
        
        PermissionCode.ACCOUNTING_VIEW,
        PermissionCode.ACCOUNTING_JOURNAL_VIEW,
        PermissionCode.ACCOUNTING_REPORT_VIEW,
        PermissionCode.ACCOUNTING_REPORT_EXPORT,
        
        PermissionCode.CRM_CUSTOMER_VIEW,
        PermissionCode.CRM_CUSTOMER_CREATE,
        PermissionCode.CRM_CUSTOMER_UPDATE,
        PermissionCode.CRM_LEAD_VIEW,
        PermissionCode.CRM_LEAD_CREATE,
        PermissionCode.CRM_LEAD_UPDATE,
        PermissionCode.CRM_LEAD_CONVERT,
        
        PermissionCode.USERS_VIEW,
        
        PermissionCode.REPORTS_VIEW,
        PermissionCode.REPORTS_EXPORT,
        PermissionCode.REPORTS_DASHBOARD_MANAGE,
    },
    
    # Accountant - Financial operations
    RoleCode.ACCOUNTANT: {
        PermissionCode.INVENTORY_VIEW,
        PermissionCode.INVENTORY_STOCK_VIEW,
        
        PermissionCode.SALES_VIEW,
        PermissionCode.SALES_INVOICE_VIEW,
        PermissionCode.SALES_INVOICE_CREATE,
        
        PermissionCode.PURCHASE_VIEW,
        PermissionCode.PURCHASE_RECEIPT_VIEW,
        PermissionCode.PURCHASE_INVOICE_VIEW,
        PermissionCode.PURCHASE_INVOICE_CREATE,
        PermissionCode.PURCHASE_INVOICE_UPDATE,
        
        PermissionCode.ACCOUNTING_VIEW,
        PermissionCode.ACCOUNTING_CREATE,
        PermissionCode.ACCOUNTING_UPDATE,
        PermissionCode.ACCOUNTING_JOURNAL_VIEW,
        PermissionCode.ACCOUNTING_JOURNAL_CREATE,
        PermissionCode.ACCOUNTING_JOURNAL_UPDATE,
        PermissionCode.ACCOUNTING_JOURNAL_POST,
        PermissionCode.ACCOUNTING_JOURNAL_REVERSE,
        PermissionCode.ACCOUNTING_REPORT_VIEW,
        PermissionCode.ACCOUNTING_REPORT_EXPORT,
        PermissionCode.ACCOUNTING_PERIOD_CLOSE,
        
        PermissionCode.REPORTS_VIEW,
        PermissionCode.REPORTS_EXPORT,
    },
    
    # Sales Manager
    RoleCode.SALES_MANAGER: {
        PermissionCode.INVENTORY_VIEW,
        PermissionCode.INVENTORY_STOCK_VIEW,
        
        PermissionCode.SALES_VIEW,
        PermissionCode.SALES_CREATE,
        PermissionCode.SALES_UPDATE,
        PermissionCode.SALES_DELETE,
        PermissionCode.SALES_APPROVE,
        PermissionCode.SALES_CANCEL,
        PermissionCode.SALES_QUOTATION_VIEW,
        PermissionCode.SALES_QUOTATION_CREATE,
        PermissionCode.SALES_QUOTATION_UPDATE,
        PermissionCode.SALES_QUOTATION_DELETE,
        PermissionCode.SALES_QUOTATION_CONVERT,
        PermissionCode.SALES_INVOICE_VIEW,
        PermissionCode.SALES_INVOICE_CREATE,
        PermissionCode.SALES_INVOICE_UPDATE,
        
        PermissionCode.CRM_CUSTOMER_VIEW,
        PermissionCode.CRM_CUSTOMER_CREATE,
        PermissionCode.CRM_CUSTOMER_UPDATE,
        PermissionCode.CRM_CUSTOMER_DELETE,
        PermissionCode.CRM_CUSTOMER_EXPORT,
        PermissionCode.CRM_LEAD_VIEW,
        PermissionCode.CRM_LEAD_CREATE,
        PermissionCode.CRM_LEAD_UPDATE,
        PermissionCode.CRM_LEAD_DELETE,
        PermissionCode.CRM_LEAD_CONVERT,
        PermissionCode.CRM_OPPORTUNITY_VIEW,
        PermissionCode.CRM_OPPORTUNITY_CREATE,
        PermissionCode.CRM_OPPORTUNITY_UPDATE,
        
        PermissionCode.REPORTS_VIEW,
        PermissionCode.REPORTS_EXPORT,
    },
    
    # Sales Representative
    RoleCode.SALES_REP: {
        PermissionCode.INVENTORY_VIEW,
        PermissionCode.INVENTORY_STOCK_VIEW,
        
        PermissionCode.SALES_VIEW,
        PermissionCode.SALES_CREATE,
        PermissionCode.SALES_UPDATE,
        PermissionCode.SALES_QUOTATION_VIEW,
        PermissionCode.SALES_QUOTATION_CREATE,
        PermissionCode.SALES_QUOTATION_UPDATE,
        PermissionCode.SALES_QUOTATION_CONVERT,
        PermissionCode.SALES_INVOICE_VIEW,
        
        PermissionCode.CRM_CUSTOMER_VIEW,
        PermissionCode.CRM_CUSTOMER_CREATE,
        PermissionCode.CRM_CUSTOMER_UPDATE,
        PermissionCode.CRM_LEAD_VIEW,
        PermissionCode.CRM_LEAD_CREATE,
        PermissionCode.CRM_LEAD_UPDATE,
        PermissionCode.CRM_LEAD_CONVERT,
        PermissionCode.CRM_OPPORTUNITY_VIEW,
        PermissionCode.CRM_OPPORTUNITY_CREATE,
    },
    
    # Purchase Manager
    RoleCode.PURCHASE_MANAGER: {
        PermissionCode.INVENTORY_VIEW,
        PermissionCode.INVENTORY_STOCK_VIEW,
        
        PermissionCode.PURCHASE_VIEW,
        PermissionCode.PURCHASE_CREATE,
        PermissionCode.PURCHASE_UPDATE,
        PermissionCode.PURCHASE_DELETE,
        PermissionCode.PURCHASE_APPROVE,
        PermissionCode.PURCHASE_CANCEL,
        PermissionCode.PURCHASE_RFQ_VIEW,
        PermissionCode.PURCHASE_RFQ_CREATE,
        PermissionCode.PURCHASE_RFQ_UPDATE,
        PermissionCode.PURCHASE_RFQ_DELETE,
        PermissionCode.PURCHASE_RECEIPT_VIEW,
        PermissionCode.PURCHASE_RECEIPT_CREATE,
        PermissionCode.PURCHASE_INVOICE_VIEW,
        PermissionCode.PURCHASE_INVOICE_CREATE,
        PermissionCode.PURCHASE_INVOICE_UPDATE,
        
        PermissionCode.REPORTS_VIEW,
        PermissionCode.REPORTS_EXPORT,
    },
    
    # Purchase Representative
    RoleCode.PURCHASE_REP: {
        PermissionCode.INVENTORY_VIEW,
        PermissionCode.INVENTORY_STOCK_VIEW,
        
        PermissionCode.PURCHASE_VIEW,
        PermissionCode.PURCHASE_CREATE,
        PermissionCode.PURCHASE_UPDATE,
        PermissionCode.PURCHASE_RFQ_VIEW,
        PermissionCode.PURCHASE_RFQ_CREATE,
        PermissionCode.PURCHASE_RFQ_UPDATE,
        PermissionCode.PURCHASE_RECEIPT_VIEW,
        PermissionCode.PURCHASE_RECEIPT_CREATE,
    },
    
    # Inventory Manager
    RoleCode.INVENTORY_MANAGER: {
        PermissionCode.INVENTORY_VIEW,
        PermissionCode.INVENTORY_CREATE,
        PermissionCode.INVENTORY_UPDATE,
        PermissionCode.INVENTORY_DELETE,
        PermissionCode.INVENTORY_EXPORT,
        PermissionCode.INVENTORY_IMPORT,
        PermissionCode.INVENTORY_WAREHOUSE_VIEW,
        PermissionCode.INVENTORY_WAREHOUSE_CREATE,
        PermissionCode.INVENTORY_WAREHOUSE_UPDATE,
        PermissionCode.INVENTORY_WAREHOUSE_DELETE,
        PermissionCode.INVENTORY_STOCK_VIEW,
        PermissionCode.INVENTORY_STOCK_ADJUST,
        PermissionCode.INVENTORY_STOCK_TRANSFER,
        PermissionCode.INVENTORY_MOVEMENTS_VIEW,
        PermissionCode.INVENTORY_MOVEMENTS_CREATE,
        
        PermissionCode.PURCHASE_VIEW,
        PermissionCode.PURCHASE_RECEIPT_VIEW,
        
        PermissionCode.REPORTS_VIEW,
        PermissionCode.REPORTS_EXPORT,
    },
    
    # Inventory Clerk
    RoleCode.INVENTORY_CLERK: {
        PermissionCode.INVENTORY_VIEW,
        PermissionCode.INVENTORY_CREATE,
        PermissionCode.INVENTORY_UPDATE,
        PermissionCode.INVENTORY_STOCK_VIEW,
        PermissionCode.INVENTORY_STOCK_ADJUST,
        PermissionCode.INVENTORY_MOVEMENTS_VIEW,
        PermissionCode.INVENTORY_MOVEMENTS_CREATE,
    },
    
    # CRM Manager
    RoleCode.CRM_MANAGER: {
        PermissionCode.CRM_CUSTOMER_VIEW,
        PermissionCode.CRM_CUSTOMER_CREATE,
        PermissionCode.CRM_CUSTOMER_UPDATE,
        PermissionCode.CRM_CUSTOMER_DELETE,
        PermissionCode.CRM_CUSTOMER_EXPORT,
        PermissionCode.CRM_LEAD_VIEW,
        PermissionCode.CRM_LEAD_CREATE,
        PermissionCode.CRM_LEAD_UPDATE,
        PermissionCode.CRM_LEAD_DELETE,
        PermissionCode.CRM_LEAD_CONVERT,
        PermissionCode.CRM_OPPORTUNITY_VIEW,
        PermissionCode.CRM_OPPORTUNITY_CREATE,
        PermissionCode.CRM_OPPORTUNITY_UPDATE,
        PermissionCode.CRM_OPPORTUNITY_DELETE,
        
        PermissionCode.SALES_VIEW,
        PermissionCode.SALES_CREATE,
        
        PermissionCode.REPORTS_VIEW,
        PermissionCode.REPORTS_EXPORT,
    },
    
    # CRM Representative
    RoleCode.CRM_REP: {
        PermissionCode.CRM_CUSTOMER_VIEW,
        PermissionCode.CRM_CUSTOMER_CREATE,
        PermissionCode.CRM_CUSTOMER_UPDATE,
        PermissionCode.CRM_LEAD_VIEW,
        PermissionCode.CRM_LEAD_CREATE,
        PermissionCode.CRM_LEAD_UPDATE,
        PermissionCode.CRM_LEAD_CONVERT,
        PermissionCode.CRM_OPPORTUNITY_VIEW,
        PermissionCode.CRM_OPPORTUNITY_CREATE,
        PermissionCode.CRM_OPPORTUNITY_UPDATE,
    },
    
    # Manufacturing Manager
    RoleCode.MANUFACTURING_MANAGER: {
        PermissionCode.INVENTORY_VIEW,
        PermissionCode.INVENTORY_STOCK_VIEW,
        
        PermissionCode.MANUFACTURING_VIEW,
        PermissionCode.MANUFACTURING_CREATE,
        PermissionCode.MANUFACTURING_UPDATE,
        PermissionCode.MANUFACTURING_DELETE,
        PermissionCode.MANUFACTURING_APPROVE,
        PermissionCode.MANUFACTURING_CANCEL,
        PermissionCode.MANUFACTURING_BOM_VIEW,
        PermissionCode.MANUFACTURING_BOM_CREATE,
        PermissionCode.MANUFACTURING_BOM_UPDATE,
        PermissionCode.MANUFACTURING_BOM_DELETE,
        PermissionCode.MANUFACTURING_WORKCENTER_VIEW,
        PermissionCode.MANUFACTURING_WORKCENTER_MANAGE,
        
        PermissionCode.REPORTS_VIEW,
        PermissionCode.REPORTS_EXPORT,
    },
    
    # Production Supervisor
    RoleCode.PRODUCTION_SUPERVISOR: {
        PermissionCode.INVENTORY_VIEW,
        PermissionCode.INVENTORY_STOCK_VIEW,
        
        PermissionCode.MANUFACTURING_VIEW,
        PermissionCode.MANUFACTURING_CREATE,
        PermissionCode.MANUFACTURING_UPDATE,
        PermissionCode.MANUFACTURING_BOM_VIEW,
        PermissionCode.MANUFACTURING_WORKCENTER_VIEW,
    },
    
    # Viewer - Read-only access
    RoleCode.VIEWER: {
        PermissionCode.INVENTORY_VIEW,
        PermissionCode.INVENTORY_STOCK_VIEW,
        PermissionCode.SALES_VIEW,
        PermissionCode.SALES_QUOTATION_VIEW,
        PermissionCode.SALES_INVOICE_VIEW,
        PermissionCode.PURCHASE_VIEW,
        PermissionCode.ACCOUNTING_VIEW,
        PermissionCode.ACCOUNTING_REPORT_VIEW,
        PermissionCode.CRM_CUSTOMER_VIEW,
        PermissionCode.CRM_LEAD_VIEW,
        PermissionCode.CRM_OPPORTUNITY_VIEW,
        PermissionCode.MANUFACTURING_VIEW,
        PermissionCode.REPORTS_VIEW,
    },
}


# ========================================
# Permission Checking Functions
# ========================================

def check_permission(user_permissions: Set[str], required_permission: str) -> bool:
    """
    Check if user has a specific permission.
    
    Args:
        user_permissions: Set of user's permission codes
        required_permission: Permission code to check
        
    Returns:
        True if user has the permission
    """
    # Super admin has all permissions
    if PermissionCode.ADMIN_FULL_ACCESS in user_permissions:
        return True
    
    # Check for wildcard permissions (e.g., "inventory.*")
    parts = required_permission.split(".")
    if len(parts) >= 2:
        module_wildcard = f"{parts[0]}.*"
        if module_wildcard in user_permissions:
            return True
    
    # Check exact permission
    return required_permission in user_permissions


def check_any_permission(user_permissions: Set[str], required_permissions: List[str]) -> bool:
    """
    Check if user has any of the specified permissions.
    
    Args:
        user_permissions: Set of user's permission codes
        required_permissions: List of permission codes to check
        
    Returns:
        True if user has any of the permissions
    """
    return any(check_permission(user_permissions, p) for p in required_permissions)


def check_all_permissions(user_permissions: Set[str], required_permissions: List[str]) -> bool:
    """
    Check if user has all of the specified permissions.
    
    Args:
        user_permissions: Set of user's permission codes
        required_permissions: List of permission codes to check
        
    Returns:
        True if user has all of the permissions
    """
    return all(check_permission(user_permissions, p) for p in required_permissions)


# ========================================
# Permission Decorator
# ========================================

def require_permission(permission: str):
    """
    Decorator to require a specific permission for an endpoint.
    
    Args:
        permission: Required permission code
        
    Usage:
        @router.post("/products")
        @require_permission(PermissionCode.INVENTORY_CREATE)
        async def create_product(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, current_user: User = None, **kwargs):
            # Get user from kwargs if not provided
            if current_user is None:
                for arg in args:
                    if isinstance(arg, User):
                        current_user = arg
                        break
            
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Superuser bypass
            if current_user.is_superuser:
                return await func(*args, current_user=current_user, **kwargs)
            
            # Check permission
            user_permissions = _get_user_permissions(current_user)
            if not check_permission(user_permissions, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "permission_denied",
                        "message": f"Permission '{permission}' required",
                        "required_permission": permission
                    }
                )
            
            return await func(*args, current_user=current_user, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, current_user: User = None, **kwargs):
            # Get user from kwargs if not provided
            if current_user is None:
                for arg in args:
                    if isinstance(arg, User):
                        current_user = arg
                        break
            
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Superuser bypass
            if current_user.is_superuser:
                return func(*args, current_user=current_user, **kwargs)
            
            # Check permission
            user_permissions = _get_user_permissions(current_user)
            if not check_permission(user_permissions, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "permission_denied",
                        "message": f"Permission '{permission}' required",
                        "required_permission": permission
                    }
                )
            
            return func(*args, current_user=current_user, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def require_any_permission(*permissions: str):
    """
    Decorator to require any of the specified permissions.
    
    Args:
        permissions: Required permission codes (any one)
        
    Usage:
        @router.get("/reports")
        @require_any_permission(PermissionCode.REPORTS_VIEW, PermissionCode.ADMIN_AUDIT_VIEW)
        async def get_reports(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, current_user: User = None, **kwargs):
            if current_user is None:
                for arg in args:
                    if isinstance(arg, User):
                        current_user = arg
                        break
            
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if current_user.is_superuser:
                return await func(*args, current_user=current_user, **kwargs)
            
            user_permissions = _get_user_permissions(current_user)
            if not check_any_permission(user_permissions, list(permissions)):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "permission_denied",
                        "message": f"One of permissions {permissions} required",
                        "required_permissions": list(permissions)
                    }
                )
            
            return await func(*args, current_user=current_user, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return func
    
    return decorator


def require_all_permissions(*permissions: str):
    """
    Decorator to require all of the specified permissions.
    
    Args:
        permissions: Required permission codes (all)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, current_user: User = None, **kwargs):
            if current_user is None:
                for arg in args:
                    if isinstance(arg, User):
                        current_user = arg
                        break
            
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if current_user.is_superuser:
                return await func(*args, current_user=current_user, **kwargs)
            
            user_permissions = _get_user_permissions(current_user)
            if not check_all_permissions(user_permissions, list(permissions)):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "permission_denied",
                        "message": f"All permissions {permissions} required",
                        "required_permissions": list(permissions)
                    }
                )
            
            return await func(*args, current_user=current_user, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return func
    
    return decorator


# ========================================
# Access Check Functions
# ========================================

async def check_access(
    user: User,
    permission: str,
    db: AsyncSession
) -> bool:
    """
    Check if user has access to a specific permission.
    
    This function loads user permissions from the database
    for a complete access check.
    
    Args:
        user: User model instance
        permission: Permission code to check
        db: Database session
        
    Returns:
        True if user has access
    """
    # Superuser has all access
    if user.is_superuser:
        return True
    
    # Get user permissions from database
    user_permissions = await _load_user_permissions(user, db)
    
    return check_permission(user_permissions, permission)


async def check_resource_access(
    user: User,
    resource_type: str,
    action: str,
    db: AsyncSession,
    resource_tenant_id: Optional[str] = None
) -> bool:
    """
    Check if user has access to perform an action on a resource.
    
    Args:
        user: User model instance
        resource_type: Type of resource (e.g., "product", "order")
        action: Action to perform (e.g., "view", "create", "update", "delete")
        db: Database session
        resource_tenant_id: Tenant ID of the resource for cross-tenant check
        
    Returns:
        True if user has access
    """
    # Superuser has all access
    if user.is_superuser:
        return True
    
    # Check tenant isolation
    if resource_tenant_id and str(user.tenant_id) != str(resource_tenant_id):
        return False
    
    # Build permission code
    permission = f"{resource_type}.{action}"
    
    # Get user permissions
    user_permissions = await _load_user_permissions(user, db)
    
    return check_permission(user_permissions, permission)


# ========================================
# FastAPI Dependencies
# ========================================

class PermissionChecker:
    """
    Permission checker dependency for FastAPI.
    
    Usage:
        @router.post("/products")
        async def create_product(
            user: User = Depends(PermissionChecker(PermissionCode.INVENTORY_CREATE))
        ):
            ...
    """
    
    def __init__(self, permission: str):
        self.permission = permission
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_user)
    ) -> User:
        # Superuser bypass
        if current_user.is_superuser:
            return current_user
        
        # Check permission
        user_permissions = _get_user_permissions(current_user)
        if not check_permission(user_permissions, self.permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "permission_denied",
                    "message": f"Permission '{self.permission}' required",
                    "required_permission": self.permission
                }
            )
        
        return current_user


class AnyPermissionChecker:
    """
    Permission checker that requires any of the specified permissions.
    """
    
    def __init__(self, *permissions: str):
        self.permissions = list(permissions)
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_user)
    ) -> User:
        if current_user.is_superuser:
            return current_user
        
        user_permissions = _get_user_permissions(current_user)
        if not check_any_permission(user_permissions, self.permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "permission_denied",
                    "message": f"One of permissions {self.permissions} required",
                    "required_permissions": self.permissions
                }
            )
        
        return current_user


# ========================================
# Helper Functions
# ========================================

def _get_user_permissions(user: User) -> Set[str]:
    """
    Get user's permissions from loaded roles.
    
    Args:
        user: User model instance
        
    Returns:
        Set of permission codes
    """
    permissions = set()
    
    # Get permissions from user's roles
    for role in user.roles:
        if hasattr(role, 'code') and role.code in ROLE_PERMISSIONS:
            permissions.update(ROLE_PERMISSIONS[role.code])
    
    # Add direct permissions if any
    if hasattr(user, 'permissions'):
        for perm in user.permissions:
            if hasattr(perm, 'code'):
                permissions.add(perm.code)
    
    return permissions


async def _load_user_permissions(user: User, db: AsyncSession) -> Set[str]:
    """
    Load user's permissions from database.
    
    Args:
        user: User model instance
        db: Database session
        
    Returns:
        Set of permission codes
    """
    # Load roles with permissions
    result = await db.execute(
        select(User)
        .where(User.id == user.id)
        .options(
            # Eager load roles and permissions
        )
    )
    
    loaded_user = result.scalar_one_or_none()
    
    if not loaded_user:
        return set()
    
    return _get_user_permissions(loaded_user)


def get_role_permissions(role_code: str) -> Set[str]:
    """
    Get permissions for a specific role.
    
    Args:
        role_code: Role code string
        
    Returns:
        Set of permission codes
    """
    return ROLE_PERMISSIONS.get(role_code, set())


def get_all_permissions() -> Set[str]:
    """
    Get all defined permissions.
    
    Returns:
        Set of all permission codes
    """
    all_permissions = set()
    for permissions in ROLE_PERMISSIONS.values():
        all_permissions.update(permissions)
    return all_permissions


def get_all_roles() -> List[str]:
    """
    Get all defined role codes.
    
    Returns:
        List of role codes
    """
    return list(ROLE_PERMISSIONS.keys())


def validate_permission(permission: str) -> bool:
    """
    Validate that a permission code exists.
    
    Args:
        permission: Permission code to validate
        
    Returns:
        True if permission is valid
    """
    return permission in get_all_permissions()


def validate_role(role_code: str) -> bool:
    """
    Validate that a role code exists.
    
    Args:
        role_code: Role code to validate
        
    Returns:
        True if role is valid
    """
    return role_code in ROLE_PERMISSIONS
