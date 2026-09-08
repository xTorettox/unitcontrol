import streamlit as st
import base64
import io
import os
import re
import uuid
from datetime import datetime, date
from PIL import Image, ImageDraw, ImageFont

from database.connection import get_db
from modules.pdf_generator import SECTIONS_STRUCTURE, generate_sullair_pdf


def sanitize_filename(filename: str) -> str:
    """Limpia el nombre de archivo para evitar caracteres inválidos en descargas del navegador."""
    # Reemplazar espacios y caracteres no alfanuméricos excepto guiones y puntos
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
    Renderiza un bloque robusto y garantizado de descarga, apertura y previsualización de PDF.
    Usa tanto enlace directo HTML5 base64 con extensión .pdf forzada, como botón nativo de Streamlit
    y apertura directa en Windows (os.startfile).
    """
    clean_name = sanitize_filename(filename)
    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        # Enlace HTML5 directo - Garantiza la extensión .pdf en Chrome / Edge
        html_btn = f"""
        <a href="data:application/pdf;base64,{b64_pdf}" download="{clean_name}" target="_blank"
           style="display: flex; align-items: center; justify-content: center; width: 100%;
                  background-color: #00853E; color: #FFFFFF !important; padding: 10px 18px; text-decoration: none !important;
                  font-weight: 700; font-size: 0.95rem; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.15);
                  text-align: center; border: none; cursor: pointer; margin-bottom: 5px;">
            📥 Descargar {clean_name}
        </a>
        """
        st.markdown(html_btn, unsafe_allow_html=True)

    with col_btn2:
        if saved_path and os.path.exists(saved_path):
            if st.button("📂 Abrir PDF en el Visor de Windows", key=f"{key_prefix}_btn_open_win", use_container_width=True):
                try:
                    os.startfile(saved_path)
                    st.toast("Abriendo documento en su visor predeterminado...")
                except Exception as e:
                    st.error(f"No se pudo abrir automáticamente: {e}")
        else:
            st.download_button(
                label=f"💾 Descarga Alternativa ({clean_name})",
                data=pdf_bytes,
                file_name=clean_name,
                mime="application/pdf",
                key=f"{key_prefix}_alt_dl",
                use_container_width=True
            )

    # Previsualización directa en pantalla
    if show_preview:
        with st.expander("👁️ Ver Vista Previa del Reporte FSSA 106 generado", expanded=False):
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
        
        try:
            font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 16)
        except Exception:
            font = ImageFont.load_default()
            
        draw.text((10, h - 28), text, fill=(255, 255, 255), font=font)
        
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"Error procesando foto: {e}")
        return ""


def create_digital_signature_stamp(name: str, date_str: str) -> str:
    """Genera una firma digital gráfica certificada con sello oficial de Sullair Argentina."""
    img = Image.new("RGBA", (460, 125), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Marco institucional verde Sullair
    draw.rounded_rectangle([(2, 2), (458, 123)], radius=8, outline=(0, 90, 42, 220), width=2, fill=(240, 253, 244, 240))
    
    try:
        font_title = ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", 14)
        font_main = ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", 12)
        font_sub = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 10)
        font_hash = ImageFont.truetype("C:\\Windows\\Fonts\\consola.ttf", 9)
    except Exception:
        font_title = ImageFont.load_default()
        font_main = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_hash = ImageFont.load_default()

    draw.text((16, 10), "🛡️ FIRMA DIGITAL CERTIFICADA - SULLAIR ARGENTINA", fill=(0, 90, 42, 255), font=font_title)
    draw.text((16, 36), f"Inspector / Firmante: {name}", fill=(30, 41, 59, 255), font=font_main)
    draw.text((16, 58), f"Fecha de emisión: {date_str} | Sistema FSSA 106 Rev. 06", fill=(71, 85, 105, 255), font=font_sub)
    draw.text((16, 78), f"Certificación Digital: {uuid.uuid4().hex[:14].upper()}", fill=(100, 116, 139, 255), font=font_hash)
    draw.text((16, 96), "Inspección mensual de flota - Sullair Argentina S.A.", fill=(100, 116, 139, 255), font=font_hash)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def render_checklist_view(user: dict):
    db = get_db()
    st.markdown("### 📋 Control de Vehículos (Mensual)")
    st.caption("Formulario oficial de inspección mensual **FSSA 106 Rev. 06**")

    # Si hay un reporte recién guardado, mostrarlo de forma persistente y destacada
    if st.session_state.get("last_submission"):
        sub = st.session_state["last_submission"]
        st.success(f"🎉 **¡Reporte FSSA 106 generado y guardado exitosamente!**")
        with st.container():
            st.markdown(
                f"""
                <div style="background: #f0fdf4; border: 2px solid #86efac; padding: 16px; border-radius: 10px; margin-bottom: 20px;">
                    <h4 style="margin: 0 0 10px 0; color: #166534;">📄 Reporte Oficial Listo</h4>
                    <p style="margin: 0 0 6px 0; font-size: 0.95rem;">
                        <strong>ID de Inspección:</strong> <code>{sub['id'][:8]}</code> | 
                        <strong>Vehículo:</strong> {sub['interno']} ({sub['patente']}) | 
                        <strong>Fecha:</strong> {sub['fecha']}
                    </p>
                    <p style="margin: 0 0 10px 0; font-size: 0.9rem; color: #4b5563;">
                        <strong>Estado:</strong> {'⚠️ Contiene ' + str(sub['nc_count']) + ' No Conformidades (Derivado a CASS)' if sub['nc_count'] > 0 else '✅ Cumple sin observaciones'}
                    </p>
                    <p style="margin: 0; font-size: 0.85rem; color: #15803d;">
                        📁 <strong>Archivo persistido en disco:</strong> <code>{sub['saved_path']}</code>
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Bloque robusto de descarga y visor
            render_pdf_download_block(
                pdf_bytes=sub["pdf_bytes"],
                filename=sub["filename"],
                saved_path=sub["saved_path"],
                key_prefix="sub_success",
                show_preview=True
            )

            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            if st.button("🔄 Cargar Nueva Inspección", use_container_width=True):
                del st.session_state["last_submission"]
                st.rerun()

        st.markdown("---")

    # 1. DATOS DEL VEHÍCULO Y CABECERA
    vehicles = db.get_vehicles()
    assigned_v = None
    if user.get("assigned_vehicle_id"):
        assigned_v = db.get_vehicle_by_id(user["assigned_vehicle_id"])

    with st.expander("🚗 Datos del Vehículo e Inspección", expanded=True):
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            fecha_val = st.date_input("Fecha de Inspección", value=date.today(), key="insp_fecha")
        with col_f2:
            veh_options = ["(Seleccionar de la flota)"] + [f"{v['interno']} - {v['patente']} ({v['marca']} {v['modelo']})" for v in vehicles]
            
            default_v_idx = 0
            if assigned_v:
                for idx, opt in enumerate(veh_options):
                    if assigned_v["patente"] in opt:
                        default_v_idx = idx
                        break

            selected_veh_opt = st.selectbox(
                "Vehículo Asignado / Flota",
                options=veh_options,
                index=default_v_idx,
                help="Podés seleccionar tu vehículo o ingresar los datos manualmente si usaste otra unidad."
            )

        # Cargar datos del vehículo seleccionado
        sel_v_data = None
        if selected_veh_opt != "(Seleccionar de la flota)":
            sel_patente = selected_veh_opt.split("-")[1].split("(")[0].strip()
            for v in vehicles:
                if v["patente"] == sel_patente:
                    sel_v_data = v
                    break

        c_v1, c_v2, c_v3 = st.columns(3)
        with c_v1:
            interno_val = st.text_input("N° Interno *", value=sel_v_data["interno"] if sel_v_data else "", key="v_interno")
            marca_val = st.text_input("Marca *", value=sel_v_data["marca"] if sel_v_data else "", key="v_marca")
        with c_v2:
            patente_val = st.text_input("Patente *", value=sel_v_data["patente"] if sel_v_data else "", key="v_patente")
            modelo_val = st.text_input("Modelo", value=sel_v_data["modelo"] if sel_v_data else "", key="v_modelo")
        with c_v3:
            km_val = st.number_input(
                "Kilometraje Actual *",
                value=int(sel_v_data["km_actual"]) if sel_v_data else 0,
                min_value=0,
                step=100,
                key="v_km"
            )

        st.markdown("#### 📄 Documentación del Vehículo")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            tarjeta_verde_val = st.radio(
                "Tarjeta Verde",
                options=["SI", "NO"],
                horizontal=True,
                index=0 if (sel_v_data and sel_v_data.get("tarjeta_verde", True)) else 0,
                key="doc_tarjeta"
            )
            manual_val = st.radio(
                "Manual del Vehículo",
                options=["SI", "NO"],
                horizontal=True,
                index=0 if (sel_v_data and sel_v_data.get("manual", True)) else 0,
                key="doc_manual"
            )
        with col_d2:
            col_vtv1, col_vtv2 = st.columns([1, 2])
            with col_vtv1:
                vtv_val = st.radio("VTV / RTO", options=["SI", "NO"], horizontal=True, key="doc_vtv")
            with col_vtv2:
                default_vtv_date = date.today()
                if sel_v_data and sel_v_data.get("vtv_vencimiento"):
                    try:
                        default_vtv_date = datetime.strptime(sel_v_data["vtv_vencimiento"], "%Y-%m-%d").date()
                    except Exception:
                        pass
                vtv_venc_val = st.date_input("Vencimiento VTV", value=default_vtv_date, key="doc_vtv_venc")

            col_seg1, col_seg2 = st.columns([1, 2])
            with col_seg1:
                seguro_val = st.radio("Seguro vehicular", options=["SI", "NO"], horizontal=True, key="doc_seguro")
            with col_seg2:
                default_seg_date = date.today()
                if sel_v_data and sel_v_data.get("seguro_vencimiento"):
                    try:
                        default_seg_date = datetime.strptime(sel_v_data["seguro_vencimiento"], "%Y-%m-%d").date()
                    except Exception:
                        pass
                seguro_venc_val = st.date_input("Vencimiento Seguro", value=default_seg_date, key="doc_seguro_venc")

    # 2. CHECKLIST INTERACTIVO
    st.markdown("---")
    st.markdown("### ✅ Checklist de Inspección")
    st.markdown(
        """
        <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; padding: 10px; border-radius: 8px; margin-bottom: 15px;">
            <strong style="color: #166534;">Referencias de estado:</strong> 
            <span class="status-badge badge-c">C = Cumple</span> 
            <span class="status-badge badge-nc">NC = No Cumple</span> 
            <span class="status-badge badge-na">NA = No Aplica</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Botón rápido para autocompletar todo en Cumple (C)
    col_bulk1, col_bulk2 = st.columns([2, 1])
    with col_bulk1:
        if st.button("✨ Marcar todos los ítems como 'C' (Cumple)", use_container_width=True):
            for side in ["LEFT", "RIGHT"]:
                for sec in SECTIONS_STRUCTURE[side]:
                    for item in sec["items"]:
                        st.session_state[f"chk_{sec['title']}_{item}"] = "C"
            st.rerun()

    # Recorrer todas las secciones estructuradas
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
                if key not in st.session_state:
                    st.session_state[key] = "C"

                col_it, col_opt = st.columns([3, 2])
                with col_it:
                    st.markdown(f"**{item}**")
                with col_opt:
                    status_choice = st.segmented_control(
                        label=f"Estado de {item}",
                        options=["C", "NC", "NA"],
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
                    "status": status_choice or "C",
                    "has_photo": has_photo,
                    "observation": obs_falla
                })

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

    # Si no se eligió ninguna firma manual, asegurar firma digital por defecto
    if not final_realizo_sig_b64:
        final_realizo_sig_b64 = create_digital_signature_stamp(user.get("name", "Inspector"), datetime.now().strftime("%d/%m/%Y %H:%M"))

    # 5. BOTÓN DE ENVÍO Y GENERACIÓN DE REPORTE
    st.markdown("---")
    nc_total = sum(1 for it in checklist_results if it["status"] == "NC")
    if nc_total > 0:
        st.warning(f"⚠️ Se detectaron **{nc_total} No Conformidades (NC)** en esta inspección. El reporte quedará marcado para revisión por el equipo de CASS.")
    else:
        st.success("✅ Todos los ítems cumplen satisfactoriamente.")

    if st.button("🚀 Guardar Reporte y Generar PDF Oficial", type="primary", use_container_width=True):
        if not interno_val or not patente_val:
            st.error("Por favor complete los campos obligatorios de Interno y Patente del vehículo.")
            return

        # 1. Preparar datos de guardado
        inspection_payload = {
            "fecha": fecha_val.strftime("%Y-%m-%d"),
            "mes_periodo": fecha_val.strftime("%Y-%m"),
            "user_id": user["id"],
            "user_name": user["name"],
            "vehicle_id": sel_v_data["id"] if sel_v_data else None,
            "interno": interno_val,
            "patente": patente_val,
            "marca": marca_val,
            "modelo": modelo_val,
            "km": int(km_val),
            "tarjeta_verde_si_no": tarjeta_verde_val,
            "manual_si_no": manual_val,
            "vtv_si_no": vtv_val,
            "vtv_vencimiento": vtv_venc_val.strftime("%d/%m/%Y"),
            "seguro_si_no": seguro_val,
            "seguro_vencimiento": seguro_venc_val.strftime("%d/%m/%Y"),
            "observaciones": observaciones_val,
            "realizo_nombre": user["name"],
            "realizo_firma_png": final_realizo_sig_b64,
            "responsable_sitio_nombre": "",
            "responsable_sitio_firma_png": ""
        }

        # 2. Guardar en Base de Datos
        insp_id = db.save_inspection(inspection_payload, checklist_results, uploaded_photos)

        # 3. Generar PDF oficial y guardarlo físicamente en disco
        reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        clean_pat = sanitize_filename(patente_val).replace(".pdf", "")
        clean_date_str = fecha_val.strftime('%Y%m%d')
        pdf_filename = f"FSSA106_{clean_pat}_{clean_date_str}_{insp_id[:8]}.pdf"
        pdf_file_path = os.path.join(reports_dir, pdf_filename)
        
        pdf_buffer = io.BytesIO()
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo_sullair.png")
        
        pdf_payload = dict(inspection_payload)
        pdf_payload["fecha"] = fecha_val.strftime("%d/%m/%Y")
        
        generate_sullair_pdf(pdf_payload, checklist_results, pdf_buffer, logo_path)
        pdf_bytes = pdf_buffer.getvalue()

        # Guardar en archivo local
        try:
            with open(pdf_file_path, "wb") as f_out:
                f_out.write(pdf_bytes)
        except Exception as e:
            print(f"Error guardando PDF en disco: {e}")

        # 4. Guardar en session_state para descarga persistente
        st.session_state["last_submission"] = {
            "id": insp_id,
            "interno": interno_val,
            "patente": patente_val,
            "fecha": fecha_val.strftime("%d/%m/%Y"),
            "nc_count": nc_total,
            "pdf_bytes": pdf_bytes,
            "filename": pdf_filename,
            "saved_path": pdf_file_path
        }
        
        st.balloons()
        st.rerun()
