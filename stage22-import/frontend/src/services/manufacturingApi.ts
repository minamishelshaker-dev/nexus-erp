/**
 * Nexus ERP - Manufacturing API Service
 * API functions for manufacturing module
 */

import api, { PaginatedResponse } from './api'

// Types
export interface BillOfMaterial {
  id: string
  code: string
  name: string
  product_id: string
  product_name: string
  product_code: string
  bom_type: 'normal' | 'phantom' | 'subcontracting'
  product_qty: number
  product_uom: string
  state: 'draft' | 'active' | 'archived'
  total_cost: number
  line_count: number
  routing_id?: string
  routing_name?: string
  lines: BOMLine[]
  operations?: BOMOperation[]
  created_at: string
  updated_at: string
}

export interface BOMLine {
  id: string
  product_id: string
  product_name: string
  product_code: string
  quantity: number
  uom: string
  unit_cost: number
  subtotal: number
  operation_id?: string
  operation_name?: string
}

export interface BOMOperation {
  id: string
  name: string
  workcenter_id: string
  workcenter_name: string
  duration: number
  duration_unit: 'minutes' | 'hours'
  cost_per_hour: number
  sequence: number
}

export interface ManufacturingOrder {
  id: string
  number: string
  name: string
  product_id: string
  product_name: string
  product_code: string
  bom_id: string
  bom_name: string
  product_qty: number
  product_uom: string
  qty_produced: number
  progress_percent: number
  state: 'draft' | 'confirmed' | 'planned' | 'in_progress' | 'done' | 'cancelled'
  planned_date: string
  start_date?: string
  end_date?: string
  total_cost: number
  material_cost: number
  labor_cost: number
  overhead_cost: number
  warehouse_id: string
  warehouse_name: string
  lines: ManufacturingOrderLine[]
  workorders?: WorkOrder[]
  created_by: string
  created_at: string
}

export interface ManufacturingOrderLine {
  id: string
  product_id: string
  product_name: string
  product_code: string
  quantity_required: number
  quantity_consumed: number
  uom: string
  unit_cost: number
  source_location?: string
  state: 'pending' | 'available' | 'consumed'
}

export interface WorkOrder {
  id: string
  name: string
  manufacturing_order_id: string
  manufacturing_order_number: string
  operation_id: string
  operation_name: string
  workcenter_id: string
  workcenter_name: string
  duration_planned: number
  duration_actual?: number
  state: 'pending' | 'ready' | 'in_progress' | 'done' | 'cancelled'
  sequence: number
  started_at?: string
  finished_at?: string
}

export interface WorkCenter {
  id: string
  name: string
  code: string
  capacity: number
  cost_per_hour: number
  overhead_cost_per_hour: number
  is_active: boolean
  location_id?: string
  location_name?: string
}

export interface Routing {
  id: string
  name: string
  code: string
  operations: BOMOperation[]
  total_duration: number
  is_active: boolean
}

