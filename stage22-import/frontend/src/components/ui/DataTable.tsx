/**
 * Nexus ERP DataTable Component
 * Feature-rich data table with sorting, filtering, and pagination
 */

import React, { useState, useMemo } from 'react'
import { clsx } from 'clsx'
import {
  ChevronUp,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Search,
  Filter,
  MoreHorizontal,
} from 'lucide-react'
import { Button } from './Button'

export interface Column<T> {
  key: keyof T | string
  header: string
  sortable?: boolean
  render?: (value: any, row: T, index: number) => React.ReactNode
  className?: string
  width?: string | number
  align?: 'left' | 'center' | 'right'
}

export interface DataTableProps<T> {
  data: T[]
  columns: Column<T>[]
  keyField: keyof T
  pageSize?: number
  searchable?: boolean
  searchPlaceholder?: string
  emptyMessage?: string
  isLoading?: boolean
  onRowClick?: (row: T) => void
  className?: string
  actions?: (row: T) => React.ReactNode
  selectable?: boolean
  selectedRows?: T[]
  onSelectionChange?: (rows: T[]) => void
  stickyHeader?: boolean
}

type SortDirection = 'asc' | 'desc' | null

export function DataTable<T extends Record<string, any>>({
  data,
  columns,
  keyField,
  pageSize = 10,
  searchable = true,
  searchPlaceholder = 'Search...',
  emptyMessage = 'No data available',
  isLoading = false,
  onRowClick,
  className,
  actions,
  selectable = false,
  selectedRows = [],
  onSelectionChange,
  stickyHeader = false,
}: DataTableProps<T>) {
  const [currentPage, setCurrentPage] = useState(1)
  const [searchTerm, setSearchTerm] = useState('')
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<SortDirection>(null)

  // Filter data
  const filteredData = useMemo(() => {
    if (!searchTerm) return data

    return data.filter((row) =>
      columns.some((col) => {
        const value = row[col.key as keyof T]
        if (value === null || value === undefined) return false
        return String(value).toLowerCase().includes(searchTerm.toLowerCase())
      })
    )
  }, [data, searchTerm, columns])

  // Sort data
  const sortedData = useMemo(() => {
    if (!sortKey || !sortDirection) return filteredData

    return [...filteredData].sort((a, b) => {
      const aValue = a[sortKey]
      const bValue = b[sortKey]

      if (aValue === bValue) return 0
      if (aValue === null || aValue === undefined) return 1
      if (bValue === null || bValue === undefined) return -1

      const comparison = aValue < bValue ? -1 : 1
      return sortDirection === 'asc' ? comparison : -comparison
    })
  }, [filteredData, sortKey, sortDirection])

  // Paginate data
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    return sortedData.slice(start, start + pageSize)
  }, [sortedData, currentPage, pageSize])

  const totalPages = Math.ceil(sortedData.length / pageSize)

  // Handle sorting
  const handleSort = (key: string) => {
    if (sortKey === key) {
      if (sortDirection === 'asc') {
        setSortDirection('desc')
      } else if (sortDirection === 'desc') {
        setSortKey(null)
        setSortDirection(null)
      }
    } else {
      setSortKey(key)
      setSortDirection('asc')
    }
  }

  // Handle selection
  const handleSelectAll = () => {
    if (selectedRows.length === paginatedData.length) {
      onSelectionChange?.([])
    } else {
      onSelectionChange?.([...paginatedData])
    }
  }

  const handleSelectRow = (row: T) => {
    const isSelected = selectedRows.some(
      (selected) => selected[keyField] === row[keyField]
    )
    if (isSelected) {
      onSelectionChange?.(
        selectedRows.filter((selected) => selected[keyField] !== row[keyField])
      )
    } else {
      onSelectionChange?.([...selectedRows, row])
    }
  }

  // Render skeleton rows
  const renderSkeleton = () => (
    <>
      {Array.from({ length: pageSize }).map((_, index) => (
        <tr key={index} className="animate-pulse">
          {selectable && (
            <td className="px-4 py-4">
              <div className="w-4 h-4 bg-slate-200 rounded" />
            </td>
          )}
          {columns.map((col) => (
            <td key={String(col.key)} className="px-4 py-4">
              <div className="h-4 bg-slate-200 rounded w-3/4" />
            </td>
          ))}
          {actions && (
            <td className="px-4 py-4">
              <div className="w-8 h-4 bg-slate-200 rounded" />
            </td>
          )}
        </tr>
      ))}
    </>
  )

  return (
    <div className={clsx('flex flex-col', className)}>
      {/* Search Bar */}
      {searchable && (
        <div className="mb-4">
          <div className="relative max-w-sm">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input
              type="text"
              placeholder={searchPlaceholder}
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value)
                setCurrentPage(1)
              }}
              className="w-full pl-11 pr-4 py-2.5 text-sm bg-white border border-slate-300 
                         rounded-xl shadow-sm hover:border-slate-400
                         focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20
                         transition-all duration-200"
            />
          </div>
        </div>
      )}

      {/* Table Container */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead
              className={clsx(
                'bg-slate-50/80',
                stickyHeader && 'sticky top-0 z-10'
              )}
            >
              <tr>
                {selectable && (
                  <th className="px-4 py-3.5 w-12">
                    <input
                      type="checkbox"
                      checked={
                        paginatedData.length > 0 &&
                        selectedRows.length === paginatedData.length
                      }
                      onChange={handleSelectAll}
                      className="w-4 h-4 rounded border-slate-300 text-primary-600 
                                 focus:ring-primary-500"
                    />
                  </th>
                )}
                {columns.map((col) => (
                  <th
                    key={String(col.key)}
                    className={clsx(
                      'px-4 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider',
                      col.sortable && 'cursor-pointer select-none hover:bg-slate-100',
                      col.align === 'center' && 'text-center',
                      col.align === 'right' && 'text-right'
                    )}
                    style={{ width: col.width }}
                    onClick={() => col.sortable && handleSort(String(col.key))}
                  >
                    <div className="flex items-center gap-2">
                      <span>{col.header}</span>
                      {col.sortable && (
                        <span className="flex flex-col">
                          <ChevronUp
                            className={clsx(
                              'w-3 h-3 -mb-1',
                              sortKey === col.key && sortDirection === 'asc'
                                ? 'text-primary-600'
                                : 'text-slate-300'
                            )}
                          />
                          <ChevronDown
                            className={clsx(
                              'w-3 h-3',
                              sortKey === col.key && sortDirection === 'desc'
                                ? 'text-primary-600'
                                : 'text-slate-300'
                            )}
                          />
                        </span>
                      )}
                    </div>
                  </th>
                ))}
                {actions && (
                  <th className="px-4 py-3.5 w-16 text-center font-semibold text-slate-600 text-xs uppercase tracking-wider">
                    Actions
                  </th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                renderSkeleton()
              ) : paginatedData.length === 0 ? (
                <tr>
                  <td
                    colSpan={
                      columns.length + (selectable ? 1 : 0) + (actions ? 1 : 0)
                    }
                    className="px-4 py-12 text-center text-slate-500"
                  >
                    {emptyMessage}
                  </td>
                </tr>
              ) : (
                paginatedData.map((row, index) => {
                  const isSelected = selectedRows.some(
                    (selected) => selected[keyField] === row[keyField]
                  )
                  return (
                    <tr
                      key={String(row[keyField])}
                      className={clsx(
                        'transition-colors duration-150',
                        onRowClick && 'cursor-pointer hover:bg-slate-50/50',
                        isSelected && 'bg-primary-50/50'
                      )}
                      onClick={() => onRowClick?.(row)}
                    >
                      {selectable && (
                        <td className="px-4 py-4" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleSelectRow(row)}
                            className="w-4 h-4 rounded border-slate-300 text-primary-600 
                                       focus:ring-primary-500"
                          />
                        </td>
                      )}
                      {columns.map((col) => {
                        const value = row[col.key as keyof T]
                        return (
                          <td
                            key={String(col.key)}
                            className={clsx(
                              'px-4 py-4',
                              col.align === 'center' && 'text-center',
                              col.align === 'right' && 'text-right',
                              col.className
                            )}
                          >
                            {col.render
                              ? col.render(value, row, index)
                              : value !== null && value !== undefined
                              ? String(value)
                              : '-'}
                          </td>
                        )
                      })}
                      {actions && (
                        <td
                          className="px-4 py-4 text-center"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {actions(row)}
                        </td>
                      )}
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100">
            <p className="text-sm text-slate-500">
              Showing{' '}
              <span className="font-medium">
                {(currentPage - 1) * pageSize + 1}
              </span>{' '}
              to{' '}
              <span className="font-medium">
                {Math.min(currentPage * pageSize, sortedData.length)}
              </span>{' '}
              of <span className="font-medium">{sortedData.length}</span> results
            </p>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setCurrentPage(1)}
                disabled={currentPage === 1}
                className="p-2"
              >
                <ChevronsLeft className="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setCurrentPage((p) => p - 1)}
                disabled={currentPage === 1}
                className="p-2"
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let page: number
                if (totalPages <= 5) {
                  page = i + 1
                } else if (currentPage <= 3) {
                  page = i + 1
                } else if (currentPage >= totalPages - 2) {
                  page = totalPages - 4 + i
                } else {
                  page = currentPage - 2 + i
                }
                return (
                  <Button
                    key={page}
                    variant={currentPage === page ? 'primary' : 'ghost'}
                    size="sm"
                    onClick={() => setCurrentPage(page)}
                    className="min-w-[2rem]"
                  >
                    {page}
                  </Button>
                )
              })}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setCurrentPage((p) => p + 1)}
                disabled={currentPage === totalPages}
                className="p-2"
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setCurrentPage(totalPages)}
                disabled={currentPage === totalPages}
                className="p-2"
              >
                <ChevronsRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default DataTable
