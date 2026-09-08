import streamlit as st
import base64
import pandas as pd
from datetime import date, datetime

from database.connection import get_db
from modules.auth import ROLE_NAMES
from modules.checklist_view import create_digital_signature_stamp


def render_profile_view(current_user: dict):
    db = get_db()
    st.markdown("## 👤 Mi Perfil y Firma Digital")
    st.caption("Configuración personal de cuenta y firma digital para reportes oficiales FSSA 106.")

    c_p1, c_p2 = st.columns([1, 1])
    with c_p1:
        st.markdown("### 📋 Datos Personales")
        st.markdown(f"**Nombre:** `{current_user['name']}`")
        st.markdown(f"**Correo Corporativo:** `{current_user['email']}`")
        st.markdown(f"**Rol en Sullair:** `{ROLE_NAMES.get(current_user['role'], current_user['role'])}`")
        if current_user.get("assigned_vehicle_id"):
            v = db.get_vehicle_by_id(current_user["assigned_vehicle_id"])
            if v:
                st.markdown(f"**Vehículo Asignado:** `{v['interno']}` ({v['patente']} - {v['marca']} {v['modelo']})")

    with c_p2:
        st.markdown("### 🖋️ Firma Digital Registrada")
        if current_user.get("signature_png"):
            st.image(f"data:image/png;base64,{current_user['signature_png']}", width=250, caption="Firma activa en el sistema")
            if st.button("🗑️ Eliminar firma guardada"):
                db.update_user(current_user["id"], {"signature_png": ""})
                current_user["signature_png"] = ""
                st.session_state["user"] = current_user
                st.success("Firma eliminada.")
                st.rerun()
        else:
            st.info("Aún no registraste una firma personal. Podés subir una imagen o generar un sello digital certificado abajo.")

    st.markdown("---")
    st.markdown("### ⚙️ Actualizar o Generar Firma")
    tab_upload, tab_cert = st.tabs(["📁 Subir Imagen de Firma (PNG/JPG)", "🛡️ Generar Sello Digital Certificado"])

    with tab_upload:
        new_sig_file = st.file_uploader(
            "Seleccione un archivo de imagen de su firma (fondo blanco o transparente recomendado)",
            type=["png", "jpg", "jpeg"],
            key="profile_sig_upload"
        )
        if new_sig_file:
            sig_b64 = base64.b64encode(new_sig_file.getvalue()).decode("utf-8")
            st.image(new_sig_file, width=220, caption="Vista previa de firma a guardar")
            if st.button("💾 Guardar Firma Subida en Mi Perfil", type="primary", key="btn_save_uploaded_sig"):
                db.update_user(current_user["id"], {"signature_png": sig_b64})
                current_user["signature_png"] = sig_b64
                st.session_state["user"] = current_user
                st.success("¡Firma actualizada y guardada con éxito!")
                st.rerun()

    with tab_cert:
        st.caption("Podés generar un sello digital certificado oficial de Sullair Argentina para firmar automáticamente:")
        cert_preview_b64 = create_digital_signature_stamp(current_user["name"], datetime.now().strftime("%d/%m/%Y %H:%M"))
        st.image(f"data:image/png;base64,{cert_preview_b64}", width=320, caption="Vista previa del Sello Certificado")
        if st.button("🛡️ Activar este Sello Certificado en Mi Perfil", type="primary", key="btn_save_cert_sig"):
            db.update_user(current_user["id"], {"signature_png": cert_preview_b64})
            current_user["signature_png"] = cert_preview_b64
            st.session_state["user"] = current_user
            st.success("¡Sello digital certificado guardado en tu perfil!")
            st.rerun()


