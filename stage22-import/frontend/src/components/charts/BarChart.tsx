/**
 * Premium Bar Chart Component
 * with animations and tooltips
 */

import React from 'react'
import {
  Bar,
  BarChart as RechartsBarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Cell,
} from 'recharts'
import { clsx } from 'clsx'
import { colors } from '@/styles/tokens'

export interface BarChartProps {
  data: Array<Record<string, any>>
  dataKey: string
  xAxisKey?: string
  height?: number
  color?: string
  colors?: string[]
  showGrid?: boolean
  showAxis?: boolean
  showTooltip?: boolean
  animated?: boolean
  radius?: number | [number, number, number, number]
  className?: string
  layout?: 'horizontal' | 'vertical'
  barSize?: number
  formatValue?: (value: number) => string
  formatLabel?: (label: string) => string
  onBarClick?: (data: any, index: number) => void
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
          <span
            className="inline-block w-2 h-2 rounded-full mr-2"
            style={{ backgroundColor: entry.color }}
          />
          <span className="font-medium">
            {formatValue ? formatValue(entry.value) : entry.value.toLocaleString()}
          </span>
        </p>
      ))}
    </div>
  )
}

export const BarChart: React.FC<BarChartProps> = ({
  data,
  dataKey,
  xAxisKey = 'name',
  height = 300,
  color = colors.primary[500],
  colors: barColors,
  showGrid = true,
  showAxis = true,
  showTooltip = true,
  animated = true,
  radius = [8, 8, 0, 0],
  className,
  layout = 'horizontal',
  barSize = 32,
  formatValue,
  formatLabel,
  onBarClick,
}) => {
  const defaultRadius = layout === 'horizontal' ? [8, 8, 0, 0] : [0, 8, 8, 0]
  const chartRadius = typeof radius === 'number' ? radius : defaultRadius

  return (
    <div className={clsx('w-full', className)} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RechartsBarChart
          data={data}
          layout={layout}
          margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
        >
          {showGrid && (
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={colors.neutral[200]}
              vertical={layout === 'horizontal'}
              horizontal={layout === 'vertical'}
            />
          )}

          {showAxis && layout === 'horizontal' && (
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

          {showAxis && layout === 'vertical' && (
            <>
              <XAxis
                type="number"
                axisLine={false}
                tickLine={false}
                tick={{ fill: colors.neutral[500], fontSize: 12 }}
                tickFormatter={formatValue}
              />
              <YAxis
                type="category"
                dataKey={xAxisKey}
                axisLine={false}
                tickLine={false}
                tick={{ fill: colors.neutral[500], fontSize: 12 }}
                tickFormatter={formatLabel}
              />
            </>
          )}

          {showTooltip && (
            <Tooltip
              content={<CustomTooltip formatValue={formatValue} formatLabel={formatLabel} />}
              cursor={{ fill: colors.neutral[100], radius: 8 }}
            />
          )}

          <Bar
            dataKey={dataKey}
            fill={color}
            radius={chartRadius as any}
            barSize={barSize}
            isAnimationActive={animated}
            animationDuration={animated ? 800 : 0}
            animationEasing="ease-out"
            onClick={onBarClick}
          >
            {barColors &&
              data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={barColors[index % barColors.length]} />
              ))}
          </Bar>
        </RechartsBarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default BarChart
