import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/layout/Layout'
import LoginPage from './pages/auth/LoginPage'
import DashboardPage from './pages/DashboardPage'
import CustomersPage from './pages/crm/CustomersPage'
import CustomerDetailPage from './pages/crm/CustomerDetailPage'
import LeadsPage from './pages/crm/LeadsPage'
import OpportunitiesPage from './pages/crm/OpportunitiesPage'
import { useAuthStore } from './stores/authStore'

// Accounting Pages
import ChartOfAccounts from './pages/accounts/ChartOfAccounts'
import JournalEntryForm from './pages/accounts/JournalEntryForm'
import FinancialReports from './pages/accounts/FinancialReports'
import GeneralLedger from './pages/accounts/GeneralLedger'

// Inventory Pages
import ProductList from './pages/products/ProductList'
import WarehousesPage from './pages/products/Warehouses'
import StockLevelsPage from './pages/products/StockLevels'
import StockMovements from './pages/inventory/StockMovements'
import InventoryAdjustments from './pages/products/InventoryAdjustments'

// Sales Pages
import QuotationsPage from './pages/sales/QuotationsPage'
import SaleOrdersPage from './pages/sales/SaleOrdersPage'
import InvoicesPage from './pages/sales/InvoicesPage'

// Purchasing Pages
import PurchaseOrdersPage from './pages/purchase/PurchaseOrdersPage'
import SuppliersPage from './pages/purchasing/SuppliersPage'

// HR Pages
import EmployeesPage from './pages/hr/EmployeesPage'
import AttendancePage from './pages/hr/AttendancePage'
import PayrollPage from './pages/hr/PayrollPage'

// Manufacturing Pages
import ManufacturingOrdersPage from './pages/manufacturing/ManufacturingOrdersPage'

// Projects Pages
import ProjectsPage from './pages/projects/ProjectsPage'
import TasksPage from './pages/projects/TasksPage'
import TimesheetsPage from './pages/projects/TimesheetsPage'

// POS Page
import POSPage from './pages/pos/POSPage'

// Reports Page
import ReportsPage from './pages/reports/ReportsPage'

// Settings Page
import SettingsPage from './pages/settings/SettingsPage'

// AI Dashboard
import AIDashboardPage from './pages/ai/AIDashboardPage'

function App() {
  const { isAuthenticated } = useAuthStore()

  return (
    <BrowserRouter>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={
          isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />
        } />

        {/* Protected Routes */}
        <Route path="/" element={
          isAuthenticated ? <Layout /> : <Navigate to="/login" replace />
        }>
          {/* Dashboard */}
          <Route index element={<DashboardPage />} />

          {/* CRM Module */}
          <Route path="crm">
            <Route path="customers" element={<CustomersPage />} />
            <Route path="customers/:id" element={<CustomerDetailPage />} />
            <Route path="leads" element={<LeadsPage />} />
            <Route path="opportunities" element={<OpportunitiesPage />} />
          </Route>

          {/* Sales Module */}
          <Route path="sales">
            <Route path="quotes" element={<QuotationsPage />} />
            <Route path="orders" element={<SaleOrdersPage />} />
            <Route path="invoices" element={<InvoicesPage />} />
          </Route>

          {/* Inventory Module */}
          <Route path="inventory">
            <Route path="products" element={<ProductList />} />
            <Route path="warehouses" element={<WarehousesPage />} />
            <Route path="stock" element={<StockLevelsPage />} />
            <Route path="movements" element={<StockMovements />} />
            <Route path="adjustments" element={<InventoryAdjustments />} />
          </Route>

          {/* Purchasing Module */}
          <Route path="purchasing">
            <Route path="orders" element={<PurchaseOrdersPage />} />
            <Route path="suppliers" element={<SuppliersPage />} />
          </Route>

          {/* Accounting Module */}
          <Route path="accounting">
            <Route path="chart-of-accounts" element={<ChartOfAccounts />} />
            <Route path="journal-entries" element={<JournalEntryForm />} />
            <Route path="reports" element={<FinancialReports />} />
            <Route path="general-ledger" element={<GeneralLedger />} />
          </Route>

          {/* HR Module */}
          <Route path="hr">
            <Route path="employees" element={<EmployeesPage />} />
            <Route path="attendance" element={<AttendancePage />} />
            <Route path="payroll" element={<PayrollPage />} />
          </Route>

          {/* Projects Module */}
          <Route path="projects">
            <Route index element={<ProjectsPage />} />
            <Route path="tasks" element={<TasksPage />} />
            <Route path="timesheets" element={<TimesheetsPage />} />
            <Route path=":id" element={<ProjectsPage />} />
          </Route>

          {/* Manufacturing Module */}
          <Route path="manufacturing">
            <Route path="bom" element={<ManufacturingOrdersPage />} />
            <Route path="orders" element={<ManufacturingOrdersPage />} />
          </Route>

          {/* POS Module */}
          <Route path="pos" element={<POSPage />} />

          {/* Reports */}
          <Route path="reports" element={<ReportsPage />} />

          {/* AI Dashboard */}
          <Route path="ai" element={<AIDashboardPage />} />

          {/* Settings */}
          <Route path="settings" element={<SettingsPage />} />
        </Route>

        {/* Catch all - 404 */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  )
}

const NotFoundPage = () => (
  <div className="min-h-screen flex items-center justify-center bg-slate-50">
    <div className="text-center">
      <h1 className="text-6xl font-bold text-slate-300">404</h1>
      <p className="text-xl text-slate-600 mt-4">Page not found</p>
      <a href="/" className="btn btn-primary mt-6">Go Home</a>
    </div>
  </div>
)

export default App
