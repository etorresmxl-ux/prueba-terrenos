import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# CONFIGURACIÓN DE LA APP
st.set_page_config(page_title="Gestión Inmobiliaria Pro", layout="wide")

# CONEXIÓN SEGURA
# Nota: No pasamos 'creds' aquí porque Streamlit los lee de los Secrets automáticamente
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# LINK DE TU HOJA (Cámbialo por el tuyo)
URL_SHEET = "https://docs.google.com/spreadsheets/d/TU_NUEVO_ID_AQUI/"

# INTERFAZ PRINCIPAL
st.title("🏡 Sistema de Gestión Inmobiliaria")

menu = st.sidebar.selectbox("Seleccione una opción:", 
    ["📊 Resumen General", "📍 Inventario de Terrenos", "👤 Gestión de Clientes", "💰 Abonos y Pagos"])

# --- SECCIÓN: INVENTARIO ---
if menu == "📍 Inventario de Terrenos":
    st.header("Inventario de Lotes")
    try:
        df_lotes = conn.read(spreadsheet=URL_SHEET, worksheet="terrenos")
        st.dataframe(df_lotes, use_container_width=True)
        
        with st.expander("➕ Agregar nuevo lote"):
            with st.form("nuevo_lote"):
                mz = st.text_input("Manzana")
                lt = st.text_input("Lote")
                precio = st.number_input("Precio de venta", min_value=0)
                if st.form_submit_button("Guardar en Drive"):
                    st.info("Función de guardado lista para programar en el siguiente paso.")
    except Exception as e:
        st.error(f"Error al leer 'terrenos': {e}")

# --- SECCIÓN: CLIENTES ---
elif menu == "👤 Gestión de Clientes":
    st.header("Directorio de Clientes")
    try:
        df_clientes = conn.read(spreadsheet=URL_SHEET, worksheet="clientes")
        st.dataframe(df_clientes, use_container_width=True)
    except Exception as e:
        st.error(f"Error al leer 'clientes': {e}")

# --- SECCIÓN: ABONOS (LO QUE VIENE) ---
elif menu == "💰 Abonos y Pagos":
    st.header("Control de Pagos y Comisiones")
    st.info("Aquí registraremos los abonos mensuales y calcularemos las comisiones de los vendedores.")

else:
    st.subheader("Bienvenido al sistema")
    st.write("Selecciona una opción en el menú de la izquierda para comenzar.")
