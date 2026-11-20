/**
 * Nexus ERP - Settings Page
 * Application settings with multiple tabs
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, PaginatedResponse } from '../../services/api'
import {
  Building2,
  Users,
  CreditCard,
  Shield,
  Bell,
  Palette,
  Globe,
  Database,
  Key,
  Mail,
  Save,
  Upload,
  Plus,
  Edit,
  Trash2,
  MoreVertical,
  CheckCircle,
  XCircle,
  Clock,
  DollarSign,
  Calendar,
  FileText,
  Zap,
} from 'lucide-react'

interface Company {
  id: string
  name: string
  legal_name?: string
  logo_url?: string
  address: string
  city: string
  country: string
  phone: string
  email: string
  website?: string
  tax_id?: string
  currency: string
  timezone: string
  date_format: string
}

interface User {
  id: string
  username: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  avatar_url?: string
  is_active: boolean
  is_admin: boolean
  role_name?: string
  last_login?: string
  created_at: string
}

interface Plan {
  id: string
  name: string
  code: string
  price_monthly: number
  price_yearly: number
  currency: string
  max_users: number
  features: string[]
  is_current: boolean
}

interface Subscription {
  id: string
  plan_id: string
  plan_name: string
  status: 'active' | 'trial' | 'expired' | 'cancelled'
  billing_cycle: 'monthly' | 'yearly'
  end_date?: string
  amount: number
  currency: string
  auto_renew: boolean
}

const tabs = [
  { id: 'company', label: 'Company', icon: Building2 },
  { id: 'users', label: 'Users', icon: Users },
  { id: 'plans', label: 'Plans & Billing', icon: CreditCard },
  { id: 'security', label: 'Security', icon: Shield },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'appearance', label: 'Appearance', icon: Palette },
  { id: 'integrations', label: 'Integrations', icon: Zap },
  { id: 'backup', label: 'Backup & Restore', icon: Database },
]

export default function SettingsPage() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('company')
  const [isSaving, setIsSaving] = useState(false)

  // Fetch company data
  const { data: company, isLoading: companyLoading } = useQuery({
    queryKey: ['company'],
    queryFn: async () => {
      const response = await api.get('/settings/company')
      return response.data as Company
    },
  })

  // Fetch users
  const { data: usersData, isLoading: usersLoading } = useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const response = await api.get('/settings/users')
      return response.data as PaginatedResponse<User>
    },
  })

  // Fetch plans
  const { data: plans } = useQuery({
    queryKey: ['plans'],
    queryFn: async () => {
      const response = await api.get('/settings/plans')
      return response.data as Plan[]
    },
  })

  // Fetch subscription
  const { data: subscription } = useQuery({
    queryKey: ['subscription'],
    queryFn: async () => {
      const response = await api.get('/settings/subscription')
      return response.data as Subscription
    },
  })

  // Update company mutation
  const updateCompanyMutation = useMutation({
    mutationFn: async (data: Partial<Company>) => {
      const response = await api.put('/settings/company', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company'] })
      setIsSaving(false)
    },
  })

  const handleSaveCompany = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setIsSaving(true)
    const formData = new FormData(e.currentTarget)
    const data = Object.fromEntries(formData)
    await updateCompanyMutation.mutateAsync(data)
  }

  const formatCurrency = (amount: number, currency = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    })
  }

  return (
    <div className="flex gap-6 -mx-6 -mb-6">
      {/* Sidebar */}
      <div className="w-64 flex-shrink-0 bg-slate-50 border-r border-slate-200 p-4">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Settings</h2>
        <nav className="space-y-1">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'bg-white text-primary-600 shadow-sm'
                    : 'text-slate-600 hover:bg-white/50'
                }`}
              >
                <Icon className="w-5 h-5" />
                {tab.label}
              </button>
            )
          })}
        </nav>
      </div>

      {/* Content */}
      <div className="flex-1 p-6 overflow-y-auto">
        {/* Company Tab */}
        {activeTab === 'company' && (
          <div className="max-w-3xl">
            <h3 className="text-lg font-semibold text-slate-900 mb-6">Company Information</h3>
            {companyLoading ? (
              <div className="animate-pulse space-y-4">
                {[...Array(8)].map((_, i) => (
                  <div key={i} className="h-10 bg-slate-200 rounded" />
                ))}
              </div>
            ) : (
              <form onSubmit={handleSaveCompany} className="space-y-6">
                {/* Logo */}
                <div className="flex items-center gap-6">
                  <div className="w-24 h-24 bg-slate-100 rounded-xl flex items-center justify-center border-2 border-dashed border-slate-300">
                    {company?.logo_url ? (
                      <img src={company.logo_url} alt="Logo" className="w-full h-full object-cover rounded-xl" />
                    ) : (
                      <Building2 className="w-8 h-8 text-slate-400" />
                    )}
                  </div>
                  <div>
                    <button type="button" className="btn btn-secondary">
                      <Upload className="w-4 h-4" />
                      Upload Logo
                    </button>
                    <p className="text-xs text-slate-500 mt-2">PNG, JPG up to 2MB. Recommended: 200x200px</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Company Name *</label>
                    <input
                      type="text"
                      name="name"
                      defaultValue={company?.name}
                      className="input"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Legal Name</label>
                    <input
                      type="text"
                      name="legal_name"
                      defaultValue={company?.legal_name}
                      className="input"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Email *</label>
                    <input
                      type="email"
                      name="email"
                      defaultValue={company?.email}
                      className="input"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Phone *</label>
                    <input
                      type="tel"
                      name="phone"
                      defaultValue={company?.phone}
                      className="input"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Address</label>
                  <input
                    type="text"
                    name="address"
                    defaultValue={company?.address}
                    className="input"
                  />
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">City</label>
                    <input
                      type="text"
                      name="city"
                      defaultValue={company?.city}
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Country</label>
                    <input
                      type="text"
                      name="country"
                      defaultValue={company?.country}
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Tax ID</label>
                    <input
                      type="text"
                      name="tax_id"
                      defaultValue={company?.tax_id}
                      className="input"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Currency</label>
                    <select name="currency" defaultValue={company?.currency || 'USD'} className="select">
                      <option value="USD">USD - US Dollar</option>
                      <option value="EUR">EUR - Euro</option>
                      <option value="GBP">GBP - British Pound</option>
                      <option value="SAR">SAR - Saudi Riyal</option>
                      <option value="AED">AED - UAE Dirham</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Timezone</label>
                    <select name="timezone" defaultValue={company?.timezone || 'UTC'} className="select">
                      <option value="UTC">UTC</option>
                      <option value="America/New_York">Eastern Time (ET)</option>
                      <option value="America/Chicago">Central Time (CT)</option>
                      <option value="America/Denver">Mountain Time (MT)</option>
                      <option value="America/Los_Angeles">Pacific Time (PT)</option>
                      <option value="Europe/London">London (GMT)</option>
                      <option value="Europe/Paris">Paris (CET)</option>
                      <option value="Asia/Riyadh">Riyadh (AST)</option>
                      <option value="Asia/Dubai">Dubai (GST)</option>
                    </select>
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-200">
                  <button type="submit" className="btn btn-primary" disabled={isSaving}>
                    <Save className="w-4 h-4" />
                    {isSaving ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              </form>
            )}
          </div>
        )}

        {/* Users Tab */}
        {activeTab === 'users' && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-slate-900">User Management</h3>
              <button className="btn btn-primary">
                <Plus className="w-4 h-4" />
                Add User
              </button>
            </div>
            {usersLoading ? (
              <div className="animate-pulse space-y-4">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="h-16 bg-slate-200 rounded" />
                ))}
              </div>
            ) : (
              <div className="card overflow-hidden">
                <table className="table">
                  <thead>
                    <tr>
                      <th>User</th>
                      <th>Email</th>
                      <th>Role</th>
                      <th>Last Login</th>
                      <th>Status</th>
                      <th className="w-20"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {usersData?.items.map((user) => (
                      <tr key={user.id}>
                        <td>
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
                              <span className="text-sm font-medium text-primary-600">
                                {user.full_name.charAt(0)}
                              </span>
                            </div>
                            <div>
                              <p className="font-medium text-slate-900">{user.full_name}</p>
                              <p className="text-sm text-slate-500">@{user.username}</p>
                            </div>
                          </div>
                        </td>
                        <td>
                          <span className="text-slate-600">{user.email}</span>
                        </td>
                        <td>
                          <span className="badge bg-blue-100 text-blue-700">
                            {user.role_name || (user.is_admin ? 'Admin' : 'User')}
                          </span>
                        </td>
                        <td>
                          <span className="text-slate-600">
                            {user.last_login ? formatDate(user.last_login) : 'Never'}
                          </span>
                        </td>
                        <td>
                          {user.is_active ? (
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
                              <button className="w-full text-left px-4 py-2 text-sm hover:bg-slate-50 flex items-center gap-2">
                                <Edit className="w-4 h-4" />
                                Edit
                              </button>
                              <button className="w-full text-left px-4 py-2 text-sm hover:bg-slate-50 flex items-center gap-2">
                                <Key className="w-4 h-4" />
                                Reset Password
                              </button>
                              <button className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-slate-50 flex items-center gap-2">
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
          </div>
        )}

        {/* Plans Tab */}
        {activeTab === 'plans' && (
          <div>
            <h3 className="text-lg font-semibold text-slate-900 mb-6">Plans & Billing</h3>
            
            {/* Current Subscription */}
            {subscription && (
              <div className="card p-6 mb-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-slate-500">Current Plan</p>
                    <p className="text-2xl font-bold text-slate-900">{subscription.plan_name}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className={`badge ${
                        subscription.status === 'active' ? 'bg-green-100 text-green-700' :
                        subscription.status === 'trial' ? 'bg-blue-100 text-blue-700' :
                        subscription.status === 'expired' ? 'bg-red-100 text-red-700' :
                        'bg-slate-100 text-slate-500'
                      }`}>
                        {subscription.status.charAt(0).toUpperCase() + subscription.status.slice(1)}
                      </span>
                      {subscription.end_date && (
                        <span className="text-sm text-slate-500">
                          {subscription.status === 'trial' ? 'Trial ends' : 'Renews'} {formatDate(subscription.end_date)}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold text-slate-900">
                      {formatCurrency(subscription.amount, subscription.currency)}
                    </p>
                    <p className="text-sm text-slate-500">/{subscription.billing_cycle}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Available Plans */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {plans?.map((plan) => (
                <div key={plan.id} className={`card overflow-hidden ${plan.is_current ? 'ring-2 ring-primary-500' : ''}`}>
                  {plan.is_current && (
                    <div className="bg-primary-600 text-white text-sm font-medium py-1 px-4 text-center">
                      Current Plan
                    </div>
                  )}
                  <div className="p-6">
                    <h4 className="font-semibold text-slate-900">{plan.name}</h4>
                    <div className="mt-4">
                      <span className="text-3xl font-bold text-slate-900">
                        {formatCurrency(plan.price_monthly, plan.currency)}
                      </span>
                      <span className="text-slate-500">/month</span>
                    </div>
                    <p className="text-sm text-slate-500 mt-1">
                      or {formatCurrency(plan.price_yearly, plan.currency)}/year (save 17%)
                    </p>
                    <ul className="mt-6 space-y-3">
                      <li className="flex items-center gap-2 text-sm text-slate-600">
                        <CheckCircle className="w-4 h-4 text-green-500" />
                        Up to {plan.max_users} users
                      </li>
                      {plan.features.map((feature, i) => (
                        <li key={i} className="flex items-center gap-2 text-sm text-slate-600">
                          <CheckCircle className="w-4 h-4 text-green-500" />
                          {feature}
                        </li>
                      ))}
                    </ul>
                    <button
                      className={`btn w-full mt-6 ${plan.is_current ? 'btn-secondary' : 'btn-primary'}`}
                      disabled={plan.is_current}
                    >
                      {plan.is_current ? 'Current Plan' : 'Upgrade'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Security Tab */}
        {activeTab === 'security' && (
          <div className="max-w-2xl">
            <h3 className="text-lg font-semibold text-slate-900 mb-6">Security Settings</h3>
            <div className="space-y-6">
              <div className="card p-6">
                <h4 className="font-medium text-slate-900 mb-4">Password Policy</h4>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-slate-700">Minimum Password Length</p>
                      <p className="text-sm text-slate-500">Set minimum characters required</p>
                    </div>
                    <select className="select w-24">
                      <option>8</option>
                      <option>10</option>
                      <option>12</option>
                    </select>
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-slate-700">Require Special Characters</p>
                      <p className="text-sm text-slate-500">Must include symbols like !@#$%</p>
                    </div>
                    <button className="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent bg-primary-600 transition-colors duration-200 ease-in-out focus:outline-none">
                      <span className="translate-x-5 inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"></span>
                    </button>
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-slate-700">Two-Factor Authentication</p>
                      <p className="text-sm text-slate-500">Require 2FA for all users</p>
                    </div>
                    <button className="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent bg-slate-200 transition-colors duration-200 ease-in-out focus:outline-none">
                      <span className="translate-x-0 inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"></span>
                    </button>
                  </div>
                </div>
              </div>

              <div className="card p-6">
                <h4 className="font-medium text-slate-900 mb-4">Session Settings</h4>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-slate-700">Session Timeout</p>
                      <p className="text-sm text-slate-500">Auto logout after inactivity</p>
                    </div>
                    <select className="select w-32">
                      <option>30 minutes</option>
                      <option>1 hour</option>
                      <option>2 hours</option>
                      <option>4 hours</option>
                    </select>
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-slate-700">Remember Me Duration</p>
                      <p className="text-sm text-slate-500">How long to remember logged-in users</p>
                    </div>
                    <select className="select w-32">
                      <option>7 days</option>
                      <option>14 days</option>
                      <option>30 days</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Notifications Tab */}
        {activeTab === 'notifications' && (
          <div className="max-w-2xl">
            <h3 className="text-lg font-semibold text-slate-900 mb-6">Notification Preferences</h3>
            <div className="card p-6">
              <div className="space-y-6">
                {[
                  { label: 'Email Notifications', desc: 'Receive updates via email' },
                  { label: 'Push Notifications', desc: 'Browser push notifications' },
                  { label: 'Low Stock Alerts', desc: 'Alert when inventory is low' },
                  { label: 'Payment Reminders', desc: 'Upcoming and overdue payments' },
                  { label: 'New Order Notifications', desc: 'Alert for new sales orders' },
                  { label: 'Weekly Summary', desc: 'Weekly business summary email' },
                ].map((item, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-slate-700">{item.label}</p>
                      <p className="text-sm text-slate-500">{item.desc}</p>
                    </div>
                    <button className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                      i < 3 ? 'bg-primary-600' : 'bg-slate-200'
                    }`}>
                      <span className={`${i < 3 ? 'translate-x-5' : 'translate-x-0'} inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out`}></span>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Appearance Tab */}
        {activeTab === 'appearance' && (
          <div className="max-w-2xl">
            <h3 className="text-lg font-semibold text-slate-900 mb-6">Appearance Settings</h3>
            <div className="space-y-6">
              <div className="card p-6">
                <h4 className="font-medium text-slate-900 mb-4">Theme</h4>
                <div className="grid grid-cols-3 gap-4">
                  {['Light', 'Dark', 'System'].map((theme) => (
                    <button
                      key={theme}
                      className={`p-4 rounded-lg border-2 text-center ${
                        theme === 'Light' ? 'border-primary-500 bg-primary-50' : 'border-slate-200'
                      }`}
                    >
                      <div className={`w-12 h-8 mx-auto rounded ${
                        theme === 'Dark' ? 'bg-slate-800' : theme === 'System' ? 'bg-gradient-to-r from-white to-slate-800' : 'bg-white border border-slate-200'
                      }`} />
                      <p className="text-sm font-medium text-slate-700 mt-2">{theme}</p>
                    </button>
                  ))}
                </div>
              </div>

              <div className="card p-6">
                <h4 className="font-medium text-slate-900 mb-4">Language & Region</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Language</label>
                    <select className="select w-full">
                      <option>English</option>
                      <option>العربية</option>
                      <option>Français</option>
                      <option>Español</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Date Format</label>
                    <select className="select w-full">
                      <option>MM/DD/YYYY</option>
                      <option>DD/MM/YYYY</option>
                      <option>YYYY-MM-DD</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Integrations Tab */}
        {activeTab === 'integrations' && (
          <div>
            <h3 className="text-lg font-semibold text-slate-900 mb-6">Integrations</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                { name: 'Stripe', desc: 'Payment processing', status: 'connected' },
                { name: 'QuickBooks', desc: 'Accounting sync', status: 'disconnected' },
                { name: 'Slack', desc: 'Team notifications', status: 'connected' },
                { name: 'Mailchimp', desc: 'Email marketing', status: 'disconnected' },
                { name: 'Google Workspace', desc: 'Calendar & Drive', status: 'connected' },
                { name: 'Zapier', desc: 'Automation workflows', status: 'disconnected' },
              ].map((integration) => (
                <div key={integration.name} className="card p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-slate-100 rounded-lg flex items-center justify-center">
                        <Zap className="w-6 h-6 text-slate-400" />
                      </div>
                      <div>
                        <p className="font-medium text-slate-900">{integration.name}</p>
                        <p className="text-sm text-slate-500">{integration.desc}</p>
                      </div>
                    </div>
                    {integration.status === 'connected' ? (
                      <button className="btn btn-secondary btn-sm">
                        Configure
                      </button>
                    ) : (
                      <button className="btn btn-primary btn-sm">
                        Connect
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Backup Tab */}
        {activeTab === 'backup' && (
          <div className="max-w-2xl">
            <h3 className="text-lg font-semibold text-slate-900 mb-6">Backup & Restore</h3>
            <div className="space-y-6">
              <div className="card p-6">
                <h4 className="font-medium text-slate-900 mb-4">Create Backup</h4>
                <p className="text-sm text-slate-500 mb-4">
                  Download a complete backup of your data including all settings, customers, products, and transactions.
                </p>
                <button className="btn btn-primary">
                  <Database className="w-4 h-4" />
                  Create Backup
                </button>
              </div>

              <div className="card p-6">
                <h4 className="font-medium text-slate-900 mb-4">Recent Backups</h4>
                <div className="space-y-3">
                  {[
                    { date: '2024-01-15 10:30 AM', size: '125 MB', type: 'Automatic' },
                    { date: '2024-01-14 10:30 AM', size: '124 MB', type: 'Automatic' },
                    { date: '2024-01-13 02:15 PM', size: '123 MB', type: 'Manual' },
                  ].map((backup, i) => (
                    <div key={i} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
                      <div>
                        <p className="text-sm font-medium text-slate-700">{backup.date}</p>
                        <p className="text-xs text-slate-500">{backup.type} • {backup.size}</p>
                      </div>
                      <div className="flex gap-2">
                        <button className="btn btn-secondary btn-sm">Download</button>
                        <button className="btn btn-secondary btn-sm">Restore</button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="card p-6 border-red-200 bg-red-50">
                <h4 className="font-medium text-red-900 mb-2">Danger Zone</h4>
                <p className="text-sm text-red-700 mb-4">
                  Restore from a backup file. This will replace all current data.
                </p>
                <button className="btn btn-danger">
                  <Upload className="w-4 h-4" />
                  Restore from File
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
