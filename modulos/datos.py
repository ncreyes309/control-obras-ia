"""Acceso centralizado a Google Cloud SQL (PostgreSQL) mediante SQLAlchemy."""
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

TZ = ZoneInfo("America/Argentina/Buenos_Aires")

ESTADOS_OBRA_ACTIVA = ["activa", "en curso", "activo", ""]

# Empresa por defecto si el usuario logueado no tiene empresa_id (Constructora Reyes Juan SRL)
EMPRESA_ID_DEFECTO = 100

def empresa_actual() -> int:
    """empresa_id del usuario logueado (se guarda en la sesión al iniciar sesión)."""
    try:
        return int(st.session_state.get("empresa_id") or EMPRESA_ID_DEFECTO)
    except (TypeError, ValueError):
        return EMPRESA_ID_DEFECTO

# ---------- Conexión a Base de Datos ----------
@st.cache_resource
def _get_engine():
    """Crea UNA sola vez el motor de conexión a PostgreSQL (se reutiliza entre ejecuciones)."""
    cfg = st.secrets["postgres"]
    url = f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['database']}"
    return create_engine(url, pool_pre_ping=True)

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
    query = "SELECT id, empresa_id, dni, apellido, nombre, email, usuario, rol, activo FROM usuarios WHERE empresa_id = :empresa_id"
    params = {"empresa_id": empresa_id}
    df = leer_sql(query, params=params)
    # Renombramos dni a DNI para que coincida con la vista de la tabla
    if "dni" in df.columns:
        df = df.rename(columns={"dni": "DNI"})
    return df

