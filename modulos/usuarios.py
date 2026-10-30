import streamlit as st
import modulos.datos as datos
import auth

def mostrar_modulo():
    st.title("👤 Alta y Gestión de empleados (usuarios)")
    st.markdown("Módulo exclusivo para Administradores de Constructora Reyes Juan SRL.")
    
    # Supongamos que ya tenemos un ID de empresa en el estado de la sesión, sino usamos 1
    empresa_id = 1 # Para pruebas. En producción usar st.session_state["usuario_info"]["empresa_id"]

    with st.form("form_alta_usuario"):
        st.subheader("➕ Registrar Nuevo Empleado / Usuario")
        col1, col2 = st.columns(2)
        with col1:
            dni_val = st.text_input("DNI (Sin puntos ni guiones)*")
            nombre_val = st.text_input("Nombre*")
            apellido_val = st.text_input("Apellido*")
            email_val = st.text_input("Email institucional")
        with col2:
            nuevo_user = st.text_input("Nombre de Usuario (ej. pedro.perez)*")
            nuevo_pass = st.text_input("Contraseña asignada*", type="password")
            nuevo_rol = st.selectbox("Rol / Nivel de Permisos", ["Administrador", "Gerente", "Director de Obras", "Abogada", "Administrativo General", "Capataz"])
        
        btn_crear = st.form_submit_button("💾 Guardar Usuario en PostgreSQL")
        
        if btn_crear:
            # Validaciones de campos obligatorios
            campos_obligatorios = [dni_val, nombre_val, apellido_val, nuevo_user, nuevo_pass]
            if not all(str(c).strip() for c in campos_obligatorios):
                st.error("⚠️ Los campos marcados con * son obligatorios.")
            else:
                # 1. Proteger la contraseña con bcrypt --se cambioo
                password_hash = auth.proteger_contraseña(nuevo_pass)
                
                # 2. Guardar en PostgreSQL
                exito, msj = datos.crear_usuario(empresa_id, dni_val, apellido_val, nombre_val, email_val, nuevo_user, password_hash, nuevo_rol)
                
                if exito:
                    st.success(f"✅ {msj}")
                    st.rerun()
                else:
                    st.error(f"⚠️ {msj}")

    st.markdown("---")
    st.subheader("📋 usuarios Registrados en PostgreSQL")
    try:
        df_u = datos.cargar_todos_usuarios(empresa_id)
        st.dataframe(df_u[["DNI", "apellido", "nombre", "usuario", "email", "rol", "activo"]], use_container_width=True)
    except Exception as e:
        st.error(f"No se pudieron cargar los usuarios: {e}")