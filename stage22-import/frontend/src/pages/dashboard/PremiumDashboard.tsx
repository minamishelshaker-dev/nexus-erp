/**
 * Premium Dashboard Component
 * Modern KPI cards with trends, sparklines, AI insights
 * Revenue chart, activity feed, quick actions, and command palette trigger
 */

import React, { useState, useMemo } from 'react'
import { clsx } from 'clsx'
import {
  DollarSign,
  Users,
  ShoppingCart,
  Package,
  TrendingUp,
  TrendingDown,
  AlertCircle,
  Clock,
  Plus,
  FileText,
  BarChart3,
  Sparkles,
  ArrowUpRight,
  ArrowDownRight,
  ChevronRight,
  Calendar,
  Activity,
  Zap,
  Target,
} from 'lucide-react'
import { AreaChart, BarChart, PieChart, PieChartLegend, MetricCard } from '@/components/charts'
import { colors } from '@/styles/tokens'
import { format, formatDistanceToNow } from 'date-fns'

// ========================================
// Types
// ========================================

interface KPIMetric {
  id: string
  title: string
  value: string | number
  prefix?: string
  suffix?: string
  change: {
    value: string
    type: 'positive' | 'negative' | 'neutral'
    label: string
  }
  trend: number[]
  icon: React.ReactNode
  iconVariant: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'info'
}

interface Activity {
  id: string
  type: 'order' | 'customer' | 'product' | 'payment' | 'alert'
  title: string
  description: string
  timestamp: Date
  amount?: string
  status?: string
}

interface AIInsight {
  id: string
  type: 'opportunity' | 'warning' | 'info'
  title: string
  description: string
  impact: string
  action?: string
}

// ========================================
// Mock Data
// ========================================

const kpiMetrics: KPIMetric[] = [
  {
    id: 'revenue',
    title: 'Total Revenue',
    value: '1,234,567',
    prefix: '$',
    change: { value: '+12.5%', type: 'positive', label: 'vs last month' },
    trend: [65, 72, 68, 85, 92, 88, 95, 102, 98, 110, 115, 120],
    icon: <DollarSign className="w-6 h-6" />,
    iconVariant: 'primary',
  },
  {
    id: 'customers',
    title: 'Active Customers',
    value: '2,847',
    change: { value: '+8.2%', type: 'positive', label: 'new this month' },
    trend: [42, 48, 52, 58, 62, 65, 68, 72, 78, 82, 85, 88],
    icon: <Users className="w-6 h-6" />,
    iconVariant: 'secondary',
  },
  {
    id: 'orders',
    title: 'Open Orders',
    value: '156',
    change: { value: '-3.1%', type: 'negative', label: 'vs last week' },
    trend: [32, 28, 35, 42, 38, 45, 52, 48, 55, 50, 58, 52],
    icon: <ShoppingCart className="w-6 h-6" />,
    iconVariant: 'info',
  },
  {
    id: 'inventory',
    title: 'Low Stock Items',
    value: '23',
    change: { value: '+5', type: 'negative', label: 'items need reorder' },
    trend: [12, 15, 18, 16, 20, 22, 18, 24, 21, 23, 25, 23],
    icon: <AlertCircle className="w-6 h-6" />,
    iconVariant: 'warning',
  },
]

const recentActivities: Activity[] = [
  {
    id: '1',
    type: 'order',
    title: 'New order #SO-2024-1234',
    description: 'Placed by Acme Corp',
    timestamp: new Date(Date.now() - 5 * 60 * 1000),
    amount: '$15,000',
    status: 'pending',
  },
  {
    id: '2',
    type: 'payment',
    title: 'Payment received',
    description: 'From Tech Solutions Inc.',
    timestamp: new Date(Date.now() - 15 * 60 * 1000),
    amount: '$8,500',
    status: 'completed',
  },
  {
    id: '3',
    type: 'customer',
    title: 'New customer registered',
    description: 'Global Industries LLC',
    timestamp: new Date(Date.now() - 45 * 60 * 1000),
  },
  {
    id: '4',
    type: 'product',
    title: 'Product stock updated',
    description: 'SKU-001 restocked',
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
    amount: '+500 units',
  },
  {
    id: '5',
    type: 'alert',
    title: 'Low stock alert',
    description: 'SKU-002 below threshold',
    timestamp: new Date(Date.now() - 3 * 60 * 60 * 1000),
    status: 'warning',
  },
]

const aiInsights: AIInsight[] = [
  {
    id: '1',
    type: 'opportunity',
    title: 'Revenue Opportunity',
    description: 'Based on current trends, you could increase monthly revenue by 15% by focusing on the top 3 product categories.',
    impact: '+$185,000 potential',
    action: 'View recommendations',
  },
  {
    id: '2',
    type: 'warning',
    title: 'Inventory Alert',
    description: '5 products are predicted to run out of stock within the next 7 days based on current sales velocity.',
    impact: 'Potential stockouts',
    action: 'Review inventory',
  },
  {
    id: '3',
    type: 'info',
    title: 'Customer Insight',
    description: 'Your customer retention rate has improved by 8% this quarter. Consider expanding your loyalty program.',
    impact: '+320 retained customers',
  },
]

