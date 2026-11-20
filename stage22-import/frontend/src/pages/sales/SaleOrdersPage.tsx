/**
 * Nexus ERP - Sale Orders Page
 * =============================
 * Sale orders management page
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  PlusIcon,
  PencilIcon,
  CheckCircleIcon,
  XCircleIcon,
  EyeIcon,
  DocumentDuplicateIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';

interface SaleOrder {
  id: string;
  number: string;
  name: string;
  date_order: string;
  state: 'draft' | 'confirmed' | 'done' | 'cancelled';
  amount_total: number;
  delivery_status: string;
  invoice_status: string;
}

const stateColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-800',
  confirmed: 'bg-blue-100 text-blue-800',
  done: 'bg-green-100 text-green-800',
  cancelled: 'bg-red-100 text-red-600',
};

const stateLabels: Record<string, string> = {
  draft: 'مسودة',
  confirmed: 'مؤكد',
  done: 'تم التنفيذ',
  cancelled: 'ملغي',
};

export const SaleOrdersPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [stateFilter, setStateFilter] = useState<string>('');

  const { data, isLoading } = useQuery({
    queryKey: ['sale-orders', page, stateFilter],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20',
        ...(stateFilter && { state: stateFilter }),
      });
      const response = await api.get(`/sales/orders?${params}`);
      return response.data;
    },
  });

  const confirmMutation = useMutation({
    mutationFn: async (id: string) => {
      return await api.post(`/sales/orders/${id}/confirm`, {
        create_delivery: true,
        create_invoice: false,
      });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sale-orders'] }),
  });

  const cancelMutation = useMutation({
    mutationFn: async (id: string) => {
      return await api.post(`/sales/orders/${id}/cancel`, { reason: 'طلب إلغاء' });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sale-orders'] }),
  });

  const createInvoiceMutation = useMutation({
    mutationFn: async (id: string) => {
      return await api.post(`/sales/orders/${id}/invoice`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sale-orders'] });
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
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
          <h1 className="text-2xl font-bold text-gray-900">أوامر البيع</h1>
          <p className="text-gray-500">إدارة أوامر بيع المبيعات</p>
        </div>
        <button
          onClick={() => navigate('/sales/orders/new')}
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <PlusIcon className="h-5 w-5 ml-2" />
          أمر بيع جديد
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
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">رقم الأمر</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">الاسم</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">التاريخ</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">المبلغ</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">التسليم</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">الفاتورة</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">الحالة</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">الإجراءات</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {data?.items?.map((order: SaleOrder) => (
              <tr key={order.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 text-sm font-medium text-blue-600">{order.number}</td>
                <td className="px-6 py-4 text-sm text-gray-900">{order.name}</td>
                <td className="px-6 py-4 text-sm text-gray-500">{formatDate(order.date_order)}</td>
                <td className="px-6 py-4 text-sm text-gray-900">{formatCurrency(order.amount_total)}</td>
                <td className="px-6 py-4 text-sm">
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    order.delivery_status === 'done' ? 'bg-green-100 text-green-800' :
                    order.delivery_status === 'partial' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    {order.delivery_status === 'done' ? 'تم' : order.delivery_status === 'partial' ? 'جزئي' : 'لا'}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm">
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    order.invoice_status === 'invoiced' ? 'bg-green-100 text-green-800' :
                    order.invoice_status === 'partial' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    {order.invoice_status === 'invoiced' ? 'فاتورة' : order.invoice_status === 'partial' ? 'جزئي' : 'لا'}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 text-xs rounded-full ${stateColors[order.state]}`}>
                    {stateLabels[order.state]}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm">
                  <div className="flex gap-2">
                    <button onClick={() => navigate(`/sales/orders/${order.id}`)} className="text-blue-600">
                      <EyeIcon className="h-5 w-5" />
                    </button>
                    {order.state === 'draft' && (
                      <>
                        <button onClick={() => navigate(`/sales/orders/${order.id}/edit`)} className="text-yellow-600">
                          <PencilIcon className="h-5 w-5" />
                        </button>
                        <button onClick={() => confirmMutation.mutate(order.id)} className="text-green-600">
                          <CheckCircleIcon className="h-5 w-5" />
                        </button>
                        <button onClick={() => cancelMutation.mutate(order.id)} className="text-red-600">
                          <XCircleIcon className="h-5 w-5" />
                        </button>
                      </>
                    )}
                    {order.state === 'confirmed' && order.invoice_status !== 'invoiced' && (
                      <button onClick={() => createInvoiceMutation.mutate(order.id)} className="text-purple-600">
                        <DocumentDuplicateIcon className="h-5 w-5" />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data && data.total_pages > 1 && (
        <div className="flex justify-center gap-2">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >
            السابق
          </button>
          <span className="px-3 py-1">{page} من {data.total_pages}</span>
          <button
            onClick={() => setPage(p => Math.min(data.total_pages, p + 1))}
            disabled={page === data.total_pages}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >
            التالي
          </button>
        </div>
      )}
    </div>
  );
};

export default SaleOrdersPage;
