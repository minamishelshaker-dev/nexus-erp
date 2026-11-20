/**
 * Nexus ERP - Settings API Service
 * API functions for settings/configuration module
 */

import api, { PaginatedResponse } from './api'

// Types
export interface Company {
  id: string
  name: string
  legal_name?: string
  code: string
  logo_url?: string
  address: string
  city: string
  state?: string
  country: string
  postal_code?: string
  phone: string
  email: string
  website?: string
  tax_id?: string
  registration_number?: string
  currency: string
  currency_id: string
  currency_symbol: string
  fiscal_year_start: number
  fiscal_year_month: number
  timezone: string
  date_format: string
  time_format: string
  decimal_places: number
  created_at: string
  updated_at: string
}

export interface User {
  id: string
  username: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  avatar_url?: string
  is_active: boolean
  is_admin: boolean
  role_id?: string
  role_name?: string
  department?: string
  phone?: string
  language: string
  timezone: string
  last_login?: string
  created_at: string
  updated_at: string
}

export interface Role {
  id: string
  name: string
  code: string
  description?: string
  is_system: boolean
  permissions: Permission[]
  user_count: number
  created_at: string
}

export interface Permission {
  id: string
  name: string
  code: string
  module: string
  description?: string
}

export interface Plan {
  id: string
  name: string
  code: string
  description?: string
  price_monthly: number
  price_yearly: number
  currency: string
  max_users: number
  max_customers: number
  max_products: number
  max_warehouses: number
  features: PlanFeature[]
  is_active: boolean
  is_default: boolean
  created_at: string
}

export interface PlanFeature {
  id: string
  name: string
  code: string
  enabled: boolean
  limit?: number
}

export interface Subscription {
  id: string
  plan_id: string
  plan_name: string
  status: 'active' | 'trial' | 'expired' | 'cancelled'
  billing_cycle: 'monthly' | 'yearly'
  start_date: string
  end_date?: string
  trial_end?: string
  amount: number
  currency: string
  auto_renew: boolean
  payment_method?: string
  last_payment_date?: string
  next_payment_date?: string
}

export interface SystemSettings {
  id: string
  module: string
  key: string
  value: string
  value_type: 'string' | 'number' | 'boolean' | 'json'
  description?: string
  updated_at: string
}

export interface AuditLog {
  id: string
  user_id: string
  user_name: string
  action: string
  module: string
  model: string
  record_id: string
  old_values?: Record<string, unknown>
  new_values?: Record<string, unknown>
  ip_address: string
  user_agent: string
  created_at: string
}

