---
tags:
  - bug
  - scrapers
  - resuelto
status: resuelto
created: 2026-03-18
updated: 2026-03-19
afecta:
  - "[[v0.2 — Ingesta histórica y Tendencias]]"
---

# Bugs — Scrapers BOCM, MIVAU e INE

> [!success] Todos los bugs resueltos — 2026-03-19
> Los cuatro bugs documentados han sido corregidos y verificados con tests.
> `test_scrapers.py` — 7 tests (4 estáticos + 3 integración con red real).

---

## Bug 1 — BOCM: HTTP 404 en todas las fechas

### Síntoma original

```
Client error '404 Not Found' for url
'https://www.bocm.es/buscador?busqueda=Getafe%20urbanismo&fecha=18%2F03%2F2026&tipo=1'
```

404 en **cada una de las 365 peticiones** del rango histórico. Resultado: `alertas` = 0 registros.

### Causa

El portal BOCM (Drupal) renombró el path `/buscador` → `/advanced-search` en 2024.
Los parámetros del Views exposed filter también cambiaron:

| Parámetro | Antes (roto) | Ahora (correcto) |
|-----------|-------------|-----------------|
| URL | `/buscador` | `/advanced-search` |
| Texto | `busqueda=...` | `keys=...` |
| Fecha | `fecha=DD/MM/YYYY` | `field_bulletin_field_date[value]=DD-MM-YYYY` |
| Tipo | `tipo=1` | _(eliminado)_ |

### Solución aplicada

```python
# backend/app/scrapers/bocm.py
BOCM_SEARCH_URL = "https://www.bocm.es/advanced-search"  # era /buscador

params = {
    "keys": "Getafe urbanismo",
    "field_bulletin_field_date[value]": fecha.strftime("%d-%m-%Y"),  # DD-MM-YYYY
}
# Añadido header Referer; selectores CSS actualizados a Drupal Views:
# items = soup.select(".view-content .views-row") o fallback .views-row
```

### Verificación

- [x] Test de integración `test_bocm_search_url_responde_200` → HTTP 200 ✅
- [x] `initial_load --fuente bocm --force` → escaneando 365 días sin errores HTTP ✅
- [x] `initial_load` no aborta aunque no haya resultados (fechas sin publicaciones BOCM) ✅

> [!note] 0 resultados es normal
> El filtro de keywords (`"Getafe urbanismo"` + selectores de título) es estricto.
> Las alertas se acumulan en producción con el uso diario del Celery beat.

---

## Bug 2 — MIVAU: HTTP 403 + estructura Excel no estándar

### Síntoma original

```
Client error '403 Forbidden'
https://www.mivau.gob.es/recursos_mivau/.../visados_libre.xls
```

Fallback activado → sólo 23 registros de referencia en `visados_estadisticos`.

### Causa

Dos problemas encadenados:

1. **URLs muertas**: Los ficheros del MIVAU se movieron a `apps.fomento.gob.es/Boletinonline/sedal/`
2. **Dependencia faltante**: Los nuevos ficheros son `.XLS` (formato binario OLE2), que requiere `xlrd>=2.0.1` (no estaba en `requirements.txt`)
3. **Parser incorrecto**: La estructura del fichero SEDAL es diferente a lo esperado — los años están en la **columna 0** de cada fila mensual, no en cabeceras de columna

### Estructura real del fichero SEDAL (`09032810.XLS`)

```
Filas 0-7:   Metadatos (título, provincia: Madrid)
Filas 8-12:  Resumen últimos 5 años  → col0=año, col4=total anual
Filas 14+:   Desglose mensual        → col0=año (sólo 1ª fila del año),
                                        col2=mes (Ene/Feb/.../Dic),
                                        col4=viviendas ese mes
```

El histórico completo desde 1991 está en el **desglose mensual** → se agrega sumando meses por año.

### Solución aplicada

