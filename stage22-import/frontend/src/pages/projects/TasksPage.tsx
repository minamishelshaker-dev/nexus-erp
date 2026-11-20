/**
 * Nexus ERP - Tasks Page
 * Task management with Kanban-style board
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, PaginatedResponse } from '../../services/api'
import {
  Plus,
  Search,
  CheckSquare,
  Calendar,
  Clock,
  User,
  MoreVertical,
  Eye,
  Edit,
  Trash2,
  Flag,
  Tag,
  MessageSquare,
  ArrowRight,
} from 'lucide-react'

interface Task {
  id: string
  name: string
  description?: string
  project_id: string
  project_name: string
  parent_id?: string
  assignee_id?: string
  assignee_name?: string
  state: 'backlog' | 'todo' | 'in_progress' | 'review' | 'done' | 'cancelled'
  priority: 'low' | 'medium' | 'high' | 'urgent'
  task_type: 'task' | 'bug' | 'feature' | 'improvement'
  estimated_hours: number
  actual_hours: number
  remaining_hours: number
  start_date?: string
  due_date?: string
  completed_date?: string
  progress: number
  tags: string[]
  created_by: string
  created_at: string
}

const stateColors: Record<string, string> = {
  backlog: 'bg-slate-100 text-slate-600',
  todo: 'bg-blue-100 text-blue-700',
  in_progress: 'bg-yellow-100 text-yellow-700',
  review: 'bg-purple-100 text-purple-700',
  done: 'bg-green-100 text-green-700',
  cancelled: 'bg-red-100 text-red-500',
}

const stateLabels: Record<string, string> = {
  backlog: 'Backlog',
  todo: 'To Do',
  in_progress: 'In Progress',
  review: 'In Review',
  done: 'Done',
  cancelled: 'Cancelled',
}

const priorityColors: Record<string, string> = {
  low: 'border-l-slate-300',
  medium: 'border-l-blue-400',
  high: 'border-l-orange-400',
  urgent: 'border-l-red-400',
}

const typeColors: Record<string, string> = {
  task: 'bg-blue-50 text-blue-600',
  bug: 'bg-red-50 text-red-600',
  feature: 'bg-purple-50 text-purple-600',
  improvement: 'bg-green-50 text-green-600',
}

export default function TasksPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selectedProject, setSelectedProject] = useState<string>('')
  const [selectedState, setSelectedState] = useState<string>('')
  const [selectedAssignee, setSelectedAssignee] = useState<string>('')
  const [viewMode, setViewMode] = useState<'list' | 'kanban'>('kanban')

  // Fetch tasks
  const { data, isLoading, error } = useQuery({
    queryKey: ['tasks', { page, search, project: selectedProject, state: selectedState, assignee: selectedAssignee }],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '50',
        ...(search && { search }),
        ...(selectedProject && { project_id: selectedProject }),
        ...(selectedState && { state: selectedState }),
        ...(selectedAssignee && { assignee_id: selectedAssignee }),
      })
      const response = await api.get(`/projects/tasks?${params}`)
      return response.data as PaginatedResponse<Task>
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

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/projects/tasks/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
    },
  })

  // Update state mutation
  const updateStateMutation = useMutation({
    mutationFn: async ({ id, state }: { id: string; state: Task['state'] }) => {
      await api.post(`/projects/tasks/${id}/state`, { state })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
    },
  })

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this task?')) {
      await deleteMutation.mutateAsync(id)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    })
  }

  // Group tasks by state for Kanban view
  const tasksByState = data?.items.reduce((acc, task) => {
    if (!acc[task.state]) {
      acc[task.state] = []
    }
    acc[task.state].push(task)
    return acc
  }, {} as Record<string, Task[]>)

  const kanbanColumns = ['backlog', 'todo', 'in_progress', 'review', 'done']

  // Calculate summary
  const summary = data?.items.reduce((acc, task) => {
    acc.total++
    if (task.state === 'done') acc.completed++
    if (task.state === 'in_progress') acc.inProgress++
    acc.totalHours += task.estimated_hours
    acc.actualHours += task.actual_hours
    return acc
  }, { total: 0, completed: 0, inProgress: 0, totalHours: 0, actualHours: 0 })

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Tasks</h1>
          <p className="text-slate-500 mt-1">Manage and track your tasks</p>
        </div>
        <Link
          to="/projects/tasks/new"
          className="btn btn-primary"
        >
          <Plus className="w-4 h-4" />
          New Task
        </Link>
      </div>

      {/* Summary Cards */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="card p-4">
            <p className="text-sm text-slate-500">Total Tasks</p>
            <p className="text-2xl font-bold text-slate-900">{summary?.total || 0}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-slate-500">In Progress</p>
            <p className="text-2xl font-bold text-yellow-600">{summary?.inProgress || 0}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-slate-500">Completed</p>
            <p className="text-2xl font-bold text-green-600">{summary?.completed || 0}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-slate-500">Est. Hours</p>
            <p className="text-2xl font-bold text-slate-900">{summary?.totalHours?.toFixed(1) || 0}h</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-slate-500">Actual Hours</p>
            <p className="text-2xl font-bold text-purple-600">{summary?.actualHours?.toFixed(1) || 0}h</p>
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
              placeholder="Search tasks..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
            />
          </div>
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
          <div className="flex bg-slate-100 rounded-lg p-1">
            <button
              onClick={() => setViewMode('kanban')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                viewMode === 'kanban' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'
              }`}
            >
              Kanban
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

      {/* Tasks View */}
      {isLoading ? (
        <div className="card p-12 text-center">
          <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto" />
          <p className="text-slate-500 mt-4">Loading tasks...</p>
        </div>
      ) : error ? (
        <div className="card p-12 text-center">
          <p className="text-red-600">Failed to load tasks</p>
        </div>
      ) : data?.items.length === 0 ? (
        <div className="card p-12 text-center">
          <CheckSquare className="w-12 h-12 text-slate-300 mx-auto" />
          <h3 className="text-lg font-medium text-slate-900 mt-4">No tasks found</h3>
          <p className="text-slate-500 mt-2">Create your first task to get started.</p>
          <Link to="/projects/tasks/new" className="btn btn-primary mt-4">
            <Plus className="w-4 h-4" />
            New Task
          </Link>
        </div>
      ) : viewMode === 'kanban' ? (
        <div className="flex gap-4 overflow-x-auto pb-4">
          {kanbanColumns.map((state) => (
            <div key={state} className="flex-shrink-0 w-72">
              <div className="bg-slate-50 rounded-lg p-3">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium text-slate-700">{stateLabels[state]}</h3>
                  <span className="text-sm text-slate-500 bg-white px-2 py-0.5 rounded-full">
                    {tasksByState?.[state]?.length || 0}
                  </span>
                </div>
                <div className="space-y-2 max-h-[calc(100vh-400px)] overflow-y-auto">
                  {tasksByState?.[state]?.map((task) => (
                    <div
                      key={task.id}
                      className={`bg-white rounded-lg border-l-4 ${priorityColors[task.priority]} p-3 shadow-sm hover:shadow-md transition-shadow cursor-pointer`}
                      onClick={() => window.location.href = `/projects/tasks/${task.id}`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <span className={`badge text-xs ${typeColors[task.task_type]}`}>
                          {task.task_type}
                        </span>
                        <Flag className={`w-4 h-4 ${
                          task.priority === 'urgent' ? 'text-red-500' :
                          task.priority === 'high' ? 'text-orange-500' :
                          task.priority === 'medium' ? 'text-blue-500' : 'text-slate-300'
                        }`} />
                      </div>
                      <h4 className="font-medium text-slate-900 text-sm mb-1">{task.name}</h4>
                      <p className="text-xs text-slate-500 mb-2">{task.project_name}</p>
                      {task.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mb-2">
                          {task.tags.slice(0, 2).map((tag, i) => (
                            <span key={i} className="text-xs bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                      <div className="flex items-center justify-between text-xs text-slate-500">
                        <div className="flex items-center gap-1">
                          {task.assignee_name ? (
                            <div className="flex items-center gap-1">
                              <div className="w-5 h-5 bg-primary-100 rounded-full flex items-center justify-center text-xs font-medium text-primary-600">
                                {task.assignee_name.charAt(0)}
                              </div>
                            </div>
                          ) : (
                            <User className="w-4 h-4 text-slate-300" />
                          )}
                        </div>
                        {task.due_date && (
                          <div className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {formatDate(task.due_date)}
                          </div>
                        )}
                      </div>
                      {task.estimated_hours > 0 && (
                        <div className="mt-2 text-xs text-slate-500">
                          <Clock className="w-3 h-3 inline mr-1" />
                          {task.actual_hours}/{task.estimated_hours}h
                        </div>
                      )}
                    </div>
                  ))}
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
                <th>Task</th>
                <th>Project</th>
                <th>Assignee</th>
                <th>Priority</th>
                <th>Hours</th>
                <th>Due Date</th>
                <th>Status</th>
                <th className="w-20"></th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((task) => (
                <tr key={task.id} className="hover:bg-slate-50">
                  <td>
                    <Link
                      to={`/projects/tasks/${task.id}`}
                      className="flex items-center gap-3 hover:text-primary-600"
                    >
                      <CheckSquare className="w-4 h-4 text-slate-400" />
                      <div>
                        <p className="font-medium text-slate-900">{task.name}</p>
                        <div className="flex items-center gap-2">
                          <span className={`text-xs ${typeColors[task.task_type]}`}>
                            {task.task_type}
                          </span>
                          {task.tags.slice(0, 2).map((tag, i) => (
                            <span key={i} className="text-xs bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>
                    </Link>
                  </td>
                  <td>
                    <span className="text-slate-600">{task.project_name}</span>
                  </td>
                  <td>
                    {task.assignee_name ? (
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 bg-primary-100 rounded-full flex items-center justify-center text-xs font-medium text-primary-600">
                          {task.assignee_name.charAt(0)}
                        </div>
                        <span className="text-slate-600">{task.assignee_name}</span>
                      </div>
                    ) : (
                      <span className="text-slate-400">Unassigned</span>
                    )}
                  </td>
                  <td>
                    <Flag className={`w-4 h-4 inline ${
                      task.priority === 'urgent' ? 'text-red-500' :
                      task.priority === 'high' ? 'text-orange-500' :
                      task.priority === 'medium' ? 'text-blue-500' : 'text-slate-300'
                    }`} />
                    <span className="ml-1 text-sm capitalize">{task.priority}</span>
                  </td>
                  <td>
                    <span className="text-slate-600">
                      {task.actual_hours}/{task.estimated_hours}h
                    </span>
                  </td>
                  <td>
                    {task.due_date ? (
                      <span className="text-slate-600">{formatDate(task.due_date)}</span>
                    ) : (
                      <span className="text-slate-400">-</span>
                    )}
                  </td>
                  <td>
                    <span className={`badge ${stateColors[task.state]}`}>
                      {stateLabels[task.state]}
                    </span>
                  </td>
                  <td>
                    <div className="relative group">
                      <button className="p-2 hover:bg-slate-100 rounded-lg">
                        <MoreVertical className="w-4 h-4 text-slate-400" />
                      </button>
                      <div className="absolute right-0 top-full mt-1 w-40 bg-white rounded-lg shadow-lg border border-slate-200 py-1 hidden group-hover:block z-10">
                        <Link
                          to={`/projects/tasks/${task.id}`}
                          className="dropdown-item"
                        >
                          <Eye className="w-4 h-4" />
                          View
                        </Link>
                        <Link
                          to={`/projects/tasks/${task.id}/edit`}
                          className="dropdown-item"
                        >
                          <Edit className="w-4 h-4" />
                          Edit
                        </Link>
                        <button
                          onClick={() => handleDelete(task.id)}
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
    </div>
  )
}
