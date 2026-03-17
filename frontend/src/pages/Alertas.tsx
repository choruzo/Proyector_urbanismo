import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Bell, CheckCheck, ExternalLink, Filter } from 'lucide-react'
import { getAlertas, marcarAlertaLeida } from '@/services/api'
import { formatCurrency } from '@/utils/format'

const TIPOS = ['todos', 'licitacion', 'adjudicacion', 'convenio', 'planeamiento', 'emsv', 'otro']
const FUENTES = ['todos', 'bocm', 'boe', 'ayuntamiento', 'emsv']

export default function Alertas() {
  const [tipo,   setTipo]   = useState('todos')
  const [fuente, setFuente] = useState('todos')
  const [dias,   setDias]   = useState(30)
  const [soloNoLeidas, setSoloNoLeidas] = useState(false)

  const qc = useQueryClient()

  const { data: alertas = [], isLoading } = useQuery({
    queryKey: ['alertas', { dias, tipo, fuente, soloNoLeidas }],
    queryFn: () => getAlertas({
      dias,
      tipo:   tipo   !== 'todos' ? tipo   : undefined,
      fuente: fuente !== 'todos' ? fuente : undefined,
      leida:  soloNoLeidas ? false : undefined,
    }),
  })

  const { mutate: marcarLeida } = useMutation({
    mutationFn: (id: number) => marcarAlertaLeida(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alertas'] }),
  })

  return (
    <div className="p-8 space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white">Alertas Urbanísticas</h2>
        <p className="text-slate-400 mt-1">Publicaciones del BOCM y BOE relacionadas con Getafe</p>
      </div>

      {/* Filtros */}
      <div className="card !py-4 flex flex-wrap gap-4 items-center">
        <Filter size={16} className="text-slate-500" />
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-500">Período</label>
          <select value={dias} onChange={(e) => setDias(Number(e.target.value))}
            className="bg-surface border border-surface-border text-slate-200 text-sm rounded-lg px-3 py-1.5">
            {[7, 14, 30, 60, 90, 180, 365].map((d) => <option key={d} value={d}>{d} días</option>)}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-500">Tipo</label>
          <select value={tipo} onChange={(e) => setTipo(e.target.value)}
            className="bg-surface border border-surface-border text-slate-200 text-sm rounded-lg px-3 py-1.5">
            {TIPOS.map((t) => <option key={t} value={t}>{t === 'todos' ? 'Todos los tipos' : t}</option>)}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-500">Fuente</label>
          <select value={fuente} onChange={(e) => setFuente(e.target.value)}
            className="bg-surface border border-surface-border text-slate-200 text-sm rounded-lg px-3 py-1.5">
            {FUENTES.map((f) => <option key={f} value={f}>{f === 'todos' ? 'Todas las fuentes' : f.toUpperCase()}</option>)}
          </select>
        </div>
        <label className="flex items-center gap-2 cursor-pointer ml-2 mt-4">
          <input type="checkbox" checked={soloNoLeidas} onChange={(e) => setSoloNoLeidas(e.target.checked)}
            className="rounded" />
          <span className="text-sm text-slate-400">Solo no leídas</span>
        </label>
        <span className="ml-auto text-sm text-slate-500">{alertas.length} resultados</span>
      </div>

      {/* Lista de alertas */}
      {isLoading ? (
        <div className="card text-center text-slate-500 py-12">Cargando alertas...</div>
      ) : alertas.length === 0 ? (
        <div className="card text-center py-16">
          <Bell size={40} className="mx-auto text-slate-700 mb-4" />
          <p className="text-slate-500">No hay alertas con los filtros seleccionados.</p>
          <p className="text-xs text-slate-600 mt-2">
            Las alertas se generan automáticamente en el siguiente escaneo del BOCM/BOE.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {alertas.map((a: any) => (
            <div key={a.id}
              className={`card !py-4 transition-opacity ${a.leida ? 'opacity-60' : ''}`}>
              <div className="flex items-start gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-2">
                    <span className={`badge badge-${a.tipo}`}>{a.tipo}</span>
                    <span className="badge badge-otro">{a.fuente.toUpperCase()}</span>
                    {a.importe_euros && (
                      <span className="text-xs text-emerald-400 font-semibold">
                        {formatCurrency(a.importe_euros)}
                      </span>
                    )}
                    {!a.leida && (
                      <span className="w-2 h-2 bg-brand-500 rounded-full flex-shrink-0" title="No leída" />
                    )}
                  </div>
                  <p className="text-sm text-slate-200 font-medium">{a.titulo}</p>
                  {a.descripcion && (
                    <p className="text-xs text-slate-500 mt-1 line-clamp-2">{a.descripcion}</p>
                  )}
                  <p className="text-xs text-slate-600 mt-2">{a.fecha_publicacion}</p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {!a.leida && (
                    <button
                      onClick={() => marcarLeida(a.id)}
                      className="p-1.5 rounded-lg text-slate-500 hover:text-emerald-400 hover:bg-surface-border/50 transition-colors"
                      title="Marcar como leída"
                    >
                      <CheckCheck size={16} />
                    </button>
                  )}
                  {a.url && (
                    <a href={a.url} target="_blank" rel="noopener noreferrer"
                      className="p-1.5 rounded-lg text-slate-500 hover:text-brand-400 hover:bg-surface-border/50 transition-colors">
                      <ExternalLink size={16} />
                    </a>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
