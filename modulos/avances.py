from datetime import datetime

import pandas as pd
import streamlit as st

from modulos.horas import HOJA_OBRAS, TZ, _conn, _leer

HOJA_AVANCES = "Avances"  # fecha | obra_id | obra | avance_pct | tarea | novedades | cargado_por | timestamp
COLUMNAS_AVANCES = ["fecha", "obra_id", "obra", "avance_pct", "tarea", "novedades", "cargado_por", "timestamp"]


def mostrar_modulo():
    st.title("📝 Avances y Novedades de Obra")

    try:
        obras = _leer(HOJA_OBRAS, ttl=300)
    except Exception as e:
        st.error(f"No pude leer la hoja '{HOJA_OBRAS}': {e}")
        return

    if "estado" in obras.columns:
        obras = obras[obras["estado"].astype(str).str.strip().str.lower().isin(["activa", "en curso", "activo", ""])]
    if obras.empty:
        st.warning("No hay obras activas cargadas.")
        return

    try:
        existentes = _leer(HOJA_AVANCES, ttl=0)
    except Exception:
        existentes = pd.DataFrame(columns=COLUMNAS_AVANCES)

    col1, col2 = st.columns(2)
    with col1:
        obra_nombre = st.selectbox("Obra", obras["nombre"].tolist())
    with col2:
        fecha = st.date_input("Fecha", value=datetime.now(TZ).date(), format="DD/MM/YYYY")

    obra_row = obras[obras["nombre"] == obra_nombre].iloc[0]

    # Último avance conocido de la obra
    ultimo = 0.0
    if not existentes.empty and "avance_pct" in existentes.columns:
        previos = existentes[existentes["obra_id"].astype(str) == str(obra_row["obra_id"])]
        previos = pd.to_numeric(previos["avance_pct"], errors="coerce").dropna()
        if not previos.empty:
            ultimo = float(previos.iloc[-1])
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
                "fecha": fecha.strftime("%Y-%m-%d"),
                "obra_id": obra_row["obra_id"],
                "obra": obra_nombre,
                "avance_pct": float(avance),
                "tarea": tarea.strip(),
                "novedades": novedades.strip(),
                "cargado_por": st.session_state["usuario_actual"],
                "timestamp": datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
            }])
            total = pd.concat([existentes, nuevo], ignore_index=True)
            _conn().update(worksheet=HOJA_AVANCES, data=total)
            st.success("Avance guardado.")
        except Exception as e:
            st.error(f"Error al guardar: {e}")

    with st.expander("Ver lo cargado hoy en esta obra"):
        if existentes.empty:
            st.caption("Todavía no hay avances cargados.")
        else:
            d = existentes[
                (existentes["fecha"].astype(str).str[:10] == fecha.strftime("%Y-%m-%d"))
                & (existentes["obra_id"].astype(str) == str(obra_row["obra_id"]))
            ]
            if d.empty:
                st.caption("Todavía no hay avances cargados para este día.")
            else:
                st.dataframe(d[["avance_pct", "tarea", "novedades", "cargado_por"]], hide_index=True, use_container_width=True)
