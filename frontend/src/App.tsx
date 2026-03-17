import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  LayoutDashboard, TrendingUp, Map, Building2, Euro, Bell, BrainCircuit,
} from 'lucide-react'
import Overview from '@/pages/Overview'
import Tendencias from '@/pages/Tendencias'
import MapaValor from '@/pages/MapaValor'
import ObraNueva from '@/pages/ObraNueva'
import Inversiones from '@/pages/Inversiones'
import Alertas from '@/pages/Alertas'
import Predicciones from '@/pages/Predicciones'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 5 * 60 * 1000, retry: 2 } },
})

const NAV_ITEMS = [
  { to: '/',            icon: LayoutDashboard, label: 'Resumen'   },
  { to: '/tendencias',  icon: TrendingUp,      label: 'Tendencias' },
  { to: '/mapa',        icon: Map,             label: 'Mapa Suelo' },
  { to: '/obra-nueva',  icon: Building2,       label: 'Obra Nueva' },
  { to: '/inversiones', icon: Euro,            label: 'Inversión'  },
  { to: '/alertas',     icon: Bell,            label: 'Alertas'    },
  { to: '/predicciones',icon: BrainCircuit,    label: 'Predicciones' },
]

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="flex min-h-screen">
          {/* Sidebar */}
          <aside className="w-60 flex-shrink-0 bg-surface-card border-r border-surface-border flex flex-col">
            {/* Logo */}
            <div className="px-6 py-5 border-b border-surface-border">
              <p className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-1">Dashboard Urbanístico</p>
              <h1 className="text-lg font-bold text-white leading-tight">Getafe</h1>
            </div>

            {/* Nav items */}
            <nav className="flex-1 py-4 px-3 space-y-1">
              {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
                     ${isActive
                       ? 'bg-brand-600 text-white'
                       : 'text-slate-400 hover:text-slate-200 hover:bg-surface-border/50'}`
                  }
                >
                  <Icon size={17} strokeWidth={1.8} />
                  {label}
                </NavLink>
              ))}
            </nav>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-surface-border">
              <p className="text-xs text-slate-600">Datos desde 2001 · Actualización automática</p>
            </div>
          </aside>

          {/* Contenido principal */}
          <main className="flex-1 overflow-y-auto bg-surface">
            <Routes>
              <Route path="/"             element={<Overview />}     />
              <Route path="/tendencias"   element={<Tendencias />}   />
              <Route path="/mapa"         element={<MapaValor />}    />
              <Route path="/obra-nueva"   element={<ObraNueva />}    />
              <Route path="/inversiones"  element={<Inversiones />}  />
              <Route path="/alertas"      element={<Alertas />}      />
              <Route path="/predicciones" element={<Predicciones />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
