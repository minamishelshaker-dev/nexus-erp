/**
 * Nexus ERP - General Ledger Page
 * Chart of accounts and general ledger entries
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, PaginatedResponse } from '../../services/api'
import {
  Search,
  BookOpen,
  Calendar,
  ChevronDown,
  ChevronRight,
  ArrowUpRight,
  ArrowDownRight,
  Filter,
} from 'lucide-react'

interface GLAccount {
  id: string
  code: string
  name: string
  type: 'asset' | 'liability' | 'equity' | 'revenue' | 'expense'
  parent_id?: string
  parent_name?: string
  level: number
  is_active: boolean
  allow_reconciliation: boolean
  balance: number
  debit: number
  credit: number
  children?: GLAccount[]
}

interface GLJournalEntry {
  id: string
  date: string
  entry_number: string
  account_code: string
  account_name: string
  description: string
  reference: string
  debit: number
  credit: number
  balance: number
}

const accountTypeColors: Record<string, string> = {
  asset: 'bg-blue-100 text-blue-700',
  liability: 'bg-red-100 text-red-700',
  equity: 'bg-purple-100 text-purple-700',
  revenue: 'bg-green-100 text-green-700',
  expense: 'bg-orange-100 text-orange-700',
}

const accountTypeLabels: Record<string, string> = {
  asset: 'Asset',
  liability: 'Liability',
  equity: 'Equity',
  revenue: 'Revenue',
  expense: 'Expense',
}

export default function GeneralLedgerPage() {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selectedType, setSelectedType] = useState<string>('')
  const [selectedAccount, setSelectedAccount] = useState<string>('')
  const [dateFrom, setDateFrom] = useState<string>('')
  const [dateTo, setDateTo] = useState<string>('')
  const [viewMode, setViewMode] = useState<'accounts' | 'entries'>('accounts')

  // Fetch GL accounts
  const { data: accountsData, isLoading: accountsLoading } = useQuery({
    queryKey: ['gl-accounts', { type: selectedType }],
    queryFn: async () => {
      const params = new URLSearchParams({
        ...(selectedType && { type: selectedType }),
      })
      const response = await api.get(`/accounting/accounts?${params}`)
      return response.data as GLAccount[]
    },
  })

  // Fetch journal entries
  const { data: entriesData, isLoading: entriesLoading } = useQuery({
    queryKey: ['journal-entries', { page, account: selectedAccount, dateFrom, dateTo }],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20',
        ...(selectedAccount && { account: selectedAccount }),
        ...(dateFrom && { date_from: dateFrom }),
        ...(dateTo && { date_to: dateTo }),
      })
      const response = await api.get(`/accounting/journal-entries?${params}`)
      return response.data as PaginatedResponse<GLJournalEntry>
    },
  })

  // Fetch accounts for filter
  const { data: accountsList } = useQuery({
    queryKey: ['accounts-list'],
    queryFn: async () => {
      const response = await api.get('/accounting/accounts?flat=true')
      return response.data as { id: string; code: string; name: string }[]
    },
  })

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }

  // Calculate summary from accounts
  const summary = accountsData?.reduce((acc, account) => {
    if (account.type === 'asset' || account.type === 'expense') {
      acc.totalDebits += account.debit
      acc.totalCredits += account.credit
    } else {
      acc.totalDebits += account.debit
      acc.totalCredits += account.credit
    }
    return acc
  }, { totalDebits: 0, totalCredits: 0 })

  // Render account row with indentation
  const renderAccountRow = (account: GLAccount, depth = 0) => {
    const hasChildren = account.children && account.children.length > 0
    const [expanded, setExpanded] = useState(true)

    return (
      <div key={account.id}>
        <div 
          className={`flex items-center py-3 px-4 hover:bg-slate-50 ${depth > 0 ? 'bg-slate-50/50' : ''}`}
          style={{ paddingLeft: `${depth * 24 + 16}px` }}
        >
          {hasChildren && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="mr-2 p-0.5 hover:bg-slate-200 rounded"
            >
              {expanded ? (
                <ChevronDown className="w-4 h-4 text-slate-400" />
              ) : (
                <ChevronRight className="w-4 h-4 text-slate-400" />
              )}
            </button>
          )}
          <div className="flex-1 flex items-center gap-3">
            <span className="font-mono text-sm text-slate-500 w-20">{account.code}</span>
            <span className="font-medium text-slate-900">{account.name}</span>
            <span className={`badge ${accountTypeColors[account.type]}`}>
              {accountTypeLabels[account.type]}
            </span>
          </div>
          <div className="flex items-center gap-8 text-sm">
            <div className="w-28 text-right">
              {account.debit > 0 ? (
                <span className="text-green-600">{formatCurrency(account.debit)}</span>
              ) : (
                <span className="text-slate-300">-</span>
              )}
            </div>
            <div className="w-28 text-right">
              {account.credit > 0 ? (
                <span className="text-red-600">{formatCurrency(account.credit)}</span>
              ) : (
                <span className="text-slate-300">-</span>
              )}
            </div>
            <div className="w-28 text-right font-medium">
              {formatCurrency(account.balance)}
            </div>
          </div>
        </div>
        {hasChildren && expanded && account.children?.map(child => renderAccountRow(child, depth + 1))}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">General Ledger</h1>
          <p className="text-slate-500 mt-1">View account balances and journal entries</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex bg-slate-100 rounded-lg p-1">
            <button
              onClick={() => setViewMode('accounts')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                viewMode === 'accounts' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'
              }`}
            >
              Account Balances
            </button>
            <button
              onClick={() => setViewMode('entries')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                viewMode === 'entries' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'
              }`}
            >
              Journal Entries
            </button>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-4">
          <p className="text-sm text-slate-500">Total Debits</p>
          <p className="text-xl font-bold text-green-600">{formatCurrency(summary?.totalDebits || 0)}</p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-slate-500">Total Credits</p>
          <p className="text-xl font-bold text-red-600">{formatCurrency(summary?.totalCredits || 0)}</p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-slate-500">Net Balance</p>
          <p className="text-xl font-bold text-slate-900">
            {formatCurrency(Math.abs((summary?.totalDebits || 0) - (summary?.totalCredits || 0)))}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-slate-500">Active Accounts</p>
          <p className="text-xl font-bold text-slate-900">{accountsData?.length || 0}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-col md:flex-row gap-4">
          {viewMode === 'accounts' ? (
            <>
              {/* Search */}
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search accounts..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="input pl-10"
                />
              </div>

              {/* Type filter */}
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="select w-full md:w-40"
              >
                <option value="">All Types</option>
                <option value="asset">Asset</option>
                <option value="liability">Liability</option>
                <option value="equity">Equity</option>
                <option value="revenue">Revenue</option>
                <option value="expense">Expense</option>
              </select>
            </>
          ) : (
            <>
              {/* Account filter */}
              <select
                value={selectedAccount}
                onChange={(e) => setSelectedAccount(e.target.value)}
                className="select w-full md:w-56"
              >
                <option value="">All Accounts</option>
                {accountsList?.map((acc) => (
                  <option key={acc.id} value={acc.id}>{acc.code} - {acc.name}</option>
                ))}
              </select>

              {/* Date From */}
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="select w-full md:w-40"
              />

              {/* Date To */}
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="select w-full md:w-40"
              />
            </>
          )}
        </div>
      </div>

      {/* Content */}
      {viewMode === 'accounts' ? (
        // Account Balances View
        <div className="card">
          {accountsLoading ? (
            <div className="p-12 text-center">
              <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto" />
              <p className="text-slate-500 mt-4">Loading accounts...</p>
            </div>
          ) : (
            <>
              {/* Header */}
              <div className="flex items-center py-3 px-4 bg-slate-50 border-b border-slate-200 text-sm font-medium text-slate-500">
                <div className="flex-1">Account</div>
                <div className="flex items-center gap-8">
                  <div className="w-28 text-right">Debit</div>
                  <div className="w-28 text-right">Credit</div>
                  <div className="w-28 text-right">Balance</div>
                </div>
              </div>
              {/* Account rows */}
              <div className="divide-y divide-slate-100">
                {accountsData?.map(account => renderAccountRow(account))}
              </div>
            </>
          )}
        </div>
      ) : (
        // Journal Entries View
        <div className="card">
          {entriesLoading ? (
            <div className="p-12 text-center">
              <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto" />
              <p className="text-slate-500 mt-4">Loading entries...</p>
            </div>
          ) : entriesData?.items.length === 0 ? (
            <div className="p-12 text-center">
              <BookOpen className="w-12 h-12 text-slate-300 mx-auto" />
              <h3 className="text-lg font-medium text-slate-900 mt-4">No journal entries found</h3>
              <p className="text-slate-500 mt-2">Journal entries will appear here once transactions are recorded.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Entry #</th>
                    <th>Account</th>
                    <th>Description</th>
                    <th>Reference</th>
                    <th className="text-right">Debit</th>
                    <th className="text-right">Credit</th>
                    <th className="text-right">Balance</th>
                  </tr>
                </thead>
                <tbody>
                  {entriesData?.items.map((entry, index) => (
                    <tr key={`${entry.id}-${index}`}>
                      <td>
                        <div className="flex items-center gap-2 text-slate-500">
                          <Calendar className="w-4 h-4" />
                          {formatDate(entry.date)}
                        </div>
                      </td>
                      <td>
                        <Link
                          to={`/accounting/journal-entries/${entry.id}`}
                          className="font-medium text-primary-600 hover:underline"
                        >
                          {entry.entry_number}
                        </Link>
                      </td>
                      <td>
                        <div>
                          <span className="font-mono text-sm text-slate-500">{entry.account_code}</span>
                          <p className="text-slate-900">{entry.account_name}</p>
                        </div>
                      </td>
                      <td>
                        <span className="text-slate-600">{entry.description || '-'}</span>
                      </td>
                      <td>
                        <span className="text-slate-500">{entry.reference || '-'}</span>
                      </td>
                      <td className="text-right">
                        {entry.debit > 0 ? (
                          <span className="text-green-600 font-medium flex items-center justify-end gap-1">
                            <ArrowUpRight className="w-4 h-4" />
                            {formatCurrency(entry.debit)}
                          </span>
                        ) : (
                          <span className="text-slate-300">-</span>
                        )}
                      </td>
                      <td className="text-right">
                        {entry.credit > 0 ? (
                          <span className="text-red-600 font-medium flex items-center justify-end gap-1">
                            <ArrowDownRight className="w-4 h-4" />
                            {formatCurrency(entry.credit)}
                          </span>
                        ) : (
                          <span className="text-slate-300">-</span>
                        )}
                      </td>
                      <td className="text-right font-medium">
                        {formatCurrency(entry.balance)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {entriesData && entriesData.pages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200">
              <p className="text-sm text-slate-500">
                Showing {((page - 1) * 20) + 1} to {Math.min(page * 20, entriesData.total)} of {entriesData.total} entries
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="btn btn-secondary btn-sm"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(entriesData.pages, p + 1))}
                  disabled={page === entriesData.pages}
                  className="btn btn-secondary btn-sm"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
