# Sistema de Control e Inspección Vehicular (Fleet Vehicle Control)

Aplicación web integral para la gestión, registro y auditoría de inspecciones mensuales de flotas de vehículos corporativos, generación automatizada de reportes oficiales en formato PDF y despacho de notificaciones por correo electrónico.

---

## 🚀 Características Principales

1. **Checklist de Inspección Mobile-First & Desktop**:
   - Interfaz táctil optimizada para smartphones, tablets y equipos de escritorio.
   - Selector interactivo de tres estados: `C` (Cumple), `NC` (No Cumple) y `NA` (No Aplica).
   - Atajos de autocompletado y validación de ítems pendientes.
   - Carga de fotografías de evidencia con estampa de agua automática para No Conformidades (`NC`).
   - Firma digital táctil, carga de firmas en imagen o certificación digital con sello de seguridad.

2. **Generador Oficial de Reportes PDF**:
   - Generación precisa y profesional de hojas de inspección vehicular en **formato estándar A4**.
   - Tabla de documentación: VTV / RTO, Póliza de Seguro, Tarjeta Verde y Manual con fechas de vigencia.
   - Resumen estructurado a 2 columnas con todos los sistemas del vehículo inspeccionados.
   - Observaciones detalladas y galería de fotografías adjuntas con sus leyendas descriptivas.
   - Bloque de firmas para el inspector responsable y la auditoría de sitio.

3. **Dashboard y Analítica de Flota**:
   - Métricas y KPIs en tiempo real: Total de inspecciones, unidades pendientes en el período, no conformidades detectadas y porcentaje de cobertura.
   - Alertas preventivas de vencimiento de VTV / RTO y seguros vehiculares (vencidos o próximos a expirar).
   - Ranking de fallas recurrentes y análisis de estado general de la flota.
   - Módulo de auditoría con revisión y firma de reportes.

4. **Gestión de Roles y Permisos**:
   - **Administrador**: Control total del sistema, administración de usuarios, flota de vehículos y configuración de correo SMTP.
   - **Auditor / Gestor de Flota**: Acceso a analíticas, panel de control general, revisión y aprobación digital de reportes.
   - **Inspector / Conductor**: Carga ágil con autocompletado de la unidad asignada e historial propio de reportes.

5. **Notificaciones y Despacho Automatizado**:
   - Envío automático de resúmenes por correo electrónico a auditores, inspectores y listas de distribución.
   - Adjunto directo del reporte oficial PDF firmado.
   - Persistencia segura de configuraciones en base de datos en la nube.

---

## 🛠️ Tecnologías Utilizadas

- **Frontend & App Engine**: [Streamlit](https://streamlit.io/) (Python)
- **Generación de Documentos**: [ReportLab](https://www.reportlab.com/) & [PyMuPDF](https://pymupdf.readthedocs.io/)
- **Procesamiento de Imágenes**: [Pillow (PIL)](https://python-pillow.org/)
- **Base de Datos**: [Supabase](https://supabase.com/) (PostgreSQL) con fallback offline en [SQLite](https://www.sqlite.org/)
- **Seguridad**: Cifrado de credenciales con `bcrypt`

---

## 💻 Instalación y Ejecución Local

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/control-vehicular.git
cd control-vehicular
```

### 2. Crear y activar un entorno virtual (opcional pero recomendado)
```bash
python -m venv venv
# En Windows:
venv\Scripts\activate
# En Linux/macOS:
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno o Secrets
Podés configurar las credenciales en un archivo `.streamlit/secrets.toml` o en las variables de entorno:

```toml
# .streamlit/secrets.toml
[supabase]
url = "https://tu-proyecto.supabase.co"
key = "tu-supabase-anon-key"

[email]
smtp_server = "smtp.office365.com"
smtp_port = 587
smtp_user = "notificaciones@tu-dominio.com"
smtp_password = "tu_password_aqui"
smtp_from = "notificaciones@tu-dominio.com"
sender_name = "Control de Flota"
use_tls = true
```

### 5. Iniciar la aplicación
```bash
streamlit run app.py
```

La aplicación se ejecutará en `http://localhost:8501`.

---

## 🗄️ Esquema de Base de Datos

El sistema inicializa automáticamente una base de datos local SQLite si no se detecta conexión a Supabase. Para utilizar Supabase, ejecute el script SQL incluido en `database/schema.sql` desde el Editor SQL de su proyecto.

---

## 📄 Licencia

Distribuido bajo la Licencia MIT. Consulte `LICENSE` para más información.
