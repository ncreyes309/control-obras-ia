import datetime as dt
import pandas as pd
import streamlit as st
import modulos.datos as datos

ROLES_PERMITIDOS = ["Administrador", "Gerente", "Director de Obras"]
ROLES_VER_VALOR = ["Administrador", "Gerente"]  # solo ellos ven y editan el valor hora


def _s(valor) -> str:
    """Texto seguro: None/NaN -> ''."""
    return "" if valor is None or (not isinstance(valor, str) and pd.isna(valor)) else str(valor)


def _solo_digitos(texto: str) -> str:
    return "".join(ch for ch in texto if ch.isdigit())


def mostrar_modulo():
    st.title("👷 Gestión de Empleados")

    rol = st.session_state.get("rol_actual")
    if rol not in ROLES_PERMITIDOS:
        st.error("⛔ No tenés permisos para ver este módulo.")
        return
    puede_valor = rol in ROLES_VER_VALOR
    empresa_id = datos.empresa_actual()

    flash = st.session_state.pop("_flash_empleados", None)
    if flash:
        st.success(flash)

    try:
        df_cat = datos.cargar_categorias(empresa_id)
        df_emp = datos.cargar_empleados(empresa_id)
        df_obras = datos.cargar_todas_obras(empresa_id)
        df_asig = datos.cargar_asignaciones(empresa_id)
    except Exception as e:
        st.error(
            "No se pudieron cargar los datos. ¿Ya ejecutaste el script `crear_tablas_empleados.sql` "
            f"en la base?\n\nDetalle: {e}"
        )
        return

    nombres_tabs = ["👷 Empleados", "🏗️ Asignación a obras"]
    if puede_valor:
        nombres_tabs.append("🏷️ Categorías")
    tabs = st.tabs(nombres_tabs)

    cat_activas = df_cat[df_cat["activo"] == True] if not df_cat.empty else df_cat  # noqa: E712
    opciones_cat = {"Sin categoría": None}
    opciones_cat.update({str(r.nombre): int(r.id) for r in cat_activas.itertuples()})

    # =====================================================================
    # TAB 1: EMPLEADOS
    # =====================================================================
    with tabs[0]:
        with st.form("form_alta_empleado", clear_on_submit=True):
            st.subheader("➕ Registrar Nuevo Empleado")
            c1, c2 = st.columns(2)
            with c1:
                dni = st.text_input("DNI (sin puntos ni guiones)*")
                apellido = st.text_input("Apellido*")
                nombre = st.text_input("Nombre*")
                telefono = st.text_input("Teléfono")
            with c2:
                cuil = st.text_input("CUIL (11 dígitos, sin guiones)")
                categoria = st.selectbox("Categoría", list(opciones_cat.keys()))
                fecha_ingreso = st.date_input("Fecha de ingreso", value=dt.date.today(), format="DD/MM/YYYY")
            guardar = st.form_submit_button("💾 Guardar Empleado")

            if guardar:
                dni_n, cuil_n = _solo_digitos(dni), _solo_digitos(cuil)
                if not (dni_n and apellido.strip() and nombre.strip()):
                    st.error("⚠️ DNI, apellido y nombre son obligatorios.")
                elif not 7 <= len(dni_n) <= 8:
                    st.error("⚠️ El DNI debe tener 7 u 8 dígitos.")
                elif cuil_n and len(cuil_n) != 11:
                    st.error("⚠️ El CUIL debe tener 11 dígitos.")
                else:
                    ok, msj = datos.crear_empleado(
                        empresa_id, dni_n, cuil_n, apellido.strip(), nombre.strip(),
                        opciones_cat[categoria], telefono.strip(), fecha_ingreso,
                    )
                    if ok:
                        st.session_state["_flash_empleados"] = f"✅ {msj}"
                        st.rerun()
                    else:
                        st.error(f"⚠️ {msj}")

        st.markdown("---")
        st.subheader("📋 Empleados registrados")
        if df_emp.empty:
            st.info("Todavía no hay empleados cargados.")
        else:
            solo_activos = st.checkbox("Mostrar solo activos", value=True, key="emp_solo_activos")
            df_ver = df_emp[df_emp["activo"] == True] if solo_activos else df_emp  # noqa: E712
            columnas = ["dni", "cuil", "apellido", "nombre", "categoria", "telefono", "fecha_ingreso", "activo"]
            if puede_valor:
                columnas.insert(5, "valor_hora")
            st.dataframe(df_ver[columnas], use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("✏️ Editar un empleado")
            opciones_emp = {f"{r.apellido}, {r.nombre} - DNI {r.dni}": r for r in df_emp.itertuples()}
            etiqueta = st.selectbox("Empleado", list(opciones_emp.keys()), key="emp_edit_sel")
            f = opciones_emp[etiqueta]

            nombres_cat = list(opciones_cat.keys())
            idx_cat = 0
            if pd.notna(f.categoria_id):
                for i, (_, cid) in enumerate(opciones_cat.items()):
                    if cid == int(f.categoria_id):
                        idx_cat = i

            with st.form(f"form_edit_empleado_{f.id}"):
                c1, c2 = st.columns(2)
                with c1:
                    e_apellido = st.text_input("Apellido", value=_s(f.apellido))
                    e_nombre = st.text_input("Nombre", value=_s(f.nombre))
                    e_telefono = st.text_input("Teléfono", value=_s(f.telefono))
                with c2:
                    e_cuil = st.text_input("CUIL", value=_s(f.cuil))
                    e_cat = st.selectbox("Categoría", nombres_cat, index=idx_cat)
                    e_activo = st.checkbox("Activo", value=bool(f.activo))
                st.caption(f"DNI {f.dni} (no se puede modificar).")
                editar = st.form_submit_button("💾 Guardar cambios")

                if editar:
                    cuil_n = _solo_digitos(e_cuil)
                    if not (e_apellido.strip() and e_nombre.strip()):
                        st.error("⚠️ Apellido y nombre no pueden quedar vacíos.")
                    elif cuil_n and len(cuil_n) != 11:
                        st.error("⚠️ El CUIL debe tener 11 dígitos.")
                    else:
                        ok, msj = datos.actualizar_empleado(
                            f.id, empresa_id, cuil_n, e_apellido.strip(), e_nombre.strip(),
                            opciones_cat[e_cat], e_telefono.strip(), e_activo,
                        )
                        if ok:
                            st.session_state["_flash_empleados"] = f"✅ {msj}"
                            st.rerun()
                        else:
                            st.error(f"⚠️ {msj}")

    # =====================================================================
    # TAB 2: ASIGNACIÓN A OBRAS
    # =====================================================================
    with tabs[1]:
        emp_activos = df_emp[df_emp["activo"] == True] if not df_emp.empty else df_emp  # noqa: E712
        estados_ok = [e for e in datos.ESTADOS_OBRA_ACTIVA]
        obras_ok = (
            df_obras[df_obras["estado"].fillna("").astype(str).str.strip().str.lower().isin(estados_ok)]
            if not df_obras.empty else df_obras
        )

        if emp_activos.empty or obras_ok.empty:
            st.info("Para asignar personal necesitás al menos un empleado activo y una obra activa.")
        else:
            opc_emp = {f"{r.apellido}, {r.nombre} (DNI {r.dni})": int(r.id) for r in emp_activos.itertuples()}
            opc_obra = {f"{r.nombre_obra} (#{r.id})": int(r.id) for r in obras_ok.itertuples()}

            with st.form("form_asignar", clear_on_submit=True):
                st.subheader("➕ Asignar empleados a una obra")
                st.caption("Un empleado puede estar asignado a varias obras a la vez.")
                obra_sel = st.selectbox("Obra", list(opc_obra.keys()))
                emps_sel = st.multiselect("Empleados", list(opc_emp.keys()))
                desde = st.date_input("Desde", value=dt.date.today(), format="DD/MM/YYYY")
                asignar = st.form_submit_button("💾 Asignar")

                if asignar:
                    if not emps_sel:
                        st.error("⚠️ Elegí al menos un empleado.")
                    else:
                        errores, hechos = [], 0
                        for etiqueta in emps_sel:
                            ok, msj = datos.asignar_empleado_obra(opc_emp[etiqueta], opc_obra[obra_sel], desde)
                            if ok:
                                hechos += 1
                            else:
                                errores.append(f"{etiqueta}: {msj}")
                        if errores:
                            st.error("⚠️ " + " | ".join(errores))
                        if hechos:
                            st.session_state["_flash_empleados"] = f"✅ {hechos} empleado(s) asignado(s) a la obra."
                            if not errores:
                                st.rerun()

        st.markdown("---")
        st.subheader("📋 Personal asignado")
        if df_asig.empty:
            st.info("Todavía no hay asignaciones.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                filtro_obra = st.selectbox("Filtrar por obra", ["Todas"] + sorted(df_asig["obra"].unique().tolist()),
                                           key="asig_filtro_obra")
            with c2:
                ver_hist = st.checkbox("Incluir asignaciones finalizadas", value=False, key="asig_hist")
            df_v = df_asig if ver_hist else df_asig[df_asig["fecha_hasta"].isna()]
            if filtro_obra != "Todas":
                df_v = df_v[df_v["obra"] == filtro_obra]
            st.dataframe(df_v[["obra", "dni", "apellido", "nombre", "fecha_desde", "fecha_hasta"]],
                         use_container_width=True, hide_index=True)

            vigentes = df_asig[df_asig["fecha_hasta"].isna()]
            if not vigentes.empty:
                st.markdown("---")
                st.subheader("🔚 Finalizar una asignación")
                opc_vig = {f"{r.obra} - {r.apellido}, {r.nombre} (desde {r.fecha_desde})": int(r.id)
                           for r in vigentes.itertuples()}
                c1, c2, c3 = st.columns([4, 2, 1])
                with c1:
                    sel = st.selectbox("Asignación vigente", list(opc_vig.keys()), key="asig_cerrar_sel")
                with c2:
                    hasta = st.date_input("Hasta", value=dt.date.today(), format="DD/MM/YYYY", key="asig_hasta")
                with c3:
                    st.write("")
                    st.write("")
                    if st.button("Finalizar", key="asig_cerrar_btn"):
                        ok, msj = datos.cerrar_asignacion(opc_vig[sel], empresa_id, hasta)
                        if ok:
                            st.session_state["_flash_empleados"] = f"✅ {msj}"
                            st.rerun()
                        else:
                            st.error(f"⚠️ {msj}")

    # =====================================================================
    # TAB 3: CATEGORÍAS (solo Administrador y Gerente)
    # =====================================================================
    if puede_valor:
        with tabs[2]:
            with st.form("form_alta_categoria", clear_on_submit=True):
                st.subheader("➕ Nueva categoría")
                c1, c2 = st.columns(2)
                with c1:
                    cat_nombre = st.text_input("Nombre* (ej. Oficial)")
                with c2:
                    cat_valor = st.number_input("Valor hora ($)", min_value=0.0, step=100.0, format="%.2f")
                crear = st.form_submit_button("💾 Guardar categoría")
                if crear:
                    if not cat_nombre.strip():
                        st.error("⚠️ El nombre es obligatorio.")
                    else:
                        ok, msj = datos.crear_categoria(empresa_id, cat_nombre.strip(), cat_valor)
                        if ok:
                            st.session_state["_flash_empleados"] = f"✅ {msj}"
                            st.rerun()
                        else:
                            st.error(f"⚠️ {msj}")

            st.markdown("---")
            st.subheader("📋 Categorías y valor hora")
            if df_cat.empty:
                st.info("Todavía no hay categorías cargadas.")
            else:
                st.dataframe(df_cat[["nombre", "valor_hora", "activo"]], use_container_width=True, hide_index=True)

                st.markdown("---")
                st.subheader("✏️ Editar una categoría")
                opc_c = {f"{r.nombre} (#{r.id})": r for r in df_cat.itertuples()}
                etiqueta = st.selectbox("Categoría", list(opc_c.keys()), key="cat_edit_sel")
                c = opc_c[etiqueta]
                with st.form(f"form_edit_cat_{c.id}"):
                    n_nombre = st.text_input("Nombre", value=_s(c.nombre))
                    n_valor = st.number_input("Valor hora ($)", min_value=0.0, step=100.0, format="%.2f",
                                              value=float(c.valor_hora) if pd.notna(c.valor_hora) else 0.0)
                    n_activo = st.checkbox("Activa", value=bool(c.activo))
                    editar = st.form_submit_button("💾 Guardar cambios")
                    if editar:
                        if not n_nombre.strip():
                            st.error("⚠️ El nombre no puede quedar vacío.")
                        else:
                            ok, msj = datos.actualizar_categoria(c.id, empresa_id, n_nombre.strip(), n_valor, n_activo)
                            if ok:
                                st.session_state["_flash_empleados"] = f"✅ {msj}"
                                st.rerun()
                            else:
                                st.error(f"⚠️ {msj}")
                st.caption("Cambiar el valor hora no modifica horas ya cargadas: solo afecta los cálculos futuros.")
