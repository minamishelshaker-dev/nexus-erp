/**
 * Nexus ERP - Warehouses Page
 * Warehouse management
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, PaginatedResponse } from '../../services/api'
import {
  Plus,
  Search,
  Warehouse,
  MapPin,
  MoreVertical,
  Eye,
  Edit,
  Trash2,
  Package,
  Building2,
} from 'lucide-react'

interface WarehouseData {
  id: string
  code: string
  name: string
  address: string
  city: string
  country: string
  phone: string
  email: string
  manager: string
  is_active: boolean
  total_products: number
  total_quantity: number
  total_value: number
  created_at: string
}

export default function WarehousesPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)

  // Fetch warehouses
  const { data, isLoading, error } = useQuery({
    queryKey: ['warehouses', { page, search }],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20',
        ...(search && { search }),
      })
      const response = await api.get(`/inventory/warehouses?${params}`)
      return response.data as PaginatedResponse<WarehouseData>
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/inventory/warehouses/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['warehouses'] })
    },
  })

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this warehouse? This will also delete all stock records in this warehouse.')) {
      await deleteMutation.mutateAsync(id)
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
          <h1 className="text-2xl font-bold text-slate-900">Warehouses</h1>
          <p className="text-slate-500 mt-1">Manage your storage locations</p>
        </div>
        <Link
          to="/inventory/warehouses/new"
          className="btn btn-primary"
        >
          <Plus className="w-4 h-4" />
          Add Warehouse
        </Link>
      </div>

      {/* Summary Cards */}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <Building2 className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Total Warehouses</p>
                <p className="text-xl font-bold text-slate-900">{data.total}</p>
              </div>
            </div>
          </div>
          <div className="card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                <Package className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Total Products</p>
                <p className="text-xl font-bold text-slate-900">
                  {data.items.reduce((sum, w) => sum + w.total_products, 0)}
                </p>
              </div>
            </div>
          </div>
          <div className="card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                <Warehouse className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Total Stock Value</p>
                <p className="text-xl font-bold text-slate-900">
                  {formatCurrency(data.items.reduce((sum, w) => sum + w.total_value, 0))}
                </p>
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
              placeholder="Search warehouses..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
            />
          </div>
        </div>
      </div>

      {/* Warehouses grid */}
      {isLoading ? (
        <div className="card p-12 text-center">
          <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto" />
          <p className="text-slate-500 mt-4">Loading warehouses...</p>
        </div>
      ) : error ? (
        <div className="card p-12 text-center">
          <p className="text-red-600">Failed to load warehouses</p>
        </div>
      ) : data?.items.length === 0 ? (
        <div className="card p-12 text-center">
          <Warehouse className="w-12 h-12 text-slate-300 mx-auto" />
          <h3 className="text-lg font-medium text-slate-900 mt-4">No warehouses found</h3>
          <p className="text-slate-500 mt-2">Get started by creating a new warehouse.</p>
          <Link to="/inventory/warehouses/new" className="btn btn-primary mt-4">
            <Plus className="w-4 h-4" />
            Add Warehouse
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {data?.items.map((warehouse) => (
            <div key={warehouse.id} className="card overflow-hidden">
              <div className="p-4 border-b border-slate-100">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center">
                      <Warehouse className="w-6 h-6 text-primary-600" />
                    </div>
                    <div>
                      <Link
                        to={`/inventory/warehouses/${warehouse.id}`}
                        className="font-semibold text-slate-900 hover:text-primary-600"
                      >
                        {warehouse.name}
                      </Link>
                      <p className="text-sm text-slate-500">{warehouse.code}</p>
                    </div>
                  </div>
                  <div className="relative group">
                    <button className="p-2 hover:bg-slate-100 rounded-lg">
                      <MoreVertical className="w-4 h-4 text-slate-400" />
                    </button>
                    <div className="absolute right-0 top-full mt-1 w-40 bg-white rounded-lg shadow-lg border border-slate-200 py-1 hidden group-hover:block z-10">
                      <Link
                        to={`/inventory/warehouses/${warehouse.id}`}
                        className="dropdown-item"
                      >
                        <Eye className="w-4 h-4" />
                        View Details
                      </Link>
                      <Link
                        to={`/inventory/warehouses/${warehouse.id}/edit`}
                        className="dropdown-item"
                      >
                        <Edit className="w-4 h-4" />
                        Edit
                      </Link>
                      <button
                        onClick={() => handleDelete(warehouse.id)}
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
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  <MapPin className="w-4 h-4 text-slate-400" />
                  <span>{[warehouse.address, warehouse.city, warehouse.country].filter(Boolean).join(', ') || 'No address'}</span>
                </div>
                {warehouse.manager && (
                  <div className="flex items-center gap-2 text-sm text-slate-600">
                    <Package className="w-4 h-4 text-slate-400" />
                    <span>Manager: {warehouse.manager}</span>
                  </div>
                )}
              </div>
              <div className="px-4 py-3 bg-slate-50 flex items-center justify-between text-sm">
                <div>
                  <span className="text-slate-500">Products: </span>
                  <span className="font-medium">{warehouse.total_products}</span>
                </div>
                <div>
                  <span className="text-slate-500">Value: </span>
                  <span className="font-medium">{formatCurrency(warehouse.total_value)}</span>
                </div>
                <span className={`badge ${warehouse.is_active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'}`}>
                  {warehouse.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
          ))}
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
