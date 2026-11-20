/**
 * Nexus ERP - Attendance Page
 * Employee attendance tracking
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, PaginatedResponse } from '../../services/api'
import {
  Search,
  Calendar,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  User,
  Filter,
  Download,
} from 'lucide-react'

interface AttendanceRecord {
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
  notes: string
  department: string
}

const statusColors: Record<string, string> = {
  present: 'bg-green-100 text-green-700',
  absent: 'bg-red-100 text-red-700',
  late: 'bg-yellow-100 text-yellow-700',
  early_leave: 'bg-orange-100 text-orange-700',
  half_day: 'bg-purple-100 text-purple-700',
  leave: 'bg-blue-100 text-blue-700',
}

const statusLabels: Record<string, string> = {
  present: 'Present',
  absent: 'Absent',
  late: 'Late',
  early_leave: 'Early Leave',
  half_day: 'Half Day',
  leave: 'On Leave',
}

export default function AttendancePage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0])
  const [selectedDepartment, setSelectedDepartment] = useState<string>('')
  const [selectedStatus, setSelectedStatus] = useState<string>('')

  // Fetch attendance records
  const { data, isLoading, error } = useQuery({
    queryKey: ['attendance', { page, date: selectedDate, search, department: selectedDepartment, status: selectedStatus }],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20',
        date: selectedDate,
        ...(search && { search }),
        ...(selectedDepartment && { department: selectedDepartment }),
        ...(selectedStatus && { status: selectedStatus }),
      })
      const response = await api.get(`/hr/attendance?${params}`)
      return response.data as PaginatedResponse<AttendanceRecord>
    },
  })

  // Fetch departments for filter
  const { data: departments } = useQuery({
    queryKey: ['departments-list'],
    queryFn: async () => {
      const response = await api.get('/hr/departments')
      return response.data
    },
  })

  // Check-in mutation
  const checkInMutation = useMutation({
    mutationFn: async (employeeId: string) => {
      await api.post('/hr/attendance/check-in', { employee_id: employeeId })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['attendance'] })
    },
  })

  // Check-out mutation
  const checkOutMutation = useMutation({
    mutationFn: async (employeeId: string) => {
      await api.post('/hr/attendance/check-out', { employee_id: employeeId })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['attendance'] })
    },
  })

  const formatTime = (timeString: string) => {
    if (!timeString) return '-'
    return new Date(timeString).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  // Calculate summary
  const summary = data?.items.reduce((acc, record) => {
    acc.total++
    if (record.status === 'present') acc.present++
    if (record.status === 'absent') acc.absent++
    if (record.status === 'late') acc.late++
    if (record.work_hours > 8) acc.overtime++
    acc.totalHours += record.work_hours
    return acc
  }, { total: 0, present: 0, absent: 0, late: 0, overtime: 0, totalHours: 0 })

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Attendance</h1>
          <p className="text-slate-500 mt-1">Track employee attendance and working hours</p>
        </div>
        <div className="flex gap-2">
          <button className="btn btn-secondary">
            <Download className="w-4 h-4" />
            Export
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="card p-4">
            <p className="text-sm text-slate-500">Total</p>
            <p className="text-2xl font-bold text-slate-900">{summary?.total || 0}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-slate-500">Present</p>
            <p className="text-2xl font-bold text-green-600">{summary?.present || 0}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-slate-500">Late</p>
            <p className="text-2xl font-bold text-yellow-600">{summary?.late || 0}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-slate-500">Absent</p>
            <p className="text-2xl font-bold text-red-600">{summary?.absent || 0}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-slate-500">Total Hours</p>
            <p className="text-2xl font-bold text-slate-900">{summary?.totalHours?.toFixed(1) || 0}h</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Date picker */}
          <div className="relative">
            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="select pl-10"
            />
          </div>

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
            <option value="present">Present</option>
            <option value="absent">Absent</option>
            <option value="late">Late</option>
            <option value="early_leave">Early Leave</option>
            <option value="half_day">Half Day</option>
            <option value="leave">On Leave</option>
          </select>
        </div>
      </div>

      {/* Selected Date Display */}
      <div className="text-center">
        <p className="text-lg font-medium text-slate-900">{formatDate(selectedDate)}</p>
      </div>

      {/* Attendance table */}
      <div className="card">
        {isLoading ? (
          <div className="p-12 text-center">
            <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto" />
            <p className="text-slate-500 mt-4">Loading attendance...</p>
          </div>
        ) : error ? (
          <div className="p-12 text-center">
            <p className="text-red-600">Failed to load attendance</p>
          </div>
        ) : data?.items.length === 0 ? (
          <div className="p-12 text-center">
            <Clock className="w-12 h-12 text-slate-300 mx-auto" />
            <h3 className="text-lg font-medium text-slate-900 mt-4">No attendance records</h3>
            <p className="text-slate-500 mt-2">No attendance records found for the selected date.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Department</th>
                  <th>Check In</th>
                  <th>Check Out</th>
                  <th>Work Hours</th>
                  <th>Overtime</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((record) => (
                  <tr key={record.id}>
                    <td>
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
                          <User className="w-5 h-5 text-primary-600" />
                        </div>
                        <div>
                          <p className="font-medium text-slate-900">{record.employee_name}</p>
                          <p className="text-sm text-slate-500">{record.employee_number}</p>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="text-slate-600">{record.department || '-'}</span>
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        {record.check_in ? (
                          <>
                            <CheckCircle className="w-4 h-4 text-green-500" />
                            <span>{formatTime(record.check_in)}</span>
                          </>
                        ) : (
                          <>
                            <XCircle className="w-4 h-4 text-slate-300" />
                            <span className="text-slate-400">Not checked in</span>
                          </>
                        )}
                      </div>
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        {record.check_out ? (
                          <>
                            <CheckCircle className="w-4 h-4 text-green-500" />
                            <span>{formatTime(record.check_out)}</span>
                          </>
                        ) : (
                          <span className="text-slate-400">-</span>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className="font-medium">{record.work_hours?.toFixed(1) || 0}h</span>
                    </td>
                    <td>
                      {record.overtime_hours > 0 ? (
                        <span className="text-purple-600 font-medium">{record.overtime_hours?.toFixed(1)}h</span>
                      ) : (
                        <span className="text-slate-400">-</span>
                      )}
                    </td>
                    <td>
                      <span className={`badge ${statusColors[record.status]}`}>
                        {statusLabels[record.status]}
                      </span>
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
