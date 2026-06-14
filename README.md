# SocTrace MVP

Primer MVP end-to-end con:

- `backend/`: FastAPI + SQLAlchemy 2 + psycopg 3 + PostgreSQL/PostGIS
- `soctrace-web/`: React + TypeScript + Vite + Tailwind + MapLibre + Deck.gl

## Base de datos

La implementación usa la base real `mijas` y se apoya en:

- `marts.v_mapa_seccion_2023`
- `marts.mijas_features_panel`

## Arranque rápido

### 1. Recomendado: script único

```bash
./run-dev.sh
```

Este flujo:

- crea `.venv` si no existe
- instala dependencias del backend si faltan
- crea `backend/.env` y `soctrace-web/.env` desde sus ejemplos
- arranca FastAPI en `127.0.0.1:8000`
- espera al `healthcheck`
- arranca Vite en `127.0.0.1:5173`

### 2. Backend manual

```bash
python3 -m venv .venv
./.venv/bin/pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
cd backend
../.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Variables:

- `DATABASE_URL=postgresql+psycopg:///mijas`

### 3. Frontend manual

```bash
cd soctrace-web
npm install
cp .env.example .env
npm run dev
```

## Endpoint del mapa

```text
GET /api/v1/geo/sections?municipality_id=29070&year=2023
```

## Auth de demo friends & family

La demo del dashboard usa Supabase Auth con email y contrasena. No hay registro
publico: los usuarios se crean manualmente en Supabase Auth y despues se validan
contra `soctrace-web/src/auth/accessControl.ts`.

Usuarios autorizados iniciales:

- `soctrace@gmail.com`: `admin`, acceso `full`
- `espaciotania@gmail.com`: `demo_full`, acceso `full`
- `acatafal@gmail.com`: `demo_full`, acceso `full`

Variables frontend:

```env
VITE_SUPABASE_URL=https://hkgwspzgpkzjhdemwjhf.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=sb_publishable_y2TryAvwuUquwvOSwEpKHA_2spCnnH_
VITE_BYPASS_AUTH=true
```

Desarrollo local:
`VITE_BYPASS_AUTH=true`

Prueba de login real:
`VITE_BYPASS_AUTH=false`

Produccion:
`VITE_BYPASS_AUTH=false`

La publishable key puede estar en frontend. No se deben usar ni exponer secret
keys, service role keys ni passwords de base de datos en React/Vite.

La tabla de logs de acceso esta documentada en
`soctrace-web/supabase/demo_access_logs.sql`. Los eventos minimos son
`login_success`, `login_denied`, `dashboard_enter`, `dashboard_exit` y
`heartbeat`. Si la tabla no existe todavia, el tracking falla de forma silenciosa
para no bloquear el login.

Supabase Free es suficiente para esta fase friends & family. No se implementan
pagos ni billing. La arquitectura queda preparada para una fase posterior con
roles, organizaciones, permisos por municipio, limites de uso del AI Analyst y
modulos premium.

## MVP visible

Al abrir `http://localhost:5173/login` y validar un usuario autorizado:

- carga Mijas
- renderiza sus secciones reales
- colorea por `population_density`
- ajusta el bbox del municipio
- permite hover y click
- carga detalle real de sección en el panel derecho
