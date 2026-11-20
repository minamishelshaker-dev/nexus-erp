/**
 * Premium Command Palette Component
 * Global search, quick navigation, action shortcuts
 * with fuzzy search and AI query integration
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { createPortal } from 'react-dom'
import { clsx } from 'clsx'
import { useHotkeys } from 'react-hotkeys-hook'
import {
  Search,
  Command,
  ArrowRight,
  Clock,
  File,
  Settings,
  Users,
  Package,
  ShoppingCart,
  BarChart3,
  HelpCircle,
  Moon,
  Sun,
  LogOut,
  Plus,
  Sparkles,
  Loader2,
  X,
} from 'lucide-react'

// ========================================
// Types
// ========================================

export interface CommandItem {
  id: string
  title: string
  description?: string
  icon?: React.ReactNode
  category: string
  shortcut?: string
  action?: () => void
  href?: string
  keywords?: string[]
  recent?: boolean
}

export interface CommandPaletteProps {
  commands?: CommandItem[]
  recentItems?: CommandItem[]
  onAIQuery?: (query: string) => Promise<void>
  onNavigate?: (href: string) => void
  onCommand?: (command: CommandItem) => void
  placeholder?: string
  isLoading?: boolean
}

// ========================================
// Default Commands
// ========================================

const defaultCommands: CommandItem[] = [
  // Navigation
  { id: 'nav-dashboard', title: 'Dashboard', icon: <BarChart3 className="w-4 h-4" />, category: 'Navigation', href: '/dashboard' },
  { id: 'nav-customers', title: 'Customers', icon: <Users className="w-4 h-4" />, category: 'Navigation', href: '/customers' },
  { id: 'nav-products', title: 'Products', icon: <Package className="w-4 h-4" />, category: 'Navigation', href: '/products' },
  { id: 'nav-orders', title: 'Sales Orders', icon: <ShoppingCart className="w-4 h-4" />, category: 'Navigation', href: '/sales/orders' },
  { id: 'nav-reports', title: 'Reports', icon: <File className="w-4 h-4" />, category: 'Navigation', href: '/reports' },
  
  // Actions
  { id: 'action-new-order', title: 'Create New Order', icon: <Plus className="w-4 h-4" />, category: 'Actions', shortcut: 'N' },
  { id: 'action-new-customer', title: 'Add Customer', icon: <Plus className="w-4 h-4" />, category: 'Actions', shortcut: 'C' },
  { id: 'action-new-product', title: 'Add Product', icon: <Plus className="w-4 h-4" />, category: 'Actions', shortcut: 'P' },
  
  // Settings
  { id: 'settings-general', title: 'Settings', icon: <Settings className="w-4 h-4" />, category: 'Settings', href: '/settings' },
  { id: 'settings-theme', title: 'Toggle Dark Mode', icon: <Moon className="w-4 h-4" />, category: 'Settings', shortcut: 'D' },
  { id: 'settings-help', title: 'Help & Support', icon: <HelpCircle className="w-4 h-4" />, category: 'Settings', href: '/help' },
  { id: 'settings-logout', title: 'Sign Out', icon: <LogOut className="w-4 h-4" />, category: 'Settings' },
]

// ========================================
// Fuzzy Search
// ========================================

const fuzzyMatch = (query: string, text: string): boolean => {
  const pattern = query.split('').map(char => {
    const escaped = char.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, '\\$&')
    return `${escaped}.*`
  }).join('')
  const regex = new RegExp(pattern, 'i')
  return regex.test(text)
}

const scoreMatch = (query: string, item: CommandItem): number => {
  const lowerQuery = query.toLowerCase()
  const lowerTitle = item.title.toLowerCase()
  const keywords = item.keywords?.map(k => k.toLowerCase()) || []
  
  // Exact match
  if (lowerTitle === lowerQuery) return 100
  
  // Starts with
  if (lowerTitle.startsWith(lowerQuery)) return 80
  
  // Contains
  if (lowerTitle.includes(lowerQuery)) return 60
  
  // Keywords match
  if (keywords.some(k => k.includes(lowerQuery))) return 50
  
  // Fuzzy match
  if (fuzzyMatch(lowerQuery, lowerTitle)) return 30
  
  // Description match
  if (item.description?.toLowerCase().includes(lowerQuery)) return 20
  
  return 0
}

// ========================================
// Command Palette Component
// ========================================

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  commands = defaultCommands,
  recentItems = [],
  onAIQuery,
  onNavigate,
  onCommand,
  placeholder = 'Search commands, ask AI...',
  isLoading = false,
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [isAIQuery, setIsAIQuery] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  // Open command palette with Cmd+K
  useHotkeys('mod+k', (e) => {
    e.preventDefault()
    setIsOpen(true)
  }, { enableOnContentEditable: true })

  // Close with Escape
  useHotkeys('escape', () => {
    if (isOpen) {
      setIsOpen(false)
      setQuery('')
    }
  }, { enableOnContentEditable: true }, [isOpen])

  // Focus input when opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  // Filter and sort commands
  const filteredCommands = useMemo(() => {
    if (!query) {
      // Show recent items first when no query
      const recentIds = recentItems.map(r => r.id)
      const nonRecentCommands = commands.filter(c => !recentIds.includes(c.id))
      return [...recentItems, ...nonRecentCommands]
    }

    // Check if it's an AI query (starts with ?)
    if (query.startsWith('?') && onAIQuery) {
      setIsAIQuery(true)
      return []
    }
    setIsAIQuery(false)

    // Score and filter commands
    const scored = commands
      .map(item => ({ item, score: scoreMatch(query, item) }))
      .filter(({ score }) => score > 0)
      .sort((a, b) => b.score - a.score)
      .map(({ item }) => item)

    return scored
  }, [query, commands, recentItems, onAIQuery])

  // Reset selection when filtered commands change
  useEffect(() => {
    setSelectedIndex(0)
  }, [filteredCommands])

  // Handle keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex(prev => 
          prev < filteredCommands.length - 1 ? prev + 1 : prev
        )
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex(prev => prev > 0 ? prev - 1 : prev)
        break
      case 'Enter':
        e.preventDefault()
        if (isAIQuery && onAIQuery) {
          onAIQuery(query.substring(1).trim())
          setIsOpen(false)
          setQuery('')
        } else if (filteredCommands[selectedIndex]) {
          handleSelect(filteredCommands[selectedIndex])
        }
        break
    }
  }, [filteredCommands, selectedIndex, isAIQuery, query, onAIQuery])

  // Handle command selection
  const handleSelect = useCallback((item: CommandItem) => {
    if (item.action) {
      item.action()
    } else if (item.href && onNavigate) {
      onNavigate(item.href)
    } else if (onCommand) {
      onCommand(item)
    }
    setIsOpen(false)
    setQuery('')
  }, [onNavigate, onCommand])

  // Scroll selected item into view
  useEffect(() => {
    if (listRef.current) {
      const selectedElement = listRef.current.children[selectedIndex] as HTMLElement
      if (selectedElement) {
        selectedElement.scrollIntoView({ block: 'nearest' })
      }
    }
  }, [selectedIndex])

  // Group commands by category
  const groupedCommands = useMemo(() => {
    const groups: Record<string, CommandItem[]> = {}
    filteredCommands.forEach(item => {
      if (!groups[item.category]) {
        groups[item.category] = []
      }
      groups[item.category].push(item)
    })
    return groups
  }, [filteredCommands])

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className={clsx(
          'flex items-center gap-2 px-3 py-2 rounded-xl',
          'bg-slate-100 dark:bg-slate-800',
          'text-slate-500 dark:text-slate-400',
          'hover:bg-slate-200 dark:hover:bg-slate-700',
          'transition-colors duration-200'
        )}
        aria-label="Open command palette"
      >
        <Search className="w-4 h-4" />
        <span className="text-sm hidden sm:inline">Search...</span>
        <kbd className="hidden sm:flex items-center gap-1 px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-700 text-xs font-medium">
          <Command className="w-3 h-3" />K
        </kbd>
      </button>
    )
  }

  return createPortal(
    <div
      className="fixed inset-0 z-[1090] flex items-start justify-center pt-[15vh]"
      onClick={() => {
        setIsOpen(false)
        setQuery('')
      }}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm animate-fade-in" />
      
      {/* Modal */}
      <div
        className="relative w-full max-w-xl mx-4 bg-white dark:bg-slate-800 rounded-2xl shadow-2xl overflow-hidden animate-scale-in"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
      >
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-200 dark:border-slate-700">
          {isAIQuery ? (
            <Sparkles className="w-5 h-5 text-primary-500 flex-shrink-0" />
          ) : (
            <Search className="w-5 h-5 text-slate-400 flex-shrink-0" />
          )}
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isAIQuery ? 'Ask AI anything...' : placeholder}
            className="flex-1 bg-transparent text-slate-900 dark:text-white placeholder:text-slate-400 outline-none text-base"
            autoComplete="off"
            autoFocus
          />
          {isLoading && (
            <Loader2 className="w-5 h-5 text-slate-400 animate-spin" />
          )}
          <kbd
            onClick={() => {
              setIsOpen(false)
              setQuery('')
            }}
            className="px-2 py-1 rounded bg-slate-100 dark:bg-slate-700 text-xs font-medium text-slate-500 cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-600"
          >
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div
          ref={listRef}
          className="max-h-[60vh] overflow-y-auto py-2"
        >
          {/* AI Query Result */}
          {isAIQuery && (
            <div className="px-4 py-8 text-center">
              <Sparkles className="w-8 h-8 text-primary-500 mx-auto mb-3" />
              <p className="text-sm text-slate-600 dark:text-slate-400">
                Press <kbd className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-xs font-medium">Enter</kbd> to ask AI
              </p>
            </div>
          )}

          {/* No results */}
          {!isAIQuery && filteredCommands.length === 0 && query && (
            <div className="px-4 py-8 text-center">
              <Search className="w-8 h-8 text-slate-300 mx-auto mb-3" />
              <p className="text-sm text-slate-600 dark:text-slate-400">
                No results found for "{query}"
              </p>
            </div>
          )}

          {/* Command groups */}
          {!isAIQuery && Object.entries(groupedCommands).map(([category, items]) => (
            <div key={category}>
              <div className="px-4 py-2 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                {category}
              </div>
              {items.map((item, index) => {
                const globalIndex = filteredCommands.indexOf(item)
                return (
                  <button
                    key={item.id}
                    className={clsx(
                      'w-full flex items-center gap-3 px-4 py-3 text-left',
                      'transition-colors duration-150',
                      selectedIndex === globalIndex
                        ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300'
                        : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/50'
                    )}
                    onClick={() => handleSelect(item)}
                    onMouseEnter={() => setSelectedIndex(globalIndex)}
                  >
                    {item.recent && (
                      <Clock className="w-3 h-3 text-slate-400 absolute ml-6 mt-1" />
                    )}
                    <span className={clsx(
                      'flex-shrink-0 w-5 h-5 flex items-center justify-center',
                      item.recent && 'opacity-50'
                    )}>
                      {item.icon}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{item.title}</p>
                      {item.description && (
                        <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                          {item.description}
                        </p>
                      )}
                    </div>
                    {item.shortcut && (
                      <kbd className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-xs font-medium text-slate-500 dark:text-slate-400">
                        {item.shortcut}
                      </kbd>
                    )}
                    <ArrowRight className="w-4 h-4 text-slate-400 opacity-0 group-hover:opacity-100" />
                  </button>
                )
              })}
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-2 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 text-xs text-slate-500">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <kbd className="px-1 py-0.5 rounded bg-slate-200 dark:bg-slate-700">↑↓</kbd>
              to navigate
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1 py-0.5 rounded bg-slate-200 dark:bg-slate-700">↵</kbd>
              to select
            </span>
          </div>
          <span className="flex items-center gap-1">
            <kbd className="px-1 py-0.5 rounded bg-slate-200 dark:bg-slate-700">?</kbd>
            for AI query
          </span>
        </div>
      </div>
    </div>,
    document.body
  )
}

export default CommandPalette
