/**
 * Nexus ERP - Projects API Service
 * API functions for project management module
 */

import api, { PaginatedResponse } from './api'

// Types
export interface Project {
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
  team_members: ProjectMember[]
  tasks_count: number
  tasks_completed: number
  created_at: string
  updated_at: string
}

export interface ProjectMember {
  id: string
  employee_id: string
  employee_name: string
  role: string
  allocation: number
  hourly_rate?: number
}

export interface Task {
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
  updated_at: string
}

export interface TaskComment {
  id: string
  task_id: string
  content: string
  author_id: string
  author_name: string
  created_at: string
}

export interface Timesheet {
  id: string
  employee_id: string
  employee_name: string
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
  created_at: string
}

export interface Milestone {
  id: string
  project_id: string
  name: string
  description?: string
  due_date: string
  completed_date?: string
  state: 'pending' | 'completed' | 'overdue'
  progress: number
}

// API Functions
export const projectsApi = {
  // Projects
  listProjects: async (params?: {
    page?: number
    page_size?: number
    search?: string
    state?: string
    customer_id?: string
    manager_id?: string
  }) => {
    const response = await api.get('/projects', { params })
    return response.data as PaginatedResponse<Project>
  },

  getProject: async (id: string) => {
    const response = await api.get(`/projects/${id}`)
    return response.data as Project
  },

  createProject: async (data: Partial<Project>) => {
    const response = await api.post('/projects', data)
    return response.data as Project
  },

  updateProject: async (id: string, data: Partial<Project>) => {
    const response = await api.put(`/projects/${id}`, data)
    return response.data as Project
  },

  deleteProject: async (id: string) => {
    await api.delete(`/projects/${id}`)
  },

  startProject: async (id: string) => {
    const response = await api.post(`/projects/${id}/start`)
    return response.data
  },

  completeProject: async (id: string) => {
    const response = await api.post(`/projects/${id}/complete`)
    return response.data
  },

  holdProject: async (id: string, reason?: string) => {
    const response = await api.post(`/projects/${id}/hold`, { reason })
    return response.data
  },

  cancelProject: async (id: string, reason?: string) => {
    const response = await api.post(`/projects/${id}/cancel`, { reason })
    return response.data
  },

  getProjectDashboard: async (id: string) => {
    const response = await api.get(`/projects/${id}/dashboard`)
    return response.data
  },

  getProjectMembers: async (projectId: string) => {
    const response = await api.get(`/projects/${projectId}/members`)
    return response.data as ProjectMember[]
  },

  addProjectMember: async (projectId: string, data: Partial<ProjectMember>) => {
    const response = await api.post(`/projects/${projectId}/members`, data)
    return response.data as ProjectMember
  },

  removeProjectMember: async (projectId: string, memberId: string) => {
    await api.delete(`/projects/${projectId}/members/${memberId}`)
  },

  // Tasks
  listTasks: async (params?: {
    page?: number
    page_size?: number
    search?: string
    project_id?: string
    assignee_id?: string
    state?: string
    priority?: string
  }) => {
    const response = await api.get('/projects/tasks', { params })
    return response.data as PaginatedResponse<Task>
  },

  getTask: async (id: string) => {
    const response = await api.get(`/projects/tasks/${id}`)
    return response.data as Task
  },

  createTask: async (data: Partial<Task>) => {
    const response = await api.post('/projects/tasks', data)
    return response.data as Task
  },

  updateTask: async (id: string, data: Partial<Task>) => {
    const response = await api.put(`/projects/tasks/${id}`, data)
    return response.data as Task
  },

  deleteTask: async (id: string) => {
    await api.delete(`/projects/tasks/${id}`)
  },

  updateTaskState: async (id: string, state: Task['state']) => {
    const response = await api.post(`/projects/tasks/${id}/state`, { state })
    return response.data
  },

  assignTask: async (id: string, assigneeId: string) => {
    const response = await api.post(`/projects/tasks/${id}/assign`, { assignee_id: assigneeId })
    return response.data
  },

  logTimeOnTask: async (id: string, data: { hours: number; description?: string; date?: string }) => {
    const response = await api.post(`/projects/tasks/${id}/log-time`, data)
    return response.data
  },

  getTaskComments: async (taskId: string) => {
    const response = await api.get(`/projects/tasks/${taskId}/comments`)
    return response.data as TaskComment[]
  },

  addTaskComment: async (taskId: string, content: string) => {
    const response = await api.post(`/projects/tasks/${taskId}/comments`, { content })
    return response.data as TaskComment
  },

  deleteTaskComment: async (taskId: string, commentId: string) => {
    await api.delete(`/projects/tasks/${taskId}/comments/${commentId}`)
  },

  // Timesheets
  listTimesheets: async (params?: {
    page?: number
    page_size?: number
    employee_id?: string
    project_id?: string
    state?: string
    date_from?: string
    date_to?: string
  }) => {
    const response = await api.get('/projects/timesheets', { params })
    return response.data as PaginatedResponse<Timesheet>
  },

  getTimesheet: async (id: string) => {
    const response = await api.get(`/projects/timesheets/${id}`)
    return response.data as Timesheet
  },

  createTimesheet: async (data: Partial<Timesheet>) => {
    const response = await api.post('/projects/timesheets', data)
    return response.data as Timesheet
  },

  updateTimesheet: async (id: string, data: Partial<Timesheet>) => {
    const response = await api.put(`/projects/timesheets/${id}`, data)
    return response.data as Timesheet
  },

  deleteTimesheet: async (id: string) => {
    await api.delete(`/projects/timesheets/${id}`)
  },

  submitTimesheet: async (id: string) => {
    const response = await api.post(`/projects/timesheets/${id}/submit`)
    return response.data
  },

  approveTimesheet: async (id: string) => {
    const response = await api.post(`/projects/timesheets/${id}/approve`)
    return response.data
  },

  rejectTimesheet: async (id: string, reason: string) => {
    const response = await api.post(`/projects/timesheets/${id}/reject`, { reason })
    return response.data
  },

  getMyTimesheets: async (params?: {
    page?: number
    page_size?: number
    date_from?: string
    date_to?: string
    state?: string
  }) => {
    const response = await api.get('/projects/timesheets/my', { params })
    return response.data as PaginatedResponse<Timesheet>
  },

  // Milestones
  listMilestones: async (projectId: string) => {
    const response = await api.get(`/projects/${projectId}/milestones`)
    return response.data as Milestone[]
  },

  createMilestone: async (projectId: string, data: Partial<Milestone>) => {
    const response = await api.post(`/projects/${projectId}/milestones`, data)
    return response.data as Milestone
  },

  updateMilestone: async (projectId: string, milestoneId: string, data: Partial<Milestone>) => {
    const response = await api.put(`/projects/${projectId}/milestones/${milestoneId}`, data)
    return response.data as Milestone
  },

  deleteMilestone: async (projectId: string, milestoneId: string) => {
    await api.delete(`/projects/${projectId}/milestones/${milestoneId}`)
  },

  completeMilestone: async (projectId: string, milestoneId: string) => {
    const response = await api.post(`/projects/${projectId}/milestones/${milestoneId}/complete`)
    return response.data
  },

  // Reports
  getProjectReport: async (id: string) => {
    const response = await api.get(`/projects/${id}/report`)
    return response.data
  },

  getTimeReport: async (params?: {
    project_id?: string
    employee_id?: string
    date_from?: string
    date_to?: string
  }) => {
    const response = await api.get('/projects/reports/time', { params })
    return response.data
  },

  getProfitabilityReport: async (params?: {
    date_from?: string
    date_to?: string
  }) => {
    const response = await api.get('/projects/reports/profitability', { params })
    return response.data
  },
}

export default projectsApi
