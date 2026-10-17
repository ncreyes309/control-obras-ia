import streamlit as st

# Base de datos temporal de usuarios con sus respectivos roles y permisos
USUARIOS = {
    "admin": {"password": "reyes2026", "rol": "Administrador"},
    "capataz": {"password": "obra2026", "rol": "Capataz"},
    "juan": {"password": "constructora123", "rol": "Capataz"}
}

def verificar_autenticacion():
    """Verifica si el usuario está autenticado y gestiona el formulario de login."""
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
    if "usuario_actual" not in st.session_state:
        st.session_state["usuario_actual"] = ""
    if "rol_actual" not in st.session_state:
        st.session_state["rol_actual"] = ""

    if not st.session_state["autenticado"]:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("🏗️ Constructora Reyes Juan SRL")
            st.subheader("Acceso al Sistema de Control")
            
            with st.form("form_login"):
                usuario_input = st.text_input("Usuario")
                password_input = st.text_input("Contraseña", type="password")
                submit_login = st.form_submit_button("Ingresar")

                if submit_login:
                    if usuario_input in USUARIOS and USUARIOS[usuario_input]["password"] == password_input:
                        st.session_state["autenticado"] = True
                        st.session_state["usuario_actual"] = usuario_input
                        st.session_state["rol_actual"] = USUARIOS[usuario_input]["rol"]
                        st.success(f"¡Bienvenido {usuario_input}! Cargando panel...")
                        st.rerun()
                    else:
                        st.error("⚠️ Usuario o contraseña incorrectos.")
        st.stop()

def registrar_usuario(nuevo_usuario, nueva_clave, nuevo_rol):
    """Permite al Administrador dar de alta un nuevo usuario en el diccionario."""
    if nuevo_usuario in USUARIOS:
        return False, "El nombre de usuario ya existe."
    
    USUARIOS[nuevo_usuario] = {"password": nueva_clave, "rol": nuevo_rol}
    return True, f"Usuario '{nuevo_usuario}' registrado con éxito como {nuevo_rol}."