import streamlit as st
import auth

# Importamos los submódulos de la carpeta 'modulos'
from modulos import usuarios, reportes, resumen, horas

# Configuración inicial de la página
st.set_page_config(
    page_title="Control de Obras | Constructora Reyes Juan SRL",
    page_icon="🏗️",
    layout="wide",
)

# 1. Verificación de acceso
autenticado = auth.verificar_autenticacion()

if not autenticado:
    st.stop()  # Detiene la ejecución si no hay sesión activa

rol = st.session_state["rol_actual"]

# 2. Barra lateral de navegación
st.sidebar.title("🏗️ Reyes Juan SRL")
st.sidebar.caption(f"Usuario: **{st.session_state['usuario_actual']}** ({rol})")

# Menú por rol
opciones_menu = ["🕒 Carga de Horas", "⏱️ Carga de Horas y Reportes IA"]

if rol in ("Administrador", "Gerente"):
    opciones_menu.append("📊 Resumen y Control")

if rol == "Administrador":
    opciones_menu.append("👤 Gestión de Usuarios")

menu = st.sidebar.radio("Navegación", opciones_menu)

st.sidebar.markdown("---")

# Herramienta de administrador: hashear contraseñas que sigan en texto plano
if rol == "Administrador":
    if st.sidebar.button("🔒 Proteger contraseñas"):
        try:
            n = auth.migrar_passwords()
            st.sidebar.success(f"Contraseñas protegidas: {n}")
        except Exception as e:
            st.sidebar.error(f"Error: {e}")

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.session_state["usuario_actual"] = ""
    st.session_state["rol_actual"] = ""
    st.rerun()

# 3. Enrutamiento dinámico según la opción seleccionada
if menu == "🕒 Carga de Horas":
    horas.mostrar_modulo()

elif menu == "⏱️ Carga de Horas y Reportes IA":
    reportes.mostrar_modulo()

elif menu == "📊 Resumen y Control":
    resumen.mostrar_modulo()

elif menu == "👤 Gestión de Usuarios":
    usuarios.mostrar_modulo()
