/**
 * Nexus ERP - Purchasing API Service
 * API functions for purchasing module
 */

import api, { PaginatedResponse } from './api'

// Types
export interface Supplier {
  id: string
  code: string
  name: string
  contact_person: string
  email: string
  phone: string
  website?: string
  address: string
  city: string
  country: string
  tax_id?: string
  payment_terms: string
  payment_terms_id?: string
  currency: string
  is_active: boolean
  rating: number
  total_orders: number
  total_purchases: number
  outstanding_balance: number
  bank_name?: string
  bank_account?: string
  notes?: string
  created_at: string
}

export interface PurchaseOrder {
  id: string
  number: string
  name: string
  supplier_id: string
  supplier_name: string
  date_order: string
  delivery_date?: string
  state: 'draft' | 'confirmed' | 'approved' | 'done' | 'cancelled'
  amount_untaxed: number
  amount_tax: number
  amount_total: number
  receipt_status: 'no' | 'partial' | 'done'
  invoice_status: 'no' | 'partial' | 'invoiced'
  currency: string
  warehouse_id?: string
  warehouse_name?: string
  lines: PurchaseOrderLine[]
  notes?: string
  created_by: string
  created_at: string
}

export interface PurchaseOrderLine {
  id: string
  product_id: string
  product_name: string
  product_code: string
  description: string
  quantity: number
  qty_received: number
  qty_invoiced: number
  uom: string
  price_unit: number
  discount: number
  price_subtotal: number
  tax_id?: string
  tax_name?: string
  date_planned?: string
}

export interface PurchaseReceipt {
  id: string
  number: string
  name: string
  purchase_order_id?: string
  purchase_order_number?: string
  supplier_id: string
  supplier_name: string
  warehouse_id: string
  warehouse_name: string
  date: string
  state: 'draft' | 'confirmed' | 'done' | 'cancelled'
  lines: PurchaseReceiptLine[]
  notes?: string
  created_by: string
  created_at: string
}

export interface PurchaseReceiptLine {
  id: string
  product_id: string
  product_name: string
  product_code: string
  quantity_ordered: number
  quantity_received: number
  uom: string
  lot_number?: string
  expiry_date?: string
}

export interface PurchaseInvoice {
  id: string
  number: string
  supplier_invoice_number?: string
  supplier_id: string
  supplier_name: string
  date: string
  due_date: string
  state: 'draft' | 'posted' | 'paid' | 'cancelled'
  amount_untaxed: number
  amount_tax: number
  amount_total: number
  amount_due: number
  currency: string
  lines: PurchaseInvoiceLine[]
  created_at: string
}

export interface PurchaseInvoiceLine {
  id: string
  product_id: string
  product_name: string
  description: string
  quantity: number
  uom: string
  price_unit: number
  price_subtotal: number
}

// API Functions
export const purchasingApi = {
  // Suppliers
  listSuppliers: async (params?: {
    page?: number
    page_size?: number
    search?: string
    is_active?: boolean
    country?: string
  }) => {
    const response = await api.get('/purchasing/suppliers', { params })
    return response.data as PaginatedResponse<Supplier>
  },

  getSupplier: async (id: string) => {
    const response = await api.get(`/purchasing/suppliers/${id}`)
    return response.data as Supplier
  },

  createSupplier: async (data: Partial<Supplier>) => {
    const response = await api.post('/purchasing/suppliers', data)
    return response.data as Supplier
  },

  updateSupplier: async (id: string, data: Partial<Supplier>) => {
    const response = await api.put(`/purchasing/suppliers/${id}`, data)
    return response.data as Supplier
  },

  deleteSupplier: async (id: string) => {
    await api.delete(`/purchasing/suppliers/${id}`)
  },

  getSupplierProducts: async (id: string) => {
    const response = await api.get(`/purchasing/suppliers/${id}/products`)
    return response.data
  },

  // Purchase Orders
  listPurchaseOrders: async (params?: {
    page?: number
    page_size?: number
    search?: string
    state?: string
    supplier_id?: string
    date_from?: string
    date_to?: string
  }) => {
    const response = await api.get('/purchase/orders', { params })
    return response.data as PaginatedResponse<PurchaseOrder>
  },

  getPurchaseOrder: async (id: string) => {
    const response = await api.get(`/purchase/orders/${id}`)
    return response.data as PurchaseOrder
  },

  createPurchaseOrder: async (data: Partial<PurchaseOrder>) => {
    const response = await api.post('/purchase/orders', data)
    return response.data as PurchaseOrder
  },

  updatePurchaseOrder: async (id: string, data: Partial<PurchaseOrder>) => {
    const response = await api.put(`/purchase/orders/${id}`, data)
    return response.data as PurchaseOrder
  },

  deletePurchaseOrder: async (id: string) => {
    await api.delete(`/purchase/orders/${id}`)
  },

  confirmPurchaseOrder: async (id: string) => {
    const response = await api.post(`/purchase/orders/${id}/confirm`)
    return response.data
  },

  approvePurchaseOrder: async (id: string) => {
    const response = await api.post(`/purchase/orders/${id}/approve`)
    return response.data
  },

  cancelPurchaseOrder: async (id: string, reason?: string) => {
    const response = await api.post(`/purchase/orders/${id}/cancel`, { reason })
    return response.data
  },

  createReceiptFromOrder: async (id: string) => {
    const response = await api.post('/purchase/receipts/from-order', { purchase_order_id: id })
    return response.data as PurchaseReceipt
  },

  createInvoiceFromOrder: async (id: string) => {
    const response = await api.post(`/purchase/orders/${id}/invoice`)
    return response.data as PurchaseInvoice
  },

  // Purchase Receipts
  listPurchaseReceipts: async (params?: {
    page?: number
    page_size?: number
    search?: string
    supplier_id?: string
    state?: string
  }) => {
    const response = await api.get('/purchase/receipts', { params })
    return response.data as PaginatedResponse<PurchaseReceipt>
  },

  getPurchaseReceipt: async (id: string) => {
    const response = await api.get(`/purchase/receipts/${id}`)
    return response.data as PurchaseReceipt
  },

  confirmPurchaseReceipt: async (id: string) => {
    const response = await api.post(`/purchase/receipts/${id}/confirm`)
    return response.data
  },

  // Purchase Invoices
  listPurchaseInvoices: async (params?: {
    page?: number
    page_size?: number
    search?: string
    supplier_id?: string
    state?: string
  }) => {
    const response = await api.get('/purchase/invoices', { params })
    return response.data as PaginatedResponse<PurchaseInvoice>
  },

  getPurchaseInvoice: async (id: string) => {
    const response = await api.get(`/purchase/invoices/${id}`)
    return response.data as PurchaseInvoice
  },

  postPurchaseInvoice: async (id: string) => {
    const response = await api.post(`/purchase/invoices/${id}/post`)
    return response.data
  },

  payPurchaseInvoice: async (id: string, paymentData: { amount: number; payment_method: string; date: string }) => {
    const response = await api.post(`/purchase/invoices/${id}/pay`, paymentData)
    return response.data
  },

  // Reports
  getSupplierPerformance: async (supplierId: string) => {
    const response = await api.get(`/purchasing/suppliers/${supplierId}/performance`)
    return response.data
  },

  getPurchaseAnalysis: async (params?: {
    supplier_id?: string
    product_id?: string
    date_from?: string
    date_to?: string
  }) => {
    const response = await api.get('/purchase/reports/analysis', { params })
    return response.data
  },
}

export default purchasingApi
