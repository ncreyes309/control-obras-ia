import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
URL_SHEET = "https://docs.google.com/spreadsheets/d/1kLefq4buQ1hkNfi0WDxrbNKqcDWIL4mdj98Awfcaf64/edit?usp=drive_link"

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
        # Se le pasa el parámetro spreadsheet directamente al leer los datos
        df = conn.read(spreadsheet=URL_SHEET, worksheet="Usuarios", ttl=0)
        return df
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        return pd.DataFrame()

def autenticar_usuario(usuario, contrasena):
    """
    Verifica si las credenciales ingresadas coinciden con algún registro.
    """
    df = cargar_usuarios()
    if df.empty:
        return None
    
    # Normalización de los nombres de columnas (minusculas y sin espacios)
    df.columns = [str(col).strip().lower() for col in df.columns]
    
    # Búsqueda del usuario y contraseña
    usuario_ingresado = str(usuario).strip()
    contrasena_ingresada = str(contrasena).strip()
    
    # Filtrar credenciales en el DataFrame
    coincidencias = df[(df['usuario'].astype(str).str.strip() == usuario_ingresado) & 
                       (df['password'].astype(str).str.strip() == contrasena_ingresada)]
    
    if not coincidencias.empty:
        # Retorna la primera fila como diccionario si la autenticación es exitosa
        return coincidencias.iloc[0].to_dict()
    
    return None