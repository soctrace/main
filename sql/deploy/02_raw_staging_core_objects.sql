-- soctrace MVP Supabase deployment: raw/staging/core object DDL.
-- Execute with psql from the repository root:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f sql/deploy/02_raw_staging_core_objects.sql

\ir ../raw/001_create_raw_demografia_genero_edad_2023.sql
\ir ../raw/002_create_raw_renta_ine_2023.sql
\ir ../raw/003_create_raw_elecciones_municipales_2019_mesa.sql
\ir ../raw/004_create_raw_demografia_genero_edad_multi_anio.sql
\ir ../raw/005_create_raw_renta_ine_2019_2023.sql
\ir ../raw/006_create_raw_fuentes_ingresos_2019_2023.sql
\ir ../raw/007_create_raw_ine_socioeconomic.sql

\ir ../staging/001_create_staging_fact_genero_edad.sql
\ir ../staging/002_create_staging_renta_seccion_2023.sql
\ir ../staging/003_create_manual_precio_m2_seccion_2023.sql
\ir ../staging/004_create_staging_resultados_mesa_2019.sql
\ir ../staging/005_create_staging_fact_genero_edad_multi_anio.sql
\ir ../staging/006_create_staging_renta_seccion_multi_anio.sql
\ir ../staging/007_create_staging_fuentes_ingresos_seccion.sql
\ir ../staging/008_create_staging_socioeconomic_indicator_section.sql

\ir ../core/001_create_core_poblacion_edad.sql
\ir ../core/002_create_core_renta_seccion.sql
\ir ../core/003_create_core_seccion_historica.sql
\ir ../core/004_create_core_candidatura_alias.sql
\ir ../core/005_create_core_elecciones_mun_2019.sql
\ir ../core/006_create_core_fuentes_ingresos_seccion.sql
\ir ../core/007_create_core_electoral_historical.sql
\ir ../core/008_create_core_socioeconomic_indicators.sql
\ir ../core/030_agent_conversation_memory.sql
