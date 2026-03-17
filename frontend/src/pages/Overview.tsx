import { useQuery } from '@tanstack/react-query'
import { Building2, TrendingUp, Euro, Bell, ArrowUpRight, ArrowDownRight } from 'lucide-react'
import { getKPIs, getResumenAlertas, getAlertas } from '@/services/api'
import { formatNumber, formatCurrency } from '@/utils/format'

function KPICard({
  label, value, subtitle, icon: Icon, trend, color = 'blue',
}: {
  label: string; value: string; subtitle?: string;
  icon: React.ElementType; trend?: number; color?: string;
}) {
  const colorMap: Record<string, string> = {
    blue:    'bg-blue-500/10 text-blue-400',
    emerald: 'bg-emerald-500/10 text-emerald-400',
    violet:  'bg-violet-500/10 text-violet-400',
    amber:   'bg-amber-500/10 text-amber-400',
  }
  return (
    <div className="card flex flex-col gap-4">
      <div className="flex items-start justify-between">
        <div className={`p-2.5 rounded-lg ${colorMap[color]}`}>
          <Icon size={20} strokeWidth={1.8} />
        </div>
        {trend !== undefined && (
          <span className={`flex items-center gap-1 text-sm font-medium ${trend >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {trend >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
            {Math.abs(trend).toFixed(1)}%
          </span>
        )}
      </div>
      <div>
        <p className="kpi-value">{value}</p>
        <p className="kpi-label mt-1">{label}</p>
        {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
      </div>
    </div>
  )
}

export default function Overview() {
  const { data: kpis, isLoading: kpisLoading } = useQuery({
    queryKey: ['kpis'],
    queryFn: getKPIs,
  })
  const { data: alertas = [] } = useQuery({
    queryKey: ['alertas', { dias: 7 }],
    queryFn: () => getAlertas({ dias: 7 }),
  })

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-white">Resumen General</h2>
        <p className="text-slate-400 mt-1">Indicadores urbanísticos de Getafe · Actualizado hoy</p>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5 mb-8">
        <KPICard
          label="Viviendas nuevas (último año)"
          value={kpisLoading ? '...' : formatNumber(kpis?.viviendas_ultimo_anno ?? 0)}
          icon={Building2}
          color="blue"
        />
        <KPICard
          label="Visados de obra"
          value={kpisLoading ? '...' : formatNumber(kpis?.visados_ultimo_anno ?? 0)}
          icon={TrendingUp}
          color="emerald"
        />
        <KPICard
          label="Alertas últimos 7 días"
          value={String(alertas.length)}
          subtitle={`${alertas.filter((a: any) => !a.leida).length} sin leer`}
          icon={Bell}
          color="amber"
        />
        <KPICard
          label="Año de referencia"
          value={String(kpis?.anno ?? 2026)}
          icon={Euro}
          color="violet"
        />
      </div>

      {/* Alertas recientes */}
      <div className="card">
        <h3 className="text-base font-semibold text-white mb-4">Alertas recientes (7 días)</h3>
        {alertas.length === 0 ? (
          <p className="text-slate-500 text-sm">Sin publicaciones recientes en BOCM/BOE.</p>
        ) : (
          <div className="space-y-3">
            {alertas.slice(0, 5).map((a: any) => (
              <div key={a.id} className="flex items-start gap-3 py-3 border-b border-surface-border last:border-0">
                <span className={`badge badge-${a.tipo} flex-shrink-0 mt-0.5`}>{a.tipo}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-200 line-clamp-2">{a.titulo}</p>
                  <p className="text-xs text-slate-500 mt-1">
                    {a.fuente.toUpperCase()} · {a.fecha_publicacion}
                    {a.importe_euros && ` · ${formatCurrency(a.importe_euros)}`}
                  </p>
                </div>
                {a.url && (
                  <a href={a.url} target="_blank" rel="noopener noreferrer"
                    className="text-brand-500 hover:text-blue-300 flex-shrink-0 mt-0.5">
                    <ArrowUpRight size={16} />
                  </a>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
