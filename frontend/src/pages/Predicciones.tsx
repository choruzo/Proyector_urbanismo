import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ResponsiveContainer, ComposedChart, Area, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ReferenceLine,
} from 'recharts'
import { getPrediccionObraNueva, getPrediccionValorSuelo } from '@/services/api'
import { formatNumber } from '@/utils/format'

const ANNO_ACTUAL = new Date().getFullYear()

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  const tipo = payload[0]?.payload?.tipo
  return (
    <div className="bg-surface-card border border-surface-border rounded-xl p-3 text-sm shadow-xl">
      <p className="font-semibold text-white mb-2">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: <span className="text-white">{formatNumber(p.value)}</span>
        </p>
      ))}
      {tipo === 'prediccion' && (
        <p className="text-xs text-slate-500 mt-1 italic">Estimación modelo ML</p>
      )}
    </div>
  )
}

export default function Predicciones() {
  const [horizonteObra,  setHorizonteObra]  = useState(10)
  const [horizonteValor, setHorizonteValor] = useState(10)

  const { data: dataObra = [], isLoading: loadingObra } = useQuery({
    queryKey: ['pred-obra', horizonteObra],
    queryFn: () => getPrediccionObraNueva(horizonteObra),
  })

  const { data: dataValor, isLoading: loadingValor } = useQuery({
    queryKey: ['pred-valor', horizonteValor],
    queryFn: () => getPrediccionValorSuelo({ horizonte: horizonteValor }),
  })

  const datosValorCombinados = dataValor?.datos ?? []

  return (
    <div className="p-8 space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-white">Predicciones a largo plazo</h2>
        <p className="text-slate-400 mt-1">
          Proyecciones generadas con Prophet y regresión polinómica. La línea discontinua indica el inicio de la estimación.
        </p>
      </div>

      {/* Nota metodológica */}
      <div className="bg-blue-950/40 border border-blue-800/40 rounded-xl p-4 text-sm text-blue-300">
        <strong className="text-blue-200">Nota:</strong> Los modelos se entrenan con datos históricos desde 2001.
        Las predicciones incluyen bandas de confianza al 80%. Los resultados son orientativos y no constituyen
        valoraciones oficiales. La precisión mejora con más datos históricos.
      </div>

      {/* Predicción obra nueva */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-base font-semibold text-white">Proyección de viviendas nuevas</h3>
          <select
            value={horizonteObra}
            onChange={(e) => setHorizonteObra(Number(e.target.value))}
            className="bg-surface-card border border-surface-border text-slate-200 text-sm rounded-lg px-3 py-2"
          >
            {[5, 7, 10, 15, 20].map((h) => <option key={h} value={h}>{h} años</option>)}
          </select>
        </div>
        {loadingObra ? (
          <div className="h-80 flex items-center justify-center text-slate-500">Entrenando modelo...</div>
        ) : dataObra.length === 0 ? (
          <div className="h-80 flex items-center justify-center text-slate-500">
            Sin datos históricos suficientes para generar predicción.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={dataObra} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
              <defs>
                <linearGradient id="gradPred" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#8b5cf6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="anno" tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
              <ReferenceLine x={ANNO_ACTUAL} stroke="#475569" strokeDasharray="6 3" label={{ value: 'Hoy', fill: '#64748b', fontSize: 11 }} />
              {/* Banda de confianza */}
              <Area dataKey="upper_80" fill="url(#gradPred)" stroke="transparent" name="IC sup. 80%" legendType="none" />
              <Area dataKey="lower_80" fill="#0f172a"         stroke="transparent" name="IC inf. 80%" legendType="none" />
              {/* Línea real */}
              <Line dataKey="num_viviendas" stroke="#3b82f6"  strokeWidth={2} dot={false} name="Real (historico)" />
              {/* Línea predicción */}
              <Line dataKey="prediccion"    stroke="#8b5cf6"  strokeWidth={2} strokeDasharray="6 3" dot={false} name="Predicción" />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Predicción valor del suelo */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-base font-semibold text-white">Proyección valor del suelo (€/m²)</h3>
          <select
            value={horizonteValor}
            onChange={(e) => setHorizonteValor(Number(e.target.value))}
            className="bg-surface-card border border-surface-border text-slate-200 text-sm rounded-lg px-3 py-2"
          >
            {[5, 7, 10, 15, 20].map((h) => <option key={h} value={h}>{h} años</option>)}
          </select>
        </div>
        {loadingValor ? (
          <div className="h-80 flex items-center justify-center text-slate-500">Calculando proyección...</div>
        ) : datosValorCombinados.length === 0 ? (
          <div className="h-80 flex items-center justify-center text-slate-500">
            Sin datos de valor del suelo para generar predicción.
          </div>
        ) : (
          <>
            <ResponsiveContainer width="100%" height={320}>
              <ComposedChart data={datosValorCombinados} margin={{ top: 5, right: 20, bottom: 5, left: 20 }}>
                <defs>
                  <linearGradient id="gradValorPred" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#f59e0b" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="anno" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} unit=" €/m²" width={90} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
                <ReferenceLine x={ANNO_ACTUAL} stroke="#475569" strokeDasharray="6 3"
                  label={{ value: 'Hoy', fill: '#64748b', fontSize: 11 }} />
                <Area dataKey="valor_predicho_euro_m2" fill="url(#gradValorPred)"
                  stroke="#f59e0b" strokeWidth={2} name="Valor €/m²" />
              </ComposedChart>
            </ResponsiveContainer>
            {dataValor?.metricas_modelo && (
              <div className="mt-4 flex gap-6 text-xs text-slate-500">
                <span>Modelo: Regresión polinómica (grado 2)</span>
                <span>R² = {dataValor.metricas_modelo.r2?.toFixed(3)}</span>
                <span>MAE = {dataValor.metricas_modelo.mae?.toFixed(1)} €/m²</span>
                <span>N muestras = {dataValor.metricas_modelo.n_samples}</span>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
