"""Acceso al sistema: login, contraseñas con hash, usuarios activos/inactivos y cambio de clave.

Tabla 'usuarios' en Google Cloud SQL (PostgreSQL).
Columnas obligatorias: DNI, apellido, nombre, usuario, password, rol.
Columnas opcionales: activo (si/no), cambiar_clave (si/no).
"""
import hmac

import bcrypt
import pandas as pd
import streamlit as st
from sqlalchemy import inspect, text

from modulos import datos

MAX_INTENTOS = 5
MIN_PASSWORD = 8
ROLES = ["Administrador", "Gerente", "Director de Obras", "Abogada", "Administrativo General", "Capataz"]

# ---------- Contraseñas ----------
def es_hash(valor) -> bool:
    return str(valor).startswith("$2")

def hashear_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verificar_password(ingresada: str, almacenada) -> bool:
    almacenada = str(almacenada)
    if es_hash(almacenada):
        try:
            return bcrypt.checkpw(ingresada.encode("utf-8"), almacenada.encode("utf-8"))
        except ValueError:
            return False
    # Contraseña vieja en texto plano: solo hasta que se migre
    return hmac.compare_digest(ingresada, almacenada)

def validar_password_nueva(nueva: str, actual: str = ""):
    if len(nueva) < MIN_PASSWORD:
        return False, f"La contraseña debe tener al menos {MIN_PASSWORD} caracteres."
    if len(nueva.encode("utf-8")) > 72:
        return False, "La contraseña es demasiado larga (máximo 72 caracteres)."
    if actual and nueva == actual:
        return False, "La nueva contraseña debe ser distinta de la actual."
    return True, ""

# ---------- Acceso a los usuarios (PostgreSQL) ----------
def cargar_usuarios() -> pd.DataFrame:
    """Carga los usuarios directamente desde la tabla PostgreSQL."""
    query = "SELECT id, empresa_id, dni, apellido, nombre, usuario, password, rol, activo, cambiar_clave FROM usuarios"
    try:
        df = datos.leer_sql(query)
    except Exception:
        df = datos.leer_sql("SELECT * FROM usuarios")
    return df.fillna("")

def guardar_usuarios(df: pd.DataFrame) -> None:
    """Actualiza (UPDATE por id) solo las filas existentes, sin tocar la estructura de la tabla."""
    engine = datos._get_engine()
    cols_db = {c["name"] for c in inspect(engine).get_columns("usuarios")}
    editables = [c for c in ("password", "rol", "activo", "cambiar_clave") if c in df.columns and c in cols_db]
    if "id" not in df.columns or not editables:
        raise ValueError("No se puede guardar: falta la columna 'id' o no hay columnas editables.")
    sets = ", ".join(f"{c} = :{c}" for c in editables)
    query = text(f"UPDATE usuarios SET {sets} WHERE id = :id")
    with engine.begin() as conn:  # una sola transacción: o se guarda todo o nada
        for _, fila in df.iterrows():
            if str(fila["id"]).strip() == "":
                continue
            params = {c: (None if c != "password" and fila[c] == "" else fila[c]) for c in editables}
            params["id"] = int(fila["id"])
            conn.execute(query, params)

def guardar_usuario_db(usuario_dict: dict):
    """Inserta un usuario directamente en la base de datos."""
    query = """
        INSERT INTO usuarios (empresa_id, dni, nombre, email, password, rol)
        VALUES (:empresa_id, :dni, :nombre, :email, :password, :rol)
    """
    datos.ejecutar_sql(query, {
        "empresa_id": usuario_dict.get("empresa_id", 1),
        "dni": usuario_dict.get("dni"),
        "nombre": f"{usuario_dict.get('apellido', '')} {usuario_dict.get('nombre', '')}".strip(),
        "email": usuario_dict.get("usuario", "user") + "@constructora.com",
        "password": usuario_dict.get("password"),
        "rol": usuario_dict.get("rol")
    })

def _col(df: pd.DataFrame, nombre: str):
    for c in df.columns:
        if str(c).strip().lower() == nombre:
            return c
    raise KeyError(f"Falta la columna '{nombre}' en la tabla usuarios")

def _col_opcional(df: pd.DataFrame, nombre: str, crear: bool = False):
    for c in df.columns:
        if str(c).strip().lower() == nombre:
            return c
    if crear:
        df[nombre] = ""
        return nombre
    return None