const revenueData = [
  { name: 'Jan', value: 65000 },
  { name: 'Feb', value: 72000 },
  { name: 'Mar', value: 68000 },
  { name: 'Apr', value: 85000 },
  { name: 'May', value: 92000 },
  { name: 'Jun', value: 88000 },
  { name: 'Jul', value: 95000 },
  { name: 'Aug', value: 102000 },
  { name: 'Sep', value: 98000 },
  { name: 'Oct', value: 110000 },
  { name: 'Nov', value: 115000 },
  { name: 'Dec', value: 120000 },
]

const salesByCategory = [
  { name: 'Electronics', value: 450000, color: colors.primary[500] },
  { name: 'Furniture', value: 280000, color: colors.secondary[500] },
  { name: 'Clothing', value: 195000, color: colors.accent[500] },
  { name: 'Food & Beverage', value: 165000, color: colors.success[500] },
  { name: 'Other', value: 145000, color: colors.neutral[400] },
]

const weeklyOrders = [
  { name: 'Mon', value: 45 },
  { name: 'Tue', value: 52 },
  { name: 'Wed', value: 48 },
  { name: 'Thu', value: 61 },
  { name: 'Fri', value: 55 },
  { name: 'Sat', value: 38 },
  { name: 'Sun', value: 32 },
]

// ========================================
// Activity Icon
// ========================================

const getActivityIcon = (type: Activity['type']) => {
  const icons = {
    order: <ShoppingCart className="w-4 h-4" />,
    customer: <Users className="w-4 h-4" />,
    product: <Package className="w-4 h-4" />,
    payment: <DollarSign className="w-4 h-4" />,
    alert: <AlertCircle className="w-4 h-4" />,
  }
  return icons[type]
}

const getActivityColor = (type: Activity['type']) => {
  const colorMap = {
    order: 'bg-primary-100 text-primary-600',
    customer: 'bg-secondary-100 text-secondary-600',
    product: 'bg-info-100 text-info-600',
    payment: 'bg-success-100 text-success-600',
    alert: 'bg-warning-100 text-warning-600',
  }
  return colorMap[type]
}

// ========================================
// Quick Actions
// ========================================

const quickActions = [
  { id: 'new-order', label: 'New Order', icon: <ShoppingCart className="w-5 h-5" />, color: 'primary' },
  { id: 'new-customer', label: 'Add Customer', icon: <Users className="w-5 h-5" />, color: 'secondary' },
  { id: 'new-product', label: 'Add Product', icon: <Package className="w-5 h-5" />, color: 'info' },
  { id: 'new-report', label: 'Create Report', icon: <FileText className="w-5 h-5" />, color: 'success' },
]

// ========================================
// Premium Dashboard Component
// ========================================