```python
# 1. requirements.txt — nueva dependencia
xlrd>=2.0.1
openpyxl>=3.1.0

# 2. vivienda.py — URLs actualizadas
URLS_ESTADISTICAS = {
    "visados_madrid_viviendas": "https://apps.fomento.gob.es/Boletinonline/sedal/09032810.XLS",
    "visados_madrid_edificios": "https://apps.fomento.gob.es/Boletinonline/sedal/09032820.XLS",
    "viviendas_libres_anual":   "https://apps.fomento.gob.es/BoletinOnline2/sedal/32200500.XLS",
    "viviendas_libres_terminadas": "https://apps.fomento.gob.es/BoletinOnline2/sedal/32201000.XLS",
}

# 3. get_visados_getafe() — nuevo parser basado en agregación mensual
MESES = {"Ene", "Feb", "Mar", "Abr", "May", "Jun",
         "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"}
year_totals = {}
current_year = None
for _, row in df_raw.iterrows():
    c0 = row.iloc[0]  # año (sólo en primer mes del año)
    c2 = row.iloc[2]  # abreviatura del mes
    c4 = row.iloc[4]  # nº viviendas
    if isinstance(c0, (int, float)) and 1990 < c0 < 2030:
        current_year = int(c0)
    if current_year and isinstance(c2, str) and c2.strip() in MESES and pd.notna(c4):
        year_totals[current_year] = year_totals.get(current_year, 0.0) + float(c4)
```

### Verificación

- [x] Test `test_mivau_urls_apuntan_a_fomento` → todas las URLs apuntan a `fomento.gob.es` ✅
- [x] Test `test_mivau_url_visados_descarga_xls` → HTTP 200, 1.1 MB, magic bytes XLS válido ✅
- [x] `initial_load --fuente vivienda --force` → **35 años (1991-2025) parseados, 12 insertados** ✅

### Resultado en BD

| fuente | registros | rango |
|--------|-----------|-------|
| `mivau` | 12 | 1991–2025 (años no cubiertos por referencia) |
| `mivau_referencia` | 23 | 2001–2023 (datos de referencia hardcoded) |
| **Total** | **35** | **1991–2025** |

---

## Referencias

- [[Bienvenido]] — Índice del proyecto
- [[v0.2 — Ingesta histórica y Tendencias]] — Roadmap activo (estas correcciones desbloquean las tareas 2.x)

---

## Resumen de estado final

| Scraper | Error original | Estado | Resultado |
|---------|---------------|--------|-----------|
| `BOCMScraper` | 404 — `/buscador` obsoleto | ✅ **Resuelto** | HTTP 200, escaneando sin errores |
| `ViviendaScraper` | 403 + xlrd + parser | ✅ **Resuelto** | 35 años de datos históricos en BD |
| `INEScraper` (ETN 46964) | Tabla inexistente (404) | ✅ **Resuelto** | Serie ETDP3899 (Madrid prov.) — datos reales 2007-hoy |
| `CatastroScraper` (WFS) | DNS sin internet en Docker | ⚠️ No bloqueante | 12 barrios hardcoded cargados |

---

## Bug 3 — Vite proxy: datos no aparecen en el frontend

> [!success] Resuelto — 2026-03-18

### Síntoma
Los endpoints de la API devolvían datos correctamente (`/api/v1/tendencias/obra-nueva` → 200 con 23 registros), pero el frontend mostraba "Sin datos en el rango seleccionado".

### Causa
El proxy de Vite apuntaba a `http://localhost:8001`, pero dentro del contenedor `getafe_frontend` ese `localhost` es el propio contenedor, no el host de Docker. El backend está en la red interna Docker con nombre `backend`.

```typescript
// vite.config.ts — ANTES (roto en Docker)
target: 'http://localhost:8001'

// DESPUÉS (correcto)
target: 'http://backend:8000'  // nombre del servicio Docker Compose
```

### Solución
Cambiar el proxy target en `frontend/vite.config.ts` al nombre del servicio Docker Compose (`backend:8000`).

### Verificación
```
GET http://localhost:5173/api/v1/tendencias/obra-nueva → 200, 23 registros ✅
GET http://localhost:5173/api/v1/tendencias/valor-suelo → 200, 312 registros ✅
GET http://localhost:5173/api/v1/tendencias/kpis → { viviendas: 987, valor: 1748 €/m² } ✅
```

---

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `backend/app/scrapers/bocm.py` | URL `/buscador` → `/advanced-search`; nuevos params y selectores CSS |
| `backend/app/scrapers/vivienda.py` | `URLS_ESTADISTICAS` → `fomento.gob.es`; parser mensual agregado |
| `backend/requirements.txt` | Añadido `xlrd>=2.0.1`, `openpyxl>=3.1.0` |
| `backend/tests/test_scrapers.py` | 5 tests nuevos (3 estáticos + 2 integración) |
| `backend/pytest.ini` | Marcador `integration` registrado |
| `frontend/vite.config.ts` | Proxy target: `localhost:8001` → `backend:8000` |
| `backend/app/api/routes/tendencias.py` | KPI endpoint mejorado: filtra nulls, añade valor suelo y variación % |

