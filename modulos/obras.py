import streamlit as st
import modulos.datos as datos

ESTADOS = ["Activa", "En curso", "Pausada", "Finalizada"]
ROLES_PERMITIDOS = ["Administrador", "Gerente", "Director de Obras"]


def mostrar_modulo():
    st.title("🏗️ Gestión de Obras")

    if st.session_state.get("rol_actual") not in ROLES_PERMITIDOS:
        st.error("⛔ No tenés permisos para ver este módulo.")
        return

    empresa_id = datos.empresa_actual()

    # Mensaje que sobrevive al st.rerun()
    flash = st.session_state.pop("_flash_obras", None)
    if flash:
        st.success(flash)

    try:
        df_obras = datos.cargar_todas_obras(empresa_id)
    except Exception as e:
        st.error(f"No se pudieron cargar las obras: {e}")
        return

    # ---------- Alta ----------
    with st.form("form_alta_obra", clear_on_submit=True):
        st.subheader("➕ Registrar Nueva Obra")
        col1, col2 = st.columns(2)
        with col1:
            nombre_obra = st.text_input("Nombre de la obra*")
            ubicacion = st.text_input("Ubicación / Dirección")
        with col2:
            estado = st.selectbox("Estado inicial", ESTADOS)
        guardar = st.form_submit_button("💾 Guardar Obra")

        if guardar:
            nombre_obra = nombre_obra.strip()
            existentes = df_obras["nombre_obra"].astype(str).str.strip().str.lower().tolist() if not df_obras.empty else []
            if not nombre_obra:
                st.error("⚠️ El nombre de la obra es obligatorio.")
            elif nombre_obra.lower() in existentes:
                st.error(f"⚠️ Ya existe una obra llamada '{nombre_obra}'.")
            else:
                ok, msj = datos.crear_obra(empresa_id, nombre_obra, ubicacion.strip(), estado)
                if ok:
                    st.session_state["_flash_obras"] = f"✅ {msj}"
                    st.rerun()
                else:
                    st.error(f"⚠️ {msj}")

    # ---------- Listado ----------
    st.markdown("---")
    st.subheader("📋 Obras registradas")
    if df_obras.empty:
        st.info("Todavía no hay obras cargadas.")
        return
    st.dataframe(df_obras, use_container_width=True, hide_index=True)

    # ---------- Cambio de estado ----------
    st.markdown("---")
    st.subheader("🔄 Cambiar estado de una obra")
    opciones = {f"{r.nombre_obra} (#{r.id}) - {r.estado}": int(r.id) for r in df_obras.itertuples()}
    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        etiqueta = st.selectbox("Obra", list(opciones.keys()), key="obra_estado_sel")
    with col2:
        nuevo_estado = st.selectbox("Nuevo estado", ESTADOS, key="obra_estado_nuevo")
    with col3:
        st.write("")
        st.write("")
        if st.button("Actualizar", key="obra_estado_btn"):
            ok, msj = datos.actualizar_estado_obra(opciones[etiqueta], empresa_id, nuevo_estado)
            if ok:
                st.session_state["_flash_obras"] = f"✅ {msj}"
                st.rerun()
            else:
                st.error(f"⚠️ {msj}")
    st.caption("Solo las obras en estado Activa o En curso aparecen en los selectores de carga de horas y avances.")