export const PremiumDashboard: React.FC = () => {
  const [selectedPeriod, setSelectedPeriod] = useState<'week' | 'month' | 'year'>('month')

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            Dashboard
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            Welcome back! Here's what's happening with your business.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Period Selector */}
          <div className="flex items-center bg-white dark:bg-slate-800 rounded-xl p-1 border border-slate-200 dark:border-slate-700">
            {(['week', 'month', 'year'] as const).map((period) => (
              <button
                key={period}
                onClick={() => setSelectedPeriod(period)}
                className={clsx(
                  'px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200',
                  selectedPeriod === period
                    ? 'bg-primary-500 text-white shadow-sm'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                )}
              >
                {period.charAt(0).toUpperCase() + period.slice(1)}
              </button>
            ))}
          </div>
          <button className="btn btn-primary">
            <Plus className="w-4 h-4" />
            New Order
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {kpiMetrics.map((metric) => (
          <MetricCard
            key={metric.id}
            title={metric.title}
            value={metric.value}
            prefix={metric.prefix}
            suffix={metric.suffix}
            change={metric.change}
            sparkline={{ data: metric.trend, color: colors[metric.iconVariant][500] }}
            icon={metric.icon}
            iconVariant={metric.iconVariant}
          />
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Revenue Chart */}
        <div className="lg:col-span-2 bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                Revenue Overview
              </h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                Monthly revenue for the current year
              </p>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <span className="flex items-center gap-1 text-success-600">
                <TrendingUp className="w-4 h-4" />
                +12.5%
              </span>
              <span className="text-slate-500 dark:text-slate-400">vs last year</span>
            </div>
          </div>
          <AreaChart
            data={revenueData}
            dataKey="value"
            height={300}
            color={colors.primary[500]}
            gradientId="revenueGradient"
            formatValue={(v) => formatCurrency(v)}
          />
        </div>

        {/* Sales by Category */}
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
              Sales by Category
            </h3>
            <button className="text-sm text-primary-600 dark:text-primary-400 font-medium hover:underline">
              View all
            </button>
          </div>
          <PieChart
            data={salesByCategory}
            height={200}
            innerRadius={50}
            outerRadius={80}
            formatValue={(v) => formatCurrency(v)}
          />
          <div className="mt-4">
            <PieChartLegend data={salesByCategory} formatValue={(v) => formatCurrency(v)} />
          </div>
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* AI Insights Panel */}
        <div className="bg-gradient-to-br from-primary-600 to-primary-700 rounded-2xl p-6 text-white">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles className="w-5 h-5" />
            <h3 className="font-semibold">AI Insights</h3>
          </div>
          <div className="space-y-4">
            {aiInsights.map((insight) => (
              <div
                key={insight.id}
                className="bg-white/10 backdrop-blur-sm rounded-xl p-4"
              >
                <div className="flex items-start gap-3">
                  <div
                    className={clsx(
                      'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
                      insight.type === 'opportunity' && 'bg-success-400/20 text-success-300',
                      insight.type === 'warning' && 'bg-warning-400/20 text-warning-300',
                      insight.type === 'info' && 'bg-info-400/20 text-info-300'
                    )}
                  >
                    {insight.type === 'opportunity' && <Target className="w-4 h-4" />}
                    {insight.type === 'warning' && <AlertCircle className="w-4 h-4" />}
                    {insight.type === 'info' && <Activity className="w-4 h-4" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-white">{insight.title}</p>
                    <p className="text-sm text-white/80 mt-1">{insight.description}</p>
                    <div className="flex items-center justify-between mt-3">
                      <span className="text-xs font-medium bg-white/20 px-2 py-1 rounded">
                        {insight.impact}
                      </span>
                      {insight.action && (
                        <button className="text-sm font-medium text-white hover:underline flex items-center gap-1">
                          {insight.action}
                          <ChevronRight className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <button className="w-full mt-4 py-2 text-sm font-medium text-white/80 hover:text-white border border-white/20 rounded-xl hover:bg-white/10 transition-colors">
            View all insights
          </button>
        </div>

        {/* Recent Activity */}
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
              Recent Activity
            </h3>
            <button className="text-sm text-primary-600 dark:text-primary-400 font-medium hover:underline">
              View all
            </button>
          </div>
          <div className="space-y-4">
            {recentActivities.map((activity) => (
              <div
                key={activity.id}
                className="flex items-start gap-3 py-2"
              >
                <div
                  className={clsx(
                    'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
                    getActivityColor(activity.type)
                  )}
                >
                  {getActivityIcon(activity.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-900 dark:text-white">
                    {activity.title}
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {activity.description}
                  </p>
                </div>
                <div className="flex-shrink-0 text-right">
                  {activity.amount && (
                    <p className="text-sm font-medium text-slate-900 dark:text-white">
                      {activity.amount}
                    </p>
                  )}
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {formatDistanceToNow(activity.timestamp, { addSuffix: true })}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Actions & Weekly Orders */}
        <div className="space-y-6">
          {/* Quick Actions */}
          <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-6">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
              Quick Actions
            </h3>
            <div className="grid grid-cols-2 gap-3">
              {quickActions.map((action) => (
                <button
                  key={action.id}
                  className={clsx(
                    'flex flex-col items-center justify-center gap-2 p-4 rounded-xl',
                    'border border-slate-200 dark:border-slate-700',
                    'hover:bg-slate-50 dark:hover:bg-slate-700',
                    'transition-colors duration-200',
                    'group'
                  )}
                >
                  <div
                    className={clsx(
                      'w-10 h-10 rounded-xl flex items-center justify-center',
                      action.color === 'primary' && 'bg-primary-100 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400',
                      action.color === 'secondary' && 'bg-secondary-100 text-secondary-600 dark:bg-secondary-900/30 dark:text-secondary-400',
                      action.color === 'info' && 'bg-info-100 text-info-600 dark:bg-info-900/30 dark:text-info-400',
                      action.color === 'success' && 'bg-success-100 text-success-600 dark:bg-success-900/30 dark:text-success-400',
                      'group-hover:scale-110 transition-transform duration-200'
                    )}
                  >
                    {action.icon}
                  </div>
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                    {action.label}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Weekly Orders */}
          <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                Weekly Orders
              </h3>
              <span className="text-sm text-slate-500 dark:text-slate-400">
                Total: 331
              </span>
            </div>
            <BarChart
              data={weeklyOrders}
              dataKey="value"
              xAxisKey="name"
              height={150}
              color={colors.primary[500]}
              showAxis={false}
              showGrid={false}
              barSize={24}
            />
          </div>
        </div>
      </div>

      {/* Command Palette Hint */}
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50">
        <div className="flex items-center gap-2 px-4 py-2 bg-slate-900 dark:bg-slate-800 text-white rounded-full shadow-lg text-sm">
          <Zap className="w-4 h-4 text-warning-400" />
          <span>Press</span>
          <kbd className="px-2 py-0.5 bg-slate-700 rounded text-xs font-mono">⌘K</kbd>
          <span>to open command palette</span>
        </div>
      </div>
    </div>
  )
}

export default PremiumDashboard
