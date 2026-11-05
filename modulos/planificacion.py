import datetime as dt
import pandas as pd
import streamlit as st
import modulos.datos as datos

ROLES_PERMITIDOS = ["Administrador", "Gerente", "Director de Obras"]


def mostrar_modulo():
    st.title("📅 Planificación diaria de personal")

    if st.session_state.get("rol_actual") not in ROLES_PERMITIDOS:
        st.error("⛔ No tenés permisos para ver este módulo.")
        return

    empresa_id = datos.empresa_actual()

    flash = st.session_state.pop("_flash_plan", None)
    if flash:
        st.success(flash)

    fecha = st.date_input("Día a planificar", value=dt.date.today(), format="DD/MM/YYYY", key="plan_fecha")

    try:
        df_obras = datos.cargar_todas_obras(empresa_id)
        df_emp = datos.cargar_empleados(empresa_id)
        df_plan = datos.cargar_planificacion(empresa_id, fecha)
    except Exception as e:
        st.error(
            "No se pudieron cargar los datos. ¿Ya ejecutaste `crear_tabla_planificacion.sql` "
            f"en la base?\n\nDetalle: {e}"
        )
        return

    if not df_obras.empty:
        df_obras = df_obras[df_obras["estado"].fillna("").astype(str).str.strip().str.lower()
                            .isin(datos.ESTADOS_OBRA_ACTIVA)]
    df_emp = df_emp[df_emp["activo"] == True] if not df_emp.empty else df_emp  # noqa: E712

    if df_obras.empty:
        st.info("No hay obras activas. Cargalas o activalas en el módulo 🏗️ Obras.")
        return
    if df_emp.empty:
        st.info("No hay empleados activos. Cargalos en el módulo 👷 Empleados.")
        return

    # ---------- Copiar de otro día ----------
    with st.expander("📋 Copiar la planificación de otro día"):
        origen = st.date_input("Copiar desde", value=fecha - dt.timedelta(days=1),
                               format="DD/MM/YYYY", key="plan_origen")
        st.caption(f"Se suma a lo que ya esté planificado el {fecha.strftime('%d/%m/%Y')}, sin duplicar.")
        if st.button("Copiar", key="plan_copiar"):
            if origen == fecha:
                st.error("⚠️ El día de origen y el de destino son el mismo.")
            else:
                ok, msj = datos.copiar_planificacion(empresa_id, origen, fecha)
                if ok:
                    st.session_state["_flash_plan"] = f"✅ {msj}"
                    st.rerun()
                else:
                    st.error(f"⚠️ {msj}")

    # ---------- Resumen del día ----------
    st.markdown("---")
    st.subheader(f"👀 Personal planificado el {fecha.strftime('%d/%m/%Y')}")
    if df_plan.empty:
        st.info("Todavía no hay nadie planificado para este día.")
    else:
        resumen = (
            df_plan.assign(persona=df_plan["apellido"] + ", " + df_plan["nombre"])
            .groupby("obra")["persona"].agg(Cantidad="count", Personal=lambda s: " · ".join(s))
            .reset_index().rename(columns={"obra": "Obra"})
        )
        st.dataframe(resumen, use_container_width=True, hide_index=True)

    asignados_ids = set(df_plan["empleado_id"].astype(int)) if not df_plan.empty else set()
    sin_asignar = df_emp[~df_emp["id"].astype(int).isin(asignados_ids)]
    if not sin_asignar.empty:
        with st.expander(f"Sin asignar este día ({len(sin_asignar)})"):
            st.write(", ".join(f"{r.apellido}, {r.nombre}" for r in sin_asignar.itertuples()))

    # ---------- Editar una obra ----------
    st.markdown("---")
    st.subheader("✏️ Asignar personal a una obra")
    opc_obra = {f"{r.nombre_obra} (#{r.id})": int(r.id) for r in df_obras.itertuples()}
    obra_sel = st.selectbox("Obra", list(opc_obra.keys()), key="plan_obra_sel")
    obra_id = opc_obra[obra_sel]

    opc_emp = {f"{r.apellido}, {r.nombre} (DNI {r.dni})": int(r.id) for r in df_emp.itertuples()}
    id_a_label = {v: k for k, v in opc_emp.items()}

    actuales = df_plan[df_plan["obra_id"] == obra_id]["empleado_id"].astype(int).tolist() if not df_plan.empty else []
    default = [id_a_label[i] for i in actuales if i in id_a_label]

    en_otras = df_plan[df_plan["obra_id"] != obra_id] if not df_plan.empty else df_plan
    if not en_otras.empty:
        nombres_otras = sorted({f"{r.apellido}, {r.nombre}" for r in en_otras.itertuples()})
        st.caption("Ya asignados a otras obras ese día (podés repetirlos si trabajan en más de una): "
                   + " · ".join(nombres_otras))

    elegidos = st.multiselect("Empleados", list(opc_emp.keys()), default=default,
                              key=f"plan_emp_{fecha}_{obra_id}")
    if st.button("💾 Guardar planificación de esta obra", type="primary", key=f"plan_guardar_{fecha}_{obra_id}"):
        ok, msj = datos.planificar_dia(empresa_id, fecha, obra_id, [opc_emp[e] for e in elegidos])
        if ok:
            st.session_state["_flash_plan"] = f"✅ {msj}"
            st.rerun()
        else:
            st.error(f"⚠️ {msj}")
