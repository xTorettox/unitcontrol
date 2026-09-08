import streamlit as st
import io
import os
from datetime import datetime

from database.connection import get_db
from modules.pdf_generator import generate_sullair_pdf
from modules.checklist_view import render_pdf_download_block, sanitize_filename


def render_history_view(user: dict):
    db = get_db()
    st.markdown("## 📚 Historial de Inspecciones")
    st.caption("Consulte, reimprima y descargue los reportes mensuales oficiales.")

    is_admin_or_gestor = user.get("role") in ["admin", "gestor_cass", "responsable_flota"]

    c_h1, c_h2 = st.columns([1, 2])
    with c_h1:
        mes_filtro = st.selectbox(
            "Filtrar por Mes",
            options=["Todos"] + [
                datetime.now().strftime("%Y-%m"),
                "2026-08",
                "2026-07",
                "2026-06"
            ],
            key="hist_mes"
        )
    with c_h2:
        search = st.text_input("Buscar por Patente, Interno o Inspector", key="hist_search")

    filter_user_id = None if is_admin_or_gestor else user["id"]
    filter_mes = None if mes_filtro == "Todos" else mes_filtro

    inspections = db.get_inspections(user_id=filter_user_id, mes_periodo=filter_mes, search=search if search else None)

    if not inspections:
        st.info("No se registraron inspecciones que coincidan con los criterios de búsqueda.")
        return

    st.markdown(f"**Total de reportes encontrados:** {len(inspections)}")

    reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
    os.makedirs(reports_dir, exist_ok=True)

    for ins in inspections:
        items = db.get_inspection_items(ins["id"])
        photos = db.get_inspection_photos(ins["id"])
        nc_count = ins.get("nc_count", 0)
        km_val = int(ins.get("km") or 0)

        with st.container():
            st.markdown(
                f"""
                <div class="mobile-card">
                    <div class="mobile-card-header">
                        <span>🗓️ {ins['fecha']} - {ins['interno']} ({ins['patente']})</span>
                        <span class="status-badge {'badge-nc' if nc_count > 0 else 'badge-c'}">
                            {f'{nc_count} No Conformidades' if nc_count > 0 else 'Aprobado sin fallas'}
                        </span>
                    </div>
                    <div style="font-size: 0.95rem; line-height: 1.5;">
                        <strong>Vehículo:</strong> {ins['marca']} {ins['modelo']} | <strong>Km:</strong> {km_val:,} km<br/>
                        <strong>Inspector:</strong> {ins['user_name']} | <strong>Período:</strong> {ins['mes_periodo']}<br/>
                        <strong>Firma CASS / Sitio:</strong> {'✅ Firmado (' + ins['responsable_sitio_nombre'] + ')' if ins.get('responsable_sitio_nombre') else '⏳ Pendiente de firma'}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Generar PDF para descarga
            pdf_buf = io.BytesIO()
            logo_p = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo_sullair.png")
            pdf_payload = dict(ins)
            try:
                if "-" in str(ins["fecha"]):
                    dt_obj = datetime.strptime(ins["fecha"], "%Y-%m-%d")
                    pdf_payload["fecha"] = dt_obj.strftime("%d/%m/%Y")
            except Exception:
                pass
                
            generate_sullair_pdf(pdf_payload, items, pdf_buf, logo_p)
            pdf_data = pdf_buf.getvalue()

            clean_pat = sanitize_filename(ins['patente']).replace(".pdf", "")
            clean_date = str(ins['fecha']).replace('-', '').replace('/', '')
            pdf_filename = f"FSSA106_{clean_pat}_{clean_date}_{ins['id'][:8]}.pdf"
            pdf_file_path = os.path.join(reports_dir, pdf_filename)
            try:
                if not os.path.exists(pdf_file_path):
                    with open(pdf_file_path, "wb") as f_out:
                        f_out.write(pdf_data)
            except Exception:
                pass

            c_act1, c_act2 = st.columns([1, 1])
            with c_act1:
                if nc_count > 0:
                    st.markdown("**Detalle de fallas registradas:**")
                    for it in items:
                        if it["status"] == "NC":
                            st.markdown(f"- 🔴 **{it['item_name']}**: {it.get('observation') or 'Sin observación'}")

                if photos:
                    st.markdown(f"**Fotos adjuntas ({len(photos)}):**")
                    cols = st.columns(min(len(photos), 3))
                    for i, p in enumerate(photos):
                        with cols[i % 3]:
                            st.image(f"data:image/jpeg;base64,{p['image_base64']}", caption=p.get('caption', ''), use_container_width=True)

            with c_act2:
                render_pdf_download_block(
                    pdf_bytes=pdf_data,
                    filename=pdf_filename,
                    saved_path=pdf_file_path,
                    key_prefix=f"hist_{ins['id'][:8]}",
                    show_preview=True
                )

            st.markdown("---")
