/**
 * Nexus ERP - Stock Levels Page
 * Real-time stock monitoring and management
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, PaginatedResponse } from '../../services/api'
import {
  Search,
  Package,
  AlertTriangle,
  TrendingDown,
  TrendingUp,
  Minus,
  Plus,
  Warehouse,
  BarChart3,
} from 'lucide-react'

interface StockLevel {
  id: string
  product_id: string
  product_code: string
  product_name: string
  warehouse_id: string
  warehouse_name: string
  quantity_on_hand: number
  quantity_reserved: number
  quantity_available: number
  quantity_incoming: number
  quantity_outgoing: number
  reorder_point: number
  max_stock: number
  uom: string
  cost: number
  stock_value: number
  last_movement_date: string
}

export default function StockPage() {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selectedWarehouse, setSelectedWarehouse] = useState<string>('')
  const [stockFilter, setStockFilter] = useState<string>('')

  // Fetch stock levels
  const { data, isLoading, error } = useQuery({
    queryKey: ['stock-levels', { page, search, warehouse: selectedWarehouse, filter: stockFilter }],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20',
        ...(search && { search }),
        ...(selectedWarehouse && { warehouse: selectedWarehouse }),
        ...(stockFilter && { filter: stockFilter }),
      })
      const response = await api.get(`/inventory/stock?${params}`)
      return response.data as PaginatedResponse<StockLevel>
    },
  })

  // Fetch warehouses for filter
  const { data: warehouses } = useQuery({
    queryKey: ['warehouses-list'],
    queryFn: async () => {
      const response = await api.get('/inventory/warehouses?page_size=100')
      return response.data
    },
  })

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
    })
  }

  // Calculate summary
  const summary = data?.items.reduce((acc, stock) => {
    acc.totalValue += stock.stock_value
    acc.totalItems++
    if (stock.quantity_available <= stock.reorder_point) {
      acc.lowStock++
    }
    if (stock.quantity_on_hand < 0) {
      acc.negativeStock++
    }
    if (stock.quantity_incoming > 0) {
      acc.incoming += stock.quantity_incoming
    }
    return acc
  }, { totalValue: 0, totalItems: 0, lowStock: 0, negativeStock: 0, incoming: 0 })

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Stock Levels</h1>
          <p className="text-slate-500 mt-1">Real-time inventory monitoring</p>
        </div>
        <Link
          to="/inventory/adjustments/new"
          className="btn btn-primary"
        >
          <Plus className="w-4 h-4" />
          Stock Adjustment
        </Link>
      </div>

      {/* Summary Cards */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <Package className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Total Items</p>
                <p className="text-xl font-bold text-slate-900">{summary?.totalItems || 0}</p>
              </div>
            </div>
          </div>
          <div className="card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                <BarChart3 className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Stock Value</p>
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
                <p className="text-sm text-slate-500">Low Stock</p>
                <p className="text-xl font-bold text-yellow-600">{summary?.lowStock || 0}</p>
              </div>
            </div>
          </div>
          <div className="card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Incoming</p>
                <p className="text-xl font-bold text-slate-900">{summary?.incoming || 0}</p>
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

          {/* Warehouse filter */}
          <select
            value={selectedWarehouse}
            onChange={(e) => setSelectedWarehouse(e.target.value)}
            className="select w-full md:w-48"
          >
            <option value="">All Warehouses</option>
            {warehouses?.items?.map((wh: { id: string; name: string }) => (
              <option key={wh.id} value={wh.id}>{wh.name}</option>
            ))}
          </select>

          {/* Stock filter */}
          <select
            value={stockFilter}
            onChange={(e) => setStockFilter(e.target.value)}
            className="select w-full md:w-48"
          >
            <option value="">All Stock Levels</option>
            <option value="low_stock">Low Stock</option>
            <option value="out_of_stock">Out of Stock</option>
            <option value="negative">Negative Stock</option>
            <option value="in_stock">In Stock</option>
          </select>
        </div>
      </div>

      {/* Stock table */}
      <div className="card">
        {isLoading ? (
          <div className="p-12 text-center">
            <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto" />
            <p className="text-slate-500 mt-4">Loading stock levels...</p>
          </div>
        ) : error ? (
          <div className="p-12 text-center">
            <p className="text-red-600">Failed to load stock levels</p>
          </div>
        ) : data?.items.length === 0 ? (
          <div className="p-12 text-center">
            <Package className="w-12 h-12 text-slate-300 mx-auto" />
            <h3 className="text-lg font-medium text-slate-900 mt-4">No stock data found</h3>
            <p className="text-slate-500 mt-2">Stock levels will appear here once products are added to warehouses.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Warehouse</th>
                  <th className="text-right">On Hand</th>
                  <th className="text-right">Reserved</th>
                  <th className="text-right">Available</th>
                  <th className="text-right">Incoming</th>
                  <th className="text-right">Value</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((stock) => {
                  const isLowStock = stock.quantity_available <= stock.reorder_point && stock.quantity_available > 0
                  const isOutOfStock = stock.quantity_available <= 0
                  const isNegative = stock.quantity_on_hand < 0
                  
                  return (
                    <tr key={stock.id} className={isNegative ? 'bg-red-50' : ''}>
                      <td>
                        <Link
                          to={`/inventory/products/${stock.product_id}`}
                          className="flex items-center gap-3 hover:text-primary-600"
                        >
                          <div className="w-8 h-8 bg-slate-100 rounded-lg flex items-center justify-center">
                            <Package className="w-4 h-4 text-slate-400" />
                          </div>
                          <div>
                            <p className="font-medium text-slate-900">{stock.product_name}</p>
                            <p className="text-xs text-slate-500">{stock.product_code}</p>
                          </div>
                        </Link>
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          <Warehouse className="w-4 h-4 text-slate-400" />
                          <span>{stock.warehouse_name}</span>
                        </div>
                      </td>
                      <td className="text-right">
                        <span className={stock.quantity_on_hand < 0 ? 'text-red-600 font-medium' : ''}>
                          {stock.quantity_on_hand} {stock.uom}
                        </span>
                      </td>
                      <td className="text-right text-slate-600">
                        {stock.quantity_reserved} {stock.uom}
                      </td>
                      <td className="text-right">
                        <span className={isLowStock || isOutOfStock ? 'font-medium' : ''}>
                          {isOutOfStock ? (
                            <span className="text-red-600">0 {stock.uom}</span>
                          ) : isLowStock ? (
                            <span className="text-yellow-600">{stock.quantity_available} {stock.uom}</span>
                          ) : (
                            <span>{stock.quantity_available} {stock.uom}</span>
                          )}
                        </span>
                      </td>
                      <td className="text-right">
                        {stock.quantity_incoming > 0 ? (
                          <span className="text-purple-600 font-medium flex items-center justify-end gap-1">
                            <TrendingUp className="w-4 h-4" />
                            {stock.quantity_incoming} {stock.uom}
                          </span>
                        ) : (
                          <span className="text-slate-400">-</span>
                        )}
                      </td>
                      <td className="text-right font-medium">
                        {formatCurrency(stock.stock_value)}
                      </td>
                      <td>
                        {isNegative ? (
                          <span className="badge bg-red-100 text-red-700">Negative</span>
                        ) : isOutOfStock ? (
                          <span className="badge bg-red-100 text-red-700">Out of Stock</span>
                        ) : isLowStock ? (
                          <span className="badge bg-yellow-100 text-yellow-700">Low Stock</span>
                        ) : (
                          <span className="badge bg-green-100 text-green-700">In Stock</span>
                        )}
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
