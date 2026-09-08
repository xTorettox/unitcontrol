import streamlit as st
import os
from PIL import Image

# Configuración de página
st.set_page_config(
    page_title="Sullair Argentina - Control de Vehículos",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="auto"
)

# Cargar estilos CSS personalizados
css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

from database.connection import get_db
from modules.auth import init_auth_state, login_user, logout_user, get_current_user, is_authenticated, ROLE_NAMES
from modules.checklist_view import render_checklist_view
from modules.dashboard_view import render_dashboard_view
from modules.history_view import render_history_view
from modules.admin_view import render_admin_view, render_profile_view


def render_login_screen():
    # Logo e Identidad Sullair
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo_sullair.png")
    c_l1, c_l2, c_l3 = st.columns([1, 2, 1])
    with c_l2:
        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)
        else:
            st.markdown("<h1 style='text-align: center; color: #00853E;'>SULLAIR ARGENTINA</h1>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 25px;">
                <h3 style="margin: 0; color: #1F2937;">Control de Vehículos (FSSA 106)</h3>
                <p style="color: #6B7280; font-size: 0.95rem;">Sistema de inspección mensual y gestión de flota CASS</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.container():
            with st.form("login_form"):
                email_input = st.text_input("Correo electrónico corporativo", placeholder="usuario@sullair.com.ar")
                password_input = st.text_input("Contraseña", type="password", placeholder="••••••••")
                submit_login = st.form_submit_button("Ingresar al Sistema", type="primary", use_container_width=True)

                if submit_login:
                    if login_user(email_input, password_input):
                        st.success("¡Bienvenido!")
                        st.rerun()
                    else:
                        st.error("Credenciales incorrectas. Verifique su correo o contraseña.")

        # Acceso Rápido de Demostración para Pruebas
        with st.expander("🔑 Cuentas Preconfiguradas para Acceso Rápido", expanded=True):
            st.caption("Seleccioná un perfil para ingresar directamente:")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                if st.button("👑 Federico Cendra (Admin)", use_container_width=True):
                    login_user("fcendra@sullair.com.ar", "C4n1ch3r1426")
                    st.rerun()
                if st.button("🚙 Lucas Toto (Comercial)", use_container_width=True):
                    login_user("ltoto@sullair.com.ar", "esmeralda26")
                    st.rerun()
            with col_d2:
                if st.button("📊 Gestor CASS (Auditoría)", use_container_width=True):
                    login_user("cass@sullair.com.ar", "cass")
                    st.rerun()
                if st.button("⚙️ Administrador General", use_container_width=True):
                    login_user("admin@sullair.com.ar", "admin")
                    st.rerun()


def main():
    init_auth_state()

    if not is_authenticated():
        render_login_screen()
        return

    user = get_current_user()
    role = user.get("role", "comercial")

    # --- ENCABEZADO SUPERIOR ---
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo_sullair.png")
    c_h1, c_h2, c_h3 = st.columns([1, 2, 1])
    with c_h1:
        if os.path.exists(logo_path):
            st.image(logo_path, width=220)
    with c_h2:
        st.markdown(
            f"""
            <div style="text-align: center; padding-top: 5px;">
                <span style="font-size: 1.1rem; font-weight: 700; color: #005A2A;">Sistema de Control de Vehículos</span><br/>
                <span style="font-size: 0.85rem; color: #4B5563;">Usuario: <strong>{user['name']}</strong> ({ROLE_NAMES.get(role, role)})</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c_h3:
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            logout_user()

    st.markdown("---")

    # --- NAVEGACIÓN SEGÚN ROL ---
    if role == "comercial":
        nav_options = ["📋 Nueva Inspección", "📚 Mi Historial", "👤 Mi Perfil y Firma"]
    elif role in ["gestor_cass", "responsable_flota"]:
        nav_options = ["📊 Dashboard CASS", "📋 Cargar Inspección", "📚 Historial de Flota", "👤 Mi Perfil y Firma"]
    else:  # admin
        nav_options = ["📊 Dashboard CASS", "📋 Cargar Inspección", "📚 Historial de Flota", "⚙️ Administración", "👤 Mi Perfil y Firma"]

    # Barra lateral / Selector de vista
    with st.sidebar:
        st.markdown(f"### 📍 Navegación")
        selected_nav = st.radio("Secciones", options=nav_options, label_visibility="collapsed")
        
        st.markdown("---")
        st.markdown(f"**Conectado como:**")
        st.markdown(f"👤 `{user['name']}`")
        st.markdown(f"🏷️ `{ROLE_NAMES.get(role, role)}`")
        if user.get("assigned_vehicle_id"):
            db = get_db()
            v = db.get_vehicle_by_id(user["assigned_vehicle_id"])
            if v:
                st.markdown(f"🚙 Asignado: **{v['interno']}** ({v['patente']})")

    # --- RENDERIZADO DE VISTA SELECCIONADA ---
    if selected_nav in ["📋 Nueva Inspección", "📋 Cargar Inspección"]:
        render_checklist_view(user)
    elif selected_nav == "📊 Dashboard CASS":
        render_dashboard_view(user)
    elif selected_nav in ["📚 Mi Historial", "📚 Historial de Flota"]:
        render_history_view(user)
    elif selected_nav == "⚙️ Administración":
        render_admin_view(user)
    elif selected_nav == "👤 Mi Perfil y Firma":
        render_profile_view(user)


if __name__ == "__main__":
    main()
