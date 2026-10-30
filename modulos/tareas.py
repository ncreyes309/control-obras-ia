import streamlit as st
import modulos.datos as datos

ESTADOS_TAREA = ["Pendiente", "En curso", "Finalizada"]
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
        df_obras = datos.cargar_todas_obras(empresa_id)
        df_tareas = datos.cargar_tareas(empresa_id)
    except Exception as e:
        st.error(f"No se pudieron cargar los datos: {e}")
        return

    if df_obras.empty:
        st.info("Primero tenés que registrar al menos una obra en el módulo 🏗️ Obras.")
        return

    # ---------- Alta ----------
    obras_opc = {f"{r.nombre_obra} (#{r.id})": int(r.id) for r in df_obras.itertuples()}

    with st.form("form_alta_tarea", clear_on_submit=True):
        st.subheader("➕ Registrar Nueva Tarea")
        col1, col2 = st.columns(2)
        with col1:
            obra_sel = st.selectbox("Obra*", list(obras_opc.keys()))
            nombre_tarea = st.text_input("Nombre de la tarea* (ej. Colado de hormigón)")
        with col2:
            estado = st.selectbox("Estado inicial", ESTADOS_TAREA)
        descripcion = st.text_area("Descripción", height=100)
        guardar = st.form_submit_button("💾 Guardar Tarea")

        if guardar:
            nombre_tarea = nombre_tarea.strip()
            obra_id = obras_opc[obra_sel]
            duplicada = False
            if not df_tareas.empty:
                mismas = df_tareas[df_tareas["obra_id"] == obra_id]
                duplicada = nombre_tarea.lower() in mismas["nombre_tarea"].astype(str).str.strip().str.lower().tolist()
            if not nombre_tarea:
                st.error("⚠️ El nombre de la tarea es obligatorio.")
            elif duplicada:
                st.error(f"⚠️ La tarea '{nombre_tarea}' ya existe en esa obra.")
            else:
                ok, msj = datos.crear_tarea(empresa_id, nombre_tarea, descripcion.strip(), obra_id, estado)
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

    filtro = st.selectbox("Filtrar por obra", ["Todas"] + list(obras_opc.keys()), key="tarea_filtro_obra")
    df_ver = df_tareas if filtro == "Todas" else df_tareas[df_tareas["obra_id"] == obras_opc[filtro]]
    st.dataframe(df_ver[["id", "obra", "nombre_tarea", "descripcion", "estado"]],
                 use_container_width=True, hide_index=True)

    if df_ver.empty:
        return

    # ---------- Edición ----------
    st.markdown("---")
    st.subheader("✏️ Editar una tarea")
    opciones = {f"{r.obra} - {r.nombre_tarea} (#{r.id})": r for r in df_ver.itertuples()}
    etiqueta = st.selectbox("Tarea", list(opciones.keys()), key="tarea_edit_sel")
    fila = opciones[etiqueta]
    estado_actual = str(fila.estado or "")
    idx_estado = ESTADOS_TAREA.index(estado_actual) if estado_actual in ESTADOS_TAREA else 0

    # La key incluye el id para que los campos se refresquen al cambiar de tarea
    with st.form(f"form_edit_tarea_{fila.id}"):
        nuevo_nombre = st.text_input("Nombre", value=str(fila.nombre_tarea or ""))
        nueva_desc = st.text_area("Descripción", value=str(fila.descripcion or ""), height=100)
        nuevo_estado = st.selectbox("Estado", ESTADOS_TAREA, index=idx_estado)
        editar = st.form_submit_button("💾 Guardar cambios")

        if editar:
            if not nuevo_nombre.strip():
                st.error("⚠️ El nombre no puede quedar vacío.")
            else:
                ok, msj = datos.actualizar_tarea(fila.id, empresa_id, nuevo_nombre.strip(), nueva_desc.strip(), nuevo_estado)
                if ok:
                    st.session_state["_flash_tareas"] = f"✅ {msj}"
                    st.rerun()
                else:
                    st.error(f"⚠️ {msj}")
