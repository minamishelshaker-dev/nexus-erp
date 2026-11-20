/**
 * Premium Notification Center Component
 * Real-time notifications with categories, badges, and actions
 */

import React, { useState, useRef, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { clsx } from 'clsx'
import {
  Bell,
  BellOff,
  Check,
  CheckCheck,
  X,
  AlertCircle,
  CheckCircle,
  Info,
  AlertTriangle,
  Trash2,
  Settings,
  MoreVertical,
  Clock,
} from 'lucide-react'
import { format, formatDistanceToNow, isToday, isYesterday } from 'date-fns'

// ========================================
// Types
// ========================================

export type NotificationType = 'alert' | 'success' | 'info' | 'warning'
export type NotificationPriority = 'high' | 'medium' | 'low'

export interface Notification {
  id: string
  title: string
  message: string
  type: NotificationType
  priority?: NotificationPriority
  isRead?: boolean
  timestamp: Date | string
  actionUrl?: string
  actionLabel?: string
  category?: string
  avatar?: string
  sender?: string
}

export interface NotificationCenterProps {
  notifications?: Notification[]
  onMarkAsRead?: (id: string) => void
  onMarkAllAsRead?: () => void
  onDelete?: (id: string) => void
  onClearAll?: () => void
  onActionClick?: (notification: Notification) => void
  onSettingsClick?: () => void
  maxVisible?: number
  showUnreadBadge?: boolean
}

// ========================================
// Notification Icons
// ========================================

const notificationIcons: Record<NotificationType, React.ReactNode> = {
  alert: <AlertCircle className="w-5 h-5 text-danger-500" />,
  success: <CheckCircle className="w-5 h-5 text-success-500" />,
  info: <Info className="w-5 h-5 text-info-500" />,
  warning: <AlertTriangle className="w-5 h-5 text-warning-500" />,
}

const notificationBgColors: Record<NotificationType, string> = {
  alert: 'bg-danger-50 dark:bg-danger-900/20',
  success: 'bg-success-50 dark:bg-success-900/20',
  info: 'bg-info-50 dark:bg-info-900/20',
  warning: 'bg-warning-50 dark:bg-warning-900/20',
}

// ========================================
// Mock Data
// ========================================

const mockNotifications: Notification[] = [
  {
    id: '1',
    title: 'New Order Received',
    message: 'Order #SO-2024-1234 has been placed by Acme Corp for $15,000',
    type: 'success',
    priority: 'high',
    timestamp: new Date(Date.now() - 5 * 60 * 1000),
    category: 'Orders',
    actionUrl: '/sales/orders/SO-2024-1234',
    actionLabel: 'View Order',
  },
  {
    id: '2',
    title: 'Low Stock Alert',
    message: 'Product SKU-001 is running low (5 units remaining)',
    type: 'warning',
    priority: 'high',
    timestamp: new Date(Date.now() - 30 * 60 * 1000),
    category: 'Inventory',
    actionUrl: '/inventory/products/SKU-001',
    actionLabel: 'Reorder',
  },
  {
    id: '3',
    title: 'Payment Received',
    message: 'Payment of $8,500 received from Tech Solutions Inc.',
    type: 'info',
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
    category: 'Finance',
  },
  {
    id: '4',
    title: 'System Maintenance',
    message: 'Scheduled maintenance tonight from 2:00 AM to 4:00 AM EST',
    type: 'alert',
    priority: 'medium',
    timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000),
    category: 'System',
  },
  {
    id: '5',
    title: 'Report Generated',
    message: 'Your monthly sales report is ready for download',
    type: 'success',
    timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000),
    category: 'Reports',
    actionUrl: '/reports/monthly-sales',
    actionLabel: 'Download',
  },
]

// ========================================
// Format Timestamp
// ========================================

