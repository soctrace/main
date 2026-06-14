# Familias ETL SocTrace

## Familia A · Geografía
**Fuentes incluidas:** F001  
**Unidad canónica destino:** sección censal  
**Destino principal:** core.seccion  
**Transformaciones clave:**
- validación de geometría
- reproyección a EPSG:4326
- normalización de claves territoriales
- generación de seccion_id / CUSEC canónico

---

## Familia B · Demografía y estructura social por sección
**Fuentes incluidas:** F002, F003  
**Unidad canónica destino:** sección censal  
**Destino principal:** core.poblacion_edad, core.poblacion_nacimiento  
**Transformaciones clave:**
- normalización de nombres de columnas
- normalización de genero / sexo
- normalización de cohortes de edad
- normalización de pais_nacimiento
- conversión de periodo a anio
- validación de seccion_id

---

## Familia C · Electoral relacional
**Fuentes incluidas:** F004, F005, F006, F007, F008, F009  
**Unidad canónica destino:** sección censal  
**Destino principal:** core.election, core.candidatura, core.mesa, core.datos_mesa, core.resultados_mesa, core.resultados_municipio  
**Transformaciones clave:**
- alta de la elección en core.election
- carga de candidaturas
- alta de mesas nuevas en core.mesa
- carga de datos_mesa
- carga de resultados_mesa
- agregación posterior a sección censal
- control histórico de cambios en el mapa de secciones

---

## Familia D · Encuestas
**Fuentes incluidas:** F010  
**Unidad canónica destino:** sección censal  
**Destino principal:** por definir  
**Transformaciones clave:**
- definir unidad de observación
- diseñar agregación a sección
- tratamiento temporal
- anonimización
- posible georreferenciación