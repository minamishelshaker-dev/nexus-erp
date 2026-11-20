/**
 * Nexus ERP - Payroll Page
 * Employee payroll management
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, PaginatedResponse } from '../../services/api'
import {
  Plus,
  Search,
  DollarSign,
  Calendar,
  CheckCircle,
  XCircle,
  Clock,
  MoreVertical,
  Eye,
  FileText,
  Send,
  Download,
} from 'lucide-react'

interface PayrollRun {
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
  created_at: string
}

const stateColors: Record<string, string> = {
  draft: 'bg-yellow-100 text-yellow-700',
  confirmed: 'bg-blue-100 text-blue-700',
  paid: 'bg-green-100 text-green-700',
  cancelled: 'bg-slate-100 text-slate-500',
}

const stateLabels: Record<string, string> = {
  draft: 'Draft',
  confirmed: 'Confirmed',
  paid: 'Paid',
  cancelled: 'Cancelled',
}

interface Payslip {
  id: string
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
  gross_salary: number
  tax: number
  insurance: number
  other_deductions: number
  net_salary: number
  currency: string
  state: 'draft' | 'confirmed' | 'paid'
}

export default function PayrollPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selectedState, setSelectedState] = useState<string>('')
  const [viewMode, setViewMode] = useState<'runs' | 'payslips'>('runs')

  // Fetch payroll runs
  const { data: runsData, isLoading: runsLoading } = useQuery({
    queryKey: ['payroll-runs', { page, search, state: selectedState }],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20',
        ...(search && { search }),
        ...(selectedState && { state: selectedState }),
      })
      const response = await api.get(`/hr/payroll/runs?${params}`)
      return response.data as PaginatedResponse<PayrollRun>
    },
  })

  // Fetch payslips
  const { data: payslipsData, isLoading: payslipsLoading } = useQuery({
    queryKey: ['payslips', { page, search }],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20',
        ...(search && { search }),
      })
      const response = await api.get(`/hr/payroll/payslips?${params}`)
      return response.data as PaginatedResponse<Payslip>
    },
  })

  const formatCurrency = (amount: number, currency = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }

  const isLoading = viewMode === 'runs' ? runsLoading : payslipsLoading
  const data = viewMode === 'runs' ? runsData : payslipsData

  // Calculate summary for runs
  const runsSummary = runsData?.items.reduce((acc, run) => {
    acc.totalGross += run.total_gross
    acc.totalNet += run.total_net
    acc.totalDeductions += run.total_deductions
    return acc
  }, { totalGross: 0, totalNet: 0, totalDeductions: 0 })

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Payroll</h1>
          <p className="text-slate-500 mt-1">Manage employee salaries and payments</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex bg-slate-100 rounded-lg p-1">
            <button
              onClick={() => setViewMode('runs')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                viewMode === 'runs' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'
              }`}
            >
              Payroll Runs
            </button>
            <button
              onClick={() => setViewMode('payslips')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                viewMode === 'payslips' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'
              }`}
            >
              Payslips
            </button>
          </div>
          <Link
            to="/hr/payroll/new"
            className="btn btn-primary"
          >
            <Plus className="w-4 h-4" />
            New Payroll Run
          </Link>
        </div>
      </div>

      {/* Summary Cards */}
      {viewMode === 'runs' && runsData && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="card p-4">
            <p className="text-sm text-slate-500">Total Gross</p>
            <p className="text-2xl font-bold text-slate-900">{formatCurrency(runsSummary?.totalGross || 0)}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-slate-500">Total Deductions</p>
            <p className="text-2xl font-bold text-red-600">{formatCurrency(runsSummary?.totalDeductions || 0)}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-slate-500">Total Net Pay</p>
            <p className="text-2xl font-bold text-green-600">{formatCurrency(runsSummary?.totalNet || 0)}</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder={viewMode === 'runs' ? 'Search payroll runs...' : 'Search payslips...'}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
            />
          </div>

          {viewMode === 'runs' && (
            <select
              value={selectedState}
              onChange={(e) => setSelectedState(e.target.value)}
              className="select w-full md:w-40"
            >
              <option value="">All States</option>
              <option value="draft">Draft</option>
              <option value="confirmed">Confirmed</option>
              <option value="paid">Paid</option>
              <option value="cancelled">Cancelled</option>
            </select>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="card">
        {isLoading ? (
          <div className="p-12 text-center">
            <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto" />
            <p className="text-slate-500 mt-4">Loading...</p>
          </div>
        ) : data?.items.length === 0 ? (
          <div className="p-12 text-center">
            <DollarSign className="w-12 h-12 text-slate-300 mx-auto" />
            <h3 className="text-lg font-medium text-slate-900 mt-4">No payroll records found</h3>
            <p className="text-slate-500 mt-2">
              {viewMode === 'runs' 
                ? 'Create your first payroll run to get started.'
                : 'Payslips will appear here after running payroll.'}
            </p>
            {viewMode === 'runs' && (
              <Link to="/hr/payroll/new" className="btn btn-primary mt-4">
                <Plus className="w-4 h-4" />
                New Payroll Run
              </Link>
            )}
          </div>
        ) : viewMode === 'runs' ? (
          // Payroll Runs View
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Period</th>
                  <th>Payment Date</th>
                  <th>Employees</th>
                  <th>Gross</th>
                  <th>Deductions</th>
                  <th>Net Pay</th>
                  <th>Status</th>
                  <th className="w-20"></th>
                </tr>
              </thead>
              <tbody>
                {runsData?.items.map((run) => (
                  <tr key={run.id}>
                    <td>
                      <Link
                        to={`/hr/payroll/${run.id}`}
                        className="font-medium text-primary-600 hover:underline"
                      >
                        {run.name}
                      </Link>
                    </td>
                    <td>
                      <span className="text-slate-600">
                        {formatDate(run.period_start)} - {formatDate(run.period_end)}
                      </span>
                    </td>
                    <td>
                      <span className="text-slate-600">{formatDate(run.payment_date)}</span>
                    </td>
                    <td>
                      <span className="font-medium">{run.total_employees}</span>
                    </td>
                    <td>
                      <span>{formatCurrency(run.total_gross, run.currency)}</span>
                    </td>
                    <td>
                      <span className="text-red-600">{formatCurrency(run.total_deductions, run.currency)}</span>
                    </td>
                    <td>
                      <span className="font-medium text-green-600">{formatCurrency(run.total_net, run.currency)}</span>
                    </td>
                    <td>
                      <span className={`badge ${stateColors[run.state]}`}>
                        {stateLabels[run.state]}
                      </span>
                    </td>
                    <td>
                      <div className="relative group">
                        <button className="p-2 hover:bg-slate-100 rounded-lg">
                          <MoreVertical className="w-4 h-4 text-slate-400" />
                        </button>
                        <div className="absolute right-0 top-full mt-1 w-48 bg-white rounded-lg shadow-lg border border-slate-200 py-1 hidden group-hover:block z-10">
                          <Link
                            to={`/hr/payroll/${run.id}`}
                            className="dropdown-item"
                          >
                            <Eye className="w-4 h-4" />
                            View Details
                          </Link>
                          {run.state === 'draft' && (
                            <button className="w-full text-left dropdown-item text-blue-600">
                              <CheckCircle className="w-4 h-4" />
                              Confirm
                            </button>
                          )}
                          {run.state === 'confirmed' && (
                            <button className="w-full text-left dropdown-item text-green-600">
                              <DollarSign className="w-4 h-4" />
                              Mark as Paid
                            </button>
                          )}
                          <button className="w-full text-left dropdown-item">
                            <FileText className="w-4 h-4" />
                            Export Report
                          </button>
                        </div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          // Payslips View
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Department</th>
                  <th>Period</th>
                  <th>Gross</th>
                  <th>Deductions</th>
                  <th>Net Pay</th>
                  <th>Status</th>
                  <th className="w-20"></th>
                </tr>
              </thead>
              <tbody>
                {payslipsData?.items.map((payslip) => (
                  <tr key={payslip.id}>
                    <td>
                      <div>
                        <p className="font-medium text-slate-900">{payslip.employee_name}</p>
                        <p className="text-sm text-slate-500">{payslip.employee_number}</p>
                      </div>
                    </td>
                    <td>{payslip.department || '-'}</td>
                    <td>
                      <span className="text-slate-600">
                        {formatDate(payslip.period_start)} - {formatDate(payslip.period_end)}
                      </span>
                    </td>
                    <td>{formatCurrency(payslip.gross_salary, payslip.currency)}</td>
                    <td>
                      <span className="text-red-600">
                        {formatCurrency(payslip.tax + payslip.insurance + payslip.other_deductions, payslip.currency)}
                      </span>
                    </td>
                    <td>
                      <span className="font-medium text-green-600">
                        {formatCurrency(payslip.net_salary, payslip.currency)}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${stateColors[payslip.state]}`}>
                        {stateLabels[payslip.state]}
                      </span>
                    </td>
                    <td>
                      <div className="relative group">
                        <button className="p-2 hover:bg-slate-100 rounded-lg">
                          <MoreVertical className="w-4 h-4 text-slate-400" />
                        </button>
                        <div className="absolute right-0 top-full mt-1 w-40 bg-white rounded-lg shadow-lg border border-slate-200 py-1 hidden group-hover:block z-10">
                          <Link
                            to={`/hr/payroll/payslips/${payslip.id}`}
                            className="dropdown-item"
                          >
                            <Eye className="w-4 h-4" />
                            View Payslip
                          </Link>
                          <button className="w-full text-left dropdown-item">
                            <Download className="w-4 h-4" />
                            Download PDF
                          </button>
                        </div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {data && data.pages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200">
            <p className="text-sm text-slate-500">
              Showing {((page - 1) * 20) + 1} to {Math.min(page * 20, data.total)} of {data.total} results
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn btn-secondary btn-sm"
              >
                Previous
              </button>
              <button
                onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
                disabled={page === data.pages}
                className="btn btn-secondary btn-sm"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
