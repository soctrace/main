CREATE SCHEMA IF NOT EXISTS core;

DROP VIEW IF EXISTS marts.v_ranking_municipal CASCADE;

ALTER TABLE core.election DROP CONSTRAINT IF EXISTS election_tipo_eleccion_code_fkey;
ALTER TABLE core.election DROP CONSTRAINT IF EXISTS election_tipo_eleccion_code_anio_mes_num_vuelta_key;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'core'
          AND table_name = 'election_type'
          AND column_name = 'tipo_eleccion_code'
          AND data_type <> 'text'
    ) THEN
        ALTER TABLE core.election_type
            ALTER COLUMN tipo_eleccion_code TYPE TEXT
            USING CASE TRIM(tipo_eleccion_code)
                WHEN '02' THEN 'CONGRESO'
                WHEN '04' THEN 'MUNICIPALES'
                WHEN '07' THEN 'PARLAMENTO_EUROPEO'
                ELSE TRIM(tipo_eleccion_code)
            END;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'core'
          AND table_name = 'election'
          AND column_name = 'tipo_eleccion_code'
          AND data_type <> 'text'
    ) THEN
        ALTER TABLE core.election
            ALTER COLUMN tipo_eleccion_code TYPE TEXT
            USING CASE TRIM(tipo_eleccion_code)
                WHEN '02' THEN 'CONGRESO'
                WHEN '04' THEN 'MUNICIPALES'
                WHEN '07' THEN 'PARLAMENTO_EUROPEO'
                ELSE TRIM(tipo_eleccion_code)
            END;
    END IF;
END $$;

INSERT INTO core.election_type (tipo_eleccion_code, descripcion)
VALUES
    ('CONGRESO', 'Elecciones al Congreso de los Diputados'),
    ('MUNICIPALES', 'Elecciones Municipales'),
    ('PARLAMENTO_EUROPEO', 'Elecciones al Parlamento Europeo'),
    ('ANDALUZAS', 'Elecciones Andaluzas')
ON CONFLICT (tipo_eleccion_code) DO UPDATE
SET descripcion = EXCLUDED.descripcion;

ALTER TABLE core.election
    ADD COLUMN IF NOT EXISTS tipo_eleccion_nombre TEXT,
    ADD COLUMN IF NOT EXISTS source_folder TEXT,
    ADD COLUMN IF NOT EXISTS source_file TEXT,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'core'
          AND table_name = 'election'
          AND column_name = 'election_date'
          AND is_generated <> 'NEVER'
    ) THEN
        ALTER TABLE core.election ALTER COLUMN election_date DROP EXPRESSION;
    END IF;
END $$;

UPDATE core.election e
SET tipo_eleccion_nombre = et.descripcion
FROM core.election_type et
WHERE e.tipo_eleccion_code = et.tipo_eleccion_code
  AND e.tipo_eleccion_nombre IS NULL;

ALTER TABLE core.election
    ADD CONSTRAINT election_tipo_eleccion_code_fkey
    FOREIGN KEY (tipo_eleccion_code)
    REFERENCES core.election_type(tipo_eleccion_code);

CREATE UNIQUE INDEX IF NOT EXISTS ux_election_type_year_month_round
    ON core.election (tipo_eleccion_code, anio, mes, COALESCE(num_vuelta, 1));

ALTER TABLE core.datos_mesa
    ADD COLUMN IF NOT EXISTS seccion_id TEXT,
    ADD COLUMN IF NOT EXISTS censo BIGINT,
    ADD COLUMN IF NOT EXISTS votos_emitidos BIGINT,
    ADD COLUMN IF NOT EXISTS votos_validos BIGINT,
    ADD COLUMN IF NOT EXISTS source_file TEXT,
    ADD COLUMN IF NOT EXISTS loaded_at TIMESTAMP DEFAULT NOW();

UPDATE core.datos_mesa
SET
    seccion_id = COALESCE(
        seccion_id,
        LPAD(cod_provincia::text, 2, '0') ||
        LPAD(cod_municipio::text, 3, '0') ||
        LPAD(cod_distrito::text, 2, '0') ||
        cod_seccion
    ),
    censo = COALESCE(censo, censo_ine),
    votos_validos = COALESCE(votos_validos, votos_candidaturas),
    votos_emitidos = COALESCE(votos_emitidos, votos_candidaturas + votos_blanco + votos_nulos)
WHERE seccion_id IS NULL
   OR censo IS NULL
   OR votos_validos IS NULL
   OR votos_emitidos IS NULL;

ALTER TABLE core.resultados_mesa
    ADD COLUMN IF NOT EXISTS seccion_id TEXT,
    ADD COLUMN IF NOT EXISTS source_file TEXT,
    ADD COLUMN IF NOT EXISTS loaded_at TIMESTAMP DEFAULT NOW();

UPDATE core.resultados_mesa
SET seccion_id = COALESCE(
    seccion_id,
    LPAD(cod_provincia::text, 2, '0') ||
    LPAD(cod_municipio::text, 3, '0') ||
    LPAD(cod_distrito::text, 2, '0') ||
    cod_seccion
)
WHERE seccion_id IS NULL;

