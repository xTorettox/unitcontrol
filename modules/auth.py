import streamlit as st
from database.connection import get_db

ROLE_NAMES = {
    "admin": "Administrador General",
    "gestor_cass": "Gestor CASS / Mantenimiento",
    "responsable_flota": "Responsable de Flota",
    "comercial": "Usuario Comercial / Inspector"
}

def init_auth_state():
    if "user" not in st.session_state:
        st.session_state["user"] = None
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

def login_user(email: str, password: str) -> bool:
    db = get_db()
    user = db.get_user_by_email(email)
    if user and db.verify_password(password, user["password_hash"]):
        st.session_state["user"] = user
        st.session_state["authenticated"] = True
        return True
    return False

def logout_user():
    st.session_state["user"] = None
    st.session_state["authenticated"] = False
    st.rerun()

def get_current_user():
    return st.session_state.get("user")

def is_authenticated():
    return st.session_state.get("authenticated", False)

def has_role(allowed_roles: list) -> bool:
    user = get_current_user()
    if not user:
        return False
    return user.get("role") in allowed_roles