def crear_usuario(empresa_id, dni, apellido, nombre, email, usuario, password_hash, rol):
    """Crea un nuevo usuario en PostgreSQL."""
    query = """
    INSERT INTO usuarios (empresa_id, dni, apellido, nombre, email, usuario, password, rol, activo, cambiar_clave)
    VALUES (:empresa_id, :dni, :apellido, :nombre, :email, :usuario, :password, :rol, 'si', 'si');
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
    query = "SELECT id, nombre_obra, ubicacion, estado FROM obras WHERE empresa_id = :empresa_id ORDER BY nombre_obra"
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

def actualizar_estado_obra(obra_id, empresa_id, estado):
    """Cambia el estado de una obra (activa, en curso, pausada, finalizada...)."""
    query = "UPDATE obras SET estado = :estado WHERE id = :id AND empresa_id = :empresa_id"
    try:
        ejecutar_sql(query, {"estado": estado, "id": int(obra_id), "empresa_id": int(empresa_id)})
        return True, f"Estado actualizado a '{estado}'."
    except Exception as e:
        return False, f"Error al actualizar la obra: {e}"

# ---------- Módulo 3: Gestión de Tareas ----------
def cargar_tareas(empresa_id: int) -> pd.DataFrame:
    """Obtiene todas las tareas para una empresa de PostgreSQL."""
    query = """
    SELECT t.id, t.obra_id, o.nombre_obra AS obra, t.nombre_tarea, t.descripcion, t.estado
    FROM tareas t
    LEFT JOIN obras o ON o.id = t.obra_id
    WHERE t.empresa_id = :empresa_id
    ORDER BY o.nombre_obra, t.nombre_tarea
    """
    params = {"empresa_id": empresa_id}
    return leer_sql(query, params=params)

def crear_tarea(empresa_id, nombre_tarea, descripcion, obra_id=None, estado="Pendiente"):
    """Crea una nueva tarea en PostgreSQL."""
    query = """
    INSERT INTO tareas (empresa_id, obra_id, nombre_tarea, descripcion, estado)
    VALUES (:empresa_id, :obra_id, :nombre_tarea, :descripcion, :estado);
    """
    params = {
        "empresa_id": empresa_id,
        "obra_id": int(obra_id) if obra_id is not None else None,
        "nombre_tarea": nombre_tarea,
        "descripcion": descripcion,
        "estado": estado,
    }
    try:
        ejecutar_sql(query, params)
        return True, f"Tarea '{nombre_tarea}' creada exitosamente."
    except Exception as e:
        if "unique" in str(e).lower() and "nombre_tarea" in str(e).lower():
            return False, f"La tarea '{nombre_tarea}' ya existe."
        return False, f"Error al crear tarea: {e}"
    
def actualizar_tarea(tarea_id, empresa_id, nombre_tarea, descripcion, estado=None):
    """Edita nombre, descripción y estado de una tarea existente (estado=None lo deja igual)."""
    query = """
    UPDATE tareas
    SET nombre_tarea = :nombre_tarea, descripcion = :descripcion, estado = COALESCE(:estado, estado)
    WHERE id = :id AND empresa_id = :empresa_id
    """
    params = {
        "nombre_tarea": nombre_tarea,
        "descripcion": descripcion,
        "estado": estado,
        "id": int(tarea_id),
        "empresa_id": int(empresa_id),
    }
    try:
        ejecutar_sql(query, params)
        return True, f"Tarea '{nombre_tarea}' actualizada."
    except Exception as e:
        if "unique" in str(e).lower() and "nombre_tarea" in str(e).lower():
            return False, f"Ya existe otra tarea llamada '{nombre_tarea}'."
        return False, f"Error al actualizar la tarea: {e}"

def empleados_activos() -> pd.DataFrame:
    """Obtiene los usuarios con rol operativo o general desde la base de datos."""
    query = "SELECT id, dni, nombre, email, rol FROM usuarios"
    return leer_sql(query)

# ---------- Módulo 4: Empleados, categorías y asignaciones a obras ----------
def cargar_categorias(empresa_id: int) -> pd.DataFrame:
    """Categorías laborales con su valor hora."""
    df = leer_sql(
        "SELECT id, nombre, valor_hora, activo FROM categorias WHERE empresa_id = :e ORDER BY nombre",
        {"e": int(empresa_id)},
    )
    df["valor_hora"] = pd.to_numeric(df["valor_hora"], errors="coerce")
    return df

def crear_categoria(empresa_id, nombre, valor_hora):
    query = "INSERT INTO categorias (empresa_id, nombre, valor_hora) VALUES (:e, :nombre, :valor)"
    try:
        ejecutar_sql(query, {"e": int(empresa_id), "nombre": nombre, "valor": float(valor_hora)})
        return True, f"Categoría '{nombre}' creada."
    except Exception as e:
        if "unique" in str(e).lower():
            return False, f"La categoría '{nombre}' ya existe."
        return False, f"Error al crear la categoría: {e}"

def actualizar_categoria(cat_id, empresa_id, nombre, valor_hora, activo):
    query = """
    UPDATE categorias SET nombre = :nombre, valor_hora = :valor, activo = :activo
    WHERE id = :id AND empresa_id = :e
    """
    try:
        ejecutar_sql(query, {"nombre": nombre, "valor": float(valor_hora), "activo": bool(activo),
                             "id": int(cat_id), "e": int(empresa_id)})
        return True, f"Categoría '{nombre}' actualizada."
    except Exception as e:
        if "unique" in str(e).lower():
            return False, f"Ya existe otra categoría llamada '{nombre}'."
        return False, f"Error al actualizar la categoría: {e}"

def cargar_empleados(empresa_id: int) -> pd.DataFrame:
    query = """
    SELECT e.id, e.dni, e.cuil, e.apellido, e.nombre, e.categoria_id,
           c.nombre AS categoria, c.valor_hora, e.telefono, e.fecha_ingreso, e.activo
    FROM empleados e
    LEFT JOIN categorias c ON c.id = e.categoria_id
    WHERE e.empresa_id = :e
    ORDER BY e.apellido, e.nombre
    """
    df = leer_sql(query, {"e": int(empresa_id)})
    df["valor_hora"] = pd.to_numeric(df["valor_hora"], errors="coerce")
    return df

def crear_empleado(empresa_id, dni, cuil, apellido, nombre, categoria_id, telefono, fecha_ingreso):
    query = """
    INSERT INTO empleados (empresa_id, dni, cuil, apellido, nombre, categoria_id, telefono, fecha_ingreso)
    VALUES (:e, :dni, :cuil, :apellido, :nombre, :categoria_id, :telefono, :fecha_ingreso)
    """
    params = {
        "e": int(empresa_id), "dni": dni, "cuil": cuil or None, "apellido": apellido, "nombre": nombre,
        "categoria_id": int(categoria_id) if categoria_id is not None else None,
        "telefono": telefono or None, "fecha_ingreso": fecha_ingreso,
    }
    try:
        ejecutar_sql(query, params)
        return True, f"Empleado {apellido}, {nombre} registrado."
    except Exception as e:
        if "unique" in str(e).lower():
            return False, f"Ya existe un empleado con el DNI '{dni}'."
        return False, f"Error al crear el empleado: {e}"

def actualizar_empleado(emp_id, empresa_id, cuil, apellido, nombre, categoria_id, telefono, activo):
    query = """
    UPDATE empleados
    SET cuil = :cuil, apellido = :apellido, nombre = :nombre, categoria_id = :categoria_id,
        telefono = :telefono, activo = :activo
    WHERE id = :id AND empresa_id = :e
    """
    params = {
        "cuil": cuil or None, "apellido": apellido, "nombre": nombre,
        "categoria_id": int(categoria_id) if categoria_id is not None else None,
        "telefono": telefono or None, "activo": bool(activo),
        "id": int(emp_id), "e": int(empresa_id),
    }
    try:
        ejecutar_sql(query, params)
        return True, f"Empleado {apellido}, {nombre} actualizado."
    except Exception as e:
        return False, f"Error al actualizar el empleado: {e}"

def cargar_asignaciones(empresa_id: int) -> pd.DataFrame:
    """Asignaciones de empleados a obras (vigentes e históricas)."""
    query = """
    SELECT a.id, a.empleado_id, a.obra_id, e.dni, e.apellido, e.nombre,
           o.nombre_obra AS obra, a.fecha_desde, a.fecha_hasta
    FROM empleado_obra a
    JOIN empleados e ON e.id = a.empleado_id
    JOIN obras o ON o.id = a.obra_id
    WHERE e.empresa_id = :e
    ORDER BY o.nombre_obra, e.apellido, e.nombre
    """
    return leer_sql(query, {"e": int(empresa_id)})

def asignar_empleado_obra(empleado_id, obra_id, fecha_desde):
    query = "INSERT INTO empleado_obra (empleado_id, obra_id, fecha_desde) VALUES (:emp, :obra, :desde)"
    try:
        ejecutar_sql(query, {"emp": int(empleado_id), "obra": int(obra_id), "desde": fecha_desde})
        return True, "Asignación creada."
    except Exception as e:
        if "unique" in str(e).lower():
            return False, "El empleado ya está asignado a esa obra."
        return False, f"Error al asignar: {e}"

def cerrar_asignacion(asignacion_id, empresa_id, fecha_hasta):
    query = """
    UPDATE empleado_obra SET fecha_hasta = :hasta
    WHERE id = :id AND empleado_id IN (SELECT id FROM empleados WHERE empresa_id = :e)
    """
    try:
        ejecutar_sql(query, {"hasta": fecha_hasta, "id": int(asignacion_id), "e": int(empresa_id)})
        return True, "Asignación finalizada."
    except Exception as e:
        if "check" in str(e).lower():
            return False, "La fecha de fin no puede ser anterior a la de inicio."
        return False, f"Error al finalizar la asignación: {e}"

# ---------- Módulo 5: Planificación diaria de personal ----------
def cargar_planificacion(empresa_id: int, fecha) -> pd.DataFrame:
    """Personal planificado en TODAS las obras para una fecha."""
    query = """
    SELECT p.id, p.fecha, p.obra_id, o.nombre_obra AS obra, p.empleado_id,
           e.dni, e.apellido, e.nombre
    FROM planificacion_diaria p
    JOIN empleados e ON e.id = p.empleado_id
    JOIN obras o ON o.id = p.obra_id
    WHERE p.fecha = :fecha AND e.empresa_id = :e
    ORDER BY o.nombre_obra, e.apellido, e.nombre
    """
    return leer_sql(query, {"fecha": fecha, "e": int(empresa_id)})

def planificar_dia(empresa_id, fecha, obra_id, empleado_ids):
    """Deja exactamente a `empleado_ids` planificados en esa obra y fecha (altas y bajas, en una transacción)."""
    ids = [int(i) for i in empleado_ids]
    params = {"fecha": fecha, "obra": int(obra_id), "e": int(empresa_id), "ids": ids}
    try:
        engine = _get_engine()
        with engine.begin() as conn:
            conn.execute(text("""
                DELETE FROM planificacion_diaria p USING empleados e
                WHERE p.empleado_id = e.id AND e.empresa_id = :e
                  AND p.fecha = :fecha AND p.obra_id = :obra
                  AND NOT (p.empleado_id = ANY(:ids))
            """), params)
            if ids:
                conn.execute(text("""
                    INSERT INTO planificacion_diaria (fecha, obra_id, empleado_id)
                    SELECT :fecha, :obra, e.id FROM empleados e
                    WHERE e.id = ANY(:ids) AND e.empresa_id = :e AND e.activo
                    ON CONFLICT DO NOTHING
                """), params)
        return True, f"Planificación guardada ({len(ids)} empleado(s))."
    except Exception as e:
        return False, f"Error al guardar la planificación: {e}"

def copiar_planificacion(empresa_id, fecha_origen, fecha_destino):
    """Copia la planificación de un día a otro (suma a lo que ya haya, sin duplicar)."""
    query = """
    INSERT INTO planificacion_diaria (fecha, obra_id, empleado_id)
    SELECT :destino, p.obra_id, p.empleado_id
    FROM planificacion_diaria p
    JOIN empleados e ON e.id = p.empleado_id
    WHERE p.fecha = :origen AND e.empresa_id = :e AND e.activo
    ON CONFLICT DO NOTHING
    """
    try:
        engine = _get_engine()
        with engine.begin() as conn:
            res = conn.execute(text(query), {"origen": fecha_origen, "destino": fecha_destino, "e": int(empresa_id)})
        return True, f"Se copiaron {res.rowcount} asignación(es)."
    except Exception as e:
        return False, f"Error al copiar la planificación: {e}"

def empleados_planificados(empresa_id: int, obra_id: int, fecha) -> pd.DataFrame:
    """Empleados activos planificados en una obra para una fecha (los que se ven en Carga de Horas)."""
    query = """
    SELECT e.id, e.dni, e.apellido, e.nombre, c.nombre AS categoria
    FROM planificacion_diaria p
    JOIN empleados e ON e.id = p.empleado_id
    LEFT JOIN categorias c ON c.id = e.categoria_id
    WHERE p.fecha = :fecha AND p.obra_id = :obra AND e.empresa_id = :e AND e.activo
    ORDER BY e.apellido, e.nombre
    """
    df = leer_sql(query, {"fecha": fecha, "obra": int(obra_id), "e": int(empresa_id)})
    if not df.empty:
        df["dni"] = dni_str(df["dni"])
    return df

# ---------- Normalización y Utilidades ----------
def dni_str(serie: pd.Series) -> pd.Series:
    return serie.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)

def num(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie.astype(str).str.replace(",", ".", regex=False), errors="coerce")