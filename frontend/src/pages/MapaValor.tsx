import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { MapContainer, TileLayer, GeoJSON, Tooltip as LeafletTooltip } from 'react-leaflet'
import { getBarriosGeoJSON, getRevalorizacionBarrios } from '@/services/api'
import { formatNumber } from '@/utils/format'
import 'leaflet/dist/leaflet.css'

// Centro aproximado de Getafe
const GETAFE_CENTER: [number, number] = [40.3056, -3.7325]
const GETAFE_ZOOM = 13

function getColor(value: number | null, max: number): string {
  if (value === null) return '#334155'
  const ratio = Math.min(value / max, 1)
  // Gradiente azul frío → rojo cálido para valor del suelo
  const r = Math.round(59  + ratio * (239 - 59))
  const g = Math.round(130 + ratio * (68  - 130))
  const b = Math.round(246 + ratio * (68  - 246))
  return `rgb(${r},${g},${b})`
}

export default function MapaValor() {
  const [anno, setAnno] = useState(2024)
  const [annoInicio, setAnnoInicio] = useState(2015)

  const { data: geojson, isLoading: loadingGeo } = useQuery({
    queryKey: ['barrios-geojson', anno],
    queryFn: () => getBarriosGeoJSON(anno),
  })

  const { data: revalorizacion = [], isLoading: loadingRev } = useQuery({
    queryKey: ['revalorizacion', annoInicio, anno],
    queryFn: () => getRevalorizacionBarrios({ anno_inicio: annoInicio, anno_fin: anno }),
  })

  const maxValor = geojson?.features
    ? Math.max(...geojson.features.map((f: any) => f.properties.valor_euro_m2 ?? 0), 1)
    : 1

  const styleFeature = (feature: any) => ({
    fillColor: getColor(feature.properties.valor_euro_m2, maxValor),
    fillOpacity: 0.75,
    color: '#475569',
    weight: 1.5,
  })

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Mapa de Valor del Suelo</h2>
          <p className="text-slate-400 mt-1">Valor catastral medio (€/m²) y revalorización por barrio</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-500">Año visualizado</label>
            <select
              value={anno}
              onChange={(e) => setAnno(Number(e.target.value))}
              className="bg-surface-card border border-surface-border text-slate-200 text-sm rounded-lg px-3 py-2"
            >
              {Array.from({ length: 26 }, (_, i) => 2001 + i).map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-500">Revalorizac. desde</label>
            <select
              value={annoInicio}
              onChange={(e) => setAnnoInicio(Number(e.target.value))}
              className="bg-surface-card border border-surface-border text-slate-200 text-sm rounded-lg px-3 py-2"
            >
              {Array.from({ length: 25 }, (_, i) => 2001 + i).map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Mapa */}
      <div className="card !p-0 overflow-hidden" style={{ height: 480 }}>
        {loadingGeo ? (
          <div className="h-full flex items-center justify-center text-slate-500">Cargando mapa...</div>
        ) : (
          <MapContainer center={GETAFE_CENTER} zoom={GETAFE_ZOOM} style={{ width: '100%', height: '100%' }}>
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            />
            {geojson && geojson.features.length > 0 && (
              <GeoJSON
                key={anno}
                data={geojson}
                style={styleFeature}
                onEachFeature={(feature, layer) => {
                  const p = feature.properties
                  layer.bindTooltip(
                    `<div style="font-family:Inter,sans-serif;font-size:13px;color:#e2e8f0;background:#1e293b;border:1px solid #334155;border-radius:8px;padding:8px 12px">
                      <strong>${p.nombre}</strong><br/>
                      ${p.valor_euro_m2 ? `${formatNumber(p.valor_euro_m2)} €/m²` : 'Sin datos'}
                    </div>`,
                    { sticky: true, className: 'leaflet-tooltip-custom' }
                  )
                }}
              />
            )}
            {geojson?.features.length === 0 && (
              // Placeholder: sin geometrías cargadas aún
              <></>
            )}
          </MapContainer>
        )}
      </div>

      {/* Tabla de revalorización */}
      <div className="card">
        <h3 className="text-base font-semibold text-white mb-4">
          Revalorización por barrio ({annoInicio} → {anno})
        </h3>
        {loadingRev ? (
          <p className="text-slate-500 text-sm">Cargando datos...</p>
        ) : revalorizacion.length === 0 ? (
          <p className="text-slate-500 text-sm">Sin datos de revalorización (ingesta pendiente).</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 border-b border-surface-border">
                  <th className="pb-3 font-medium">Barrio</th>
                  <th className="pb-3 font-medium text-right">Valor {annoInicio}</th>
                  <th className="pb-3 font-medium text-right">Valor {anno}</th>
                  <th className="pb-3 font-medium text-right">Revalorización</th>
                </tr>
              </thead>
              <tbody>
                {revalorizacion.map((b: any) => (
                  <tr key={b.barrio_id} className="border-b border-surface-border/50 hover:bg-surface-border/20">
                    <td className="py-3 text-slate-200">{b.nombre}</td>
                    <td className="py-3 text-right text-slate-400">
                      {b.valor_inicio ? `${formatNumber(b.valor_inicio)} €/m²` : '—'}
                    </td>
                    <td className="py-3 text-right text-slate-300">
                      {b.valor_fin ? `${formatNumber(b.valor_fin)} €/m²` : '—'}
                    </td>
                    <td className={`py-3 text-right font-semibold ${
                      b.revalorizacion_pct > 0 ? 'text-emerald-400' : b.revalorizacion_pct < 0 ? 'text-red-400' : 'text-slate-500'
                    }`}>
                      {b.revalorizacion_pct != null ? `${b.revalorizacion_pct > 0 ? '+' : ''}${b.revalorizacion_pct.toFixed(1)}%` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
