/**
 * Nexus ERP - Projects Page
 * Project management with Kanban view
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { api, PaginatedResponse } from '../../services/api'
import {
  Plus,
  Search,
  FolderKanban,
  Calendar,
  Users,
  DollarSign,
  MoreVertical,
  Eye,
  Edit,
  Trash2,
  Play,
  Pause,
  CheckCircle,
  AlertCircle,
  Clock,
  TrendingUp,
} from 'lucide-react'

interface Project {
  id: string
  name: string
  code: string
  description?: string
  customer_id?: string
  customer_name?: string
  manager_id: string
  manager_name: string
  start_date: string
  end_date?: string
  planned_end_date?: string
  state: 'draft' | 'in_progress' | 'on_hold' | 'completed' | 'cancelled'
  priority: 'low' | 'medium' | 'high' | 'urgent'
  progress: number
  budget: number
  actual_cost: number
  remaining_budget: number
  tasks_count: number
  tasks_completed: number
  created_at: string
}

const stateColors: Record<string, string> = {
  draft: 'bg-slate-100 text-slate-700',
  in_progress: 'bg-blue-100 text-blue-700',
  on_hold: 'bg-yellow-100 text-yellow-700',
  completed: 'bg-green-100 text-green-700',
  cancelled: 'bg-red-100 text-red-500',
}

const stateLabels: Record<string, string> = {
  draft: 'Draft',
  in_progress: 'In Progress',
  on_hold: 'On Hold',
  completed: 'Completed',
  cancelled: 'Cancelled',
}

const priorityColors: Record<string, string> = {
  low: 'bg-slate-100 text-slate-600',
  medium: 'bg-blue-100 text-blue-600',
  high: 'bg-orange-100 text-orange-600',
  urgent: 'bg-red-100 text-red-600',
}

export default function ProjectsPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selectedState, setSelectedState] = useState<string>('')
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('grid')

  // Fetch projects
  const { data, isLoading, error } = useQuery({
    queryKey: ['projects', { page, search, state: selectedState }],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20',
        ...(search && { search }),
        ...(selectedState && { state: selectedState }),
      })
      const response = await api.get(`/projects?${params}`)
      return response.data as PaginatedResponse<Project>
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/projects/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this project?')) {
      await deleteMutation.mutateAsync(id)
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
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }

  // Calculate summary
  const summary = data?.items.reduce((acc, project) => {
    acc.total++
    if (project.state === 'in_progress') acc.active++
    if (project.state === 'completed') acc.completed++
    acc.totalBudget += project.budget
    acc.totalCost += project.actual_cost
    return acc
  }, { total: 0, active: 0, completed: 0, totalBudget: 0, totalCost: 0 })

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Projects</h1>
          <p className="text-slate-500 mt-1">Manage your projects and tasks</p>
        </div>
        <Link
          to="/projects/new"
          className="btn btn-primary"
        >
          <Plus className="w-4 h-4" />
          New Project
        </Link>
      </div>

      {/* Summary Cards */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="card p-4">
            <p className="text-sm text-slate-500">Total Projects</p>
            <p className="text-2xl font-bold text-slate-900">{summary?.total || 0}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-slate-500">Active</p>
            <p className="text-2xl font-bold text-blue-600">{summary?.active || 0}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-slate-500">Completed</p>
            <p className="text-2xl font-bold text-green-600">{summary?.completed || 0}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-slate-500">Total Budget</p>
            <p className="text-2xl font-bold text-slate-900">{formatCurrency(summary?.totalBudget || 0)}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-slate-500">Actual Cost</p>
            <p className="text-2xl font-bold text-purple-600">{formatCurrency(summary?.totalCost || 0)}</p>
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
              placeholder="Search projects..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
            />
          </div>
          <select
            value={selectedState}
            onChange={(e) => setSelectedState(e.target.value)}
            className="select w-full md:w-40"
          >
            <option value="">All States</option>
            <option value="draft">Draft</option>
            <option value="in_progress">In Progress</option>
            <option value="on_hold">On Hold</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
          </select>
          <div className="flex bg-slate-100 rounded-lg p-1">
            <button
              onClick={() => setViewMode('grid')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                viewMode === 'grid' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'
              }`}
            >
              Grid
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                viewMode === 'list' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'
              }`}
            >
              List
            </button>
          </div>
        </div>
      </div>

      {/* Projects Grid/List */}
      {isLoading ? (
        <div className="card p-12 text-center">
          <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto" />
          <p className="text-slate-500 mt-4">Loading projects...</p>
        </div>
      ) : error ? (
        <div className="card p-12 text-center">
          <p className="text-red-600">Failed to load projects</p>
        </div>
      ) : data?.items.length === 0 ? (
        <div className="card p-12 text-center">
          <FolderKanban className="w-12 h-12 text-slate-300 mx-auto" />
          <h3 className="text-lg font-medium text-slate-900 mt-4">No projects found</h3>
          <p className="text-slate-500 mt-2">Get started by creating your first project.</p>
          <Link to="/projects/new" className="btn btn-primary mt-4">
            <Plus className="w-4 h-4" />
            New Project
          </Link>
        </div>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {data?.items.map((project) => (
            <div key={project.id} className="card overflow-hidden">
              <div className="p-4 border-b border-slate-100">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center">
                      <FolderKanban className="w-6 h-6 text-primary-600" />
                    </div>
                    <div>
                      <Link
                        to={`/projects/${project.id}`}
                        className="font-semibold text-slate-900 hover:text-primary-600"
                      >
                        {project.name}
                      </Link>
                      <p className="text-sm text-slate-500">{project.code}</p>
                    </div>
                  </div>
                  <div className="relative group">
                    <button className="p-2 hover:bg-slate-100 rounded-lg">
                      <MoreVertical className="w-4 h-4 text-slate-400" />
                    </button>
                    <div className="absolute right-0 top-full mt-1 w-40 bg-white rounded-lg shadow-lg border border-slate-200 py-1 hidden group-hover:block z-10">
                      <Link
                        to={`/projects/${project.id}`}
                        className="dropdown-item"
                      >
                        <Eye className="w-4 h-4" />
                        View Details
                      </Link>
                      <Link
                        to={`/projects/${project.id}/edit`}
                        className="dropdown-item"
                      >
                        <Edit className="w-4 h-4" />
                        Edit
                      </Link>
                      <button
                        onClick={() => handleDelete(project.id)}
                        className="w-full text-left dropdown-item text-red-600"
                      >
                        <Trash2 className="w-4 h-4" />
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              <div className="p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className={`badge ${stateColors[project.state]}`}>
                    {stateLabels[project.state]}
                  </span>
                  <span className={`badge ${priorityColors[project.priority]}`}>
                    {project.priority}
                  </span>
                </div>
                
                {project.customer_name && (
                  <div className="text-sm text-slate-600">
                    <span className="text-slate-400">Customer:</span> {project.customer_name}
                  </div>
                )}
                
                <div className="flex items-center gap-4 text-sm text-slate-600">
                  <div className="flex items-center gap-1">
                    <Calendar className="w-4 h-4" />
                    {formatDate(project.start_date)}
                  </div>
                  {project.end_date && (
                    <div className="flex items-center gap-1">
                      <Clock className="w-4 h-4" />
                      {formatDate(project.end_date)}
                    </div>
                  )}
                </div>

                {/* Progress */}
                <div>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="text-slate-500">Progress</span>
                    <span className="font-medium">{project.progress}%</span>
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-2">
                    <div
                      className="bg-primary-500 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${project.progress}%` }}
                    />
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
                    {project.tasks_completed} / {project.tasks_count} tasks
                  </div>
                </div>

                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-1 text-slate-600">
                    <Users className="w-4 h-4" />
                    <span>{project.manager_name}</span>
                  </div>
                  <div className="flex items-center gap-1 text-slate-600">
                    <DollarSign className="w-4 h-4" />
                    <span>{formatCurrency(project.budget)}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="table">
            <thead>
              <tr>
                <th>Project</th>
                <th>Customer</th>
                <th>Manager</th>
                <th>Start Date</th>
                <th>Progress</th>
                <th>Budget</th>
                <th>Status</th>
                <th className="w-20"></th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((project) => (
                <tr key={project.id}>
                  <td>
                    <Link
                      to={`/projects/${project.id}`}
                      className="flex items-center gap-3 hover:text-primary-600"
                    >
                      <div className="w-8 h-8 bg-primary-100 rounded-lg flex items-center justify-center">
                        <FolderKanban className="w-4 h-4 text-primary-600" />
                      </div>
                      <div>
                        <p className="font-medium text-slate-900">{project.name}</p>
                        <p className="text-xs text-slate-500">{project.code}</p>
                      </div>
                    </Link>
                  </td>
                  <td>
                    <span className="text-slate-600">{project.customer_name || '-'}</span>
                  </td>
                  <td>
                    <span className="text-slate-600">{project.manager_name}</span>
                  </td>
                  <td>
                    <span className="text-slate-600">{formatDate(project.start_date)}</span>
                  </td>
                  <td>
                    <div className="flex items-center gap-2">
                      <div className="w-16 bg-slate-200 rounded-full h-2">
                        <div
                          className="bg-primary-500 h-2 rounded-full"
                          style={{ width: `${project.progress}%` }}
                        />
                      </div>
                      <span className="text-sm">{project.progress}%</span>
                    </div>
                  </td>
                  <td>
                    <span className="font-medium">{formatCurrency(project.budget)}</span>
                  </td>
                  <td>
                    <span className={`badge ${stateColors[project.state]}`}>
                      {stateLabels[project.state]}
                    </span>
                  </td>
                  <td>
                    <div className="relative group">
                      <button className="p-2 hover:bg-slate-100 rounded-lg">
                        <MoreVertical className="w-4 h-4 text-slate-400" />
                      </button>
                      <div className="absolute right-0 top-full mt-1 w-40 bg-white rounded-lg shadow-lg border border-slate-200 py-1 hidden group-hover:block z-10">
                        <Link
                          to={`/projects/${project.id}`}
                          className="dropdown-item"
                        >
                          <Eye className="w-4 h-4" />
                          View
                        </Link>
                        <Link
                          to={`/projects/${project.id}/edit`}
                          className="dropdown-item"
                        >
                          <Edit className="w-4 h-4" />
                          Edit
                        </Link>
                        <button
                          onClick={() => handleDelete(project.id)}
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
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn btn-secondary btn-sm"
          >
            Previous
          </button>
          <span className="text-sm text-slate-500">
            Page {page} of {data.pages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
            disabled={page === data.pages}
            className="btn btn-secondary btn-sm"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
