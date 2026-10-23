from datetime import datetime

import pandas as pd
import streamlit as st
from openai import OpenAI

from modulos.avances import COLUMNAS_AVANCES, HOJA_AVANCES
from modulos.horas import COLUMNAS_HORAS, HOJA_HORAS, HOJA_OBRAS, TZ, _leer

MODELO = "gpt-4o-mini"

PROMPT = """Sos el asistente del gerente general de una empresa constructora en Argentina.
Redactá el reporte de cierre del día {fecha} usando ÚNICAMENTE los datos de abajo.
No inventes cifras, tareas ni novedades. Si algo no fue informado, decí "sin información".

Estructura:
1. Resumen general del día (2-3 líneas)
2. Detalle por obra (avance %, tareas, horas trabajadas)
3. Novedades y puntos de atención (faltantes, clima, inconvenientes, visitas)
4. Obras sin reporte

Tono formal y conciso.

DATOS:
{datos}
"""


# ---------- Lógica reutilizable (sin Streamlit): la va a usar también el envío automático ----------
def construir_resumen(fecha_str: str, horas: pd.DataFrame, avances: pd.DataFrame, obras_activas: list[str]) -> str:
    h = horas[horas["fecha"].astype(str).str[:10] == fecha_str]
    a = avances[avances["fecha"].astype(str).str[:10] == fecha_str]

    con_datos = sorted(set(h["obra"]) | set(a["obra"]))
    bloques = []
    for obra in con_datos:
        ho, av = h[h["obra"] == obra], a[a["obra"] == obra]
        lineas = [f"OBRA: {obra}"]
        if ho.empty:
            lineas.append("Horas: sin registros")
        else:
            lineas.append(f"Horas totales: {pd.to_numeric(ho['horas']).sum():g} ({len(ho)} personas)")
            for _, r in ho.iterrows():
                tarea = f" - {r['tarea']}" if str(r["tarea"]).strip() else ""
                lineas.append(f"  - {r['empleado']}: {float(r['horas']):g} hs{tarea}")
        if av.empty:
            lineas.append("Avances/novedades: sin registros")
        else:
            for _, r in av.iterrows():
                lineas.append(f"Avance total de la obra: {r['avance_pct']}% | Tarea: {r['tarea']} | Novedades: {r['novedades']}")
        bloques.append("\n".join(lineas))

    sin_reporte = [o for o in obras_activas if o not in con_datos]
    if sin_reporte:
        bloques.append("OBRAS ACTIVAS SIN NINGÚN REGISTRO HOY: " + ", ".join(sin_reporte))
    return "\n\n".join(bloques)


def redactar_reporte(fecha_str: str, datos: str, api_key: str) -> str:
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=MODELO,
        messages=[{"role": "user", "content": PROMPT.format(fecha=fecha_str, datos=datos)}],
        temperature=0.2,
    )
    return resp.choices[0].message.content


# ---------- Pantalla ----------
def _api_key() -> str | None:
    try:
        return st.secrets.get("OPENAI_API_KEY")
    except Exception:
        return None


def _cargar(hoja: str, columnas: list[str]) -> pd.DataFrame:
    df = _leer(hoja, ttl=0).fillna("")
    for c in columnas:
        if c not in df.columns:
            df[c] = ""
    return df


def mostrar_modulo():
    st.title("📨 Reporte Diario para la Gerencia")

    api_key = _api_key()
    if not api_key:
        st.error("Falta configurar `OPENAI_API_KEY` en los secrets de la app (Streamlit Cloud → Settings → Secrets).")
        return

    fecha = st.date_input("Fecha del reporte", value=datetime.now(TZ).date(), format="DD/MM/YYYY")
    fecha_str = fecha.strftime("%Y-%m-%d")

    if st.button("🤖 Generar reporte", type="primary"):
        with st.spinner("Leyendo lo cargado y redactando el informe..."):
            try:
                horas = _cargar(HOJA_HORAS, COLUMNAS_HORAS)
                avances = _cargar(HOJA_AVANCES, COLUMNAS_AVANCES)
                obras = _cargar(HOJA_OBRAS, ["nombre", "estado"])
                activas = obras[obras["estado"].astype(str).str.strip().str.lower().isin(["activa", "en curso", "activo", ""])]
                datos = construir_resumen(fecha_str, horas, avances, activas["nombre"].tolist())

                if not datos.strip():
                    st.warning("No hay horas ni avances cargados para esa fecha.")
                    st.session_state.pop("reporte_texto", None)
                else:
                    st.session_state["reporte_texto"] = redactar_reporte(fecha_str, datos, api_key)
                    st.session_state["reporte_datos"] = datos
                    st.session_state["reporte_fecha"] = fecha_str
            except Exception as e:
                st.error(f"No se pudo generar el reporte: {e}")

    if st.session_state.get("reporte_texto"):
        st.markdown(f"### Informe del {st.session_state['reporte_fecha']}")
        st.markdown(st.session_state["reporte_texto"])
        st.download_button(
            "⬇️ Descargar (.txt)",
            st.session_state["reporte_texto"],
            file_name=f"reporte_{st.session_state['reporte_fecha']}.txt",
        )
        with st.expander("Ver los datos en los que se basó el informe"):
            st.text(st.session_state["reporte_datos"])
