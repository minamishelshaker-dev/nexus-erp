import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  Plus, Search, Filter, MoreVertical, Edit, Trash2, Eye, ChevronRight, ChevronDown,
  Folder, FolderOpen, DollarSign, TrendingUp, TrendingDown, AlertCircle
} from 'lucide-react'
import api from '../../services/api'

const accountTypeColors: Record<string, string> = {
  asset: 'bg-blue-100 text-blue-700',
  liability: 'bg-red-100 text-red-700',
  equity: 'bg-purple-100 text-purple-700',
  revenue: 'bg-green-100 text-green-700',
  expense: 'bg-orange-100 text-orange-700',
}

const accountTypeLabels: Record<string, string> = {
  asset: 'أصول',
  liability: 'خصوم',
  equity: 'حقوق الملكية',
  revenue: 'إيرادات',
  expense: 'مصروفات',
}

interface Account {
  id: string
  code: string
  name: string
  account_type: string
  balance: number
  debit_balance: number
  credit_balance: number
  is_active: boolean
  is_header: boolean
  parent_id?: string
  children?: Account[]
}

interface AccountTreeNodeProps {
  account: Account
  level: number
  onSelect: (account: Account) => void
  selectedId?: string
}

function AccountTreeNode({ account, level, onSelect, selectedId }: AccountTreeNodeProps) {
  const [expanded, setExpanded] = useState(level < 2)
  const hasChildren = account.children && account.children.length > 0
  
  return (
    <div>
      <div
        className={`flex items-center gap-2 p-2 hover:bg-slate-50 cursor-pointer ${
          selectedId === account.id ? 'bg-primary-50' : ''
        }`}
        style={{ paddingLeft: `${level * 20 + 8}px` }}
        onClick={() => onSelect(account)}
      >
        {hasChildren ? (
          <button
            onClick={(e) => {
              e.stopPropagation()
              setExpanded(!expanded)
            }}
            className="p-1 hover:bg-slate-100 rounded"
          >
            {expanded ? (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-slate-400" />
            )}
          </button>
        ) : (
          <span className="w-6" />
        )}
        
        {account.is_header ? (
          <FolderOpen className="w-4 h-4 text-amber-500" />
        ) : (
          <DollarSign className="w-4 h-4 text-slate-400" />
        )}
        
        <span className="font-mono text-sm text-slate-500 w-20">{account.code}</span>
        <span className="flex-1 text-sm">{account.name}</span>
        
        <span className={`badge ${accountTypeColors[account.account_type] || 'bg-slate-100'}`}>
          {accountTypeLabels[account.account_type] || account.account_type}
        </span>
        
        {!account.is_header && (
          <span className={`font-mono text-sm ${
            account.balance >= 0 ? 'text-green-600' : 'text-red-600'
          }`}>
            {account.balance.toLocaleString()}
          </span>
        )}
      </div>
      
      {expanded && hasChildren && (
        <div>
          {account.children!.map((child) => (
            <AccountTreeNode
              key={child.id}
              account={child}
              level={level + 1}
              onSelect={onSelect}
              selectedId={selectedId}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default function ChartOfAccounts() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [selectedType, setSelectedType] = useState('')
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  
  // Fetch accounts tree
  const { data: accountsTree, isLoading } = useQuery({
    queryKey: ['accounts-tree', selectedType],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (selectedType) params.append('account_type', selectedType)
      const response = await api.get(`/accounts/tree?${params}`)
      return response.data
    }
  })
  
  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/accounts/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts-tree'] })
    }
  })
  
  const handleDelete = async (id: string) => {
    if (confirm('هل أنت متأكد من حذف هذا الحساب؟')) {
      await deleteMutation.mutateAsync(id)
      setSelectedAccount(null)
    }
  }
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">مخطط الحسابات</h1>
          <p className="text-slate-500 mt-1">إدارة الهيكل المحاسبي للشركة</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn btn-primary"
        >
          <Plus className="w-4 h-4" />
          إضافة حساب
        </button>
      </div>
      
      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">إجمالي الأصول</p>
              <p className="text-xl font-bold">1,250,000</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
              <TrendingDown className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">إجمالي الخصوم</p>
              <p className="text-xl font-bold">850,000</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <DollarSign className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">حقوق الملكية</p>
              <p className="text-xl font-bold">400,000</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">صافي الربح</p>
              <p className="text-xl font-bold">125,000</p>
            </div>
          </div>
        </div>
      </div>
      
      <div className="grid grid-cols-3 gap-6">
        {/* Filters & Tree */}
        <div className="col-span-2 card">
          <div className="card-header flex items-center justify-between">
            <h2 className="font-semibold">شجرة الحسابات</h2>
            <div className="flex gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="بحث..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="input pl-9 w-64"
                />
              </div>
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="select w-40"
              >
                <option value="">كل الأنواع</option>
                <option value="asset">أصول</option>
                <option value="liability">خصوم</option>
                <option value="equity">حقوق الملكية</option>
                <option value="revenue">إيرادات</option>
                <option value="expense">مصروفات</option>
              </select>
            </div>
          </div>
          
          <div className="divide-y divide-slate-100 max-h-[600px] overflow-y-auto">
            {isLoading ? (
              <div className="p-8 text-center text-slate-500">جاري التحميل...</div>
            ) : accountsTree?.length === 0 ? (
              <div className="p-8 text-center text-slate-500">لا توجد حسابات</div>
            ) : (
              accountsTree?.map((account: Account) => (
                <AccountTreeNode
                  key={account.id}
                  account={account}
                  level={0}
                  onSelect={setSelectedAccount}
                  selectedId={selectedAccount?.id}
                />
              ))
            )}
          </div>
        </div>
        
        {/* Account Details */}
        <div className="card">
          <div className="card-header">
            <h2 className="font-semibold">تفاصيل الحساب</h2>
          </div>
          
          {selectedAccount ? (
            <div className="p-4 space-y-4">
              <div>
                <p className="text-sm text-slate-500">الكود</p>
                <p className="font-mono text-lg">{selectedAccount.code}</p>
              </div>
              
              <div>
                <p className="text-sm text-slate-500">اسم الحساب</p>
                <p className="font-medium">{selectedAccount.name}</p>
              </div>
              
              <div>
                <p className="text-sm text-slate-500">نوع الحساب</p>
                <span className={`badge ${accountTypeColors[selectedAccount.account_type]}`}>
                  {accountTypeLabels[selectedAccount.account_type]}
                </span>
              </div>
              
              <div className="pt-4 border-t border-slate-200">
                <p className="text-sm text-slate-500">الرصيد</p>
                <p className={`text-2xl font-bold ${
                  selectedAccount.balance >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {selectedAccount.balance.toLocaleString()}
                </p>
              </div>
              
              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-slate-200">
                <div>
                  <p className="text-sm text-slate-500">مدين</p>
                  <p className="font-medium text-blue-600">
                    {selectedAccount.debit_balance.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">دائن</p>
                  <p className="font-medium text-red-600">
                    {selectedAccount.credit_balance.toLocaleString()}
                  </p>
                </div>
              </div>
              
              {!selectedAccount.is_header && (
                <div className="flex gap-2 pt-4">
                  <Link
                    to={`/accounts/journal-entries?account_id=${selectedAccount.id}`}
                    className="btn btn-secondary flex-1"
                  >
                    <Eye className="w-4 h-4" />
                    الحركات
                  </Link>
                  <button
                    onClick={() => handleDelete(selectedAccount.id)}
                    className="btn btn-danger"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="p-8 text-center text-slate-400">
              اختر حساباً لعرض التفاصيل
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
