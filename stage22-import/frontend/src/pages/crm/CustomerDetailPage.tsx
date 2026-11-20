import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { customersApi } from '../../services/api'
import {
  ArrowLeft,
  Mail,
  Phone,
  Globe,
  MapPin,
  Building2,
  Edit,
  CreditCard,
  ShoppingCart,
  FileText,
} from 'lucide-react'

export default function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>()

  const { data: customer, isLoading, error } = useQuery({
    queryKey: ['customer', id],
    queryFn: () => customersApi.get(id!),
    enabled: !!id,
  })

  if (isLoading) {
    return (
      <div className="p-12 text-center">
        <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto" />
        <p className="text-slate-500 mt-4">Loading customer...</p>
      </div>
    )
  }

  if (error || !customer) {
    return (
      <div className="p-12 text-center">
        <p className="text-danger-600">Failed to load customer</p>
        <Link to="/crm/customers" className="btn btn-secondary mt-4">
          Back to Customers
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-4">
        <Link
          to="/crm/customers"
          className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{customer.name}</h1>
          <p className="text-slate-500">{customer.code}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Overview card */}
          <div className="card">
            <div className="card-header flex items-center justify-between">
              <h2 className="text-lg font-semibold">Overview</h2>
              <Link to={`/crm/customers/${id}/edit`} className="btn btn-secondary btn-sm">
                <Edit className="w-4 h-4" />
                Edit
              </Link>
            </div>
            <div className="card-body">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Contact info */}
                <div className="space-y-4">
                  <h3 className="font-medium text-slate-900">Contact Information</h3>
                  
                  {customer.email && (
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                        <Mail className="w-5 h-5 text-primary-600" />
                      </div>
                      <div>
                        <p className="text-sm text-slate-500">Email</p>
                        <a href={`mailto:${customer.email}`} className="text-slate-900 hover:text-primary-600">
                          {customer.email}
                        </a>
                      </div>
                    </div>
                  )}

                  {customer.phone && (
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                        <Phone className="w-5 h-5 text-primary-600" />
                      </div>
                      <div>
                        <p className="text-sm text-slate-500">Phone</p>
                        <a href={`tel:${customer.phone}`} className="text-slate-900 hover:text-primary-600">
                          {customer.phone}
                        </a>
                      </div>
                    </div>
                  )}

                  {customer.website && (
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                        <Globe className="w-5 h-5 text-primary-600" />
                      </div>
                      <div>
                        <p className="text-sm text-slate-500">Website</p>
                        <a href={customer.website} target="_blank" rel="noopener noreferrer" className="text-slate-900 hover:text-primary-600">
                          {customer.website}
                        </a>
                      </div>
                    </div>
                  )}
                </div>

                {/* Address */}
                <div className="space-y-4">
                  <h3 className="font-medium text-slate-900">Address</h3>
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center flex-shrink-0">
                      <MapPin className="w-5 h-5 text-primary-600" />
                    </div>
                    <div>
                      {customer.address_line1 && <p>{customer.address_line1}</p>}
                      {customer.city && <p>{customer.city}</p>}
                      {customer.country && <p>{customer.country}</p>}
                      {!customer.address_line1 && !customer.city && !customer.country && (
                        <p className="text-slate-400">No address provided</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Contacts */}
          <div className="card">
            <div className="card-header flex items-center justify-between">
              <h2 className="text-lg font-semibold">Contacts</h2>
              <button className="btn btn-secondary btn-sm">
                <Edit className="w-4 h-4" />
                Add Contact
              </button>
            </div>
            <div className="divide-y divide-slate-100">
              {customer.contacts && customer.contacts.length > 0 ? (
                customer.contacts.map((contact) => (
                  <div key={contact.id} className="p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-slate-100 rounded-full flex items-center justify-center">
                        <span className="font-medium text-slate-600">
                          {contact.first_name.charAt(0)}
                          {contact.last_name.charAt(0)}
                        </span>
                      </div>
                      <div>
                        <p className="font-medium text-slate-900">{contact.full_name}</p>
                        <p className="text-sm text-slate-500">{contact.title || 'No title'}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      {contact.email && (
                        <p className="text-sm">{contact.email}</p>
                      )}
                      {contact.phone && (
                        <p className="text-sm text-slate-500">{contact.phone}</p>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-8 text-center text-slate-500">
                  No contacts added yet
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Stats */}
          <div className="card p-6 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Status</span>
              <span className={`badge ${
                customer.status === 'active' ? 'bg-success-100 text-success-700' :
                customer.status === 'prospect' ? 'bg-primary-100 text-primary-700' :
                'bg-slate-100 text-slate-700'
              }`}>
                {customer.status}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Type</span>
              <span className="capitalize">{customer.customer_type}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Total Orders</span>
              <span className="font-medium">{customer.total_orders}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Total Revenue</span>
              <span className="font-medium">${customer.total_revenue.toLocaleString()}</span>
            </div>
          </div>

          {/* Credit Info */}
          <div className="card p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                <CreditCard className="w-5 h-5 text-primary-600" />
              </div>
              <h3 className="font-semibold">Credit Information</h3>
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Credit Limit</span>
                <span className="font-medium">${customer.credit_limit.toLocaleString()}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Credit Used</span>
                <span className="font-medium">${customer.credit_used.toLocaleString()}</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2 mt-2">
                <div
                  className="bg-primary-500 h-2 rounded-full"
                  style={{ width: `${Math.min((customer.credit_used / customer.credit_limit) * 100, 100)}%` }}
                />
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="card p-4 space-y-2">
            <button className="w-full btn btn-secondary justify-start">
              <ShoppingCart className="w-4 h-4" />
              Create Sales Order
            </button>
            <button className="w-full btn btn-secondary justify-start">
              <FileText className="w-4 h-4" />
              Create Quote
            </button>
            <button className="w-full btn btn-secondary justify-start">
              <Mail className="w-4 h-4" />
              Send Email
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
