import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { customersApi, Customer } from '../../services/api'
import {
  Plus,
  Search,
  Filter,
  MoreVertical,
  Mail,
  Phone,
  Building2,
  User,
  Edit,
  Trash2,
  Eye,
} from 'lucide-react'

export default function CustomersPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selectedType, setSelectedType] = useState<string>('')
  const [selectedStatus, setSelectedStatus] = useState<string>('')

  // Fetch customers
  const { data, isLoading, error } = useQuery({
    queryKey: ['customers', { page, search, type: selectedType, status: selectedStatus }],
    queryFn: () =>
      customersApi.list({
        page,
        page_size: 20,
        search: search || undefined,
        customer_type: selectedType || undefined,
        status: selectedStatus || undefined,
      }),
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: customersApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customers'] })
    },
  })

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this customer?')) {
      await deleteMutation.mutateAsync(id)
    }
  }

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      active: 'bg-success-100 text-success-700',
      inactive: 'bg-slate-100 text-slate-700',
      prospect: 'bg-primary-100 text-primary-700',
      suspended: 'bg-warning-100 text-warning-700',
    }
    return styles[status] || 'bg-slate-100 text-slate-700'
  }

  const getTypeIcon = (type: string) => {
    return type === 'company' ? Building2 : User
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Customers</h1>
          <p className="text-slate-500 mt-1">Manage your customer relationships</p>
        </div>
        <Link
          to="/crm/customers/new"
          className="btn btn-primary"
        >
          <Plus className="w-4 h-4" />
          Add Customer
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
              placeholder="Search customers..."
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
            <option value="company">Company</option>
            <option value="individual">Individual</option>
            <option value="government">Government</option>
            <option value="partner">Partner</option>
          </select>

          {/* Status filter */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="select w-full md:w-40"
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="prospect">Prospect</option>
            <option value="suspended">Suspended</option>
          </select>
        </div>
      </div>

      {/* Customers table */}
      <div className="card">
        {isLoading ? (
          <div className="p-12 text-center">
            <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto" />
            <p className="text-slate-500 mt-4">Loading customers...</p>
          </div>
        ) : error ? (
          <div className="p-12 text-center">
            <p className="text-danger-600">Failed to load customers</p>
          </div>
        ) : data?.items.length === 0 ? (
          <div className="p-12 text-center">
            <Users className="w-12 h-12 text-slate-300 mx-auto" />
            <h3 className="text-lg font-medium text-slate-900 mt-4">No customers found</h3>
            <p className="text-slate-500 mt-2">Get started by creating a new customer.</p>
            <Link to="/crm/customers/new" className="btn btn-primary mt-4">
              <Plus className="w-4 h-4" />
              Add Customer
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Customer</th>
                  <th>Type</th>
                  <th>Contact</th>
                  <th>Location</th>
                  <th>Status</th>
                  <th>Revenue</th>
                  <th className="w-20"></th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((customer) => {
                  const TypeIcon = getTypeIcon(customer.customer_type)
                  return (
                    <tr key={customer.id}>
                      <td>
                        <Link
                          to={`/crm/customers/${customer.id}`}
                          className="flex items-center gap-3 hover:text-primary-600"
                        >
                          <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
                            <span className="font-medium text-primary-600">
                              {customer.name.charAt(0).toUpperCase()}
                            </span>
                          </div>
                          <div>
                            <p className="font-medium text-slate-900">{customer.name}</p>
                            <p className="text-sm text-slate-500">{customer.code}</p>
                          </div>
                        </Link>
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          <TypeIcon className="w-4 h-4 text-slate-400" />
                          <span className="capitalize">{customer.customer_type}</span>
                        </div>
                      </td>
                      <td>
                        <div className="space-y-1">
                          {customer.email && (
                            <div className="flex items-center gap-2 text-sm">
                              <Mail className="w-3 h-3 text-slate-400" />
                              <span>{customer.email}</span>
                            </div>
                          )}
                          {customer.phone && (
                            <div className="flex items-center gap-2 text-sm text-slate-500">
                              <Phone className="w-3 h-3" />
                              <span>{customer.phone}</span>
                            </div>
                          )}
                        </div>
                      </td>
                      <td>
                        <span className="text-slate-500">
                          {[customer.city, customer.country].filter(Boolean).join(', ') || '-'}
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${getStatusBadge(customer.status)}`}>
                          {customer.status}
                        </span>
                      </td>
                      <td>
                        <span className="font-medium">
                          ${customer.total_revenue.toLocaleString()}
                        </span>
                      </td>
                      <td>
                        <div className="relative group">
                          <button className="p-2 hover:bg-slate-100 rounded-lg">
                            <MoreVertical className="w-4 h-4 text-slate-400" />
                          </button>
                          <div className="absolute right-0 top-full mt-1 w-40 bg-white rounded-lg shadow-lg border border-slate-200 py-1 hidden group-hover:block z-10">
                            <Link
                              to={`/crm/customers/${customer.id}`}
                              className="dropdown-item"
                            >
                              <Eye className="w-4 h-4" />
                              View Details
                            </Link>
                            <Link
                              to={`/crm/customers/${customer.id}/edit`}
                              className="dropdown-item"
                            >
                              <Edit className="w-4 h-4" />
                              Edit
                            </Link>
                            <button
                              onClick={() => handleDelete(customer.id)}
                              className="w-full text-left dropdown-item text-danger-600"
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
