import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de la página (Título fijo como solicitaste)
st.set_page_config(page_title="Inmobiliaria", layout="wide")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. URL de tu base de datos
URL_SHEET = "https://docs.google.com/spreadsheets/d/1d_G8VafPZp5jj3c1Io9kN3mG31GE70kK2Q2blxWzCCs/edit#gid=0"

# --- BARRA LATERAL (MENÚ) ---
st.sidebar.title("Navegación")

# Estructura de menú solicitada
menu = st.sidebar.radio(
    "Seleccione una sección:",
    [
        "🏠 Inicio", 
        "📝 Ventas", 
        "💰 Cobranza", 
        "📅 Historial de Pagos", 
        "📂 Gestión de Contratos", 
        "📈 Comisiones"
    ]
)

st.sidebar.markdown("---")

# Botón para actualizar la base de datos
if st.sidebar.button("🔄 Actualizar Base de Datos"):
    st.cache_data.clear()
    st.rerun()

# --- LÓGICA DE LAS SECCIONES ---

st.title(f"Inmobiliaria - {menu[2:]}") # Muestra el nombre sin el emoji

if menu == "🏠 Inicio":
    st.subheader("Resumen de Créditos Activos")
    st.info("Aquí visualizaremos el estado general de la cartera vencida y créditos al corriente.")
    # Próximo paso: Cargar datos de contratos y mostrar indicadores (Kpis)

elif menu == "📝 Ventas":
    st.subheader("Generación de Nuevos Contratos")
    st.write("Formulario para registrar la venta de un lote y asignar un cliente.")

elif menu == "💰 Cobranza":
    st.subheader("Registro de Pagos / Abonos")
    st.write("Selección de cliente y registro de entrada de dinero.")

elif menu == "📅 Historial de Pagos":
    st.subheader("Consulta de Movimientos")
    try:
        # Intento de lectura de la pestaña 'pagos'
        df_pagos = conn.read(spreadsheet=URL_SHEET, worksheet="pagos")
        st.dataframe(df_pagos, use_container_width=True, hide_index=True)
    except:
        st.warning("No se encontró la pestaña 'pagos' en el Excel.")

elif menu == "📂 Gestión de Contratos":
    st.subheader("Base de Datos de Contratos")
    st.write("Edición y estatus de contratos existentes.")

elif menu == "📈 Comisiones":
    st.subheader("Cálculo de Comisiones")
    st.write("Resumen de ventas por asesor y montos a liquidar.")

# --- FOOTER DE CONEXIÓN ---
st.sidebar.write("---")
st.sidebar.success("Conectado a Google Sheets")
