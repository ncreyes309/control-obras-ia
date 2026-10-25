"""Acceso centralizado a Google Sheets.

Archivos globales (URLs en secrets, sección [archivos]): usuarios, empleados, obras.
Cada obra tiene además su propio archivo (URL en la columna 'archivo' de la hoja Obras)
con las pestañas Horas y Avances.
"""
import re
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

TZ = ZoneInfo("America/Argentina/Buenos_Aires")

HOJA_EMPLEADOS = "empleados"
HOJA_OBRAS = "obras"
HOJA_HORAS = "horas"
HOJA_AVANCES = "avances"

COLUMNAS_HORAS = ["fecha", "DNI", "empleado", "horas", "tarea", "cargado_por", "timestamp"]
COLUMNAS_AVANCES = ["fecha", "avance_pct", "tarea", "novedades", "cargado_por", "timestamp"]

ESTADOS_OBRA_ACTIVA = ["activa", "en curso", "activo", ""]


# ---------- Conexión ----------
def _conn():
    return st.connection("gsheets", type=GSheetsConnection)


def url_archivo(clave: str) -> str:
    """URL del archivo de Google Sheets que contiene la hoja pedida.

    Con un único Sheet (el modelo de la documentación) alcanza con 'spreadsheet' en
    [connections.gsheets]. Si algún día se separan archivos, se pueden definir
    en una sección [archivos] (usuarios, empleados, obras).
    """
    try:
        return st.secrets["archivos"][clave]
    except Exception:
        pass
    try:
        return st.secrets["connections"]["gsheets"]["spreadsheet"]
    except Exception:
        raise RuntimeError("Falta la URL del Sheet: agregá 'spreadsheet' en [connections.gsheets] de los secrets.")


def leer(url: str, hoja: str, ttl: int = 0) -> pd.DataFrame:
    df = _conn().read(spreadsheet=url, worksheet=hoja, ttl=ttl)
    #df = _conn().read(spreadsheet=url, worksheet=hoja, sheet=hoja, ttl=ttl)
    df = df.dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def escribir(url: str, hoja: str, df: pd.DataFrame) -> None:
    _conn().update(spreadsheet=url, worksheet=hoja, data=df)


def leer_obra(url_obra: str, hoja: str, columnas: list[str]) -> pd.DataFrame:
    """Lee una pestaña del archivo de una obra, asegurando que existan las columnas esperadas."""
    df = leer(url_obra, hoja, ttl=0).fillna("")
    for c in columnas:
        if c not in df.columns:
            df[c] = ""
    return df


# ---------- Catálogos ----------
def obras_activas() -> pd.DataFrame:
    df = leer(url_archivo("obras"), HOJA_OBRAS, ttl=60)
    if "estado" in df.columns:
        df = df[df["estado"].fillna("").astype(str).str.strip().str.lower().isin(ESTADOS_OBRA_ACTIVA)]
    return df


def empleados_activos() -> pd.DataFrame:
    df = leer(url_archivo("empleados"), HOJA_EMPLEADOS, ttl=60)
    if "activo" in df.columns:
        df = df[df["activo"].fillna("").astype(str).str.strip().str.lower().isin(["si", "sí", "true", "1", "x", "activo", ""])]
    return df


# ---------- Normalización (Sheets puede devolver fechas/números según el idioma de la planilla) ----------
def _a_iso(v) -> str:
    v = str(v).strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", v)
    if m:
        return m.group(0)
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", v)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    return v


def fecha_iso(serie: pd.Series) -> pd.Series:
    return serie.map(_a_iso)


def num(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie.astype(str).str.replace(",", ".", regex=False), errors="coerce")


def dni_str(serie: pd.Series) -> pd.Series:
    return serie.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
