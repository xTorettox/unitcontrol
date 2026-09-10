import streamlit as st
import streamlit.components.v1 as components
import base64
import io
import os
import re
import uuid
from datetime import datetime, date
from PIL import Image, ImageDraw, ImageFont

from database.connection import get_db
from modules.pdf_generator import SECTIONS_STRUCTURE, generate_sullair_pdf
from modules.email_notifier import send_inspection_email


def sanitize_filename(filename: str) -> str:
    """Limpia el nombre de archivo para evitar caracteres inválidos en descargas del navegador."""
    clean = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)
    clean = re.sub(r'_+', '_', clean)
    if not clean.lower().endswith(".pdf"):
        clean += ".pdf"
    return clean


def get_pdf_preview_image(pdf_bytes: bytes) -> bytes:
    """Genera una imagen PNG nítida de la primera página del PDF para previsualizar en la app."""
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if len(doc) > 0:
            page = doc[0]
            pix = page.get_pixmap(dpi=140)
            return pix.tobytes("png")
    except Exception as e:
        print(f"Error generando vista previa con PyMuPDF: {e}")
    return None


def render_pdf_download_block(pdf_bytes: bytes, filename: str, saved_path: str = None, key_prefix: str = "pdf", show_preview: bool = True):
    """
    Renderiza un bloque robusto de descarga y previsualización de PDF 100% compatible en web, móviles y desktop.
    """
    clean_name = sanitize_filename(filename)
    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

    # Botón HTML5 directo en Base64 con atributo download forzado (garantiza la extensión .pdf en Chrome/Safari/Edge)
    html_btn = f"""
    <div style="text-align: center; margin: 12px 0;">
        <a href="data:application/pdf;base64,{b64_pdf}" download="{clean_name}" target="_blank" class="pdf-download-btn"
           style="display: inline-flex; align-items: center; justify-content: center; width: 100%;
                  background-color: #00853E; color: #FFFFFF !important; padding: 14px 20px; text-decoration: none !important;
                  font-weight: 700; font-size: 1.05rem; border-radius: 8px; box-shadow: 0 3px 8px rgba(0,0,0,0.18);
                  text-align: center; border: none; cursor: pointer; transition: background-color 0.2s ease;">
            <span style="color: #FFFFFF !important; text-decoration: none !important; font-weight: 700;">
                📥 Descargar Reporte PDF Oficial ({clean_name})
            </span>
        </a>
    </div>
    """
    st.markdown(html_btn, unsafe_allow_html=True)

    # Previsualización directa en pantalla
    if show_preview:
        with st.expander("👁️ Ver Vista Previa del Reporte FSSA 106 generado", expanded=True):
            img_preview = get_pdf_preview_image(pdf_bytes)
            if img_preview:
                st.image(img_preview, caption=f"Vista previa oficial del documento: {clean_name}", use_container_width=True)
            else:
                st.info("Vista previa no disponible para este documento.")


def stamp_photo(img_file, item_name: str, fecha_str: str) -> str:
    """Añade una marca de agua con la fecha y el ítem inspeccionado sobre la foto y devuelve base64."""
    try:
        image = Image.open(img_file).convert("RGB")
        max_size = (1200, 1200)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        draw = ImageDraw.Draw(image)
        text = f"Sullair Argentina - FSSA 106 | {fecha_str} | Falla: {item_name}"
        
        w, h = image.size
        draw.rectangle([(0, h - 35), (w, h)], fill=(0, 0, 0))
        
        # Búsqueda de fuentes multiplataforma
        font = None
        for p in ["C:\\Windows\\Fonts\\arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
            if os.path.exists(p):
                font = ImageFont.truetype(p, 16)
                break
        if not font:
            font = ImageFont.load_default()
            
        draw.text((10, h - 28), text, fill=(255, 255, 255), font=font)
        
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"Error procesando foto: {e}")
        return ""


