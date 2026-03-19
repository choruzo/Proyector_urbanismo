import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

// ── Tendencias ──────────────────────────────────────────────────────────────
export const getTendenciaObraNueva = (params?: { anno_inicio?: number; anno_fin?: number }) =>
  api.get('/tendencias/obra-nueva', { params }).then((r) => r.data)

export const getTendenciaValorSuelo = (params?: { anno_inicio?: number; anno_fin?: number; barrio_id?: number }) =>
  api.get('/tendencias/valor-suelo', { params }).then((r) => r.data)

export const getTendenciaTransacciones = (params?: { anno_inicio?: number; anno_fin?: number }) =>
  api.get('/tendencias/transacciones', { params }).then((r) => r.data)

export const getKPIs = () =>
  api.get('/tendencias/kpis').then((r) => r.data)

// ── Mapa ─────────────────────────────────────────────────────────────────────
export const getBarriosGeoJSON = (anno: number) =>
  api.get('/mapa/barrios/geojson', { params: { anno } }).then((r) => r.data)

export const getRevalorizacionBarrios = (params?: { anno_inicio?: number; anno_fin?: number }) =>
  api.get('/mapa/barrios/revalorizacion', { params }).then((r) => r.data)

// ── Alertas ──────────────────────────────────────────────────────────────────
export const getAlertas = (params?: { dias?: number; tipo?: string; fuente?: string; leida?: boolean }) =>
  api.get('/alertas/', { params }).then((r) => r.data)

export const getResumenAlertas = () =>
  api.get('/alertas/resumen').then((r) => r.data)

export const marcarAlertaLeida = (id: number) =>
  api.patch(`/alertas/${id}/marcar-leida`).then((r) => r.data)

// ── Predicciones ─────────────────────────────────────────────────────────────
export const getPrediccionObraNueva = (horizonte = 10) =>
  api.get('/predicciones/obra-nueva', { params: { horizonte } }).then((r) => r.data)

export const getPrediccionValorSuelo = (params?: { barrio_id?: number; horizonte?: number }) =>
  api.get('/predicciones/valor-suelo', { params }).then((r) => r.data)

export default api