// API Functions
export const settingsApi = {
  // Company
  getCompany: async () => {
    const response = await api.get('/settings/company')
    return response.data as Company
  },

  updateCompany: async (data: Partial<Company>) => {
    const response = await api.put('/settings/company', data)
    return response.data as Company
  },

  uploadLogo: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post('/settings/company/logo', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  // Users
  listUsers: async (params?: {
    page?: number
    page_size?: number
    search?: string
    is_active?: boolean
    role_id?: string
  }) => {
    const response = await api.get('/settings/users', { params })
    return response.data as PaginatedResponse<User>
  },

  getUser: async (id: string) => {
    const response = await api.get(`/settings/users/${id}`)
    return response.data as User
  },

  createUser: async (data: Partial<User> & { password: string }) => {
    const response = await api.post('/settings/users', data)
    return response.data as User
  },

  updateUser: async (id: string, data: Partial<User>) => {
    const response = await api.put(`/settings/users/${id}`, data)
    return response.data as User
  },

  deleteUser: async (id: string) => {
    await api.delete(`/settings/users/${id}`)
  },

  resetUserPassword: async (id: string) => {
    const response = await api.post(`/settings/users/${id}/reset-password`)
    return response.data
  },

  changePassword: async (currentPassword: string, newPassword: string) => {
    const response = await api.post('/settings/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
    return response.data
  },

  updateUserPreferences: async (data: { language?: string; timezone?: string }) => {
    const response = await api.post('/settings/preferences', data)
    return response.data
  },

  // Roles
  listRoles: async () => {
    const response = await api.get('/settings/roles')
    return response.data as Role[]
  },

  getRole: async (id: string) => {
    const response = await api.get(`/settings/roles/${id}`)
    return response.data as Role
  },

  createRole: async (data: Partial<Role>) => {
    const response = await api.post('/settings/roles', data)
    return response.data as Role
  },

  updateRole: async (id: string, data: Partial<Role>) => {
    const response = await api.put(`/settings/roles/${id}`, data)
    return response.data as Role
  },

  deleteRole: async (id: string) => {
    await api.delete(`/settings/roles/${id}`)
  },

  getPermissions: async () => {
    const response = await api.get('/settings/permissions')
    return response.data as Permission[]
  },

  // Plans
  listPlans: async () => {
    const response = await api.get('/settings/plans')
    return response.data as Plan[]
  },

  getPlan: async (id: string) => {
    const response = await api.get(`/settings/plans/${id}`)
    return response.data as Plan
  },

  createPlan: async (data: Partial<Plan>) => {
    const response = await api.post('/settings/plans', data)
    return response.data as Plan
  },

  updatePlan: async (id: string, data: Partial<Plan>) => {
    const response = await api.put(`/settings/plans/${id}`, data)
    return response.data as Plan
  },

  deletePlan: async (id: string) => {
    await api.delete(`/settings/plans/${id}`)
  },

  // Subscription
  getSubscription: async () => {
    const response = await api.get('/settings/subscription')
    return response.data as Subscription
  },

  changePlan: async (planId: string, billingCycle: 'monthly' | 'yearly') => {
    const response = await api.post('/settings/subscription/change-plan', {
      plan_id: planId,
      billing_cycle: billingCycle,
    })
    return response.data as Subscription
  },

  cancelSubscription: async (reason?: string) => {
    const response = await api.post('/settings/subscription/cancel', { reason })
    return response.data
  },

  reactivateSubscription: async () => {
    const response = await api.post('/settings/subscription/reactivate')
    return response.data as Subscription
  },

  updatePaymentMethod: async (paymentMethodId: string) => {
    const response = await api.post('/settings/subscription/payment-method', {
      payment_method_id: paymentMethodId,
    })
    return response.data
  },

  getInvoices: async () => {
    const response = await api.get('/settings/subscription/invoices')
    return response.data
  },

  // System Settings
  getSystemSettings: async (module?: string) => {
    const response = await api.get('/settings/system', { params: { module } })
    return response.data as SystemSettings[]
  },

  updateSystemSetting: async (key: string, value: string) => {
    const response = await api.put(`/settings/system/${key}`, { value })
    return response.data as SystemSettings
  },

  // Audit Logs
  listAuditLogs: async (params?: {
    page?: number
    page_size?: number
    user_id?: string
    module?: string
    action?: string
    date_from?: string
    date_to?: string
  }) => {
    const response = await api.get('/settings/audit-logs', { params })
    return response.data as PaginatedResponse<AuditLog>
  },

  exportAuditLogs: async (params?: {
    user_id?: string
    module?: string
    date_from?: string
    date_to?: string
    format?: 'csv' | 'xlsx' | 'pdf'
  }) => {
    const response = await api.get('/settings/audit-logs/export', {
      params,
      responseType: 'blob',
    })
    return response.data
  },

  // Integrations
  getIntegrations: async () => {
    const response = await api.get('/settings/integrations')
    return response.data
  },

  configureIntegration: async (integrationId: string, config: Record<string, unknown>) => {
    const response = await api.post(`/settings/integrations/${integrationId}/configure`, config)
    return response.data
  },

  disconnectIntegration: async (integrationId: string) => {
    const response = await api.post(`/settings/integrations/${integrationId}/disconnect`)
    return response.data
  },

  // Backup & Restore
  createBackup: async () => {
    const response = await api.post('/settings/backup')
    return response.data
  },

  listBackups: async () => {
    const response = await api.get('/settings/backups')
    return response.data
  },

  downloadBackup: async (backupId: string) => {
    const response = await api.get(`/settings/backups/${backupId}/download`, {
      responseType: 'blob',
    })
    return response.data
  },

  restoreBackup: async (backupId: string) => {
    const response = await api.post(`/settings/backups/${backupId}/restore`)
    return response.data
  },

  deleteBackup: async (backupId: string) => {
    await api.delete(`/settings/backups/${backupId}`)
  },
}

export default settingsApi
