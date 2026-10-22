import streamlit as st
import auth

# Importamos los submódulos de la carpeta 'modulos'
from modulos import usuarios, reportes, resumen

# Configuración inicial de la página
st.set_page_config(
    page_title="Control de Obras | Constructora Reyes Juan SRL", 
    page_icon="🏗️", 
    layout="wide"
)

# 1. Verificación de acceso
autenticado = auth.verificar_autenticacion()

if not autenticado:
    st.stop()  # Detiene la ejecución si no hay sesión activa

# 2. Barra lateral de navegación
st.sidebar.title("🏗️ Reyes Juan SRL")
st.sidebar.caption(f"Usuario: **{st.session_state['usuario_actual']}** ({st.session_state['rol_actual']})")

opciones_menu = ["⏱️ Carga de Horas y Reportes IA", "📊 Resumen y Control"]

if st.session_state["rol_actual"] == "Administrador":
    opciones_menu.append("👤 Gestión de Usuarios")

menu = st.sidebar.radio("Navegación", opciones_menu)

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.session_state["usuario_actual"] = ""
    st.session_state["rol_actual"] = ""
    st.rerun()

# 3. Enrutamiento dinámico según la opción seleccionada
if menu == "⏱️ Carga de Horas y Reportes IA":
    reportes.mostrar_modulo()

elif menu == "📊 Resumen y Control":
    resumen.mostrar_modulo()

elif menu == "👤 Gestión de Usuarios":
    usuarios.mostrar_modulo()