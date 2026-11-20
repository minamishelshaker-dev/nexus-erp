/**
 * Nexus ERP - POS Page
 * Point of Sale interface
 */

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../services/api'
import {
  Search,
  ShoppingCart,
  User,
  CreditCard,
  Banknote,
  Smartphone,
  Trash2,
  Plus,
  Minus,
  X,
  Printer,
  Send,
  CheckCircle,
  Package,
  Grid,
  List,
  DollarSign,
  Receipt,
} from 'lucide-react'

interface POSProduct {
  id: string
  code: string
  name: string
  price: number
  uom: string
  barcode?: string
  category_id: string
  category_name: string
  quantity_available: number
  image_url?: string
  tax_rate: number
}

interface POSCategory {
  id: string
  name: string
  product_count: number
}

interface CartItem {
  product: POSProduct
  quantity: number
  discount: number
  notes?: string
}

interface POSSession {
  id: string
  config_name: string
  state: string
  opening_balance: number
  total_sales: number
}

export default function POSPage() {
  const queryClient = useQueryClient()
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')
  const [cart, setCart] = useState<CartItem[]>([])
  const [selectedCustomer, setSelectedCustomer] = useState<{ id: string; name: string } | null>(null)
  const [showPaymentModal, setShowPaymentModal] = useState(false)
  const [showNewSessionModal, setShowNewSessionModal] = useState(false)
  const [openingBalance, setOpeningBalance] = useState('')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')

  // Get active session
  const { data: activeSession } = useQuery({
    queryKey: ['pos-active-session'],
    queryFn: async () => {
      const response = await api.get('/pos/sessions/active')
      return response.data as POSSession | null
    },
  })

  // Fetch categories
  const { data: categories } = useQuery({
    queryKey: ['pos-categories'],
    queryFn: async () => {
      const response = await api.get('/pos/categories')
      return response.data as POSCategory[]
    },
  })

  // Fetch products
  const { data: products } = useQuery({
    queryKey: ['pos-products', selectedCategory, searchQuery],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (selectedCategory) params.append('category_id', selectedCategory)
      if (searchQuery) params.append('search', searchQuery)
      const response = await api.get(`/pos/products?${params}`)
      return response.data as POSProduct[]
    },
    enabled: !!activeSession,
  })

  // Create session mutation
  const createSessionMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post('/pos/sessions/open', {
        config_id: 'default',
        opening_balance: parseFloat(openingBalance) || 0,
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pos-active-session'] })
      setShowNewSessionModal(false)
      setOpeningBalance('')
    },
  })

  // Create order mutation
  const createOrderMutation = useMutation({
    mutationFn: async (paymentData: { payments: { method: string; amount: number }[] }) => {
      const orderData = {
        session_id: activeSession?.id,
        customer_id: selectedCustomer?.id,
        lines: cart.map(item => ({
          product_id: item.product.id,
          quantity: item.quantity,
          discount: item.discount,
          notes: item.notes,
        })),
        payments: paymentData.payments,
      }
      const response = await api.post('/pos/orders', orderData)
      return response.data
    },
    onSuccess: () => {
      setCart([])
      setSelectedCustomer(null)
      setShowPaymentModal(false)
      queryClient.invalidateQueries({ queryKey: ['pos-active-session'] })
    },
  })

  // Barcode scanner handler
  useEffect(() => {
    const handleKeyDown = async (e: KeyboardEvent) => {
      if (e.key === 'Enter' && searchQuery.length > 3) {
        // Try to find product by barcode
        try {
          const response = await api.get(`/pos/products/barcode/${searchQuery}`)
          const product = response.data as POSProduct
          addToCart(product)
          setSearchQuery('')
        } catch {
          // Not a barcode, it's a search query
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [searchQuery])

  const addToCart = (product: POSProduct) => {
    setCart(prev => {
      const existing = prev.find(item => item.product.id === product.id)
      if (existing) {
        return prev.map(item =>
          item.product.id === product.id
            ? { ...item, quantity: item.quantity + 1 }
            : item
        )
      }
      return [...prev, { product, quantity: 1, discount: 0 }]
    })
  }

  const updateQuantity = (productId: string, delta: number) => {
    setCart(prev =>
      prev.map(item => {
        if (item.product.id === productId) {
          const newQty = item.quantity + delta
          return newQty > 0 ? { ...item, quantity: newQty } : item
        }
        return item
      }).filter(item => item.quantity > 0)
    )
  }

  const removeFromCart = (productId: string) => {
    setCart(prev => prev.filter(item => item.product.id !== productId))
  }

  const clearCart = () => {
    setCart([])
    setSelectedCustomer(null)
  }

  // Calculate totals
  const subtotal = cart.reduce((sum, item) => sum + (item.product.price * item.quantity), 0)
  const totalDiscount = cart.reduce((sum, item) => sum + (item.product.price * item.quantity * item.discount / 100), 0)
  const taxAmount = cart.reduce((sum, item) => sum + (item.product.price * item.quantity * item.product.tax_rate / 100), 0)
  const total = subtotal - totalDiscount + taxAmount

  // If no active session, show session start modal
  if (!activeSession && !showNewSessionModal) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <ShoppingCart className="w-16 h-16 text-slate-300 mx-auto" />
          <h2 className="text-xl font-semibold text-slate-900 mt-4">No Active Session</h2>
          <p className="text-slate-500 mt-2">Start a new POS session to begin selling</p>
          <button
            onClick={() => setShowNewSessionModal(true)}
            className="btn btn-primary mt-4"
          >
            <Plus className="w-4 h-4" />
            Start New Session
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-[calc(100vh-120px)] -mx-6 -mb-6">
      {/* Left Panel - Products */}
      <div className="flex-1 flex flex-col border-r border-slate-200 bg-slate-50">
        {/* Search & Categories */}
        <div className="p-4 border-b border-slate-200 bg-white">
          <div className="flex gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="text"
                placeholder="Search products or scan barcode..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div className="flex bg-slate-100 rounded-lg p-1">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-2 rounded ${viewMode === 'grid' ? 'bg-white shadow-sm' : ''}`}
              >
                <Grid className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-2 rounded ${viewMode === 'list' ? 'bg-white shadow-sm' : ''}`}
              >
                <List className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Categories */}
        <div className="px-4 py-2 border-b border-slate-200 bg-white overflow-x-auto">
          <div className="flex gap-2">
            <button
              onClick={() => setSelectedCategory('')}
              className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                !selectedCategory ? 'bg-primary-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              All
            </button>
            {categories?.map((category) => (
              <button
                key={category.id}
                onClick={() => setSelectedCategory(category.id)}
                className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                  selectedCategory === category.id
                    ? 'bg-primary-600 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {category.name}
              </button>
            ))}
          </div>
        </div>

        {/* Products Grid */}
        <div className="flex-1 overflow-y-auto p-4">
          {viewMode === 'grid' ? (
            <div className="grid grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
              {products?.map((product) => (
                <button
                  key={product.id}
                  onClick={() => addToCart(product)}
                  disabled={product.quantity_available <= 0}
                  className="bg-white rounded-lg p-3 text-left hover:shadow-md transition-shadow disabled:opacity-50 disabled:cursor-not-allowed border border-slate-200"
                >
                  <div className="aspect-square bg-slate-100 rounded-lg mb-2 flex items-center justify-center">
                    <Package className="w-8 h-8 text-slate-400" />
                  </div>
                  <p className="font-medium text-slate-900 text-sm truncate">{product.name}</p>
                  <p className="text-xs text-slate-500">{product.code}</p>
                  <div className="flex items-center justify-between mt-1">
                    <p className="font-semibold text-primary-600">
                      ${product.price.toFixed(2)}
                    </p>
                    <span className={`text-xs ${product.quantity_available > 0 ? 'text-green-600' : 'text-red-500'}`}>
                      {product.quantity_available > 0 ? `${product.quantity_available} in stock` : 'Out of stock'}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {products?.map((product) => (
                <button
                  key={product.id}
                  onClick={() => addToCart(product)}
                  disabled={product.quantity_available <= 0}
                  className="w-full bg-white rounded-lg p-3 flex items-center gap-4 hover:shadow-md transition-shadow disabled:opacity-50 disabled:cursor-not-allowed border border-slate-200"
                >
                  <div className="w-12 h-12 bg-slate-100 rounded-lg flex items-center justify-center">
                    <Package className="w-6 h-6 text-slate-400" />
                  </div>
                  <div className="flex-1 text-left">
                    <p className="font-medium text-slate-900">{product.name}</p>
                    <p className="text-sm text-slate-500">{product.code}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-primary-600">${product.price.toFixed(2)}</p>
                    <p className={`text-xs ${product.quantity_available > 0 ? 'text-green-600' : 'text-red-500'}`}>
                      {product.quantity_available > 0 ? `${product.quantity_available} in stock` : 'Out'}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right Panel - Cart */}
      <div className="w-96 flex flex-col bg-white">
        {/* Cart Header */}
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShoppingCart className="w-5 h-5 text-slate-400" />
            <h2 className="font-semibold text-slate-900">Cart</h2>
            <span className="bg-primary-100 text-primary-600 text-sm px-2 py-0.5 rounded-full">
              {cart.length}
            </span>
          </div>
          {cart.length > 0 && (
            <button
              onClick={clearCart}
              className="text-red-500 hover:text-red-600 text-sm"
            >
              Clear All
            </button>
          )}
        </div>

        {/* Customer Selection */}
        <div className="px-4 py-3 border-b border-slate-200">
          <button className="w-full flex items-center gap-3 p-2 rounded-lg border border-slate-200 hover:bg-slate-50">
            <User className="w-5 h-5 text-slate-400" />
            {selectedCustomer ? (
              <span className="text-slate-900">{selectedCustomer.name}</span>
            ) : (
              <span className="text-slate-500">Select Customer (optional)</span>
            )}
          </button>
        </div>

        {/* Cart Items */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {cart.length === 0 ? (
            <div className="text-center py-8">
              <ShoppingCart className="w-12 h-12 text-slate-300 mx-auto" />
              <p className="text-slate-500 mt-2">Cart is empty</p>
              <p className="text-slate-400 text-sm">Add products to get started</p>
            </div>
          ) : (
            cart.map((item) => (
              <div key={item.product.id} className="bg-slate-50 rounded-lg p-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="font-medium text-slate-900">{item.product.name}</p>
                    <p className="text-sm text-slate-500">${item.product.price.toFixed(2)} each</p>
                  </div>
                  <button
                    onClick={() => removeFromCart(item.product.id)}
                    className="p-1 text-slate-400 hover:text-red-500"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                <div className="flex items-center justify-between mt-2">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => updateQuantity(item.product.id, -1)}
                      className="p-1 rounded bg-white border border-slate-200 hover:bg-slate-100"
                    >
                      <Minus className="w-4 h-4" />
                    </button>
                    <span className="w-8 text-center font-medium">{item.quantity}</span>
                    <button
                      onClick={() => updateQuantity(item.product.id, 1)}
                      className="p-1 rounded bg-white border border-slate-200 hover:bg-slate-100"
                    >
                      <Plus className="w-4 h-4" />
                    </button>
                  </div>
                  <p className="font-semibold text-slate-900">
                    ${(item.product.price * item.quantity).toFixed(2)}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Totals */}
        <div className="p-4 border-t border-slate-200 space-y-2">
          <div className="flex justify-between text-sm text-slate-600">
            <span>Subtotal</span>
            <span>${subtotal.toFixed(2)}</span>
          </div>
          {totalDiscount > 0 && (
            <div className="flex justify-between text-sm text-green-600">
              <span>Discount</span>
              <span>-${totalDiscount.toFixed(2)}</span>
            </div>
          )}
          <div className="flex justify-between text-sm text-slate-600">
            <span>Tax</span>
            <span>${taxAmount.toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-lg font-bold text-slate-900 pt-2 border-t border-slate-200">
            <span>Total</span>
            <span>${total.toFixed(2)}</span>
          </div>
        </div>

        {/* Payment Buttons */}
        <div className="p-4 border-t border-slate-200 space-y-2">
          <button
            onClick={() => setShowPaymentModal(true)}
            disabled={cart.length === 0}
            className="btn btn-primary w-full py-3 text-lg"
          >
            <CreditCard className="w-5 h-5" />
            Payment
          </button>
          <div className="grid grid-cols-3 gap-2">
            <button
              onClick={() => cart.length > 0 && createOrderMutation.mutate({ payments: [{ method: 'cash', amount: total }] })}
              disabled={cart.length === 0}
              className="btn btn-secondary flex flex-col items-center py-2"
            >
              <Banknote className="w-5 h-5" />
              <span className="text-xs mt-1">Cash</span>
            </button>
            <button
              onClick={() => cart.length > 0 && createOrderMutation.mutate({ payments: [{ method: 'card', amount: total }] })}
              disabled={cart.length === 0}
              className="btn btn-secondary flex flex-col items-center py-2"
            >
              <CreditCard className="w-5 h-5" />
              <span className="text-xs mt-1">Card</span>
            </button>
            <button
              onClick={() => cart.length > 0 && createOrderMutation.mutate({ payments: [{ method: 'mobile', amount: total }] })}
              disabled={cart.length === 0}
              className="btn btn-secondary flex flex-col items-center py-2"
            >
              <Smartphone className="w-5 h-5" />
              <span className="text-xs mt-1">Mobile</span>
            </button>
          </div>
        </div>
      </div>

      {/* New Session Modal */}
      {showNewSessionModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold text-slate-900 mb-4">Start New Session</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Opening Cash Balance</label>
                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input
                    type="number"
                    value={openingBalance}
                    onChange={(e) => setOpeningBalance(e.target.value)}
                    placeholder="0.00"
                    className="input pl-10"
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowNewSessionModal(false)}
                  className="btn btn-secondary flex-1"
                >
                  Cancel
                </button>
                <button
                  onClick={() => createSessionMutation.mutate()}
                  disabled={createSessionMutation.isPending}
                  className="btn btn-primary flex-1"
                >
                  Start Session
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Payment Modal */}
      {showPaymentModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-slate-900">Payment</h2>
              <button onClick={() => setShowPaymentModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-6 h-6" />
              </button>
            </div>
            <div className="text-center mb-6">
              <p className="text-3xl font-bold text-slate-900">${total.toFixed(2)}</p>
              <p className="text-slate-500">Amount Due</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => createOrderMutation.mutate({ payments: [{ method: 'cash', amount: total }] })}
                className="btn btn-secondary py-4 flex flex-col items-center"
              >
                <Banknote className="w-6 h-6" />
                <span className="mt-1">Cash</span>
              </button>
              <button
                onClick={() => createOrderMutation.mutate({ payments: [{ method: 'card', amount: total }] })}
                className="btn btn-secondary py-4 flex flex-col items-center"
              >
                <CreditCard className="w-6 h-6" />
                <span className="mt-1">Card</span>
              </button>
              <button
                onClick={() => createOrderMutation.mutate({ payments: [{ method: 'mobile', amount: total }] })}
                className="btn btn-secondary py-4 flex flex-col items-center"
              >
                <Smartphone className="w-6 h-6" />
                <span className="mt-1">Mobile</span>
              </button>
              <button
                onClick={() => createOrderMutation.mutate({ payments: [{ method: 'check', amount: total }] })}
                className="btn btn-secondary py-4 flex flex-col items-center"
              >
                <Receipt className="w-6 h-6" />
                <span className="mt-1">Check</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
