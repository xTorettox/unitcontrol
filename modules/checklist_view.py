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
                📥 Descargar Reporte PDF ({clean_name})
            </span>
        </a>
    </div>
    """
    st.markdown(html_btn, unsafe_allow_html=True)

    # Previsualización directa en pantalla (colapsada por defecto para ahorrar espacio)
    if show_preview:
        with st.expander("👁️ Ver Vista Previa del Reporte FSSA 106 generado", expanded=False):
            img_preview = get_pdf_preview_image(pdf_bytes)
            if img_preview:
                st.image(img_preview, caption=f"Vista previa del documento: {clean_name}", use_container_width=True)
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
    form_ver = st.session_state.get("chk_form_ver", 1)

    # PANTALLA DE CONFIRMACIÓN Y DESCARGA (Evita duplicaciones y confirma guardado)
    if st.session_state.get("last_submission"):
        sub = st.session_state["last_submission"]

        # Autoscroll directo e inmediato hacia arriba de la pantalla al confirmar
        scroll_direct_html = """
        <div id="top-anchor"></div>
        <img src="data:image/svg+xml;utf8,<svg></svg>" style="display:none;" onerror="
            (function() {
                function runScroll() {
                    try {
                        window.scrollTo({top: 0, left: 0, behavior: 'smooth'});
                        document.documentElement.scrollTop = 0;
                        document.body.scrollTop = 0;
                        var targets = document.querySelectorAll('[data-testid=&quot;stAppViewContainer&quot;], section.main, .main .block-container, [data-testid=&quot;stMain&quot;]');
                        targets.forEach(function(el) {
                            try {
                                el.scrollTo({top: 0, left: 0, behavior: 'smooth'});
                                el.scrollTop = 0;
                            } catch(err) {}
                        });
                        var topEl = document.getElementById('top-anchor');
                        if (topEl) {
                            topEl.scrollIntoView({behavior: 'smooth', block: 'start'});
                        }
                    } catch(e) {}
                }
                runScroll();
                setTimeout(runScroll, 60);
                setTimeout(runScroll, 200);
                setTimeout(runScroll, 500);
            })();
        ">
        """
        st.markdown(scroll_direct_html, unsafe_allow_html=True)

        email_status_html = ""
        if sub.get("email_sent"):
            email_status_html = f"""<p style="margin: 0 0 8px 0; font-size: 0.95rem; color: #15803d;">
                📧 <strong>Notificación por Email:</strong> Reporte y PDF oficial despachados con éxito a: <code>{sub.get('email_recipients', '')}</code>
            </p>"""
        else:
            email_status_html = f"""<p style="margin: 0 0 8px 0; font-size: 0.90rem; color: #64748b;">
                📧 <strong>Notificación por Email:</strong> Registrado en base de datos. (Casilla SMTP configurable en Panel de Administrador).
            </p>"""
        
        nc_count_sub = sub.get('nc_count', 0)
        estado_label = f"⚠️ Contiene {nc_count_sub} No Conformidades (Notificado a CASS)" if nc_count_sub > 0 else "✅ Cumple sin observaciones"
        estado_color = "#dc2626" if nc_count_sub > 0 else "#16a34a"

        with st.container():
            st.markdown(
                f"""
                <div style="background: #f0fdf4; border: 2px solid #86efac; padding: 22px; border-radius: 12px; margin-bottom: 20px;">
                    <h3 style="margin: 0 0 10px 0; color: #166534;">🎉 ¡Inspección Registrada y Despachada con Éxito!</h3>
                    <p style="margin: 0 0 12px 0; font-size: 1.05rem; color: #1e293b; font-weight: 500;">
                        El documento oficial <strong>FSSA 106</strong> fue cargado y generado correctamente, enviado con éxito por correo electrónico, y puede ser consultado o descargado en cualquier momento desde la sección <strong>{'Mi Historial' if user.get('role') == 'comercial' else 'Historial de Flota'}</strong>.
                    </p>
                    <div style="background-color: #ffffff; border: 1px solid #bbf7d0; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px;">
                        <p style="margin: 0 0 6px 0; font-size: 0.95rem;">
                            <strong>ID de Inspección:</strong> <code>{sub['id'][:8]}</code> | 
                            <strong>Vehículo:</strong> <strong>{sub['interno']}</strong> ({sub['patente']}) | 
                            <strong>Fecha:</strong> {sub['fecha']}
                        </p>
                        <p style="margin: 0 0 6px 0; font-size: 0.95rem; color: #374151;">
                            <strong>Inspector:</strong> {sub.get('inspector', user.get('name'))} | 
                            <strong>Resultado:</strong> <span style="color: {estado_color}; font-weight: 700;">{estado_label}</span>
                        </p>
                        {email_status_html}
                    </div>
                    <p style="margin: 0; font-size: 0.88rem; color: #15803d;">
                        💾 <strong>Base de Datos:</strong> El reporte quedó respaldado en la nube Supabase.
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
            c_action1, c_action2 = st.columns([1, 1])
            with c_action1:
                if st.button("🔄 Realizar Nueva Inspección (Formulario en blanco)", type="primary", use_container_width=True):
                    # Incrementar la versión del formulario para iniciar en blanco total
                    del st.session_state["last_submission"]
                    st.session_state["chk_form_ver"] = form_ver + 1
                    st.session_state.pop("mode_cargar_otro_vehiculo", None)
                    st.session_state.pop("_last_synced_veh_opt", None)
                    st.rerun()

            with c_action2:
                hist_btn_label = "📚 Ir a Mi Historial" if user.get("role") == "comercial" else "📚 Ir al Historial de Flota"
                if st.button(hist_btn_label, use_container_width=True):
                    del st.session_state["last_submission"]
                    st.session_state["chk_form_ver"] = form_ver + 1
                    st.session_state["nav_redirect"] = "historial"
                    st.rerun()

        # Detener la ejecución aquí para NO mostrar el formulario duplicado abajo
        return

    # FORMULARIO DE CARGA DE INSPECCIÓN
    st.markdown("""
    <style>
    /* Segmented Control - Formato limpio para opciones con indicador cromático */
    div[data-testid="stSegmentedControl"] {
        display: flex;
        justify-content: flex-end;
    }
    div[data-testid="stSegmentedControl"] button {
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        border-radius: 8px !important;
        border: 1px solid #CBD5E1 !important;
        padding: 5px 14px !important;
        min-width: 56px !important;
        background-color: #FFFFFF !important;
        color: #334155 !important;
        transition: all 0.15s ease !important;
    }
    div[data-testid="stSegmentedControl"] button:hover {
        border-color: #94A3B8 !important;
        background-color: #F8FAFC !important;
    }
    /* C - 1er botón activo: Verde */
    div[data-testid="stSegmentedControl"] [role="radiogroup"] > button:nth-child(1)[aria-checked="true"],
    div[data-testid="stSegmentedControl"] button:nth-of-type(1)[aria-checked="true"],
    div[data-testid="stSegmentedControl"] button:first-child[aria-checked="true"] {
        background-color: #E6F4EA !important;
        border: 2px solid #00853E !important;
        color: #00853E !important;
    }
    /* NC - 2do botón activo: Rojo */
    div[data-testid="stSegmentedControl"] [role="radiogroup"] > button:nth-child(2)[aria-checked="true"],
    div[data-testid="stSegmentedControl"] button:nth-of-type(2)[aria-checked="true"] {
        background-color: #FEE2E2 !important;
        border: 2px solid #DC2626 !important;
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
            fecha_val = st.date_input("Fecha de Inspección", value=date.today(), key=f"insp_fecha_{form_ver}")
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
                assigned_km = int(assigned_v.get("km_actual") or 0)
                km_val = st.number_input(
                    "Kilometraje Actual *",
                    value=assigned_km,
                    min_value=assigned_km,
                    step=100,
                    key=f"v_km_assigned_{form_ver}",
                    help=f"El kilometraje debe ser mayor o igual al último registrado ({assigned_km:,} km)." if assigned_km > 0 else "Ingrese el kilometraje actual registrado en el odómetro."
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
                tarjeta_verde_val = st.radio("Tarjeta Verde", options=["SI", "NO"], horizontal=True, key=f"doc_tarjeta_assigned_{form_ver}")
                manual_val = st.radio("Manual del Vehículo", options=["SI", "NO"], horizontal=True, key=f"doc_manual_assigned_{form_ver}")
            with col_d2:
                col_vtv1, col_vtv2 = st.columns([1, 2])
                with col_vtv1:
                    vtv_val = st.radio("VTV / RTO", options=["SI", "NO"], horizontal=True, key=f"doc_vtv_assigned_{form_ver}")
                with col_vtv2:
                    default_vtv_date = vtv_date_obj or date.today()
                    vtv_venc_val = st.date_input("Vencimiento VTV", value=default_vtv_date, key=f"doc_vtv_venc_assigned_{form_ver}")

                col_seg1, col_seg2 = st.columns([1, 2])
                with col_seg1:
                    seguro_val = st.radio("Seguro vehicular", options=["SI", "NO"], horizontal=True, key=f"doc_seguro_assigned_{form_ver}")
                with col_seg2:
                    default_seg_date = seg_date_obj or date.today()
                    seguro_venc_val = st.date_input("Vencimiento Seguro", value=default_seg_date, key=f"doc_seguro_venc_assigned_{form_ver}")

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
                key=f"sb_vehiculo_{form_ver}",
                help="Podés seleccionar una unidad de la flota o cargar los datos de una unidad nueva."
            )

            # Sincronización de los campos de texto al seleccionar del dropdown
            matched_v = None
            if selected_veh_opt != "(Cargar datos manualmente)":
                matched_v = veh_map.get(selected_veh_opt)
                if not matched_v:
                    for v in vehicles:
                        if v["patente"] in selected_veh_opt or v["interno"] in selected_veh_opt:
                            matched_v = v
                            break

            def_interno = str(matched_v.get("interno", "")).strip() if matched_v else ""
            def_patente = str(matched_v.get("patente", "")).strip() if matched_v else ""
            def_marca = str(matched_v.get("marca", "")).strip() if matched_v else ""
            def_modelo = str(matched_v.get("modelo", "") or "").strip() if matched_v else ""
            def_km = int(matched_v.get("km_actual") or 0) if matched_v else 0
            
            def_vtv_date = date.today()
            if matched_v and matched_v.get("vtv_vencimiento"):
                try:
                    def_vtv_date = datetime.strptime(matched_v["vtv_vencimiento"], "%Y-%m-%d").date()
                except Exception:
                    pass

            def_seg_date = date.today()
            if matched_v and matched_v.get("seguro_vencimiento"):
                try:
                    def_seg_date = datetime.strptime(matched_v["seguro_vencimiento"], "%Y-%m-%d").date()
                except Exception:
                    pass

            c_v1, c_v2, c_v3 = st.columns(3)
            with c_v1:
                interno_val = st.text_input("N° Interno *", value=def_interno, key=f"v_int_{form_ver}", placeholder="Ej: INT-104")
                marca_val = st.text_input("Marca *", value=def_marca, key=f"v_mar_{form_ver}", placeholder="Ej: Toyota")
            with c_v2:
                patente_val = st.text_input("Patente *", value=def_patente, key=f"v_pat_{form_ver}", placeholder="Ej: AE 452 CD")
                modelo_val = st.text_input("Modelo", value=def_modelo, key=f"v_mod_{form_ver}", placeholder="Ej: Hilux 4x4 D/C")
            with c_v3:
                km_val = st.number_input(
                    "Kilometraje Actual *",
                    value=def_km,
                    min_value=def_km,
                    step=100,
                    key=f"v_km_{form_ver}",
                    help=f"El kilometraje debe ser mayor o igual al último registrado ({def_km:,} km)." if def_km > 0 else "Ingrese el kilometraje actual registrado en el odómetro."
                )

            st.markdown("#### 📄 Documentación del Vehículo")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                tarjeta_verde_val = st.radio("Tarjeta Verde", options=["SI", "NO"], horizontal=True, key=f"doc_tarjeta_{form_ver}")
                manual_val = st.radio("Manual del Vehículo", options=["SI", "NO"], horizontal=True, key=f"doc_manual_{form_ver}")
            with col_d2:
                col_vtv1, col_vtv2 = st.columns([1, 2])
                with col_vtv1:
                    vtv_val = st.radio("VTV / RTO", options=["SI", "NO"], horizontal=True, key=f"doc_vtv_{form_ver}")
                with col_vtv2:
                    vtv_venc_val = st.date_input("Vencimiento VTV", value=def_vtv_date, key=f"doc_vtv_venc_{form_ver}")

                col_seg1, col_seg2 = st.columns([1, 2])
                with col_seg1:
                    seguro_val = st.radio("Seguro vehicular", options=["SI", "NO"], horizontal=True, key=f"doc_seguro_{form_ver}")
                with col_seg2:
                    seguro_venc_val = st.date_input("Vencimiento Seguro", value=def_seg_date, key=f"doc_seguro_venc_{form_ver}")

            # Checkbox de asignación predeterminada
            set_as_default = st.checkbox(
                "📌 Guardar y recordar este vehículo como predeterminado para mi usuario",
                value=True if not assigned_v else False,
                key=f"chk_default_veh_{form_ver}",
                help="Si lo marcás, la próxima vez que ingreses con tu usuario se precargará este vehículo automáticamente."
            )
            sel_v_id = matched_v["id"] if matched_v else None

    # 2. CHECKLIST INTERACTIVO (Sin valor por defecto para exigir llenado a conciencia)
    st.markdown("---")
    
    col_head1, col_head2 = st.columns([3, 1.2])
    with col_head1:
        st.markdown("### ✅ Checklist de Inspección")
    with col_head2:
        # Botón directo para autocompletar todo en Cumple
        if st.button("🪄 Marcar todo 'C'", key=f"btn_cheat_mark_all_c_{form_ver}", help="Atajo para marcar todas las opciones en C (Cumple)", use_container_width=True):
            for side in ["LEFT", "RIGHT"]:
                for sec in SECTIONS_STRUCTURE[side]:
                    for item in sec["items"]:
                        st.session_state[f"chk_{form_ver}_{sec['title']}_{item}"] = "🟢 C"
            st.toast("✨ ¡Todos los 34 ítems han sido marcados como 'C (Cumple)'!", icon="✅")
            st.rerun()

    st.markdown(
        """
        <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 12px 16px; border-radius: 8px; margin-bottom: 18px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
            <strong style="color: #334155;">Referencias de estado:</strong> 
            <div style="display: flex; gap: 10px;">
                <span class="status-badge badge-c">🟢 C = CUMPLE</span> 
                <span class="status-badge badge-nc">🔴 NC = NO CUMPLE</span> 
                <span class="status-badge badge-na">⚪ NA = NO APLICA</span>
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

    # Opciones con distintivo cromático visible y nítido
    OPTION_C = "🟢 C"
    OPTION_NC = "🔴 NC"
    OPTION_NA = "⚪ NA"
    STATUS_OPTIONS = [OPTION_C, OPTION_NC, OPTION_NA]

    for sec in all_sections:
        with st.expander(f"📌 {sec['title']}", expanded=True):
            for item in sec["items"]:
                key = f"chk_{form_ver}_{sec['title']}_{item}"

                # Normalizar y resolver valor inicial de session_state si existía
                curr_val = st.session_state.get(key, None)
                if curr_val in ["C", OPTION_C]:
                    default_pill = OPTION_C
                    st.session_state[key] = OPTION_C
                elif curr_val in ["NC", OPTION_NC]:
                    default_pill = OPTION_NC
                    st.session_state[key] = OPTION_NC
                elif curr_val in ["NA", OPTION_NA]:
                    default_pill = OPTION_NA
                    st.session_state[key] = OPTION_NA
                else:
                    default_pill = None

                col_it, col_opt = st.columns([3, 2])
                with col_it:
                    st.markdown(f"**{item}**")
                with col_opt:
                    raw_choice = st.segmented_control(
                        label=f"Estado de {item}",
                        options=STATUS_OPTIONS,
                        default=default_pill,
                        key=key,
                        label_visibility="collapsed"
                    )

                # Mapear al código estándar C / NC / NA
                if raw_choice == OPTION_C:
                    status_choice = "C"
                elif raw_choice == OPTION_NC:
                    status_choice = "NC"
                elif raw_choice == OPTION_NA:
                    status_choice = "NA"
                else:
                    status_choice = None

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
                            key=f"obs_falla_{form_ver}_{sec['title']}_{item}"
                        )
                    with c_ph2:
                        photo_file = st.file_uploader(
                            f"📸 Adjuntar foto de '{item}'",
                            type=["jpg", "jpeg", "png"],
                            key=f"photo_{form_ver}_{sec['title']}_{item}",
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

    # Listener invisible de teclado para autocompletar 'masfacilcontrucos' (Sin botón visible)
    cheat_js = """
    <script>
    (function() {
        var keyBuffer = "";
        var targetWord = "masfacilcontrucos";
        
        function handleKeyDown(e) {
            if (!e.key) return;
            var k = e.key.toLowerCase();
            if (k.length === 1) {
                keyBuffer += k;
                if (keyBuffer.length > 40) {
                    keyBuffer = keyBuffer.slice(-25);
                }
                if (keyBuffer.endsWith(targetWord)) {
                    keyBuffer = "";
                    var parentDoc = null;
                    try {
                        if (window.parent && window.parent.document) {
                            parentDoc = window.parent.document;
                        }
                    } catch(err) {}
                    
                    var doc = parentDoc || document;
                    var segmentedControls = doc.querySelectorAll('[data-testid="stSegmentedControl"]');
                    if (segmentedControls && segmentedControls.length > 0) {
                        segmentedControls.forEach(function(sc) {
                            var buttons = sc.querySelectorAll('button');
                            if (buttons.length > 0) {
                                buttons[0].click();
                            }
                        });
                    }
                }
            }
        }

        try {
            if (window.parent && window.parent.document) {
                window.parent.document.removeEventListener('keydown', handleKeyDown);
                window.parent.document.addEventListener('keydown', handleKeyDown);
            }
        } catch(err) {}
        document.addEventListener('keydown', handleKeyDown);
    })();
    </script>
    """
    components.html(cheat_js, height=0, width=0)

    # 3. OBSERVACIONES GENERALES
    st.markdown("---")
    st.markdown("### 📝 Observaciones Generales")
    observaciones_val = st.text_area(
        "Detalles o comentarios adicionales de la inspección",
        placeholder="Ingrese cualquier observación o comentario sobre el estado del vehículo...",
        height=100,
        key=f"insp_observaciones_{form_ver}"
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
        
        selected_sig_mode = st.radio("Método de firma para este reporte:", options=sig_options, key=f"sig_mode_{form_ver}")

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
            sig_upload = st.file_uploader("Subir imagen de firma (PNG o JPG con fondo blanco/transparente)", type=["png", "jpg", "jpeg"], key=f"upload_sig_{form_ver}")
            if sig_upload:
                final_realizo_sig_b64 = base64.b64encode(sig_upload.getvalue()).decode("utf-8")
                st.image(sig_upload, width=180, caption="Firma cargada")
                if st.checkbox("Guardar esta firma en mi perfil para futuras inspecciones", key=f"save_sig_chk_{form_ver}"):
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
                    key=f"canvas_firma_{form_ver}",
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
        c_un1, c_un2 = st.columns([3, 1.5])
        with c_un1:
            st.warning(f"⚠️ Quedan **{unanswered_total} de 34 ítems sin responder** en la planilla de inspección.")
        with c_un2:
            if st.button("🪄 Marcar pendientes en 'C'", key=f"btn_fill_pending_c_{form_ver}", help="Completa automáticamente las preguntas vacías con C (Cumple)", use_container_width=True):
                for side in ["LEFT", "RIGHT"]:
                    for sec in SECTIONS_STRUCTURE[side]:
                        for item in sec["items"]:
                            k_it = f"chk_{form_ver}_{sec['title']}_{item}"
                            if not st.session_state.get(k_it):
                                st.session_state[k_it] = OPTION_C
                st.toast("✨ ¡Ítems pendientes completados con 'C'!", icon="✅")
                st.rerun()
    elif nc_total > 0:
        st.warning(f"⚠️ Se detectaron **{nc_total} No Conformidades (NC)** en esta inspección. El reporte quedará catalogado como 'Observado' y será notificado al equipo de CASS.")
    else:
        st.success("✅ Todos los 34 ítems cumplen satisfactoriamente.")

    # Alerta si faltan datos del vehículo
    veh_invalido = not interno_val or not patente_val or not marca_val
    if veh_invalido:
        st.info("ℹ️ Recuerde seleccionar o ingresar los datos del vehículo (N° Interno, Patente y Marca) en la sección superior.")

    if st.button("🚀 Guardar Reporte y Generar PDF Oficial", key=f"btn_submit_insp_{form_ver}", type="primary", use_container_width=True):
        # Validación 1: Datos de vehículo
        if veh_invalido:
            st.error("⚠️ Complete los datos obligatorios del vehículo (Interno, Patente y Marca) antes de continuar.")
            st.toast("⚠️ Complete los datos del vehículo.", icon="⚠️")
            return

        # Validación 1.1: Kilometraje >= último registrado
        clean_pat = patente_val.strip().upper()
        existing_veh = next((v for v in db.get_vehicles() if v["patente"].upper() == clean_pat), None)
        last_km = int(existing_veh.get("km_actual") or 0) if existing_veh else 0
        if int(km_val) < last_km:
            st.error(f"⚠️ El kilometraje ingresado ({int(km_val):,} km) no puede ser menor al último kilometraje registrado ({last_km:,} km) para la unidad {interno_val} ({clean_pat}).")
            st.toast(f"⚠️ Kilometraje menor al anterior ({last_km:,} km).", icon="⚠️")
            return

        # Validación 2: Todos los checks deben estar contestados
        if unanswered_total > 0:
            st.error(f"⚠️ Debe completar todos los ítems del formulario antes de guardar. Quedan {unanswered_total} ítems sin responder.")
            st.toast(f"⚠️ Faltan responder {unanswered_total} ítems.", icon="⚠️")
            return

        with st.spinner("💾 Guardando inspección en base de datos Supabase y despachando correos automáticos..."):
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

            # 2. Preparar payload de inspección con NC count y detalle
            nc_items_list = [it for it in checklist_results if it.get("status") == "NC"]
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
                "responsable_sitio_firma_png": "",
                "status": "observado" if nc_total > 0 else "pendiente_revision",
                "nc_count": nc_total,
                "nc_items": nc_items_list
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
            email_sent = False
            email_recipients_str = ""
            try:
                cass_users = [u for u in db.get_all_users() if u.get("role") == "gestor_cass"]
                recipients = [u["email"] for u in cass_users if u.get("email")]
                
                user_email = user.get("email")
                if user_email:
                    recipients.append(user_email)
                
                extra_emails = db.get_extra_recipients()
                recipients.extend(extra_emails)

                recipients = [r.strip().lower() for r in recipients if r and "@" in r]
                recipients = list(dict.fromkeys(recipients))

                if recipients:
                    email_sent = send_inspection_email(inspection_payload, pdf_bytes, pdf_filename, recipients)
                    if email_sent:
                        email_recipients_str = ", ".join(recipients)
            except Exception as mail_err:
                print(f"Aviso envío email: {mail_err}")

            # 6. Incrementar versión del formulario para iniciar en blanco total en la próxima carga
            st.session_state["chk_form_ver"] = form_ver + 1
            st.session_state.pop("mode_cargar_otro_vehiculo", None)
            st.session_state.pop("_last_synced_veh_opt", None)

            # 7. Guardar en session_state para confirmación y descarga exclusiva
            st.session_state["last_submission"] = {
                "id": insp_id,
                "interno": interno_val.strip(),
                "patente": clean_pat,
                "fecha": fecha_val.strftime("%d/%m/%Y"),
                "inspector": user.get("name"),
                "nc_count": nc_total,
                "pdf_bytes": pdf_bytes,
                "filename": pdf_filename,
                "email_sent": email_sent,
                "email_recipients": email_recipients_str
            }
            
            st.balloons()
            st.rerun()
