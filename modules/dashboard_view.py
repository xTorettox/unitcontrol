import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import io
import os

from database.connection import get_db
from modules.pdf_generator import generate_sullair_pdf
from modules.checklist_view import render_pdf_download_block, sanitize_filename, create_digital_signature_stamp


def render_dashboard_view(user: dict):
    db = get_db()
    st.markdown("## 📊 Panel de Control y Auditoría CASS")
    st.caption("Monitoreo integral de inspecciones de flota, control de vencimientos y análisis de fallas.")

    # 1. Filtros superiores
    current_month_str = datetime.now().strftime("%Y-%m")
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        mes_filtro = st.selectbox(
            "📅 Período Mensual",
            options=[
                datetime.now().strftime("%Y-%m"),
                (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y-%m"),
                (datetime.now().replace(day=1) - timedelta(days=32)).strftime("%Y-%m"),
                "Todos los períodos"
            ],
            index=0
        )
    with col_f2:
        search_query = st.text_input("🔍 Buscar por Patente, N° Interno o Inspector", placeholder="Ej: AE 452 CD, INT-104, Martín...")

    # Obtener datos
    filter_period = None if mes_filtro == "Todos los períodos" else mes_filtro
    inspections = db.get_inspections(mes_periodo=filter_period, search=search_query if search_query else None)
    all_vehicles = db.get_vehicles()

    # Calcular vehículos pendientes de inspección en el mes
    inspected_vehicle_ids = set()
    inspected_patentes = set()
    for ins in inspections:
        if ins.get("vehicle_id"):
            inspected_vehicle_ids.add(ins["vehicle_id"])
        if ins.get("patente"):
            inspected_patentes.add(ins["patente"].upper().strip())

    pending_vehicles = [
        v for v in all_vehicles 
        if v["id"] not in inspected_vehicle_ids and v["patente"].upper().strip() not in inspected_patentes
    ]

    # Calcular alertas de vencimiento (VTV y Seguro en los próximos 30 días o vencidos)
    today = date.today()
    in_30_days = today + timedelta(days=30)
    alerts_vtv = []
    alerts_seguro = []

    for v in all_vehicles:
        if v.get("vtv_vencimiento"):
            try:
                v_date = datetime.strptime(v["vtv_vencimiento"], "%Y-%m-%d").date()
                if v_date <= in_30_days:
                    days_left = (v_date - today).days
                    alerts_vtv.append({
                        "interno": v["interno"],
                        "patente": v["patente"],
                        "vencimiento": v["vtv_vencimiento"],
                        "dias_restantes": days_left,
                        "tipo": "VTV / RTO"
                    })
            except Exception:
                pass

        if v.get("seguro_vencimiento"):
            try:
                s_date = datetime.strptime(v["seguro_vencimiento"], "%Y-%m-%d").date()
                if s_date <= in_30_days:
                    days_left = (s_date - today).days
                    alerts_seguro.append({
                        "interno": v["interno"],
                        "patente": v["patente"],
                        "vencimiento": v["seguro_vencimiento"],
                        "dias_restantes": days_left,
                        "poliza": v.get("seguro_poliza", "S/D"),
                        "tipo": "Seguro Vehicular"
                    })
            except Exception:
                pass

    # 2. BANNER DE ALERTAS CRÍTICAS
    if alerts_vtv or alerts_seguro:
        with st.expander(f"⚠️ Alertas de Vencimiento de Documentación ({len(alerts_vtv) + len(alerts_seguro)})", expanded=True):
            for a in alerts_vtv:
                if a["dias_restantes"] < 0:
                    st.error(f"🚨 **VTV VENCIDA**: Unidad **{a['interno']}** ({a['patente']}) venció el {a['vencimiento']} (hace {abs(a['dias_restantes'])} días).")
                else:
                    st.warning(f"⏳ **VTV por Vencer**: Unidad **{a['interno']}** ({a['patente']}) vence el {a['vencimiento']} ({a['dias_restantes']} días restantes).")

            for a in alerts_seguro:
                if a["dias_restantes"] < 0:
                    st.error(f"🚨 **SEGURO VENCIDO**: Unidad **{a['interno']}** ({a['patente']}) venció el {a['vencimiento']} - {a.get('poliza')}.")
                else:
                    st.warning(f"⏳ **Seguro por Vencer**: Unidad **{a['interno']}** ({a['patente']}) vence el {a['vencimiento']} ({a['dias_restantes']} días restantes).")

    # 3. TARJETAS DE INDICADORES (KPIs)
    st.markdown("---")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    total_inspections = len(inspections)
    total_nc = sum(ins.get("nc_count", 0) for ins in inspections)
    pct_compliance = 0
    if len(all_vehicles) > 0:
        pct_compliance = int((len(all_vehicles) - len(pending_vehicles)) / len(all_vehicles) * 100)

    with kpi1:
        st.markdown(
            f"""<div class="kpi-container">
                <div class="kpi-val" style="color: #00853E;">{total_inspections}</div>
                <div class="kpi-label">Reportes Cargados</div>
            </div>""",
            unsafe_allow_html=True
        )
    with kpi2:
        st.markdown(
            f"""<div class="kpi-container">
                <div class="kpi-val" style="color: {'#D93025' if len(pending_vehicles) > 0 else '#00853E'};">{len(pending_vehicles)}</div>
                <div class="kpi-label">Pendientes del Mes</div>
            </div>""",
            unsafe_allow_html=True
        )
    with kpi3:
        st.markdown(
            f"""<div class="kpi-container">
                <div class="kpi-val" style="color: {'#D93025' if total_nc > 0 else '#00853E'};">{total_nc}</div>
                <div class="kpi-label">Fallas / NC Detectadas</div>
            </div>""",
            unsafe_allow_html=True
        )
    with kpi4:
        st.markdown(
            f"""<div class="kpi-container">
                <div class="kpi-val" style="color: #1A73E8;">{pct_compliance}%</div>
                <div class="kpi-label">Cobertura de Flota</div>
            </div>""",
            unsafe_allow_html=True
        )

    st.markdown("---")

    # 4. GRÁFICOS ANALÍTICOS
    c_g1, c_g2 = st.columns([3, 2])

    with c_g1:
        st.markdown("#### 📉 Ranking de Fallas más Frecuentes (No Conformidades)")
        # Consultar ítems de no conformidad
        nc_items_list = []
        for ins in inspections:
            items = db.get_inspection_items(ins["id"])
            for it in items:
                if it.get("status") == "NC":
                    nc_items_list.append({
                        "item_name": it["item_name"],
                        "section": it["section"],
                        "patente": ins["patente"]
                    })

        if nc_items_list:
            df_nc = pd.DataFrame(nc_items_list)
            top_nc = df_nc["item_name"].value_counts().reset_index()
            top_nc.columns = ["Ítem con Falla", "Cantidad"]

            fig = px.bar(
                top_nc.head(8),
                x="Cantidad",
                y="Ítem con Falla",
                orientation="h",
                color="Cantidad",
                color_continuous_scale=["#F9AB00", "#D93025"],
                text="Cantidad"
            )
            fig.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                height=280,
                yaxis=dict(autorange="reversed"),
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("✨ No se registraron no conformidades (NC) en los reportes seleccionados.")

    with c_g2:
        st.markdown("#### ⏳ Estado de Cumplimiento Mensual")
        labels = ["Inspeccionados", "Pendientes"]
        values = [len(all_vehicles) - len(pending_vehicles), len(pending_vehicles)]
        
        fig_donut = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=.6,
            marker_colors=["#00853E", "#E2E8F0"]
        )])
        fig_donut.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=280,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    # 5. TABLA DE UNIDADES PENDIENTES
    if pending_vehicles and filter_period:
        with st.expander(f"⚠️ Unidades Pendientes de Inspección en el período {filter_period} ({len(pending_vehicles)})"):
            df_pending = pd.DataFrame(pending_vehicles)[["interno", "patente", "marca", "modelo", "km_actual"]]
            df_pending.columns = ["Interno", "Patente", "Marca", "Modelo", "Km Registrado"]
            st.dataframe(df_pending, use_container_width=True, hide_index=True)

    # 6. BANDEJA DE REPORTES PARA REVISIÓN Y FIRMA DE CASS / SITIO
    st.markdown("---")
    st.markdown("### 📑 Reportes Registrados")

    if not inspections:
        st.info("No se encontraron reportes registrados para los filtros aplicados.")
        return

    for ins in inspections:
        items = db.get_inspection_items(ins["id"])
        photos = db.get_inspection_photos(ins["id"])
        nc_count = ins.get("nc_count", 0)

        # Card container
        st.markdown(
            f"""
            <div class="mobile-card">
                <div class="mobile-card-header">
                    <span>🚗 {ins['interno']} - {ins['patente']} ({ins['marca']} {ins['modelo']})</span>
                    <span class="status-badge {'badge-nc' if nc_count > 0 else 'badge-c'}">
                        {f'{nc_count} NC' if nc_count > 0 else 'CUMPLE'}
                    </span>
                </div>
                <div>
                    <strong>Fecha:</strong> {ins['fecha']} | <strong>Inspector:</strong> {ins['user_name']} | <strong>Km:</strong> {int(ins.get('km') or 0):,} km<br/>
                    <strong>Estado de firma CASS:</strong> {'✅ Firmado por ' + ins['responsable_sitio_nombre'] if ins.get('responsable_sitio_nombre') else '⏳ Pendiente de firma'}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.expander(f"🔍 Ver detalles de inspección {ins['interno']} ({ins['fecha']})"):
            c_det1, c_det2 = st.columns([2, 1])
            with c_det1:
                st.markdown(f"**Observaciones:** {ins.get('observaciones') or 'Sin observaciones registradas.'}")
                if nc_count > 0:
                    st.markdown("**No Conformidades detectadas:**")
                    for it in items:
                        if it["status"] == "NC":
                            st.markdown(f"- 🔴 **{it['item_name']}**: {it.get('observation') or 'Sin detalle adicional'}")

                if photos:
                    st.markdown(f"**📸 Fotos de Evidencia ({len(photos)}):**")
                    cols_ph = st.columns(min(len(photos), 3))
                    for idx, p in enumerate(photos):
                        with cols_ph[idx % 3]:
                            st.image(
                                f"data:image/jpeg;base64,{p['image_base64']}",
                                caption=f"{p['item_name']} - {p.get('caption', '')}",
                                use_container_width=True
                            )

            with c_det2:
                # Generar y descargar PDF oficial
                pdf_buffer = io.BytesIO()
                logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo_sullair.png")
                pdf_payload = dict(ins)
                # Formatear fecha para el PDF
                try:
                    if "-" in str(ins["fecha"]):
                        dt_obj = datetime.strptime(ins["fecha"], "%Y-%m-%d")
                        pdf_payload["fecha"] = dt_obj.strftime("%d/%m/%Y")
                except Exception:
                    pass
                generate_sullair_pdf(pdf_payload, items, pdf_buffer, logo_path)
                pdf_bytes = pdf_buffer.getvalue()

                # Guardar en disco si no existe
                clean_pat = sanitize_filename(ins['patente']).replace(".pdf", "")
                clean_date = str(ins['fecha']).replace('-', '').replace('/', '')
                reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
                os.makedirs(reports_dir, exist_ok=True)
                pdf_filename = f"FSSA106_{clean_pat}_{clean_date}_{ins['id'][:8]}.pdf"
                pdf_file_path = os.path.join(reports_dir, pdf_filename)
                try:
                    if not os.path.exists(pdf_file_path):
                        with open(pdf_file_path, "wb") as f_out:
                            f_out.write(pdf_bytes)
                except Exception:
                    pass

                render_pdf_download_block(
                    pdf_bytes=pdf_bytes,
                    filename=pdf_filename,
                    saved_path=pdf_file_path,
                    key_prefix=f"dash_{ins['id'][:8]}",
                    show_preview=True
                )

                # Opción para firmar como Responsable de Sitio / CASS
                if not ins.get("responsable_sitio_nombre"):
                    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                    if st.button("✍️ Firmar como Responsable CASS / Sitio", key=f"btn_sign_{ins['id']}", use_container_width=True):
                        sig_to_use = user.get("signature_png") or create_digital_signature_stamp(user["name"], datetime.now().strftime("%d/%m/%Y %H:%M"))
                        db.sign_as_responsible(ins["id"], user["name"], sig_to_use)
                        st.success("¡Reporte firmado y aprobado con éxito!")
                        st.rerun()
