# SocTrace - Architecture

## Vision

SocTrace is a territorial intelligence platform focused on section-level urban, demographic and electoral analytics.

Initial scope:
- Municipality of Mijas (Málaga, Spain)

Future scope:
- Multi-municipality
- Multi-year panels
- AI-assisted querying

---

## Core Principles

1. PostgreSQL/PostGIS as analytical core
2. Clean layered data architecture
3. Frontend decoupled from database
4. AI layer separated from transactional logic
5. Iterative MVP-first development

---

## Current Architecture

Raw sources
↓
Python ETL
↓
PostgreSQL

Schemas:

- raw
- staging
- core
- marts

---

## Schema Roles

### raw
Unmodified imported data

Examples:
- CSVs
- election raw files
- demographic raw datasets

### staging
Cleaning + normalization

### core
Canonical relational model

Examples:
- seccion
- poblacion_edad
- resultados_mesa
- candidatura

### marts
Analytics-ready views / materialized views

Examples:
- mijas_features_panel
- v_resultados_seccion_anio
- v_poblacion_seccion_anio

---

## Frontend (Current Transition)

Old:
- Streamlit MVP

Current:
- soctrace-web
- React
- TypeScript
- Tailwind

---

## Future Production Architecture

Frontend (React)
↓
API Layer
↓
PostgreSQL/PostGIS
↓
AI Query Layer (LLM)

---

## Strategic Direction

PostgreSQL remains source of truth.
Frontend evolves independently.
LLM consumes curated marts / APIs only.