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

# Configuración oficial de Supabase
DEFAULT_SUPABASE_URL = "https://kgdbgjuezooecsobfwfy.supabase.co"
DEFAULT_SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtnZGJnanVlem9vZWNzb2Jmd2Z5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODU3NjE2NjAsImV4cCI6MjEwMTMzNzY2MH0.sBop0Ktko7uH6phKvZ6P141wNYdbytyHeYl1t7OutCE"


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
        cursor.executescript("""
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
                tarjeta_verde BOOLEAN DEFAULT 1,
                manual BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS sullair_users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'comercial',
                password_hash TEXT NOT NULL,
                assigned_vehicle_id TEXT,
                signature_png TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS sullair_inspections (
                id TEXT PRIMARY KEY,
                fecha TEXT NOT NULL,
                mes_periodo TEXT NOT NULL,
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
                status TEXT DEFAULT 'pendiente_revision',
                nc_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS sullair_inspection_items (
                id TEXT PRIMARY KEY,
                inspection_id TEXT NOT NULL,
                section TEXT NOT NULL,
                item_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'C',
                has_photo BOOLEAN DEFAULT 0,
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
        """)
        conn.commit()
        conn.close()

    def _try_init_supabase(self):
        """Prueba la conexión a Supabase y verifica si las tablas sullair_ existen."""
        if SUPABASE_AVAILABLE and self.supabase_url and self.supabase_key:
            try:
                client = create_client(self.supabase_url, self.supabase_key)
                res = client.table("sullair_users").select("id").limit(1).execute()
                self.supabase_client = client
                self.use_supabase = True
                print("Conectado exitosamente a Supabase con tablas sullair_*.")
            except Exception as e:
                print(f"Aviso Supabase: {e}. Utilizando base de datos local SQLite para asegurar disponibilidad continua.")
                self.use_supabase = False

    def _hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify_password(self, password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return password == hashed

    def _seed_default_data(self):
        """Asegura únicamente las cuentas oficiales iniciales requeridas (clean slate)."""
        # 1. Limpiar usuarios y vehículos mock/demo antiguos de SQLite
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sullair_users WHERE email IN ('comercial@sullair.com.ar', 'cass@sullair.com.ar', 'flota@sullair.com.ar', 'admin@sullair.com.ar', 'test@sullair.com.ar')")
        conn.commit()
        conn.close()

        # 2. Asegurar las dos cuentas principales requeridas
        # - fcendra (admin, clave C4n1ch3r1426)
        # - ltoto (Lourdes Toto, gestor_cass, clave esmeralda26)
        user_seeds = [
            ("fcendra@sullair.com.ar", "Federico Cendra", "admin", "C4n1ch3r1426", None),
            ("ltoto@sullair.com.ar", "Lourdes Toto", "gestor_cass", "esmeralda26", None),
        ]

        for email, name, role, pwd, veh_id in user_seeds:
            existing = self.get_user_by_email(email)
            if not existing:
                self.create_user(email=email, name=name, role=role, password=pwd, assigned_vehicle_id=veh_id)
            else:
                if existing.get("role") != role or existing.get("name") != name:
                    self.update_user(existing["id"], {"name": name, "role": role, "password": pwd})

    # --- USUARIOS ---
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Busca un usuario por su nombre de usuario (ej: 'fcendra', 'ltoto') o por correo."""
        if not username:
            return None
        clean_user = username.strip().lower()
        if "@" in clean_user:
            clean_user = clean_user.split("@")[0]
        
        email_pattern = f"{clean_user}@sullair.com.ar"
        
        # 1. Intentar en Supabase
        if self.use_supabase and self.supabase_client:
            try:
                res = self.supabase_client.table("sullair_users").select("*").or_(f"email.eq.{email_pattern},email.ilike.{clean_user}@%").execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
            except Exception as e:
                print(f"Supabase get_user_by_username fallback: {e}")

        # 2. Fallback local SQLite
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sullair_users WHERE LOWER(email) = ? OR LOWER(email) LIKE ?", (email_pattern, f"{clean_user}@%"))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_user_by_email(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Busca un usuario por correo electrónico exacto o por nombre de usuario."""
        return self.get_user_by_username(identifier)

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        if self.use_supabase and self.supabase_client:
            try:
                res = self.supabase_client.table("sullair_users").select("*").eq("id", user_id).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
            except Exception as e:
                print(f"Supabase get_user_by_id fallback: {e}")

        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sullair_users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_users(self) -> List[Dict[str, Any]]:
        if self.use_supabase and self.supabase_client:
            try:
                res = self.supabase_client.table("sullair_users").select("*").order("name").execute()
                if res.data:
                    return res.data
            except Exception as e:
                print(f"Supabase get_all_users fallback: {e}")

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
        clean_email = email.strip().lower()
        clean_name = name.strip()

        # Guardar en Supabase
        if self.use_supabase and self.supabase_client:
            try:
                self.supabase_client.table("sullair_users").insert({
                    "id": user_id,
                    "email": clean_email,
                    "name": clean_name,
                    "role": role,
                    "password_hash": pwd_hash,
                    "assigned_vehicle_id": assigned_vehicle_id
                }).execute()
            except Exception as e:
                print(f"Supabase create_user error: {e}")

        # Guardar en SQLite local
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO sullair_users (id, email, name, role, password_hash, assigned_vehicle_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, clean_email, clean_name, role, pwd_hash, assigned_vehicle_id))
        conn.commit()
        conn.close()
        return user_id

    def update_user(self, user_id: str, data: Dict[str, Any]) -> bool:
        update_payload = {}
        fields = []
        values = []
        for k, v in data.items():
            if k == "password" and v:
                h = self._hash_password(v)
                update_payload["password_hash"] = h
                fields.append("password_hash = ?")
                values.append(h)
            elif k in ["name", "email", "role", "assigned_vehicle_id", "signature_png"]:
                update_payload[k] = v
                fields.append(f"{k} = ?")
                values.append(v)
        if not update_payload:
            return False

        # Actualizar en Supabase
        if self.use_supabase and self.supabase_client:
            try:
                self.supabase_client.table("sullair_users").update(update_payload).eq("id", user_id).execute()
            except Exception as e:
                print(f"Supabase update_user error: {e}")

        # Actualizar en SQLite
        values.append(user_id)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(f"UPDATE sullair_users SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
        conn.close()
        return True

    def delete_user(self, user_id: str) -> bool:
        if self.use_supabase and self.supabase_client:
            try:
                self.supabase_client.table("sullair_users").delete().eq("id", user_id).execute()
            except Exception as e:
                print(f"Supabase delete_user error: {e}")

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sullair_users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True

    # --- VEHÍCULOS ---
    def get_vehicles(self) -> List[Dict[str, Any]]:
        if self.use_supabase and self.supabase_client:
            try:
                res = self.supabase_client.table("sullair_vehicles").select("*").order("interno").execute()
                if res.data and len(res.data) > 0:
                    return res.data
            except Exception as e:
                print(f"Supabase get_vehicles fallback: {e}")

        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sullair_vehicles ORDER BY interno ASC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_vehicle_by_id(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        if self.use_supabase and self.supabase_client:
            try:
                res = self.supabase_client.table("sullair_vehicles").select("*").eq("id", vehicle_id).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
            except Exception as e:
                print(f"Supabase get_vehicle_by_id fallback: {e}")

        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sullair_vehicles WHERE id = ?", (vehicle_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def create_vehicle(self, data: Dict[str, Any]) -> str:
        v_id = str(uuid.uuid4())
        clean_interno = data.get("interno", "").strip()
        clean_patente = data.get("patente", "").strip().upper()
        clean_marca = data.get("marca", "").strip()
        clean_modelo = data.get("modelo", "").strip()
        km_val = int(data.get("km_actual", 0))
        vtv_val = data.get("vtv_vencimiento", "")
        seg_val = data.get("seguro_vencimiento", "")
        poliza_val = data.get("seguro_poliza", "")
        tarjeta_v = True if data.get("tarjeta_verde", True) else False
        manual_v = True if data.get("manual", True) else False

        # Guardar en Supabase
        if self.use_supabase and self.supabase_client:
            try:
                self.supabase_client.table("sullair_vehicles").insert({
                    "id": v_id,
                    "interno": clean_interno,
                    "patente": clean_patente,
                    "marca": clean_marca,
                    "modelo": clean_modelo,
                    "km_actual": km_val,
                    "vtv_vencimiento": vtv_val,
                    "seguro_vencimiento": seg_val,
                    "seguro_poliza": poliza_val,
                    "tarjeta_verde": tarjeta_v,
                    "manual": manual_v
                }).execute()
            except Exception as e:
                print(f"Supabase create_vehicle error: {e}")

        # Guardar en SQLite local
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO sullair_vehicles (id, interno, patente, marca, modelo, km_actual, vtv_vencimiento, seguro_vencimiento, seguro_poliza, tarjeta_verde, manual)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (v_id, clean_interno, clean_patente, clean_marca, clean_modelo, km_val, vtv_val, seg_val, poliza_val, 1 if tarjeta_v else 0, 1 if manual_v else 0))
        conn.commit()
        conn.close()
        return v_id

    def update_vehicle(self, vehicle_id: str, data: Dict[str, Any]) -> bool:
        update_payload = {}
        fields = []
        values = []
        for k in ["interno", "patente", "marca", "modelo", "km_actual", "vtv_vencimiento", "seguro_vencimiento", "seguro_poliza", "tarjeta_verde", "manual"]:
            if k in data:
                val = data[k]
                if k in ["tarjeta_verde", "manual"]:
                    val_bool = bool(val)
                    val_int = 1 if val else 0
                    update_payload[k] = val_bool
                    fields.append(f"{k} = ?")
                    values.append(val_int)
                elif k == "km_actual":
                    v_km = int(val or 0)
                    update_payload[k] = v_km
                    fields.append(f"{k} = ?")
                    values.append(v_km)
                else:
                    update_payload[k] = val
                    fields.append(f"{k} = ?")
                    values.append(val)
        if not update_payload:
            return False

        if self.use_supabase and self.supabase_client:
            try:
                self.supabase_client.table("sullair_vehicles").update(update_payload).eq("id", vehicle_id).execute()
            except Exception as e:
                print(f"Supabase update_vehicle error: {e}")

        values.append(vehicle_id)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(f"UPDATE sullair_vehicles SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
        conn.close()
        return True

    def delete_vehicle(self, vehicle_id: str) -> bool:
        if self.use_supabase and self.supabase_client:
            try:
                self.supabase_client.table("sullair_vehicles").delete().eq("id", vehicle_id).execute()
            except Exception as e:
                print(f"Supabase delete_vehicle error: {e}")

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sullair_vehicles WHERE id = ?", (vehicle_id,))
        conn.commit()
        conn.close()
        return True

    # --- INSPECCIONES ---
    def save_inspection(self, data: Dict[str, Any], items: List[Dict[str, Any]], photos: List[Dict[str, Any]] = None) -> str:
        insp_id = str(uuid.uuid4())
        nc_count = sum(1 for it in items if it.get("status") == "NC")
        status = "observado" if nc_count > 0 else "pendiente_revision"

        insp_record = {
            "id": insp_id,
            "fecha": data.get("fecha", datetime.now().strftime("%Y-%m-%d")),
            "mes_periodo": data.get("mes_periodo", datetime.now().strftime("%Y-%m")),
            "user_id": data.get("user_id", ""),
            "user_name": data.get("user_name", ""),
            "vehicle_id": data.get("vehicle_id", ""),
            "interno": data.get("interno", ""),
            "patente": data.get("patente", ""),
            "marca": data.get("marca", ""),
            "modelo": data.get("modelo", ""),
            "km": int(data.get("km", 0)),
            "tarjeta_verde_si_no": data.get("tarjeta_verde_si_no", "SI"),
            "manual_si_no": data.get("manual_si_no", "SI"),
            "vtv_si_no": data.get("vtv_si_no", "SI"),
            "vtv_vencimiento": data.get("vtv_vencimiento", ""),
            "seguro_si_no": data.get("seguro_si_no", "SI"),
            "seguro_vencimiento": data.get("seguro_vencimiento", ""),
            "observaciones": data.get("observaciones", ""),
            "realizo_nombre": data.get("realizo_nombre", ""),
            "realizo_firma_png": data.get("realizo_firma_png", ""),
            "responsable_sitio_nombre": data.get("responsable_sitio_nombre", ""),
            "responsable_sitio_firma_png": data.get("responsable_sitio_firma_png", ""),
            "status": status,
            "nc_count": nc_count
        }

        items_records = []
        for it in items:
            items_records.append({
                "id": str(uuid.uuid4()),
                "inspection_id": insp_id,
                "section": it.get("section", ""),
                "item_name": it.get("item_name", ""),
                "status": it.get("status", "C"),
                "has_photo": bool(it.get("has_photo")),
                "observation": it.get("observation", "")
            })

        photos_records = []
        if photos:
            for p in photos:
                photos_records.append({
                    "id": str(uuid.uuid4()),
                    "inspection_id": insp_id,
                    "item_name": p.get("item_name", ""),
                    "file_name": p.get("file_name", ""),
                    "image_base64": p.get("image_base64", ""),
                    "caption": p.get("caption", "")
                })

        # 1. Guardar en Supabase
        if self.use_supabase and self.supabase_client:
            try:
                self.supabase_client.table("sullair_inspections").insert(insp_record).execute()
                if items_records:
                    self.supabase_client.table("sullair_inspection_items").insert(items_records).execute()
                if photos_records:
                    self.supabase_client.table("sullair_inspection_photos").insert(photos_records).execute()
                if data.get("vehicle_id") and data.get("km"):
                    self.supabase_client.table("sullair_vehicles").update({"km_actual": int(data["km"])}).eq("id", data["vehicle_id"]).execute()
            except Exception as e:
                print(f"Supabase save_inspection error: {e}")

        # 2. Guardar en SQLite local
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
        """, tuple(insp_record.values()))

        for it in items_records:
            cursor.execute("""
                INSERT INTO sullair_inspection_items (id, inspection_id, section, item_name, status, has_photo, observation)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (it["id"], it["inspection_id"], it["section"], it["item_name"], it["status"], 1 if it["has_photo"] else 0, it["observation"]))

        for p in photos_records:
            cursor.execute("""
                INSERT INTO sullair_inspection_photos (id, inspection_id, item_name, file_name, image_base64, caption)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (p["id"], p["inspection_id"], p["item_name"], p["file_name"], p["image_base64"], p["caption"]))

        if data.get("vehicle_id") and data.get("km"):
            cursor.execute("UPDATE sullair_vehicles SET km_actual = ? WHERE id = ?", (int(data["km"]), data["vehicle_id"]))

        conn.commit()
        conn.close()
        return insp_id

    def get_inspections(self, user_id: Optional[str] = None, mes_periodo: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.use_supabase and self.supabase_client:
            try:
                query = self.supabase_client.table("sullair_inspections").select("*")
                if user_id:
                    query = query.eq("user_id", user_id)
                if mes_periodo:
                    query = query.eq("mes_periodo", mes_periodo)
                if search:
                    query = query.or_(f"patente.ilike.%{search}%,interno.ilike.%{search}%,user_name.ilike.%{search}%")
                res = query.order("fecha", desc=True).order("created_at", desc=True).execute()
                if res.data is not None:
                    return res.data
            except Exception as e:
                print(f"Supabase get_inspections fallback: {e}")

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
        if self.use_supabase and self.supabase_client:
            try:
                res = self.supabase_client.table("sullair_inspections").select("*").eq("id", inspection_id).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
            except Exception as e:
                print(f"Supabase get_inspection_by_id fallback: {e}")

        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sullair_inspections WHERE id = ?", (inspection_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_inspection_items(self, inspection_id: str) -> List[Dict[str, Any]]:
        if self.use_supabase and self.supabase_client:
            try:
                res = self.supabase_client.table("sullair_inspection_items").select("*").eq("inspection_id", inspection_id).execute()
                if res.data:
                    return res.data
            except Exception as e:
                print(f"Supabase get_inspection_items fallback: {e}")

        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sullair_inspection_items WHERE inspection_id = ?", (inspection_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_inspection_photos(self, inspection_id: str) -> List[Dict[str, Any]]:
        if self.use_supabase and self.supabase_client:
            try:
                res = self.supabase_client.table("sullair_inspection_photos").select("*").eq("inspection_id", inspection_id).execute()
                if res.data:
                    return res.data
            except Exception as e:
                print(f"Supabase get_inspection_photos fallback: {e}")

        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sullair_inspection_photos WHERE inspection_id = ?", (inspection_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def sign_as_responsible(self, inspection_id: str, responsible_name: str, signature_png: str) -> bool:
        if self.use_supabase and self.supabase_client:
            try:
                self.supabase_client.table("sullair_inspections").update({
                    "responsable_sitio_nombre": responsible_name,
                    "responsable_sitio_firma_png": signature_png,
                    "status": "aprobado"
                }).eq("id", inspection_id).execute()
            except Exception as e:
                print(f"Supabase sign_as_responsible error: {e}")

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
