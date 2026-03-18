---
tags:
  - bug
  - scrapers
  - blocker
status: abierto
created: 2026-03-18
updated: 2026-03-18
afecta:
  - "[[v0.2 — Ingesta histórica y Tendencias]]"
---

# Bugs — Scrapers BOCM y MIVAU

> [!bug] Dos scrapers externos no operativos desde Docker
> Detectados durante la ejecución de `initial_load.py` el 2026-03-18.
> Las fuentes afectadas son **BOCM** (tabla `alertas`) y **MIVAU** (tabla `visados_estadisticos`).
> Las demás fuentes (INE, Catastro) funcionan correctamente o tienen fallback robusto.

---

## Bug 1 — BOCM: HTTP 404 en todas las fechas

### Síntoma

```
ERROR | app.scrapers.bocm:buscar_publicaciones_getafe:94 -
Error al acceder BOCM para fecha 18/03/2026:
Client error '404 Not Found' for url
'https://www.bocm.es/buscador?busqueda=Getafe%20urbanismo&fecha=18%2F03%2F2026&tipo=1'
```

404 en **cada una de las 365 peticiones** del rango histórico. Resultado: `alertas` = 0 registros.

### Causa probable

La URL del buscador del BOCM ha cambiado de estructura. La URL hardcoded en `bocm.py`:

```python
# backend/app/scrapers/bocm.py — línea ~50
url = "https://www.bocm.es/buscador"
params = {
    "busqueda": "Getafe urbanismo",
    "fecha": fecha.strftime("%d/%m/%Y"),
    "tipo": "1",
}
```

El portal `www.bocm.es` ha migrado su buscador a una nueva estructura (posiblemente SPA con API REST interna o cambio de parámetros).

### Impacto

| Tabla | Estado |
|-------|--------|
| `alertas` | 0 registros — sin datos históricos del BOCM |
| Tarea `task_escanear_bocm` (Celery) | También afectada — las alertas diarias tampoco se insertan |

### Pasos para investigar y resolver

- [ ] Abrir manualmente `https://www.bocm.es/buscador` en el navegador e inspeccionar la petición de red real (DevTools → Network)
- [ ] Identificar la nueva URL, parámetros y formato de respuesta
- [ ] Actualizar `bocm.py` → clase `BOCMScraper` → método `buscar_publicaciones_getafe()`
- [ ] Re-ejecutar: `docker exec getafe_backend python -m app.tasks.initial_load --fuente bocm --force`

### Archivos afectados

- `backend/app/scrapers/bocm.py` — método `buscar_publicaciones_getafe()` (~línea 50-95)
- `backend/app/tasks/initial_load.py` — función `_cargar_alertas_bocm()` (sin cambios necesarios)
- `backend/app/tasks/scheduled_tasks.py` — función `task_escanear_bocm()` (también afectada)

---

## Bug 2 — MIVAU: HTTP 403 Forbidden en descarga de Excel

### Síntoma

```
ERROR | app.scrapers.vivienda:_descargar_fichero:68 -
Error al descargar
https://www.mivau.gob.es/recursos_mivau/publicaciones/estadisticas/vivienda/
construccion/visados_libre.xls:
Client error '403 Forbidden'
```

El servidor del Ministerio rechaza la petición. Resultado: fallback activado → 23 registros de referencia insertados.

### Causa probable

El Ministerio de Vivienda (MIVAU) ha añadido protección anti-bot o ha movido los ficheros estadísticos a una nueva ruta. Las URLs hardcoded en `vivienda.py`:

```python
# backend/app/scrapers/vivienda.py — líneas 25-42
URLS_ESTADISTICAS = {
    "visados_nueva_planta": (
        "https://www.mivau.gob.es/recursos_mivau/publicaciones/estadisticas/vivienda/"
        "construccion/visados_libre.xls"
    ),
    ...
}
```

Posibles causas:
1. **User-Agent bloqueado** — el servidor filtra bots aunque el header esté configurado
2. **Referer requerido** — el servidor exige que la petición venga de `www.mivau.gob.es`
3. **URL caducada** — los ficheros se han movido a otra ruta o ahora requieren sesión
4. **Protección Cloudflare / WAF** — el servidor bloquea IPs de contenedores Docker

### Impacto

| Tabla | Estado |
|-------|--------|
| `visados_estadisticos` | 23 registros de **referencia** (no oficiales) — suficiente para Tendencias |
| Tarea `task_actualizar_vivienda` (Celery) | También afectada |

> [!tip] El fallback cubre el caso de uso
> Los 23 años de datos de referencia (2001–2023) son suficientes para visualizar la curva histórica de obra nueva en la página de Tendencias. Este bug es **no bloqueante para v0.2**.

### Pasos para investigar y resolver

- [ ] Verificar manualmente si la URL existe: `curl -I "https://www.mivau.gob.es/recursos_mivau/..."` con headers de navegador
- [ ] Buscar la URL actualizada en `https://www.mivau.gob.es/vivienda/estadisticas`
- [ ] Probar añadir header `Referer: https://www.mivau.gob.es` en `ViviendaScraper.__init__()`
- [ ] Si la URL ha cambiado, actualizar `URLS_ESTADISTICAS` en `vivienda.py`
- [ ] Como alternativa robusta: descargar los ficheros manualmente y servirlos desde `backend/data/` (solución offline)

### Archivos afectados

- `backend/app/scrapers/vivienda.py` — `URLS_ESTADISTICAS` (~línea 25) y `_descargar_fichero()`
- `backend/app/tasks/initial_load.py` — función `_cargar_visados()` (sin cambios necesarios, el fallback funciona)
- `backend/app/tasks/scheduled_tasks.py` — función `task_actualizar_vivienda()`

---

## Resumen de estado

| Scraper | Error | Bloqueante | Fallback activo |
|---------|-------|-----------|-----------------|
| `BOCMScraper` | 404 — URL buscador cambiada | ⚠️ Para alertas en tiempo real | ✅ `initial_load` omite sin abortar |
| `ViviendaScraper` | 403 — Acceso denegado al Excel | No para v0.2 | ✅ 23 años de referencia cargados |
| `INEScraper` | Ninguno — **operativo** ✅ | — | — |
| `CatastroScraper` (WFS) | DNS — sin internet en Docker | No (barrios hardcoded) | ✅ 12 barrios cargados |

---

## Referencias

- [[v0.2 — Ingesta histórica y Tendencias]] — Punto 2
- Scrapers: `backend/app/scrapers/bocm.py`, `backend/app/scrapers/vivienda.py`
- Tarea de carga: `backend/app/tasks/initial_load.py`
- Tareas periódicas: `backend/app/tasks/scheduled_tasks.py`
