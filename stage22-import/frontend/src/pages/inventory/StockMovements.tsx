import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Plus, Search, Package, ArrowRight, Check, X, AlertCircle,
  TrendingUp, TrendingDown, Minus
} from 'lucide-react'
import api from '../../services/api'

const moveTypeColors: Record<string, string> = {
  in: 'bg-green-100 text-green-700',
  out: 'bg-red-100 text-red-700',
  internal: 'bg-blue-100 text-blue-700',
  adjustment: 'bg-amber-100 text-amber-700',
  return_in: 'bg-teal-100 text-teal-700',
  return_out: 'bg-orange-100 text-orange-700',
  production: 'bg-purple-100 text-purple-700',
  loss: 'bg-red-100 text-red-700',
}

const moveTypeLabels: Record<string, string> = {
  in: 'استلام',
  out: 'صرف',
  internal: 'تحويل',
  adjustment: 'تسوية',
  return_in: 'إرجاع وارد',
  return_out: 'إرجاع صادر',
  production: 'إنتاج',
  loss: 'هالك',
}

const stateColors: Record<string, string> = {
  draft: 'bg-slate-100 text-slate-700',
  confirmed: 'bg-blue-100 text-blue-700',
  done: 'bg-green-100 text-green-700',
  cancelled: 'bg-red-100 text-red-700',
}

const stateLabels: Record<string, string> = {
  draft: 'مسودة',
  confirmed: 'مؤكد',
  done: 'تم',
  cancelled: 'ملغي',
}

interface StockMove {
  id: string
  number: string
  product_id: string
  product?: { sku: string; name: string }
  quantity: number
  quantity_done: number
  move_type: string
  state: string
  date: string
  warehouse_from_id?: string
  warehouse_to_id?: string
  location_from_id?: string
  location_to_id?: string
  unit_cost: number
  total_cost: number
  reference?: string
}

