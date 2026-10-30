import re
from datetime import datetime, time

import pandas as pd
import streamlit as st

from modulos import datos


def _a_hora(valor):
    """time, datetime/Timestamp o texto ('07:30', '7:30:00') -> datetime.time o None."""
    if valor is None:
        return None
    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(valor, datetime):
        return valor.time().replace(second=0, microsecond=0)
    if isinstance(valor, time):
        return valor.replace(second=0, microsecond=0)
    m = re.search(r"(\d{1,2}):(\d{2})", str(valor))
    if m and int(m.group(1)) < 24 and int(m.group(2)) < 60:
        return time(int(m.group(1)), int(m.group(2)))
    return None


def _texto(hora) -> str:
    return hora.strftime("%H:%M") if hora else ""


def _horas_trabajadas(entrada, salida):
    """Calcula horas decimales entre entrada y salida (None si falta alguna)."""
    if not entrada or not salida:
        return None
    minutos = (salida.hour * 60 + salida.minute) - (entrada.hour * 60 + entrada.minute)
    return round(minutos / 60, 2)


def cargar_horas_obra_fecha(id_obra: str, fecha_str: str) -> pd.DataFrame:
    """Consulta los registros de horas desde PostgreSQL para una obra y fecha dada."""
    query = """
        SELECT id_registro, dni_empleado, id_obra, id_tarea_obra, fecha, 
               hora_inicio, hora_fin, cantidad_horas, fecha_carga
        FROM horas
        WHERE id_obra = :id_obra AND fecha = :fecha
    """
    return datos.leer_sql(query, {"id_obra": str(id_obra), "fecha": fecha_str})


def guardar_registro_hora(registro: dict):
    """Inserta o actualiza un registro de horas en la base de datos PostgreSQL."""
    query = """
        INSERT INTO horas (id_registro, dni_empleado, id_obra, id_tarea_obra, fecha, hora_inicio, hora_fin, cantidad_horas, fecha_carga)
        VALUES (:id_registro, :dni_empleado, :id_obra, :id_tarea_obra, :fecha, :hora_inicio, :hora_fin, :cantidad_horas, :fecha_carga)
        ON CONFLICT (id_registro) 
        DO UPDATE SET 
            hora_inicio = EXCLUDED.hora_inicio,
            hora_fin = EXCLUDED.hora_fin,
            cantidad_horas = EXCLUDED.cantidad_horas,
            id_tarea_obra = EXCLUDED.id_tarea_obra,
            fecha_carga = EXCLUDED.fecha_carga;
    """
    datos.ejecutar_sql(query, registro)


def mostrar_modulo():
    st.title("🕒 Carga de Horas")

    try:
        empleados = datos.empleados_activos()
        obras = datos.obras_activas()
    except Exception as e:
        st.error(f"No pude leer los datos de Empleados u Obras desde PostgreSQL: {e}")
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
    id_obra = str(obra_row.get("id", obra_row.get("id_obra", obra_nombre)))

    try:
        existentes = cargar_horas_obra_fecha(id_obra, fecha_str)
    except Exception as e:
        st.error(f"Error al consultar horas registradas en PostgreSQL: {e}")
        return

    previo = {
        datos.dni_str(pd.Series([r["dni_empleado"]])).iloc[0]: r
        for _, r in existentes.iterrows()
    } if not existentes.empty else {}

    filas = []
    for _, e in empleados.iterrows():
        dni_empleado = datos.dni_str(pd.Series([e.get("dni", e.get("DNI", ""))])).iloc[0]
        p = previo.get(dni_empleado)
        filas.append({
            "DNI": dni_empleado,
            "Empleado": f"{e.get('nombre', '')}",
            "Entrada": _a_hora(p["hora_inicio"]) if p is not None else None,
            "Salida": _a_hora(p["hora_fin"]) if p is not None else None,
            "Tarea": str(p["id_tarea_obra"]) if p is not None and p["id_tarea_obra"] else "",
        })
    base = pd.DataFrame(filas)

    st.caption(
        "A la mañana cargá la **Entrada** y guardá. Al finalizar la jornada, "
        "completá la **Salida** y la **Tarea**: las horas se calculan y guardan directo en Cloud SQL."
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
        key=f"editor_horas_{id_obra}_{fecha_str}",
    )

    if st.button("💾 Guardar en Cloud SQL", type="primary"):
        a_guardar = editado[editado["Entrada"].notna() | editado["Salida"].notna()]
        if a_guardar.empty:
            st.warning("No cargaste ninguna entrada ni salida.")
            return

        errores = []
        for _, r in a_guardar.iterrows():
            ent, sal = _a_hora(r["Entrada"]), _a_hora(r["Salida"])
            if (pd.notna(r["Entrada"]) and not ent) or (pd.notna(r["Salida"]) and not sal):
                errores.append(f"{r['Empleado']}: no pude interpretar la hora ({r['Entrada']!r} / {r['Salida']!r}).")
                continue
            if sal and not ent:
                errores.append(f"{r['Empleado']}: tiene salida pero falta la entrada.")
            elif ent and sal and sal <= ent:
                errores.append(f"{r['Empleado']}: la salida ({_texto(sal)}) debe ser posterior a la entrada ({_texto(ent)}).")
        if errores:
            for m in errores:
                st.error(m)
            return

        try:
            ahora = datetime.now(datos.TZ).strftime("%Y-%m-%d %H:%M:%S")
            guardados = 0

            for _, r in a_guardar.iterrows():
                ent, sal = _a_hora(r["Entrada"]), _a_hora(r["Salida"])
                hs = _horas_trabajadas(ent, sal) if (ent and sal) else 0.0
                dni_emp = str(r["DNI"])
                id_reg = f"H-{id_obra}-{dni_emp}-{fecha_str}"

                registro = {
                    "id_registro": id_reg,
                    "dni_empleado": dni_emp,
                    "id_obra": id_obra,
                    "id_tarea_obra": str(r["Tarea"]) if r["Tarea"] else "General",
                    "fecha": fecha_str,
                    "hora_inicio": ent if ent else time(0, 0),
                    "hora_fin": sal if sal else time(0, 0),
                    "cantidad_horas": float(hs),
                    "fecha_carga": ahora,
                }
                guardar_registro_hora(registro)
                guardados += 1

            st.success(f" Se guardaron/actualizaron {guardados} registros en Google Cloud SQL para {obra_nombre}.")
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar en la base de datos: {e}")

    with st.expander("Resumen del día en esta obra", expanded=True):
        try:
            h = cargar_horas_obra_fecha(id_obra, fecha_str)
            if h.empty:
                st.caption("Todavía no hay horas cargadas para este día.")
            else:
                st.dataframe(h[["dni_empleado", "hora_inicio", "hora_fin", "cantidad_horas", "id_tarea_obra"]],
                             hide_index=True, use_container_width=True)
        except Exception as e:
            st.caption(f"No se pudieron consultar los registros del día: {e}")