"""Acceso centralizado a Google Cloud SQL (PostgreSQL) mediante SQLAlchemy."""
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

TZ = ZoneInfo("America/Argentina/Buenos_Aires")

ESTADOS_OBRA_ACTIVA = ["activa", "en curso", "activo", ""]

# ---------- Conexión a Base de Datos ----------
def _get_engine():
    """Crea y reutiliza el motor de conexión a PostgreSQL usando los secrets."""
    cfg = st.secrets["postgres"]
    url = f"postgresql://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['database']}"
    return create_engine(url)

def leer_sql(query: str, params: dict = None) -> pd.DataFrame:
    """Ejecuta una consulta SQL de lectura y devuelve un DataFrame."""
    engine = _get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)

def ejecutar_sql(query: str, params: dict = None):
    """Ejecuta una sentencia SQL de escritura, actualización o eliminación."""
    engine = _get_engine()
    with engine.begin() as conn:
        conn.execute(text(query), params or {})

# ---------- Catálogos y Consultas ----------
def obras_activas() -> pd.DataFrame:
    """Obtiene las obras desde la base de datos."""
    query = "SELECT id, nombre_obra as nombre, ubicacion, estado FROM obras"
    df = leer_sql(query)
    if not df.empty and "estado" in df.columns:
        df = df[df["estado"].fillna("").astype(str).str.strip().str.lower().isin(ESTADOS_OBRA_ACTIVA)]
    return df

def empleados_activos() -> pd.DataFrame:
    """Obtiene los usuarios con rol operativo o general desde la base de datos."""
    query = "SELECT id, dni, nombre, email, rol FROM usuarios"
    return leer_sql(query)

# ---------- Normalización y Utilidades ----------
def dni_str(serie: pd.Series) -> pd.Series:
    return serie.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)

def num(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie.astype(str).str.replace(",", ".", regex=False), errors="coerce")