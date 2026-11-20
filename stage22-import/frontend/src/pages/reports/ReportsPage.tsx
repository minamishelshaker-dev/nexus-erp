/**
 * Nexus ERP - Reports Page
 * Report center with various report categories
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../../services/api'
import {
  FileText,
  TrendingUp,
  DollarSign,
  Package,
  Users,
  PieChart,
  BarChart3,
  Calendar,
  Download,
  Eye,
  Clock,
  FileBarChart,
  Building2,
  ShoppingCart,
  Briefcase,
  Activity,
} from 'lucide-react'

interface ReportCategory {
  id: string
  name: string
  description: string
  icon: string
  reports: Report[]
}

interface Report {
  id: string
  name: string
  description: string
  type: 'standard' | 'custom' | 'scheduled'
  last_run?: string
  is_favorite: boolean
}

const iconMap: Record<string, React.FC<{ className?: string }>> = {
  FileText,
  TrendingUp,
  DollarSign,
  Package,
  Users,
  PieChart,
  BarChart3,
}

export default function ReportsPage() {
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [dateRange, setDateRange] = useState({ from: '', to: '' })

  // Fetch report categories
  const { data: categories, isLoading } = useQuery({
    queryKey: ['report-categories'],
    queryFn: async () => {
      const response = await api.get('/reports/categories')
      return response.data as ReportCategory[]
    },
  })

  // Fetch recent reports
  const { data: recentReports } = useQuery({
    queryKey: ['recent-reports'],
    queryFn: async () => {
      const response = await api.get('/reports/recent')
      return response.data as Report[]
    },
  })

  // Fetch scheduled reports
  const { data: scheduledReports } = useQuery({
    queryKey: ['scheduled-reports'],
    queryFn: async () => {
      const response = await api.get('/reports/scheduled')
      return response.data as Report[]
    },
  })

  const defaultCategories: ReportCategory[] = [
    {
      id: 'financial',
      name: 'Financial Reports',
      description: 'Balance sheets, P&L, cash flow statements',
      icon: 'DollarSign',
      reports: [
        { id: 'balance-sheet', name: 'Balance Sheet', description: 'Assets, liabilities, and equity', type: 'standard', is_favorite: true },
        { id: 'profit-loss', name: 'Profit & Loss Statement', description: 'Revenue and expenses overview', type: 'standard', is_favorite: true },
        { id: 'cash-flow', name: 'Cash Flow Statement', description: 'Cash movements analysis', type: 'standard', is_favorite: false },
        { id: 'trial-balance', name: 'Trial Balance', description: 'Account balances summary', type: 'standard', is_favorite: false },
        { id: 'general-ledger', name: 'General Ledger', description: 'Complete transaction history', type: 'standard', is_favorite: false },
      ],
    },
    {
      id: 'sales',
      name: 'Sales Reports',
      description: 'Sales analysis and customer insights',
      icon: 'TrendingUp',
      reports: [
        { id: 'sales-summary', name: 'Sales Summary', description: 'Overall sales performance', type: 'standard', is_favorite: true },
        { id: 'sales-by-customer', name: 'Sales by Customer', description: 'Customer-wise sales breakdown', type: 'standard', is_favorite: false },
        { id: 'sales-by-product', name: 'Sales by Product', description: 'Product-wise sales analysis', type: 'standard', is_favorite: false },
        { id: 'sales-by-region', name: 'Sales by Region', description: 'Geographic sales distribution', type: 'standard', is_favorite: false },
        { id: 'ar-aging', name: 'AR Aging Report', description: 'Receivables aging analysis', type: 'standard', is_favorite: true },
      ],
    },
    {
      id: 'inventory',
      name: 'Inventory Reports',
      description: 'Stock levels and movements',
      icon: 'Package',
      reports: [
        { id: 'stock-levels', name: 'Stock Levels', description: 'Current inventory status', type: 'standard', is_favorite: true },
        { id: 'stock-valuation', name: 'Stock Valuation', description: 'Inventory value analysis', type: 'standard', is_favorite: false },
        { id: 'stock-movement', name: 'Stock Movement', description: 'Inventory transactions', type: 'standard', is_favorite: false },
        { id: 'low-stock', name: 'Low Stock Report', description: 'Items below reorder point', type: 'standard', is_favorite: true },
        { id: 'slow-moving', name: 'Slow Moving Items', description: 'Dead stock analysis', type: 'standard', is_favorite: false },
      ],
    },
    {
      id: 'purchasing',
      name: 'Purchasing Reports',
      description: 'Purchase orders and supplier analysis',
      icon: 'ShoppingCart',
      reports: [
        { id: 'purchase-summary', name: 'Purchase Summary', description: 'Overall purchasing activity', type: 'standard', is_favorite: false },
        { id: 'supplier-performance', name: 'Supplier Performance', description: 'Supplier metrics analysis', type: 'standard', is_favorite: false },
        { id: 'ap-aging', name: 'AP Aging Report', description: 'Payables aging analysis', type: 'standard', is_favorite: true },
        { id: 'purchase-by-supplier', name: 'Purchases by Supplier', description: 'Supplier-wise breakdown', type: 'standard', is_favorite: false },
      ],
    },
    {
      id: 'hr',
      name: 'HR Reports',
      description: 'Employee and payroll reports',
      icon: 'Users',
      reports: [
        { id: 'employee-list', name: 'Employee List', description: 'Complete employee directory', type: 'standard', is_favorite: false },
        { id: 'attendance-summary', name: 'Attendance Summary', description: 'Attendance statistics', type: 'standard', is_favorite: true },
        { id: 'payroll-summary', name: 'Payroll Summary', description: 'Payroll costs overview', type: 'standard', is_favorite: true },
        { id: 'leave-report', name: 'Leave Report', description: 'Leave balances and usage', type: 'standard', is_favorite: false },
      ],
    },
    {
      id: 'projects',
      name: 'Project Reports',
      description: 'Project progress and billing',
      icon: 'Briefcase',
      reports: [
        { id: 'project-summary', name: 'Project Summary', description: 'Project status overview', type: 'standard', is_favorite: false },
        { id: 'time-report', name: 'Time Report', description: 'Hours logged analysis', type: 'standard', is_favorite: false },
        { id: 'profitability', name: 'Project Profitability', description: 'Revenue vs costs', type: 'standard', is_favorite: true },
      ],
    },
  ]

  const displayCategories = categories || defaultCategories
  const filteredCategories = selectedCategory === 'all' 
    ? displayCategories 
    : displayCategories.filter(c => c.id === selectedCategory)

  const runReport = (reportId: string) => {
    window.location.href = `/reports/${reportId}`
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Reports</h1>
          <p className="text-slate-500 mt-1">Generate and manage business reports</p>
        </div>
        <Link
          to="/reports/builder"
          className="btn btn-primary"
        >
          <FileBarChart className="w-4 h-4" />
          Custom Report
        </Link>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <FileText className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Total Reports</p>
              <p className="text-xl font-bold text-slate-900">
                {displayCategories.reduce((sum, c) => sum + c.reports.length, 0)}
              </p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <Activity className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Run Today</p>
              <p className="text-xl font-bold text-slate-900">{recentReports?.length || 0}</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <Clock className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Scheduled</p>
              <p className="text-xl font-bold text-slate-900">{scheduledReports?.length || 0}</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center">
              <PieChart className="w-5 h-5 text-yellow-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Categories</p>
              <p className="text-xl font-bold text-slate-900">{displayCategories.length}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Category Filter */}
      <div className="card p-4">
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setSelectedCategory('all')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              selectedCategory === 'all'
                ? 'bg-primary-600 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            All Categories
          </button>
          {displayCategories.map((category) => {
            const IconComponent = iconMap[category.icon] || FileText
            return (
              <button
                key={category.id}
                onClick={() => setSelectedCategory(category.id)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                  selectedCategory === category.id
                    ? 'bg-primary-600 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                <IconComponent className="w-4 h-4" />
                {category.name}
              </button>
            )
          })}
        </div>
      </div>

      {/* Reports Grid */}
      {isLoading ? (
        <div className="card p-12 text-center">
          <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto" />
          <p className="text-slate-500 mt-4">Loading reports...</p>
        </div>
      ) : (
        <div className="space-y-6">
          {filteredCategories.map((category) => {
            const IconComponent = iconMap[category.icon] || FileText
            return (
              <div key={category.id} className="card overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                      <IconComponent className="w-5 h-5 text-primary-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-900">{category.name}</h3>
                      <p className="text-sm text-slate-500">{category.description}</p>
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-slate-100">
                  {category.reports.map((report) => (
                    <div
                      key={report.id}
                      className="bg-white p-4 hover:bg-slate-50 transition-colors cursor-pointer"
                      onClick={() => runReport(report.id)}
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="font-medium text-slate-900">{report.name}</h4>
                            {report.is_favorite && (
                              <span className="text-yellow-500">★</span>
                            )}
                          </div>
                          <p className="text-sm text-slate-500 mt-0.5">{report.description}</p>
                          {report.last_run && (
                            <p className="text-xs text-slate-400 mt-2">
                              Last run: {new Date(report.last_run).toLocaleDateString()}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-1">
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              runReport(report.id)
                            }}
                            className="p-1.5 hover:bg-slate-200 rounded"
                            title="Run Report"
                          >
                            <Eye className="w-4 h-4 text-slate-400" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              // Download logic
                            }}
                            className="p-1.5 hover:bg-slate-200 rounded"
                            title="Download"
                          >
                            <Download className="w-4 h-4 text-slate-400" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Scheduled Reports */}
      {scheduledReports && scheduledReports.length > 0 && (
        <div className="card overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100">
            <h3 className="font-semibold text-slate-900">Scheduled Reports</h3>
            <p className="text-sm text-slate-500">Auto-generated reports</p>
          </div>
          <div className="divide-y divide-slate-100">
            {scheduledReports.map((report) => (
              <div key={report.id} className="px-6 py-4 flex items-center justify-between hover:bg-slate-50">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
                    <Clock className="w-4 h-4 text-purple-600" />
                  </div>
                  <div>
                    <p className="font-medium text-slate-900">{report.name}</p>
                    <p className="text-sm text-slate-500">{report.description}</p>
                  </div>
                </div>
                <button className="btn btn-secondary btn-sm">
                  View Schedule
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
