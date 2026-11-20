/**
 * Premium Metric Card Component
 * KPI card with sparkline and trend indicators
 */

import React from 'react'
import { clsx } from 'clsx'
import {
  TrendingUp,
  TrendingDown,
  Minus,
  MoreHorizontal,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react'
import { colors } from '@/styles/tokens'
import { Area, AreaChart, ResponsiveContainer } from 'recharts'

export interface MetricCardProps {
  title: string
  value: string | number
  change?: {
    value: string | number
    type: 'positive' | 'negative' | 'neutral'
    label?: string
  }
  sparkline?: {
    data: number[]
    color?: string
  }
  icon?: React.ReactNode
  iconVariant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'info'
  variant?: 'default' | 'compact' | 'featured'
  className?: string
  onClick?: () => void
  action?: React.ReactNode
  prefix?: string
  suffix?: string
  loading?: boolean
}

const iconVariantStyles: Record<string, string> = {
  primary: 'bg-primary-100 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400',
  secondary: 'bg-secondary-100 text-secondary-600 dark:bg-secondary-900/30 dark:text-secondary-400',
  success: 'bg-success-100 text-success-600 dark:bg-success-900/30 dark:text-success-400',
  warning: 'bg-warning-100 text-warning-600 dark:bg-warning-900/30 dark:text-warning-400',
  danger: 'bg-danger-100 text-danger-600 dark:bg-danger-900/30 dark:text-danger-400',
  info: 'bg-info-100 text-info-600 dark:bg-info-900/30 dark:text-info-400',
}

const changeStyles: Record<string, { text: string; bg: string; icon: React.ReactNode }> = {
  positive: {
    text: 'text-success-600 dark:text-success-400',
    bg: 'bg-success-50 dark:bg-success-900/20',
    icon: <ArrowUpRight className="w-3.5 h-3.5" />,
  },
  negative: {
    text: 'text-danger-600 dark:text-danger-400',
    bg: 'bg-danger-50 dark:bg-danger-900/20',
    icon: <ArrowDownRight className="w-3.5 h-3.5" />,
  },
  neutral: {
    text: 'text-slate-600 dark:text-slate-400',
    bg: 'bg-slate-50 dark:bg-slate-800',
    icon: <Minus className="w-3.5 h-3.5" />,
  },
}

// Mini sparkline component
const Sparkline: React.FC<{
  data: number[]
  color?: string
}> = ({ data, color = colors.primary[500] }) => {
  const chartData = data.map((value, index) => ({ value, index }))

  return (
    <div className="w-full h-12">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
          <defs>
            <linearGradient id={`sparklineGradient-${color}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.3} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#sparklineGradient-${color})`}
            isAnimationActive={true}
            animationDuration={1000}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

// Loading skeleton
const Skeleton: React.FC = () => (
  <div className="animate-pulse space-y-3">
    <div className="h-4 w-20 bg-slate-200 dark:bg-slate-700 rounded" />
    <div className="h-8 w-32 bg-slate-200 dark:bg-slate-700 rounded" />
    <div className="h-3 w-16 bg-slate-200 dark:bg-slate-700 rounded" />
  </div>
)

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  change,
  sparkline,
  icon,
  iconVariant = 'primary',
  variant = 'default',
  className,
  onClick,
  action,
  prefix,
  suffix,
  loading = false,
}) => {
  const changeStyle = change ? changeStyles[change.type] : null

  if (loading) {
    return (
      <div
        className={clsx(
          'bg-white dark:bg-slate-800 rounded-2xl p-6',
          'border border-slate-200 dark:border-slate-700',
          className
        )}
      >
        <Skeleton />
      </div>
    )
  }

  return (
    <div
      className={clsx(
        // Base styles
        'bg-white dark:bg-slate-800 rounded-2xl',
        'border border-slate-200 dark:border-slate-700',
        'shadow-[0_1px_3px_rgba(0,0,0,0.05),0_4px_12px_rgba(0,0,0,0.05)]',
        // Hover effects
        'transition-all duration-200 ease-out',
        onClick && 'cursor-pointer hover:-translate-y-0.5 hover:shadow-lg',
        // Padding based on variant
        variant === 'compact' ? 'p-4' : 'p-6',
        className
      )}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          {icon && (
            <div
              className={clsx(
                'w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0',
                iconVariantStyles[iconVariant]
              )}
            >
              {icon}
            </div>
          )}
          <span className="text-sm font-medium text-slate-500 dark:text-slate-400">
            {title}
          </span>
        </div>
        {action && (
          <div className="flex-shrink-0">{action}</div>
        )}
      </div>

      {/* Value */}
      <div className="mb-3">
        <div className="flex items-baseline gap-1">
          {prefix && (
            <span className="text-lg font-medium text-slate-500 dark:text-slate-400">
              {prefix}
            </span>
          )}
          <span className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">
            {typeof value === 'number' ? value.toLocaleString() : value}
          </span>
          {suffix && (
            <span className="text-lg font-medium text-slate-500 dark:text-slate-400">
              {suffix}
            </span>
          )}
        </div>
      </div>

      {/* Change indicator */}
      {change && changeStyle && (
        <div className="flex items-center gap-2 mb-3">
          <span
            className={clsx(
              'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
              changeStyle.text,
              changeStyle.bg
            )}
          >
            {changeStyle.icon}
            {change.value}
          </span>
          {change.label && (
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {change.label}
            </span>
          )}
        </div>
      )}

      {/* Sparkline */}
      {sparkline && (
        <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-700">
          <Sparkline data={sparkline.data} color={sparkline.color} />
        </div>
      )}
    </div>
  )
}

// Compact metric card for dashboards
export interface CompactMetricProps {
  title: string
  value: string | number
  change?: string
  trend?: 'up' | 'down' | 'neutral'
  className?: string
}

export const CompactMetric: React.FC<CompactMetricProps> = ({
  title,
  value,
  change,
  trend = 'neutral',
  className,
}) => {
  const trendIcons = {
    up: <TrendingUp className="w-4 h-4 text-success-500" />,
    down: <TrendingDown className="w-4 h-4 text-danger-500" />,
    neutral: <Minus className="w-4 h-4 text-slate-400" />,
  }

  return (
    <div
      className={clsx(
        'bg-white dark:bg-slate-800 rounded-xl p-4',
        'border border-slate-200 dark:border-slate-700',
        className
      )}
    >
      <p className="text-sm text-slate-500 dark:text-slate-400">{title}</p>
      <div className="flex items-end justify-between mt-1">
        <span className="text-2xl font-bold text-slate-900 dark:text-white">
          {value}
        </span>
        {change && (
          <div className="flex items-center gap-1 text-sm">
            {trendIcons[trend]}
            <span
              className={clsx(
                trend === 'up' && 'text-success-600',
                trend === 'down' && 'text-danger-600',
                trend === 'neutral' && 'text-slate-500'
              )}
            >
              {change}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

export default MetricCard
