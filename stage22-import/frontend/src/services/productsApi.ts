/**
 * Nexus ERP - Products API Service
 * API functions for products/inventory module
 */

import api, { PaginatedResponse } from './api'

// Types
export interface Product {
  id: string
  code: string
  name: string
  category_id: string
  category_name: string
  type: 'product' | 'service' | 'consumable'
  uom: string
  uom_id: string
  price: number
  cost: number
  barcode?: string
  description?: string
  weight?: number
  volume?: number
  quantity_on_hand: number
  quantity_available: number
  quantity_reserved: number
  quantity_incoming: number
  quantity_outgoing: number
  reorder_point: number
  max_stock?: number
  is_active: boolean
  is_saleable: boolean
  is_purchasable: boolean
  tracking: 'none' | 'serial' | 'lot'
  image_url?: string
  created_at: string
  updated_at: string
}

export interface ProductCategory {
  id: string
  name: string
  parent_id?: string
  parent_name?: string
  product_count: number
  is_active: boolean
}

export interface Warehouse {
  id: string
  code: string
  name: string
  address: string
  city: string
  country: string
  phone: string
  email: string
  manager_id?: string
  manager_name?: string
  is_active: boolean
  total_products: number
  total_quantity: number
  total_value: number
  created_at: string
}

export interface StockLevel {
  id: string
  product_id: string
  product_code: string
  product_name: string
  warehouse_id: string
  warehouse_name: string
  quantity_on_hand: number
  quantity_reserved: number
  quantity_available: number
  quantity_incoming: number
  quantity_outgoing: number
  reorder_point: number
  max_stock: number
  uom: string
  cost: number
  stock_value: number
  last_movement_date: string
}

export interface StockMovement {
  id: string
  number: string
  product_id: string
  product_name: string
  product_code: string
  warehouse_id: string
  warehouse_name: string
  movement_type: 'in' | 'out' | 'internal'
  source_document?: string
  source_document_type?: string
  quantity: number
  uom: string
  reference?: string
  state: 'draft' | 'confirmed' | 'done' | 'cancelled'
  scheduled_date: string
  effective_date?: string
  created_by: string
  created_at: string
}

export interface InventoryAdjustment {
  id: string
  number: string
  name: string
  warehouse_id: string
  warehouse_name: string
  state: 'draft' | 'in_progress' | 'confirmed' | 'cancelled'
  count_date: string
  lines: InventoryAdjustmentLine[]
  created_by: string
  created_at: string
}

export interface InventoryAdjustmentLine {
  id: string
  product_id: string
  product_name: string
  product_code: string
  quantity_theoretical: number
  quantity_counted: number
  difference: number
  uom: string
  cost: number
  value_difference: number
}

