import streamlit as st
from streamlit_gsheets import GSheetsConnection

# 1. Configuración básica
st.set_page_config(page_title="Inmobiliaria", layout="wide")

# 2. Conexión automática (Streamlit busca solito los [connections.gsheets] que guardaste)
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. PEGA AQUÍ TU LINK DE GOOGLE SHEETS
# Asegúrate de que termine en /edit o algo similar
URL_SHEET = "https://docs.google.com/spreadsheets/d/1d_G8VafPZp5jj3c1Io9kN3mG31GE70kK2Q2blxWzCCs/"

st.title("🏡 Sistema de Gestión Inmobiliaria")

# Botón para forzar la actualización de datos
if st.sidebar.button("🔄 Refrescar Datos"):
    st.cache_data.clear()
    st.rerun()

try:
    # 4. Intentamos leer la pestaña 'terrenos'
    # Si tu pestaña tiene otro nombre (ej. Sheet1), cámbialo aquí abajo
    df = conn.read(spreadsheet=URL_SHEET, worksheet="terrenos")
    
    st.success("✅ ¡Conexión Exitosa con Google Sheets!")
    st.write("### Vista de Terrenos")
    st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error("❌ No se pudieron cargar los datos.")
    st.info("Cosas a revisar:")
    st.markdown("""
    1. ¿Compartiste el Excel con el correo `inmobiliaria-2026@agile-terra-487416-e3.iam.gserviceaccount.com`?
    2. ¿La pestaña se llama exactamente **terrenos**?
    3. ¿El link de la URL es el correcto?
    """)
    # Esto te mostrará el error técnico si algo falla
    st.exception(e)
