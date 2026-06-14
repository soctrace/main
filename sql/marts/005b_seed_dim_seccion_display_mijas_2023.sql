WITH src AS (
    SELECT *
    FROM (
        VALUES
            ('01', 'Mijas Oeste / Valtocado', 'Pueblo'),
            ('02', 'Mijas Este', 'Pueblo'),
            ('03', 'Las Cañadas', 'Las Lagunas'),
            ('04', 'Centro Salud', 'Las Lagunas'),
            ('05', 'Los Santiago', 'Las Lagunas'),
            ('06', 'María Barranco Sur', 'Las Lagunas'),
            ('07', 'Cala de Mijas', 'Cala'),
            ('08', 'Barrio de los santos', 'Las Lagunas'),
            ('09', 'Barrio de las flores Este', 'Las Lagunas'),
            ('10', 'El Coto / Lagarejo', 'Las Lagunas'),
            ('11', 'Calahonda Sur / El Zoco', 'Cala'),
            ('12', 'Avda Los Lirios / Ferrán Caballero', 'Las Lagunas'),
            ('13', 'Osunillas', 'Pueblo'),
            ('14', 'María Barranco Norte', 'Las Lagunas'),
            ('15', 'Barrio de los ríos', 'Las Lagunas'),
            ('16', 'El Juncal', 'Las Lagunas'),
            ('17', 'Campo Mijas', 'Las Lagunas'),
            ('18', 'Camino Campanales', 'Las Lagunas'),
            ('19', 'Barrio de las flores Oeste', 'Las Lagunas'),
            ('20', 'Parque Andalucía', 'Las Lagunas'),
            ('21', 'El Albero', 'Las Lagunas'),
            ('22', 'El Chaparral', 'Cala'),
            ('23', 'Riviera Sur', 'Cala'),
            ('24', 'Doña Ermita / Pol San Rafael', 'Las Lagunas'),
            ('25', 'María Zambrano Este', 'Las Lagunas'),
            ('26', 'Mijas Golf', 'Diseminados'),
            ('27', 'Torrenueva', 'Cala'),
            ('28', 'Cerros del Águila / La Ponderosa', 'Diseminados'),
            ('29', 'Doña Ermita Este', 'Las Lagunas'),
            ('30', 'Parque Los Olivos / La Noria', 'Cala'),
            ('31', 'Calahonda Norte', 'Cala'),
            ('32', 'Entrerríos', 'Diseminados'),
            ('33', 'La Vega', 'Las Lagunas'),
            ('34', 'Riviera Norte', 'Cala'),
            ('35', 'Media Legua / Puebla Tranquila', 'Diseminados'),
            ('36', 'Sierrezuela (Las Lagunas)', 'La Cala'),
            ('37', 'María Zambrano Oeste', 'Las Lagunas')
    ) AS v(seccion_numero_visible, nombre_barrio, zona_macro)
),
final_rows AS (
    SELECT
        '29070010' || src.seccion_numero_visible AS seccion_id,
        src.seccion_numero_visible,
        src.nombre_barrio,
        src.zona_macro,
        'Sección ' || src.seccion_numero_visible || ' · ' || src.nombre_barrio AS label_cliente
    FROM src
)
INSERT INTO marts.dim_seccion_display (
    seccion_id,
    seccion_numero_visible,
    nombre_barrio,
    zona_macro,
    label_cliente
)
SELECT
    seccion_id,
    seccion_numero_visible,
    nombre_barrio,
    zona_macro,
    label_cliente
FROM final_rows
ON CONFLICT (seccion_id) DO UPDATE
SET
    seccion_numero_visible = EXCLUDED.seccion_numero_visible,
    nombre_barrio = EXCLUDED.nombre_barrio,
    zona_macro = EXCLUDED.zona_macro,
    label_cliente = EXCLUDED.label_cliente;