def _buscar(df: pd.DataFrame, c_user, usuario: str):
    """Índice de la fila del usuario (sin distinguir mayúsculas), o None."""
    mask = df[c_user].astype(str).str.strip().str.lower() == usuario.strip().lower()
    return df.index[mask][0] if mask.any() else None

def _esta_activo(fila, c_activo) -> bool:
    if c_activo is None:
        return True
    return str(fila[c_activo]).strip().lower() not in ("no", "false", "0", "inactivo")

def _es_si(valor) -> bool:
    return str(valor).strip().lower() in ("si", "sí", "true", "1", "x", "yes")

def _normalizar_rol(valor) -> str:
    """Devuelve el rol con su escritura oficial."""
    texto = str(valor).strip()
    for rol in ROLES:
        if rol.lower() == texto.lower():
            return rol
    return texto

def _requiere_admin() -> None:
    if st.session_state.get("rol_actual") != "Administrador":
        raise PermissionError("Solo el Administrador puede hacer esto.")

# ---------- Sesión ----------
def cerrar_sesion() -> None:
    st.session_state["autenticado"] = False
    st.session_state["usuario_actual"] = ""
    st.session_state["rol_actual"] = ""
    st.session_state["empresa_id"] = None
    st.session_state["debe_cambiar_clave"] = False

def verificar_autenticacion() -> bool:
    st.session_state.setdefault("autenticado", False)
    st.session_state.setdefault("usuario_actual", "")
    st.session_state.setdefault("rol_actual", "")
    st.session_state.setdefault("intentos_login", 0)
    st.session_state.setdefault("debe_cambiar_clave", False)

    if st.session_state["autenticado"]:
        if st.session_state["debe_cambiar_clave"]:
            _pantalla_cambio_obligatorio()
            return False
        return True

    st.subheader("🔐 Acceso al Sistema de Control")

    if st.session_state["intentos_login"] >= MAX_INTENTOS:
        st.error("Demasiados intentos fallidos. Recargá la página e intentá de nuevo en unos minutos.")
        return False

    with st.form("form_login"):
        usuario_input = st.text_input("Usuario").strip()
        password_input = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("Ingresar")

    if not submit:
        return False

    ingreso_ok = False
    try:
        df = cargar_usuarios()
        c_user, c_pass, c_rol = _col(df, "usuario"), _col(df, "password"), _col(df, "rol")
        c_activo, c_cc = _col_opcional(df, "activo"), _col_opcional(df, "cambiar_clave")

        idx = _buscar(df, c_user, usuario_input) if usuario_input else None

        if idx is None or not verificar_password(password_input, df.at[idx, c_pass]):
            st.session_state["intentos_login"] += 1
            st.error("Usuario o contraseña incorrectos.")
            return False

        fila = df.loc[idx]
        if not _esta_activo(fila, c_activo):
            st.error("Tu usuario está desactivado. Consultá con el administrador.")
            return False

        # Si todavía estaba en texto plano, la guardamos con hash llamando a la función global
        if not es_hash(fila[c_pass]):
            df.at[idx, c_pass] = hashear_password(password_input)
            guardar_usuarios(df)

        st.session_state["autenticado"] = True
        st.session_state["usuario_actual"] = str(fila[c_user]).strip()
        c_emp = _col_opcional(df, "empresa_id")
        emp = pd.to_numeric(fila[c_emp], errors="coerce") if c_emp else None
        st.session_state["empresa_id"] = int(emp) if emp is not None and pd.notna(emp) else datos.EMPRESA_ID_DEFECTO
        st.session_state["rol_actual"] = _normalizar_rol(fila[c_rol])
        st.session_state["debe_cambiar_clave"] = bool(c_cc and _es_si(fila[c_cc]))
        st.session_state["intentos_login"] = 0
        ingreso_ok = True
    except Exception as e:
        st.error(f"Error al conectar con la base de datos de usuarios: {e}")

    if ingreso_ok:
        st.rerun()
    return False


# ---------- Cambio de contraseña ----------
def cambiar_password(usuario: str, actual: str, nueva: str):
    try:
        df = cargar_usuarios()
        c_user, c_pass = _col(df, "usuario"), _col(df, "password")
        idx = _buscar(df, c_user, usuario)
        if idx is None:
            return False, "Usuario no encontrado."
        if not verificar_password(actual, df.at[idx, c_pass]):
            return False, "La contraseña actual no es correcta."
        ok, msj = validar_password_nueva(nueva, actual)
        if not ok:
            return False, msj
        df.at[idx, c_pass] = hashear_password(nueva)
        c_cc = _col_opcional(df, "cambiar_clave")
        if c_cc:
            df.at[idx, c_cc] = "no"
        guardar_usuarios(df)
        return True, "Contraseña actualizada."
    except Exception as e:
        return False, str(e)


