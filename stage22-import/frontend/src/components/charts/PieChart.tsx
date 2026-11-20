/**
 * Premium Pie Chart Component
 * with tooltips and animations
 */

import React, { useState } from 'react'
import {
  Pie,
  PieChart as RechartsPieChart,
  ResponsiveContainer,
  Tooltip,
  Cell,
} from 'recharts'
import { clsx } from 'clsx'
import { colors } from '@/styles/tokens'

export interface PieChartProps {
  data: Array<{
    name: string
    value: number
    color?: string
  }>
  height?: number
  innerRadius?: number | string
  outerRadius?: number | string
  paddingAngle?: number
  showTooltip?: boolean
  showLabels?: boolean
  animated?: boolean
  className?: string
  formatValue?: (value: number) => string
  onSliceClick?: (data: any, index: number) => void
}

const defaultColors = [
  colors.primary[500],
  colors.secondary[500],
  colors.accent[500],
  colors.success[500],
  colors.warning[500],
  colors.danger[500],
  colors.info[500],
  colors.chart.purple,
  colors.chart.pink,
  colors.chart.indigo,
]

const CustomTooltip = ({
  active,
  payload,
  formatValue,
}: any) => {
  if (!active || !payload || !payload.length) return null

  const data = payload[0].payload

  return (
    <div className="bg-white px-4 py-3 rounded-xl shadow-lg border border-slate-100">
      <div className="flex items-center gap-2">
        <span
          className="w-3 h-3 rounded-full"
          style={{ backgroundColor: data.color || payload[0].color }}
        />
        <p className="text-sm font-medium text-slate-900">{data.name}</p>
      </div>
      <p className="text-sm text-slate-600 mt-1">
        <span className="font-medium">
          {formatValue ? formatValue(data.value) : data.value.toLocaleString()}
        </span>
      </p>
    </div>
  )
}

interface RenderLabelProps {
  cx: number
  cy: number
  midAngle: number
  innerRadius: number
  outerRadius: number
  percent: number
  name: string
}

const renderCustomLabel = ({
  cx,
  cy,
  midAngle,
  innerRadius,
  outerRadius,
  percent,
  name,
}: RenderLabelProps) => {
  const RADIAN = Math.PI / 180
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5 + 30
  const x = cx + radius * Math.cos(-midAngle * RADIAN)
  const y = cy + radius * Math.sin(-midAngle * RADIAN)

  if (percent < 0.05) return null

  return (
    <text
      x={x}
      y={y}
      fill={colors.neutral[700]}
      textAnchor={x > cx ? 'start' : 'end'}
      dominantBaseline="central"
      className="text-xs font-medium"
    >
      {name} ({(percent * 100).toFixed(0)}%)
    </text>
  )
}

export const PieChart: React.FC<PieChartProps> = ({
  data,
  height = 300,
  innerRadius = 60,
  outerRadius = 100,
  paddingAngle = 2,
  showTooltip = true,
  showLabels = false,
  animated = true,
  className,
  formatValue,
  onSliceClick,
}) => {
  const [activeIndex, setActiveIndex] = useState<number | null>(null)

  const handleMouseEnter = (_: any, index: number) => {
    setActiveIndex(index)
  }

  const handleMouseLeave = () => {
    setActiveIndex(null)
  }

  return (
    <div className={clsx('w-full', className)} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RechartsPieChart>
          {showTooltip && (
            <Tooltip content={<CustomTooltip formatValue={formatValue} />} />
          )}
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={innerRadius}
            outerRadius={activeIndex !== null ? (outerRadius as number) + 5 : outerRadius}
            paddingAngle={paddingAngle}
            dataKey="value"
            label={showLabels ? renderCustomLabel : false}
            labelLine={showLabels}
            isAnimationActive={animated}
            animationDuration={animated ? 800 : 0}
            animationEasing="ease-out"
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            onClick={onSliceClick}
          >
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.color || defaultColors[index % defaultColors.length]}
                stroke={activeIndex === index ? colors.neutral[900] : 'transparent'}
                strokeWidth={activeIndex === index ? 2 : 0}
                style={{
                  filter: activeIndex === index ? 'brightness(1.1)' : 'none',
                  transition: 'all 0.2s ease-out',
                  cursor: onSliceClick ? 'pointer' : 'default',
                }}
              />
            ))}
          </Pie>
        </RechartsPieChart>
      </ResponsiveContainer>
    </div>
  )
}

// Legend component for PieChart
export interface PieChartLegendProps {
  data: Array<{
    name: string
    value: number
    color?: string
  }>
  className?: string
  formatValue?: (value: number) => string
}

export const PieChartLegend: React.FC<PieChartLegendProps> = ({
  data,
  className,
  formatValue,
}) => {
  const total = data.reduce((sum, item) => sum + item.value, 0)

  return (
    <div className={clsx('space-y-2', className)}>
      {data.map((item, index) => (
        <div
          key={item.name}
          className="flex items-center justify-between py-1.5"
        >
          <div className="flex items-center gap-2">
            <span
              className="w-3 h-3 rounded-full flex-shrink-0"
              style={{ backgroundColor: item.color || defaultColors[index % defaultColors.length] }}
            />
            <span className="text-sm text-slate-700">{item.name}</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-slate-900">
              {formatValue ? formatValue(item.value) : item.value.toLocaleString()}
            </span>
            <span className="text-xs text-slate-500 w-12 text-right">
              {((item.value / total) * 100).toFixed(1)}%
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}

export default PieChart
