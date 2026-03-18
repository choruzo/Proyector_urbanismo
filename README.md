# Proyector Urbanístico — Getafe Dashboard

Dashboard de seguimiento urbanístico para la ciudad de Getafe (Madrid) con visualización de tendencias históricas, predicciones a largo plazo, obra nueva, inversión pública/privada, valor del suelo por barrios y sistema de alertas sobre licitaciones y obra pública.

---

## Objetivo

Centralizar, analizar y visualizar datos urbanísticos de Getafe desde 2001 hasta la actualidad, permitiendo:
- Detectar tendencias en obra nueva y valor del suelo
- Proyectar evolución urbanística a 5-10 años vista mediante modelos de ML
- Monitorizar inversión pública (Ayuntamiento, EMSV, Comunidad de Madrid) y privada
- Recibir alertas automáticas sobre nuevas licitaciones y expedientes urbanísticos

---

## Stack Tecnológico

### Backend
| Componente | Tecnología |
|---|---|
| Framework API | FastAPI (Python 3.12) |
| Base de datos | PostgreSQL 16 + PostGIS |
| ORM | SQLAlchemy 2.x + GeoAlchemy2 |
| Tasks periódicas | Celery + Redis |
| ML / Predicciones | Prophet, scikit-learn, Pandas |
| Scraping | httpx, BeautifulSoup4, feedparser |

### Frontend
| Componente | Tecnología |
|---|---|
| Framework | React 18 + TypeScript + Vite |
| Estilos | Tailwind CSS + shadcn/ui |
| Gráficas | Recharts + Apache ECharts |
| Mapas | React-Leaflet + OpenStreetMap |
| Estado global | Zustand |
| Data fetching | TanStack Query |

### Infraestructura local
- Docker Compose (PostgreSQL, Redis, Backend, Frontend)

---

## Fuentes de Datos

### Fuentes con API oficial (actualizaciones automáticas)
| Fuente | Datos | URL |
|---|---|---|
| Catastro (DGC) | Valor catastral, parcelas, superficies | sede.catastro.meh.es |
| INE | Demográficos, estadísticas de vivienda | servicios.ine.es/wstempus |
| Ministerio de Vivienda | Obra nueva, visados, transacciones | www.mivau.gob.es |
| Datos Abiertos CM | Planeamiento, licencias, urbanismo | datos.comunidad.madrid |
| Registro de la Propiedad | Compraventas (vía IMIE/Colegio Notarial) | — |

### Fuentes con scraping periódico
| Fuente | Datos | Periodicidad |
|---|---|---|
| BOCM | Licitaciones, expedientes, convenios urbanísticos | Diaria |
| Ayuntamiento de Getafe | Licencias de obra, planeamiento PGOU | Semanal |
| EMSV Getafe | Proyectos vivienda pública, suelo municipal | Semanal |
| BOE | Licitaciones estatales en Getafe | Diaria |

### Fuentes de mercado (a evaluar)
- Idealista/Fotocasa — precios de mercado (scraping con moderación)
- API Portales de Transparencia municipales

---

## Páginas del Dashboard

| Página | Descripción |
|---|---|
| **Resumen (Overview)** | KPIs principales: viviendas nuevas, valor medio suelo, inversión activa, alertas recientes |
| **Tendencias urbanísticas** | Series temporales 2001-hoy: obra nueva, licencias, superficie construida |
| **Mapa de valor del suelo** | Coropletas por barrios y distritos de Getafe con evolución de valor |
| **Obra nueva** | Vivienda nueva pública (EMSV) y privada: proyectos, superficie, estado |
| **Inversión pública/privada** | Partidas presupuestarias, licitaciones adjudicadas, proyectos activos |
| **Alertas** | Feed de nuevas publicaciones en BOCM/BOE relacionadas con Getafe |
| **Predicciones** | Modelos Prophet/ML: proyección vivienda new, valor suelo, suelo disponible |

---

## Estructura del Proyecto

```
proyector_urbanismo/
├── backend/
│   ├── app/
│   │   ├── api/routes/          # Endpoints FastAPI por módulo
│   │   ├── core/                # Config, DB, seguridad
│   │   ├── models/              # Modelos SQLAlchemy
│   │   ├── scrapers/            # Módulos de ingesta de datos
│   │   ├── analytics/           # ML, predicciones, análisis
│   │   └── tasks/               # Tareas Celery periódicas
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/               # Páginas del dashboard
│   │   ├── components/          # Componentes reutilizables
│   │   └── services/            # Llamadas a la API
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Inicio rápido (local)

```bash
# 1. Clonar y configurar variables de entorno
cp .env.example .env

# 2. Levantar todos los servicios
docker compose up -d

# 3. Ejecutar migraciones iniciales
docker compose exec backend alembic upgrade head

# 4. Lanzar ingesta inicial de datos históricos (2001-hoy)
docker compose exec backend python -m app.tasks.initial_load

# Frontend disponible en http://localhost:5173
# API + Swagger disponible en http://localhost:8001/docs
```

---

## Roadmap

- [X] **v0.1** — Scaffold completo, conexiones a fuentes, base de datos operativa
- [ ] **v0.2** — Ingesta histórica de datos (2001-hoy), página de Tendencias funcional *(en progreso: backend completado, frontend pendiente)*
- [ ] **v0.3** — Mapa interactivo de valor del suelo por barrios
- [ ] **v0.4** — Sistema de alertas BOCM/BOE automático
- [ ] **v0.5** — Modelos de predicción ML integrados
- [ ] **v1.0** — Dashboard completo, despliegue público

Se trata de crear una aplicacion que muestre los proyectos urbanisticos de la ciudade de getafe, (entraria obra nueva publica o privada, nuevos barrios, ofertas de segunda mano)
