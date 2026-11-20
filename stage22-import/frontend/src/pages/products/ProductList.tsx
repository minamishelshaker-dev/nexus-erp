/**
 * Nexus ERP - Products Page
 * Product catalog management
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, PaginatedResponse } from '../../services/api'
import {
  Plus,
  Search,
  Package,
  MoreVertical,
  Eye,
  Edit,
  Trash2,
  Copy,
  BarChart3,
  AlertTriangle,
  Tag,
} from 'lucide-react'

interface Product {
  id: string
  code: string
  name: string
  category: string
  category_name: string
  type: 'product' | 'service' | 'consumable'
  uom: string
  price: number
  cost: number
  quantity_on_hand: number
  quantity_available: number
  quantity_reserved: number
  reorder_point: number
  is_active: boolean
  barcode?: string
  description?: string
}

const typeColors: Record<string, string> = {
  product: 'bg-blue-100 text-blue-700',
  service: 'bg-purple-100 text-purple-700',
  consumable: 'bg-orange-100 text-orange-700',
}

const typeLabels: Record<string, string> = {
  product: 'Product',
  service: 'Service',
  consumable: 'Consumable',
}

export default function ProductsPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selectedType, setSelectedType] = useState<string>('')
  const [selectedCategory, setSelectedCategory] = useState<string>('')

  // Fetch products
  const { data, isLoading, error } = useQuery({
    queryKey: ['products', { page, search, type: selectedType, category: selectedCategory }],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20',
        ...(search && { search }),
        ...(selectedType && { type: selectedType }),
        ...(selectedCategory && { category: selectedCategory }),
      })
      const response = await api.get(`/inventory/products?${params}`)
      return response.data as PaginatedResponse<Product>
    },
  })

  // Fetch categories for filter
  const { data: categories } = useQuery({
    queryKey: ['product-categories'],
    queryFn: async () => {
      const response = await api.get('/inventory/categories')
      return response.data
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/inventory/products/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })

  // Duplicate mutation
  const duplicateMutation = useMutation({
    mutationFn: async (id: string) => {
      const response = await api.post(`/inventory/products/${id}/duplicate`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this product?')) {
      await deleteMutation.mutateAsync(id)
    }
  }

  const handleDuplicate = async (id: string) => {
    if (confirm('Create a copy of this product?')) {
      await duplicateMutation.mutateAsync(id)
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount)
  }

  // Calculate summary
  const summary = data?.items.reduce((acc, product) => {
    if (product.type === 'product') {
      acc.totalProducts++
      acc.totalValue += product.quantity_on_hand * product.cost
      if (product.quantity_available <= product.reorder_point) {
        acc.lowStock++
      }
    }
    return acc
  }, { totalProducts: 0, totalValue: 0, lowStock: 0 })

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Products</h1>
          <p className="text-slate-500 mt-1">Manage your product catalog</p>
        </div>
        <Link
          to="/inventory/products/new"
          className="btn btn-primary"
        >
          <Plus className="w-4 h-4" />
          Add Product
        </Link>
      </div>

      {/* Summary Cards */}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <Package className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Total Products</p>
                <p className="text-xl font-bold text-slate-900">{summary?.totalProducts || 0}</p>
              </div>
            </div>
          </div>
          <div className="card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                <BarChart3 className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Inventory Value</p>
                <p className="text-xl font-bold text-slate-900">{formatCurrency(summary?.totalValue || 0)}</p>
              </div>
            </div>
          </div>
          <div className="card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Low Stock Items</p>
                <p className="text-xl font-bold text-yellow-600">{summary?.lowStock || 0}</p>
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
              placeholder="Search products..."
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
            <option value="product">Product</option>
            <option value="service">Service</option>
            <option value="consumable">Consumable</option>
          </select>

          {/* Category filter */}
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="select w-full md:w-48"
          >
            <option value="">All Categories</option>
            {categories?.map((cat: { id: string; name: string }) => (
              <option key={cat.id} value={cat.id}>{cat.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Products table */}
      <div className="card">
        {isLoading ? (
          <div className="p-12 text-center">
            <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto" />
            <p className="text-slate-500 mt-4">Loading products...</p>
          </div>
        ) : error ? (
          <div className="p-12 text-center">
            <p className="text-red-600">Failed to load products</p>
          </div>
        ) : data?.items.length === 0 ? (
          <div className="p-12 text-center">
            <Package className="w-12 h-12 text-slate-300 mx-auto" />
            <h3 className="text-lg font-medium text-slate-900 mt-4">No products found</h3>
            <p className="text-slate-500 mt-2">Get started by creating a new product.</p>
            <Link to="/inventory/products/new" className="btn btn-primary mt-4">
              <Plus className="w-4 h-4" />
              Add Product
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Type</th>
                  <th>Category</th>
                  <th>Price</th>
                  <th>Cost</th>
                  <th>On Hand</th>
                  <th>Available</th>
                  <th>Status</th>
                  <th className="w-20"></th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((product) => {
                  const isLowStock = product.type === 'product' && product.quantity_available <= product.reorder_point
                  return (
                    <tr key={product.id} className={!product.is_active ? 'bg-slate-50 opacity-60' : ''}>
                      <td>
                        <Link
                          to={`/inventory/products/${product.id}`}
                          className="flex items-center gap-3 hover:text-primary-600"
                        >
                          <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center">
                            <Package className="w-5 h-5 text-slate-400" />
                          </div>
                          <div>
                            <p className="font-medium text-slate-900">{product.name}</p>
                            <div className="flex items-center gap-2 text-sm text-slate-500">
                              <span>{product.code}</span>
                              {product.barcode && (
                                <>
                                  <span>•</span>
                                  <span className="flex items-center gap-1">
                                    <Tag className="w-3 h-3" />
                                    {product.barcode}
                                  </span>
                                </>
                              )}
                            </div>
                          </div>
                        </Link>
                      </td>
                      <td>
                        <span className={`badge ${typeColors[product.type]}`}>
                          {typeLabels[product.type]}
                        </span>
                      </td>
                      <td>
                        <span className="text-slate-600">{product.category_name || '-'}</span>
                      </td>
                      <td>
                        <span className="font-medium">{formatCurrency(product.price)}</span>
                      </td>
                      <td>
                        <span className="text-slate-600">{formatCurrency(product.cost)}</span>
                      </td>
                      <td>
                        <span className={product.quantity_on_hand < 0 ? 'text-red-600 font-medium' : ''}>
                          {product.quantity_on_hand} {product.uom}
                        </span>
                      </td>
                      <td>
                        <div className="flex items-center gap-1">
                          <span className={isLowStock ? 'text-yellow-600 font-medium' : ''}>
                            {product.quantity_available} {product.uom}
                          </span>
                          {isLowStock && (
                            <AlertTriangle className="w-4 h-4 text-yellow-500" />
                          )}
                        </div>
                      </td>
                      <td>
                        {product.is_active ? (
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
                          <div className="absolute right-0 top-full mt-1 w-48 bg-white rounded-lg shadow-lg border border-slate-200 py-1 hidden group-hover:block z-10">
                            <Link
                              to={`/inventory/products/${product.id}`}
                              className="dropdown-item"
                            >
                              <Eye className="w-4 h-4" />
                              View Details
                            </Link>
                            <Link
                              to={`/inventory/products/${product.id}/edit`}
                              className="dropdown-item"
                            >
                              <Edit className="w-4 h-4" />
                              Edit
                            </Link>
                            <button
                              onClick={() => handleDuplicate(product.id)}
                              className="w-full text-left dropdown-item"
                            >
                              <Copy className="w-4 h-4" />
                              Duplicate
                            </button>
                            <button
                              onClick={() => handleDelete(product.id)}
                              className="w-full text-left dropdown-item text-red-600"
                            >
                              <Trash2 className="w-4 h-4" />
                              Delete
                            </button>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )
                })}
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
