-- =========================================================================
-- SULLAIR ARGENTINA - CONTROL DE VEHÍCULOS (FSSA 106 REV. 06)
-- Esquema Oficial de Base de Datos para Supabase y SQLite
-- =========================================================================

-- 1. TABLA DE VEHÍCULOS DE LA FLOTA
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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. TABLA DE USUARIOS Y ROLES
CREATE TABLE IF NOT EXISTS sullair_users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'comercial', -- 'admin', 'gestor_cass', 'responsable_flota', 'comercial'
    password_hash TEXT NOT NULL,
    assigned_vehicle_id TEXT,
    signature_png TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. TABLA DE INSPECCIONES MENSUALES
CREATE TABLE IF NOT EXISTS sullair_inspections (
    id TEXT PRIMARY KEY,
    fecha TEXT NOT NULL,
    mes_periodo TEXT NOT NULL, -- Ej: '2026-09'
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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. TABLA DE ÍTEMS DEL CHECKLIST FSSA 106
CREATE TABLE IF NOT EXISTS sullair_inspection_items (
    id TEXT PRIMARY KEY,
    inspection_id TEXT NOT NULL,
    section TEXT NOT NULL,
    item_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'C', -- 'C' (Cumple), 'NC' (No Cumple), 'NA' (No Aplica)
    has_photo BOOLEAN DEFAULT FALSE,
    observation TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. TABLA DE FOTOS DE EVIDENCIA ADJUNTAS
CREATE TABLE IF NOT EXISTS sullair_inspection_photos (
    id TEXT PRIMARY KEY,
    inspection_id TEXT NOT NULL,
    item_name TEXT NOT NULL,
    file_name TEXT NOT NULL,
    image_base64 TEXT NOT NULL,
    caption TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Habilitar Row Level Security (RLS) y Políticas de Acceso para Supabase
ALTER TABLE sullair_vehicles ENABLE ROW LEVEL SECURITY;
ALTER TABLE sullair_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE sullair_inspections ENABLE ROW LEVEL SECURITY;
ALTER TABLE sullair_inspection_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE sullair_inspection_photos ENABLE ROW LEVEL SECURITY;

-- Políticas de acceso anónimo / autenticado
DO $$
BEGIN
    DROP POLICY IF EXISTS "Allow full access sullair_vehicles" ON sullair_vehicles;
    CREATE POLICY "Allow full access sullair_vehicles" ON sullair_vehicles FOR ALL USING (true) WITH CHECK (true);
    
    DROP POLICY IF EXISTS "Allow full access sullair_users" ON sullair_users;
    CREATE POLICY "Allow full access sullair_users" ON sullair_users FOR ALL USING (true) WITH CHECK (true);
    
    DROP POLICY IF EXISTS "Allow full access sullair_inspections" ON sullair_inspections;
    CREATE POLICY "Allow full access sullair_inspections" ON sullair_inspections FOR ALL USING (true) WITH CHECK (true);
    
    DROP POLICY IF EXISTS "Allow full access sullair_inspection_items" ON sullair_inspection_items;
    CREATE POLICY "Allow full access sullair_inspection_items" ON sullair_inspection_items FOR ALL USING (true) WITH CHECK (true);
    
    DROP POLICY IF EXISTS "Allow full access sullair_inspection_photos" ON sullair_inspection_photos;
    CREATE POLICY "Allow full access sullair_inspection_photos" ON sullair_inspection_photos FOR ALL USING (true) WITH CHECK (true);
EXCEPTION
    WHEN undefined_object THEN NULL;
END $$;

-- DATOS INICIALES DE VEHÍCULOS DE FLOTA
INSERT INTO sullair_vehicles (id, interno, patente, marca, modelo, km_actual, vtv_vencimiento, seguro_vencimiento, seguro_poliza, tarjeta_verde, manual)
VALUES 
    ('v-104', 'INT-104', 'AE 452 CD', 'Toyota', 'Hilux 4x4 D/C', 48250, '2026-11-15', '2026-10-30', 'Allianz - Póliza #994821', true, true),
    ('v-108', 'INT-108', 'AF 892 KL', 'Ford', 'Ranger XLS 3.2', 62100, '2026-09-25', '2026-12-01', 'La Caja - Póliza #331902', true, true),
    ('v-112', 'INT-112', 'AD 311 ZZ', 'Volkswagen', 'Amarok 2.0 TDI', 91500, '2026-09-18', '2026-09-28', 'Zurich - Póliza #772819', true, true),
    ('v-120', 'INT-120', 'AF 444 DF', 'Toyota', 'Yaris XLS 1.5', 700, '2027-01-15', '2027-01-15', 'San Cristóbal - #102938', true, true)
ON CONFLICT (patente) DO UPDATE SET 
    km_actual = EXCLUDED.km_actual,
    vtv_vencimiento = EXCLUDED.vtv_vencimiento,
    seguro_vencimiento = EXCLUDED.seguro_vencimiento;

-- DATOS INICIALES DE USUARIOS Y ROLES
-- fcendra (pass: C4n1ch3r1426) -> Federico Cendra (admin)
-- ltoto (pass: esmeralda26) -> Lourdes Toto (gestor_cass)

INSERT INTO sullair_users (id, email, name, role, password_hash, assigned_vehicle_id)
VALUES
    ('u-fcendra', 'fcendra@sullair.com.ar', 'Federico Cendra', 'admin', '$2b$12$4fSUwDiWI3aqF2p1eLZ12eTnDBSp8TJKW1ACilXUDQPquSr70lLIe', NULL),
    ('u-ltoto', 'ltoto@sullair.com.ar', 'Lourdes Toto', 'gestor_cass', '$2b$12$r8NVEwMxGvZm6jAZZR2Bbu1oqgXFF7Oz91p/ZRjcq1UXF9fPfo3jG', NULL)
ON CONFLICT (email) DO UPDATE SET 
    name = EXCLUDED.name,
    role = EXCLUDED.role,
    password_hash = EXCLUDED.password_hash,
    assigned_vehicle_id = EXCLUDED.assigned_vehicle_id;
