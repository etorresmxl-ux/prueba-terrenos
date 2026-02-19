import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- IMPORTACION DE MODULOS ---
from modulos.reportes import render_reportes
from modulos.ventas import render_ventas
from modulos.credito import render_detalle_credito
from modulos.cobranza import render_cobranza
from modulos.gastos import render_gastos
from modulos.ubicaciones import render_ubicaciones
from modulos.clientes import render_clientes


# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Inmobiliaria Pro", layout="wide")

# 2. CONEXIÓN A GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)

URL_SHEET = "https://docs.google.com/spreadsheets/d/1d_G8VafPZp5jj3c1Io9kN3mG31GE70kK2Q2blxWzCCs/edit#gid=0"

# --- FUNCIÓN PARA FORMATO DE MONEDA ($) ---
def fmt_moneda(valor):
    try:
        return f"$ {float(valor):,.2f}"
    except:
        return "$ 0.00"

# --- FUNCIONES DE APOYO ---
def cargar_datos(pestana):
    try:
        df = conn.read(spreadsheet=URL_SHEET, worksheet=pestana)
        df = df.dropna(axis=1, how='all').dropna(axis=0, how='all')
        return df
    except:
        return pd.DataFrame()

# ==========================================
# 🛠️ BARRA LATERAL
# ==========================================
with st.sidebar:
    st.title("🏢 Panel de Gestión")
    
    # --- MENÚ DE NAVEGACIÓN ---
    menu = st.radio(
        "Seleccione un módulo:",
        ["🏠 Inicio", "📝 Ventas", "📊 Detalle de Crédito", "💰 Cobranza", "💸 Gastos", "📍 Ubicaciones", "👥 Clientes"]
    )
    
    st.divider()

    # --- BOTÓN DE ACTUALIZACIÓN ---
    st.subheader("🔄 Base de Datos")
    if st.button("Actualizar Información"):
        st.cache_data.clear()
        st.success("¡Datos actualizados!")
        st.rerun()

    # --- INDICADOR DE CONEXIÓN ---
    # Esto verifica si la URL está configurada
    if URL_SHEET != "TU_URL_AQUI":
        st.sidebar.markdown("---")
        st.sidebar.write("### 🌐 Estado del Sistema")
        st.sidebar.success("✅ Conectado a la Nube")
        
        # Mostrar hora de última sincronización
        ahora = datetime.now().strftime("%H:%M:%S")
        st.sidebar.info(f"Última sincronización:\n{ahora}")
    else:
        st.sidebar.error("❌ Desconectado (Falta URL)")

# --- MODULOS ---

if menu == "🏠 Inicio":
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")
    df_g = cargar_datos("gastos")
    render_reportes(df_v, df_p, df_g, fmt_moneda)

if menu == "🤝 Ventas":
    df_ventas = cargar_datos("ventas")
    df_clientes = cargar_datos("clientes")
    df_ubicaciones = cargar_datos("ubicaciones")
    render_ventas(df_ventas, df_clientes, df_ubicaciones, conn, URL_SHEET, fmt_moneda, cargar_datos)

if menu == "📊 Detalle de Crédito":
    df_ventas = cargar_datos("ventas")
    df_pagos = cargar_datos("pagos")
    render_detalle_credito(df_ventas, df_pagos, fmt_moneda)

if menu == "💰 Cobranza":
    df_ventas = cargar_datos("ventas")
    df_pagos = cargar_datos("pagos")
    render_cobranza(df_ventas, df_pagos, conn, URL_SHEET, fmt_moneda, cargar_datos)

if menu == "💸 Gastos":
    df_gastos = cargar_datos("gastos")
    render_gastos(df_gastos, conn, URL_SHEET, fmt_moneda, cargar_datos)

if menu == "📍 Ubicaciones":
    df_ubicaciones = cargar_datos("ubicaciones")
    render_ubicaciones(df_ubicaciones, conn, URL_SHEET, cargar_datos)

elif menu == "👥 Clientes":
    df_clientes = cargar_datos("clientes")
    render_clientes(df_clientes, conn, URL_SHEET, cargar_datos)

