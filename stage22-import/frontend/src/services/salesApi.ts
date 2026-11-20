/**
 * Nexus ERP - Sales API Service
 * API functions for sales module
 */

import api, { PaginatedResponse } from './api'

// Types
export interface Quotation {
  id: string
  number: string
  name: string
  customer_id: string
  customer_name: string
  date: string
  valid_until: string
  state: 'draft' | 'sent' | 'accepted' | 'lost' | 'expired' | 'cancelled'
  amount_untaxed: number
  amount_tax: number
  amount_total: number
  currency: string
  lines: QuotationLine[]
  created_at: string
}

export interface QuotationLine {
  id: string
  product_id: string
  product_name: string
  description: string
  quantity: number
  uom: string
  price_unit: number
  discount: number
  price_subtotal: number
  tax_id?: string
  tax_name?: string
}

export interface SaleOrder {
  id: string
  number: string
  name: string
  customer_id: string
  customer_name: string
  date_order: string
  delivery_date?: string
  state: 'draft' | 'confirmed' | 'done' | 'cancelled'
  amount_untaxed: number
  amount_tax: number
  amount_total: number
  delivery_status: 'no' | 'partial' | 'done'
  invoice_status: 'no' | 'partial' | 'invoiced'
  currency: string
  quotation_id?: string
  quotation_number?: string
  lines: SaleOrderLine[]
  created_at: string
}

export interface SaleOrderLine {
  id: string
  product_id: string
  product_name: string
  description: string
  quantity: number
  qty_delivered: number
  qty_invoiced: number
  uom: string
  price_unit: number
  discount: number
  price_subtotal: number
}

export interface Invoice {
  id: string
  number: string
  customer_id: string
  customer_name: string
  date: string
  due_date: string
  state: 'draft' | 'posted' | 'sent' | 'paid' | 'partial' | 'overdue' | 'cancelled'
  amount_untaxed: number
  amount_tax: number
  amount_total: number
  amount_due: number
  payment_status: string
  currency: string
  order_id?: string
  order_number?: string
  lines: InvoiceLine[]
  created_at: string
}

export interface InvoiceLine {
  id: string
  product_id: string
  product_name: string
  description: string
  quantity: number
  uom: string
  price_unit: number
  discount: number
  price_subtotal: number
  tax_amount: number
}

// API Functions
export const salesApi = {
  // Quotations
  listQuotations: async (params?: {
    page?: number
    page_size?: number
    search?: string
    state?: string
    customer_id?: string
    date_from?: string
    date_to?: string
  }) => {
    const response = await api.get('/sales/quotations', { params })
    return response.data as PaginatedResponse<Quotation>
  },

  getQuotation: async (id: string) => {
    const response = await api.get(`/sales/quotations/${id}`)
    return response.data as Quotation
  },

  createQuotation: async (data: Partial<Quotation>) => {
    const response = await api.post('/sales/quotations', data)
    return response.data as Quotation
  },

  updateQuotation: async (id: string, data: Partial<Quotation>) => {
    const response = await api.put(`/sales/quotations/${id}`, data)
    return response.data as Quotation
  },

  deleteQuotation: async (id: string) => {
    await api.delete(`/sales/quotations/${id}`)
  },

  sendQuotation: async (id: string) => {
    const response = await api.post(`/sales/quotations/${id}/send`)
    return response.data
  },

  confirmQuotation: async (id: string) => {
    const response = await api.post(`/sales/quotations/${id}/confirm`)
    return response.data as SaleOrder
  },

  cancelQuotation: async (id: string) => {
    const response = await api.post(`/sales/quotations/${id}/cancel`)
    return response.data
  },

  // Sale Orders
  listSaleOrders: async (params?: {
    page?: number
    page_size?: number
    search?: string
    state?: string
    customer_id?: string
    date_from?: string
    date_to?: string
  }) => {
    const response = await api.get('/sales/orders', { params })
    return response.data as PaginatedResponse<SaleOrder>
  },

  getSaleOrder: async (id: string) => {
    const response = await api.get(`/sales/orders/${id}`)
    return response.data as SaleOrder
  },

  createSaleOrder: async (data: Partial<SaleOrder>) => {
    const response = await api.post('/sales/orders', data)
    return response.data as SaleOrder
  },

  updateSaleOrder: async (id: string, data: Partial<SaleOrder>) => {
    const response = await api.put(`/sales/orders/${id}`, data)
    return response.data as SaleOrder
  },

  deleteSaleOrder: async (id: string) => {
    await api.delete(`/sales/orders/${id}`)
  },

  confirmSaleOrder: async (id: string, options?: { create_delivery?: boolean; create_invoice?: boolean }) => {
    const response = await api.post(`/sales/orders/${id}/confirm`, options)
    return response.data
  },

  cancelSaleOrder: async (id: string, reason?: string) => {
    const response = await api.post(`/sales/orders/${id}/cancel`, { reason })
    return response.data
  },

  createInvoiceFromOrder: async (id: string) => {
    const response = await api.post(`/sales/orders/${id}/invoice`)
    return response.data as Invoice
  },

  createDeliveryFromOrder: async (id: string) => {
    const response = await api.post(`/sales/orders/${id}/delivery`)
    return response.data
  },

  // Invoices
  listInvoices: async (params?: {
    page?: number
    page_size?: number
    search?: string
    state?: string
    customer_id?: string
    date_from?: string
    date_to?: string
  }) => {
    const response = await api.get('/sales/invoices', { params })
    return response.data as PaginatedResponse<Invoice>
  },

  getInvoice: async (id: string) => {
    const response = await api.get(`/sales/invoices/${id}`)
    return response.data as Invoice
  },

  createInvoice: async (data: Partial<Invoice>) => {
    const response = await api.post('/sales/invoices', data)
    return response.data as Invoice
  },

  updateInvoice: async (id: string, data: Partial<Invoice>) => {
    const response = await api.put(`/sales/invoices/${id}`, data)
    return response.data as Invoice
  },

  deleteInvoice: async (id: string) => {
    await api.delete(`/sales/invoices/${id}`)
  },

  postInvoice: async (id: string) => {
    const response = await api.post(`/sales/invoices/${id}/post`)
    return response.data
  },

  sendInvoice: async (id: string) => {
    const response = await api.post(`/sales/invoices/${id}/send`)
    return response.data
  },

  registerPayment: async (id: string, paymentData: { amount: number; payment_method: string; date: string }) => {
    const response = await api.post(`/sales/invoices/${id}/payment`, paymentData)
    return response.data
  },

  cancelInvoice: async (id: string) => {
    const response = await api.post(`/sales/invoices/${id}/cancel`)
    return response.data
  },

  getInvoicePdf: async (id: string) => {
    const response = await api.get(`/sales/invoices/${id}/pdf`, { responseType: 'blob' })
    return response.data
  },
}

export default salesApi