def formulario_cambiar_password(clave: str = "cambio_pass") -> bool:
    """Formulario reutilizable. Devuelve True cuando se cambió la contraseña."""
    with st.form(clave, clear_on_submit=True):
        actual = st.text_input("Contraseña actual", type="password")
        nueva = st.text_input("Nueva contraseña", type="password")
        repetir = st.text_input("Repetir la nueva contraseña", type="password")
        enviar = st.form_submit_button("Cambiar contraseña")

    if not enviar:
        return False
    if nueva != repetir:
        st.error("Las contraseñas nuevas no coinciden.")
        return False
    ok, msj = cambiar_password(st.session_state["usuario_actual"], actual, nueva)
    (st.success if ok else st.error)(msj)
    return ok


def _pantalla_cambio_obligatorio() -> None:
    st.subheader("🔑 Elegí tu contraseña")
    st.info("Estás usando una contraseña temporal. Cambiala para poder continuar.")
    if formulario_cambiar_password("cambio_obligatorio"):
        st.session_state["debe_cambiar_clave"] = False
        st.rerun()
    if st.button("Cerrar sesión", key="salir_cambio"):
        cerrar_sesion()
        st.rerun()


# ---------- Administración de usuarios (solo Administrador) ----------
def registrar_usuario(dni, apellido, nombre, usuario, password, rol):
    """Alta de usuario con contraseña temporal."""
    try:
        _requiere_admin()
        usuario = str(usuario).strip()
        if not usuario:
            return False, "El usuario no puede estar vacío."
        if rol not in ROLES:
            return False, "Rol inválido."
        ok, msj = validar_password_nueva(password)
        if not ok:
            return False, msj

        df = cargar_usuarios()
        c_user = _col(df, "usuario")
        if _buscar(df, c_user, usuario) is not None:
            return False, "El nombre de usuario ya está registrado."

        return datos.crear_usuario(datos.empresa_actual(), str(dni).strip(), apellido.strip(), nombre.strip(), "",
                                   usuario, hashear_password(password), rol)
    except Exception as e:
        return False, str(e)


def resetear_password(usuario: str, temporal: str):
    try:
        _requiere_admin()
        ok, msj = validar_password_nueva(temporal)
        if not ok:
            return False, msj
        df = cargar_usuarios()
        c_user, c_pass = _col(df, "usuario"), _col(df, "password")
        idx = _buscar(df, c_user, usuario)
        if idx is None:
            return False, "Usuario no encontrado."
        df.at[idx, c_pass] = hashear_password(temporal)
        c_cc = _col_opcional(df, "cambiar_clave", crear=True)
        df.at[idx, c_cc] = "si"
        guardar_usuarios(df)
        return True, "Contraseña temporal asignada. Deberá cambiarla al ingresar."
    except Exception as e:
        return False, str(e)


def set_activo(usuario: str, activo: bool):
    try:
        _requiere_admin()
        if not activo and usuario.strip().lower() == st.session_state["usuario_actual"].strip().lower():
            return False, "No podés desactivar tu propio usuario."
        df = cargar_usuarios()
        c_user = _col(df, "usuario")
        idx = _buscar(df, c_user, usuario)
        if idx is None:
            return False, "Usuario no encontrado."
        c_activo = _col_opcional(df, "activo", crear=True)
        df.at[idx, c_activo] = "si" if activo else "no"
        guardar_usuarios(df)
        return True, "Usuario activado." if activo else "Usuario desactivado."
    except Exception as e:
        return False, str(e)

def migrar_passwords() -> int:
    """Guarda con hash todas las contraseñas que sigan en texto plano."""
    _requiere_admin()
    df = cargar_usuarios()
    c_pass = _col(df, "password")
    cambios = 0
    for idx, valor in df[c_pass].items():
        if str(valor).strip() and not es_hash(valor):
            df.at[idx, c_pass] = hashear_password(str(valor))
            cambios += 1
    if cambios:
        guardar_usuarios(df)
    return cambios