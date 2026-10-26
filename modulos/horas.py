from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

TZ = ZoneInfo("America/Argentina/Buenos_Aires")

HOJA_EMPLEADOS = "empleados"   # DNI | apellido | nombre | categoria | activo
HOJA_OBRAS = "obras"           # obra_id | nombre | direccion | estado
HOJA_HORAS = "horas"           # fecha | obra_id | obra | DNI | empleado | horas | tarea | cargado_por | timestamp

COLUMNAS_HORAS = ["fecha", "obra_id", "obra", "DNI", "empleado", "horas", "tarea", "cargado_por", "timestamp"]


def _conn():
    return st.connection("gsheets", type=GSheetsConnection)


def _leer(hoja: str, ttl: int) -> pd.DataFrame:
    df = _conn().read(worksheet=hoja, ttl=ttl)
    df = df.dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _es_activo(valor) -> bool:
    return str(valor).strip().lower() in ("si", "sí", "true", "1", "x", "activo", "")


def mostrar_modulo():
    st.title("🕒 Carga de Horas")

    try:
        empleados = _leer(HOJA_EMPLEADOS, ttl=300)
        obras = _leer(HOJA_OBRAS, ttl=300)
    except Exception as e:
        st.error(f"No pude leer las hojas '{HOJA_EMPLEADOS}' u '{HOJA_OBRAS}': {e}")
        st.info("Creá esas hojas en el Google Sheet con las columnas indicadas en la guía.")
        return

    if "activo" in empleados.columns:
        empleados = empleados[empleados["activo"].apply(_es_activo)]
    if "estado" in obras.columns:
        obras = obras[obras["estado"].astype(str).str.strip().str.lower().isin(["activa", "en curso", "activo", ""])]

    if obras.empty or empleados.empty:
        st.warning("Necesitás al menos una obra activa y un empleado activo cargados.")
        return

    col1, col2 = st.columns(2)
    with col1:
        obra_nombre = st.selectbox("Obra", obras["nombre"].tolist())
    with col2:
        fecha = st.date_input("Fecha", value=datetime.now(TZ).date(), format="DD/MM/YYYY")

    obra_row = obras[obras["nombre"] == obra_nombre].iloc[0]

    # Tabla editable: el encargado completa horas solo de quienes trabajaron
    base = pd.DataFrame({
        "DNI": empleados["DNI"].astype(str),
        "Empleado": (empleados["apellido"].astype(str) + ", " + empleados["nombre"].astype(str)),
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
        key=f"editor_horas_{obra_nombre}_{fecha}",
    )

    if st.button("💾 Guardar horas", type="primary"):
        a_guardar = editado[editado["Horas"] > 0]
        if a_guardar.empty:
            st.warning("No cargaste horas para nadie.")
            return

        try:
            conn = _conn()
            try:
                existentes = _leer(HOJA_HORAS, ttl=0)
            except Exception:
                existentes = pd.DataFrame(columns=COLUMNAS_HORAS)

            fecha_str = fecha.strftime("%Y-%m-%d")
            ahora = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")

            # Evitar duplicados: misma fecha + obra + DNI
            if not existentes.empty:
                clave = (
                    existentes["fecha"].astype(str).str[:10] + "|"
                    + existentes["obra_id"].astype(str) + "|"
                    + existentes["DNI"].astype(str)
                )
                ya_cargados = set(clave)
            else:
                ya_cargados = set()

            nuevas, duplicados = [], []
            for _, r in a_guardar.iterrows():
                k = f"{fecha_str}|{obra_row['obra_id']}|{r['DNI']}"
                if k in ya_cargados:
                    duplicados.append(r["Empleado"])
                    continue
                nuevas.append({
                    "fecha": fecha_str,
                    "obra_id": obra_row["obra_id"],
                    "obra": obra_nombre,
                    "DNI": str(r["DNI"]),
                    "empleado": r["Empleado"],
                    "horas": float(r["Horas"]),
                    "tarea": r["Tarea"],
                    "cargado_por": st.session_state["usuario_actual"],
                    "timestamp": ahora,
                })

            if nuevas:
                total = pd.concat([existentes, pd.DataFrame(nuevas)], ignore_index=True)
                conn.update(worksheet=HOJA_HORAS, data=total)
                st.success(f"Se guardaron {len(nuevas)} registros.")
            if duplicados:
                st.warning("Ya tenían horas cargadas ese día en esta obra (no se duplicaron): " + ", ".join(duplicados))
        except Exception as e:
            st.error(f"Error al guardar: {e}")

    # Lo cargado hoy en la obra
    with st.expander("Ver lo ya cargado en esta obra y fecha"):
        try:
            h = _leer(HOJA_HORAS, ttl=0)
            h = h[(h["fecha"].astype(str).str[:10] == fecha.strftime("%Y-%m-%d")) & (h["obra_id"].astype(str) == str(obra_row["obra_id"]))]
            if h.empty:
                st.caption("Todavía no hay horas cargadas.")
            else:
                st.dataframe(h[["empleado", "horas", "tarea", "cargado_por"]], hide_index=True, use_container_width=True)
                st.metric("Total de horas", f"{h['horas'].astype(float).sum():g}")
        except Exception:
            st.caption("Todavía no hay horas cargadas.")