def render_admin_view(current_user: dict):
    db = get_db()
    st.markdown("## ⚙️ Panel de Administración")
    st.caption("Gestión integral de usuarios, roles, asignaciones y flota de vehículos Sullair Argentina.")

    tab_users, tab_vehicles = st.tabs(["👥 Gestión de Usuarios", "🚙 Gestión de Flota"])

    # --- TAB 1: USUARIOS ---
    with tab_users:
        st.markdown("### Usuarios Registrados")
        users = db.get_all_users()
        vehicles = db.get_vehicles()
        veh_dict = {v["id"]: f"{v['interno']} ({v['patente']})" for v in vehicles}

        # Tabla resumen
        user_rows = []
        for u in users:
            v_name = veh_dict.get(u.get("assigned_vehicle_id"), "Ninguno")
            user_rows.append({
                "Nombre": u["name"],
                "Email": u["email"],
                "Rol": ROLE_NAMES.get(u["role"], u["role"]),
                "Vehículo Asignado": v_name,
                "Tiene Firma": "✅ Sí" if u.get("signature_png") else "❌ No"
            })
        st.dataframe(pd.DataFrame(user_rows), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### ➕ Crear Nuevo Usuario")
        with st.form("form_create_user"):
            c_u1, c_u2 = st.columns(2)
            with c_u1:
                new_name = st.text_input("Nombre Completo *", placeholder="Ej: Juan Pérez")
                new_email = st.text_input("Correo Electrónico *", placeholder="juan.perez@sullair.com.ar")
                new_role = st.selectbox(
                    "Rol en el Sistema *",
                    options=["comercial", "gestor_cass", "responsable_flota", "admin"],
                    format_func=lambda x: ROLE_NAMES.get(x, x)
                )
            with c_u2:
                new_pass = st.text_input("Contraseña Temporal *", type="password")
                veh_select_opts = ["(Sin vehículo asignado)"] + [f"{v['interno']} - {v['patente']} ({v['marca']})" for v in vehicles]
                new_veh_choice = st.selectbox("Vehículo Asignado por Defecto", options=veh_select_opts)

            submitted_user = st.form_submit_button("Crear Usuario", type="primary", use_container_width=True)
            if submitted_user:
                if not new_name or not new_email or not new_pass:
                    st.error("Por favor complete todos los campos obligatorios.")
                else:
                    chosen_v_id = None
                    if new_veh_choice != "(Sin vehículo asignado)":
                        pat = new_veh_choice.split("-")[1].split("(")[0].strip()
                        for v in vehicles:
                            if v["patente"] == pat:
                                chosen_v_id = v["id"]
                                break

                    try:
                        uid = db.create_user(
                            email=new_email,
                            name=new_name,
                            role=new_role,
                            password=new_pass,
                            assigned_vehicle_id=chosen_v_id
                        )
                        st.success(f"¡Usuario '{new_name}' creado exitosamente!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creando usuario: {e}")

        # Modificar o Eliminar Usuario existente
        if len(users) > 1:
            st.markdown("---")
            st.markdown("### ✏️ Modificar o Eliminar Usuario")
            user_select_opts = [f"{u['name']} ({u['email']})" for u in users]
            sel_u_label = st.selectbox("Seleccionar Usuario para Administrar", options=user_select_opts, key="admin_sel_user")
            sel_u_email = sel_u_label.split("(")[-1].replace(")", "").strip()
            target_user = next((u for u in users if u["email"] == sel_u_email), None)

            if target_user:
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    edit_role = st.selectbox(
                        "Cambiar Rol",
                        options=["comercial", "gestor_cass", "responsable_flota", "admin"],
                        index=["comercial", "gestor_cass", "responsable_flota", "admin"].index(target_user["role"]) if target_user["role"] in ["comercial", "gestor_cass", "responsable_flota", "admin"] else 0,
                        format_func=lambda x: ROLE_NAMES.get(x, x),
                        key="edit_role"
                    )
                    edit_pass = st.text_input("Nueva Contraseña (dejar vacío para no cambiar)", type="password", key="edit_pass")
                with col_m2:
                    curr_veh_idx = 0
                    if target_user.get("assigned_vehicle_id") and target_user["assigned_vehicle_id"] in veh_dict:
                        target_v_str = veh_dict[target_user["assigned_vehicle_id"]]
                        for idx, opt in enumerate(veh_select_opts):
                            if target_v_str.split("(")[0].strip() in opt:
                                curr_veh_idx = idx
                                break
                    edit_veh = st.selectbox("Reasignar Vehículo", options=veh_select_opts, index=curr_veh_idx, key="edit_veh")

                col_btn1, col_btn2 = st.columns([1, 1])
                with col_btn1:
                    if st.button("💾 Guardar Cambios en Usuario", key="btn_save_user_edit", type="primary", use_container_width=True):
                        update_dict = {"role": edit_role}
                        if edit_pass:
                            update_dict["password"] = edit_pass
                        if edit_veh != "(Sin vehículo asignado)":
                            pat = edit_veh.split("-")[1].split("(")[0].strip()
                            for v in vehicles:
                                if v["patente"] == pat:
                                    update_dict["assigned_vehicle_id"] = v["id"]
                                    break
                        else:
                            update_dict["assigned_vehicle_id"] = None

                        db.update_user(target_user["id"], update_dict)
                        st.success(f"¡Usuario {target_user['name']} actualizado correctamente!")
                        st.rerun()

                with col_btn2:
                    if target_user["id"] != current_user["id"]:
                        if st.button("🗑️ Eliminar Usuario", key="btn_del_user", type="secondary", use_container_width=True):
                            db.delete_user(target_user["id"])
                            st.warning(f"Usuario {target_user['name']} eliminado.")
                            st.rerun()

    # --- TAB 2: FLOTA ---
    with tab_vehicles:
        st.markdown("### Flota de Vehículos")
        vehicles = db.get_vehicles()
        if vehicles:
            df_v = pd.DataFrame(vehicles)[["interno", "patente", "marca", "modelo", "km_actual", "vtv_vencimiento", "seguro_vencimiento", "seguro_poliza"]]
            df_v.columns = ["Interno", "Patente", "Marca", "Modelo", "Km Actual", "Vto VTV", "Vto Seguro", "Póliza"]
            st.dataframe(df_v, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### ➕ Registrar Nueva Unidad")
        with st.form("form_create_vehicle"):
            c_v1, c_v2, c_v3 = st.columns(3)
            with c_v1:
                v_interno = st.text_input("N° Interno *", placeholder="Ej: INT-120")
                v_marca = st.text_input("Marca *", placeholder="Ej: Toyota")
                v_vtv = st.date_input("Vencimiento VTV / RTO", value=date.today())
            with c_v2:
                v_patente = st.text_input("Patente *", placeholder="Ej: AF 123 ZZ")
                v_modelo = st.text_input("Modelo *", placeholder="Ej: Hilux 4x4")
                v_seguro = st.date_input("Vencimiento Seguro", value=date.today())
            with c_v3:
                v_km = st.number_input("Kilometraje Inicial", value=0, min_value=0, step=500)
                v_poliza = st.text_input("Compañía / N° Póliza", placeholder="Ej: Allianz #883912")

            submitted_veh = st.form_submit_button("Guardar Vehículo", type="primary", use_container_width=True)
            if submitted_veh:
                if not v_interno or not v_patente or not v_marca:
                    st.error("Por favor complete los campos obligatorios de Interno, Patente y Marca.")
                else:
                    try:
                        db.create_vehicle({
                            "interno": v_interno,
                            "patente": v_patente,
                            "marca": v_marca,
                            "modelo": v_modelo,
                            "km_actual": v_km,
                            "vtv_vencimiento": v_vtv.strftime("%Y-%m-%d"),
                            "seguro_vencimiento": v_seguro.strftime("%Y-%m-%d"),
                            "seguro_poliza": v_poliza,
                            "tarjeta_verde": True,
                            "manual": True
                        })
                        st.success(f"¡Vehículo {v_interno} ({v_patente}) registrado con éxito!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error registrando vehículo: {e}")
