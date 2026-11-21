/**
 * Premium Area Chart Component
 * with gradient fill and smooth animations
 */

import type React from 'react'
import {
  Area,
  AreaChart as RechartsAreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { clsx } from 'clsx'
import { colors } from '@/styles/tokens'

export interface AreaChartProps {
  data: Array<Record<string, any>>
  dataKey: string
  xAxisKey?: string
  height?: number
  color?: string
  gradientId?: string
  showGrid?: boolean
  showAxis?: boolean
  showTooltip?: boolean
  animated?: boolean
  strokeWidth?: number
  className?: string
  formatValue?: (value: number) => string
  formatLabel?: (label: string) => string
}

const CustomTooltip = ({
  active,
  payload,
  label,
  formatValue,
  formatLabel,
}: any) => {
  if (!active || !payload || !payload.length) return null

  return (
    <div className="bg-white px-4 py-3 rounded-xl shadow-lg border border-slate-100">
      <p className="text-sm font-medium text-slate-900">
        {formatLabel ? formatLabel(label) : label}
      </p>
      {payload.map((entry: any, index: number) => (
        <p key={index} className="text-sm text-slate-600 mt-1">
          <span className="font-medium" style={{ color: entry.color }}>
            {formatValue ? formatValue(entry.value) : entry.value.toLocaleString()}
          </span>
        </p>
      ))}
    </div>
  )
}

export const AreaChart: React.FC<AreaChartProps> = ({
  data,
  dataKey,
  xAxisKey = 'name',
  height = 300,
  color = colors.primary[500],
  gradientId = 'areaGradient',
  showGrid = true,
  showAxis = true,
  showTooltip = true,
  animated = true,
  strokeWidth = 2,
  className,
  formatValue,
  formatLabel,
}) => {
  return (
    <div className={clsx('w-full', className)} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RechartsAreaChart
          data={data}
          margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop
                offset="0%"
                stopColor={color}
                stopOpacity={0.3}
              />
              <stop
                offset="100%"
                stopColor={color}
                stopOpacity={0}
              />
            </linearGradient>
          </defs>

          {showGrid && (
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={colors.neutral[200]}
              vertical={false}
            />
          )}

          {showAxis && (
            <>
              <XAxis
                dataKey={xAxisKey}
                axisLine={false}
                tickLine={false}
                tick={{ fill: colors.neutral[500], fontSize: 12 }}
                dy={10}
                tickFormatter={formatLabel}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: colors.neutral[500], fontSize: 12 }}
                dx={-10}
                tickFormatter={formatValue}
              />
            </>
          )}

          {showTooltip && (
            <Tooltip
              content={<CustomTooltip formatValue={formatValue} formatLabel={formatLabel} />}
            />
          )}

          <Area
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            strokeWidth={strokeWidth}
            fill={`url(#${gradientId})`}
            isAnimationActive={animated}
            animationDuration={animated ? 1000 : 0}
            animationEasing="ease-out"
          />
        </RechartsAreaChart>
      </ResponsiveContainer>
    </div>
  )
}

export default AreaChart