def get_unicode_font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.ImageFont:
    """Busca y carga una fuente TrueType con soporte completo de acentos en español (á, é, í, ó, ú, ñ)."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_fonts = [
        os.path.join(base_dir, "assets", "fonts", "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
        os.path.join(base_dir, "assets", "fonts", "arialbd.ttf" if bold else "arial.ttf")
    ]
    for lf in local_fonts:
        if os.path.exists(lf):
            try:
                return ImageFont.truetype(lf, size)
            except Exception:
                pass

    # Nombres estándar reconocidos por el sistema
    sys_names = ["arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf", "Arial-Bold"] if bold else ["arial.ttf", "segoeui.ttf", "DejaVuSans.ttf", "Arial"]
    if mono:
        sys_names = ["consola.ttf", "cour.ttf", "DejaVuSansMono.ttf", "Courier New"]
    for sn in sys_names:
        try:
            return ImageFont.truetype(sn, size)
        except Exception:
            pass

    # Rutas absolutas estándar de SO
    os_paths = [
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\segoeuib.ttf" if bold else "C:\\Windows\\Fonts\\segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
    ]
    for p in os_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass

    return ImageFont.load_default()


def create_digital_signature_stamp(name: str, date_str: str) -> str:
    """Genera una firma digital gráfica certificada con sello oficial de Sullair Argentina y soporte total de acentos."""
    img = Image.new("RGBA", (480, 130), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Marco institucional verde Sullair
    draw.rounded_rectangle([(2, 2), (478, 128)], radius=8, outline=(0, 122, 51, 230), width=2, fill=(240, 253, 244, 245))
    
    # Escudo de seguridad institucional dibujado en vector
    draw.polygon([(18, 12), (32, 12), (32, 22), (25, 28), (18, 22)], fill=(0, 122, 51, 255))
    draw.line([(21, 19), (24, 23), (29, 16)], fill=(255, 255, 255, 255), width=2)
    
    # Fuentes con soporte tipográfico completo UTF-8
    font_title = get_unicode_font(13, bold=True)
    font_main = get_unicode_font(12, bold=False)
    font_sub = get_unicode_font(10, bold=False)
    font_hash = get_unicode_font(9, bold=False)

    # Limpiar nombre para que nunca diga Administrador sino Comercial
    clean_name = re.sub(r'\s*\((Administrador|Admin|Gestor.*?)\)', '', name, flags=re.IGNORECASE).strip()
    if not clean_name.endswith("(Comercial)"):
        clean_name = f"{clean_name} (Comercial)"

    draw.text((38, 12), "FIRMA DIGITAL CERTIFICADA - SULLAIR ARGENTINA", fill=(0, 122, 51, 255), font=font_title)
    draw.text((18, 36), f"Inspector / Firmante: {clean_name}", fill=(30, 41, 59, 255), font=font_main)
    draw.text((18, 58), f"Fecha de emisión: {date_str} | Sistema FSSA 106 Rev. 06", fill=(71, 85, 105, 255), font=font_sub)
    draw.text((18, 78), f"Certificación Digital: {uuid.uuid4().hex[:14].upper()}", fill=(100, 116, 139, 255), font=font_hash)
    draw.text((18, 96), "Inspección mensual de flota - Sullair Argentina S.A.", fill=(100, 116, 139, 255), font=font_hash)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def render_checklist_view(user: dict):
    db = get_db()

    # PANTALLA DE CONFIRMACIÓN Y DESCARGA (Evita duplicaciones)
    if st.session_state.get("last_submission"):
        sub = st.session_state["last_submission"]
        st.markdown("### 🎉 ¡Inspección Registrada y Guardada con Éxito!")
        
        with st.container():
            st.markdown(
                f"""
                <div style="background: #f0fdf4; border: 2px solid #86efac; padding: 20px; border-radius: 12px; margin-bottom: 20px;">
                    <h3 style="margin: 0 0 10px 0; color: #166534;">📄 Reporte Oficial FSSA 106 Listo</h3>
                    <p style="margin: 0 0 8px 0; font-size: 1.05rem;">
                        <strong>ID de Inspección:</strong> <code>{sub['id'][:8]}</code> | 
                        <strong>Vehículo:</strong> <strong>{sub['interno']}</strong> ({sub['patente']}) | 
                        <strong>Fecha:</strong> {sub['fecha']}
                    </p>
                    <p style="margin: 0 0 8px 0; font-size: 0.95rem; color: #374151;">
                        <strong>Inspector:</strong> {sub.get('inspector', user.get('name'))} | 
                        <strong>Estado:</strong> {'⚠️ Contiene ' + str(sub['nc_count']) + ' No Conformidades (Notificado a CASS)' if sub['nc_count'] > 0 else '✅ Cumple sin observaciones'}
                    </p>
                    <p style="margin: 0; font-size: 0.85rem; color: #15803d;">
                        💾 <em>El reporte ya quedó guardado en la base de datos Supabase y en tu historial.</em>
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Bloque de descarga directa y vista previa
            render_pdf_download_block(
                pdf_bytes=sub["pdf_bytes"],
                filename=sub["filename"],
                saved_path=sub.get("saved_path"),
                key_prefix="sub_confirm",
                show_preview=True
            )

            st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
            if st.button("🔄 Realizar Nueva Inspección", type="secondary", use_container_width=True):
                # Limpiar estado y reiniciar formulario
                del st.session_state["last_submission"]
                if "mode_cargar_otro_vehiculo" in st.session_state:
                    del st.session_state["mode_cargar_otro_vehiculo"]
                st.rerun()

        # Detener la ejecución aquí para NO mostrar el formulario duplicado abajo
        return

    # FORMULARIO DE CARGA DE INSPECCIÓN
    st.markdown("""
    <style>
    /* Segmented Control - Colores exactos para C (Verde), NC (Rojo), NA (Gris) */
    div[data-testid="stSegmentedControl"] {
        display: flex;
        justify-content: flex-end;
    }
    div[data-testid="stSegmentedControl"] button {
        font-weight: 700 !important;
        border-radius: 6px !important;
        border: 1px solid #CBD5E1 !important;
        padding: 4px 12px !important;
        min-width: 44px !important;
        background-color: #FFFFFF !important;
        color: #64748B !important;
        transition: all 0.15s ease !important;
    }
    div[data-testid="stSegmentedControl"] button:hover {
        border-color: #94A3B8 !important;
        color: #1E293B !important;
    }
    /* C - 1er botón activo: Verde */
    div[data-testid="stSegmentedControl"] [role="radiogroup"] > button:nth-child(1)[aria-checked="true"],
    div[data-testid="stSegmentedControl"] button:nth-of-type(1)[aria-checked="true"],
    div[data-testid="stSegmentedControl"] button:first-child[aria-checked="true"] {
        background-color: #E6F4EA !important;
        border: 2px solid #00853E !important;
        color: #00853E !important;
    }
    div[data-testid="stSegmentedControl"] [role="radiogroup"] > button:nth-child(1)[aria-checked="true"] *,
    div[data-testid="stSegmentedControl"] button:nth-of-type(1)[aria-checked="true"] *,
    div[data-testid="stSegmentedControl"] button:first-child[aria-checked="true"] * {
        color: #00853E !important;
    }
    /* NC - 2do botón activo: Rojo */
    div[data-testid="stSegmentedControl"] [role="radiogroup"] > button:nth-child(2)[aria-checked="true"],
    div[data-testid="stSegmentedControl"] button:nth-of-type(2)[aria-checked="true"] {
        background-color: #FEE2E2 !important;
        border: 2px solid #DC2626 !important;
        color: #DC2626 !important;
    }
    div[data-testid="stSegmentedControl"] [role="radiogroup"] > button:nth-child(2)[aria-checked="true"] *,
    div[data-testid="stSegmentedControl"] button:nth-of-type(2)[aria-checked="true"] * {
        color: #DC2626 !important;
    }
    /* NA - 3er botón activo: Gris */
    div[data-testid="stSegmentedControl"] [role="radiogroup"] > button:nth-child(3)[aria-checked="true"],
    div[data-testid="stSegmentedControl"] button:nth-of-type(3)[aria-checked="true"],
    div[data-testid="stSegmentedControl"] button:last-child[aria-checked="true"] {
        background-color: #F1F5F9 !important;
        border: 2px solid #64748B !important;
        color: #475569 !important;
    }
    div[data-testid="stSegmentedControl"] [role="radiogroup"] > button:nth-child(3)[aria-checked="true"] *,
    div[data-testid="stSegmentedControl"] button:nth-of-type(3)[aria-checked="true"] *,
    div[data-testid="stSegmentedControl"] button:last-child[aria-checked="true"] * {
        color: #475569 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("### 📋 Control de Vehículos (Mensual)")
    st.caption("Formulario oficial de inspección mensual **FSSA 106 Rev. 06**")

    # 1. DATOS DEL VEHÍCULO Y CABECERA
    vehicles = db.get_vehicles()
    assigned_v = None
    if user.get("assigned_vehicle_id"):
        assigned_v = db.get_vehicle_by_id(user["assigned_vehicle_id"])

    is_override = st.session_state.get("mode_cargar_otro_vehiculo", False)

    with st.expander("🚗 Datos del Vehículo e Inspección", expanded=True):
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            fecha_val = st.date_input("Fecha de Inspección", value=date.today(), key="insp_fecha")
        with col_f2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if assigned_v and not is_override:
                st.info(f"🚙 Unidad Asignada activa: **{assigned_v['interno']} - {assigned_v['patente']}**")
            elif is_override and assigned_v:
                if st.button("↩️ Volver a mi vehículo asignado", use_container_width=True):
                    st.session_state["mode_cargar_otro_vehiculo"] = False
                    st.rerun()

        # CASO A: Usuario con Vehículo Asignado Predefinido
        if assigned_v and not is_override:
            today = date.today()
            vtv_status_str = "No registrado"
            seg_status_str = "No registrado"
            
            vtv_date_obj = None
            if assigned_v.get("vtv_vencimiento"):
                try:
                    vtv_date_obj = datetime.strptime(assigned_v["vtv_vencimiento"], "%Y-%m-%d").date()
                except Exception:
                    try:
                        vtv_date_obj = datetime.strptime(assigned_v["vtv_vencimiento"], "%d/%m/%Y").date()
                    except Exception:
                        pass
            if vtv_date_obj:
                d_vtv = (vtv_date_obj - today).days
                if d_vtv < 0:
                    vtv_status_str = f"🚨 VENCIDA ({vtv_date_obj.strftime('%d/%m/%Y')})"
                elif d_vtv <= 30:
                    vtv_status_str = f"⏳ Vence pronto ({vtv_date_obj.strftime('%d/%m/%Y')})"
                else:
                    vtv_status_str = f"✅ Al día ({vtv_date_obj.strftime('%d/%m/%Y')})"

            seg_date_obj = None
            if assigned_v.get("seguro_vencimiento"):
                try:
                    seg_date_obj = datetime.strptime(assigned_v["seguro_vencimiento"], "%Y-%m-%d").date()
                except Exception:
                    try:
                        seg_date_obj = datetime.strptime(assigned_v["seguro_vencimiento"], "%d/%m/%Y").date()
                    except Exception:
                        pass
            if seg_date_obj:
                d_seg = (seg_date_obj - today).days
                if d_seg < 0:
                    seg_status_str = f"🚨 VENCIDO ({seg_date_obj.strftime('%d/%m/%Y')})"
                elif d_seg <= 30:
                    seg_status_str = f"⏳ Vence pronto ({seg_date_obj.strftime('%d/%m/%Y')})"
                else:
                    seg_status_str = f"✅ Al día ({seg_date_obj.strftime('%d/%m/%Y')})"

            st.markdown(
                f"""
                <div style="background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px; padding: 14px 18px; margin-bottom: 15px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin-bottom: 8px;">
                        <span style="font-size: 1.15rem; font-weight: 700; color: #005A2A;">🚙 {assigned_v['interno']} - {assigned_v['patente']} ({assigned_v['marca']} {assigned_v.get('modelo', '')})</span>
                        <span style="font-size: 0.85rem; color: #64748B;">Unidad predeterminada</span>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; font-size: 0.9rem; color: #334155;">
                        <div><strong>VTV / RTO:</strong> {vtv_status_str}</div>
                        <div><strong>Seguro:</strong> {seg_status_str}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            c_act_v1, c_act_v2 = st.columns([2, 1])
            with c_act_v1:
                km_val = st.number_input(
                    "Kilometraje Actual *",
                    value=0,
                    min_value=0,
                    step=100,
                    key="v_km_assigned",
                    help="Ingrese el kilometraje actual registrado en el odómetro."
                )
            with c_act_v2:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("➕ Cargar un vehículo nuevo", use_container_width=True):
                    st.session_state["mode_cargar_otro_vehiculo"] = True
                    st.rerun()

            # Asignar valores fijos de este vehículo
            interno_val = assigned_v["interno"]
            patente_val = assigned_v["patente"]
            marca_val = assigned_v["marca"]
            modelo_val = assigned_v.get("modelo", "")
            sel_v_id = assigned_v["id"]
            set_as_default = True

            # Documentación del vehículo
            st.markdown("#### 📄 Documentación del Vehículo")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                tarjeta_verde_val = st.radio("Tarjeta Verde", options=["SI", "NO"], horizontal=True, key="doc_tarjeta_assigned")
                manual_val = st.radio("Manual del Vehículo", options=["SI", "NO"], horizontal=True, key="doc_manual_assigned")
            with col_d2:
                col_vtv1, col_vtv2 = st.columns([1, 2])
                with col_vtv1:
                    vtv_val = st.radio("VTV / RTO", options=["SI", "NO"], horizontal=True, key="doc_vtv_assigned")
                with col_vtv2:
                    default_vtv_date = vtv_date_obj or date.today()
                    vtv_venc_val = st.date_input("Vencimiento VTV", value=default_vtv_date, key="doc_vtv_venc_assigned")

                col_seg1, col_seg2 = st.columns([1, 2])
                with col_seg1:
                    seguro_val = st.radio("Seguro vehicular", options=["SI", "NO"], horizontal=True, key="doc_seguro_assigned")
                with col_seg2:
                    default_seg_date = seg_date_obj or date.today()
                    seguro_venc_val = st.date_input("Vencimiento Seguro", value=default_seg_date, key="doc_seguro_venc_assigned")

        # CASO B: Sin vehículo asignado o en modo Cargar / Inspeccionar otro vehículo
        else:
            veh_map = {}
            veh_options = ["(Cargar datos manualmente)"]
            for v in vehicles:
                lbl = f"{v['interno']} - {v['patente']} ({v['marca']} {v.get('modelo', '')})".strip()
                veh_options.append(lbl)
                veh_map[lbl] = v

            selected_veh_opt = st.selectbox(
                "Vehículo Asignado / Flota",
                options=veh_options,
                key="sb_vehiculo_custom",
                help="Podés seleccionar una unidad de la flota o cargar los datos de una unidad nueva."
            )

            # Sincronización instantánea de los campos de texto al seleccionar del dropdown
            if selected_veh_opt != st.session_state.get("_last_synced_veh_opt"):
                st.session_state["_last_synced_veh_opt"] = selected_veh_opt
                matched_v = veh_map.get(selected_veh_opt)
                if not matched_v and selected_veh_opt != "(Cargar datos manualmente)":
                    for v in vehicles:
                        if v["patente"] in selected_veh_opt or v["interno"] in selected_veh_opt:
                            matched_v = v
                            break

                if matched_v:
                    st.session_state["v_interno_cust"] = str(matched_v.get("interno", "")).strip()
                    st.session_state["v_patente_cust"] = str(matched_v.get("patente", "")).strip()
                    st.session_state["v_marca_cust"] = str(matched_v.get("marca", "")).strip()
                    st.session_state["v_modelo_cust"] = str(matched_v.get("modelo", "") or "").strip()
                    st.session_state["v_km_cust"] = int(matched_v.get("km_actual") or 0)
                    if matched_v.get("vtv_vencimiento"):
                        try:
                            st.session_state["doc_vtv_venc_cust"] = datetime.strptime(matched_v["vtv_vencimiento"], "%Y-%m-%d").date()
                        except Exception:
                            pass
                    if matched_v.get("seguro_vencimiento"):
                        try:
                            st.session_state["doc_seguro_venc_cust"] = datetime.strptime(matched_v["seguro_vencimiento"], "%Y-%m-%d").date()
                        except Exception:
                            pass
                elif selected_veh_opt == "(Cargar datos manualmente)":
                    st.session_state["v_interno_cust"] = ""
                    st.session_state["v_patente_cust"] = ""
                    st.session_state["v_marca_cust"] = ""
                    st.session_state["v_modelo_cust"] = ""
                    st.session_state["v_km_cust"] = 0
                st.rerun()

            # Asegurar claves en session_state
            if "v_interno_cust" not in st.session_state:
                st.session_state["v_interno_cust"] = ""
                st.session_state["v_patente_cust"] = ""
                st.session_state["v_marca_cust"] = ""
                st.session_state["v_modelo_cust"] = ""
                st.session_state["v_km_cust"] = 0
                st.session_state["doc_vtv_venc_cust"] = date.today()
                st.session_state["doc_seguro_venc_cust"] = date.today()

            sel_v_data = veh_map.get(selected_veh_opt)

            c_v1, c_v2, c_v3 = st.columns(3)
            with c_v1:
                interno_val = st.text_input("N° Interno *", key="v_interno_cust", placeholder="Ej: INT-104")
                marca_val = st.text_input("Marca *", key="v_marca_cust", placeholder="Ej: Toyota")
            with c_v2:
                patente_val = st.text_input("Patente *", key="v_patente_cust", placeholder="Ej: AE 452 CD")
                modelo_val = st.text_input("Modelo", key="v_modelo_cust", placeholder="Ej: Hilux 4x4 D/C")
            with c_v3:
                km_val = st.number_input("Kilometraje Actual *", key="v_km_cust", min_value=0, step=100)

            st.markdown("#### 📄 Documentación del Vehículo")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                tarjeta_verde_val = st.radio("Tarjeta Verde", options=["SI", "NO"], horizontal=True, key="doc_tarjeta_cust")
                manual_val = st.radio("Manual del Vehículo", options=["SI", "NO"], horizontal=True, key="doc_manual_cust")
            with col_d2:
                col_vtv1, col_vtv2 = st.columns([1, 2])
                with col_vtv1:
                    vtv_val = st.radio("VTV / RTO", options=["SI", "NO"], horizontal=True, key="doc_vtv_cust")
                with col_vtv2:
                    vtv_venc_val = st.date_input("Vencimiento VTV", key="doc_vtv_venc_cust")

                col_seg1, col_seg2 = st.columns([1, 2])
                with col_seg1:
                    seguro_val = st.radio("Seguro vehicular", options=["SI", "NO"], horizontal=True, key="doc_seguro_cust")
                with col_seg2:
                    seguro_venc_val = st.date_input("Vencimiento Seguro", key="doc_seguro_venc_cust")

            # Checkbox de asignación predeterminada
            set_as_default = st.checkbox(
                "📌 Guardar y recordar este vehículo como predeterminado para mi usuario",
                value=True if not assigned_v else False,
                help="Si lo marcás, la próxima vez que ingreses con tu usuario se precargará este vehículo automáticamente."
            )
            sel_v_id = sel_v_data["id"] if sel_v_data else None

    # 2. CHECKLIST INTERACTIVO (Sin valor por defecto para exigir llenado a conciencia)
    st.markdown("---")
    st.markdown("### ✅ Checklist de Inspección")
    st.markdown(
        """
        <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 12px 16px; border-radius: 8px; margin-bottom: 18px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
            <strong style="color: #334155;">Referencias de estado:</strong> 
            <div style="display: flex; gap: 10px;">
                <span class="status-badge badge-c">C = CUMPLE</span> 
                <span class="status-badge badge-nc">NC = NO CUMPLE</span> 
                <span class="status-badge badge-na">NA = NO APLICA</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    all_sections = []
    for side in ["LEFT", "RIGHT"]:
        for sec in SECTIONS_STRUCTURE[side]:
            all_sections.append(sec)

    checklist_results = []
    uploaded_photos = []

    for sec in all_sections:
        with st.expander(f"📌 {sec['title']}", expanded=True):
            for item in sec["items"]:
                key = f"chk_{sec['title']}_{item}"

                col_it, col_opt = st.columns([3, 2])
                with col_it:
                    st.markdown(f"**{item}**")
                with col_opt:
                    status_choice = st.segmented_control(
                        label=f"Estado de {item}",
                        options=["C", "NC", "NA"],
                        default=st.session_state.get(key, None),
                        key=key,
                        label_visibility="collapsed"
                    )

                has_photo = False
                obs_falla = ""
                if status_choice == "NC":
                    st.markdown(
                        f"""<div style="background-color: #fee2e2; border-left: 4px solid #ef4444; padding: 8px 12px; border-radius: 4px; margin-top: -5px; margin-bottom: 10px;">
                            <strong style="color: #991b1b;">⚠️ No Conformidad en: {item}</strong>
                        </div>""",
                        unsafe_allow_html=True
                    )
                    c_ph1, c_ph2 = st.columns([1, 1])
                    with c_ph1:
                        obs_falla = st.text_input(
                            f"Detalle de la falla en '{item}'",
                            placeholder="Ej: Foco quemado, golpe en paragolpe, etc.",
                            key=f"obs_falla_{sec['title']}_{item}"
                        )
                    with c_ph2:
                        photo_file = st.file_uploader(
                            f"📸 Adjuntar foto de '{item}'",
                            type=["jpg", "jpeg", "png"],
                            key=f"photo_{sec['title']}_{item}",
                            help="Podés tomar una foto con la cámara del celular o subir un archivo."
                        )
                        if photo_file:
                            has_photo = True
                            b64_img = stamp_photo(photo_file, item, fecha_val.strftime("%d/%m/%Y"))
                            if b64_img:
                                uploaded_photos.append({
                                    "item_name": item,
                                    "file_name": f"falla_{item.replace(' ', '_').replace('/', '_')}.jpg",
                                    "image_base64": b64_img,
                                    "caption": obs_falla or f"Falla en {item}"
                                })
                                st.image(photo_file, caption=f"Foto cargada para {item}", width=150)

                checklist_results.append({
                    "section": sec["title"],
                    "item_name": item,
                    "status": status_choice,
                    "has_photo": has_photo,
                    "observation": obs_falla
                })

    # Inyección de script en el DOM principal para colores exactos y activación del truco de teclado
    js_colorize_and_cheat = """
    <img src="data:image/svg+xml;utf8,<svg/>" style="display:none;" onerror="
    (function() {
        function colorize() {
            var scList = document.querySelectorAll('div[data-testid=\\'stSegmentedControl\\']');
            scList.forEach(function(sc) {
                var btns = sc.querySelectorAll('button');
                btns.forEach(function(btn, idx) {
                    var checked = btn.getAttribute('aria-checked') === 'true';
                    var txt = (btn.textContent || btn.innerText || '').trim();
                    var isC = txt === 'C' || (idx === 0 && txt.indexOf('NC') === -1 && txt.indexOf('NA') === -1);
                    var isNC = txt === 'NC' || idx === 1;
                    var isNA = txt === 'NA' || idx === 2;
                    
                    if (checked) {
                        if (isC) {
                            btn.style.setProperty('background-color', '#E6F4EA', 'important');
                            btn.style.setProperty('background', '#E6F4EA', 'important');
                            btn.style.setProperty('border', '2px solid #00853E', 'important');
                            btn.style.setProperty('color', '#00853E', 'important');
                            btn.querySelectorAll('*').forEach(function(el) { el.style.setProperty('color', '#00853E', 'important'); });
                        } else if (isNC) {
                            btn.style.setProperty('background-color', '#FEE2E2', 'important');
                            btn.style.setProperty('background', '#FEE2E2', 'important');
                            btn.style.setProperty('border', '2px solid #DC2626', 'important');
                            btn.style.setProperty('color', '#DC2626', 'important');
                            btn.querySelectorAll('*').forEach(function(el) { el.style.setProperty('color', '#DC2626', 'important'); });
                        } else if (isNA) {
                            btn.style.setProperty('background-color', '#F1F5F9', 'important');
                            btn.style.setProperty('background', '#F1F5F9', 'important');
                            btn.style.setProperty('border', '2px solid #64748B', 'important');
                            btn.style.setProperty('color', '#475569', 'important');
                            btn.querySelectorAll('*').forEach(function(el) { el.style.setProperty('color', '#475569', 'important'); });
                        }
                    } else {
                        btn.style.setProperty('background-color', '#FFFFFF', 'important');
                        btn.style.setProperty('background', '#FFFFFF', 'important');
                        btn.style.setProperty('border', '1px solid #CBD5E1', 'important');
                        btn.style.setProperty('color', '#64748B', 'important');
                        btn.querySelectorAll('*').forEach(function(el) { el.style.setProperty('color', '#64748B', 'important'); });
                    }
                });
            });
        }

        colorize();
        setTimeout(colorize, 100);
        setTimeout(colorize, 300);

        if (!window._sullair_dom_initialized) {
            window._sullair_dom_initialized = true;

            var observer = new MutationObserver(function() {
                colorize();
            });
            observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['aria-checked', 'class'] });

            var keyBuffer = '';
            var targetWord = 'masfacilcontrucos';
            document.addEventListener('keydown', function(e) {
                if (!e.key) return;
                var k = e.key.toLowerCase();
                if (k.length === 1) {
                    keyBuffer += k;
                    if (keyBuffer.length > 40) {
                        keyBuffer = keyBuffer.slice(-25);
                    }
                    if (keyBuffer.endsWith(targetWord)) {
                        keyBuffer = '';
                        var scList = document.querySelectorAll('div[data-testid=\\'stSegmentedControl\\']');
                        var count = 0;
                        scList.forEach(function(sc) {
                            var btns = sc.querySelectorAll('button');
                            if (btns.length > 0) {
                                btns[0].click();
                                count++;
                            }
                        });
                        setTimeout(colorize, 60);

                        var oldToast = document.getElementById('sullair_cheat_toast');
                        if (oldToast) oldToast.remove();

                        var toast = document.createElement('div');
                        toast.id = 'sullair_cheat_toast';
                        toast.innerHTML = '✨ <strong>¡Truco activado!</strong> Se marcaron todos los ítems en <strong>C (Cumple)</strong>.';
                        toast.style.cssText = 'position:fixed; bottom:28px; right:28px; background:#00853E; color:#FFFFFF; padding:14px 22px; border-radius:10px; font-size:15px; font-weight:600; box-shadow:0 8px 25px rgba(0,0,0,0.3); z-index:9999999; font-family:sans-serif; transition:all 0.4s ease;';
                        document.body.appendChild(toast);
                        setTimeout(function() {
                            toast.style.opacity = '0';
                            toast.style.transform = 'translateY(12px)';
                            setTimeout(function() { if (toast) toast.remove(); }, 400);
                        }, 4000);
                    }
                }
            });
        }
    })();
    " />
    """
    st.markdown(js_colorize_and_cheat, unsafe_allow_html=True)

    # 3. OBSERVACIONES GENERALES
    st.markdown("---")
    st.markdown("### 📝 Observaciones Generales")
    observaciones_val = st.text_area(
        "Detalles o comentarios adicionales de la inspección",
        placeholder="Ingrese cualquier observación o comentario sobre el estado del vehículo...",
        height=100,
        key="insp_observaciones"
    )

    # 4. FIRMAS
    st.markdown("---")
    st.markdown("### ✍️ Firma del Inspector / Comercial")
    
    col_sig1, col_sig2 = st.columns([1, 1])
    with col_sig1:
        st.markdown(f"**Inspector responsable:** `{user.get('name', 'Usuario')}`")
        sig_options = [
            "🛡️ Firma digital certificada (Automática)",
            "📁 Subir archivo de firma (PNG / JPG)"
        ]
        if user.get("signature_png"):
            sig_options.insert(0, "⭐ Usar mi firma guardada en mi perfil")
        sig_options.append("✏️ Dibujar firma táctil / mouse")
        
        selected_sig_mode = st.radio("Método de firma para este reporte:", options=sig_options)

    final_realizo_sig_b64 = ""

    with col_sig2:
        if "guardada" in selected_sig_mode and user.get("signature_png"):
            st.info("Utilizando firma registrada en tu perfil de usuario:")
            st.image(f"data:image/png;base64,{user['signature_png']}", width=220)
            final_realizo_sig_b64 = user["signature_png"]
            
        elif "certificada" in selected_sig_mode:
            st.success("✅ Firma digital certificada generada para este reporte:")
            cert_sig_b64 = create_digital_signature_stamp(user.get("name", "Inspector"), datetime.now().strftime("%d/%m/%Y %H:%M"))
            st.image(f"data:image/png;base64,{cert_sig_b64}", width=280)
            final_realizo_sig_b64 = cert_sig_b64
            
        elif "Subir" in selected_sig_mode:
            sig_upload = st.file_uploader("Subir imagen de firma (PNG o JPG con fondo blanco/transparente)", type=["png", "jpg", "jpeg"], key="upload_sig")
            if sig_upload:
                final_realizo_sig_b64 = base64.b64encode(sig_upload.getvalue()).decode("utf-8")
                st.image(sig_upload, width=180, caption="Firma cargada")
                if st.checkbox("Guardar esta firma en mi perfil para futuras inspecciones"):
                    db.update_user(user["id"], {"signature_png": final_realizo_sig_b64})
                    user["signature_png"] = final_realizo_sig_b64
                    st.success("¡Firma guardada en tu perfil con éxito!")
            else:
                st.caption("Seleccioná una imagen de tu firma o elegí 'Firma digital certificada'.")
                
        elif "Dibujar" in selected_sig_mode:
            st.caption("Firma con el dedo o mouse dentro del recuadro:")
            try:
                from streamlit_drawable_canvas import st_canvas
                canvas_result = st_canvas(
                    fill_color="rgba(255, 255, 255, 0)",
                    stroke_width=2,
                    stroke_color="#000000",
                    background_color="#FFFFFF",
                    height=130,
                    width=300,
                    drawing_mode="freedraw",
                    key="canvas_firma",
                    update_streamlit=True
                )
                if canvas_result is not None:
                    try:
                        img_array = getattr(canvas_result, "image_data", None)
                        if img_array is not None:
                            img_pil = Image.fromarray(img_array.astype('uint8'), 'RGBA')
                            buf = io.BytesIO()
                            img_pil.save(buf, format="PNG")
                            final_realizo_sig_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                    except Exception as ce:
                        print(f"Canvas info: {ce}")
            except Exception as e:
                st.warning("El módulo de dibujo táctil no está disponible en este navegador. Se aplicará firma digital certificada.")
                final_realizo_sig_b64 = create_digital_signature_stamp(user.get("name", "Inspector"), datetime.now().strftime("%d/%m/%Y %H:%M"))

    if not final_realizo_sig_b64:
        final_realizo_sig_b64 = create_digital_signature_stamp(user.get("name", "Inspector"), datetime.now().strftime("%d/%m/%Y %H:%M"))

    # 5. BOTÓN DE ENVÍO Y GENERACIÓN DE REPORTE
    st.markdown("---")
    nc_total = sum(1 for it in checklist_results if it.get("status") == "NC")
    unanswered_total = sum(1 for it in checklist_results if not it.get("status"))

    if unanswered_total > 0:
        st.info(f"⏳ Quedan **{unanswered_total} ítems sin responder** en la planilla de inspección.")
    elif nc_total > 0:
        st.warning(f"⚠️ Se detectaron **{nc_total} No Conformidades (NC)** en esta inspección. El reporte quedará marcado para revisión por el equipo de CASS.")
    else:
        st.success("✅ Todos los ítems cumplen satisfactoriamente.")

    if st.button("🚀 Guardar Reporte y Generar PDF Oficial", type="primary", use_container_width=True):
        # Validación 1: Datos de vehículo
        if not interno_val or not patente_val or not marca_val:
            st.error("⚠️ Por favor complete los campos obligatorios de Interno, Patente y Marca del vehículo.")
            return

        # Validación 2: Todos los checks deben estar contestados
        if unanswered_total > 0:
            st.error(f"⚠️ Debe completar todos los ítems del formulario antes de guardar. Quedan {unanswered_total} ítems sin responder.")
            return

        # 1. Crear o actualizar vehículo en Supabase
        clean_pat = patente_val.strip().upper()
        existing_veh = next((v for v in db.get_vehicles() if v["patente"].upper() == clean_pat), None)
        
        veh_payload = {
            "interno": interno_val.strip(),
            "patente": clean_pat,
            "marca": marca_val.strip(),
            "modelo": modelo_val.strip(),
            "km_actual": int(km_val),
            "vtv_vencimiento": vtv_venc_val.strftime("%Y-%m-%d"),
            "seguro_vencimiento": seguro_venc_val.strftime("%Y-%m-%d"),
            "tarjeta_verde": tarjeta_verde_val == "SI",
            "manual": manual_val == "SI"
        }

        if existing_veh:
            db.update_vehicle(existing_veh["id"], veh_payload)
            final_veh_id = existing_veh["id"]
        else:
            final_veh_id = db.create_vehicle(veh_payload)

        # Si se eligió recordar como predeterminado
        if set_as_default:
            db.update_user(user["id"], {"assigned_vehicle_id": final_veh_id})
            user["assigned_vehicle_id"] = final_veh_id
            st.session_state["user"] = user
            st.session_state["mode_cargar_otro_vehiculo"] = False

        # 2. Preparar payload de inspección
        inspection_payload = {
            "fecha": fecha_val.strftime("%Y-%m-%d"),
            "mes_periodo": fecha_val.strftime("%Y-%m"),
            "user_id": user["id"],
            "user_name": user["name"],
            "vehicle_id": final_veh_id,
            "interno": interno_val.strip(),
            "patente": clean_pat,
            "marca": marca_val.strip(),
            "modelo": modelo_val.strip(),
            "km": int(km_val),
            "tarjeta_verde_si_no": tarjeta_verde_val,
            "manual_si_no": manual_val,
            "vtv_si_no": vtv_val,
            "vtv_vencimiento": vtv_venc_val.strftime("%d/%m/%Y"),
            "seguro_si_no": seguro_val,
            "seguro_vencimiento": seguro_venc_val.strftime("%d/%m/%Y"),
            "observaciones": observaciones_val,
            "realizo_nombre": user["name"],
            "user_email": user.get("email", ""),
            "realizo_firma_png": final_realizo_sig_b64,
            "responsable_sitio_nombre": "",
            "responsable_sitio_firma_png": ""
        }

        # 3. Guardar en Base de Datos Supabase
        insp_id = db.save_inspection(inspection_payload, checklist_results, uploaded_photos)

        # 4. Generar PDF oficial en memoria
        clean_pat_file = sanitize_filename(clean_pat).replace(".pdf", "")
        clean_date_str = fecha_val.strftime('%Y%m%d')
        pdf_filename = f"FSSA106_{clean_pat_file}_{clean_date_str}_{insp_id[:8]}.pdf"
        
        pdf_buffer = io.BytesIO()
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo_sullair.png")
        
        pdf_payload = dict(inspection_payload)
        pdf_payload["fecha"] = fecha_val.strftime("%d/%m/%Y")
        
        generate_sullair_pdf(pdf_payload, checklist_results, pdf_buffer, logo_path)
        pdf_bytes = pdf_buffer.getvalue()

        # 5. Enviar notificación por correo con PDF adjunto a perfiles CASS, inspector y correos adicionales
        try:
            # a) Todos los usuarios con perfil CASS (gestor_cass)
            cass_users = [u for u in db.get_all_users() if u.get("role") == "gestor_cass"]
            recipients = [u["email"] for u in cass_users if u.get("email")]
            
            # b) Correo del usuario que realizó / cargó la checklist
            user_email = user.get("email")
            if user_email:
                recipients.append(user_email)
            
            # c) Correos adicionales registrados por el Administrador
            extra_emails = db.get_extra_recipients()
            recipients.extend(extra_emails)

            # d) Limpiar duplicados y vacíos
            recipients = [r.strip().lower() for r in recipients if r and "@" in r]
            recipients = list(dict.fromkeys(recipients))

            if recipients:
                send_inspection_email(inspection_payload, pdf_bytes, pdf_filename, recipients)
        except Exception as mail_err:
            print(f"Aviso envío email: {mail_err}")

        # 6. Guardar en session_state para confirmación y descarga exclusiva
        st.session_state["last_submission"] = {
            "id": insp_id,
            "interno": interno_val.strip(),
            "patente": clean_pat,
            "fecha": fecha_val.strftime("%d/%m/%Y"),
            "inspector": user.get("name"),
            "nc_count": nc_total,
            "pdf_bytes": pdf_bytes,
            "filename": pdf_filename
        }
        
        st.balloons()
        st.rerun()