export default function StockMovements() {
  const queryClient = useQueryClient()
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [moveType, setMoveType] = useState('')
  const [selectedMove, setSelectedMove] = useState<StockMove | null>(null)
  
  // Fetch stock moves
  const { data: moves, isLoading } = useQuery({
    queryKey: ['stock-moves', dateFrom, dateTo, moveType],
    queryFn: async () => {
      const params = new URLSearchParams()
      params.append('page', '1')
      params.append('page_size', '50')
      if (dateFrom) params.append('date_from', dateFrom)
      if (dateTo) params.append('date_to', dateTo)
      if (moveType) params.append('move_type', moveType)
      const response = await api.get(`/stock-moves?${params}`)
      return response.data
    }
  })
  
  // Confirm mutation
  const confirmMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/stock-moves/${id}/confirm`, {})
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stock-moves'] })
    }
  })
  
  // Process mutation
  const processMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/stock-moves/${id}/process`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stock-moves'] })
    }
  })
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">حركات المخزون</h1>
          <p className="text-slate-500 mt-1">إدارة تحركات المخزون والتحويلات</p>
        </div>
        <button className="btn btn-primary">
          <Plus className="w-4 h-4" />
          حركة جديدة
        </button>
      </div>
      
      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">الوارد اليوم</p>
              <p className="text-xl font-bold">1,250</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
              <TrendingDown className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">الصادر اليوم</p>
              <p className="text-xl font-bold">890</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <ArrowRight className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">التحويلات</p>
              <p className="text-xl font-bold">45</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center">
              <Package className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">في الانتظار</p>
              <p className="text-xl font-bold">12</p>
            </div>
          </div>
        </div>
      </div>
      
      {/* Filters */}
      <div className="card p-4">
        <div className="flex gap-4">
          <div className="flex-1 relative">
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="بحث..."
              className="input pr-10"
            />
          </div>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="input w-40"
          />
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="input w-40"
          />
          <select
            value={moveType}
            onChange={(e) => setMoveType(e.target.value)}
            className="select w-40"
          >
            <option value="">كل الأنواع</option>
            <option value="in">استلام</option>
            <option value="out">صرف</option>
            <option value="internal">تحويل</option>
            <option value="adjustment">تسوية</option>
          </select>
        </div>
      </div>
      
      <div className="grid grid-cols-3 gap-6">
        {/* Moves List */}
        <div className="col-span-2 card">
          <div className="card-header">
            <h2 className="font-semibold">قائمة الحركات</h2>
          </div>
          
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>رقم الحركة</th>
                  <th>المنتج</th>
                  <th>النوع</th>
                  <th>الكمية</th>
                  <th>التاريخ</th>
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
                ) : !moves?.items?.length ? (
                  <tr>
                    <td colSpan={7} className="text-center py-8 text-slate-500">
                      لا توجد حركات
                    </td>
                  </tr>
                ) : (
                  moves.items.map((move: StockMove) => (
                    <tr
                      key={move.id}
                      className={`cursor-pointer hover:bg-slate-50 ${
                        selectedMove?.id === move.id ? 'bg-primary-50' : ''
                      }`}
                      onClick={() => setSelectedMove(move)}
                    >
                      <td className="font-mono">{move.number}</td>
                      <td>
                        <div className="font-mono text-xs text-slate-400">
                          {move.product?.sku}
                        </div>
                        <div>{move.product?.name}</div>
                      </td>
                      <td>
                        <span className={`badge ${moveTypeColors[move.move_type]}`}>
                          {moveTypeLabels[move.move_type]}
                        </span>
                      </td>
                      <td className="font-mono">{move.quantity.toLocaleString()}</td>
                      <td>{move.date}</td>
                      <td>
                        <span className={`badge ${stateColors[move.state]}`}>
                          {stateLabels[move.state]}
                        </span>
                      </td>
                      <td>
                        <div className="flex gap-1">
                          {move.state === 'draft' && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                confirmMutation.mutate(move.id)
                              }}
                              className="p-1 hover:bg-blue-100 rounded text-blue-600"
                              title="تأكيد"
                            >
                              <Check className="w-4 h-4" />
                            </button>
                          )}
                          {move.state === 'confirmed' && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                processMutation.mutate(move.id)
                              }}
                              className="p-1 hover:bg-green-100 rounded text-green-600"
                              title="تنفيذ"
                            >
                              <ArrowRight className="w-4 h-4" />
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
        
        {/* Move Details */}
        <div className="card">
          <div className="card-header">
            <h2 className="font-semibold">تفاصيل الحركة</h2>
          </div>
          
          {selectedMove ? (
            <div className="p-4 space-y-4">
              <div>
                <p className="text-sm text-slate-500">رقم الحركة</p>
                <p className="font-mono text-lg">{selectedMove.number}</p>
              </div>
              
              <div>
                <p className="text-sm text-slate-500">المنتج</p>
                <div className="font-mono text-xs text-slate-400">
                  {selectedMove.product?.sku}
                </div>
                <p className="font-medium">{selectedMove.product?.name}</p>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-slate-500">النوع</p>
                  <span className={`badge ${moveTypeColors[selectedMove.move_type]}`}>
                    {moveTypeLabels[selectedMove.move_type]}
                  </span>
                </div>
                <div>
                  <p className="text-sm text-slate-500">الحالة</p>
                  <span className={`badge ${stateColors[selectedMove.state]}`}>
                    {stateLabels[selectedMove.state]}
                  </span>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-slate-200">
                <div>
                  <p className="text-sm text-slate-500">الكمية</p>
                  <p className="text-xl font-bold">{selectedMove.quantity.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">المنفذة</p>
                  <p className="text-xl font-bold">{selectedMove.quantity_done.toLocaleString()}</p>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-slate-200">
                <div>
                  <p className="text-sm text-slate-500">تكلفة الوحدة</p>
                  <p className="font-mono">{selectedMove.unit_cost.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">إجمالي التكلفة</p>
                  <p className="font-mono font-bold">{selectedMove.total_cost.toLocaleString()}</p>
                </div>
              </div>
              
              {selectedMove.reference && (
                <div className="pt-4 border-t border-slate-200">
                  <p className="text-sm text-slate-500">المرجع</p>
                  <p>{selectedMove.reference}</p>
                </div>
              )}
              
              <div className="flex gap-2 pt-4">
                {selectedMove.state === 'draft' && (
                  <button
                    onClick={() => confirmMutation.mutate(selectedMove.id)}
                    className="btn btn-primary flex-1"
                  >
                    <Check className="w-4 h-4" />
                    تأكيد
                  </button>
                )}
                {selectedMove.state === 'confirmed' && (
                  <button
                    onClick={() => processMutation.mutate(selectedMove.id)}
                    className="btn btn-primary flex-1"
                  >
                    <ArrowRight className="w-4 h-4" />
                    تنفيذ
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-slate-400">
              <Package className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>اختر حركة لعرض التفاصيل</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
