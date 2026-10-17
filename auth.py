import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Reemplaza la URL de ejemplo por el enlace completo de tu planilla de Google Sheets
URL_SHEET = "https://docs.google.com/spreadsheets/d/1kLefq4buQ1hkNfi0WDxrbNKqcDWIL4mdj98Awfcaf64/edit?gid=0#gid=0"

def obtener_conexion():
    return st.connection("gsheets", type=GSheetsConnection, spreadsheet=URL_SHEET)

def cargar_usuarios():
    conn = obtener_conexion()
    df = conn.read(worksheet="Usuarios", ttl=0)
    return df

def verificar_autenticacion():
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
                    try:
                        df_usuarios = cargar_usuarios()
                        usuario_match = df_usuarios[
                            (df_usuarios['usuario'].astype(str) == usuario_input) & 
                            (df_usuarios['password'].astype(str) == password_input)
                        ]
                        
                        if not usuario_match.empty:
                            st.session_state["autenticado"] = True
                            st.session_state["usuario_actual"] = usuario_input
                            st.session_state["rol_actual"] = usuario_match.iloc[0]["rol"]
                            st.success(f"¡Bienvenido {usuario_input}! Cargando panel...")
                            st.rerun()
                        else:
                            st.error("⚠️ Usuario o contraseña incorrectos.")
                    except Exception as e:
                        st.error(f"Error al conectar con la base de datos: {e}")
        st.stop()

def registrar_usuario(dni, apellido, nombre, nuevo_usuario, nueva_clave, nuevo_rol):
    try:
        conn = obtener_conexion()
        df_usuarios = cargar_usuarios()
        
        if str(nuevo_usuario) in df_usuarios['usuario'].astype(str).values:
            return False, "El nombre de usuario ya existe."
        
        nuevo_df = pd.DataFrame([{
            "DNI": dni,
            "apellido": apellido,
            "nombre": nombre,
            "usuario": nuevo_usuario,
            "password": nueva_clave,
            "rol": nuevo_rol
        }])
        
        df_actualizado = pd.concat([df_usuarios, nuevo_df], ignore_index=True)
        conn.update(worksheet="Usuarios", data=df_actualizado)
        return True, f"Usuario '{nuevo_usuario}' registrado con éxito."
    except Exception as e:
        return False, f"Error al guardar en Google Sheets: {e}"