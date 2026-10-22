import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

def cargar_usuarios():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Usuarios", ttl=0)
    return df

def verificar_autenticacion():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
        st.session_state["usuario_actual"] = ""
        st.session_state["rol_actual"] = ""

    if not st.session_state["autenticado"]:
        st.subheader("🔐 Acceso al Sistema de Control")
        with st.form("form_login"):
            usuario_input = st.text_input("Usuario")
            password_input = st.text_input("Contraseña", type="password")
            submit_login = st.form_submit_button("Ingresar")

            if submit_login:
                try:
                    df_usuarios = cargar_usuarios()
                    df_usuarios.columns = df_usuarios.columns.str.strip().str.lower()
                    
                    usuario_match = df_usuarios[df_usuarios["usuario"] == usuario_input]
                    
                    if not usuario_match.empty:
                        pass_real = str(usuario_match.iloc[0]["password"])
                        if pass_real == password_input:
                            st.session_state["autenticado"] = True
                            st.session_state["usuario_actual"] = usuario_match.iloc[0]["usuario"]
                            st.session_state["rol_actual"] = usuario_match.iloc[0]["rol"]
                            st.success("¡Acceso exitoso!")
                            st.rerun()
                        else:
                            st.error("Contraseña incorrecta.")
                    else:
                        st.error("El usuario no existe.")
                except Exception as e:
                    st.error(f"Error al conectar con la base de datos de usuarios: {e}")
        return False
    return True

def registrar_usuario(dni, apellido, nombre, usuario, password, rol):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_actual = conn.read(worksheet="Usuarios", ttl=0)
        
        if not df_actual[df_actual["usuario"] == usuario].empty:
            return False, "El nombre de usuario ya está registrado."
        
        nuevo_registro = pd.DataFrame([{
            "DNI": dni,
            "apellido": apellido,
            "nombre": nombre,
            "usuario": usuario,
            "password": password,
            "rol": rol
        }])
        
        df_actualizado = pd.concat([df_actual, nuevo_registro], ignore_index=True)
        conn.update(worksheet="Usuarios", data=df_actualizado)
        return True, "Usuario registrado con éxito en Google Sheets."
    except Exception as e:
        return False, str(e)