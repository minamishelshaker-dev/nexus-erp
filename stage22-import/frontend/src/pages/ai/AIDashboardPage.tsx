/**
 * Nexus ERP - AI Dashboard Page
 * ===============================
 * Main AI features dashboard with forecasting and chatbot
 */

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ChartBarIcon,
  ChatBubbleLeftRightIcon,
  DocumentTextIcon,
  LightBulbIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';

export const AIDashboardPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'forecast' | 'ocr' | 'chat'>('forecast');
  const [chatMessage, setChatMessage] = useState('');
  const [chatSessionId, setChatSessionId] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<{role: string, content: string}[]>([]);
  
  const queryClient = useQueryClient();

  // Fetch forecast dashboard
  const { data: forecastData, isLoading: forecastLoading } = useQuery({
    queryKey: ['ai-forecast-dashboard'],
    queryFn: async () => {
      const response = await api.get('/ai/forecast/dashboard?top_n=10');
      return response.data;
    },
  });

  // Create chat session mutation
  const createSessionMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post('/ai/chat/session', {});
      return response.data;
    },
  });

  // Send chat message mutation
  const sendMessageMutation = useMutation({
    mutationFn: async (message: string) => {
      const sessionId = chatSessionId || (await createSessionMutation.mutateAsync()).session_id;
      setChatSessionId(sessionId);
      
      const response = await api.post('/ai/chat/message', {
        session_id: sessionId,
        message,
      });
      return response.data;
    },
    onSuccess: (data) => {
      setChatMessages(prev => [
        ...prev,
        { role: 'user', content: chatMessage },
        { role: 'assistant', content: data.content }
      ]);
      setChatMessage('');
    },
  });

  const handleSendMessage = () => {
    if (chatMessage.trim()) {
      sendMessageMutation.mutate(chatMessage);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">الذكاء الاصطناعي</h1>
          <p className="text-gray-500">تنبؤات المخزون، تحليل الفواتير، المساعد الذكي</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('forecast')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'forecast'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <ChartBarIcon className="h-5 w-5 inline mr-2" />
            تنبؤات المخزون
          </button>
          <button
            onClick={() => setActiveTab('ocr')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'ocr'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <DocumentTextIcon className="h-5 w-5 inline mr-2" />
            تحليل الفواتير
          </button>
          <button
            onClick={() => setActiveTab('chat')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'chat'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <ChatBubbleLeftRightIcon className="h-5 w-5 inline mr-2" />
            المساعد الذكي
          </button>
        </nav>
      </div>

      {/* Forecast Tab */}
      {activeTab === 'forecast' && (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <ChartBarIcon className="h-8 w-8 text-blue-600" />
                <div className="mr-4">
                  <p className="text-sm text-gray-500">المنتجات المحللة</p>
                  <p className="text-2xl font-bold">
                    {forecastData?.summary?.total_products_analyzed || 0}
                  </p>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <ExclamationTriangleIcon className="h-8 w-8 text-red-600" />
                <div className="mr-4">
                  <p className="text-sm text-gray-500">خطر نفاد المخزون</p>
                  <p className="text-2xl font-bold text-red-600">
                    {forecastData?.summary?.potential_stockouts || 0}
                  </p>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <LightBulbIcon className="h-8 w-8 text-yellow-600" />
                <div className="mr-4">
                  <p className="text-sm text-gray-500">منتجات طلب عالي</p>
                  <p className="text-2xl font-bold">
                    {forecastData?.summary?.high_demand_products || 0}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Alerts */}
          {forecastData?.alerts?.length > 0 && (
            <div className="bg-red-50 rounded-lg p-4">
              <h3 className="text-lg font-medium text-red-800 mb-2">تنبيهات هامة</h3>
              <ul className="space-y-2">
                {forecastData.alerts.map((alert: any, idx: number) => (
                  <li key={idx} className="flex items-center text-red-700">
                    <ExclamationTriangleIcon className="h-5 w-5 ml-2" />
                    <span>
                      <strong>{alert.product_name}</strong>: المخزون الحالي {alert.current_stock}، 
                      الطلب المتوقع {alert.predicted_demand}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Forecast Table */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">المنتج</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">المخزون الحالي</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">الطلب المتوقع</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">خطر النفاد</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">الكمية المقترحة</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {forecastData?.forecasts?.map((item: any, idx: number) => (
                  <tr key={idx} className={item.stockout_risk ? 'bg-red-50' : ''}>
                    <td className="px-6 py-4 text-sm text-gray-900">{item.product_name}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">{item.current_stock}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">{item.predicted_demand}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        item.stockout_risk ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                      }`}>
                        {item.stockout_risk ? 'نعم' : 'لا'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm font-medium text-blue-600">
                      {item.reorder_quantity > 0 ? item.reorder_quantity : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* OCR Tab */}
      {activeTab === 'ocr' && (
        <div className="bg-white rounded-lg shadow p-6">
          <OCRUpload />
        </div>
      )}

      {/* Chat Tab */}
      {activeTab === 'chat' && (
        <div className="bg-white rounded-lg shadow h-[600px] flex flex-col">
          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {chatMessages.length === 0 && (
              <div className="text-center text-gray-500 mt-20">
                <ChatBubbleLeftRightIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p>مرحباً! أنا المساعد الذكي لنظام Nexus ERP.</p>
                <p className="text-sm mt-2">يمكنني مساعدتك في:</p>
                <ul className="text-sm mt-2 space-y-1">
                  <li>الاستعلام عن المخزون والمبيعات</li>
                  <li>إنشاء أوامر البيع والشراء</li>
                  <li>تحليل البيانات وتقديم التوصيات</li>
                </ul>
              </div>
            )}
            {chatMessages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-start' : 'justify-end'}`}>
                <div className={`max-w-[70%] rounded-lg p-3 ${
                  msg.role === 'user' ? 'bg-blue-100 text-blue-900' : 'bg-gray-100 text-gray-900'
                }`}>
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            ))}
            {sendMessageMutation.isPending && (
              <div className="flex justify-end">
                <div className="bg-gray-100 rounded-lg p-3">
                  <div className="flex space-x-2">
                    <div className="h-2 w-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="h-2 w-2 bg-gray-400 rounded-full animate-bounce delay-100"></div>
                    <div className="h-2 w-2 bg-gray-400 rounded-full animate-bounce delay-200"></div>
                  </div>
                </div>
              </div>
            )}
          </div>
          
          {/* Chat Input */}
          <div className="border-t p-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                placeholder="اكتب رسالتك هنا..."
                className="flex-1 border rounded-lg px-4 py-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <button
                onClick={handleSendMessage}
                disabled={sendMessageMutation.isPending}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                إرسال
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// OCR Upload Component
const OCRUpload: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<any>(null);
  const [uploading, setUploading] = useState(false);

  const handleUpload = async () => {
    if (!file) return;
    
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await api.post('/ai/parse-invoice', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setResult(response.data);
    } catch (error) {
      console.error('OCR error:', error);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
        <DocumentTextIcon className="h-12 w-12 mx-auto text-gray-400" />
        <p className="mt-4 text-gray-600">ارفع صورة الفاتورة أو ملف PDF</p>
        <input
          type="file"
          accept="image/*,.pdf"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="mt-4"
        />
      </div>
      
      {file && (
        <button
          onClick={handleUpload}
          disabled={uploading}
          className="w-full py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {uploading ? 'جاري التحليل...' : 'تحليل الفاتورة'}
        </button>
      )}
      
      {result && (
        <div className="border rounded-lg p-4">
          <h3 className="font-bold mb-4">نتائج التحليل</h3>
          <div className="space-y-2">
            <p><strong>رقم الفاتورة:</strong> {result.invoice_number || '-'}</p>
            <p><strong>التاريخ:</strong> {result.invoice_date || '-'}</p>
            <p><strong>المورد:</strong> {result.partner_name || '-'}</p>
            <p><strong>الإجمالي:</strong> {result.total_amount || '-'}</p>
            <p><strong>مستوى الثقة:</strong> {(result.confidence * 100).toFixed(0)}%</p>
          </div>
          {result.validation_errors?.length > 0 && (
            <div className="mt-4 text-red-600">
              <p className="font-medium">أخطاء:</p>
              <ul className="list-disc mr-4">
                {result.validation_errors.map((err: string, i: number) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AIDashboardPage;
