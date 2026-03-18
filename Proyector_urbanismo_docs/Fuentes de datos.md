---
tags:
  - referencia
  - fuentes
created: 2026-03-18
---

# Fuentes de datos

> [!abstract] Catálogo de fuentes externas
> Todas las fuentes de datos utilizadas por el Proyector Urbanístico de Getafe, con tipo de acceso, estado operativo y periodicidad de actualización.

Ver [[Bienvenido]] para el estado actual de la BD y [[bugs-scrapers-bocm-mivau]] para incidencias registradas.

---

## Fuentes con API oficial

| Fuente | Módulo | Datos | Estado | Periodicidad |
|---|---|---|---|---|
| **Catastro (DGC)** | `scrapers/catastro.py` | Valor catastral, parcelas, geometrías WFS | ⚠️ DNS sin internet en Docker | Semanal (dom 03:00) |
| **INE** | `scrapers/ine.py` | IPV, transacciones, población | ✅ Operativo | Mensual (día 15) |
| **Ministerio de Vivienda (MIVAU)** | `scrapers/vivienda.py` | Visados, precios vivienda | ✅ Operativo — URL corregida a `fomento.gob.es` | Trimestral |

## Fuentes con scraping periódico

| Fuente | Módulo | Datos | Estado | Periodicidad |
|---|---|---|---|---|
| **BOCM** | `scrapers/bocm.py` | Licitaciones, expedientes, convenios urbanísticos | ✅ Operativo — URL corregida a `/advanced-search` | Diaria (lun-vie 10:00) |
| **BOE** | `tasks/scheduled_tasks.py` | Licitaciones estatales en Getafe | ✅ Operativo | Diaria (lun-vie 10:30) |

## Fuentes de mercado (a evaluar)

| Fuente | Datos | Estado |
|---|---|---|
| Idealista / Fotocasa | Precios de mercado €/m² | ⏳ Pendiente — modelo `ValorMercado` ya creado |
| Datos Abiertos CM | Planeamiento, licencias | ⏳ Pendiente |
| EMSV Getafe | Proyectos vivienda pública | ⏳ Pendiente |

---

## Estructura de almacenamiento

```
Fuentes externas
  → scrapers/       (httpx, BeautifulSoup, feedparser, Playwright)
  → tasks/          (Celery beat + workers)
  → PostgreSQL + PostGIS
  → FastAPI /api/v1/...
  → React frontend
```

### Tablas por fuente

| Fuente | Tablas |
|---|---|
| INE | `datos_ine`, `valores_suelo` |
| MIVAU | `visados_estadisticos` |
| Catastro | `barrios`, `parcelas`, `valores_suelo` |
| BOCM / BOE | `alertas` |
| EMSV | `proyectos_emsv` |
| Mercado | `valores_mercado` |

---

## Notas técnicas

> [!warning] Catastro WFS
> El endpoint WFS de la DGC no es accesible desde dentro del contenedor Docker sin salida a internet. Se usa fallback de 12 barrios hardcoded mientras el entorno sea local cerrado.

> [!note] INE — Serie ETN 46964
> La URL directa de transacciones inmobiliarias devuelve redirect 301 con `httpx` (sin seguir). Se usa fallback hardcoded 2004–2025 como datos de referencia. Ver [[bugs-scrapers-bocm-mivau]].

> [!tip] Reentrenamiento de modelos ML
> Celery beat lanza `reentrenar-modelos-mensual` el día 20 de cada mes. Requiere mínimo de datos en BD para que Prophet genere predicciones válidas.

---

## Ver también

- [[Bienvenido]] — Estado actual del proyecto
- [[bugs-scrapers-bocm-mivau]] — Incidencias y correcciones en scrapers
- [[v0.2 — Ingesta histórica y Tendencias]] — Tareas de ingesta en curso