const formatTimestamp = (timestamp: Date | string): string => {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / (1000 * 60))
  
  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  
  if (isToday(date)) return `Today at ${format(date, 'h:mm a')}`
  if (isYesterday(date)) return `Yesterday at ${format(date, 'h:mm a')}`
  
  return format(date, 'MMM d, h:mm a')
}

// ========================================
// Notification Item Component
// ========================================

interface NotificationItemProps {
  notification: Notification
  onMarkAsRead?: () => void
  onDelete?: () => void
  onActionClick?: () => void
}

const NotificationItem: React.FC<NotificationItemProps> = ({
  notification,
  onMarkAsRead,
  onDelete,
  onActionClick,
}) => {
  const [showActions, setShowActions] = useState(false)

  return (
    <div
      className={clsx(
        'group relative px-4 py-3 transition-colors duration-150',
        'hover:bg-slate-50 dark:hover:bg-slate-700/50',
        !notification.isRead && 'bg-primary-50/50 dark:bg-primary-900/10'
      )}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <div className="flex gap-3">
        {/* Icon */}
        <div
          className={clsx(
            'flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center',
            notificationBgColors[notification.type]
          )}
        >
          {notificationIcons[notification.type]}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <p className={clsx(
              'text-sm font-medium text-slate-900 dark:text-white',
              !notification.isRead && 'font-semibold'
            )}>
              {notification.title}
            </p>
            <span className="flex-shrink-0 text-xs text-slate-500 dark:text-slate-400">
              {formatTimestamp(notification.timestamp)}
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400 line-clamp-2">
            {notification.message}
          </p>
          
          {/* Category & Action */}
          <div className="flex items-center gap-2 mt-2">
            {notification.category && (
              <span className="text-xs text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded">
                {notification.category}
              </span>
            )}
            {notification.actionUrl && notification.actionLabel && (
              <button
                onClick={onActionClick}
                className="text-xs text-primary-600 dark:text-primary-400 font-medium hover:underline"
              >
                {notification.actionLabel}
              </button>
            )}
          </div>
        </div>

        {/* Actions */}
        <div
          className={clsx(
            'flex-shrink-0 flex items-center gap-1 transition-opacity duration-150',
            showActions ? 'opacity-100' : 'opacity-0'
          )}
        >
          {!notification.isRead && (
            <button
              onClick={onMarkAsRead}
              className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-600 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
              title="Mark as read"
            >
              <Check className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={onDelete}
            className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-600 text-slate-400 hover:text-danger-500"
            title="Delete"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Unread indicator */}
      {!notification.isRead && (
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-primary-500 rounded-r" />
      )}
    </div>
  )
}

// ========================================
// Notification Center Component
// ========================================

export const NotificationCenter: React.FC<NotificationCenterProps> = ({
  notifications = mockNotifications,
  onMarkAsRead,
  onMarkAllAsRead,
  onDelete,
  onClearAll,
  onActionClick,
  onSettingsClick,
  maxVisible = 10,
  showUnreadBadge = true,
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [filter, setFilter] = useState<'all' | 'unread'>('all')
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)

  // Calculate unread count
  const unreadCount = notifications.filter(n => !n.isRead).length

  // Get unique categories
  const categories = [...new Set(notifications.map(n => n.category).filter(Boolean))]

  // Filter notifications
  const filteredNotifications = notifications
    .filter(n => filter === 'all' || !n.isRead)
    .filter(n => !categoryFilter || n.category === categoryFilter)
    .slice(0, maxVisible)

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        buttonRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div className="relative">
      {/* Bell Button */}
      <button
        ref={buttonRef}
        onClick={() => setIsOpen(!isOpen)}
        className={clsx(
          'relative p-2.5 rounded-xl',
          'text-slate-600 dark:text-slate-400',
          'hover:bg-slate-100 dark:hover:bg-slate-800',
          'transition-colors duration-200',
          isOpen && 'bg-slate-100 dark:bg-slate-800'
        )}
        aria-label="Notifications"
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <Bell className="w-5 h-5" />
        {showUnreadBadge && unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-5 h-5 bg-danger-500 text-white text-xs font-bold rounded-full flex items-center justify-center animate-scale-in">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {isOpen && createPortal(
        <div
          ref={dropdownRef}
          className="fixed right-4 top-16 w-96 max-w-[calc(100vw-2rem)] z-[1060]"
          style={{
            position: 'fixed',
          }}
        >
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-700 overflow-hidden animate-slide-down">
            {/* Header */}
            <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-slate-900 dark:text-white">
                  Notifications
                </h3>
                <div className="flex items-center gap-1">
                  {unreadCount > 0 && (
                    <button
                      onClick={onMarkAllAsRead}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700"
                      title="Mark all as read"
                    >
                      <CheckCheck className="w-4 h-4" />
                    </button>
                  )}
                  <button
                    onClick={onSettingsClick}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700"
                    title="Settings"
                  >
                    <Settings className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Filters */}
              <div className="flex items-center gap-2 mt-3">
                <button
                  onClick={() => setFilter('all')}
                  className={clsx(
                    'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
                    filter === 'all'
                      ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400'
                      : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
                  )}
                >
                  All
                </button>
                <button
                  onClick={() => setFilter('unread')}
                  className={clsx(
                    'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
                    filter === 'unread'
                      ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400'
                      : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
                  )}
                >
                  Unread ({unreadCount})
                </button>
                {categories.length > 0 && (
                  <select
                    value={categoryFilter || ''}
                    onChange={(e) => setCategoryFilter(e.target.value || null)}
                    className="flex-1 px-2 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-600 dark:text-slate-300"
                  >
                    <option value="">All categories</option>
                    {categories.map(cat => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                )}
              </div>
            </div>

            {/* Notification List */}
            <div className="max-h-96 overflow-y-auto">
              {filteredNotifications.length === 0 ? (
                <div className="px-4 py-8 text-center">
                  <BellOff className="w-10 h-10 text-slate-300 mx-auto mb-3" />
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    No notifications
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-slate-100 dark:divide-slate-700">
                  {filteredNotifications.map((notification) => (
                    <NotificationItem
                      key={notification.id}
                      notification={notification}
                      onMarkAsRead={() => onMarkAsRead?.(notification.id)}
                      onDelete={() => onDelete?.(notification.id)}
                      onActionClick={() => onActionClick?.(notification)}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            {notifications.length > 0 && (
              <div className="px-4 py-3 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                <button
                  onClick={onClearAll}
                  className="w-full flex items-center justify-center gap-2 py-2 text-sm text-slate-600 dark:text-slate-400 hover:text-danger-600 dark:hover:text-danger-400 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  Clear all notifications
                </button>
              </div>
            )}
          </div>
        </div>,
        document.body
      )}
    </div>
  )
}

// ========================================
// Toast Notification Component
// ========================================

export interface ToastNotificationProps {
  notification: Notification
  onClose?: () => void
  autoClose?: boolean
  duration?: number
}

export const ToastNotification: React.FC<ToastNotificationProps> = ({
  notification,
  onClose,
  autoClose = true,
  duration = 5000,
}) => {
  useEffect(() => {
    if (autoClose && onClose) {
      const timer = setTimeout(onClose, duration)
      return () => clearTimeout(timer)
    }
  }, [autoClose, duration, onClose])

  return (
    <div
      className={clsx(
        'flex items-start gap-3 p-4 rounded-xl shadow-lg',
        'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700',
        'animate-slide-right'
      )}
      role="alert"
    >
      <div className={clsx(
        'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
        notificationBgColors[notification.type]
      )}>
        {notificationIcons[notification.type]}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-slate-900 dark:text-white">
          {notification.title}
        </p>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          {notification.message}
        </p>
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className="flex-shrink-0 p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-400"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  )
}

export default NotificationCenter