// API Functions
export const productsApi = {
  // Products
  listProducts: async (params?: {
    page?: number
    page_size?: number
    search?: string
    type?: string
    category?: string
    is_active?: boolean
  }) => {
    const response = await api.get('/inventory/products', { params })
    return response.data as PaginatedResponse<Product>
  },

  getProduct: async (id: string) => {
    const response = await api.get(`/inventory/products/${id}`)
    return response.data as Product
  },

  createProduct: async (data: Partial<Product>) => {
    const response = await api.post('/inventory/products', data)
    return response.data as Product
  },

  updateProduct: async (id: string, data: Partial<Product>) => {
    const response = await api.put(`/inventory/products/${id}`, data)
    return response.data as Product
  },

  deleteProduct: async (id: string) => {
    await api.delete(`/inventory/products/${id}`)
  },

  duplicateProduct: async (id: string) => {
    const response = await api.post(`/inventory/products/${id}/duplicate`)
    return response.data as Product
  },

  // Categories
  listCategories: async () => {
    const response = await api.get('/inventory/categories')
    return response.data as ProductCategory[]
  },

  getCategory: async (id: string) => {
    const response = await api.get(`/inventory/categories/${id}`)
    return response.data as ProductCategory
  },

  createCategory: async (data: Partial<ProductCategory>) => {
    const response = await api.post('/inventory/categories', data)
    return response.data as ProductCategory
  },

  updateCategory: async (id: string, data: Partial<ProductCategory>) => {
    const response = await api.put(`/inventory/categories/${id}`, data)
    return response.data as ProductCategory
  },

  deleteCategory: async (id: string) => {
    await api.delete(`/inventory/categories/${id}`)
  },

  // Warehouses
  listWarehouses: async (params?: {
    page?: number
    page_size?: number
    search?: string
    is_active?: boolean
  }) => {
    const response = await api.get('/inventory/warehouses', { params })
    return response.data as PaginatedResponse<Warehouse>
  },

  getWarehouse: async (id: string) => {
    const response = await api.get(`/inventory/warehouses/${id}`)
    return response.data as Warehouse
  },

  createWarehouse: async (data: Partial<Warehouse>) => {
    const response = await api.post('/inventory/warehouses', data)
    return response.data as Warehouse
  },

  updateWarehouse: async (id: string, data: Partial<Warehouse>) => {
    const response = await api.put(`/inventory/warehouses/${id}`, data)
    return response.data as Warehouse
  },

  deleteWarehouse: async (id: string) => {
    await api.delete(`/inventory/warehouses/${id}`)
  },

  // Stock Levels
  listStockLevels: async (params?: {
    page?: number
    page_size?: number
    search?: string
    warehouse?: string
    filter?: 'low_stock' | 'out_of_stock' | 'negative' | 'in_stock'
  }) => {
    const response = await api.get('/inventory/stock', { params })
    return response.data as PaginatedResponse<StockLevel>
  },

  getStockLevel: async (productId: string, warehouseId: string) => {
    const response = await api.get(`/inventory/stock/${productId}/${warehouseId}`)
    return response.data as StockLevel
  },

  // Stock Movements
  listStockMovements: async (params?: {
    page?: number
    page_size?: number
    search?: string
    product_id?: string
    warehouse_id?: string
    movement_type?: string
    state?: string
    date_from?: string
    date_to?: string
  }) => {
    const response = await api.get('/inventory/movements', { params })
    return response.data as PaginatedResponse<StockMovement>
  },

  getStockMovement: async (id: string) => {
    const response = await api.get(`/inventory/movements/${id}`)
    return response.data as StockMovement
  },

  createStockMovement: async (data: Partial<StockMovement>) => {
    const response = await api.post('/inventory/movements', data)
    return response.data as StockMovement
  },

  confirmStockMovement: async (id: string) => {
    const response = await api.post(`/inventory/movements/${id}/confirm`)
    return response.data
  },

  cancelStockMovement: async (id: string) => {
    const response = await api.post(`/inventory/movements/${id}/cancel`)
    return response.data
  },

  // Inventory Adjustments
  listAdjustments: async (params?: {
    page?: number
    page_size?: number
    search?: string
    warehouse_id?: string
    state?: string
  }) => {
    const response = await api.get('/inventory/adjustments', { params })
    return response.data as PaginatedResponse<InventoryAdjustment>
  },

  getAdjustment: async (id: string) => {
    const response = await api.get(`/inventory/adjustments/${id}`)
    return response.data as InventoryAdjustment
  },

  createAdjustment: async (data: Partial<InventoryAdjustment>) => {
    const response = await api.post('/inventory/adjustments', data)
    return response.data as InventoryAdjustment
  },

  confirmAdjustment: async (id: string) => {
    const response = await api.post(`/inventory/adjustments/${id}/confirm`)
    return response.data
  },

  // Units of Measure
  listUoms: async () => {
    const response = await api.get('/inventory/uoms')
    return response.data
  },

  // Reports
  getInventoryValuation: async (params?: {
    warehouse_id?: string
    category_id?: string
    as_of_date?: string
  }) => {
    const response = await api.get('/inventory/reports/valuation', { params })
    return response.data
  },

  getLowStockReport: async (params?: {
    warehouse_id?: string
  }) => {
    const response = await api.get('/inventory/reports/low-stock', { params })
    return response.data
  },

  getMovementAnalysis: async (params?: {
    product_id?: string
    warehouse_id?: string
    date_from?: string
    date_to?: string
  }) => {
    const response = await api.get('/inventory/reports/movement-analysis', { params })
    return response.data
  },
}

export default productsApi
