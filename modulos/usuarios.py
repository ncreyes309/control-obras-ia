import streamlit as st
import auth

def mostrar_modulo():
    st.title("👤 Alta y Gestión de usuarios")
    st.markdown("Módulo exclusivo para Administradores de Constructora Reyes Juan SRL.")
    
    with st.form("form_alta_usuario"):
        st.subheader("➕ Registrar Nuevo usuario")
        col1, col2 = st.columns(2)
        with col1:
            dni_val = st.text_input("DNI")
            nombre_val = st.text_input("Nombre")
            nuevo_user = st.text_input("Usuario (ej. pedro.perez)")
        with col2:
            apellido_val = st.text_input("Apellido")
            nuevo_pass = st.text_input("Contraseña asignada", type="password")
            nuevo_rol = st.selectbox("Rol / Nivel de Permisos", ["Administrador", "Gerente", "Director de Obras", "Abogada", "Administrativo General", "Capataz"])
        
        btn_crear = st.form_submit_button("💾 Guardar Usuario en Google Sheets")
        
        if btn_crear:
            if not nuevo_user.strip() or not nuevo_pass.strip() or not dni_val.strip():
                st.error("⚠️ DNI, usuario y contraseña son campos obligatorios.")
            else:
                exito, msj = auth.registrar_usuario(dni_val, apellido_val, nombre_val, nuevo_user, nuevo_pass, nuevo_rol)
                if exito:
                    st.success(f"✅ {msj}")
                    st.rerun()
                else:
                    st.error(f"⚠️ {msj}")

    st.markdown("---")
    st.subheader("📋 usuarios Registrados en Google Sheets")
    try:
        df_u = auth.cargar_usuarios()
        st.dataframe(df_u[["DNI", "apellido", "nombre", "usuario", "rol"]], use_container_width=True)
    except Exception as e:
        st.error(f"No se pudieron cargar los usuarios: {e}")