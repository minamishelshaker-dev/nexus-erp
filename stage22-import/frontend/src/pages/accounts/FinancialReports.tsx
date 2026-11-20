import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  FileText, Download, Printer, TrendingUp, TrendingDown, DollarSign,
  PieChart, BarChart3, Calendar
} from 'lucide-react'
import api from '../../services/api'

type ReportType = 'trial_balance' | 'income_statement' | 'balance_sheet' | 'general_ledger'

export default function FinancialReports() {
  const [activeReport, setActiveReport] = useState<ReportType>('trial_balance')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [asOfDate, setAsOfDate] = useState(new Date().toISOString().split('T')[0])
  
  // Fetch report data
  const { data: reportData, isLoading, refetch } = useQuery({
    queryKey: ['financial-report', activeReport, dateFrom, dateTo, asOfDate],
    queryFn: async () => {
      if (activeReport === 'balance_sheet') {
        const response = await api.post('/reports/balance-sheet', {
          date: asOfDate
        })
        return response.data
      } else if (activeReport === 'income_statement') {
        const response = await api.post('/reports/income-statement', {
          date_from: dateFrom,
          date_to: dateTo
        })
        return response.data
      } else if (activeReport === 'trial_balance') {
        const response = await api.post('/reports/trial-balance', {
          date_from: dateFrom,
          date_to: dateTo
        })
        return response.data
      }
      return null
    },
    enabled: false
  })
  
  const handleGenerateReport = () => {
    refetch()
  }
  
  const reports = [
    { id: 'trial_balance', name: 'ميزان المراجعة', icon: BarChart3 },
    { id: 'income_statement', name: 'قائمة الدخل', icon: TrendingUp },
    { id: 'balance_sheet', name: 'الميزانية العمومية', icon: PieChart },
    { id: 'general_ledger', name: 'دفتر الأستاذ', icon: FileText },
  ]
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">التقارير المالية</h1>
          <p className="text-slate-500 mt-1">التقارير والتحليلات المالية</p>
        </div>
        <div className="flex gap-2">
          <button className="btn btn-secondary">
            <Printer className="w-4 h-4" />
            طباعة
          </button>
          <button className="btn btn-secondary">
            <Download className="w-4 h-4" />
            تصدير PDF
          </button>
        </div>
      </div>
      
      <div className="grid grid-cols-4 gap-6">
        {/* Report Selection */}
        <div className="card">
          <div className="card-header">
            <h2 className="font-semibold">اختر التقرير</h2>
          </div>
          <div className="p-2">
            {reports.map((report) => {
              const Icon = report.icon
              return (
                <button
                  key={report.id}
                  onClick={() => setActiveReport(report.id as ReportType)}
                  className={`w-full flex items-center gap-3 p-3 rounded-lg text-right transition-colors ${
                    activeReport === report.id
                      ? 'bg-primary-50 text-primary-700'
                      : 'hover:bg-slate-50'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span>{report.name}</span>
                </button>
              )
            })}
          </div>
          
          {/* Date Selection */}
          <div className="p-4 border-t border-slate-200">
            {activeReport === 'balance_sheet' ? (
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  بتاريخ
                </label>
                <input
                  type="date"
                  value={asOfDate}
                  onChange={(e) => setAsOfDate(e.target.value)}
                  className="input w-full"
                />
              </div>
            ) : (
              <>
                <div className="mb-3">
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    من تاريخ
                  </label>
                  <input
                    type="date"
                    value={dateFrom}
                    onChange={(e) => setDateFrom(e.target.value)}
                    className="input w-full"
                  />
                </div>
                <div className="mb-3">
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    إلى تاريخ
                  </label>
                  <input
                    type="date"
                    value={dateTo}
                    onChange={(e) => setDateTo(e.target.value)}
                    className="input w-full"
                  />
                </div>
              </>
            )}
            
            <button
              onClick={handleGenerateReport}
              className="btn btn-primary w-full mt-2"
            >
              عرض التقرير
            </button>
          </div>
        </div>
        
        {/* Report Display */}
        <div className="col-span-3 card">
          <div className="card-header flex items-center justify-between">
            <h2 className="font-semibold">
              {reports.find(r => r.id === activeReport)?.name}
            </h2>
            {reportData && (
              <span className="text-sm text-slate-500">
                تم الإنشاء: {new Date().toLocaleDateString('ar-SA')}
              </span>
            )}
          </div>
          
          <div className="p-6">
            {isLoading ? (
              <div className="text-center py-12">
                <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto" />
                <p className="text-slate-500 mt-4">جاري تحميل التقرير...</p>
              </div>
            ) : !reportData ? (
              <div className="text-center py-12 text-slate-400">
                <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>اختر التقرير وحدد الفترة الزمنية</p>
              </div>
            ) : activeReport === 'trial_balance' ? (
              <TrialBalanceReport data={reportData} />
            ) : activeReport === 'income_statement' ? (
              <IncomeStatementReport data={reportData} />
            ) : activeReport === 'balance_sheet' ? (
              <BalanceSheetReport data={reportData} />
            ) : null}
          </div>
        </div>
      </div>
    </div>
  )
}

// Trial Balance Report Component
function TrialBalanceReport({ data }: { data: any }) {
  return (
    <div>
      <div className="overflow-x-auto">
        <table className="table">
          <thead>
            <tr>
              <th>كود الحساب</th>
              <th>اسم الحساب</th>
              <th>مدين</th>
              <th>دائن</th>
            </tr>
          </thead>
          <tbody>
            {data.lines?.map((line: any) => (
              <tr key={line.account_id}>
                <td className="font-mono">{line.account_code}</td>
                <td>{line.account_name}</td>
                <td className="font-mono text-blue-600">
                  {line.closing_debit > 0 ? line.closing_debit.toLocaleString() : '-'}
                </td>
                <td className="font-mono text-red-600">
                  {line.closing_credit > 0 ? line.closing_credit.toLocaleString() : '-'}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="font-bold bg-slate-100">
              <td colSpan={2}>الإجمالي</td>
              <td className="font-mono text-blue-600">
                {data.total_closing_debit?.toLocaleString()}
              </td>
              <td className="font-mono text-red-600">
                {data.total_closing_credit?.toLocaleString()}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
      
      <div className="mt-4 p-4 bg-green-50 rounded-lg flex items-center gap-2">
        {data.is_balanced ? (
          <>
            <TrendingUp className="w-5 h-5 text-green-600" />
            <span className="text-green-700">ميزان المراجعة متوازن ✓</span>
          </>
        ) : (
          <>
            <TrendingDown className="w-5 h-5 text-red-600" />
            <span className="text-red-700">ميزان المراجعة غير متوازن!</span>
          </>
        )}
      </div>
    </div>
  )
}

// Income Statement Report Component
function IncomeStatementReport({ data }: { data: any }) {
  return (
    <div className="space-y-6">
      {/* Revenue Section */}
      <div>
        <h3 className="font-semibold text-lg mb-3 text-green-700">الإيرادات</h3>
        <table className="table">
          <tbody>
            {data.revenue?.lines?.map((line: any) => (
              <tr key={line.account_id}>
                <td className="font-mono text-slate-500 w-24">{line.account_code}</td>
                <td>{line.account_name}</td>
                <td className="font-mono text-green-600">
                  {line.amount.toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="font-semibold bg-green-50">
              <td colSpan={2}>إجمالي الإيرادات</td>
              <td className="font-mono">{data.revenue?.total?.toLocaleString()}</td>
            </tr>
          </tfoot>
        </table>
      </div>
      
      {/* Expenses Section */}
      <div>
        <h3 className="font-semibold text-lg mb-3 text-red-700">المصروفات</h3>
        <table className="table">
          <tbody>
            {data.expenses?.lines?.map((line: any) => (
              <tr key={line.account_id}>
                <td className="font-mono text-slate-500 w-24">{line.account_code}</td>
                <td>{line.account_name}</td>
                <td className="font-mono text-red-600">
                  {line.amount.toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="font-semibold bg-red-50">
              <td colSpan={2}>إجمالي المصروفات</td>
              <td className="font-mono">{data.expenses?.total?.toLocaleString()}</td>
            </tr>
          </tfoot>
        </table>
      </div>
      
      {/* Net Income */}
      <div className="p-4 bg-primary-50 rounded-lg">
        <div className="flex justify-between items-center">
          <span className="font-semibold text-lg">صافي الدخل</span>
          <span className={`text-2xl font-bold ${data.net_income >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {data.net_income?.toLocaleString()}
          </span>
        </div>
      </div>
    </div>
  )
}

// Balance Sheet Report Component
function BalanceSheetReport({ data }: { data: any }) {
  return (
    <div className="grid grid-cols-2 gap-8">
      {/* Assets */}
      <div>
        <h3 className="font-semibold text-lg mb-3 text-blue-700">الأصول</h3>
        <table className="table">
          <tbody>
            {data.assets?.lines?.map((line: any) => (
              <tr key={line.account_id}>
                <td className="font-mono text-slate-500">{line.account_code}</td>
                <td>{line.account_name}</td>
                <td className="font-mono">{line.amount.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="font-semibold bg-blue-50">
              <td colSpan={2}>إجمالي الأصول</td>
              <td className="font-mono">{data.total_assets?.toLocaleString()}</td>
            </tr>
          </tfoot>
        </table>
      </div>
      
      {/* Liabilities & Equity */}
      <div>
        <h3 className="font-semibold text-lg mb-3 text-red-700">الخصوم وحقوق الملكية</h3>
        <table className="table">
          <tbody>
            {data.liabilities?.lines?.map((line: any) => (
              <tr key={line.account_id}>
                <td className="font-mono text-slate-500">{line.account_code}</td>
                <td>{line.account_name}</td>
                <td className="font-mono">{line.amount.toLocaleString()}</td>
              </tr>
            ))}
            <tr className="border-t-2 border-slate-200">
              <td colSpan={3} className="font-semibold text-purple-700 pt-4">
                حقوق الملكية
              </td>
            </tr>
            {data.equity?.lines?.map((line: any) => (
              <tr key={line.account_id}>
                <td className="font-mono text-slate-500">{line.account_code}</td>
                <td>{line.account_name}</td>
                <td className="font-mono">{line.amount.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="font-semibold bg-slate-100">
              <td colSpan={2}>إجمالي الخصوم وحقوق الملكية</td>
              <td className="font-mono">
                {data.total_liabilities_and_equity?.toLocaleString()}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}
