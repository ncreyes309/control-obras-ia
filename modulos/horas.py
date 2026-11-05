import re
from datetime import datetime, time

import pandas as pd
import streamlit as st

from modulos import datos

SIN_TAREA = "General"


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


def _hora_dato(valor):
    """Hora guardada en la base: 00:00 significa 'todavía sin cargar'."""
    h = _a_hora(valor)
    return None if h == time(0, 0) else h


def _texto(hora) -> str:
    return hora.strftime("%H:%M") if hora else ""


def _s(valor) -> str:
    return "" if valor is None or (not isinstance(valor, str) and pd.isna(valor)) else str(valor)


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


def _horas_otras_obras(dnis, id_obra: str, fecha_str: str) -> pd.DataFrame:
    """Horas del mismo día de estos empleados en OTRAS obras (para evitar superposiciones)."""
    if not dnis:
        return pd.DataFrame(columns=["dni_empleado", "id_obra", "hora_inicio", "hora_fin"])
    query = """
        SELECT dni_empleado, id_obra, hora_inicio, hora_fin FROM horas
        WHERE fecha = :fecha AND id_obra <> :id_obra AND dni_empleado = ANY(:dnis)
    """
    return datos.leer_sql(query, {"fecha": fecha_str, "id_obra": str(id_obra), "dnis": list(dnis)})


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

    empresa_id = datos.empresa_actual()

    flash = st.session_state.pop("_flash_horas", None)
    if flash:
        st.success(flash)

    try:
        obras_todas = datos.cargar_todas_obras(empresa_id)
        df_emp_todos = datos.cargar_empleados(empresa_id)
        df_tareas = datos.cargar_tareas(empresa_id)
    except Exception as e:
        st.error(f"No pude leer los datos de Obras, Empleados o Tareas desde PostgreSQL: {e}")
        return

    obras = obras_todas
    if not obras.empty:
        obras = obras[obras["estado"].fillna("").astype(str).str.strip().str.lower().isin(datos.ESTADOS_OBRA_ACTIVA)]
    if obras.empty:
        st.warning("Necesitás al menos una obra activa.")
        return
    if df_emp_todos.empty:
        st.warning("Todavía no hay empleados cargados. Cargalos en el módulo 👷 Empleados.")
        return

    df_emp_todos = df_emp_todos.copy()
    df_emp_todos["dni"] = datos.dni_str(df_emp_todos["dni"])
    emp_por_dni = {
        r.dni: (f"{r.apellido}, {r.nombre}", _s(r.categoria)) for r in df_emp_todos.itertuples()
    }
    activos = df_emp_todos[df_emp_todos["activo"] == True]  # noqa: E712

    col1, col2 = st.columns(2)
    with col1:
        obra_nombre = st.selectbox("Obra", obras["nombre_obra"].tolist())
    with col2:
        fecha = st.date_input("Fecha", value=datetime.now(datos.TZ).date(), format="DD/MM/YYYY")
    fecha_str = fecha.strftime("%Y-%m-%d")

    obra_id = int(obras[obras["nombre_obra"] == obra_nombre].iloc[0]["id"])
    id_obra = str(obra_id)

    try:
        existentes = cargar_horas_obra_fecha(id_obra, fecha_str)
        planificados = datos.empleados_planificados(empresa_id, obra_id, fecha_str)
    except Exception as e:
        st.error(
            "Error al consultar la planificación o las horas. ¿Ya ejecutaste "
            f"`crear_tabla_planificacion.sql`?\n\nDetalle: {e}"
        )
        return

    previo = {
        datos.dni_str(pd.Series([r["dni_empleado"]])).iloc[0]: r
        for _, r in existentes.iterrows()
    } if not existentes.empty else {}

    # Personal de la grilla: planificado ese día + quien ya tenga horas cargadas
    personal = {str(r.dni): (f"{r.apellido}, {r.nombre}", _s(r.categoria)) for r in planificados.itertuples()}
    for dni in previo:
        if dni not in personal:
            personal[dni] = emp_por_dni.get(dni, (dni, ""))

    # Empleados que no estaban planificados pero hoy sí trabajaron en esta obra
    disponibles = {
        f"{r.apellido}, {r.nombre} (DNI {r.dni})": r.dni
        for r in activos.itertuples() if r.dni not in personal
    }
    extras = st.multiselect(
        "➕ Agregar empleados que no estaban planificados en esta obra hoy",
        list(disponibles.keys()),
        key=f"extras_{id_obra}_{fecha_str}",
    )
    for etiqueta in extras:
        dni = disponibles[etiqueta]
        personal[dni] = emp_por_dni[dni]

    if not personal:
        st.info(
            "No hay personal planificado para esta obra en esta fecha. Planificalo en "
            "**📅 Planificación** o agregalo arriba."
        )
        return

    # Tareas de la obra
    t_obra = df_tareas[df_tareas["obra_id"] == obra_id] if not df_tareas.empty else df_tareas
    id_a_label = {str(int(r.id)): str(r.nombre_tarea) for r in t_obra.itertuples()}
    label_a_id = {v: k for k, v in id_a_label.items()}
    opciones_tarea = [SIN_TAREA] + [
        str(r.nombre_tarea) for r in t_obra.itertuples() if _s(r.estado).strip().lower() != "finalizada"
    ]

    def _label_tarea(valor):
        v = _s(valor).strip()
        if not v:
            return None
        label = id_a_label.get(v, v)
        if label not in opciones_tarea:
            opciones_tarea.append(label)
        return label

    filas = []
    for dni, (nombre, categoria) in personal.items():
        p = previo.get(dni)
        filas.append({
            "DNI": dni,
            "Empleado": nombre,
            "Categoría": categoria,
            "Entrada": _hora_dato(p["hora_inicio"]) if p is not None else None,
            "Salida": _hora_dato(p["hora_fin"]) if p is not None else None,
            "Tarea": _label_tarea(p["id_tarea_obra"]) if p is not None else None,
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
        disabled=["DNI", "Empleado", "Categoría"],
        column_config={
            "Entrada": st.column_config.TimeColumn("Entrada", format="HH:mm", step=60),
            "Salida": st.column_config.TimeColumn("Salida", format="HH:mm", step=60),
            "Tarea": st.column_config.SelectboxColumn("Tarea", options=opciones_tarea, required=False),
        },
        key=f"editor_horas_{id_obra}_{fecha_str}_{hash(tuple(sorted(personal)))}",
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

        # Un empleado puede estar en varias obras el mismo día, pero no a la misma hora
        if not errores:
            try:
                otras = _horas_otras_obras([str(d) for d in a_guardar["DNI"]], id_obra, fecha_str)
                nombre_obra_por_id = dict(zip(obras_todas["id"].astype(str), obras_todas["nombre_obra"]))
                for _, r in a_guardar.iterrows():
                    ent, sal = _a_hora(r["Entrada"]), _a_hora(r["Salida"])
                    if not (ent and sal):
                        continue
                    ajenas = otras[otras["dni_empleado"].astype(str) == str(r["DNI"])]
                    for _, o in ajenas.iterrows():
                        o_ini, o_fin = _a_hora(o["hora_inicio"]), _a_hora(o["hora_fin"])
                        if o_ini and o_fin and o_fin > o_ini and ent < o_fin and sal > o_ini:
                            otra_obra = nombre_obra_por_id.get(str(o["id_obra"]), f"obra #{o['id_obra']}")
                            errores.append(
                                f"{r['Empleado']}: el horario {_texto(ent)}-{_texto(sal)} se superpone con "
                                f"{_texto(o_ini)}-{_texto(o_fin)} en {otra_obra}."
                            )
            except Exception as e:
                st.error(f"No pude verificar superposiciones con otras obras: {e}")
                return

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

                label = _s(r["Tarea"]).strip()
                id_tarea = label_a_id.get(label, label) if label else SIN_TAREA

                registro = {
                    "id_registro": id_reg,
                    "dni_empleado": dni_emp,
                    "id_obra": id_obra,
                    "id_tarea_obra": id_tarea,
                    "fecha": fecha_str,
                    "hora_inicio": ent if ent else time(0, 0),
                    "hora_fin": sal if sal else time(0, 0),
                    "cantidad_horas": float(hs),
                    "fecha_carga": ahora,
                }
                guardar_registro_hora(registro)
                guardados += 1

            st.session_state["_flash_horas"] = f"✅ Se guardaron/actualizaron {guardados} registros para {obra_nombre}."
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar en la base de datos: {e}")

    with st.expander("Resumen del día en esta obra", expanded=True):
        try:
            h = cargar_horas_obra_fecha(id_obra, fecha_str)
            if h.empty:
                st.caption("Todavía no hay horas cargadas para este día.")
            else:
                h = h.copy()
                h["dni_empleado"] = datos.dni_str(h["dni_empleado"])
                h["Empleado"] = h["dni_empleado"].map(lambda d: emp_por_dni.get(d, (d, ""))[0])
                h["Tarea"] = h["id_tarea_obra"].map(lambda v: id_a_label.get(_s(v), _s(v)))
                st.dataframe(
                    h[["dni_empleado", "Empleado", "hora_inicio", "hora_fin", "cantidad_horas", "Tarea"]],
                    hide_index=True, use_container_width=True,
                )
        except Exception as e:
            st.caption(f"No se pudieron consultar los registros del día: {e}")