---

## Bug 4 — INE scraper: tabla ETN 46964 inexistente → serie ETDP3899

> [!success] Resuelto completamente — 2026-03-19

### Síntoma original

```
app.scrapers.ine:get_tabla:60 - Error al obtener tabla INE 46964:
Redirect response '301 Moved Permanently' for url
'https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/46964'
Redirect location: '/wstempus/jsCache/ES/DATOS_TABLA/46964'
→ HTTP 404 en /wstempus/jsCache/ES/DATOS_TABLA/46964
```

`get_transacciones_inmobiliarias()` devuelve DataFrame vacío. Fallback `TRANSACCIONES_REFERENCIA` activo → 22 filas hardcoded en `datos_ine`.

### Causa raíz (diagnóstico completo — 2026-03-19)

Dos errores encadenados en el scraper original:

1. **Operación incorrecta**: el comentario del módulo citaba la operación `10058` para ETN. La operación real es **ETDP** (Id=7, Cod_IOE=30168). La operación 10058 no existe en el wstempus/Tempus3 del INE → devuelve `[]`.

2. **Tabla inexistente**: la tabla `46964` nunca existió en el INE. El ID era incorrecto desde el inicio → 404 real (no problema de redirect). La API INE usa la tabla 46964 como alias caché que también falla.

3. **Sin datos municipales**: la operación ETDP **no publica datos a nivel municipal** (solo CCAA y provincia). Variables disponibles: `CCAA`, `PROV`. Getafe a nivel municipal no existe en esta operación del INE.

### Afectaba

- `INEScraper.get_transacciones_inmobiliarias()` — `backend/app/scrapers/ine.py`
- Tabla `datos_ine` — datos de referencia hardcoded en lugar de datos reales
- Documentación del módulo (operación 10058 incorrecta)

### Fix aplicado — 2026-03-19

**Serie correcta identificada:** `ETDP3899` — Madrid provincia, compraventa general (vivienda libre + protegida), mensual 2007-hoy. 228 puntos mensuales verificados.

```python
# backend/app/scrapers/ine.py — get_transacciones_inmobiliarias()

# ANTES (roto — tabla inexistente)
datos = self.get_tabla("46964")  # ID tabla transacciones por municipio

# DESPUÉS (correcto — serie verificada, datos reales)
datos = self.get_serie("ETDP3899")  # Madrid provincia. Compraventa general. Mensual 2007-hoy
# + procesamiento: agrega datos mensuales por año → columnas [anno, transacciones]
```

Series disponibles para ETDP en Madrid (todas verificadas):

| Serie | Descripción | Ámbito |
|-------|-------------|--------|
| `ETDP3899` | Compraventa general | Provincia Madrid |
| `ETDP3898` | Vivienda nueva | Provincia Madrid |
| `ETDP3897` | Vivienda segunda mano | Provincia Madrid |
| `ETDP1761` | Compraventa general | CCAA Madrid |

Se usa `ETDP3899` (provincia) como proxy de actividad inmobiliaria para Getafe.

### Datos reales obtenidos

| Anno | Transacciones (Madrid prov.) |
|------|------------------------------|
| 2007 | ~85.000 (máximo pre-crisis) |
| 2012 | ~41.000 (mínimo crisis) |
| 2022 | ~85.000 (máximo reciente) |

### Verificación

- [x] `test_ine_scraper_sigue_redirects` → `follow_redirects=True` confirmado ✅
- [x] `test_ine_transacciones_usa_serie_etdp3899` → código usa ETDP3899, no tabla 46964 ✅
- [x] `test_ine_etdp3899_devuelve_datos_madrid` → DataFrame con ≥10 años, >10.000 transacciones/año ✅

---

## Referencias

- [[v0.2 — Ingesta histórica y Tendencias]] — Puntos 2 y 4
- Scrapers: `backend/app/scrapers/bocm.py`, `backend/app/scrapers/vivienda.py`, `backend/app/scrapers/ine.py`
- Tests: `backend/tests/test_scrapers.py`, `backend/tests/test_tendencias.py`
