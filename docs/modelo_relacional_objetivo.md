# Modelo relacional objetivo SocTrace

## 1. Arquitectura por capas

### raw
Capa de preservación de fuentes originales cargadas a base de datos.

### staging
Capa de normalización técnica y homogeneización mínima.

### core
Modelo relacional canónico del dominio.

### marts
Capa analítica para paneles, mapas y modelado.

---

## 2. Claves de diseño

- La unidad analítica canónica es la sección censal.
- La clave derivada principal es `seccion_id`.
- Se conservan también `cod_provincia`, `cod_municipio`, `cod_distrito`, `cod_seccion`.
- Todas las tablas fact deben llevar `anio`.
- Las tablas electorales deben llevar además `election_id`.
- Los cambios históricos en el mapa de secciones no se fuerzan a una falsa homogeneidad.

---

## 3. Tablas objetivo por schema

### raw
- raw.geo_seccion_YYYY
- raw.demografia_genero_edad_YYYY
- raw.demografia_genero_pais_YYYY
- raw.elect_candidaturas_YYYY
- raw.elect_datos_mesa_YYYY
- raw.elect_resultados_mesa_YYYY
- raw.elect_resultados_municipio_YYYY
- raw.encuesta_<nombre>_<YYYY>

### staging
- staging.seccion_geo
- staging.fact_genero_edad
- staging.fact_genero_pais
- staging.candidatura_raw
- staging.datos_mesa_raw
- staging.resultados_mesa_raw
- staging.resultados_municipio_raw
- staging.encuesta_<nombre>

### core
#### Dimensiones
- core.municipio
- core.seccion
- core.mesa
- core.election_type
- core.election
- core.candidatura

#### Hechos
- core.poblacion_edad
- core.poblacion_nacimiento
- core.datos_mesa
- core.resultados_mesa
- core.resultados_municipio

#### Futuro
- core.indicadores_socioeconomicos
- core.encuesta_respuesta
- core.encuesta_agregada_seccion

### marts
- marts.demografia_seccion_anio
- marts.electoral_seccion_anio
- marts.features_panel
- marts.mapa_seccion_anio
- marts.encuesta_seccion_anio

---

## 4. Principios para la evolución temporal

- Cada año conserva su propia cartografía real.
- El panel temporal acepta diferencias en número de secciones entre años.
- La armonización territorial interanual, si se necesita, será una capa adicional específica.