// API Functions
export const manufacturingApi = {
  // Bill of Materials
  listBOMs: async (params?: {
    page?: number
    page_size?: number
    search?: string
    product_id?: string
    state?: string
  }) => {
    const response = await api.get('/manufacturing/boms', { params })
    return response.data as PaginatedResponse<BillOfMaterial>
  },

  getBOM: async (id: string) => {
    const response = await api.get(`/manufacturing/boms/${id}`)
    return response.data as BillOfMaterial
  },

  createBOM: async (data: Partial<BillOfMaterial>) => {
    const response = await api.post('/manufacturing/boms', data)
    return response.data as BillOfMaterial
  },

  updateBOM: async (id: string, data: Partial<BillOfMaterial>) => {
    const response = await api.put(`/manufacturing/boms/${id}`, data)
    return response.data as BillOfMaterial
  },

  deleteBOM: async (id: string) => {
    await api.delete(`/manufacturing/boms/${id}`)
  },

  activateBOM: async (id: string) => {
    const response = await api.post(`/manufacturing/boms/${id}/activate`)
    return response.data
  },

  archiveBOM: async (id: string) => {
    const response = await api.post(`/manufacturing/boms/${id}/archive`)
    return response.data
  },

  duplicateBOM: async (id: string) => {
    const response = await api.post(`/manufacturing/boms/${id}/duplicate`)
    return response.data as BillOfMaterial
  },

  calculateBOMCost: async (id: string) => {
    const response = await api.post(`/manufacturing/boms/${id}/calculate-cost`)
    return response.data
  },

  // Manufacturing Orders
  listManufacturingOrders: async (params?: {
    page?: number
    page_size?: number
    search?: string
    product_id?: string
    state?: string
    date_from?: string
    date_to?: string
  }) => {
    const response = await api.get('/manufacturing/orders', { params })
    return response.data as PaginatedResponse<ManufacturingOrder>
  },

  getManufacturingOrder: async (id: string) => {
    const response = await api.get(`/manufacturing/orders/${id}`)
    return response.data as ManufacturingOrder
  },

  createManufacturingOrder: async (data: Partial<ManufacturingOrder>) => {
    const response = await api.post('/manufacturing/orders', data)
    return response.data as ManufacturingOrder
  },

  updateManufacturingOrder: async (id: string, data: Partial<ManufacturingOrder>) => {
    const response = await api.put(`/manufacturing/orders/${id}`, data)
    return response.data as ManufacturingOrder
  },

  deleteManufacturingOrder: async (id: string) => {
    await api.delete(`/manufacturing/orders/${id}`)
  },

  confirmManufacturingOrder: async (id: string) => {
    const response = await api.post(`/manufacturing/orders/${id}/confirm`)
    return response.data
  },

  planManufacturingOrder: async (id: string) => {
    const response = await api.post(`/manufacturing/orders/${id}/plan`)
    return response.data
  },

  startManufacturingOrder: async (id: string) => {
    const response = await api.post(`/manufacturing/orders/${id}/start`)
    return response.data
  },

  finishManufacturingOrder: async (id: string, qty?: number) => {
    const response = await api.post(`/manufacturing/orders/${id}/finish`, { quantity: qty })
    return response.data
  },

  cancelManufacturingOrder: async (id: string, reason?: string) => {
    const response = await api.post(`/manufacturing/orders/${id}/cancel`, { reason })
    return response.data
  },

  checkAvailability: async (id: string) => {
    const response = await api.post(`/manufacturing/orders/${id}/check-availability`)
    return response.data
  },

  // Work Orders
  listWorkOrders: async (params?: {
    page?: number
    page_size?: number
    manufacturing_order_id?: string
    workcenter_id?: string
    state?: string
  }) => {
    const response = await api.get('/manufacturing/workorders', { params })
    return response.data as PaginatedResponse<WorkOrder>
  },

  getWorkOrder: async (id: string) => {
    const response = await api.get(`/manufacturing/workorders/${id}`)
    return response.data as WorkOrder
  },

  startWorkOrder: async (id: string) => {
    const response = await api.post(`/manufacturing/workorders/${id}/start`)
    return response.data
  },

  pauseWorkOrder: async (id: string) => {
    const response = await api.post(`/manufacturing/workorders/${id}/pause`)
    return response.data
  },

  resumeWorkOrder: async (id: string) => {
    const response = await api.post(`/manufacturing/workorders/${id}/resume`)
    return response.data
  },

  finishWorkOrder: async (id: string, duration?: number) => {
    const response = await api.post(`/manufacturing/workorders/${id}/finish`, { duration })
    return response.data
  },

  // Work Centers
  listWorkCenters: async () => {
    const response = await api.get('/manufacturing/workcenters')
    return response.data as WorkCenter[]
  },

  getWorkCenter: async (id: string) => {
    const response = await api.get(`/manufacturing/workcenters/${id}`)
    return response.data as WorkCenter
  },

  createWorkCenter: async (data: Partial<WorkCenter>) => {
    const response = await api.post('/manufacturing/workcenters', data)
    return response.data as WorkCenter
  },

  updateWorkCenter: async (id: string, data: Partial<WorkCenter>) => {
    const response = await api.put(`/manufacturing/workcenters/${id}`, data)
    return response.data as WorkCenter
  },

  deleteWorkCenter: async (id: string) => {
    await api.delete(`/manufacturing/workcenters/${id}`)
  },

  // Routings
  listRoutings: async () => {
    const response = await api.get('/manufacturing/routings')
    return response.data as Routing[]
  },

  getRouting: async (id: string) => {
    const response = await api.get(`/manufacturing/routings/${id}`)
    return response.data as Routing
  },

  createRouting: async (data: Partial<Routing>) => {
    const response = await api.post('/manufacturing/routings', data)
    return response.data as Routing
  },

  updateRouting: async (id: string, data: Partial<Routing>) => {
    const response = await api.put(`/manufacturing/routings/${id}`, data)
    return response.data as Routing
  },

  deleteRouting: async (id: string) => {
    await api.delete(`/manufacturing/routings/${id}`)
  },

  // Reports
  getProductionReport: async (params?: {
    date_from?: string
    date_to?: string
    product_id?: string
    workcenter_id?: string
  }) => {
    const response = await api.get('/manufacturing/reports/production', { params })
    return response.data
  },

  getEfficiencyReport: async (params?: {
    date_from?: string
    date_to?: string
    workcenter_id?: string
  }) => {
    const response = await api.get('/manufacturing/reports/efficiency', { params })
    return response.data
  },

  getCostAnalysis: async (params?: {
    date_from?: string
    date_to?: string
    product_id?: string
  }) => {
    const response = await api.get('/manufacturing/reports/cost-analysis', { params })
    return response.data
  },
}

export default manufacturingApi
