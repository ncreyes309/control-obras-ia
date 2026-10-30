import streamlit as st
import modulos.datos as datos

def mostrar_modulo():
    st.title("🛠️ Alta y Gestión de Tareas")
    st.markdown("Gestione los tipos de tareas disponibles para el sistema.")

    empresa_id = 1 # Para pruebas. En producción usar st.session_state["usuario_info"]["empresa_id"]

    with st.form("form_alta_tarea"):
        st.subheader("➕ Registrar Nueva Tarea / Categoría")
        col1, col2 = st.columns(2)
        with col1:
            nombre_tarea = st.text_input("Nombre de la Tarea* (ej. Encofrado)")
        with col2:
            descripcion = st.text_area("Descripción (ej. Preparación de estructura de madera)")
        
        btn_crear = st.form_submit_button("💾 Guardar Tarea en PostgreSQL")
        
        if btn_crear:
            if not nombre_tarea.strip():
                st.error("⚠️ El nombre de la tarea es obligatorio.")
            else:
                exito, msj = datos.crear_tarea(empresa_id, nombre_tarea, descripcion)
                if exito:
                    st.success(f"✅ {msj}")
                    st.rerun()
                else:
                    st.error(f"⚠️ {msj}")

    st.markdown("---")
    st.subheader("📋 Catálogo de Tareas en PostgreSQL")
    try:
        df_t = datos.cargar_tareas(empresa_id)
        st.dataframe(df_t[["nombre_tarea", "descripcion"]], use_container_width=True)
    except Exception as e:
        st.error(f"No se pudieron cargar las tareas: {e}")