---
tags:
  - meta
  - índice
created: 2026-03-18
updated: 2026-03-18
---

# Bienvenido — Proyector Urbanístico de Getafe

> [!abstract] Qué es esto
> Documentación técnica del **Proyector Urbanístico de Getafe**, un dashboard de seguimiento urbanístico con datos históricos (2001-hoy), predicciones ML y sistema de alertas.

---

## Índice de documentos

| Documento | Descripción |
|---|---|
| [[v0.2 — Ingesta histórica y Tendencias]] | Roadmap activo — ingesta de datos históricos y página de Tendencias |
| [[bugs-scrapers-bocm-mivau]] | Bugs resueltos en scrapers BOCM y MIVAU (2026-03-18) |
| [[Fuentes de datos]] | Catálogo de fuentes externas — APIs, scrapers y periodicidad |

---

## Estado actual del proyecto

**Versión:** v0.2 en progreso
**Última actualización:** 2026-03-18

### Migraciones Alembic
- `0001` — Schema inicial (8 tablas, 4 enums, PostGIS)
- `c1b80c16bdda` — Nuevos modelos: `datos_ine`, `valores_mercado`; índices en `visados_estadisticos`

### Datos cargados en BD
- **12 barrios** de Getafe (hardcoded, fallback Catastro WFS)
- **312 registros** en `valores_suelo` (12 barrios × 26 años, fuente: IPV INE)
- **35 registros** en `visados_estadisticos` (1991–2025, fuente: MIVAU real)
- **0 alertas** (BOCM operativo, acumulación via Celery beat)

### Modelos ORM activos
- `catastral.py` → `Barrio`, `Parcela`, `ValorSuelo`, `ValorMercado`
- `construccion.py` → `ObraNueva`, `VisadoEstadistico`
- `alertas.py` → `Alerta`, `InversionPublica`, `ProyectoEMSV`
- `ine.py` → `DatoINE`

---

## Comandos útiles de referencia

```bash
# Ver estado de migraciones
docker compose exec backend alembic current

# Aplicar migraciones pendientes
docker compose exec backend alembic upgrade head

# Carga inicial de datos históricos
docker compose exec backend python -m app.tasks.initial_load

# Tests
docker compose exec backend pytest tests/ -v
```

---

## Links rápidos

- **Frontend:** http://localhost:5173
- **API + Swagger:** http://localhost:8001/docs
- **Flower (Celery):** http://localhost:5555
- **Código fuente:** `backend/app/` (FastAPI) | `frontend/src/` (React + Vite)
