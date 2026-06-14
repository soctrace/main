# SocTrace Backend MVP

## Variables de entorno

1. Copia `backend/.env.example` a `backend/.env`.
2. Ajusta `DATABASE_URL` si no usas el socket/local DB por defecto.

Ejemplo:

```env
DATABASE_URL=postgresql+psycopg:///mijas
APP_HOST=0.0.0.0
APP_PORT=8000
```

## Instalar dependencias

```bash
python3 -m pip install -r backend/requirements.txt
```

## Arrancar la API

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints MVP

- `GET /api/v1/municipalities`
- `GET /api/v1/metadata/variables`
- `GET /api/v1/geo/sections?municipality_id=29070&year=2023`
- `GET /api/v1/sections/2907001001`
- `GET /api/v1/forecasts/municipalities/29070/elections/2027`
- `GET /api/v1/forecasts/sections/2907001001/elections/2027`
- `POST /api/v1/analyst/ask`

## Auth TODO

El MVP friends & family protege el dashboard desde el frontend con Supabase Auth
y una allowlist local. En la siguiente fase, FastAPI debe validar el JWT enviado
por el frontend en `Authorization: Bearer <token>`. En produccion, las APIs
sensibles no deben quedar protegidas solo por frontend.

## SocTrace Local Analyst · Mijas

El endpoint conversacional recibe una pregunta y siempre devuelve una respuesta
interpretada con confianza, fuentes internas, notas metodologicas y `audit_id`.
Las tablas y especificaciones de graficos son auxiliares: nunca sustituyen la
explicacion natural.

```json
{
  "question": "Calcula los cocientes D'Hondt del PSOE en las municipales de 2023",
  "municipality_id": "29070"
}
```

## Endpoint usado por el mapa

El dashboard consume:

```text
GET /api/v1/geo/sections?municipality_id=29070&year=2023
```

## Forecast Engine V1

Carga el escenario base estructural para Municipales 2027 y ejecuta su QA:

```bash
psql -d mijas -v ON_ERROR_STOP=1 -f sql/marts/024_mijas_political_context_counterweights.sql
psql -d mijas -v ON_ERROR_STOP=1 -f sql/marts/023_electoral_forecasting_2027.sql
psql -d mijas -v ON_ERROR_STOP=1 -f sql/qa/013_qa_electoral_forecasting_2027.sql
psql -d mijas -v ON_ERROR_STOP=1 -f sql/qa/014_qa_mijas_political_context_counterweights.sql
```

El resultado es una estimación interna con incertidumbre explícita. No es una
encuesta y todavía no incorpora calibración Oraculum. Los contrapesos
contextuales se tratan como hipótesis acotadas y auditables, no como hechos ni
transferencias automáticas de voto.
