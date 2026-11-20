import {
  Users,
  ShoppingCart,
  DollarSign,
  TrendingUp,
  TrendingDown,
  Package,
  AlertCircle,
  Clock,
} from 'lucide-react'

// Mock data for dashboard
const stats = [
  {
    name: 'Total Revenue',
    value: '$1,234,567',
    change: '+12.5%',
    changeType: 'positive',
    icon: DollarSign,
  },
  {
    name: 'Active Customers',
    value: '2,847',
    change: '+8.2%',
    changeType: 'positive',
    icon: Users,
  },
  {
    name: 'Open Orders',
    value: '156',
    change: '-3.1%',
    changeType: 'negative',
    icon: ShoppingCart,
  },
  {
    name: 'Low Stock Items',
    value: '23',
    change: '+5',
    changeType: 'warning',
    icon: AlertCircle,
  },
]

const recentOrders = [
  { id: 'SO-2024-001', customer: 'Acme Corp', amount: '$12,500', status: 'pending', date: '2024-01-15' },
  { id: 'SO-2024-002', customer: 'Tech Solutions', amount: '$8,750', status: 'confirmed', date: '2024-01-15' },
  { id: 'SO-2024-003', customer: 'Global Industries', amount: '$23,000', status: 'shipped', date: '2024-01-14' },
  { id: 'SO-2024-004', customer: 'Smart Systems', amount: '$5,200', status: 'delivered', date: '2024-01-14' },
  { id: 'SO-2024-005', customer: 'Future Labs', amount: '$15,800', status: 'pending', date: '2024-01-13' },
]

const topProducts = [
  { name: 'Product A', sold: 1234, revenue: '$45,678' },
  { name: 'Product B', sold: 987, revenue: '$32,100' },
  { name: 'Product C', sold: 876, revenue: '$28,500' },
  { name: 'Product D', sold: 654, revenue: '$21,300' },
  { name: 'Product E', sold: 543, revenue: '$18,700' },
]

const statusColors: Record<string, string> = {
  pending: 'bg-warning-100 text-warning-700',
  confirmed: 'bg-primary-100 text-primary-700',
  shipped: 'bg-success-100 text-success-700',
  delivered: 'bg-slate-100 text-slate-700',
}

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-slate-500 mt-1">Welcome back! Here's what's happening today.</p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => (
          <div key={stat.name} className="card p-6">
            <div className="flex items-center justify-between">
              <div className="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center">
                <stat.icon className="w-6 h-6 text-primary-600" />
              </div>
              <span
                className={`inline-flex items-center gap-1 text-sm font-medium ${
                  stat.changeType === 'positive'
                    ? 'text-success-600'
                    : stat.changeType === 'negative'
                    ? 'text-danger-600'
                    : 'text-warning-600'
                }`}
              >
                {stat.changeType === 'positive' ? (
                  <TrendingUp className="w-4 h-4" />
                ) : stat.changeType === 'negative' ? (
                  <TrendingDown className="w-4 h-4" />
                ) : null}
                {stat.change}
              </span>
            </div>
            <div className="mt-4">
              <p className="text-2xl font-bold text-slate-900">{stat.value}</p>
              <p className="text-sm text-slate-500 mt-1">{stat.name}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Orders */}
        <div className="lg:col-span-2 card">
          <div className="card-header">
            <h2 className="text-lg font-semibold text-slate-900">Recent Orders</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Order ID</th>
                  <th>Customer</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {recentOrders.map((order) => (
                  <tr key={order.id}>
                    <td className="font-medium text-primary-600">{order.id}</td>
                    <td>{order.customer}</td>
                    <td className="font-medium">{order.amount}</td>
                    <td>
                      <span className={`badge ${statusColors[order.status]}`}>
                        {order.status}
                      </span>
                    </td>
                    <td className="text-slate-500">{order.date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Top Products */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-lg font-semibold text-slate-900">Top Products</h2>
          </div>
          <div className="divide-y divide-slate-100">
            {topProducts.map((product, index) => (
              <div key={product.name} className="p-4 flex items-center gap-4">
                <div className="w-8 h-8 bg-slate-100 rounded-lg flex items-center justify-center text-sm font-medium text-slate-600">
                  {index + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-slate-900 truncate">{product.name}</p>
                  <p className="text-sm text-slate-500">{product.sold} sold</p>
                </div>
                <p className="font-medium text-slate-900">{product.revenue}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quick actions */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <button className="btn btn-primary">
            <ShoppingCart className="w-4 h-4" />
            New Order
          </button>
          <button className="btn btn-secondary">
            <Users className="w-4 h-4" />
            Add Customer
          </button>
          <button className="btn btn-secondary">
            <Package className="w-4 h-4" />
            Add Product
          </button>
          <button className="btn btn-secondary">
            <Clock className="w-4 h-4" />
            View Reports
          </button>
        </div>
      </div>
    </div>
  )
}
