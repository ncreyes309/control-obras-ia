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
    url = f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['database']}"
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

# ---------- Módulo 1: Gestión de Usuarios (Empleados) ----------
def cargar_todos_usuarios(empresa_id: int) -> pd.DataFrame:
    """Obtiene todos los usuarios para una empresa de PostgreSQL."""
    query = "SELECT id, empresa_id, dni as DNI, apellido, nombre, email, usuario, rol, activo FROM usuarios WHERE empresa_id = :empresa_id"
    params = {"empresa_id": empresa_id}
    return leer_sql(query, params=params)

def crear_usuario(empresa_id, dni, apellido, nombre, email, usuario, password_hash, rol):
    """Crea un nuevo usuario en PostgreSQL."""
    query = """
    INSERT INTO usuarios (empresa_id, dni, apellido, nombre, email, usuario, password, rol)
    VALUES (:empresa_id, :dni, :apellido, :nombre, :email, :usuario, :password, :rol);
    """
    params = {
        "empresa_id": empresa_id,
        "dni": dni,
        "apellido": apellido,
        "nombre": nombre,
        "email": email,
        "usuario": usuario,
        "password": password_hash, # La contraseña ya viene hasheada desde auth.py
        "rol": rol
    }
    try:
        ejecutar_sql(query, params)
        return True, f"Usuario '{usuario}' creado exitosamente."
    except Exception as e:
        error_str = str(e).lower()
        if "unique" in error_str and "usuario" in error_str:
            return False, f"El nombre de usuario '{usuario}' ya está registrado."
        elif "unique" in error_str and "dni" in error_str:
            return False, f"El DNI '{dni}' ya pertenece a otro usuario."
        return False, f"Error al crear usuario: {e}"

# ---------- Módulo 2: Gestión de Obras ----------
def obras_activas() -> pd.DataFrame:
    """Obtiene las obras activas de PostgreSQL (para combos de selección)."""
    query = "SELECT id, nombre_obra as nombre, ubicacion, estado FROM obras"
    df = leer_sql(query)
    if not df.empty and "estado" in df.columns:
        df = df[df["estado"].fillna("").astype(str).str.strip().str.lower().isin(ESTADOS_OBRA_ACTIVA)]
    return df

def cargar_todas_obras(empresa_id: int) -> pd.DataFrame:
    """Obtiene todas las obras para una empresa de PostgreSQL."""
    query = "SELECT id, nombre_obra, ubicacion, estado, created_at as fecha_creacion FROM obras WHERE empresa_id = :empresa_id"
    params = {"empresa_id": empresa_id}
    return leer_sql(query, params=params)

def crear_obra(empresa_id, nombre_obra, ubicacion, estado):
    """Crea una nueva obra en PostgreSQL."""
    query = """
    INSERT INTO obras (empresa_id, nombre_obra, ubicacion, estado)
    VALUES (:empresa_id, :nombre_obra, :ubicacion, :estado);
    """
    params = {
        "empresa_id": empresa_id,
        "nombre_obra": nombre_obra,
        "ubicacion": ubicacion,
        "estado": estado
    }
    try:
        ejecutar_sql(query, params)
        return True, f"Obra '{nombre_obra}' creada exitosamente."
    except Exception as e:
        return False, f"Error al crear obra: {e}"

# ---------- Módulo 3: Gestión de Tareas ----------
def cargar_tareas(empresa_id: int) -> pd.DataFrame:
    """Obtiene todas las tareas para una empresa de PostgreSQL."""
    query = "SELECT id, nombre_tarea, descripcion FROM tareas WHERE empresa_id = :empresa_id"
    params = {"empresa_id": empresa_id}
    return leer_sql(query, params=params)

def crear_tarea(empresa_id, nombre_tarea, descripcion):
    """Crea una nueva tarea en PostgreSQL."""
    query = """
    INSERT INTO tareas (empresa_id, nombre_tarea, descripcion)
    VALUES (:empresa_id, :nombre_tarea, :descripcion);
    """
    params = {
        "empresa_id": empresa_id,
        "nombre_tarea": nombre_tarea,
        "descripcion": descripcion
    }
    try:
        ejecutar_sql(query, params)
        return True, f"Tarea '{nombre_tarea}' creada exitosamente."
    except Exception as e:
        if "unique" in str(e).lower() and "nombre_tarea" in str(e).lower():
            return False, f"La tarea '{nombre_tarea}' ya existe."
        return False, f"Error al crear tarea: {e}"
    
def empleados_activos() -> pd.DataFrame:
    """Obtiene los usuarios con rol operativo o general desde la base de datos."""
    query = "SELECT id, dni, nombre, email, rol FROM usuarios"
    return leer_sql(query)

# ---------- Normalización y Utilidades ----------
def dni_str(serie: pd.Series) -> pd.Series:
    return serie.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)

def num(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie.astype(str).str.replace(",", ".", regex=False), errors="coerce")