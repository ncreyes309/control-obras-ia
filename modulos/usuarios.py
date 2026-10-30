import sys
import os
import streamlit as st
import modulos.datos as datos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import auth


def mostrar_modulo():
    st.title("👤 Alta y Gestión de empleados (usuarios)")
    st.markdown("Módulo exclusivo para Administradores de Constructora Reyes Juan SRL.")

    if st.session_state.get("rol_actual") != "Administrador":
        st.error("⛔ Solo el Administrador puede acceder a este módulo.")
        return

    empresa_id = st.session_state.get("empresa_id", 1)

    # Mensaje que sobrevive al st.rerun()
    flash = st.session_state.pop("_flash_usuarios", None)
    if flash:
        st.success(flash)

    # ---------- Alta ----------
    with st.form("form_alta_usuario", clear_on_submit=True):
        st.subheader("➕ Registrar Nuevo Empleado / Usuario")
        col1, col2 = st.columns(2)
        with col1:
            dni_val = st.text_input("DNI (Sin puntos ni guiones)*")
            nombre_val = st.text_input("Nombre*")
            apellido_val = st.text_input("Apellido*")
            email_val = st.text_input("Email institucional")
        with col2:
            nuevo_user = st.text_input("Nombre de Usuario (ej. pedro.perez)*")
            nuevo_pass = st.text_input("Contraseña temporal*", type="password")
            nuevo_rol = st.selectbox("Rol / Nivel de Permisos", auth.ROLES)

        btn_crear = st.form_submit_button("💾 Guardar Usuario en PostgreSQL")

        if btn_crear:
            campos_obligatorios = [dni_val, nombre_val, apellido_val, nuevo_user, nuevo_pass]
            ok_pass, msj_pass = auth.validar_password_nueva(nuevo_pass)
            if not all(str(c).strip() for c in campos_obligatorios):
                st.error("⚠️ Los campos marcados con * son obligatorios.")
            elif not ok_pass:
                st.error(f"⚠️ {msj_pass}")
            else:
                password_hash = auth.hashear_password(nuevo_pass)
                exito, msj = datos.crear_usuario(
                    empresa_id, dni_val.strip(), apellido_val.strip(), nombre_val.strip(),
                    email_val.strip(), nuevo_user.strip(), password_hash, nuevo_rol
                )
                if exito:
                    st.session_state["_flash_usuarios"] = f"✅ {msj} Deberá cambiar la contraseña al ingresar."
                    st.rerun()
                else:
                    st.error(f"⚠️ {msj}")

    # ---------- Listado ----------
    st.markdown("---")
    st.subheader("📋 Usuarios registrados en PostgreSQL")
    try:
        df_u = datos.cargar_todos_usuarios(empresa_id)
    except Exception as e:
        st.error(f"No se pudieron cargar los usuarios: {e}")
        return

    st.dataframe(df_u[["DNI", "apellido", "nombre", "usuario", "email", "rol", "activo"]],
                 use_container_width=True, hide_index=True)

    if df_u.empty:
        return

    # ---------- Administrar un usuario existente ----------
    st.markdown("---")
    st.subheader("🛠️ Administrar usuario existente")
    usuario_sel = st.selectbox("Usuario", df_u["usuario"].tolist(), key="usr_admin_sel")
    fila = df_u[df_u["usuario"] == usuario_sel].iloc[0]
    # Un valor vacío (None) cuenta como activo, igual que en el login
    esta_activo = str(fila["activo"]).strip().lower() not in ("no", "false", "0", "inactivo")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"Estado actual: **{'Activo' if esta_activo else 'Inactivo'}**")
        etiqueta = "🚫 Desactivar usuario" if esta_activo else "✅ Activar usuario"
        if st.button(etiqueta, key="usr_toggle_btn"):
            ok, msj = auth.set_activo(usuario_sel, not esta_activo)
            if ok:
                st.session_state["_flash_usuarios"] = f"✅ {msj}"
                st.rerun()
            else:
                st.error(f"⚠️ {msj}")
    with col2:
        temporal = st.text_input("Nueva contraseña temporal", type="password", key="usr_reset_pass")
        if st.button("🔑 Resetear contraseña", key="usr_reset_btn"):
            ok, msj = auth.resetear_password(usuario_sel, temporal)
            if ok:
                st.session_state["_flash_usuarios"] = f"✅ {msj}"
                st.rerun()
            else:
                st.error(f"⚠️ {msj}")
