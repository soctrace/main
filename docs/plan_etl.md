# Plan ETL SocTrace

## 1. Principio general

Cada fuente seguirá el flujo:

**fichero origen → raw → staging → core → marts**

### Reglas generales
- `raw` preserva el fichero cargado con la mínima transformación posible.
- `staging` tipa, limpia y normaliza nombres/códigos.
- `core` inserta en el modelo relacional canónico.
- `marts` construye datasets analíticos y paneles para visualización y ML.

---

## 2. Orden de ejecución por familias

### Familia A · Geografía
Orden:
1. cargar fichero geográfico en `raw.geo_seccion_YYYY`
2. transformar a `staging.seccion_geo`
3. insertar/actualizar `core.seccion`
4. refrescar marts geográficos

### Familia B · Demografía
Orden:
1. cargar CSV en `raw.demografia_*_YYYY`
2. transformar a `staging.fact_genero_edad` o `staging.fact_genero_pais`
3. insertar en `core.poblacion_edad` o `core.poblacion_nacimiento`
4. refrescar marts demográficos y paneles

### Familia C · Electoral
Orden:
1. cargar candidaturas en `raw.elect_candidaturas_YYYY`
2. cargar datos de mesa en `raw.elect_datos_mesa_YYYY`
3. cargar resultados de mesa en `raw.elect_resultados_mesa_YYYY`
4. cargar resultados de municipio en `raw.elect_resultados_municipio_YYYY`
5. transformar a tablas `staging.*_raw`
6. asegurar alta de elección en `core.election`
7. asegurar alta de candidaturas en `core.candidatura`
8. asegurar alta de mesas nuevas en `core.mesa`
9. insertar en `core.datos_mesa`
10. insertar en `core.resultados_mesa`
11. insertar en `core.resultados_municipio`
12. construir agregados por sección y año
13. refrescar marts electorales y panel temporal

### Familia D · Encuestas
Orden provisional:
1. cargar fichero en `raw.encuesta_<nombre>_<YYYY>`
2. transformar a `staging.encuesta_<nombre>`
3. definir reglas de agregación o georreferenciación
4. insertar en `core.encuesta_respuesta` o `core.encuesta_agregada_seccion`
5. refrescar marts de encuesta

---

## 3. Reglas de normalización por familia

### Geografía
- CRS canónico: EPSG:4326
- geometrías válidas
- clave territorial completa
- generación de `seccion_id`

### Demografía
- `periodo` → `anio`
- `sexo` y `genero` → `genero`
- cohortes de edad normalizadas
- `pais_nacimiento` normalizado
- `seccion_id` validado

### Electoral
- `tipo_eleccion` normalizado contra `core.election_type`
- creación de `election_id`
- `cod_candidatura` con padding canónico
- `cod_seccion` con padding a 3
- `cod_mesa` tipado
- claves de mesa validadas antes de insertar hechos
- resultados agregables a sección

### Encuestas
- definición explícita de unidad de observación
- diseño de clave temporal
- anonimización si aplica
- reglas de asignación territorial antes de cargar a core

---

## 4. Dependencias críticas

### Dependencias geográficas
- no se pueden construir marts geográficos sin `core.seccion`

### Dependencias demográficas
- `core.poblacion_*` debe enlazar con `core.seccion`

### Dependencias electorales
- `core.election` antes que `core.candidatura`
- `core.candidatura` antes que `core.resultados_mesa`
- `core.mesa` antes que `core.datos_mesa` y `core.resultados_mesa`

### Dependencias analíticas
- `marts.features_panel` depende de geografía + demografía + electoral

---

## 5. Decisiones abiertas

- diseño exacto del schema `raw`
- estrategia para armonización territorial entre años
- diseño del modelo de encuestas
- incorporación futura de indicadores socioeconómicos
- convención definitiva para `seccion_id` y su persistencia en tablas core
- estrategia de versionado de cartografía por año
- política de tratamiento de códigos de candidatura históricos

## 6. Principios de automatización

- Cada pipeline debe poder ejecutarse más de una vez sin romper datos existentes.
- Las cargas deben ser idempotentes siempre que sea posible.
- Toda carga debe dejar trazabilidad de `source_file` y `loaded_at`.
- Los scripts Python deben dividirse por familia de fuente, no por año.
- El año debe ser un parámetro de entrada, no parte del nombre del script.
- Las validaciones deben ejecutarse después de cada fase (`raw`, `staging`, `core`).
- Los scripts deben aceptar parámetros por línea de comandos (por ejemplo: `--year`, `--municipio`, `--source-file`).
- Las validaciones deben poder ejecutarse de forma independiente del pipeline principal.