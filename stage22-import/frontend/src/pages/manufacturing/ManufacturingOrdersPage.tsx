/**
 * Nexus ERP - Manufacturing Orders Page
 * ======================================
 * Manufacturing order management and BOM listing
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  PlusIcon,
  PlayIcon,
  CheckCircleIcon,
  XCircleIcon,
  EyeIcon,
  CogIcon,
  BeakerIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';

interface ManufacturingOrder {
  id: string;
  number: string;
  name: string;
  product_id: string;
  product_qty: number;
  qty_produced: number;
  progress_percent: number;
  state: string;
  planned_date: string;
  total_cost: number;
}

const stateColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-800',
  confirmed: 'bg-blue-100 text-blue-800',
  planned: 'bg-indigo-100 text-indigo-800',
  in_progress: 'bg-yellow-100 text-yellow-800',
  done: 'bg-green-100 text-green-800',
  cancelled: 'bg-red-100 text-red-600',
};

const stateLabels: Record<string, string> = {
  draft: 'مسودة',
  confirmed: 'مؤكد',
  planned: 'مخطط',
  in_progress: 'قيد التنفيذ',
  done: 'منجز',
  cancelled: 'ملغي',
};

export const ManufacturingOrdersPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [stateFilter, setStateFilter] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'orders' | 'boms'>('orders');

  // Fetch manufacturing orders
  const { data, isLoading } = useQuery({
    queryKey: ['manufacturing-orders', page, stateFilter],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20',
        ...(stateFilter && { state: stateFilter }),
      });
      const response = await api.get(`/manufacturing/orders?${params}`);
      return response.data;
    },
  });

  // Fetch BOMs
  const { data: bomsData, isLoading: bomsLoading } = useQuery({
    queryKey: ['boms'],
    queryFn: async () => {
      const response = await api.get('/manufacturing/boms');
      return response.data;
    },
    enabled: activeTab === 'boms',
  });

  // Confirm MO mutation
  const confirmMutation = useMutation({
    mutationFn: async (id: string) => {
      return await api.post(`/manufacturing/orders/${id}/confirm`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['manufacturing-orders'] }),
  });

  // Start MO mutation
  const startMutation = useMutation({
    mutationFn: async (id: string) => {
      return await api.post(`/manufacturing/orders/${id}/start`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['manufacturing-orders'] }),
  });

  // Finish MO mutation
  const finishMutation = useMutation({
    mutationFn: async (id: string) => {
      return await api.post(`/manufacturing/orders/${id}/finish`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['manufacturing-orders'] }),
  });

  // Cancel MO mutation
  const cancelMutation = useMutation({
    mutationFn: async (id: string) => {
      return await api.post(`/manufacturing/orders/${id}/cancel`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['manufacturing-orders'] }),
  });

  const formatCurrency = (amount: number) => 
    new Intl.NumberFormat('ar-SA', { style: 'currency', currency: 'SAR' }).format(amount);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">التصنيع</h1>
          <p className="text-gray-500">إدارة أوامر التصنيع وقوائم المواد</p>
        </div>
        <button
          onClick={() => navigate('/manufacturing/orders/new')}
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <PlusIcon className="h-5 w-5 ml-2" />
          أمر تصنيع جديد
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('orders')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'orders'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <CogIcon className="h-5 w-5 inline mr-2" />
            أوامر التصنيع
          </button>
          <button
            onClick={() => setActiveTab('boms')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'boms'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <BeakerIcon className="h-5 w-5 inline mr-2" />
            قوائم المواد
          </button>
        </nav>
      </div>

      {/* Manufacturing Orders Tab */}
      {activeTab === 'orders' && (
        <>
          {/* Filter */}
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

          {/* Orders Table */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">رقم الأمر</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">الاسم</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">الكمية</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">المنجز</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">التقدم</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">التاريخ</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">الحالة</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">التكلفة</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">الإجراءات</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {data?.items?.map((order: ManufacturingOrder) => (
                  <tr key={order.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-medium text-blue-600">{order.number}</td>
                    <td className="px-6 py-4 text-sm text-gray-900">{order.name}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">{order.product_qty}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">{order.qty_produced}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <div className="w-24 bg-gray-200 rounded-full h-2 ml-2">
                          <div 
                            className="bg-blue-600 h-2 rounded-full" 
                            style={{ width: `${order.progress_percent}%` }}
                          ></div>
                        </div>
                        <span className="text-sm text-gray-500">{order.progress_percent.toFixed(0)}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {order.planned_date ? new Date(order.planned_date).toLocaleDateString('ar-SA') : '-'}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 text-xs rounded-full ${stateColors[order.state]}`}>
                        {stateLabels[order.state]}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">{formatCurrency(order.total_cost)}</td>
                    <td className="px-6 py-4 text-sm">
                      <div className="flex gap-2">
                        <button onClick={() => navigate(`/manufacturing/orders/${order.id}`)} className="text-blue-600">
                          <EyeIcon className="h-5 w-5" />
                        </button>
                        {order.state === 'draft' && (
                          <>
                            <button 
                              onClick={() => confirmMutation.mutate(order.id)} 
                              className="text-green-600"
                              title="تأكيد"
                            >
                              <CheckCircleIcon className="h-5 w-5" />
                            </button>
                            <button 
                              onClick={() => cancelMutation.mutate(order.id)} 
                              className="text-red-600"
                              title="إلغاء"
                            >
                              <XCircleIcon className="h-5 w-5" />
                            </button>
                          </>
                        )}
                        {order.state === 'confirmed' && (
                          <button 
                            onClick={() => startMutation.mutate(order.id)} 
                            className="text-yellow-600"
                            title="بدء الإنتاج"
                          >
                            <PlayIcon className="h-5 w-5" />
                          </button>
                        )}
                        {order.state === 'in_progress' && (
                          <button 
                            onClick={() => finishMutation.mutate(order.id)} 
                            className="text-green-600"
                            title="إنهاء"
                          >
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

          {/* Pagination */}
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
        </>
      )}

      {/* BOMs Tab */}
      {activeTab === 'boms' && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">الكود</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">الاسم</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">النوع</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">الكمية</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">الحالة</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">التكلفة الكلية</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">البنود</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {bomsData?.items?.map((bom: any) => (
                <tr key={bom.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm font-medium text-blue-600">{bom.code}</td>
                  <td className="px-6 py-4 text-sm text-gray-900">{bom.name}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">{bom.bom_type}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">{bom.product_qty}</td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 text-xs rounded-full ${
                      bom.state === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {bom.state === 'active' ? 'نشط' : 'مسودة'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">{formatCurrency(bom.total_cost)}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">{bom.line_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default ManufacturingOrdersPage;
