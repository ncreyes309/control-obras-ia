import os
import streamlit as st
from openai import OpenAI
from datetime import date
import auth

# Configuración inicial de la página
st.set_page_config(
    page_title="Control de Obras | Constructora Reyes Juan SRL", 
    page_icon="🏗️", 
    layout="wide"
)

# Ejecutamos la verificación de acceso y roles
auth.verificar_autenticacion()

# ---------------------------------------------------------
# BARRA LATERAL (SIDEBAR) - NAVEGACIÓN SEGÚN ROL
# ---------------------------------------------------------
st.sidebar.title("🏗️ Reyes Juan SRL")
st.sidebar.caption(f"Usuario: **{st.session_state['usuario_actual']}** ({st.session_state['rol_actual']})")

# Opciones de menú base para todos
opciones_menu = ["⏱️ Carga de Horas y Reportes IA", "📊 Resumen y Control"]

# Si el usuario actual es Administrador, agregamos la opción de gestión
if st.session_state["rol_actual"] == "Administrador":
    opciones_menu.append("👤 Gestión de Usuarios")

menu = st.sidebar.radio("Navegación", opciones_menu)

st.sidebar.markdown("---")
st.sidebar.header("Configuración")
api_key = st.sidebar.text_input("OpenAI API Key", type="password")

if api_key:
    os.environ["OPENAI_API_KEY"] = api_key

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.session_state["usuario_actual"] = ""
    st.session_state["rol_actual"] = ""
    st.rerun()

# ---------------------------------------------------------
# MÓDULO ADMINISTRADOR: GESTIÓN DE USUARIOS
# ---------------------------------------------------------
if menu == "👤 Gestión de Usuarios":
    st.title("👤 Alta y Gestión de Usuarios")
    st.markdown("Módulo exclusivo para Administradores de Constructora Reyes Juan SRL.")
    
    with st.form("form_alta_usuario"):
        st.subheader("➕ Registrar Nuevo Usuario")
        col1, col2 = st.columns(2)
        with col1:
            nuevo_user = st.text_input("Nombre de usuario (ej. pedro.perez)")
            nuevo_pass = st.text_input("Contraseña asignada", type="password")
        with col2:
            nuevo_rol = st.selectbox("Rol / Nivel de Permisos", ["Capataz", "Administrador", "Director de Obra"])
        
        btn_crear = st.form_submit_button("💾 Guardar Usuario")
        
        if btn_crear:
            if not nuevo_user.strip() or not nuevo_pass.strip():
                st.error("⚠️ Todos los campos son obligatorios.")
            else:
                exito, msj = auth.registrar_usuario(nuevo_user, nuevo_pass, nuevo_rol)
                if exito:
                    st.success(f"✅ {msj}")
                else:
                    st.error(f"⚠️ {msj}")

    st.markdown("---")
    st.subheader("📋 Usuarios Registrados en el Sistema")
    st.table([{"Usuario": u, "Rol": datos["rol"]} for u, datos in auth.USUARIOS.items()])

# ---------------------------------------------------------
# PÁGINA 1: CARGA DE HORAS Y REPORTES DE AVANCE CON IA
# ---------------------------------------------------------
elif menu == "⏱️ Carga de Horas y Reportes IA":
    st.title("🏗️ Sistema de Reportes y Horas de Obra")
    st.write("Panel para capataces y dirección de proyectos.")

    st.subheader("📝 Nuevo Reporte de Avance")

    with st.form("form_reporte"):
        obra_nombre = st.selectbox("Seleccionar Obra", ["Edificio Los Álamos", "Centro Comercial Norte", "Residencial San Martín"])
        porcentaje_avance = st.slider("Porcentaje de Avance Total (%)", 0.0, 100.0, 15.0)
        
        st.markdown("---")
        st.markdown("🕒 **Registro de Horas de la Semana**")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            operario_1 = st.text_input("Operario 1", "Juan Pérez")
            horas_1 = st.number_input("Horas Op. 1", 0.0, 60.0, 40.0)
        with col2:
            operario_2 = st.text_input("Operario 2", "Carlos Gómez")
            horas_2 = st.number_input("Horas Op. 2", 0.0, 60.0, 35.0)
        with col3:
            operario_3 = st.text_input("Operario 3", "Marcos Díaz")
            horas_3 = st.number_input("Horas Op. 3", 0.0, 60.0, 40.0)

        st.markdown("---")
        notas_crudas = st.text_area("Notas informales del capataz (¿Qué pasó esta semana en obra?)", 
                                   placeholder="Ej: Terminamos la loza del tercer piso, llovió el miércoles medio día...")
        
        enviado = st.form_submit_button("Generar y Enviar Reporte")

    if enviado:
        if not os.environ.get("OPENAI_API_KEY"):
            st.error("Por favor ingresa tu OpenAI API Key en la barra lateral.")
        else:
            with st.spinner("Generando informe ejecutivo con IA..."):
                try:
                    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
                    
                    lista_horas = [
                        {"empleado_nombre": operario_1, "horas": horas_1},
                        {"empleado_nombre": operario_2, "horas": horas_2},
                        {"empleado_nombre": operario_3, "horas": horas_3}
                    ]
                    total_horas = sum(item['horas'] for item in lista_horas)
                    detalle_horas = "\n".join([f"- {h['empleado_nombre']}: {h['horas']} hrs" for h in lista_horas])
                    
                    prompt = f"""
                    Eres un asistente experto en dirección de obras de construcción. 
                    Transforma las siguientes notas informales y el registro de horas en un reporte ejecutivo formal para el dueño de la empresa.

                    Obra: {obra_nombre}
                    Avance: {porcentaje_avance}%
                    Total Horas: {total_horas} hrs
                    Detalle:
                    {detalle_horas}

                    Notas del capataz: "{notas_crudas}"

                    Estructura el informe en: 1. Resumen Ejecutivo, 2. Avances Físicos, 3. Análisis de Mano de Obra, 4. Observaciones/Clima.
                    """
                    
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3
                    )
                    
                    reporte_final = response.choices[0].message.content
                    
                    st.success("¡Reporte generado con éxito!")
                    st.markdown("### 📊 Informe Ejecutivo para la Dirección")
                    st.markdown(reporte_final)
                    st.info(f"Total de horas registradas procesadas: {total_horas} horas.")
                    
                except Exception as e:
                    st.error(f"Ocurrió un error al conectar con la IA: {e}")

# ---------------------------------------------------------
# PÁGINA 2: RESUMEN Y CONTROL
# ---------------------------------------------------------
elif menu == "📊 Resumen y Control":
    st.header("📊 Panel de Control e Histórico")
    st.info("💡 **Próximamente:** Visualización de horas acumuladas por empleado y gráficos de control de costos por obra.")