import streamlit as st
import modulos.datos as datos

def mostrar_modulo():
    st.title("🏗️ Alta y Gestión de Obras")
    
    empresa_id = 1 # Para pruebas. En producción usar st.session_state["usuario_info"]["empresa_id"]

    with st.form("form_alta_obra"):
        st.subheader("➕ Registrar Nueva Obra")
        col1, col2 = st.columns(2)
        with col1:
            nombre_obra = st.text_input("Nombre de la Obra*")
            ubicacion = st.text_input("Ubicación (ej. Ciudad, Dirección)")
        with col2:
            estado = st.selectbox("Estado de la Obra", ["activa", "en curso", "finalizada", "pausada"])
        
        btn_crear = st.form_submit_button("💾 Guardar Obra en PostgreSQL")
        
        if btn_crear:
            if not nombre_obra.strip():
                st.error("⚠️ El nombre de la obra es obligatorio.")
            else:
                exito, msj = datos.crear_obra(empresa_id, nombre_obra, ubicacion, estado)
                if exito:
                    st.success(f"✅ {msj}")
                    st.rerun()
                else:
                    st.error(f"⚠️ {msj}")

    st.markdown("---")
    st.subheader("📋 Catálogo de Obras en PostgreSQL")
    try:
        df_o = datos.cargar_todas_obras(empresa_id)
        st.dataframe(df_o[["nombre_obra", "ubicacion", "estado", "fecha_creacion"]], use_container_width=True)
    except Exception as e:
        st.error(f"No se pudieron cargar las obras: {e}")