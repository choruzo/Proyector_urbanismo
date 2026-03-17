import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ResponsiveContainer, ComposedChart, Line, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, Area,
} from 'recharts'
import { getTendenciaObraNueva, getTendenciaValorSuelo } from '@/services/api'
import { formatNumber } from '@/utils/format'

const CHART_COLORS = {
  viviendas:   '#3b82f6',
  visados:     '#8b5cf6',
  presupuesto: '#10b981',
  valor:       '#f59e0b',
}

export default function Tendencias() {
  const [annoInicio, setAnnoInicio] = useState(2001)
  const [annoFin, setAnnoFin]       = useState(2026)

  const { data: obraNueva = [], isLoading: loadingObra } = useQuery({
    queryKey: ['tendencias-obra', annoInicio, annoFin],
    queryFn: () => getTendenciaObraNueva({ anno_inicio: annoInicio, anno_fin: annoFin }),
  })

  const { data: valorSuelo = [], isLoading: loadingValor } = useQuery({
    queryKey: ['tendencias-valor', annoInicio, annoFin],
    queryFn: () => getTendenciaValorSuelo({ anno_inicio: annoInicio, anno_fin: annoFin }),
  })

  return (
    <div className="p-8 space-y-8">
      {/* Header + filtros */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Tendencias Urbanísticas</h2>
          <p className="text-slate-400 mt-1">Serie histórica de obra nueva y valor del suelo en Getafe</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-500">Desde</label>
            <select
              value={annoInicio}
              onChange={(e) => setAnnoInicio(Number(e.target.value))}
              className="bg-surface-card border border-surface-border text-slate-200 text-sm rounded-lg px-3 py-2"
            >
              {Array.from({ length: 26 }, (_, i) => 2001 + i).map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-500">Hasta</label>
            <select
              value={annoFin}
              onChange={(e) => setAnnoFin(Number(e.target.value))}
              className="bg-surface-card border border-surface-border text-slate-200 text-sm rounded-lg px-3 py-2"
            >
              {Array.from({ length: 26 }, (_, i) => 2001 + i).map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Gráfica obra nueva */}
      <div className="card">
        <h3 className="text-base font-semibold text-white mb-6">Viviendas nuevas y visados por año</h3>
        {loadingObra ? (
          <div className="h-72 flex items-center justify-center text-slate-500">Cargando datos...</div>
        ) : obraNueva.length === 0 ? (
          <div className="h-72 flex items-center justify-center text-slate-500">
            Sin datos en el rango seleccionado. La ingesta inicial aún no se ha ejecutado.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={obraNueva} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="anno" tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <YAxis yAxisId="left"  tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                labelStyle={{ color: '#e2e8f0', fontWeight: 600 }}
                itemStyle={{ color: '#94a3b8' }}
              />
              <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
              <Bar    yAxisId="left"  dataKey="num_viviendas" fill={CHART_COLORS.viviendas} name="Viviendas" radius={[3, 3, 0, 0]} />
              <Line   yAxisId="right" dataKey="num_visados"   stroke={CHART_COLORS.visados}  name="Visados" strokeWidth={2} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Gráfica valor del suelo */}
      <div className="card">
        <h3 className="text-base font-semibold text-white mb-6">Evolución valor del suelo (€/m²)</h3>
        {loadingValor ? (
          <div className="h-72 flex items-center justify-center text-slate-500">Cargando datos...</div>
        ) : valorSuelo.length === 0 ? (
          <div className="h-72 flex items-center justify-center text-slate-500">
            Sin datos de valor del suelo aún.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={valorSuelo} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
              <defs>
                <linearGradient id="gradValor" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={CHART_COLORS.valor} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={CHART_COLORS.valor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="anno"               tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} unit=" €/m²" width={90} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                labelStyle={{ color: '#e2e8f0', fontWeight: 600 }}
                formatter={(v: number) => [`${formatNumber(v)} €/m²`, 'Valor medio']}
              />
              <Area
                dataKey="valor_medio_euro_m2"
                stroke={CHART_COLORS.valor}
                strokeWidth={2}
                fill="url(#gradValor)"
                name="Valor medio €/m²"
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
