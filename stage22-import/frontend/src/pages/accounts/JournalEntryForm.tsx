import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Plus, Search, Filter, Check, X, RotateCcw, Eye, Calendar
} from 'lucide-react'
import api from '../../services/api'

interface JournalItem {
  id: string
  account_id: string
  account?: { code: string; name: string }
  debit: number
  credit: number
  name?: string
}

interface JournalEntry {
  id: string
  number: string
  date: string
  description?: string
  state: string
  total_debit: number
  total_credit: number
  lines: JournalItem[]
  ref?: string
}

const stateColors: Record<string, string> = {
  draft: 'bg-slate-100 text-slate-700',
  posted: 'bg-green-100 text-green-700',
  cancelled: 'bg-red-100 text-red-700',
}

const stateLabels: Record<string, string> = {
  draft: 'مسودة',
  posted: 'مرحلة',
  cancelled: 'ملغاة',
}

export default function JournalEntryForm() {
  const queryClient = useQueryClient()
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [selectedEntry, setSelectedEntry] = useState<JournalEntry | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  
  // Fetch journal entries
  const { data: entries, isLoading } = useQuery({
    queryKey: ['journal-entries', dateFrom, dateTo],
    queryFn: async () => {
      const params = new URLSearchParams()
      params.append('page', '1')
      params.append('page_size', '50')
      if (dateFrom) params.append('date_from', dateFrom)
      if (dateTo) params.append('date_to', dateTo)
      const response = await api.get(`/journal-entries?${params}`)
      return response.data
    }
  })
  
  // Post mutation
  const postMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/journal-entries/${id}/post`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['journal-entries'] })
    }
  })
  
  // Reverse mutation
  const reverseMutation = useMutation({
    mutationFn: async ({ id, reason }: { id: string; reason: string }) => {
      await api.post(`/journal-entries/${id}/reverse`, { reason })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['journal-entries'] })
    }
  })
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">القيود اليومية</h1>
          <p className="text-slate-500 mt-1">إدارة القيود المحاسبية</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn btn-primary"
        >
          <Plus className="w-4 h-4" />
          قيد جديد
        </button>
      </div>
      
      {/* Filters */}
      <div className="card p-4">
        <div className="flex gap-4">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-slate-400" />
            <span className="text-sm text-slate-500">من:</span>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="input w-40"
            />
          </div>
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-slate-400" />
            <span className="text-sm text-slate-500">إلى:</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="input w-40"
            />
          </div>
          <button className="btn btn-secondary">
            <Search className="w-4 h-4" />
            بحث
          </button>
        </div>
      </div>
      
      <div className="grid grid-cols-3 gap-6">
        {/* Entries List */}
        <div className="col-span-2 card">
          <div className="card-header">
            <h2 className="font-semibold">قائمة القيود</h2>
          </div>
          
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>رقم القيد</th>
                  <th>التاريخ</th>
                  <th>البيان</th>
                  <th>مدين</th>
                  <th>دائن</th>
                  <th>الحالة</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={7} className="text-center py-8 text-slate-500">
                      جاري التحميل...
                    </td>
                  </tr>
                ) : entries?.items?.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-8 text-slate-500">
                      لا توجد قيود
                    </td>
                  </tr>
                ) : (
                  entries?.items?.map((entry: JournalEntry) => (
                    <tr
                      key={entry.id}
                      className={`cursor-pointer hover:bg-slate-50 ${
                        selectedEntry?.id === entry.id ? 'bg-primary-50' : ''
                      }`}
                      onClick={() => setSelectedEntry(entry)}
                    >
                      <td className="font-mono">{entry.number}</td>
                      <td>{entry.date}</td>
                      <td className="truncate max-w-xs">{entry.description || '-'}</td>
                      <td className="font-mono text-blue-600">
                        {entry.total_debit.toLocaleString()}
                      </td>
                      <td className="font-mono text-red-600">
                        {entry.total_credit.toLocaleString()}
                      </td>
                      <td>
                        <span className={`badge ${stateColors[entry.state]}`}>
                          {stateLabels[entry.state]}
                        </span>
                      </td>
                      <td>
                        <div className="flex gap-1">
                          {entry.state === 'draft' && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                postMutation.mutate(entry.id)
                              }}
                              className="p-1 hover:bg-green-100 rounded text-green-600"
                              title="ترحيل"
                            >
                              <Check className="w-4 h-4" />
                            </button>
                          )}
                          {entry.state === 'posted' && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                reverseMutation.mutate({ 
                                  id: entry.id, 
                                  reason: 'إلغاء' 
                                })
                              }}
                              className="p-1 hover:bg-amber-100 rounded text-amber-600"
                              title="عكس القيد"
                            >
                              <RotateCcw className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
        
        {/* Entry Details */}
        <div className="card">
          <div className="card-header">
            <h2 className="font-semibold">تفاصيل القيد</h2>
          </div>
          
          {selectedEntry ? (
            <div className="p-4">
              <div className="space-y-2 mb-4">
                <div className="flex justify-between">
                  <span className="text-slate-500">رقم القيد:</span>
                  <span className="font-mono">{selectedEntry.number}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">التاريخ:</span>
                  <span>{selectedEntry.date}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">الحالة:</span>
                  <span className={`badge ${stateColors[selectedEntry.state]}`}>
                    {stateLabels[selectedEntry.state]}
                  </span>
                </div>
                {selectedEntry.ref && (
                  <div className="flex justify-between">
                    <span className="text-slate-500">المرجع:</span>
                    <span>{selectedEntry.ref}</span>
                  </div>
                )}
              </div>
              
              {selectedEntry.description && (
                <div className="mb-4 p-2 bg-slate-50 rounded text-sm">
                  {selectedEntry.description}
                </div>
              )}
              
              <div className="border-t border-slate-200 pt-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-slate-500 text-xs">
                      <th className="text-right pb-2">الحساب</th>
                      <th className="text-right pb-2">مدين</th>
                      <th className="text-right pb-2">دائن</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedEntry.lines?.map((line) => (
                      <tr key={line.id} className="border-b border-slate-100">
                        <td className="py-2">
                          <div className="font-mono text-xs text-slate-400">
                            {line.account?.code}
                          </div>
                          <div>{line.account?.name}</div>
                          {line.name && (
                            <div className="text-xs text-slate-400">{line.name}</div>
                          )}
                        </td>
                        <td className="py-2 font-mono text-blue-600">
                          {line.debit > 0 ? line.debit.toLocaleString() : '-'}
                        </td>
                        <td className="py-2 font-mono text-red-600">
                          {line.credit > 0 ? line.credit.toLocaleString() : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="font-medium bg-slate-50">
                      <td className="py-2 px-2">الإجمالي</td>
                      <td className="py-2 font-mono text-blue-600">
                        {selectedEntry.total_debit.toLocaleString()}
                      </td>
                      <td className="py-2 font-mono text-red-600">
                        {selectedEntry.total_credit.toLocaleString()}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-slate-400">
              اختر قيداً لعرض التفاصيل
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