CREATE TABLE IF NOT EXISTS core.resultados_seccion (
    election_id BIGINT NOT NULL REFERENCES core.election(election_id) ON DELETE CASCADE,
    seccion_id TEXT NOT NULL,
    anio INT NOT NULL,
    mes INT,
    tipo_eleccion_code TEXT NOT NULL,

    cod_candidatura TEXT NOT NULL,
    siglas TEXT,
    denominacion TEXT,

    votos_partido BIGINT,
    votos_validos BIGINT,
    votos_emitidos BIGINT,
    votos_blanco BIGINT,
    votos_nulos BIGINT,
    censo BIGINT,

    pct_voto NUMERIC(10,6),

    source_type TEXT,
    source_file TEXT,
    updated_at TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (election_id, seccion_id, cod_candidatura)
);

CREATE INDEX IF NOT EXISTS idx_resultados_seccion_election
    ON core.resultados_seccion (election_id);

CREATE INDEX IF NOT EXISTS idx_resultados_seccion_seccion
    ON core.resultados_seccion (seccion_id);

CREATE INDEX IF NOT EXISTS idx_resultados_seccion_tipo_anio_mes
    ON core.resultados_seccion (tipo_eleccion_code, anio, mes);

INSERT INTO core.resultados_seccion (
    election_id,
    seccion_id,
    anio,
    mes,
    tipo_eleccion_code,
    cod_candidatura,
    siglas,
    denominacion,
    votos_partido,
    votos_validos,
    votos_emitidos,
    votos_blanco,
    votos_nulos,
    censo,
    pct_voto,
    source_type,
    source_file
)
WITH votos AS (
    SELECT
        rm.election_id,
        COALESCE(
            rm.seccion_id,
            LPAD(rm.cod_provincia::text, 2, '0') ||
            LPAD(rm.cod_municipio::text, 3, '0') ||
            LPAD(rm.cod_distrito::text, 2, '0') ||
            rm.cod_seccion
        ) AS seccion_id,
        rm.cod_candidatura::text AS cod_candidatura,
        SUM(rm.votos)::bigint AS votos_partido,
        MAX(rm.source_file) AS source_file
    FROM core.resultados_mesa rm
    GROUP BY
        rm.election_id,
        COALESCE(
            rm.seccion_id,
            LPAD(rm.cod_provincia::text, 2, '0') ||
            LPAD(rm.cod_municipio::text, 3, '0') ||
            LPAD(rm.cod_distrito::text, 2, '0') ||
            rm.cod_seccion
        ),
        rm.cod_candidatura
),
totales AS (
    SELECT
        dm.election_id,
        COALESCE(
            dm.seccion_id,
            LPAD(dm.cod_provincia::text, 2, '0') ||
            LPAD(dm.cod_municipio::text, 3, '0') ||
            LPAD(dm.cod_distrito::text, 2, '0') ||
            dm.cod_seccion
        ) AS seccion_id,
        SUM(COALESCE(dm.censo, dm.censo_ine))::bigint AS censo,
        SUM(COALESCE(dm.votos_emitidos, dm.votos_candidaturas + dm.votos_blanco + dm.votos_nulos))::bigint AS votos_emitidos,
        SUM(COALESCE(dm.votos_validos, dm.votos_candidaturas))::bigint AS votos_validos,
        SUM(dm.votos_blanco)::bigint AS votos_blanco,
        SUM(dm.votos_nulos)::bigint AS votos_nulos
    FROM core.datos_mesa dm
    GROUP BY
        dm.election_id,
        COALESCE(
            dm.seccion_id,
            LPAD(dm.cod_provincia::text, 2, '0') ||
            LPAD(dm.cod_municipio::text, 3, '0') ||
            LPAD(dm.cod_distrito::text, 2, '0') ||
            dm.cod_seccion
        )
)
SELECT
    v.election_id,
    v.seccion_id,
    e.anio,
    e.mes,
    e.tipo_eleccion_code,
    v.cod_candidatura,
    c.siglas,
    c.denominacion,
    v.votos_partido,
    t.votos_validos,
    t.votos_emitidos,
    t.votos_blanco,
    t.votos_nulos,
    t.censo,
    ROUND(v.votos_partido::numeric / NULLIF(t.votos_validos, 0), 6) AS pct_voto,
    'OFFICIAL_MESA_ZIP',
    COALESCE(v.source_file, e.source_file)
FROM votos v
JOIN totales t
  ON t.election_id = v.election_id
 AND t.seccion_id = v.seccion_id
JOIN core.election e
  ON e.election_id = v.election_id
LEFT JOIN core.candidatura c
  ON c.election_id = v.election_id
 AND c.cod_candidatura::text = v.cod_candidatura
ON CONFLICT (election_id, seccion_id, cod_candidatura)
DO UPDATE SET
    anio = EXCLUDED.anio,
    mes = EXCLUDED.mes,
    tipo_eleccion_code = EXCLUDED.tipo_eleccion_code,
    siglas = EXCLUDED.siglas,
    denominacion = EXCLUDED.denominacion,
    votos_partido = EXCLUDED.votos_partido,
    votos_validos = EXCLUDED.votos_validos,
    votos_emitidos = EXCLUDED.votos_emitidos,
    votos_blanco = EXCLUDED.votos_blanco,
    votos_nulos = EXCLUDED.votos_nulos,
    censo = EXCLUDED.censo,
    pct_voto = EXCLUDED.pct_voto,
    source_type = EXCLUDED.source_type,
    source_file = EXCLUDED.source_file,
    updated_at = NOW();
