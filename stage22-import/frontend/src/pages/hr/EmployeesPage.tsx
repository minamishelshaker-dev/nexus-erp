/**
 * Nexus ERP - Employees Page
 * Employee management
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, PaginatedResponse } from '../../services/api'
import {
  Plus,
  Search,
  Users,
  Mail,
  Phone,
  MoreVertical,
  Eye,
  Edit,
  Trash2,
  Briefcase,
  Building2,
  UserCheck,
} from 'lucide-react'

interface Employee {
  id: string
  employee_number: string
  first_name: string
  last_name: string
  full_name: string
  email: string
  phone: string
  department: string
  department_name: string
  position: string
  manager_id?: string
  manager_name?: string
  hire_date: string
  status: 'active' | 'on_leave' | 'terminated'
  employment_type: 'full_time' | 'part_time' | 'contract' | 'intern'
  salary: number
  currency: string
  avatar_url?: string
}

const statusColors: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  on_leave: 'bg-yellow-100 text-yellow-700',
  terminated: 'bg-slate-100 text-slate-500',
}

const statusLabels: Record<string, string> = {
  active: 'Active',
  on_leave: 'On Leave',
  terminated: 'Terminated',
}

const employmentTypeColors: Record<string, string> = {
  full_time: 'bg-blue-100 text-blue-700',
  part_time: 'bg-purple-100 text-purple-700',
  contract: 'bg-orange-100 text-orange-700',
  intern: 'bg-cyan-100 text-cyan-700',
}

const employmentTypeLabels: Record<string, string> = {
  full_time: 'Full Time',
  part_time: 'Part Time',
  contract: 'Contract',
  intern: 'Intern',
}

export default function EmployeesPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selectedDepartment, setSelectedDepartment] = useState<string>('')
  const [selectedStatus, setSelectedStatus] = useState<string>('')

  // Fetch employees
  const { data, isLoading, error } = useQuery({
    queryKey: ['employees', { page, search, department: selectedDepartment, status: selectedStatus }],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20',
        ...(search && { search }),
        ...(selectedDepartment && { department: selectedDepartment }),
        ...(selectedStatus && { status: selectedStatus }),
      })
      const response = await api.get(`/hr/employees?${params}`)
      return response.data as PaginatedResponse<Employee>
    },
  })

  // Fetch departments for filter
  const { data: departments } = useQuery({
    queryKey: ['departments'],
    queryFn: async () => {
      const response = await api.get('/hr/departments')
      return response.data
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/hr/employees/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] })
    },
  })

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this employee record?')) {
      await deleteMutation.mutateAsync(id)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }

  // Calculate summary
  const summary = data?.items.reduce((acc, emp) => {
    acc.total++
    if (emp.status === 'active') acc.active++
    if (emp.employment_type === 'full_time') acc.fullTime++
    return acc
  }, { total: 0, active: 0, fullTime: 0 })

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Employees</h1>
          <p className="text-slate-500 mt-1">Manage your workforce</p>
        </div>
        <Link
          to="/hr/employees/new"
          className="btn btn-primary"
        >
          <Plus className="w-4 h-4" />
          Add Employee
        </Link>
      </div>

      {/* Summary Cards */}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <Users className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Total Employees</p>
                <p className="text-xl font-bold text-slate-900">{summary?.total || 0}</p>
              </div>
            </div>
          </div>
          <div className="card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                <UserCheck className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Active</p>
                <p className="text-xl font-bold text-green-600">{summary?.active || 0}</p>
              </div>
            </div>
          </div>
          <div className="card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                <Briefcase className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Full Time</p>
                <p className="text-xl font-bold text-slate-900">{summary?.fullTime || 0}</p>
              </div>
            </div>
          </div>
          <div className="card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                <Building2 className="w-5 h-5 text-orange-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Departments</p>
                <p className="text-xl font-bold text-slate-900">{departments?.length || 0}</p>
              </div>
            </div>
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
              placeholder="Search employees..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
            />
          </div>

          {/* Department filter */}
          <select
            value={selectedDepartment}
            onChange={(e) => setSelectedDepartment(e.target.value)}
            className="select w-full md:w-48"
          >
            <option value="">All Departments</option>
            {departments?.map((dept: { id: string; name: string }) => (
              <option key={dept.id} value={dept.id}>{dept.name}</option>
            ))}
          </select>

          {/* Status filter */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="select w-full md:w-40"
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="on_leave">On Leave</option>
            <option value="terminated">Terminated</option>
          </select>
        </div>
      </div>

      {/* Employees table */}
      <div className="card">
        {isLoading ? (
          <div className="p-12 text-center">
            <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto" />
            <p className="text-slate-500 mt-4">Loading employees...</p>
          </div>
        ) : error ? (
          <div className="p-12 text-center">
            <p className="text-red-600">Failed to load employees</p>
          </div>
        ) : data?.items.length === 0 ? (
          <div className="p-12 text-center">
            <Users className="w-12 h-12 text-slate-300 mx-auto" />
            <h3 className="text-lg font-medium text-slate-900 mt-4">No employees found</h3>
            <p className="text-slate-500 mt-2">Get started by adding your first employee.</p>
            <Link to="/hr/employees/new" className="btn btn-primary mt-4">
              <Plus className="w-4 h-4" />
              Add Employee
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Department</th>
                  <th>Position</th>
                  <th>Contact</th>
                  <th>Hire Date</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th className="w-20"></th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((employee) => (
                  <tr key={employee.id} className={employee.status === 'terminated' ? 'bg-slate-50 opacity-60' : ''}>
                    <td>
                      <Link
                        to={`/hr/employees/${employee.id}`}
                        className="flex items-center gap-3 hover:text-primary-600"
                      >
                        <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center overflow-hidden">
                          {employee.avatar_url ? (
                            <img src={employee.avatar_url} alt="" className="w-full h-full object-cover" />
                          ) : (
                            <span className="font-medium text-primary-600">
                              {employee.first_name.charAt(0)}{employee.last_name.charAt(0)}
                            </span>
                          )}
                        </div>
                        <div>
                          <p className="font-medium text-slate-900">{employee.full_name}</p>
                          <p className="text-sm text-slate-500">{employee.employee_number}</p>
                        </div>
                      </Link>
                    </td>
                    <td>
                      <span className="text-slate-600">{employee.department_name || '-'}</span>
                    </td>
                    <td>
                      <div>
                        <p className="text-slate-900">{employee.position}</p>
                        {employee.manager_name && (
                          <p className="text-xs text-slate-500">Reports to {employee.manager_name}</p>
                        )}
                      </div>
                    </td>
                    <td>
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 text-sm">
                          <Mail className="w-3 h-3 text-slate-400" />
                          <span>{employee.email}</span>
                        </div>
                        {employee.phone && (
                          <div className="flex items-center gap-2 text-sm text-slate-500">
                            <Phone className="w-3 h-3" />
                            <span>{employee.phone}</span>
                          </div>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className="text-slate-500">{formatDate(employee.hire_date)}</span>
                    </td>
                    <td>
                      <span className={`badge ${employmentTypeColors[employee.employment_type]}`}>
                        {employmentTypeLabels[employee.employment_type]}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${statusColors[employee.status]}`}>
                        {statusLabels[employee.status]}
                      </span>
                    </td>
                    <td>
                      <div className="relative group">
                        <button className="p-2 hover:bg-slate-100 rounded-lg">
                          <MoreVertical className="w-4 h-4 text-slate-400" />
                        </button>
                        <div className="absolute right-0 top-full mt-1 w-40 bg-white rounded-lg shadow-lg border border-slate-200 py-1 hidden group-hover:block z-10">
                          <Link
                            to={`/hr/employees/${employee.id}`}
                            className="dropdown-item"
                          >
                            <Eye className="w-4 h-4" />
                            View Profile
                          </Link>
                          <Link
                            to={`/hr/employees/${employee.id}/edit`}
                            className="dropdown-item"
                          >
                            <Edit className="w-4 h-4" />
                            Edit
                          </Link>
                          <button
                            onClick={() => handleDelete(employee.id)}
                            className="w-full text-left dropdown-item text-red-600"
                          >
                            <Trash2 className="w-4 h-4" />
                            Delete
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
