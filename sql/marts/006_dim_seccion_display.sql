-- SocTrace | Dimension comercial de secciones (Mijas 2023)
-- Script idempotente: crea tabla si no existe, limpia e inserta 37 filas.

CREATE TABLE IF NOT EXISTS marts.dim_seccion_display (
    seccion_id text PRIMARY KEY,
    seccion_numero_visible text NOT NULL,
    nombre_barrio text,
    zona_macro text,
    label_cliente text
);

TRUNCATE TABLE marts.dim_seccion_display;

INSERT INTO marts.dim_seccion_display (
    seccion_id,
    seccion_numero_visible,
    nombre_barrio,
    zona_macro,
    label_cliente
)
VALUES
    ('2907001001', '01', 'Mijas Oeste / Valtocado', 'Pueblo', 'Sección 01 · Mijas Oeste / Valtocado'),
    ('2907001002', '02', 'Mijas Este', 'Pueblo', 'Sección 02 · Mijas Este'),
    ('2907001003', '03', 'Las Cañadas', 'Las Lagunas', 'Sección 03 · Las Cañadas'),
    ('2907001004', '04', 'Centro Salud', 'Las Lagunas', 'Sección 04 · Centro Salud'),
    ('2907001005', '05', 'Los Santiago', 'Las Lagunas', 'Sección 05 · Los Santiago'),
    ('2907001006', '06', 'María Barranco Sur', 'Las Lagunas', 'Sección 06 · María Barranco Sur'),
    ('2907001007', '07', 'Cala de Mijas', 'Cala', 'Sección 07 · Cala de Mijas'),
    ('2907001008', '08', 'Barrio de los santos', 'Las Lagunas', 'Sección 08 · Barrio de los santos'),
    ('2907001009', '09', 'Barrio de las flores Este', 'Las Lagunas', 'Sección 09 · Barrio de las flores Este'),
    ('2907001010', '10', 'El Coto / Lagarejo', 'Las Lagunas', 'Sección 10 · El Coto / Lagarejo'),
    ('2907001011', '11', 'Calahonda Sur / El Zoco', 'Cala', 'Sección 11 · Calahonda Sur / El Zoco'),
    ('2907001012', '12', 'Avda Los Lirios / Ferrán Caballero', 'Las Lagunas', 'Sección 12 · Avda Los Lirios / Ferrán Caballero'),
    ('2907001013', '13', 'Osunillas', 'Pueblo', 'Sección 13 · Osunillas'),
    ('2907001014', '14', 'María Barranco Norte', 'Las Lagunas', 'Sección 14 · María Barranco Norte'),
    ('2907001015', '15', 'Barrio de los ríos', 'Las Lagunas', 'Sección 15 · Barrio de los ríos'),
    ('2907001016', '16', 'El Juncal', 'Las Lagunas', 'Sección 16 · El Juncal'),
    ('2907001017', '17', 'Campo Mijas', 'Las Lagunas', 'Sección 17 · Campo Mijas'),
    ('2907001018', '18', 'Camino Campanales', 'Las Lagunas', 'Sección 18 · Camino Campanales'),
    ('2907001019', '19', 'Barrio de las flores Oeste', 'Las Lagunas', 'Sección 19 · Barrio de las flores Oeste'),
    ('2907001020', '20', 'Parque Andalucía', 'Las Lagunas', 'Sección 20 · Parque Andalucía'),
    ('2907001021', '21', 'El Albero', 'Las Lagunas', 'Sección 21 · El Albero'),
    ('2907001022', '22', 'El Chaparral', 'Cala', 'Sección 22 · El Chaparral'),
    ('2907001023', '23', 'Riviera Sur', 'Cala', 'Sección 23 · Riviera Sur'),
    ('2907001024', '24', 'Doña Ermita / Pol San Rafael', 'Las Lagunas', 'Sección 24 · Doña Ermita / Pol San Rafael'),
    ('2907001025', '25', 'María Zambrano Este', 'Las Lagunas', 'Sección 25 · María Zambrano Este'),
    ('2907001026', '26', 'Mijas Golf', 'Diseminados', 'Sección 26 · Mijas Golf'),
    ('2907001027', '27', 'Torrenueva', 'Cala', 'Sección 27 · Torrenueva'),
    ('2907001028', '28', 'Cerros del Águila / La Ponderosa', 'Diseminados', 'Sección 28 · Cerros del Águila / La Ponderosa'),
    ('2907001029', '29', 'Doña Ermita Este', 'Las Lagunas', 'Sección 29 · Doña Ermita Este'),
    ('2907001030', '30', 'Parque Los Olivos / La Noria', 'Cala', 'Sección 30 · Parque Los Olivos / La Noria'),
    ('2907001031', '31', 'Calahonda Norte', 'Cala', 'Sección 31 · Calahonda Norte'),
    ('2907001032', '32', 'Entrerríos', 'Diseminados', 'Sección 32 · Entrerríos'),
    ('2907001033', '33', 'La Vega', 'Las Lagunas', 'Sección 33 · La Vega'),
    ('2907001034', '34', 'Riviera Norte', 'Cala', 'Sección 34 · Riviera Norte'),
    ('2907001035', '35', 'Media Legua / Puebla Tranquila', 'Diseminados', 'Sección 35 · Media Legua / Puebla Tranquila'),
    ('2907001036', '36', 'Sierrezuela (Las Lagunas)', 'La Cala', 'Sección 36 · Sierrezuela (Las Lagunas)'),
    ('2907001037', '37', 'María Zambrano Oeste', 'Las Lagunas', 'Sección 37 · María Zambrano Oeste');
