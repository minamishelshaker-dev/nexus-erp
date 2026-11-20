/**
 * Nexus ERP - Quotations Page
 * ============================
 * Sales quotations management page
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  PlusIcon,
  PencilIcon,
  PaperAirplaneIcon,
  CheckCircleIcon,
  XCircleIcon,
  EyeIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';

interface Quotation {
  id: string;
  number: string;
  name: string;
  date: string;
  valid_until?: string;
  state: 'draft' | 'sent' | 'accepted' | 'lost' | 'expired' | 'cancelled';
  amount_total: number;
}

const stateColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-800',
  sent: 'bg-blue-100 text-blue-800',
  accepted: 'bg-green-100 text-green-800',
  lost: 'bg-red-100 text-red-800',
  expired: 'bg-yellow-100 text-yellow-800',
  cancelled: 'bg-gray-100 text-gray-600',
};

const stateLabels: Record<string, string> = {
  draft: 'مسودة',
  sent: 'مرسل',
  accepted: 'مقبول',
  lost: 'مرفوض',
  expired: 'منتهي',
  cancelled: 'ملغي',
};

export const QuotationsPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [stateFilter, setStateFilter] = useState<string>('');

  const { data, isLoading } = useQuery({
    queryKey: ['quotations', page, stateFilter],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20',
        ...(stateFilter && { state: stateFilter }),
      });
      const response = await api.get(`/sales/quotations?${params}`);
      return response.data;
    },
  });

  const sendMutation = useMutation({
    mutationFn: async (id: string) => {
      return await api.post(`/sales/quotations/${id}/send`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['quotations'] }),
  });

  const confirmMutation = useMutation({
    mutationFn: async (id: string) => {
      return await api.post(`/sales/quotations/${id}/confirm`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quotations'] });
      queryClient.invalidateQueries({ queryKey: ['sale-orders'] });
    },
  });

  const formatCurrency = (amount: number) => 
    new Intl.NumberFormat('ar-SA', { style: 'currency', currency: 'SAR' }).format(amount);
  
  const formatDate = (dateString: string) => 
    new Date(dateString).toLocaleDateString('ar-SA');

  if (isLoading) {
    return <div className="flex justify-center p-8"><div className="animate-spin h-8 w-8 border-2 border-blue-600 rounded-full"></div></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">عروض الأسعار</h1>
          <p className="text-gray-500">إدارة عروض أسعار المبيعات</p>
        </div>
        <button
          onClick={() => navigate('/sales/quotations/new')}
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <PlusIcon className="h-5 w-5 ml-2" />
          عرض سعر جديد
        </button>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <select
          value={stateFilter}
          onChange={(e) => setStateFilter(e.target.value)}
          className="border rounded-lg px-3 py-2"
        >
          <option value="">جميع الحالات</option>
          {Object.entries(stateLabels).map(([key, label]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </select>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">رقم العرض</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">الاسم</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">التاريخ</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">المبلغ</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">الحالة</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">الإجراءات</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {data?.items?.map((q: Quotation) => (
              <tr key={q.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 text-sm font-medium text-blue-600">{q.number}</td>
                <td className="px-6 py-4 text-sm text-gray-900">{q.name}</td>
                <td className="px-6 py-4 text-sm text-gray-500">{formatDate(q.date)}</td>
                <td className="px-6 py-4 text-sm text-gray-900">{formatCurrency(q.amount_total)}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 text-xs rounded-full ${stateColors[q.state]}`}>
                    {stateLabels[q.state]}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm">
                  <div className="flex gap-2">
                    <button onClick={() => navigate(`/sales/quotations/${q.id}`)} className="text-blue-600">
                      <EyeIcon className="h-5 w-5" />
                    </button>
                    {q.state === 'draft' && (
                      <>
                        <button onClick={() => navigate(`/sales/quotations/${q.id}/edit`)} className="text-yellow-600">
                          <PencilIcon className="h-5 w-5" />
                        </button>
                        <button onClick={() => sendMutation.mutate(q.id)} className="text-green-600">
                          <PaperAirplaneIcon className="h-5 w-5" />
                        </button>
                      </>
                    )}
                    {q.state === 'sent' && (
                      <button onClick={() => confirmMutation.mutate(q.id)} className="text-green-600">
                        <CheckCircleIcon className="h-5 w-5" />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default QuotationsPage;
