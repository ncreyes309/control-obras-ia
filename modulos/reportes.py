import os
import streamlit as st
from openai import OpenAI

def mostrar_modulo():
    st.title("🏗️ Sistema de Reportes y Horas de Obra")
    st.write("Panel para capataces y dirección de proyectos.")

    st.sidebar.markdown("---")
    st.sidebar.header("Configuración de IA")
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")

    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key

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