/**
 * Nexus ERP Button Component
 * Premium Button with multiple variants and sizes
 */

import React from 'react'
import { clsx } from 'clsx'
import { Loader2 } from 'lucide-react'

export type ButtonVariant = 
  | 'primary' 
  | 'secondary' 
  | 'outline' 
  | 'ghost' 
  | 'success' 
  | 'danger' 
  | 'warning'
  | 'link'

export type ButtonSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  isLoading?: boolean
  isFullWidth?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
  children: React.ReactNode
}

const variantStyles: Record<ButtonVariant, string> = {
  primary: `
    bg-gradient-to-r from-primary-600 to-primary-500 text-white
    hover:from-primary-700 hover:to-primary-600
    active:from-primary-800 active:to-primary-700
    focus-visible:ring-primary-500
    shadow-lg shadow-primary-500/25 
    hover:shadow-xl hover:shadow-primary-500/30
  `,
  secondary: `
    bg-slate-100 text-slate-700 
    hover:bg-slate-200 active:bg-slate-300
    focus-visible:ring-slate-400
  `,
  outline: `
    bg-transparent border-2 border-slate-300 text-slate-700
    hover:bg-slate-50 hover:border-slate-400
    active:bg-slate-100
  `,
  ghost: `
    bg-transparent text-slate-600
    hover:bg-slate-100 hover:text-slate-900
    active:bg-slate-200
  `,
  success: `
    bg-gradient-to-r from-success-600 to-success-500 text-white
    hover:from-success-700 hover:to-success-600
    active:from-success-800 active:to-success-700
    focus-visible:ring-success-500
    shadow-lg shadow-success-500/25
  `,
  danger: `
    bg-gradient-to-r from-danger-600 to-danger-500 text-white
    hover:from-danger-700 hover:to-danger-600
    active:from-danger-800 active:to-danger-700
    focus-visible:ring-danger-500
    shadow-lg shadow-danger-500/25
  `,
  warning: `
    bg-gradient-to-r from-warning-600 to-warning-500 text-white
    hover:from-warning-700 hover:to-warning-600
    active:from-warning-800 active:to-warning-700
    focus-visible:ring-warning-500
    shadow-lg shadow-warning-500/25
  `,
  link: `
    bg-transparent text-primary-600 underline-offset-4
    hover:underline hover:text-primary-700
    active:text-primary-800
  `,
}

const sizeStyles: Record<ButtonSize, string> = {
  xs: 'px-2.5 py-1 text-xs rounded-lg gap-1.5',
  sm: 'px-3.5 py-2 text-sm rounded-xl gap-1.5',
  md: 'px-4 py-2.5 text-sm rounded-xl gap-2',
  lg: 'px-6 py-3 text-base rounded-xl gap-2',
  xl: 'px-8 py-4 text-lg rounded-2xl gap-2.5',
}

const iconSizeStyles: Record<ButtonSize, string> = {
  xs: 'p-1.5',
  sm: 'p-2',
  md: 'p-2.5',
  lg: 'p-3',
  xl: 'p-4',
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      isLoading = false,
      isFullWidth = false,
      leftIcon,
      rightIcon,
      className,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || isLoading

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={clsx(
          // Base styles
          'inline-flex items-center justify-center font-medium',
          'transition-all duration-200',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
          // Variant styles
          variantStyles[variant],
          // Size styles
          sizeStyles[size],
          // Full width
          isFullWidth && 'w-full',
          // Animation
          'active:scale-[0.98]',
          // Custom className
          className
        )}
        {...props}
      >
        {isLoading ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <>
            {leftIcon && <span className="flex-shrink-0">{leftIcon}</span>}
            <span>{children}</span>
            {rightIcon && <span className="flex-shrink-0">{rightIcon}</span>}
          </>
        )}
      </button>
    )
  }
)

Button.displayName = 'Button'

// Icon Button variant
export interface IconButtonProps extends Omit<ButtonProps, 'leftIcon' | 'rightIcon' | 'children'> {
  icon: React.ReactNode
  'aria-label': string
}

export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ icon, size = 'md', className, ...props }, ref) => {
    return (
      <Button
        ref={ref}
        size={size}
        className={clsx(iconSizeStyles[size], 'p-2.5', className)}
        {...props}
      >
        {icon}
      </Button>
    )
  }
)

IconButton.displayName = 'IconButton'

export default Button
