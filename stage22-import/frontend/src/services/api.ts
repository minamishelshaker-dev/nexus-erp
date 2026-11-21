import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '../stores/authStore'

// Create axios instance
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor - Add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().accessToken
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor - Handle errors and token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config

    // Handle 401 Unauthorized
    if (error.response?.status === 401 && originalRequest) {
      // Check if it's a token expiry
      const refreshToken = useAuthStore.getState().refreshToken
      
      if (refreshToken) {
        try {
          // Attempt to refresh the token
          const response = await api.post('/auth/refresh', {
            refresh_token: refreshToken,
          })

          const { access_token, refresh_token } = response.data
          
          // Update tokens in store
          useAuthStore.getState().updateTokens(access_token, refresh_token)

          // Retry original request with new token
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${access_token}`
          }
          return api(originalRequest)
        } catch (refreshError) {
          // Refresh failed, logout user
          useAuthStore.getState().logout()
          window.location.href = '/login'
          return Promise.reject(refreshError)
        }
      } else {
        // No refresh token, logout
        useAuthStore.getState().logout()
        window.location.href = '/login'
      }
    }

    // Handle other errors
    return Promise.reject(error)
  }
)

// ========================================
// API Types
// ========================================

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: {
    code: number
    message: string
    details?: unknown
  }
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

// ========================================
// Auth API
// ========================================

export const authApi = {
  login: async (username: string, password: string, rememberMe = false) => {
    const response = await api.post('/auth/login', {
      username,
      password,
      remember_me: rememberMe,
    })
    return response.data
  },

  logout: async () => {
    const response = await api.post('/auth/logout')
    return response.data
  },

  refresh: async (refreshToken: string) => {
    const response = await api.post('/auth/refresh', {
      refresh_token: refreshToken,
    })
    return response.data
  },

  changePassword: async (currentPassword: string, newPassword: string) => {
    const response = await api.post('/auth/password/change', {
      current_password: currentPassword,
      new_password: newPassword,
      confirm_password: newPassword,
    })
    return response.data
  },

  requestPasswordReset: async (email: string) => {
    const response = await api.post('/auth/password/reset', { email })
    return response.data
  },
}

// ========================================
// Customers API
// ========================================

export const customersApi = {
  list: async (params?: {
    page?: number
    page_size?: number
    search?: string
    customer_type?: string
    status?: string
  }) => {
    const response = await api.get('/customers', { params })
    return response.data as PaginatedResponse<Customer>
  },

  get: async (id: string) => {
    const response = await api.get(`/customers/${id}`)
    return response.data as Customer
  },

  create: async (data: Partial<Customer>) => {
    const response = await api.post('/customers', data)
    return response.data as Customer
  },

  update: async (id: string, data: Partial<Customer>) => {
    const response = await api.put(`/customers/${id}`, data)
    return response.data as Customer
  },

  delete: async (id: string) => {
    await api.delete(`/customers/${id}`)
  },

  // Contacts
  listContacts: async (customerId: string) => {
    const response = await api.get(`/customers/${customerId}/contacts`)
    return response.data as Contact[]
  },

  createContact: async (customerId: string, data: Partial<Contact>) => {
    const response = await api.post(`/customers/${customerId}/contacts`, data)
    return response.data as Contact
  },

  // Addresses
  listAddresses: async (customerId: string) => {
    const response = await api.get(`/customers/${customerId}/addresses`)
    return response.data as Address[]
  },

  createAddress: async (customerId: string, data: Partial<Address>) => {
    const response = await api.post(`/customers/${customerId}/addresses`, data)
    return response.data as Address
  },
}

// ========================================
// Types
// ========================================

export interface Customer {
  id: string
  code: string
  name: string
  customer_type: string
  status: string
  email?: string
  phone?: string
  website?: string
  address_line1?: string
  city?: string
  country?: string
  credit_limit: number
  credit_used: number
  total_orders: number
  total_revenue: number
  created_at: string
  updated_at: string
  contacts?: Contact[]
  addresses?: Address[]
}

export interface Contact {
  id: string
  customer_id: string
  first_name: string
  last_name: string
  full_name: string
  title?: string
  email?: string
  phone?: string
  is_primary: boolean
}

export interface Address {
  id: string
  customer_id: string
  name: string
  address_line1: string
  city: string
  country: string
  is_billing: boolean
  is_shipping: boolean
  is_default: boolean
}

export { api }
export default api
