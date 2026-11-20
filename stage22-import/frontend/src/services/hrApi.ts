/**
 * Nexus ERP - HR API Service
 * API functions for HR/Payroll module
 */

import api, { PaginatedResponse } from './api'

// Types
export interface Employee {
  id: string
  employee_number: string
  first_name: string
  last_name: string
  full_name: string
  email: string
  phone: string
  department_id: string
  department_name: string
  position: string
  manager_id?: string
  manager_name?: string
  hire_date: string
  termination_date?: string
  status: 'active' | 'on_leave' | 'terminated'
  employment_type: 'full_time' | 'part_time' | 'contract' | 'intern'
  salary: number
  salary_type: 'monthly' | 'hourly' | 'annual'
  currency: string
  bank_name?: string
  bank_account?: string
  tax_id?: string
  address?: string
  city?: string
  country?: string
  avatar_url?: string
  date_of_birth?: string
  gender?: 'male' | 'female'
  emergency_contact?: string
  emergency_phone?: string
  created_at: string
  updated_at: string
}

export interface Department {
  id: string
  name: string
  parent_id?: string
  parent_name?: string
  manager_id?: string
  manager_name?: string
  employee_count: number
  is_active: boolean
  created_at: string
}

export interface AttendanceRecord {
  id: string
  employee_id: string
  employee_name: string
  employee_number: string
  date: string
  check_in: string
  check_out: string
  work_hours: number
  overtime_hours: number
  status: 'present' | 'absent' | 'late' | 'early_leave' | 'half_day' | 'leave'
  notes?: string
  department: string
  created_at: string
}

export interface LeaveRequest {
  id: string
  employee_id: string
  employee_name: string
  leave_type: string
  leave_type_name: string
  date_from: string
  date_to: string
  days: number
  reason?: string
  state: 'draft' | 'submitted' | 'approved' | 'rejected' | 'cancelled'
  approved_by?: string
  approver_name?: string
  approval_date?: string
  rejection_reason?: string
  created_at: string
}

export interface LeaveType {
  id: string
  name: string
  code: string
  days_allowed: number
  carry_forward: boolean
  is_paid: boolean
  requires_approval: boolean
}

export interface PayrollRun {
  id: string
  name: string
  period_start: string
  period_end: string
  payment_date: string
  state: 'draft' | 'confirmed' | 'paid' | 'cancelled'
  total_employees: number
  total_gross: number
  total_deductions: number
  total_net: number
  currency: string
  created_by: string
  created_at: string
}

export interface Payslip {
  id: string
  payroll_run_id: string
  payroll_run_name: string
  employee_id: string
  employee_name: string
  employee_number: string
  department: string
  period_start: string
  period_end: string
  base_salary: number
  allowances: number
  overtime: number
  bonuses: number
  commissions: number
  gross_salary: number
  tax: number
  insurance: number
  social_security: number
  other_deductions: number
  total_deductions: number
  net_salary: number
  currency: string
  state: 'draft' | 'confirmed' | 'paid'
  worked_days: number
  paid_leaves: number
  unpaid_leaves: number
  created_at: string
}

