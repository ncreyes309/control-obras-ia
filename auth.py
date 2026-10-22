import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
#URL_SHEET = "https://docs.google.com/spreadsheets/d/1kLefq4buQ1hkNfi0WDxrbNKqcDWIL4mdj98Awfcaf64/edit?usp=drive_link"
URL_SHEET = "https://docs.google.com/spreadsheets/d/1Dvb10YHHL6XBO9ULn0Pc9DQ3QgaGhmqgiRfV6abxc74/edit?usp=sharing"
def obtener_conexion():
    """
    Inicializa la conexión con Google Sheets.
    """
    return st.connection("gsheets", type=GSheetsConnection)

def cargar_usuarios():
    """
    Lee la pestaña 'Usuarios' de la planilla de Google Sheets.
    """
    try:
        conn = obtener_conexion()
        # Intentamos leer la pestaña 'Usuarios'
        df = conn.read(spreadsheet=URL_SHEET, worksheet="Usuarios", ttl=0)
        return df
    except Exception as e:
        # Si falla, intentamos leer sin especificar worksheet por si la hoja principal es la de usuarios
        try:
            conn = obtener_conexion()
            df = conn.read(spreadsheet=URL_SHEET, ttl=0)
            return df
        except Exception as e2:
            st.error(f"Error al conectar con la base de datos: {e2}")
            return pd.DataFrame()

def autenticar_usuario(usuario, contrasena):
    """
    Verifica si las credenciales ingresadas coinciden con algún registro.
    """
    df = cargar_usuarios()
    if df.empty:
        return None
    
    # Normalización de los nombres de columnas
    df.columns = [str(col).strip().lower() for col in df.columns]
    
    usuario_ingresado = str(usuario).strip()
    contrasena_ingresada = str(contrasena).strip()
    
    coincidencias = df[(df['usuario'].astype(str).str.strip() == usuario_ingresado) & 
                       (df['password'].astype(str).str.strip() == contrasena_ingresada)]
    
    if not coincidencias.empty:
        return coincidencias.iloc[0].to_dict()
    
    return None

def verificar_autenticacion():
    """
    Gestiona la visualización del formulario de login y la sesión en Streamlit.
    """
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
        st.session_state["usuario_actual"] = None
        st.session_state["rol_actual"] = None

    if not st.session_state["autenticado"]:
        st.subheader("Acceso al Sistema de Control")
        
        with st.form("form_login"):
            usuario_input = st.text_input("Usuario")
            password_input = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Ingresar")
            
            if submit:
                user_data = autenticar_usuario(usuario_input, password_input)
                if user_data:
                    st.session_state["autenticado"] = True
                    st.session_state["usuario_actual"] = user_data.get("usuario")
                    st.session_state["rol_actual"] = user_data.get("rol", "usuario")
                    st.success("¡Acceso exitoso!")
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")
        return False
    
    return True