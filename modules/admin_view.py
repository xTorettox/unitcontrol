import streamlit as st
import base64
import pandas as pd
from datetime import date, datetime

from database.connection import get_db
from modules.auth import ROLE_NAMES
from modules.checklist_view import create_digital_signature_stamp
from modules.email_notifier import send_test_email


def render_profile_view(current_user: dict):
    db = get_db()
    st.markdown("## 👤 Mi Perfil y Firma Digital")
    st.caption("Configuración personal de cuenta y firma digital para reportes oficiales FSSA 106.")

    c_p1, c_p2 = st.columns([1, 1])
    with c_p1:
        st.markdown("### 📋 Datos Personales")
        st.markdown(f"**Nombre:** `{current_user['name']}`")
        st.markdown(f"**Correo:** `{current_user['email']}`")
        st.markdown(f"**Rol:** `{ROLE_NAMES.get(current_user['role'], current_user['role'])}`")
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

    # --- CAMBIO DE CONTRASEÑA POR EL USUARIO ---
    st.markdown("---")
    st.markdown("### 🔒 Cambiar Mi Contraseña")
    st.caption("Actualizá tu clave de acceso al sistema cuando lo desees.")
    with st.form("form_change_password"):
        col_pwd1, col_pwd2, col_pwd3 = st.columns(3)
        with col_pwd1:
            old_pwd = st.text_input("Contraseña Actual *", type="password", placeholder="••••••••")
        with col_pwd2:
            new_pwd = st.text_input("Nueva Contraseña *", type="password", placeholder="••••••••")
        with col_pwd3:
            confirm_pwd = st.text_input("Confirmar Nueva Contraseña *", type="password", placeholder="••••••••")

        submit_pwd = st.form_submit_button("Actualizar Mi Contraseña", type="primary", use_container_width=True)
        if submit_pwd:
            if not old_pwd or not new_pwd or not confirm_pwd:
                st.error("Por favor complete todos los campos requeridos.")
            elif new_pwd != confirm_pwd:
                st.error("La nueva contraseña y su confirmación no coinciden.")
            elif len(new_pwd) < 4:
                st.error("La nueva contraseña debe tener al menos 4 caracteres.")
            else:
                ok, msg = db.update_user_password(current_user["id"], old_pwd, new_pwd)
                if ok:
                    st.success("¡Tu contraseña ha sido actualizada con éxito!")
                else:
                    st.error(f"Error: {msg}")


