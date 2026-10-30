import streamlit as st
import modulos.datos as datos

ROLES_PERMITIDOS = ["Administrador", "Gerente", "Director de Obras"]


def mostrar_modulo():
    st.title("🧱 Gestión de Tareas")

    if st.session_state.get("rol_actual") not in ROLES_PERMITIDOS:
        st.error("⛔ No tenés permisos para ver este módulo.")
        return

    empresa_id = st.session_state.get("empresa_id", 1)

    # Mensaje que sobrevive al st.rerun()
    flash = st.session_state.pop("_flash_tareas", None)
    if flash:
        st.success(flash)

    try:
        df_tareas = datos.cargar_tareas(empresa_id)
    except Exception as e:
        st.error(f"No se pudieron cargar las tareas: {e}")
        return

    # ---------- Alta ----------
    with st.form("form_alta_tarea", clear_on_submit=True):
        st.subheader("➕ Registrar Nueva Tarea")
        nombre_tarea = st.text_input("Nombre de la tarea* (ej. Colado de hormigón)")
        descripcion = st.text_area("Descripción", height=100)
        guardar = st.form_submit_button("💾 Guardar Tarea")

        if guardar:
            nombre_tarea = nombre_tarea.strip()
            existentes = df_tareas["nombre_tarea"].astype(str).str.strip().str.lower().tolist() if not df_tareas.empty else []
            if not nombre_tarea:
                st.error("⚠️ El nombre de la tarea es obligatorio.")
            elif nombre_tarea.lower() in existentes:
                st.error(f"⚠️ La tarea '{nombre_tarea}' ya existe.")
            else:
                ok, msj = datos.crear_tarea(empresa_id, nombre_tarea, descripcion.strip())
                if ok:
                    st.session_state["_flash_tareas"] = f"✅ {msj}"
                    st.rerun()
                else:
                    st.error(f"⚠️ {msj}")

    # ---------- Listado ----------
    st.markdown("---")
    st.subheader("📋 Tareas registradas")
    if df_tareas.empty:
        st.info("Todavía no hay tareas cargadas.")
        return
    st.dataframe(df_tareas, use_container_width=True, hide_index=True)

    # ---------- Edición ----------
    st.markdown("---")
    st.subheader("✏️ Editar una tarea")
    opciones = {f"{r.nombre_tarea} (#{r.id})": r for r in df_tareas.itertuples()}
    etiqueta = st.selectbox("Tarea", list(opciones.keys()), key="tarea_edit_sel")
    fila = opciones[etiqueta]

    # La key incluye el id para que los campos se refresquen al cambiar de tarea
    with st.form(f"form_edit_tarea_{fila.id}"):
        nuevo_nombre = st.text_input("Nombre", value=str(fila.nombre_tarea or ""))
        nueva_desc = st.text_area("Descripción", value=str(fila.descripcion or ""), height=100)
        editar = st.form_submit_button("💾 Guardar cambios")

        if editar:
            if not nuevo_nombre.strip():
                st.error("⚠️ El nombre no puede quedar vacío.")
            else:
                ok, msj = datos.actualizar_tarea(fila.id, empresa_id, nuevo_nombre.strip(), nueva_desc.strip())
                if ok:
                    st.session_state["_flash_tareas"] = f"✅ {msj}"
                    st.rerun()
                else:
                    st.error(f"⚠️ {msj}")
