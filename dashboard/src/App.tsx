import { Suspense, lazy } from 'react'
import { HashRouter, Routes, Route, NavLink } from 'react-router-dom'
import { DataProvider, useData } from './context/DataContext'
import { FilterProvider } from './context/FilterContext'
import './styles/index.css'

const HeatmapPage = lazy(() => import('./pages/HeatmapPage'))
const DatabasePage = lazy(() => import('./pages/DatabasePage'))
const SignalsPage = lazy(() => import('./pages/SignalsPage'))
const RegisterPage = lazy(() => import('./pages/RegisterPage'))
const EditorPage = lazy(() => import('./pages/EditorPage'))

function formatDate(iso: string | null) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString('en-GB', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'UTC',
      hourCycle: 'h23',
    }) + ' UTC'
  } catch {
    return iso
  }
}

function Header() {
  const { lastUpdated, editedCount } = useData()

  const navItems = [
    { to: '/', label: 'Heatmap', icon: '🗺️' },
    { to: '/database', label: 'Database', icon: '📋' },
    { to: '/signals', label: 'Signals', icon: '📣' },
    { to: '/register', label: 'Register', icon: '📚' },
    { to: '/editor', label: 'Edit Scores & Wording', icon: '✏️' },
  ]

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-wrap items-center justify-between gap-3 min-h-16 py-3">
          <div className="flex items-center gap-3">
            <span className="text-2xl" aria-hidden="true">🛡️</span>
            <div>
              <h1 className="text-lg font-bold text-slate-900 leading-tight">
                Global Trust and Safety Dashboard
              </h1>
              <p className="text-xs text-slate-500 leading-tight">
                Regulatory severity, China sentiment and key obligations across 158 markets
              </p>
            </div>
          </div>

          <nav className="flex flex-wrap items-center gap-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`
                }
              >
                <span className="mr-1.5" aria-hidden="true">{item.icon}</span>
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="flex flex-wrap items-center gap-4 pb-2 text-xs text-slate-400">
          {lastUpdated && <span>Register refreshed {formatDate(lastUpdated)}</span>}
          {editedCount > 0 && (
            <span className="text-amber-700">
              {editedCount} local {editedCount === 1 ? 'edit' : 'edits'} in this browser
            </span>
          )}
        </div>
      </div>
    </header>
  )
}

function Footer() {
  return (
    <footer className="bg-white border-t border-slate-200 mt-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-2 text-sm text-slate-500">
          <p>Global Trust and Safety Dashboard</p>
          <p>158 markets · regulatory severity, China sentiment and key obligations</p>
        </div>
      </div>
    </footer>
  )
}

function PageFallback() {
  return (
    <div className="flex items-center justify-center min-h-[50vh] text-slate-500">
      Loading page…
    </div>
  )
}

function AppContent() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6">
        <Suspense fallback={<PageFallback />}>
          <Routes>
            <Route path="/" element={<HeatmapPage />} />
            <Route path="/database" element={<DatabasePage />} />
            <Route path="/signals" element={<SignalsPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/editor" element={<EditorPage />} />
          </Routes>
        </Suspense>
      </main>
      <Footer />
    </div>
  )
}

export default function App() {
  return (
    <DataProvider>
      <FilterProvider>
        <HashRouter>
          <AppContent />
        </HashRouter>
      </FilterProvider>
    </DataProvider>
  )
}
