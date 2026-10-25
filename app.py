import streamlit as st
import auth

# Importamos los submódulos de la carpeta 'modulos'
from modulos import avances, horas, reportes, resumen, usuarios

# Configuración inicial de la página
st.set_page_config(
    page_title="Control de Obras | Constructora Reyes Juan SRL",
    page_icon="🏗️",
    layout="wide",
)

# 1. Verificación de acceso (incluye el cambio obligatorio de contraseña temporal)
if not auth.verificar_autenticacion():
    st.stop()

rol = st.session_state["rol_actual"]

# 2. Permisos por rol: menú -> (módulo, roles habilitados)
ROLES_CARGA = ("Administrador", "Director de Obras", "Administrativo General", "Capataz")
ROLES_GESTION = ("Administrador", "Gerente", "Director de Obras")

PAGINAS = {
    "🕒 Carga de Horas": (horas.mostrar_modulo, ROLES_CARGA),
    "📝 Avances y Novedades": (avances.mostrar_modulo, ROLES_CARGA),
    "📨 Reporte Diario": (reportes.mostrar_modulo, ROLES_GESTION),
    "📊 Resumen y Control": (resumen.mostrar_modulo, ROLES_GESTION),
    "👤 Gestión de Usuarios": (usuarios.mostrar_modulo, ("Administrador",)),
}
opciones_menu = [nombre for nombre, (_, roles) in PAGINAS.items() if rol in roles]

# 3. Barra lateral
st.sidebar.title("🏗️ Reyes Juan SRL")
st.sidebar.caption(f"Usuario: **{st.session_state['usuario_actual']}** ({rol})")

menu = st.sidebar.radio("Navegación", opciones_menu) if opciones_menu else None

st.sidebar.markdown("---")

with st.sidebar.expander("🔑 Mi cuenta"):
    #auth.formulario_cambiar_password("cambio_sidebar")
    auth.formulario_cambiar_password(clave="cambio_sidebar")
# Herramienta de administrador: guardar con hash contraseñas que sigan en texto plano
if rol == "Administrador":
    if st.sidebar.button("🔒 Proteger contraseñas"):
        try:
            n = auth.migrar_passwords()
            st.sidebar.success(f"Contraseñas protegidas: {n}")
        except Exception as e:
            st.sidebar.error(f"Error: {e}")

if st.sidebar.button("🚪 Cerrar Sesión"):
    auth.cerrar_sesion()
    st.rerun()

# 4. Enrutamiento
if menu is None:
    st.info("Tu rol todavía no tiene módulos habilitados. Consultá con el administrador.")
else:
    PAGINAS[menu][0]()
