import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración fija de la página
st.set_page_config(page_title="Inmobiliaria", layout="wide")

# 2. Conexión Estable
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. Tu enlace real (ID: 1d_G8VafPZp5jj3c1Io9kN3mG31GE70kK2Q2blxWzCCs)
URL_SHEET = "https://docs.google.com/spreadsheets/d/1d_G8VafPZp5jj3c1Io9kN3mG31GE70kK2Q2blxWzCCs/edit#gid=0"

st.title("🏡 Inmobiliaria")

# Sidebar - Menú de Navegación
menu = st.sidebar.selectbox(
    "Seleccionar Módulo",
    ["📍 Inventario de Terrenos", "👤 Gestión de Clientes", "💰 Abonos y Pagos", "📊 Reportes"]
)

# Botón global para refrescar datos
if st.sidebar.button("🔄 Actualizar Base de Datos"):
    st.cache_data.clear()
    st.rerun()

# --- MÓDULO: INVENTARIO ---
if menu == "📍 Inventario de Terrenos":
    st.header("Inventario de Lotes")
    try:
        df_terrenos = conn.read(spreadsheet=URL_SHEET, worksheet="terrenos")
        
        # Filtros rápidos
        col1, col2 = st.columns(2)
        with col1:
            filtro_estatus = st.multiselect("Filtrar por Estatus", options=df_terrenos["estatus"].unique(), default=df_terrenos["estatus"].unique())
        
        df_filtrado = df_terrenos[df_terrenos["estatus"].isin(filtro_estatus)]
        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
        
    except Exception as e:
        st.error("Asegúrate de que la pestaña se llame 'terrenos'")
        st.info("Nota: Si la hoja está vacía, agrega al menos una fila de datos en Google Sheets.")

# --- MÓDULO: CLIENTES ---
elif menu == "👤 Gestión de Clientes":
    st.header("Directorio de Clientes")
    try:
        df_clientes = conn.read(spreadsheet=URL_SHEET, worksheet="clientes")
        st.dataframe(df_clientes, use_container_width=True, hide_index=True)
        
        with st.expander("➕ Registrar Nuevo Cliente"):
            with st.form("form_cliente"):
                nombre = st.text_input("Nombre Completo")
                telefono = st.text_input("Teléfono")
                lote_interes = st.text_input("ID de Lote")
                if st.form_submit_button("Guardar"):
                    st.warning("Para guardar datos directamente, necesitaremos configurar permisos de escritura adicionales más adelante.")
    except:
        st.info("Pestaña 'clientes' no encontrada o vacía.")

# --- MÓDULO: ABONOS ---
elif menu == "💰 Abonos y Pagos":
    st.header("Control de Abonos y Comisiones")
    st.info("Próximamente: Aquí podrás seleccionar un cliente y registrar sus pagos mensuales.")
    
    # Simulación de vista de pagos
    try:
        df_pagos = conn.read(spreadsheet=URL_SHEET, worksheet="pagos")
        st.dataframe(df_pagos, use_container_width=True)
    except:
        st.write("Crea una pestaña llamada 'pagos' en tu Excel para ver este módulo.")

# --- MÓDULO: REPORTES ---
else:
    st.header("Resumen Ejecutivo")
    st.metric(label="Lotes Totales", value="24")
    st.metric(label="Lotes Vendidos", value="10", delta="40%")
