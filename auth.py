import hmac

import bcrypt
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

HOJA_USUARIOS = "Usuarios"
MAX_INTENTOS = 5


# ---------- Utilidades de contraseña ----------
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
    # Contraseña vieja en texto plano (solo hasta que se migre)
    return hmac.compare_digest(ingresada, almacenada)


# ---------- Acceso a la hoja ----------
def _conn():
    return st.connection("gsheets", type=GSheetsConnection)


def cargar_usuarios() -> pd.DataFrame:
    return _conn().read(worksheet=HOJA_USUARIOS, ttl=0)


def _col(df: pd.DataFrame, nombre: str):
    """Devuelve el nombre real de la columna ignorando mayúsculas y espacios."""
    for c in df.columns:
        if str(c).strip().lower() == nombre:
            return c
    raise KeyError(f"Falta la columna '{nombre}' en la hoja {HOJA_USUARIOS}")


def migrar_passwords() -> int:
    """Hashea todas las contraseñas que sigan en texto plano. Devuelve cuántas migró."""
    df = cargar_usuarios()
    col_pass = _col(df, "password")
    cambios = 0
    for idx, valor in df[col_pass].items():
        if pd.notna(valor) and not es_hash(valor):
            df.at[idx, col_pass] = hashear_password(str(valor))
            cambios += 1
    if cambios:
        _conn().update(worksheet=HOJA_USUARIOS, data=df)
    return cambios


# ---------- Login ----------
def verificar_autenticacion():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
        st.session_state["usuario_actual"] = ""
        st.session_state["rol_actual"] = ""
    st.session_state.setdefault("intentos_login", 0)

    if st.session_state["autenticado"]:
        return True

    st.subheader("🔐 Acceso al Sistema de Control")

    if st.session_state["intentos_login"] >= MAX_INTENTOS:
        st.error("Demasiados intentos fallidos. Recargá la página e intentá de nuevo en unos minutos.")
        return False

    with st.form("form_login"):
        usuario_input = st.text_input("Usuario").strip()
        password_input = st.text_input("Contraseña", type="password")
        submit_login = st.form_submit_button("Ingresar")

    if submit_login:
        try:
            df = cargar_usuarios()
            c_user, c_pass, c_rol = _col(df, "usuario"), _col(df, "password"), _col(df, "rol")

            match = df[df[c_user].astype(str).str.strip() == usuario_input]

            # Mensaje genérico: no revelamos si el usuario existe o no
            if match.empty or not verificar_password(password_input, match.iloc[0][c_pass]):
                st.session_state["intentos_login"] += 1
                st.error("Usuario o contraseña incorrectos.")
                return False

            fila = match.iloc[0]

            # Si todavía estaba en texto plano, la hasheamos ahora
            if not es_hash(fila[c_pass]):
                df.at[match.index[0], c_pass] = hashear_password(password_input)
                _conn().update(worksheet=HOJA_USUARIOS, data=df)

            st.session_state["autenticado"] = True
            st.session_state["usuario_actual"] = str(fila[c_user]).strip()
            st.session_state["rol_actual"] = str(fila[c_rol]).strip()
            st.session_state["intentos_login"] = 0
            st.rerun()
        except Exception as e:
            st.error(f"Error al conectar con la base de datos de usuarios: {e}")
    return False


# ---------- Alta de usuarios ----------
def registrar_usuario(dni, apellido, nombre, usuario, password, rol):
    try:
        df_actual = cargar_usuarios()
        c_user = _col(df_actual, "usuario")

        if not df_actual[df_actual[c_user].astype(str).str.strip() == str(usuario).strip()].empty:
            return False, "El nombre de usuario ya está registrado."

        nuevo = pd.DataFrame([{
            "DNI": str(dni),
            "apellido": apellido,
            "nombre": nombre,
            "usuario": str(usuario).strip(),
            "password": hashear_password(password),
            "rol": rol,
        }])

        df_nuevo = pd.concat([df_actual, nuevo], ignore_index=True)
        _conn().update(worksheet=HOJA_USUARIOS, data=df_nuevo)
        return True, "Usuario registrado con éxito."
    except Exception as e:
        return False, str(e)
