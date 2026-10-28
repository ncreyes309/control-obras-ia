from datetime import datetime, time

import pandas as pd
import streamlit as st

from modulos import datos


def _a_hora(valor):
    """'07:30', '7:30:00' o time -> datetime.time (o None si está vacío o es inválido)."""
    if isinstance(valor, time):
        return valor.replace(second=0, microsecond=0)
    texto = str(valor).strip()
    if not texto or texto.lower() in ("nan", "none", "nat"):
        return None
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(texto, fmt).time()
        except ValueError:
            pass
    return None


def _texto(hora) -> str:
    return hora.strftime("%H:%M") if hora else ""


def _horas_trabajadas(entrada, salida):
    """Horas decimales entre entrada y salida (None si falta alguna)."""
    if not entrada or not salida:
        return None
    minutos = (salida.hour * 60 + salida.minute) - (entrada.hour * 60 + entrada.minute)
    return round(minutos / 60, 2)


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

    try:
        existentes = datos.leer_obra(archivo, datos.HOJA_HORAS, datos.COLUMNAS_HORAS)
    except Exception as e:
        st.error(f"No pude abrir el archivo de esta obra: {e}")
        return

    # Lo ya cargado ese día (por ejemplo, entradas de la mañana)
    dia = existentes[datos.fecha_iso(existentes["fecha"]) == fecha_str]
    previo = {
        datos.dni_str(pd.Series([r["DNI"]])).iloc[0]: r
        for _, r in dia.iterrows()
    }

    filas = []
    for _, e in empleados.iterrows():
        dni = datos.dni_str(pd.Series([e["DNI"]])).iloc[0]
        p = previo.get(dni)
        filas.append({
            "DNI": dni,
            "Empleado": f"{e['apellido']}, {e['nombre']}",
            "Entrada": _a_hora(p["entrada"]) if p is not None else None,
            "Salida": _a_hora(p["salida"]) if p is not None else None,
            "Tarea": str(p["tarea"]) if p is not None else "",
        })
    base = pd.DataFrame(filas)

    st.caption(
        "A la mañana cargá solo la **Entrada** y guardá. Al terminar la jornada, volvé a abrir esta "
        "pantalla, completá la **Salida** y guardá de nuevo: las horas se calculan solas."
    )
    editado = st.data_editor(
        base,
        hide_index=True,
        use_container_width=True,
        disabled=["DNI", "Empleado"],
        column_config={
            "Entrada": st.column_config.TimeColumn("Entrada", format="HH:mm", step=60),
            "Salida": st.column_config.TimeColumn("Salida", format="HH:mm", step=60),
            "Tarea": st.column_config.TextColumn("Tarea / novedad"),
        },
        key=f"editor_horas_{obra_nombre}_{fecha_str}",
    )

    if st.button("💾 Guardar", type="primary"):
        a_guardar = editado[editado["Entrada"].notna() | editado["Salida"].notna()]
        if a_guardar.empty:
            st.warning("No cargaste ninguna entrada ni salida.")
            return

        errores = []
        for _, r in a_guardar.iterrows():
            ent, sal = _a_hora(r["Entrada"]), _a_hora(r["Salida"])
            if sal and not ent:
                errores.append(f"{r['Empleado']}: tiene salida pero falta la entrada.")
            elif ent and sal and sal <= ent:
                errores.append(f"{r['Empleado']}: la salida ({_texto(sal)}) debe ser posterior a la entrada ({_texto(ent)}).")
        if errores:
            for m in errores:
                st.error(m)
            return

        try:
            total = existentes.copy()
            total["DNI"] = datos.dni_str(total["DNI"])
            total["_fecha"] = datos.fecha_iso(total["fecha"])
            ahora = datetime.now(datos.TZ).strftime("%Y-%m-%d %H:%M:%S")
            nuevas, actualizadas = 0, 0

            for _, r in a_guardar.iterrows():
                ent, sal = _a_hora(r["Entrada"]), _a_hora(r["Salida"])
                hs = _horas_trabajadas(ent, sal)
                valores = {
                    "entrada": _texto(ent),
                    "salida": _texto(sal),
                    "horas": hs if hs is not None else "",
                    "tarea": str(r["Tarea"]),
                    "cargado_por": st.session_state["usuario_actual"],
                    "hora_actual": ahora,
                }
                mask = (total["_fecha"] == fecha_str) & (total["DNI"] == str(r["DNI"]))
                if mask.any():
                    idx = total.index[mask][0]
                    for k, v in valores.items():
                        total.at[idx, k] = v
                    actualizadas += 1
                else:
                    fila = {"fecha": fecha_str, "obra_id": str(obra_row.get("obra_id", "")), "obra": obra_nombre,
                            "DNI": str(r["DNI"]), "empleado": r["Empleado"], "_fecha": fecha_str, **valores}
                    total = pd.concat([total, pd.DataFrame([fila])], ignore_index=True)
                    nuevas += 1

            total = total.drop(columns="_fecha").fillna("")
            datos.escribir(archivo, datos.HOJA_HORAS, total)
            existentes = total
            st.success(f"Guardado: {nuevas} nuevos y {actualizadas} actualizados en {obra_nombre}.")
        except Exception as e:
            st.error(f"Error al guardar: {e}")

    with st.expander("Resumen del día en esta obra", expanded=True):
        try:
            h = existentes[datos.fecha_iso(existentes["fecha"]) == fecha_str]
            if h.empty:
                st.caption("Todavía no hay horas cargadas.")
            else:
                st.dataframe(h[["empleado", "entrada", "salida", "horas", "tarea", "cargado_por"]],
                             hide_index=True, use_container_width=True)
                pendientes = h[(h["entrada"].astype(str).str.strip() != "") & (h["salida"].astype(str).str.strip() == "")]
                c1, c2 = st.columns(2)
                c1.metric("Total de horas", f"{datos.num(h['horas']).sum():g}")
                c2.metric("Sin salida cargada", len(pendientes))
                if len(pendientes):
                    st.warning("Falta la salida de: " + ", ".join(pendientes["empleado"].astype(str)))
        except Exception as e:
            st.caption(f"No pude leer las horas de esta obra: {e}")
