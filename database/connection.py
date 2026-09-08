import os
import json
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import bcrypt

# Intentar importar Supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

DB_FILE = os.path.join(os.path.dirname(__file__), "sullair_local.db")
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schema.sql")

# Configuración por defecto de Supabase (proporcionada por el usuario)
DEFAULT_SUPABASE_URL = "https://kgdbgjuezooecsobfwfy.supabase.co"
DEFAULT_SUPABASE_KEY = "sb_publishable_zkq6DM_FialXcxIi78Jtkw_hnU_pneX"


class DatabaseManager:
    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        self.supabase_url = supabase_url or os.environ.get("SUPABASE_URL", DEFAULT_SUPABASE_URL)
        self.supabase_key = supabase_key or os.environ.get("SUPABASE_KEY", DEFAULT_SUPABASE_KEY)
        self.supabase_client: Optional[Client] = None
        self.use_supabase = False
        
        self._init_sqlite()
        self._try_init_supabase()
        self._seed_default_data()

    def _init_sqlite(self):
        """Inicializa la base de datos local SQLite con el esquema definido."""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        if os.path.exists(SCHEMA_FILE):
            with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
                cursor.executescript(f.read())
        conn.commit()
        conn.close()

    def _try_init_supabase(self):
        """Prueba la conexión a Supabase y verifica si las tablas sullair_ existen."""
        if SUPABASE_AVAILABLE and self.supabase_url and self.supabase_key:
            try:
                client = create_client(self.supabase_url, self.supabase_key)
                # Test query on sullair_users
                res = client.table("sullair_users").select("id").limit(1).execute()
                self.supabase_client = client
                self.use_supabase = True
                print("Conectado exitosamente a Supabase con tablas sullair_*.")
            except Exception as e:
                # Si las tablas no existen en Supabase aún o falla la autenticación de API, usamos SQLite local
                print(f"Aviso Supabase: {e}. Utilizando base de datos local SQLite para asegurar disponibilidad continua.")
                self.use_supabase = False

    def _hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify_password(self, password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return password == hashed  # Fallback si no está hasheada

    def _seed_default_data(self):
        """Crea usuarios y vehículos iniciales de prueba si la base está vacía."""
        users = self.get_all_users()
        if not users:
            # 1. Admin
            self.create_user(
                email="admin@sullair.com.ar",
                name="Administrador General",
                role="admin",
                password="admin",
                assigned_vehicle_id=None
            )
            # 2. Gestor CASS
            self.create_user(
                email="cass@sullair.com.ar",
                name="Equipo CASS - Control",
                role="gestor_cass",
                password="cass",
                assigned_vehicle_id=None
            )
            # 3. Responsable Flota
            self.create_user(
                email="flota@sullair.com.ar",
                name="Responsable de Flota",
                role="responsable_flota",
                password="flota",
                assigned_vehicle_id=None
            )

        vehicles = self.get_vehicles()
        if not vehicles:
            # Sembrar vehículos de ejemplo Sullair
            v1_id = self.create_vehicle({
                "interno": "INT-104",
                "patente": "AE 452 CD",
                "marca": "Toyota",
                "modelo": "Hilux 4x4 D/C",
                "km_actual": 48250,
                "vtv_vencimiento": "2026-11-15",
                "seguro_vencimiento": "2026-10-30",
                "seguro_poliza": "Allianz - Póliza #994821",
                "tarjeta_verde": True,
                "manual": True
            })
            v2_id = self.create_vehicle({
                "interno": "INT-108",
                "patente": "AF 892 KL",
                "marca": "Ford",
                "modelo": "Ranger XLS 3.2",
                "km_actual": 62100,
                "vtv_vencimiento": "2026-09-25", # Próximo a vencer
                "seguro_vencimiento": "2026-12-01",
                "seguro_poliza": "La Caja - Póliza #331902",
                "tarjeta_verde": True,
                "manual": True
            })
            v3_id = self.create_vehicle({
                "interno": "INT-112",
                "patente": "AD 311 ZZ",
                "marca": "Volkswagen",
                "modelo": "Amarok 2.0 TDI",
                "km_actual": 91500,
                "vtv_vencimiento": "2026-09-18", # Alerta vencimiento
                "seguro_vencimiento": "2026-09-28", # Alerta seguro
                "seguro_poliza": "Zurich - Póliza #772819",
                "tarjeta_verde": True,
                "manual": True
            })

            # Crear usuario comercial con vehículo asignado
            self.create_user(
                email="comercial@sullair.com.ar",
                name="Martín Rodríguez (Comercial)",
                role="comercial",
                password="comercial",
                assigned_vehicle_id=v1_id
            )
            self.create_user(
                email="lucas.gomez@sullair.com.ar",
                name="Lucas Gómez (Comercial)",
                role="comercial",
                password="lucas",
                assigned_vehicle_id=v2_id
            )

    # --- USUARIOS ---
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sullair_users WHERE LOWER(email) = LOWER(?)", (email.strip(),))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sullair_users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_users(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sullair_users ORDER BY name ASC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def create_user(self, email: str, name: str, role: str, password: str, assigned_vehicle_id: Optional[str] = None) -> str:
        user_id = str(uuid.uuid4())
        pwd_hash = self._hash_password(password)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sullair_users (id, email, name, role, password_hash, assigned_vehicle_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, email.strip().lower(), name.strip(), role, pwd_hash, assigned_vehicle_id))
        conn.commit()
        conn.close()
        return user_id

    def update_user(self, user_id: str, data: Dict[str, Any]) -> bool:
        fields = []
        values = []
        for k, v in data.items():
            if k == "password" and v:
                fields.append("password_hash = ?")
                values.append(self._hash_password(v))
            elif k in ["name", "email", "role", "assigned_vehicle_id", "signature_png"]:
                fields.append(f"{k} = ?")
                values.append(v)
        if not fields:
            return False
        values.append(user_id)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(f"UPDATE sullair_users SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
        conn.close()
        return True

    def delete_user(self, user_id: str) -> bool:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sullair_users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True

    # --- VEHÍCULOS ---
    def get_vehicles(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sullair_vehicles ORDER BY interno ASC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_vehicle_by_id(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sullair_vehicles WHERE id = ?", (vehicle_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def create_vehicle(self, data: Dict[str, Any]) -> str:
        v_id = str(uuid.uuid4())
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sullair_vehicles (id, interno, patente, marca, modelo, km_actual, vtv_vencimiento, seguro_vencimiento, seguro_poliza, tarjeta_verde, manual)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            v_id,
            data.get("interno", "").strip(),
            data.get("patente", "").strip().upper(),
            data.get("marca", "").strip(),
            data.get("modelo", "").strip(),
            int(data.get("km_actual", 0)),
            data.get("vtv_vencimiento", ""),
            data.get("seguro_vencimiento", ""),
            data.get("seguro_poliza", ""),
            1 if data.get("tarjeta_verde", True) else 0,
            1 if data.get("manual", True) else 0
        ))
        conn.commit()
        conn.close()
        return v_id

    def update_vehicle(self, vehicle_id: str, data: Dict[str, Any]) -> bool:
        fields = []
        values = []
        for k in ["interno", "patente", "marca", "modelo", "km_actual", "vtv_vencimiento", "seguro_vencimiento", "seguro_poliza", "tarjeta_verde", "manual"]:
            if k in data:
                fields.append(f"{k} = ?")
                val = data[k]
                if k in ["tarjeta_verde", "manual"]:
                    val = 1 if val else 0
                elif k == "km_actual":
                    val = int(val or 0)
                values.append(val)
        if not fields:
            return False
        values.append(vehicle_id)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(f"UPDATE sullair_vehicles SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
        conn.close()
        return True

    # --- INSPECCIONES ---
    def save_inspection(self, data: Dict[str, Any], items: List[Dict[str, Any]], photos: List[Dict[str, Any]] = None) -> str:
        insp_id = str(uuid.uuid4())
        nc_count = sum(1 for it in items if it.get("status") == "NC")
        status = "observado" if nc_count > 0 else "pendiente_revision"
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sullair_inspections (
                id, fecha, mes_periodo, user_id, user_name, vehicle_id,
                interno, patente, marca, modelo, km,
                tarjeta_verde_si_no, manual_si_no, vtv_si_no, vtv_vencimiento,
                seguro_si_no, seguro_vencimiento, observaciones,
                realizo_nombre, realizo_firma_png, responsable_sitio_nombre,
                responsable_sitio_firma_png, status, nc_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            insp_id,
            data.get("fecha", datetime.now().strftime("%Y-%m-%d")),
            data.get("mes_periodo", datetime.now().strftime("%Y-%m")),
            data.get("user_id", ""),
            data.get("user_name", ""),
            data.get("vehicle_id", ""),
            data.get("interno", ""),
            data.get("patente", ""),
            data.get("marca", ""),
            data.get("modelo", ""),
            int(data.get("km", 0)),
            data.get("tarjeta_verde_si_no", "SI"),
            data.get("manual_si_no", "SI"),
            data.get("vtv_si_no", "SI"),
            data.get("vtv_vencimiento", ""),
            data.get("seguro_si_no", "SI"),
            data.get("seguro_vencimiento", ""),
            data.get("observaciones", ""),
            data.get("realizo_nombre", ""),
            data.get("realizo_firma_png", ""),
            data.get("responsable_sitio_nombre", ""),
            data.get("responsable_sitio_firma_png", ""),
            status,
            nc_count
        ))

        # Insert items
        for it in items:
            it_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO sullair_inspection_items (id, inspection_id, section, item_name, status, has_photo, observation)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                it_id,
                insp_id,
                it.get("section", ""),
                it.get("item_name", ""),
                it.get("status", "C"),
                1 if it.get("has_photo") else 0,
                it.get("observation", "")
            ))

        # Insert photos
        if photos:
            for p in photos:
                p_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO sullair_inspection_photos (id, inspection_id, item_name, file_name, image_base64, caption)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    p_id,
                    insp_id,
                    p.get("item_name", ""),
                    p.get("file_name", ""),
                    p.get("image_base64", ""),
                    p.get("caption", "")
                ))

        # Actualizar kilometraje del vehículo si corresponde
        if data.get("vehicle_id") and data.get("km"):
            cursor.execute("UPDATE sullair_vehicles SET km_actual = ? WHERE id = ?", (int(data["km"]), data["vehicle_id"]))

        conn.commit()
        conn.close()
        return insp_id

    def get_inspections(self, user_id: Optional[str] = None, mes_periodo: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM sullair_inspections WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if mes_periodo:
            query += " AND mes_periodo = ?"
            params.append(mes_periodo)
        if search:
            query += " AND (patente LIKE ? OR interno LIKE ? OR user_name LIKE ?)"
            s_param = f"%{search}%"
            params.extend([s_param, s_param, s_param])
            
        query += " ORDER BY fecha DESC, created_at DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_inspection_by_id(self, inspection_id: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sullair_inspections WHERE id = ?", (inspection_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_inspection_items(self, inspection_id: str) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sullair_inspection_items WHERE inspection_id = ?", (inspection_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_inspection_photos(self, inspection_id: str) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sullair_inspection_photos WHERE inspection_id = ?", (inspection_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def sign_as_responsible(self, inspection_id: str, responsible_name: str, signature_png: str) -> bool:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sullair_inspections
            SET responsable_sitio_nombre = ?, responsable_sitio_firma_png = ?, status = 'aprobado'
            WHERE id = ?
        """, (responsible_name, signature_png, inspection_id))
        conn.commit()
        conn.close()
        return True


# Instancia singleton
_db_instance = None

def get_db() -> DatabaseManager:
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance
