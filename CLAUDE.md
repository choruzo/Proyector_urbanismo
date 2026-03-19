# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Reglas de trabajo

- **Cualquier modificación que requiera más de 3 pasos debe ejecutarse en modo plan** (`/plan` o `EnterPlanMode`) antes de implementar.
- **La documentación se escribe dentro de `Proyector_urbanismo_docs/`**, carpeta gestionada por Obsidian (usar Obsidian Flavored Markdown con frontmatter, wikilinks, callouts).

## Comandos de desarrollo

### Docker (stack completo)
```bash
cp .env.example .env           # Primera vez
docker compose up -d           # Levantar todos los servicios
docker compose logs -f backend # Seguir logs del backend
docker compose down            # Parar servicios
```

### Base de datos
```bash
docker compose exec backend alembic upgrade head          # Aplicar migraciones
docker compose exec backend alembic revision --autogenerate -m "descripcion"  # Nueva migración
docker compose exec backend python -m app.tasks.initial_load  # Carga inicial de datos históricos
```

### Backend (Python / FastAPI)
```bash
# Dentro del contenedor o con venv activado:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Celery worker y beat (se gestionan como servicios Docker)
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2
celery -A app.tasks.celery_app beat --loglevel=info
```

### Frontend (React / Vite)
```bash
cd frontend
npm install
npm run dev       # Dev server en :5173 con hot-reload
npm run build     # Compilar para producción (tsc + vite build)
npm run lint      # ESLint TypeScript
npm run preview   # Vista previa del build de producción
```

> **HMR en Docker sobre Windows**: Vite no detecta cambios de ficheros del host vía inotify. Tras editar ficheros del frontend, ejecutar:
> ```bash
> docker restart getafe_frontend
> ```

### URLs locales
| Servicio | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API + Swagger | http://localhost:8001/docs |
| Flower (Celery) | http://localhost:5555 |

## Arquitectura

### Stack
- **Backend**: Python 3.12 + FastAPI, PostgreSQL 16 + PostGIS, SQLAlchemy 2.x + GeoAlchemy2, Celery + Redis
- **Frontend**: React 18 + TypeScript + Vite 5, Tailwind CSS, Recharts + ECharts, React-Leaflet, TanStack Query, Zustand
- **ML**: Prophet (series temporales), scikit-learn (clustering), statsmodels
- **Infraestructura**: Docker Compose (7 servicios: postgres, redis, backend, celery_worker, celery_beat, flower, frontend)

### Flujo de datos
```
Fuentes externas (BOCM, Catastro, INE, EMSV, BOE, Min. Vivienda)
  → Scrapers (httpx, BeautifulSoup, feedparser, Playwright)
  → Celery tasks (scheduler beat + workers)
  → PostgreSQL + PostGIS
  → FastAPI /api/v1/...
  → React frontend (Axios + TanStack Query)
```

### Backend (`backend/app/`)
- `core/config.py` — Pydantic Settings; todas las variables de entorno centralizadas aquí
- `core/database.py` — SQLAlchemy engine, `get_db` dependency injection
- `models/` — ORM: `catastral.py` (Barrio, Parcela, ValorSuelo, ValorMercado con geometría PostGIS), `construccion.py` (ObraNueva, VisadoEstadistico), `alertas.py` (Alerta, InversionPublica, ProyectoEMSV), `ine.py` (DatoINE — indicadores estadísticos INE en bruto)
- `api/routes/` — Endpoints agrupados: `tendencias.py`, `mapa.py` (GeoJSON), `alertas.py`, `predicciones.py`
- `scrapers/` — Un módulo por fuente: `bocm.py`, `catastro.py`, `ine.py`, `vivienda.py`
- `tasks/celery_app.py` — Configuración Celery + beat_schedule (crontab por fuente)
- `analytics/predicciones.py` — Modelos Prophet y scikit-learn

### Frontend (`frontend/src/`)
- `App.tsx` — Router principal (React Router v6) + sidebar de 7 páginas
- `pages/` — Una página por sección: Overview, Tendencias, MapaValor, ObraNueva, Inversiones, Alertas, Predicciones
- `services/api.ts` — Cliente Axios; todas las llamadas a `/api/v1` centralizadas aquí
- `utils/format.ts` — Formateo de números, fechas, moneda

El proxy Vite redirige `/api` → `http://backend:8000` en desarrollo (nombre de servicio Docker interno).

### Tareas Celery programadas
| Tarea | Frecuencia |
|---|---|
| Escanear BOCM/BOE | Diaria (lun-vie, 10:00/10:30) |
| Actualizar Catastro | Semanal (dom 03:00) |
| Actualizar INE | Mensual (día 15) |
| Actualizar Min. Vivienda | Trimestral |
| Reentrenar modelos ML | Mensual (día 20) |

## Variables de entorno clave
Ver `.env.example`. Las más relevantes:
- `POSTGRES_*` — Conexión BD
- `REDIS_HOST/PORT` — Broker Celery
- `MUNICIPIO_CODIGO_INE=28065` — Getafe (no cambiar)
- `YEAR_START=2001` / `YEAR_END=2026` — Rango histórico
- `ALLOWED_ORIGINS` — CORS (añadir dominios de producción)

## Estado del proyecto
Actualmente en **v0.2 (casi completo — falta verificación final)**. v0.1 completado (scaffold). v0.2 avances:
- ✅ Alembic configurado, 2 migraciones aplicadas (`0001` schema inicial + `c1b80c16bdda` nuevos modelos)
- ✅ `initial_load` operativo: 12 barrios, 312 valores_suelo, 35 visados históricos (1991-2025)
- ✅ Scrapers BOCM y MIVAU corregidos y operativos
- ✅ Modelos adicionales: `DatoINE` (indicadores INE en bruto), `ValorMercado` (precios de mercado)
- ✅ Endpoints API con datos reales: `/kpis`, `/obra-nueva`, `/valor-suelo`, `/transacciones`
- ✅ Frontend Tendencias funcional: 3 gráficos reales + KPI Valor medio suelo en Overview
- ⏳ Verificación final y estabilización (tarea 6.x)

Roadmap: v0.3 mapa → v0.4 alertas → v0.5 ML → v1.0 despliegue.
