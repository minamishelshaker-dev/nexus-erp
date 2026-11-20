/**
 * Nexus ERP - POS API Service
 * API functions for Point of Sale module
 */

import api, { PaginatedResponse } from './api'

// Types
export interface POSConfig {
  id: string
  name: string
  warehouse_id: string
  warehouse_name: string
  journal_id: string
  journal_name: string
  is_active: boolean
  allow_manual_price: boolean
  allow_discount: boolean
  max_discount: number
  allow_negative_stock: boolean
  receipt_header?: string
  receipt_footer?: string
}

export interface POSSession {
  id: string
  config_id: string
  config_name: string
  user_id: string
  user_name: string
  start_time: string
  end_time?: string
  state: 'opened' | 'closed' | 'paused'
  opening_balance: number
  closing_balance?: number
  total_sales: number
  total_transactions: number
  cash_payments: number
  card_payments: number
  other_payments: number
}

export interface POSOrder {
  id: string
  number: string
  session_id: string
  session_name: string
  customer_id?: string
  customer_name?: string
  date: string
  lines: POSOrderLine[]
  amount_untaxed: number
  amount_tax: number
  amount_total: number
  discount_total: number
  state: 'draft' | 'paid' | 'invoiced' | 'cancelled'
  payment_method: string
  payments: POSPayment[]
  notes?: string
  created_by: string
  created_at: string
}

export interface POSOrderLine {
  id: string
  product_id: string
  product_name: string
  product_code: string
  quantity: number
  uom: string
  price_unit: number
  discount: number
  price_subtotal: number
  tax_amount: number
  tax_name?: string
  notes?: string
}

export interface POSPayment {
  id: string
  payment_method: 'cash' | 'card' | 'check' | 'mobile' | 'other'
  amount: number
  reference?: string
  card_number?: string
  card_type?: string
}

export interface POSProduct {
  id: string
  code: string
  name: string
  price: number
  cost: number
  uom: string
  barcode?: string
  category_id: string
  category_name: string
  quantity_available: number
  image_url?: string
  tax_included: boolean
  tax_rate: number
}

export interface POSCategory {
  id: string
  name: string
  parent_id?: string
  product_count: number
  image_url?: string
}

// API Functions
export const posApi = {
  // Config
  getPOSConfigs: async () => {
    const response = await api.get('/pos/configs')
    return response.data as POSConfig[]
  },

  getPOSConfig: async (id: string) => {
    const response = await api.get(`/pos/configs/${id}`)
    return response.data as POSConfig
  },

  createPOSConfig: async (data: Partial<POSConfig>) => {
    const response = await api.post('/pos/configs', data)
    return response.data as POSConfig
  },

  updatePOSConfig: async (id: string, data: Partial<POSConfig>) => {
    const response = await api.put(`/pos/configs/${id}`, data)
    return response.data as POSConfig
  },

  // Sessions
  listSessions: async (params?: {
    page?: number
    page_size?: number
    config_id?: string
    state?: string
    date_from?: string
    date_to?: string
  }) => {
    const response = await api.get('/pos/sessions', { params })
    return response.data as PaginatedResponse<POSSession>
  },

  getSession: async (id: string) => {
    const response = await api.get(`/pos/sessions/${id}`)
    return response.data as POSSession
  },

  openSession: async (configId: string, openingBalance: number) => {
    const response = await api.post('/pos/sessions/open', {
      config_id: configId,
      opening_balance: openingBalance,
    })
    return response.data as POSSession
  },

  closeSession: async (id: string, closingBalance: number, notes?: string) => {
    const response = await api.post(`/pos/sessions/${id}/close`, {
      closing_balance: closingBalance,
      notes,
    })
    return response.data
  },

  pauseSession: async (id: string) => {
    const response = await api.post(`/pos/sessions/${id}/pause`)
    return response.data
  },

  resumeSession: async (id: string) => {
    const response = await api.post(`/pos/sessions/${id}/resume`)
    return response.data
  },

  getSessionSummary: async (id: string) => {
    const response = await api.get(`/pos/sessions/${id}/summary`)
    return response.data
  },

  // Orders
  listOrders: async (params?: {
    page?: number
    page_size?: number
    session_id?: string
    customer_id?: string
    state?: string
    date_from?: string
    date_to?: string
  }) => {
    const response = await api.get('/pos/orders', { params })
    return response.data as PaginatedResponse<POSOrder>
  },

  getOrder: async (id: string) => {
    const response = await api.get(`/pos/orders/${id}`)
    return response.data as POSOrder
  },

  createOrder: async (data: Partial<POSOrder>) => {
    const response = await api.post('/pos/orders', data)
    return response.data as POSOrder
  },

  updateOrder: async (id: string, data: Partial<POSOrder>) => {
    const response = await api.put(`/pos/orders/${id}`, data)
    return response.data as POSOrder
  },

  deleteOrder: async (id: string) => {
    await api.delete(`/pos/orders/${id}`)
  },

  payOrder: async (id: string, payments: POSPayment[]) => {
    const response = await api.post(`/pos/orders/${id}/pay`, { payments })
    return response.data as POSOrder
  },

  cancelOrder: async (id: string, reason?: string) => {
    const response = await api.post(`/pos/orders/${id}/cancel`, { reason })
    return response.data
  },

  refundOrder: async (id: string, lines?: { line_id: string; quantity: number }[]) => {
    const response = await api.post(`/pos/orders/${id}/refund`, { lines })
    return response.data as POSOrder
  },

  createInvoiceFromOrder: async (id: string) => {
    const response = await api.post(`/pos/orders/${id}/invoice`)
    return response.data
  },

  printReceipt: async (id: string) => {
    const response = await api.get(`/pos/orders/${id}/receipt`)
    return response.data
  },

  // Products
  getProducts: async (params?: {
    category_id?: string
    search?: string
  }) => {
    const response = await api.get('/pos/products', { params })
    return response.data as POSProduct[]
  },

  getProduct: async (id: string) => {
    const response = await api.get(`/pos/products/${id}`)
    return response.data as POSProduct
  },

  getProductByBarcode: async (barcode: string) => {
    const response = await api.get(`/pos/products/barcode/${barcode}`)
    return response.data as POSProduct
  },

  // Categories
  getCategories: async () => {
    const response = await api.get('/pos/categories')
    return response.data as POSCategory[]
  },

  // Customers
  searchCustomers: async (query: string) => {
    const response = await api.get('/pos/customers/search', { params: { q: query } })
    return response.data
  },

  createCustomer: async (data: { name: string; email?: string; phone?: string }) => {
    const response = await api.post('/pos/customers', data)
    return response.data
  },

  // Reports
  getDailySales: async (date?: string) => {
    const response = await api.get('/pos/reports/daily-sales', { params: { date } })
    return response.data
  },

  getSessionReport: async (sessionId: string) => {
    const response = await api.get(`/pos/reports/session/${sessionId}`)
    return response.data
  },

  getProductSales: async (params?: {
    date_from?: string
    date_to?: string
    category_id?: string
  }) => {
    const response = await api.get('/pos/reports/product-sales', { params })
    return response.data
  },

  getPaymentMethodsSummary: async (params?: {
    date_from?: string
    date_to?: string
  }) => {
    const response = await api.get('/pos/reports/payments', { params })
    return response.data
  },
}

export default posApi
