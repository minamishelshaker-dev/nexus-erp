/**
 * Nexus ERP - Invoices Page
 * Sales invoices management
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, PaginatedResponse } from '../../services/api'
import {
  Plus,
  Search,
  FileText,
  Calendar,
  MoreVertical,
  Eye,
  Edit,
  Trash2,
  Send,
  Download,
  CreditCard,
  AlertCircle,
} from 'lucide-react'

interface Invoice {
  id: string
  number: string
  customer_id: string
  customer_name: string
  date: string
  due_date: string
  state: 'draft' | 'posted' | 'sent' | 'paid' | 'partial' | 'overdue' | 'cancelled'
  amount_untaxed: number
  amount_tax: number
  amount_total: number
  amount_due: number
  payment_status: string
  order_id?: string
  order_number?: string
}

const statusColors: Record<string, string> = {
  draft: 'bg-slate-100 text-slate-700',
  posted: 'bg-blue-100 text-blue-700',
  sent: 'bg-cyan-100 text-cyan-700',
  paid: 'bg-green-100 text-green-700',
  partial: 'bg-yellow-100 text-yellow-700',
  overdue: 'bg-red-100 text-red-700',
  cancelled: 'bg-gray-100 text-gray-500 line-through',
}

const statusLabels: Record<string, string> = {
  draft: 'Draft',
  posted: 'Posted',
  sent: 'Sent',
  paid: 'Paid',
  partial: 'Partial',
  overdue: 'Overdue',
  cancelled: 'Cancelled',
}

export default function InvoicesPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selectedStatus, setSelectedStatus] = useState<string>('')
  const [dateFrom, setDateFrom] = useState<string>('')
  const [dateTo, setDateTo] = useState<string>('')

  // Fetch invoices
  const { data, isLoading, error } = useQuery({
    queryKey: ['invoices', { page, search, status: selectedStatus, dateFrom, dateTo }],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20',
        ...(search && { search }),
        ...(selectedStatus && { state: selectedStatus }),
        ...(dateFrom && { date_from: dateFrom }),
        ...(dateTo && { date_to: dateTo }),
      })
      const response = await api.get(`/sales/invoices?${params}`)
      return response.data as PaginatedResponse<Invoice>
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/sales/invoices/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
    },
  })

  // Post/Confirm mutation
  const postMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/sales/invoices/${id}/post`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
    },
  })

  // Send mutation
  const sendMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/sales/invoices/${id}/send`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
    },
  })

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this invoice?')) {
      await deleteMutation.mutateAsync(id)
    }
  }

  const handlePost = async (id: string) => {
    if (confirm('Post this invoice? This action cannot be undone.')) {
      await postMutation.mutateAsync(id)
    }
  }

  const handleSend = async (id: string) => {
    if (confirm('Send this invoice to the customer?')) {
      await sendMutation.mutateAsync(id)
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
  const summary = data?.items.reduce((acc, inv) => {
    acc.total += inv.amount_total
    if (inv.state === 'overdue') {
      acc.overdue += inv.amount_due
    }
    if (['posted', 'sent', 'partial', 'overdue'].includes(inv.state)) {
      acc.outstanding += inv.amount_due
    }
    return acc
  }, { total: 0, outstanding: 0, overdue: 0 })

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Invoices</h1>
          <p className="text-slate-500 mt-1">Manage customer invoices and payments</p>
        </div>
        <Link
          to="/sales/invoices/new"
          className="btn btn-primary"
        >
          <Plus className="w-4 h-4" />
          Create Invoice
        </Link>
      </div>

      {/* Summary Cards */}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="card p-4">
            <p className="text-sm text-slate-500">Total Invoice Value</p>
            <p className="text-2xl font-bold text-slate-900">{formatCurrency(summary?.total || 0)}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-slate-500">Outstanding Balance</p>
            <p className="text-2xl font-bold text-yellow-600">{formatCurrency(summary?.outstanding || 0)}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-slate-500">Overdue Amount</p>
            <p className="text-2xl font-bold text-red-600">{formatCurrency(summary?.overdue || 0)}</p>
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
              placeholder="Search invoices..."
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
            <option value="draft">Draft</option>
            <option value="posted">Posted</option>
            <option value="sent">Sent</option>
            <option value="paid">Paid</option>
            <option value="partial">Partial</option>
            <option value="overdue">Overdue</option>
            <option value="cancelled">Cancelled</option>
          </select>

          {/* Date From */}
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="select w-full md:w-40"
            placeholder="From Date"
          />

          {/* Date To */}
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="select w-full md:w-40"
            placeholder="To Date"
          />
        </div>
      </div>

      {/* Invoices table */}
      <div className="card">
        {isLoading ? (
          <div className="p-12 text-center">
            <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto" />
            <p className="text-slate-500 mt-4">Loading invoices...</p>
          </div>
        ) : error ? (
          <div className="p-12 text-center">
            <p className="text-red-600">Failed to load invoices</p>
          </div>
        ) : data?.items.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-12 h-12 text-slate-300 mx-auto" />
            <h3 className="text-lg font-medium text-slate-900 mt-4">No invoices found</h3>
            <p className="text-slate-500 mt-2">Get started by creating a new invoice.</p>
            <Link to="/sales/invoices/new" className="btn btn-primary mt-4">
              <Plus className="w-4 h-4" />
              Create Invoice
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Invoice #</th>
                  <th>Customer</th>
                  <th>Date</th>
                  <th>Due Date</th>
                  <th>Total</th>
                  <th>Due</th>
                  <th>Status</th>
                  <th className="w-20"></th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((invoice) => (
                  <tr key={invoice.id} className={invoice.state === 'overdue' ? 'bg-red-50' : ''}>
                    <td>
                      <div className="flex items-center gap-2">
                        {invoice.state === 'overdue' && (
                          <AlertCircle className="w-4 h-4 text-red-500" />
                        )}
                        <Link
                          to={`/sales/invoices/${invoice.id}`}
                          className="font-medium text-primary-600 hover:underline"
                        >
                          {invoice.number}
                        </Link>
                      </div>
                      {invoice.order_number && (
                        <p className="text-xs text-slate-400">Order: {invoice.order_number}</p>
                      )}
                    </td>
                    <td>
                      <Link
                        to={`/crm/customers/${invoice.customer_id}`}
                        className="text-slate-900 hover:text-primary-600"
                      >
                        {invoice.customer_name}
                      </Link>
                    </td>
                    <td>
                      <div className="flex items-center gap-2 text-slate-500">
                        <Calendar className="w-4 h-4" />
                        {formatDate(invoice.date)}
                      </div>
                    </td>
                    <td>
                      <span className={invoice.state === 'overdue' ? 'text-red-600 font-medium' : 'text-slate-500'}>
                        {formatDate(invoice.due_date)}
                      </span>
                    </td>
                    <td>
                      <span className="font-medium">{formatCurrency(invoice.amount_total)}</span>
                    </td>
                    <td>
                      <span className={invoice.amount_due > 0 ? 'text-yellow-600 font-medium' : 'text-green-600'}>
                        {formatCurrency(invoice.amount_due)}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${statusColors[invoice.state]}`}>
                        {statusLabels[invoice.state]}
                      </span>
                    </td>
                    <td>
                      <div className="relative group">
                        <button className="p-2 hover:bg-slate-100 rounded-lg">
                          <MoreVertical className="w-4 h-4 text-slate-400" />
                        </button>
                        <div className="absolute right-0 top-full mt-1 w-48 bg-white rounded-lg shadow-lg border border-slate-200 py-1 hidden group-hover:block z-10">
                          <Link
                            to={`/sales/invoices/${invoice.id}`}
                            className="dropdown-item"
                          >
                            <Eye className="w-4 h-4" />
                            View Details
                          </Link>
                          {invoice.state === 'draft' && (
                            <>
                              <Link
                                to={`/sales/invoices/${invoice.id}/edit`}
                                className="dropdown-item"
                              >
                                <Edit className="w-4 h-4" />
                                Edit
                              </Link>
                              <button
                                onClick={() => handlePost(invoice.id)}
                                className="w-full text-left dropdown-item text-blue-600"
                              >
                                <FileText className="w-4 h-4" />
                                Post Invoice
                              </button>
                            </>
                          )}
                          {invoice.state === 'posted' && (
                            <button
                              onClick={() => handleSend(invoice.id)}
                              className="w-full text-left dropdown-item text-cyan-600"
                            >
                              <Send className="w-4 h-4" />
                              Send to Customer
                            </button>
                          )}
                          {invoice.amount_due > 0 && ['posted', 'sent', 'partial', 'overdue'].includes(invoice.state) && (
                            <Link
                              to={`/sales/invoices/${invoice.id}/payment`}
                              className="dropdown-item text-green-600"
                            >
                              <CreditCard className="w-4 h-4" />
                              Register Payment
                            </Link>
                          )}
                          <button
                            onClick={() => window.open(`/api/v1/sales/invoices/${invoice.id}/pdf`, '_blank')}
                            className="w-full text-left dropdown-item"
                          >
                            <Download className="w-4 h-4" />
                            Download PDF
                          </button>
                          {invoice.state === 'draft' && (
                            <button
                              onClick={() => handleDelete(invoice.id)}
                              className="w-full text-left dropdown-item text-red-600"
                            >
                              <Trash2 className="w-4 h-4" />
                              Delete
                            </button>
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
