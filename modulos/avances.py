from datetime import datetime

import pandas as pd
import streamlit as st

from modulos import datos


def mostrar_modulo():
    st.title("📝 Avances y Novedades de Obra")

    try:
        obras = datos.obras_activas()
    except Exception as e:
        st.error(f"No pude leer la hoja de Obras: {e}")
        return
    if obras.empty:
        st.warning("No hay obras activas cargadas.")
        return

    col1, col2 = st.columns(2)
    with col1:
        obra_nombre = st.selectbox("Obra", obras["nombre"].tolist())
    with col2:
        fecha = st.date_input("Fecha", value=datetime.now(datos.TZ).date(), format="DD/MM/YYYY")
    fecha_str = fecha.strftime("%Y-%m-%d")

    obra_row = obras[obras["nombre"] == obra_nombre].iloc[0]
    archivo = str(obra_row.get("archivo", "")).strip()
    if not archivo:
        st.error("Esta obra no tiene archivo asignado. Completá la columna 'archivo' en la hoja Obras.")
        return

    try:
        existentes = datos.leer_obra(archivo, datos.HOJA_AVANCES, datos.COLUMNAS_AVANCES)
    except Exception as e:
        st.error(f"No pude abrir el archivo de esta obra (¿está compartido con la cuenta de servicio y tiene la pestaña 'Avances'?): {e}")
        return

    previos = datos.num(existentes["avance_pct"]).dropna()
    ultimo = float(previos.iloc[-1]) if not previos.empty else 0.0
    st.caption(f"Último avance informado de esta obra: **{ultimo:g}%**")

    with st.form("form_avance", clear_on_submit=True):
        avance = st.number_input("Avance total de la obra (%)", 0.0, 100.0, ultimo, step=0.5)
        tarea = st.text_input("Tarea trabajada hoy", placeholder="Ej: Contrapiso planta baja")
        novedades = st.text_area(
            "Novedades",
            placeholder="Ej: Llovió medio día. Falta cemento para mañana. Vino el inspector municipal.",
        )
        enviado = st.form_submit_button("💾 Guardar avance", type="primary")

    if enviado:
        if not tarea.strip() and not novedades.strip():
            st.error("Cargá al menos la tarea o una novedad.")
            return
        if avance < ultimo:
            st.warning(f"El avance ({avance:g}%) es menor al último informado ({ultimo:g}%). Se guarda igual, revisá que sea correcto.")
        try:
            nuevo = pd.DataFrame([{
                "fecha": fecha_str,
                "avance_pct": float(avance),
                "tarea": tarea.strip(),
                "novedades": novedades.strip(),
                "cargado_por": st.session_state["usuario_actual"],
                "timestamp": datetime.now(datos.TZ).strftime("%Y-%m-%d %H:%M:%S"),
            }])
            total = pd.concat([existentes, nuevo], ignore_index=True)
            datos.escribir(archivo, datos.HOJA_AVANCES, total)
            st.success("Avance guardado.")
        except Exception as e:
            st.error(f"Error al guardar: {e}")

    with st.expander("Ver lo cargado ese día en esta obra"):
        d = existentes[datos.fecha_iso(existentes["fecha"]) == fecha_str]
        if d.empty:
            st.caption("Todavía no hay avances cargados para este día.")
        else:
            st.dataframe(d[["avance_pct", "tarea", "novedades", "cargado_por"]], hide_index=True, use_container_width=True)
