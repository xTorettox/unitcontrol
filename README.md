# Sullair Argentina - Control de Vehículos (FSSA 106 Rev. 06)

Sistema integral de gestión de inspecciones vehiculares mensuales para el equipo Comercial y auditoría del equipo CASS de **Sullair Argentina**.

---

## 🚀 Características Principales

1. **Checklist Mobile-First & Desktop**:
   - Acceso táctil optimizado para smartphones y tablets.
   - Selector intuitivo para `C` (Cumple), `NC` (No Cumple) y `NA` (No Aplica).
   - Botón de autocompletado rápido `✨ Marcar todos los ítems como 'C'`.
   - Adjunto de fotos de evidencia con estampa de agua automática para no conformidades (`NC`).
   - Firma digital táctil (dedo / mouse) o subida permanente de firma en PNG.

2. **Generador Oficial de PDF Idéntico**:
   - Reproducción de precisión milimétrica del formulario **FSSA 106 Rev. 06**.
   - Encabezado con logotipo de Sullair Argentina, metadatos, tabla de documentación (Tarjeta Verde, Manual, VTV y Seguro con fechas).
   - Cuadrícula completa de 2 columnas con todas las categorías de inspección y resaltado de no conformidades.
   - Cuadro de observaciones con referencias automáticas a fotos adjuntas.
   - Espacio de firmas: Realizó (inspector) y Firma del responsable de sitio / CASS.
   - Formato ajustado en **exactamente 1 página A4**.

3. **Panel y Dashboard Analítico para CASS / Flota**:
   - KPIs en tiempo real: Total de inspecciones, unidades pendientes en el mes actual, fallas detectadas y porcentaje de cobertura.
   - Alertas automáticas de vencimiento de VTV / RTO y pólizas de seguro (próximos 30 días o vencidos).
   - Ranking interactivo de fallas y no conformidades más frecuentes.
   - Gráfico de cumplimiento de flota.
   - Visualización de fotos de evidencia y firma/aprobación digital directa para CASS.

4. **Gestión y Roles de Usuario**:
   - **Administrador**: Control total, creación de usuarios con roles y gestión de flota.
   - **Gestor CASS**: Dashboard, monitoreo general, revisión y firma de reportes.
   - **Responsable de Flota**: Control de documentación, seguimiento y firma de sitio.
   - **Comercial / Inspector**: Carga rápida con datos precargados de su vehículo asignado e historial propio.

---

## 👥 Cuentas de Demostración Preconfiguradas

| **Administrador (Federico Cendra)** | `fcendra@sullair.com.ar` (`fcendra`) | `C4n1ch3r1426` | Todos los accesos |
| **Comercial (Lucas Toto)** | `ltoto@sullair.com.ar` (`ltoto`) | `esmeralda26` | INT-104 (Toyota Hilux) |
| **Comercial (Demo)** | `comercial@sullair.com.ar` | `comercial` | INT-104 (Toyota Hilux) |
| **Gestor CASS** | `cass@sullair.com.ar` | `cass` | General / Auditoría |
| **Responsable Flota** | `flota@sullair.com.ar` | `flota` | General / Flota |
| **Administrador (Demo)** | `admin@sullair.com.ar` | `admin` | Todos los accesos |

---

## 💻 Instrucciones de Ejecución

Para iniciar la aplicación localmente:

```bash
cd C:\Users\fcendra\.gemini\antigravity-ide\scratch\sullair_vehicle_control
python -m streamlit run app.py
```

La aplicación abrirá en `http://localhost:8501`.

---

## 🗄️ Base de Datos Supabase

El sistema cuenta con conexión nativa a Supabase y fallback local en SQLite.

Para habilitar las tablas en tu proyecto de Supabase:
1. Ingresá a [Supabase SQL Editor](https://supabase.com/dashboard/project/kgdbgjuezooecsobfwfy/sql).
2. Copiá y ejecutá el contenido del archivo `database/schema.sql`.
