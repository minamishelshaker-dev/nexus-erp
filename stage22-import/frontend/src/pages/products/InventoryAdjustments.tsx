/**
 * Nexus ERP - Inventory Adjustments Page
 * Stock adjustments and inventory counts
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, PaginatedResponse } from '../../services/api'
import {
  Plus,
  Search,
  ClipboardList,
  MoreVertical,
  Eye,
  Edit,
  Trash2,
  CheckCircle,
  XCircle,
  Calendar,
  User,
} from 'lucide-react'

interface InventoryAdjustment {
  id: string
  number: string
  date: string
  warehouse_id: string
  warehouse_name: string
  type: 'count' | 'adjustment' | 'loss' | 'damage' | 'theft' | 'other'
  state: 'draft' | 'confirmed' | 'cancelled'
  total_lines: number
  total_value: number
  reason: string
  notes: string
  created_by: string
  created_at: string
  confirmed_by?: string
  confirmed_at?: string
}

const typeColors: Record<string, string> = {
  count: 'bg-blue-100 text-blue-700',
  adjustment: 'bg-purple-100 text-purple-700',
  loss: 'bg-red-100 text-red-700',
  damage: 'bg-orange-100 text-orange-700',
  theft: 'bg-red-100 text-red-700',
  other: 'bg-slate-100 text-slate-700',
}

const typeLabels: Record<string, string> = {
  count: 'Inventory Count',
  adjustment: 'Adjustment',
  loss: 'Loss',
  damage: 'Damage',
  theft: 'Theft',
  other: 'Other',
}

const stateColors: Record<string, string> = {
  draft: 'bg-yellow-100 text-yellow-700',
  confirmed: 'bg-green-100 text-green-700',
  cancelled: 'bg-slate-100 text-slate-500',
}

const stateLabels: Record<string, string> = {
  draft: 'Draft',
  confirmed: 'Confirmed',
  cancelled: 'Cancelled',
}

export default function InventoryAdjustmentsPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selectedType, setSelectedType] = useState<string>('')
  const [selectedState, setSelectedState] = useState<string>('')

  // Fetch adjustments
  const { data, isLoading, error } = useQuery({
    queryKey: ['inventory-adjustments', { page, search, type: selectedType, state: selectedState }],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20',
        ...(search && { search }),
        ...(selectedType && { type: selectedType }),
        ...(selectedState && { state: selectedState }),
      })
      const response = await api.get(`/inventory/adjustments?${params}`)
      return response.data as PaginatedResponse<InventoryAdjustment>
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/inventory/adjustments/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory-adjustments'] })
    },
  })

  // Confirm mutation
  const confirmMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/inventory/adjustments/${id}/confirm`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory-adjustments'] })
      queryClient.invalidateQueries({ queryKey: ['stock-levels'] })
    },
  })

  // Cancel mutation
  const cancelMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/inventory/adjustments/${id}/cancel`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory-adjustments'] })
    },
  })

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this adjustment?')) {
      await deleteMutation.mutateAsync(id)
    }
  }

  const handleConfirm = async (id: string) => {
    if (confirm('Confirm this adjustment? This will update stock levels.')) {
      await confirmMutation.mutateAsync(id)
    }
  }

  const handleCancel = async (id: string) => {
    if (confirm('Cancel this adjustment?')) {
      await cancelMutation.mutateAsync(id)
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

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Inventory Adjustments</h1>
          <p className="text-slate-500 mt-1">Manage stock counts and adjustments</p>
        </div>
        <Link
          to="/inventory/adjustments/new"
          className="btn btn-primary"
        >
          <Plus className="w-4 h-4" />
          New Adjustment
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
              placeholder="Search adjustments..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
            />
          </div>

          {/* Type filter */}
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="select w-full md:w-40"
          >
            <option value="">All Types</option>
            <option value="count">Inventory Count</option>
            <option value="adjustment">Adjustment</option>
            <option value="loss">Loss</option>
            <option value="damage">Damage</option>
            <option value="theft">Theft</option>
            <option value="other">Other</option>
          </select>

          {/* State filter */}
          <select
            value={selectedState}
            onChange={(e) => setSelectedState(e.target.value)}
            className="select w-full md:w-40"
          >
            <option value="">All States</option>
            <option value="draft">Draft</option>
            <option value="confirmed">Confirmed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </div>

      {/* Adjustments table */}
      <div className="card">
        {isLoading ? (
          <div className="p-12 text-center">
            <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto" />
            <p className="text-slate-500 mt-4">Loading adjustments...</p>
          </div>
        ) : error ? (
          <div className="p-12 text-center">
            <p className="text-red-600">Failed to load adjustments</p>
          </div>
        ) : data?.items.length === 0 ? (
          <div className="p-12 text-center">
            <ClipboardList className="w-12 h-12 text-slate-300 mx-auto" />
            <h3 className="text-lg font-medium text-slate-900 mt-4">No adjustments found</h3>
            <p className="text-slate-500 mt-2">Get started by creating a new adjustment.</p>
            <Link to="/inventory/adjustments/new" className="btn btn-primary mt-4">
              <Plus className="w-4 h-4" />
              New Adjustment
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Number</th>
                  <th>Date</th>
                  <th>Warehouse</th>
                  <th>Type</th>
                  <th>Lines</th>
                  <th>Value Impact</th>
                  <th>Reason</th>
                  <th>Status</th>
                  <th className="w-20"></th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((adjustment) => (
                  <tr key={adjustment.id}>
                    <td>
                      <Link
                        to={`/inventory/adjustments/${adjustment.id}`}
                        className="font-medium text-primary-600 hover:underline"
                      >
                        {adjustment.number}
                      </Link>
                    </td>
                    <td>
                      <div className="flex items-center gap-2 text-slate-500">
                        <Calendar className="w-4 h-4" />
                        {formatDate(adjustment.date)}
                      </div>
                    </td>
                    <td>{adjustment.warehouse_name}</td>
                    <td>
                      <span className={`badge ${typeColors[adjustment.type]}`}>
                        {typeLabels[adjustment.type]}
                      </span>
                    </td>
                    <td>{adjustment.total_lines}</td>
                    <td>
                      <span className={adjustment.total_value < 0 ? 'text-red-600 font-medium' : adjustment.total_value > 0 ? 'text-green-600 font-medium' : ''}>
                        {formatCurrency(adjustment.total_value)}
                      </span>
                    </td>
                    <td>
                      <span className="text-slate-600 truncate max-w-[150px] block">{adjustment.reason || '-'}</span>
                    </td>
                    <td>
                      <span className={`badge ${stateColors[adjustment.state]}`}>
                        {stateLabels[adjustment.state]}
                      </span>
                    </td>
                    <td>
                      <div className="relative group">
                        <button className="p-2 hover:bg-slate-100 rounded-lg">
                          <MoreVertical className="w-4 h-4 text-slate-400" />
                        </button>
                        <div className="absolute right-0 top-full mt-1 w-48 bg-white rounded-lg shadow-lg border border-slate-200 py-1 hidden group-hover:block z-10">
                          <Link
                            to={`/inventory/adjustments/${adjustment.id}`}
                            className="dropdown-item"
                          >
                            <Eye className="w-4 h-4" />
                            View Details
                          </Link>
                          {adjustment.state === 'draft' && (
                            <>
                              <Link
                                to={`/inventory/adjustments/${adjustment.id}/edit`}
                                className="dropdown-item"
                              >
                                <Edit className="w-4 h-4" />
                                Edit
                              </Link>
                              <button
                                onClick={() => handleConfirm(adjustment.id)}
                                className="w-full text-left dropdown-item text-green-600"
                              >
                                <CheckCircle className="w-4 h-4" />
                                Confirm
                              </button>
                              <button
                                onClick={() => handleCancel(adjustment.id)}
                                className="w-full text-left dropdown-item text-orange-600"
                              >
                                <XCircle className="w-4 h-4" />
                                Cancel
                              </button>
                              <button
                                onClick={() => handleDelete(adjustment.id)}
                                className="w-full text-left dropdown-item text-red-600"
                              >
                                <Trash2 className="w-4 h-4" />
                                Delete
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
