# Inventario maestro de fuentes SocTrace

## Objetivo
Registrar todas las fuentes de datos manejadas en el proyecto para rediseñar el ETL y el modelo relacional de forma consistente.

## Tabla de inventario

| id_fuente | nombre_fuente | tipo_fichero | tema | granularidad | unidad_canonica_destino | clave_temporal | necesita_agregacion | necesita_georreferenciacion | años | ambito | clave_territorial_disponible | geometria | estado_actual | schema_destino | tabla_destino_propuesta | observaciones |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F001 | Cartografía secciones 2023 Mijas | GeoJSON / Shapefile | geografía | sección censal | sección censal | anio | no | no | 2023 | Mijas | CUSEC / cod_provincia-cod_municipio-cod_distrito-cod_seccion | sí | cargado | core | core.seccion | geometría base para mapas y joins |
| F002 | Población por género y edad | CSV | demografía | sección censal | sección censal | anio | no | no | 2023 | Mijas | seccion_id | no | cargado | core | core.poblacion_edad | variable canónica género; cohortes normalizadas |
| F003 | Población por país de nacimiento y género | CSV | demografía / migración | sección censal | sección censal | anio | no | no | 2023 | Mijas | seccion_id | no | cargado | core | core.poblacion_nacimiento | país de nacimiento normalizado |
| F004 | Resultados municipales 2023 por mesa | CSV / raw electoral | electoral | mesa | sección censal | election_id / anio | sí | no | 2023 | Mijas | prov-mun-dist-seccion-mesa | no | cargado | core | core.resultados_mesa | requiere agregación posterior a sección |
| F005 | Datos de mesa 2023 | CSV / raw electoral | electoral | mesa | sección censal | election_id / anio | sí | no | 2023 | Mijas | prov-mun-dist-seccion-mesa | no | cargado | core | core.datos_mesa | censo, blancos, nulos, votos candidaturas |
| F006 | Resultados municipales 2019 por mesa | CSV | electoral | mesa | sección censal | election_id / anio | sí | no | 2019 | Mijas | prov-mun-dist-seccion-mesa | no | en integración | core | core.resultados_mesa | 30 secciones en 2019, no 37 |
| F007 | Datos de mesa 2019 | CSV | electoral | mesa | sección censal | election_id / anio | sí | no | 2019 | Mijas | prov-mun-dist-seccion-mesa | no | en integración | core | core.datos_mesa | 63 mesas |
| F008 | Resultados municipales 2019 municipio | CSV | electoral | municipio | municipio / contraste | election_id / anio | no | no | 2019 | Mijas | cod_municipio | no | en integración | core | core.resultados_municipio | útil para comprobación agregada |
| F009 | Candidaturas municipales 2019 | CSV | electoral | candidatura / elección | elección | election_id / anio | no | no | 2019 | España / Mijas filtro | cod_candidatura | no | staging cargado | core | core.candidatura | necesaria para FK de resultados_mesa |
| F010 | Futuras encuestas por sección | CSV / XLSX / otro | encuesta | individuo / sección | sección censal | fecha_encuesta / anio | probablemente sí | probablemente sí | pendiente | Mijas | por definir | no | no iniciado | staging/core | por definir | requerirá diseño específico de agregación |

## Criterios de clasificación

### Tipo de fichero
- CSV
- XLSX
- GeoJSON
- Shapefile
- DAT / fixed-width
- Otros

### Tema
- geografía
- demografía
- migración
- socioeconómico
- electoral
- encuesta

### Granularidad
- municipio
- distrito
- sección censal
- mesa
- candidatura
- individuo

### Estado actual
- identificado
- descargado
- staging cargado
- core cargado
- marts disponible
- en integración
- no iniciado

## Nuevas columnas de diseño ETL

### unidad_canonica_destino
Unidad territorial o analítica a la que queremos llevar finalmente la fuente.
Valores típicos:
- sección censal
- municipio
- individuo
- elección

### clave_temporal
Campo o lógica temporal principal de la fuente.
Ejemplos:
- anio
- anio + mes
- election_id
- fecha_encuesta
- no aplica

### necesita_agregacion
Indica si la fuente no llega ya en la unidad final y hay que agregarla o transformarla.
Valores:
- sí
- no

### necesita_georreferenciacion
Indica si la fuente necesita ser vinculada espacialmente a la sección censal mediante claves, geometría o reglas auxiliares.
Valores:
- sí
- no