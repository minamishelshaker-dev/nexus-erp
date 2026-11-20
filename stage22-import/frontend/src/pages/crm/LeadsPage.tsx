/**
 * Nexus ERP - Leads Page
 * CRM leads management page
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, PaginatedResponse } from '../../services/api'
import {
  Plus,
  Search,
  Mail,
  Phone,
  Building2,
  User,
  MoreVertical,
  Eye,
  Edit,
  Trash2,
  ArrowRight,
} from 'lucide-react'

interface Lead {
  id: string
  name: string
  company: string
  email: string
  phone: string
  source: string
  status: 'new' | 'contacted' | 'qualified' | 'converted' | 'lost'
  priority: 'low' | 'medium' | 'high'
  estimated_value: number
  assigned_to: string
  created_at: string
  notes: string
}

const statusColors: Record<string, string> = {
  new: 'bg-blue-100 text-blue-700',
  contacted: 'bg-yellow-100 text-yellow-700',
  qualified: 'bg-purple-100 text-purple-700',
  converted: 'bg-green-100 text-green-700',
  lost: 'bg-red-100 text-red-700',
}

const statusLabels: Record<string, string> = {
  new: 'New',
  contacted: 'Contacted',
  qualified: 'Qualified',
  converted: 'Converted',
  lost: 'Lost',
}

const priorityColors: Record<string, string> = {
  low: 'bg-slate-100 text-slate-600',
  medium: 'bg-orange-100 text-orange-700',
  high: 'bg-red-100 text-red-700',
}

export default function LeadsPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selectedStatus, setSelectedStatus] = useState<string>('')
  const [selectedSource, setSelectedSource] = useState<string>('')

  // Fetch leads
  const { data, isLoading, error } = useQuery({
    queryKey: ['leads', { page, search, status: selectedStatus, source: selectedSource }],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20',
        ...(search && { search }),
        ...(selectedStatus && { status: selectedStatus }),
        ...(selectedSource && { source: selectedSource }),
      })
      const response = await api.get(`/crm/leads?${params}`)
      return response.data as PaginatedResponse<Lead>
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/crm/leads/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] })
    },
  })

  // Convert to opportunity mutation
  const convertMutation = useMutation({
    mutationFn: async (id: string) => {
      const response = await api.post(`/crm/leads/${id}/convert`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] })
      queryClient.invalidateQueries({ queryKey: ['opportunities'] })
    },
  })

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this lead?')) {
      await deleteMutation.mutateAsync(id)
    }
  }

  const handleConvert = async (id: string) => {
    if (confirm('Convert this lead to an opportunity?')) {
      await convertMutation.mutateAsync(id)
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount)
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Leads</h1>
          <p className="text-slate-500 mt-1">Manage your sales leads and prospects</p>
        </div>
        <Link
          to="/crm/leads/new"
          className="btn btn-primary"
        >
          <Plus className="w-4 h-4" />
          Add Lead
        </Link>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search leads..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
            />
          </div>

          {/* Status filter */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="select w-full md:w-40"
          >
            <option value="">All Status</option>
            <option value="new">New</option>
            <option value="contacted">Contacted</option>
            <option value="qualified">Qualified</option>
            <option value="converted">Converted</option>
            <option value="lost">Lost</option>
          </select>

          {/* Source filter */}
          <select
            value={selectedSource}
            onChange={(e) => setSelectedSource(e.target.value)}
            className="select w-full md:w-40"
          >
            <option value="">All Sources</option>
            <option value="website">Website</option>
            <option value="referral">Referral</option>
            <option value="trade_show">Trade Show</option>
            <option value="cold_call">Cold Call</option>
            <option value="social_media">Social Media</option>
          </select>
        </div>
      </div>

      {/* Leads table */}
      <div className="card">
        {isLoading ? (
          <div className="p-12 text-center">
            <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto" />
            <p className="text-slate-500 mt-4">Loading leads...</p>
          </div>
        ) : error ? (
          <div className="p-12 text-center">
            <p className="text-red-600">Failed to load leads</p>
          </div>
        ) : data?.items.length === 0 ? (
          <div className="p-12 text-center">
            <User className="w-12 h-12 text-slate-300 mx-auto" />
            <h3 className="text-lg font-medium text-slate-900 mt-4">No leads found</h3>
            <p className="text-slate-500 mt-2">Get started by creating a new lead.</p>
            <Link to="/crm/leads/new" className="btn btn-primary mt-4">
              <Plus className="w-4 h-4" />
              Add Lead
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Lead</th>
                  <th>Company</th>
                  <th>Contact</th>
                  <th>Source</th>
                  <th>Status</th>
                  <th>Priority</th>
                  <th>Est. Value</th>
                  <th className="w-20"></th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((lead) => (
                  <tr key={lead.id}>
                    <td>
                      <Link
                        to={`/crm/leads/${lead.id}`}
                        className="flex items-center gap-3 hover:text-primary-600"
                      >
                        <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
                          <span className="font-medium text-primary-600">
                            {lead.name.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <p className="font-medium text-slate-900">{lead.name}</p>
                          <p className="text-sm text-slate-500">{lead.assigned_to || 'Unassigned'}</p>
                        </div>
                      </Link>
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <Building2 className="w-4 h-4 text-slate-400" />
                        <span>{lead.company || '-'}</span>
                      </div>
                    </td>
                    <td>
                      <div className="space-y-1">
                        {lead.email && (
                          <div className="flex items-center gap-2 text-sm">
                            <Mail className="w-3 h-3 text-slate-400" />
                            <span>{lead.email}</span>
                          </div>
                        )}
                        {lead.phone && (
                          <div className="flex items-center gap-2 text-sm text-slate-500">
                            <Phone className="w-3 h-3" />
                            <span>{lead.phone}</span>
                          </div>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className="capitalize text-slate-600">{lead.source || '-'}</span>
                    </td>
                    <td>
                      <span className={`badge ${statusColors[lead.status]}`}>
                        {statusLabels[lead.status]}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${priorityColors[lead.priority]}`}>
                        {lead.priority}
                      </span>
                    </td>
                    <td>
                      <span className="font-medium">
                        {formatCurrency(lead.estimated_value || 0)}
                      </span>
                    </td>
                    <td>
                      <div className="relative group">
                        <button className="p-2 hover:bg-slate-100 rounded-lg">
                          <MoreVertical className="w-4 h-4 text-slate-400" />
                        </button>
                        <div className="absolute right-0 top-full mt-1 w-48 bg-white rounded-lg shadow-lg border border-slate-200 py-1 hidden group-hover:block z-10">
                          <Link
                            to={`/crm/leads/${lead.id}`}
                            className="dropdown-item"
                          >
                            <Eye className="w-4 h-4" />
                            View Details
                          </Link>
                          <Link
                            to={`/crm/leads/${lead.id}/edit`}
                            className="dropdown-item"
                          >
                            <Edit className="w-4 h-4" />
                            Edit
                          </Link>
                          {(lead.status === 'qualified' || lead.status === 'contacted') && (
                            <button
                              onClick={() => handleConvert(lead.id)}
                              className="w-full text-left dropdown-item text-primary-600"
                            >
                              <ArrowRight className="w-4 h-4" />
                              Convert to Opportunity
                            </button>
                          )}
                          <button
                            onClick={() => handleDelete(lead.id)}
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
