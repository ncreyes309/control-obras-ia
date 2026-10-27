from datetime import datetime

import pandas as pd
import streamlit as st

from modulos import datos


def mostrar_modulo():
    st.title("🕒 Carga de Horas")

    try:
        empleados = datos.empleados_activos()
        obras = datos.obras_activas()
    except Exception as e:
        st.error(f"No pude leer las hojas de Empleados u Obras: {e}")
        return

    if obras.empty or empleados.empty:
        st.warning("Necesitás al menos una obra activa y un empleado activo cargados.")
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

    base = pd.DataFrame({
        "DNI": datos.dni_str(empleados["DNI"]),
        "Empleado": empleados["apellido"].astype(str) + ", " + empleados["nombre"].astype(str),
        "Horas": 0.0,
        "Tarea": "",
    })

    st.caption("Completá las horas de quienes trabajaron hoy en esta obra. Las filas con 0 horas no se guardan.")
    editado = st.data_editor(
        base,
        hide_index=True,
        use_container_width=True,
        disabled=["DNI", "Empleado"],
        column_config={
            "Horas": st.column_config.NumberColumn("Horas", min_value=0.0, max_value=16.0, step=0.5),
            "Tarea": st.column_config.TextColumn("Tarea / novedad"),
        },
        key=f"editor_horas_{obra_nombre}_{fecha_str}",
    )

    if st.button("💾 Guardar horas", type="primary"):
        a_guardar = editado[editado["Horas"] > 0]
        if a_guardar.empty:
            st.warning("No cargaste horas para nadie.")
            return

        try:
            existentes = datos.leer_obra(archivo, datos.HOJA_HORAS, datos.COLUMNAS_HORAS)
            ya_cargados = set(
                zip(datos.fecha_iso(existentes["fecha"]), datos.dni_str(existentes["DNI"]))
            ) if not existentes.empty else set()

            ahora = datetime.now(datos.TZ).strftime("%Y-%m-%d %H:%M:%S")
            nuevas, duplicados = [], []
            for _, r in a_guardar.iterrows():
                if (fecha_str, str(r["DNI"])) in ya_cargados:
                    duplicados.append(r["Empleado"])
                    continue
                nuevas.append({
                    "fecha": fecha_str,
                    "DNI": str(r["DNI"]),
                    "empleado": r["Empleado"],
                    "horas": float(r["Horas"]),
                    "tarea": r["Tarea"],
                    "cargado_por": st.session_state["usuario_actual"],
                    "hora_actual": ahora,
                })

            if nuevas:
                total = pd.concat([existentes, pd.DataFrame(nuevas)], ignore_index=True)
                datos.escribir(archivo, datos.HOJA_HORAS, total)
                st.success(f"Se guardaron {len(nuevas)} registros en el archivo de {obra_nombre}.")
            if duplicados:
                st.warning("Ya tenían horas ese día en esta obra (no se duplicaron): " + ", ".join(duplicados))
        except Exception as e:
            st.error(f"Error al guardar: {e}")

    with st.expander("Ver lo ya cargado en esta obra y fecha"):
        try:
            h = datos.leer_obra(archivo, datos.HOJA_HORAS, datos.COLUMNAS_HORAS)
            h = h[datos.fecha_iso(h["fecha"]) == fecha_str]
            if h.empty:
                st.caption("Todavía no hay horas cargadas.")
            else:
                st.dataframe(h[["empleado", "horas", "tarea", "cargado_por"]], hide_index=True, use_container_width=True)
                st.metric("Total de horas", f"{datos.num(h['horas']).sum():g}")
        except Exception as e:
            st.caption(f"No pude leer las horas de esta obra: {e}")
