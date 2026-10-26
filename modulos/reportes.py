from datetime import datetime

import pandas as pd
import streamlit as st
from openai import OpenAI

from modulos import datos

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
{texto_datos}
"""


def construir_resumen(fecha_str: str, datos_obras: dict, errores: dict) -> str:
    """datos_obras: {nombre_obra: (df_horas, df_avances)}; errores: {nombre_obra: motivo}."""
    bloques, sin_registro = [], []

    for obra, (horas, avances) in datos_obras.items():
        ho = horas[datos.fecha_iso(horas["fecha"]) == fecha_str]
        av = avances[datos.fecha_iso(avances["fecha"]) == fecha_str]
        if ho.empty and av.empty:
            sin_registro.append(obra)
            continue

        lineas = [f"OBRA: {obra}"]
        if ho.empty:
            lineas.append("Horas: sin registros")
        else:
            lineas.append(f"Horas totales: {datos.num(ho['horas']).sum():g} ({len(ho)} personas)")
            for _, r in ho.iterrows():
                tarea = f" - {r['tarea']}" if str(r["tarea"]).strip() else ""
                lineas.append(f"  - {r['empleado']}: {r['horas']} hs{tarea}")
        if av.empty:
            lineas.append("Avances/novedades: sin registros")
        else:
            for _, r in av.iterrows():
                lineas.append(f"Avance total de la obra: {r['avance_pct']}% | Tarea: {r['tarea']} | Novedades: {r['novedades']}")
        bloques.append("\n".join(lineas))

    if sin_registro:
        bloques.append("OBRAS ACTIVAS SIN NINGÚN REGISTRO HOY: " + ", ".join(sin_registro))
    if errores:
        bloques.append("OBRAS CUYO ARCHIVO NO SE PUDO LEER: " + ", ".join(f"{o} ({m})" for o, m in errores.items()))
    return "\n\n".join(bloques)


def redactar_reporte(fecha_str: str, texto_datos: str, api_key: str) -> str:
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=MODELO,
        messages=[{"role": "user", "content": PROMPT.format(fecha=fecha_str, texto_datos=texto_datos)}],
        temperature=0.2,
    )
    return resp.choices[0].message.content


def _api_key() -> str | None:
    try:
        return st.secrets.get("OPENAI_API_KEY")
    except Exception:
        return None


def mostrar_modulo():
    st.title("📨 Reporte Diario para la Gerencia")

    api_key = _api_key()
    if not api_key:
        st.error("Falta configurar `OPENAI_API_KEY` en los secrets de la app.")
        return

    fecha = st.date_input("Fecha del reporte", value=datetime.now(datos.TZ).date(), format="DD/MM/YYYY")
    fecha_str = fecha.strftime("%Y-%m-%d")

    if st.button("🤖 Generar reporte", type="primary"):
        with st.spinner("Leyendo los archivos de cada obra y redactando el informe..."):
            try:
                obras = datos.obras_activas()
                datos_obras, errores = {}, {}
                for _, o in obras.iterrows():
                    nombre = str(o["nombre"])
                    archivo = str(o.get("archivo", "")).strip()
                    if not archivo:
                        errores[nombre] = "sin archivo asignado"
                        continue
                    try:
                        h = datos.leer_obra(archivo, datos.HOJA_HORAS, datos.COLUMNAS_HORAS)
                        a = datos.leer_obra(archivo, datos.HOJA_AVANCES, datos.COLUMNAS_AVANCES)
                        datos_obras[nombre] = (h, a)
                    except Exception as e:
                        errores[nombre] = str(e)[:80]

                texto_datos = construir_resumen(fecha_str, datos_obras, errores)
                if not texto_datos.strip():
                    st.warning("No hay obras activas para reportar.")
                    st.session_state.pop("reporte_texto", None)
                else:
                    st.session_state["reporte_texto"] = redactar_reporte(fecha_str, texto_datos, api_key)
                    st.session_state["reporte_datos"] = texto_datos
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
