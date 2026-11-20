/**
 * Nexus ERP - Opportunities Page
 * Sales opportunities pipeline management
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
  User,
  MoreVertical,
  Eye,
  Edit,
  Trash2,
  CheckCircle,
  XCircle,
} from 'lucide-react'

interface Opportunity {
  id: string
  name: string
  customer_id: string
  customer_name: string
  amount: number
  probability: number
  stage: 'prospecting' | 'qualification' | 'proposal' | 'negotiation' | 'closed_won' | 'closed_lost'
  expected_close_date: string
  assigned_to: string
  lead_source: string
  created_at: string
  notes: string
}

const stageColors: Record<string, string> = {
  prospecting: 'bg-blue-100 text-blue-700',
  qualification: 'bg-cyan-100 text-cyan-700',
  proposal: 'bg-yellow-100 text-yellow-700',
  negotiation: 'bg-orange-100 text-orange-700',
  closed_won: 'bg-green-100 text-green-700',
  closed_lost: 'bg-red-100 text-red-700',
}

const stageLabels: Record<string, string> = {
  prospecting: 'Prospecting',
  qualification: 'Qualification',
  proposal: 'Proposal',
  negotiation: 'Negotiation',
  closed_won: 'Won',
  closed_lost: 'Lost',
}

const stageOrder = ['prospecting', 'qualification', 'proposal', 'negotiation', 'closed_won', 'closed_lost']

export default function OpportunitiesPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selectedStage, setSelectedStage] = useState<string>('')
  const [viewMode, setViewMode] = useState<'list' | 'kanban'>('list')

  // Fetch opportunities
  const { data, isLoading, error } = useQuery({
    queryKey: ['opportunities', { page, search, stage: selectedStage }],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20',
        ...(search && { search }),
        ...(selectedStage && { stage: selectedStage }),
      })
      const response = await api.get(`/crm/opportunities?${params}`)
      return response.data as PaginatedResponse<Opportunity>
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/crm/opportunities/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['opportunities'] })
    },
  })

  // Update stage mutation
  const updateStageMutation = useMutation({
    mutationFn: async ({ id, stage }: { id: string; stage: string }) => {
      await api.patch(`/crm/opportunities/${id}`, { stage })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['opportunities'] })
    },
  })

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this opportunity?')) {
      await deleteMutation.mutateAsync(id)
    }
  }

  const handleWin = async (id: string) => {
    if (confirm('Mark this opportunity as Won?')) {
      await updateStageMutation.mutateAsync({ id, stage: 'closed_won' })
    }
  }

  const handleLose = async (id: string) => {
    if (confirm('Mark this opportunity as Lost?')) {
      await updateStageMutation.mutateAsync({ id, stage: 'closed_lost' })
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

  // Calculate pipeline summary
  const pipelineSummary = data?.items.reduce((acc, opp) => {
    if (!acc[opp.stage]) {
      acc[opp.stage] = { count: 0, value: 0 }
    }
    acc[opp.stage].count++
    acc[opp.stage].value += opp.amount
    return acc
  }, {} as Record<string, { count: number; value: number }>)

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Opportunities</h1>
          <p className="text-slate-500 mt-1">Manage your sales pipeline and deals</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex bg-slate-100 rounded-lg p-1">
            <button
              onClick={() => setViewMode('list')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                viewMode === 'list' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'
              }`}
            >
              List
            </button>
            <button
              onClick={() => setViewMode('kanban')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                viewMode === 'kanban' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'
              }`}
            >
              Kanban
            </button>
          </div>
          <Link
            to="/crm/opportunities/new"
            className="btn btn-primary"
          >
            <Plus className="w-4 h-4" />
            Add Opportunity
          </Link>
        </div>
      </div>

      {/* Pipeline Summary */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {stageOrder.slice(0, 5).map((stage) => (
            <div key={stage} className="card p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className={`badge ${stageColors[stage]}`}>
                  {stageLabels[stage]}
                </span>
              </div>
              <p className="text-2xl font-bold text-slate-900">
                {pipelineSummary?.[stage]?.count || 0}
              </p>
              <p className="text-sm text-slate-500">
                {formatCurrency(pipelineSummary?.[stage]?.value || 0)}
              </p>
            </div>
          ))}
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
              placeholder="Search opportunities..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
            />
          </div>

          {/* Stage filter */}
          <select
            value={selectedStage}
            onChange={(e) => setSelectedStage(e.target.value)}
            className="select w-full md:w-48"
          >
            <option value="">All Stages</option>
            {stageOrder.map((stage) => (
              <option key={stage} value={stage}>{stageLabels[stage]}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Opportunities table/list */}
      <div className="card">
        {isLoading ? (
          <div className="p-12 text-center">
            <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto" />
            <p className="text-slate-500 mt-4">Loading opportunities...</p>
          </div>
        ) : error ? (
          <div className="p-12 text-center">
            <p className="text-red-600">Failed to load opportunities</p>
          </div>
        ) : data?.items.length === 0 ? (
          <div className="p-12 text-center">
            <DollarSign className="w-12 h-12 text-slate-300 mx-auto" />
            <h3 className="text-lg font-medium text-slate-900 mt-4">No opportunities found</h3>
            <p className="text-slate-500 mt-2">Get started by creating a new opportunity.</p>
            <Link to="/crm/opportunities/new" className="btn btn-primary mt-4">
              <Plus className="w-4 h-4" />
              Add Opportunity
            </Link>
          </div>
        ) : viewMode === 'list' ? (
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Opportunity</th>
                  <th>Customer</th>
                  <th>Amount</th>
                  <th>Stage</th>
                  <th>Probability</th>
                  <th>Expected Close</th>
                  <th>Owner</th>
                  <th className="w-20"></th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((opp) => (
                  <tr key={opp.id}>
                    <td>
                      <Link
                        to={`/crm/opportunities/${opp.id}`}
                        className="font-medium text-slate-900 hover:text-primary-600"
                      >
                        {opp.name}
                      </Link>
                    </td>
                    <td>
                      <Link
                        to={`/crm/customers/${opp.customer_id}`}
                        className="text-primary-600 hover:underline"
                      >
                        {opp.customer_name}
                      </Link>
                    </td>
                    <td>
                      <span className="font-medium">{formatCurrency(opp.amount)}</span>
                    </td>
                    <td>
                      <span className={`badge ${stageColors[opp.stage]}`}>
                        {stageLabels[opp.stage]}
                      </span>
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-slate-200 rounded-full h-2">
                          <div
                            className="bg-primary-500 rounded-full h-2"
                            style={{ width: `${opp.probability}%` }}
                          />
                        </div>
                        <span className="text-sm text-slate-600">{opp.probability}%</span>
                      </div>
                    </td>
                    <td>
                      <div className="flex items-center gap-2 text-sm text-slate-500">
                        <Calendar className="w-4 h-4" />
                        {formatDate(opp.expected_close_date)}
                      </div>
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <User className="w-4 h-4 text-slate-400" />
                        <span>{opp.assigned_to || 'Unassigned'}</span>
                      </div>
                    </td>
                    <td>
                      <div className="relative group">
                        <button className="p-2 hover:bg-slate-100 rounded-lg">
                          <MoreVertical className="w-4 h-4 text-slate-400" />
                        </button>
                        <div className="absolute right-0 top-full mt-1 w-48 bg-white rounded-lg shadow-lg border border-slate-200 py-1 hidden group-hover:block z-10">
                          <Link
                            to={`/crm/opportunities/${opp.id}`}
                            className="dropdown-item"
                          >
                            <Eye className="w-4 h-4" />
                            View Details
                          </Link>
                          <Link
                            to={`/crm/opportunities/${opp.id}/edit`}
                            className="dropdown-item"
                          >
                            <Edit className="w-4 h-4" />
                            Edit
                          </Link>
                          {!['closed_won', 'closed_lost'].includes(opp.stage) && (
                            <>
                              <button
                                onClick={() => handleWin(opp.id)}
                                className="w-full text-left dropdown-item text-green-600"
                              >
                                <CheckCircle className="w-4 h-4" />
                                Mark as Won
                              </button>
                              <button
                                onClick={() => handleLose(opp.id)}
                                className="w-full text-left dropdown-item text-red-600"
                              >
                                <XCircle className="w-4 h-4" />
                                Mark as Lost
                              </button>
                            </>
                          )}
                          <button
                            onClick={() => handleDelete(opp.id)}
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
        ) : (
          // Kanban View
          <div className="p-4 overflow-x-auto">
            <div className="flex gap-4 min-w-max">
              {stageOrder.slice(0, 5).map((stage) => (
                <div key={stage} className="w-72 flex-shrink-0">
                  <div className={`px-3 py-2 rounded-t-lg ${stageColors[stage]}`}>
                    <span className="font-medium">{stageLabels[stage]}</span>
                    <span className="ml-2 text-sm opacity-75">
                      ({data?.items.filter(o => o.stage === stage).length || 0})
                    </span>
                  </div>
                  <div className="bg-slate-50 rounded-b-lg p-2 min-h-[200px] space-y-2">
                    {data?.items
                      .filter((o) => o.stage === stage)
                      .map((opp) => (
                        <Link
                          key={opp.id}
                          to={`/crm/opportunities/${opp.id}`}
                          className="block bg-white p-3 rounded-lg shadow-sm hover:shadow-md transition-shadow"
                        >
                          <p className="font-medium text-slate-900 truncate">{opp.name}</p>
                          <p className="text-sm text-primary-600">{opp.customer_name}</p>
                          <div className="flex items-center justify-between mt-2">
                            <span className="font-medium">{formatCurrency(opp.amount)}</span>
                            <span className="text-sm text-slate-500">{opp.probability}%</span>
                          </div>
                        </Link>
                      ))}
                    {data?.items.filter((o) => o.stage === stage).length === 0 && (
                      <div className="text-center py-8 text-slate-400 text-sm">
                        No opportunities
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Pagination - only show for list view */}
        {viewMode === 'list' && data && data.pages > 1 && (
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
