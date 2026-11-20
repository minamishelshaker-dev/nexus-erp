/**
 * Nexus ERP - Timesheets Page
 * Time tracking and timesheet management
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, PaginatedResponse } from '../../services/api'
import {
  Plus,
  Search,
  Clock,
  Calendar,
  User,
  CheckCircle,
  XCircle,
  MoreVertical,
  Eye,
  Edit,
  Trash2,
  Send,
  DollarSign,
  FileText,
  Download,
} from 'lucide-react'

interface Timesheet {
  id: string
  employee_id: string
  employee_name: string
  employee_number: string
  project_id?: string
  project_name?: string
  task_id?: string
  task_name?: string
  date: string
  hours: number
  description?: string
  billable: boolean
  hourly_rate: number
  amount: number
  state: 'draft' | 'submitted' | 'approved' | 'rejected' | 'invoiced'
  approved_by?: string
  approver_name?: string
  approved_at?: string
  rejection_reason?: string
  created_at: string
}

const stateColors: Record<string, string> = {
  draft: 'bg-slate-100 text-slate-700',
  submitted: 'bg-blue-100 text-blue-700',
  approved: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
  invoiced: 'bg-purple-100 text-purple-700',
}

const stateLabels: Record<string, string> = {
  draft: 'Draft',
  submitted: 'Submitted',
  approved: 'Approved',
  rejected: 'Rejected',
  invoiced: 'Invoiced',
}

export default function TimesheetsPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selectedEmployee, setSelectedEmployee] = useState<string>('')
  const [selectedProject, setSelectedProject] = useState<string>('')
  const [selectedState, setSelectedState] = useState<string>('')
  const [dateFrom, setDateFrom] = useState<string>('')
  const [dateTo, setDateTo] = useState<string>('')

  // Fetch timesheets
  const { data, isLoading, error } = useQuery({
    queryKey: ['timesheets', { page, search, employee: selectedEmployee, project: selectedProject, state: selectedState, dateFrom, dateTo }],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20',
        ...(search && { search }),
        ...(selectedEmployee && { employee_id: selectedEmployee }),
        ...(selectedProject && { project_id: selectedProject }),
        ...(selectedState && { state: selectedState }),
        ...(dateFrom && { date_from: dateFrom }),
        ...(dateTo && { date_to: dateTo }),
      })
      const response = await api.get(`/projects/timesheets?${params}`)
      return response.data as PaginatedResponse<Timesheet>
    },
  })

  // Fetch projects for filter
  const { data: projects } = useQuery({
    queryKey: ['projects-list'],
    queryFn: async () => {
      const response = await api.get('/projects?page_size=100')
      return response.data
    },
  })

  // Fetch employees for filter
  const { data: employees } = useQuery({
    queryKey: ['employees-list'],
    queryFn: async () => {
      const response = await api.get('/hr/employees?page_size=100')
      return response.data
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/projects/timesheets/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['timesheets'] })
    },
  })

  // Submit mutation
  const submitMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/projects/timesheets/${id}/submit`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['timesheets'] })
    },
  })

  // Approve mutation
  const approveMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/projects/timesheets/${id}/approve`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['timesheets'] })
    },
  })

  // Reject mutation
  const rejectMutation = useMutation({
    mutationFn: async ({ id, reason }: { id: string; reason: string }) => {
      await api.post(`/projects/timesheets/${id}/reject`, { reason })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['timesheets'] })
    },
  })

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this timesheet entry?')) {
      await deleteMutation.mutateAsync(id)
    }
  }

  const handleSubmit = async (id: string) => {
    if (confirm('Submit this timesheet entry for approval?')) {
      await submitMutation.mutateAsync(id)
    }
  }

  const handleApprove = async (id: string) => {
    if (confirm('Approve this timesheet entry?')) {
      await approveMutation.mutateAsync(id)
    }
  }

  const handleReject = async (id: string) => {
    const reason = prompt('Enter rejection reason:')
    if (reason) {
      await rejectMutation.mutateAsync({ id, reason })
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }

  // Calculate summary
  const summary = data?.items.reduce((acc, ts) => {
    acc.totalHours += ts.hours
    acc.totalAmount += ts.amount
    if (ts.billable) acc.billableHours += ts.hours
    if (ts.state === 'approved') acc.approvedHours += ts.hours
    return acc
  }, { totalHours: 0, billableHours: 0, approvedHours: 0, totalAmount: 0 })

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Timesheets</h1>
          <p className="text-slate-500 mt-1">Track and manage time entries</p>
        </div>
        <div className="flex gap-2">
          <button className="btn btn-secondary">
            <Download className="w-4 h-4" />
            Export
          </button>
          <Link
            to="/projects/timesheets/new"
            className="btn btn-primary"
          >
            <Plus className="w-4 h-4" />
            Log Time
          </Link>
        </div>
      </div>

      {/* Summary Cards */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="card p-4">
            <p className="text-sm text-slate-500">Total Hours</p>
            <p className="text-2xl font-bold text-slate-900">{summary?.totalHours?.toFixed(1) || 0}h</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-slate-500">Billable Hours</p>
            <p className="text-2xl font-bold text-blue-600">{summary?.billableHours?.toFixed(1) || 0}h</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-slate-500">Approved Hours</p>
            <p className="text-2xl font-bold text-green-600">{summary?.approvedHours?.toFixed(1) || 0}h</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-slate-500">Total Value</p>
            <p className="text-2xl font-bold text-purple-600">{formatCurrency(summary?.totalAmount || 0)}</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search timesheets..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
            />
          </div>
          <select
            value={selectedEmployee}
            onChange={(e) => setSelectedEmployee(e.target.value)}
            className="select w-full md:w-48"
          >
            <option value="">All Employees</option>
            {employees?.items?.map((emp: { id: string; full_name: string }) => (
              <option key={emp.id} value={emp.id}>{emp.full_name}</option>
            ))}
          </select>
          <select
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
            className="select w-full md:w-48"
          >
            <option value="">All Projects</option>
            {projects?.items?.map((project: { id: string; name: string }) => (
              <option key={project.id} value={project.id}>{project.name}</option>
            ))}
          </select>
          <select
            value={selectedState}
            onChange={(e) => setSelectedState(e.target.value)}
            className="select w-full md:w-40"
          >
            <option value="">All States</option>
            {Object.entries(stateLabels).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="select w-full md:w-36"
          />
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="select w-full md:w-36"
          />
        </div>
      </div>

      {/* Timesheets table */}
      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center">
            <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto" />
            <p className="text-slate-500 mt-4">Loading timesheets...</p>
          </div>
        ) : error ? (
          <div className="p-12 text-center">
            <p className="text-red-600">Failed to load timesheets</p>
          </div>
        ) : data?.items.length === 0 ? (
          <div className="p-12 text-center">
            <Clock className="w-12 h-12 text-slate-300 mx-auto" />
            <h3 className="text-lg font-medium text-slate-900 mt-4">No timesheet entries found</h3>
            <p className="text-slate-500 mt-2">Start tracking time by logging your first entry.</p>
            <Link to="/projects/timesheets/new" className="btn btn-primary mt-4">
              <Plus className="w-4 h-4" />
              Log Time
            </Link>
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Employee</th>
                <th>Date</th>
                <th>Project / Task</th>
                <th>Hours</th>
                <th>Billable</th>
                <th>Rate</th>
                <th>Amount</th>
                <th>Status</th>
                <th className="w-20"></th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((timesheet) => (
                <tr key={timesheet.id} className={timesheet.state === 'rejected' ? 'bg-red-50' : ''}>
                  <td>
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                        <span className="text-sm font-medium text-primary-600">
                          {timesheet.employee_name.charAt(0)}
                        </span>
                      </div>
                      <div>
                        <p className="font-medium text-slate-900">{timesheet.employee_name}</p>
                        <p className="text-xs text-slate-500">{timesheet.employee_number}</p>
                      </div>
                    </div>
                  </td>
                  <td>
                    <span className="text-slate-600">{formatDate(timesheet.date)}</span>
                  </td>
                  <td>
                    <div>
                      {timesheet.project_name ? (
                        <>
                          <p className="font-medium text-slate-900">{timesheet.project_name}</p>
                          {timesheet.task_name && (
                            <p className="text-xs text-slate-500">{timesheet.task_name}</p>
                          )}
                        </>
                      ) : (
                        <span className="text-slate-400">No project</span>
                      )}
                    </div>
                  </td>
                  <td>
                    <span className="font-medium">{timesheet.hours.toFixed(1)}h</span>
                  </td>
                  <td>
                    {timesheet.billable ? (
                      <span className="badge bg-green-100 text-green-700">Yes</span>
                    ) : (
                      <span className="badge bg-slate-100 text-slate-500">No</span>
                    )}
                  </td>
                  <td>
                    <span className="text-slate-600">{formatCurrency(timesheet.hourly_rate)}/h</span>
                  </td>
                  <td>
                    <span className="font-medium">{formatCurrency(timesheet.amount)}</span>
                  </td>
                  <td>
                    <span className={`badge ${stateColors[timesheet.state]}`}>
                      {stateLabels[timesheet.state]}
                    </span>
                  </td>
                  <td>
                    <div className="relative group">
                      <button className="p-2 hover:bg-slate-100 rounded-lg">
                        <MoreVertical className="w-4 h-4 text-slate-400" />
                      </button>
                      <div className="absolute right-0 top-full mt-1 w-48 bg-white rounded-lg shadow-lg border border-slate-200 py-1 hidden group-hover:block z-10">
                        <Link
                          to={`/projects/timesheets/${timesheet.id}`}
                          className="dropdown-item"
                        >
                          <Eye className="w-4 h-4" />
                          View Details
                        </Link>
                        {timesheet.state === 'draft' && (
                          <>
                            <Link
                              to={`/projects/timesheets/${timesheet.id}/edit`}
                              className="dropdown-item"
                            >
                              <Edit className="w-4 h-4" />
                              Edit
                            </Link>
                            <button
                              onClick={() => handleSubmit(timesheet.id)}
                              className="w-full text-left dropdown-item text-blue-600"
                            >
                              <Send className="w-4 h-4" />
                              Submit
                            </button>
                            <button
                              onClick={() => handleDelete(timesheet.id)}
                              className="w-full text-left dropdown-item text-red-600"
                            >
                              <Trash2 className="w-4 h-4" />
                              Delete
                            </button>
                          </>
                        )}
                        {timesheet.state === 'submitted' && (
                          <>
                            <button
                              onClick={() => handleApprove(timesheet.id)}
                              className="w-full text-left dropdown-item text-green-600"
                            >
                              <CheckCircle className="w-4 h-4" />
                              Approve
                            </button>
                            <button
                              onClick={() => handleReject(timesheet.id)}
                              className="w-full text-left dropdown-item text-red-600"
                            >
                              <XCircle className="w-4 h-4" />
                              Reject
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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