def render_admin_view(current_user: dict):
    db = get_db()
    st.markdown("## ⚙️ Panel de Administración")
    st.caption("Gestión integral de usuarios, roles, flota de vehículos y configuración de notificaciones Sullair Argentina.")

    tab_users, tab_vehicles, tab_emails = st.tabs([
        "👥 Gestión de Usuarios",
        "🚙 Gestión de Flota",
        "📧 Configuración de Correos y SMTP"
    ])

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

        # Modificar o Eliminar Vehículo existente
        if vehicles:
            st.markdown("---")
            st.markdown("### ✏️ Modificar o Eliminar Unidad de Flota")
            veh_manage_opts = [f"{v['interno']} - {v['patente']} ({v['marca']} {v.get('modelo', '')})" for v in vehicles]
            sel_vm_label = st.selectbox("Seleccionar Vehículo a Administrar", options=veh_manage_opts, key="admin_sel_veh")
            sel_vm_pat = sel_vm_label.split("-")[1].split("(")[0].strip()
            target_veh = next((v for v in vehicles if v["patente"] == sel_vm_pat), None)

            if target_veh:
                c_ev1, c_ev2, c_ev3 = st.columns(3)
                with c_ev1:
                    ev_interno = st.text_input("N° Interno", value=target_veh["interno"], key="ev_int")
                    ev_marca = st.text_input("Marca", value=target_veh["marca"], key="ev_mar")
                with c_ev2:
                    ev_patente = st.text_input("Patente", value=target_veh["patente"], key="ev_pat")
                    ev_modelo = st.text_input("Modelo", value=target_veh.get("modelo", ""), key="ev_mod")
                with c_ev3:
                    ev_km = st.number_input("Km Actual", value=int(target_veh.get("km_actual") or 0), step=100, key="ev_km")
                    ev_poliza = st.text_input("Póliza Seguro", value=target_veh.get("seguro_poliza", ""), key="ev_pol")

                col_vbtn1, col_vbtn2 = st.columns([1, 1])
                with col_vbtn1:
                    if st.button("💾 Guardar Cambios de Unidad", key="btn_save_veh_edit", type="primary", use_container_width=True):
                        db.update_vehicle(target_veh["id"], {
                            "interno": ev_interno.strip(),
                            "patente": ev_patente.strip().upper(),
                            "marca": ev_marca.strip(),
                            "modelo": ev_modelo.strip(),
                            "km_actual": int(ev_km),
                            "seguro_poliza": ev_poliza.strip()
                        })
                        st.success(f"¡Vehículo {ev_interno} actualizado correctamente!")
                        st.rerun()

                with col_vbtn2:
                    if st.button("🗑️ Eliminar Unidad de Flota", key="btn_del_veh", type="secondary", use_container_width=True):
                        db.delete_vehicle(target_veh["id"])
                        st.warning(f"Vehículo {target_veh['interno']} ({target_veh['patente']}) eliminado de la base de datos.")
                        st.rerun()

    # --- TAB 3: CORREOS Y SERVIDOR SMTP ---
    with tab_emails:
        st.markdown("### 📧 Gestión de Notificaciones y Casilla de Envío")
        st.caption("Configurá los destinatarios de los reportes oficiales y la casilla institucional emisora de correos.")

        # 1. DESTINATARIOS
        st.markdown("---")
        st.markdown("#### 📬 1. Destinatarios de las Inspecciones FSSA 106")
        st.info(
            "ℹ️ Cada vez que se genera un reporte, se envía automáticamente a:\n"
            "- Todos los usuarios con rol **CASS** (`gestor_cass`).\n"
            "- El **usuario/inspector** que realizó y firmó el reporte.\n"
            "- Todos los **correos adicionales** registrados a continuación."
        )

        # Mostrar usuarios CASS actuales
        all_u = db.get_all_users()
        cass_users = [u for u in all_u if u.get("role") == "gestor_cass"]
        if cass_users:
            st.markdown("**Perfiles CASS Activos (Receptores automáticos):**")
            cass_tags = " ".join([f"`{u['name']} ({u['email']})`" for u in cass_users])
            st.markdown(cass_tags)
        else:
            st.warning("⚠️ No hay usuarios registrados con el rol CASS actualmente. Podés crearlos en la pestaña 'Gestión de Usuarios'.")

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        st.markdown("**Correos Adicionales Registrados:**")
        extra_emails = db.get_extra_recipients()
        
        if extra_emails:
            for em in extra_emails:
                c_em1, c_em2 = st.columns([4, 1])
                with c_em1:
                    st.markdown(f"✉️ `{em}`")
                with c_em2:
                    if st.button("🗑️ Eliminar", key=f"del_extra_mail_{em}", use_container_width=True):
                        db.remove_extra_recipient(em)
                        st.success(f"Correo {em} eliminado.")
                        st.rerun()
        else:
            st.caption("No hay correos adicionales cargados.")

        # Formulario para agregar correo adicional
        with st.form("form_add_extra_email"):
            c_ne1, c_ne2 = st.columns([3, 1])
            with c_ne1:
                new_extra_mail = st.text_input("Agregar Nuevo Correo Adicional", placeholder="ejemplo@sullair.com.ar")
            with c_ne2:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                submit_add_mail = st.form_submit_button("➕ Agregar", type="primary", use_container_width=True)
            
            if submit_add_mail:
                if not new_extra_mail or "@" not in new_extra_mail:
                    st.error("Ingrese una dirección de correo electrónico válida.")
                else:
                    if db.add_extra_recipient(new_extra_mail):
                        st.success(f"¡Correo '{new_extra_mail}' agregado a los destinatarios!")
                        st.rerun()
                    else:
                        st.warning("El correo ya se encuentra en la lista de destinatarios adicionales.")

        # 2. CASILLA DE ENVÍO / SMTP
        st.markdown("---")
        st.markdown("#### ⚙️ 2. Casilla de Envío de Mails (Servidor SMTP)")
        st.caption("Configure los datos de la casilla institucional que despachará los avisos y reportes en PDF adjunto.")

        curr_smtp = db.get_smtp_config()

        with st.form("form_smtp_config"):
            c_s1, c_s2 = st.columns(2)
            with c_s1:
                smtp_serv = st.text_input("Servidor SMTP *", value=curr_smtp.get("smtp_server", ""), placeholder="Ej: smtp.office365.com / smtp-mail.outlook.com")
                smtp_port = st.number_input("Puerto SMTP *", value=int(curr_smtp.get("smtp_port") or 587), min_value=1, max_value=65535, step=1)
            with c_s2:
                smtp_user = st.text_input("Casilla / Usuario SMTP *", value=curr_smtp.get("smtp_user", ""), placeholder="Ej: test@sullair.com.ar / fcendra@sullair.com.ar")
                smtp_pass = st.text_input("Contraseña de Aplicación / SMTP *", value=curr_smtp.get("smtp_password", ""), type="password", placeholder="••••••••••••")

            smtp_tls = st.checkbox("Habilitar STARTTLS / Seguridad", value=curr_smtp.get("use_tls", True))

            submit_smtp = st.form_submit_button("💾 Guardar Configuración SMTP", type="primary", use_container_width=True)
            if submit_smtp:
                if not smtp_serv or not smtp_user or not smtp_pass:
                    st.error("Por favor complete los campos obligatorios: Servidor SMTP, Usuario y Contraseña.")
                else:
                    db.set_smtp_config({
                        "smtp_server": smtp_serv.strip(),
                        "smtp_port": int(smtp_port),
                        "smtp_user": smtp_user.strip(),
                        "smtp_password": smtp_pass.strip(),
                        "use_tls": smtp_tls
                    })
                    st.success("¡Configuración de casilla SMTP guardada exitosamente en la base de datos Supabase!")
                    st.rerun()

        # Prueba de conexión SMTP
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        with st.expander("🧪 Probar Envío de Correo de Prueba"):
            c_t1, c_t2 = st.columns([3, 1])
            with c_t1:
                test_dest_email = st.text_input("Enviar correo de prueba a:", value=current_user.get("email", ""), key="test_dest_mail")
            with c_t2:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                btn_test_smtp = st.button("🚀 Enviar Prueba", key="btn_run_test_smtp", use_container_width=True)

            if btn_test_smtp:
                if not test_dest_email or "@" not in test_dest_email:
                    st.error("Ingrese una dirección de correo válida para la prueba.")
                else:
                    with st.spinner("Conectando con el servidor SMTP y enviando correo..."):
                        ok, msg_res = send_test_email(test_dest_email.strip())
                        if ok:
                            st.success(msg_res)
                        else:
                            st.error(msg_res)
