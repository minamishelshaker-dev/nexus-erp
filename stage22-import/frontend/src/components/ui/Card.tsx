/**
 * Nexus ERP Card Component
 * Premium Card with animations and variants
 */

import React from 'react'
import { clsx } from 'clsx'

export type CardVariant = 'default' | 'hover' | 'interactive' | 'glass' | 'gradient'
export type CardPadding = 'none' | 'sm' | 'md' | 'lg'

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant
  padding?: CardPadding
  isAnimated?: boolean
  children: React.ReactNode
}

const variantStyles: Record<CardVariant, string> = {
  default: 'bg-white border border-slate-200',
  hover: 'bg-white border border-slate-200 hover:-translate-y-0.5 hover:shadow-lg',
  interactive: `
    bg-white border border-slate-200 
    hover:-translate-y-0.5 hover:shadow-lg 
    cursor-pointer active:translate-y-0
  `,
  glass: 'bg-white/80 backdrop-blur-md border border-white/20',
  gradient: `
    bg-gradient-to-br from-white via-slate-50 to-white 
    border border-slate-200/50
  `,
}

const paddingStyles: Record<CardPadding, string> = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  (
    {
      variant = 'default',
      padding = 'none',
      isAnimated = true,
      className,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <div
        ref={ref}
        className={clsx(
          // Base styles
          'rounded-2xl',
          // Shadow
          'shadow-[0_1px_3px_rgba(0,0,0,0.05),0_4px_12px_rgba(0,0,0,0.05)]',
          // Variant styles
          variantStyles[variant],
          // Padding
          paddingStyles[padding],
          // Animation
          isAnimated && 'transition-all duration-200 ease-out',
          // Custom className
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }
)

Card.displayName = 'Card'

// Card Header
export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string
  description?: string
  action?: React.ReactNode
}

export const CardHeader: React.FC<CardHeaderProps> = ({
  title,
  description,
  action,
  className,
  children,
  ...props
}) => {
  return (
    <div
      className={clsx(
        'px-6 py-4 border-b border-slate-100',
        'flex items-center justify-between',
        className
      )}
      {...props}
    >
      {(title || description) ? (
        <div>
          {title && <h3 className="text-lg font-semibold text-slate-900">{title}</h3>}
          {description && <p className="text-sm text-slate-500 mt-0.5">{description}</p>}
        </div>
      ) : (
        children
      )}
      {action && <div className="flex-shrink-0">{action}</div>}
    </div>
  )
}

// Card Body
export interface CardBodyProps extends React.HTMLAttributes<HTMLDivElement> {
  padding?: CardPadding
}

export const CardBody: React.FC<CardBodyProps> = ({
  padding = 'md',
  className,
  children,
  ...props
}) => {
  return (
    <div className={clsx(paddingStyles[padding], className)} {...props}>
      {children}
    </div>
  )
}

// Card Footer
export interface CardFooterProps extends React.HTMLAttributes<HTMLDivElement> {}

export const CardFooter: React.FC<CardFooterProps> = ({
  className,
  children,
  ...props
}) => {
  return (
    <div
      className={clsx(
        'px-6 py-4 border-t border-slate-100',
        'bg-slate-50/50 rounded-b-2xl',
        'flex items-center justify-end gap-3',
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

// Stat Card
export interface StatCardProps {
  title: string
  value: string | number
  change?: {
    value: string
    type: 'positive' | 'negative' | 'neutral'
  }
  icon?: React.ReactNode
  iconVariant?: 'primary' | 'success' | 'warning' | 'danger' | 'info'
  trend?: {
    data: number[]
    color?: string
  }
  className?: string
}

const iconVariantStyles: Record<string, string> = {
  primary: 'bg-primary-100 text-primary-600',
  success: 'bg-success-100 text-success-600',
  warning: 'bg-warning-100 text-warning-600',
  danger: 'bg-danger-100 text-danger-600',
  info: 'bg-info-100 text-info-600',
}

const changeStyles: Record<string, string> = {
  positive: 'text-success-600',
  negative: 'text-danger-600',
  neutral: 'text-slate-500',
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  change,
  icon,
  iconVariant = 'primary',
  className,
}) => {
  return (
    <Card variant="hover" padding="md" className={className}>
      <div className="flex items-start justify-between">
        {icon && (
          <div
            className={clsx(
              'w-12 h-12 rounded-xl flex items-center justify-center',
              iconVariantStyles[iconVariant]
            )}
          >
            {icon}
          </div>
        )}
        {change && (
          <span
            className={clsx(
              'inline-flex items-center gap-1 text-sm font-medium',
              changeStyles[change.type]
            )}
          >
            {change.value}
          </span>
        )}
      </div>
      <div className="mt-4">
        <p className="text-3xl font-bold text-slate-900 tracking-tight">{value}</p>
        <p className="text-sm font-medium text-slate-500 mt-1">{title}</p>
      </div>
    </Card>
  )
}

// Card Title
export interface CardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {}

export const CardTitle: React.FC<CardTitleProps> = ({
  className,
  children,
  ...props
}) => {
  return (
    <h3 className={clsx('text-lg font-semibold text-slate-900', className)} {...props}>
      {children}
    </h3>
  )
}

// Card Description
export interface CardDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {}

export const CardDescription: React.FC<CardDescriptionProps> = ({
  className,
  children,
  ...props
}) => {
  return (
    <p className={clsx('text-sm text-slate-500 mt-1', className)} {...props}>
      {children}
    </p>
  )
}

export default Card