// API Functions
export const hrApi = {
  // Employees
  listEmployees: async (params?: {
    page?: number
    page_size?: number
    search?: string
    department?: string
    status?: string
    employment_type?: string
  }) => {
    const response = await api.get('/hr/employees', { params })
    return response.data as PaginatedResponse<Employee>
  },

  getEmployee: async (id: string) => {
    const response = await api.get(`/hr/employees/${id}`)
    return response.data as Employee
  },

  createEmployee: async (data: Partial<Employee>) => {
    const response = await api.post('/hr/employees', data)
    return response.data as Employee
  },

  updateEmployee: async (id: string, data: Partial<Employee>) => {
    const response = await api.put(`/hr/employees/${id}`, data)
    return response.data as Employee
  },

  deleteEmployee: async (id: string) => {
    await api.delete(`/hr/employees/${id}`)
  },

  terminateEmployee: async (id: string, terminationDate: string, reason?: string) => {
    const response = await api.post(`/hr/employees/${id}/terminate`, {
      termination_date: terminationDate,
      reason,
    })
    return response.data
  },

  // Departments
  listDepartments: async () => {
    const response = await api.get('/hr/departments')
    return response.data as Department[]
  },

  getDepartment: async (id: string) => {
    const response = await api.get(`/hr/departments/${id}`)
    return response.data as Department
  },

  createDepartment: async (data: Partial<Department>) => {
    const response = await api.post('/hr/departments', data)
    return response.data as Department
  },

  updateDepartment: async (id: string, data: Partial<Department>) => {
    const response = await api.put(`/hr/departments/${id}`, data)
    return response.data as Department
  },

  deleteDepartment: async (id: string) => {
    await api.delete(`/hr/departments/${id}`)
  },

  // Attendance
  listAttendance: async (params?: {
    page?: number
    page_size?: number
    date?: string
    employee_id?: string
    department?: string
    status?: string
    date_from?: string
    date_to?: string
  }) => {
    const response = await api.get('/hr/attendance', { params })
    return response.data as PaginatedResponse<AttendanceRecord>
  },

  checkIn: async (employeeId: string) => {
    const response = await api.post('/hr/attendance/check-in', { employee_id: employeeId })
    return response.data as AttendanceRecord
  },

  checkOut: async (employeeId: string) => {
    const response = await api.post('/hr/attendance/check-out', { employee_id: employeeId })
    return response.data as AttendanceRecord
  },

  manualAttendance: async (data: { employee_id: string; date: string; check_in: string; check_out?: string; notes?: string }) => {
    const response = await api.post('/hr/attendance/manual', data)
    return response.data as AttendanceRecord
  },

  updateAttendance: async (id: string, data: Partial<AttendanceRecord>) => {
    const response = await api.put(`/hr/attendance/${id}`, data)
    return response.data as AttendanceRecord
  },

  // Leave Management
  listLeaveRequests: async (params?: {
    page?: number
    page_size?: number
    employee_id?: string
    state?: string
    leave_type?: string
  }) => {
    const response = await api.get('/hr/leaves', { params })
    return response.data as PaginatedResponse<LeaveRequest>
  },

  getLeaveRequest: async (id: string) => {
    const response = await api.get(`/hr/leaves/${id}`)
    return response.data as LeaveRequest
  },

  createLeaveRequest: async (data: Partial<LeaveRequest>) => {
    const response = await api.post('/hr/leaves', data)
    return response.data as LeaveRequest
  },

  approveLeaveRequest: async (id: string) => {
    const response = await api.post(`/hr/leaves/${id}/approve`)
    return response.data
  },

  rejectLeaveRequest: async (id: string, reason: string) => {
    const response = await api.post(`/hr/leaves/${id}/reject`, { reason })
    return response.data
  },

  cancelLeaveRequest: async (id: string) => {
    const response = await api.post(`/hr/leaves/${id}/cancel`)
    return response.data
  },

  listLeaveTypes: async () => {
    const response = await api.get('/hr/leave-types')
    return response.data as LeaveType[]
  },

  getEmployeeLeaveBalance: async (employeeId: string, leaveTypeId?: string) => {
    const response = await api.get(`/hr/employees/${employeeId}/leave-balance`, {
      params: { leave_type_id: leaveTypeId },
    })
    return response.data
  },

  // Payroll
  listPayrollRuns: async (params?: {
    page?: number
    page_size?: number
    search?: string
    state?: string
    date_from?: string
    date_to?: string
  }) => {
    const response = await api.get('/hr/payroll/runs', { params })
    return response.data as PaginatedResponse<PayrollRun>
  },

  getPayrollRun: async (id: string) => {
    const response = await api.get(`/hr/payroll/runs/${id}`)
    return response.data as PayrollRun
  },

  createPayrollRun: async (data: Partial<PayrollRun>) => {
    const response = await api.post('/hr/payroll/runs', data)
    return response.data as PayrollRun
  },

  confirmPayrollRun: async (id: string) => {
    const response = await api.post(`/hr/payroll/runs/${id}/confirm`)
    return response.data
  },

  payPayrollRun: async (id: string) => {
    const response = await api.post(`/hr/payroll/runs/${id}/pay`)
    return response.data
  },

  cancelPayrollRun: async (id: string) => {
    const response = await api.post(`/hr/payroll/runs/${id}/cancel`)
    return response.data
  },

  listPayslips: async (params?: {
    page?: number
    page_size?: number
    employee_id?: string
    payroll_run_id?: string
  }) => {
    const response = await api.get('/hr/payroll/payslips', { params })
    return response.data as PaginatedResponse<Payslip>
  },

  getPayslip: async (id: string) => {
    const response = await api.get(`/hr/payroll/payslips/${id}`)
    return response.data as Payslip
  },

  downloadPayslipPdf: async (id: string) => {
    const response = await api.get(`/hr/payroll/payslips/${id}/pdf`, { responseType: 'blob' })
    return response.data
  },
}

export default hrApi
