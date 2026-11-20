/**
 * Nexus ERP - Suppliers Page
 * Supplier management
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, PaginatedResponse } from '../../services/api'
import {
  Plus,
  Search,
  Building2,
  Mail,
  Phone,
  Globe,
  MoreVertical,
  Eye,
  Edit,
  Trash2,
  DollarSign,
  Package,
} from 'lucide-react'

interface Supplier {
  id: string
  code: string
  name: string
  contact_person: string
  email: string
  phone: string
  website: string
  address: string
  city: string
  country: string
  tax_id: string
  payment_terms: string
  currency: string
  is_active: boolean
  rating: number
  total_orders: number
  total_purchases: number
  outstanding_balance: number
  created_at: string
}

export default function SuppliersPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selectedStatus, setSelectedStatus] = useState<string>('')

  // Fetch suppliers
  const { data, isLoading, error } = useQuery({
    queryKey: ['suppliers', { page, search, status: selectedStatus }],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20',
        ...(search && { search }),
        ...(selectedStatus && { is_active: selectedStatus }),
      })
      const response = await api.get(`/purchasing/suppliers?${params}`)
      return response.data as PaginatedResponse<Supplier>
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/purchasing/suppliers/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['suppliers'] })
    },
  })

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this supplier?')) {
      await deleteMutation.mutateAsync(id)
    }
  }

  const formatCurrency = (amount: number, currency = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount)
  }

  // Render star rating
  const renderRating = (rating: number) => {
    return (
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <span
            key={star}
            className={`text-sm ${star <= rating ? 'text-yellow-400' : 'text-slate-200'}`}
          >
            ★
          </span>
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Suppliers</h1>
          <p className="text-slate-500 mt-1">Manage your vendor relationships</p>
        </div>
        <Link
          to="/purchasing/suppliers/new"
          className="btn btn-primary"
        >
          <Plus className="w-4 h-4" />
          Add Supplier
        </Link>
      </div>

      {/* Summary Cards */}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <Building2 className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Total Suppliers</p>
                <p className="text-xl font-bold text-slate-900">{data.total}</p>
              </div>
            </div>
          </div>
          <div className="card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                <Package className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Active Suppliers</p>
                <p className="text-xl font-bold text-slate-900">
                  {data.items.filter(s => s.is_active).length}
                </p>
              </div>
            </div>
          </div>
          <div className="card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                <DollarSign className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Total Purchases</p>
                <p className="text-xl font-bold text-slate-900">
                  {formatCurrency(data.items.reduce((sum, s) => sum + s.total_purchases, 0))}
                </p>
              </div>
            </div>
          </div>
          <div className="card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center">
                <DollarSign className="w-5 h-5 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Outstanding Balance</p>
                <p className="text-xl font-bold text-yellow-600">
                  {formatCurrency(data.items.reduce((sum, s) => sum + s.outstanding_balance, 0))}
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
              placeholder="Search suppliers..."
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
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </select>
        </div>
      </div>

      {/* Suppliers table */}
      <div className="card">
        {isLoading ? (
          <div className="p-12 text-center">
            <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto" />
            <p className="text-slate-500 mt-4">Loading suppliers...</p>
          </div>
        ) : error ? (
          <div className="p-12 text-center">
            <p className="text-red-600">Failed to load suppliers</p>
          </div>
        ) : data?.items.length === 0 ? (
          <div className="p-12 text-center">
            <Building2 className="w-12 h-12 text-slate-300 mx-auto" />
            <h3 className="text-lg font-medium text-slate-900 mt-4">No suppliers found</h3>
            <p className="text-slate-500 mt-2">Get started by creating a new supplier.</p>
            <Link to="/purchasing/suppliers/new" className="btn btn-primary mt-4">
              <Plus className="w-4 h-4" />
              Add Supplier
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Supplier</th>
                  <th>Contact</th>
                  <th>Location</th>
                  <th>Rating</th>
                  <th>Total Orders</th>
                  <th>Total Purchases</th>
                  <th>Outstanding</th>
                  <th>Status</th>
                  <th className="w-20"></th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((supplier) => (
                  <tr key={supplier.id} className={!supplier.is_active ? 'bg-slate-50 opacity-60' : ''}>
                    <td>
                      <Link
                        to={`/purchasing/suppliers/${supplier.id}`}
                        className="flex items-center gap-3 hover:text-primary-600"
                      >
                        <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
                          <Building2 className="w-5 h-5 text-primary-600" />
                        </div>
                        <div>
                          <p className="font-medium text-slate-900">{supplier.name}</p>
                          <p className="text-sm text-slate-500">{supplier.code}</p>
                        </div>
                      </Link>
                    </td>
                    <td>
                      <div className="space-y-1">
                        <p className="font-medium text-slate-900">{supplier.contact_person}</p>
                        <div className="flex items-center gap-2 text-sm text-slate-500">
                          <Mail className="w-3 h-3" />
                          <span>{supplier.email}</span>
                        </div>
                        <div className="flex items-center gap-2 text-sm text-slate-500">
                          <Phone className="w-3 h-3" />
                          <span>{supplier.phone}</span>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="text-slate-600">
                        {[supplier.city, supplier.country].filter(Boolean).join(', ') || '-'}
                      </span>
                    </td>
                    <td>
                      {renderRating(supplier.rating)}
                    </td>
                    <td>
                      <span className="font-medium">{supplier.total_orders}</span>
                    </td>
                    <td>
                      <span className="font-medium">{formatCurrency(supplier.total_purchases, supplier.currency)}</span>
                    </td>
                    <td>
                      <span className={supplier.outstanding_balance > 0 ? 'text-yellow-600 font-medium' : 'text-green-600'}>
                        {formatCurrency(supplier.outstanding_balance, supplier.currency)}
                      </span>
                    </td>
                    <td>
                      {supplier.is_active ? (
                        <span className="badge bg-green-100 text-green-700">Active</span>
                      ) : (
                        <span className="badge bg-slate-100 text-slate-500">Inactive</span>
                      )}
                    </td>
                    <td>
                      <div className="relative group">
                        <button className="p-2 hover:bg-slate-100 rounded-lg">
                          <MoreVertical className="w-4 h-4 text-slate-400" />
                        </button>
                        <div className="absolute right-0 top-full mt-1 w-40 bg-white rounded-lg shadow-lg border border-slate-200 py-1 hidden group-hover:block z-10">
                          <Link
                            to={`/purchasing/suppliers/${supplier.id}`}
                            className="dropdown-item"
                          >
                            <Eye className="w-4 h-4" />
                            View Details
                          </Link>
                          <Link
                            to={`/purchasing/suppliers/${supplier.id}/edit`}
                            className="dropdown-item"
                          >
                            <Edit className="w-4 h-4" />
                            Edit
                          </Link>
                          <button
                            onClick={() => handleDelete(supplier.id)}
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
