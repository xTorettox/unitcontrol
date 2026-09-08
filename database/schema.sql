-- Sullair Argentina - Control de Vehículos (FSSA 106 Rev. 06)
-- Script de inicialización de tablas (Pre-fijadas con 'sullair_' para no interferir con otras tablas)

CREATE TABLE IF NOT EXISTS sullair_users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'comercial', -- 'admin', 'gestor_cass', 'responsable_flota', 'comercial'
    password_hash TEXT NOT NULL,
    assigned_vehicle_id TEXT,
    signature_png TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sullair_vehicles (
    id TEXT PRIMARY KEY,
    interno TEXT NOT NULL,
    patente TEXT UNIQUE NOT NULL,
    marca TEXT NOT NULL,
    modelo TEXT NOT NULL,
    km_actual INTEGER DEFAULT 0,
    vtv_vencimiento TEXT,
    seguro_vencimiento TEXT,
    seguro_poliza TEXT,
    tarjeta_verde BOOLEAN DEFAULT TRUE,
    manual BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sullair_inspections (
    id TEXT PRIMARY KEY,
    fecha TEXT NOT NULL,
    mes_periodo TEXT NOT NULL, -- e.g. '2026-09'
    user_id TEXT NOT NULL,
    user_name TEXT NOT NULL,
    vehicle_id TEXT,
    interno TEXT NOT NULL,
    patente TEXT NOT NULL,
    marca TEXT NOT NULL,
    modelo TEXT NOT NULL,
    km INTEGER NOT NULL DEFAULT 0,
    tarjeta_verde_si_no TEXT DEFAULT 'SI',
    manual_si_no TEXT DEFAULT 'SI',
    vtv_si_no TEXT DEFAULT 'SI',
    vtv_vencimiento TEXT,
    seguro_si_no TEXT DEFAULT 'SI',
    seguro_vencimiento TEXT,
    observaciones TEXT,
    realizo_nombre TEXT,
    realizo_firma_png TEXT,
    responsable_sitio_nombre TEXT,
    responsable_sitio_firma_png TEXT,
    status TEXT DEFAULT 'pendiente_revision', -- 'aprobado', 'observado', 'pendiente_revision'
    nc_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sullair_inspection_items (
    id TEXT PRIMARY KEY,
    inspection_id TEXT NOT NULL,
    section TEXT NOT NULL,
    item_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'C', -- 'C', 'NC', 'NA'
    has_photo BOOLEAN DEFAULT FALSE,
    observation TEXT,
    FOREIGN KEY (inspection_id) REFERENCES sullair_inspections(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sullair_inspection_photos (
    id TEXT PRIMARY KEY,
    inspection_id TEXT NOT NULL,
    item_name TEXT NOT NULL,
    file_name TEXT NOT NULL,
    image_base64 TEXT NOT NULL,
    caption TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (inspection_id) REFERENCES sullair_inspections(id) ON DELETE CASCADE
);
