import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- IMPORTACION DE MODULOS ---
from modulos.reportes import render_inicio
from modulos.ventas import render_ventas
from modulos.credito import render_detalle_credito
from modulos.cobranza import render_cobranza
from modulos.gastos import render_gastos
from modulos.ubicaciones import render_ubicaciones
from modulos.clientes import render_clientes

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Zona Valle - Gestión Inmobiliaria", layout="wide")

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
# 🛠️ BARRA LATERAL (SIDEBAR)
# ==========================================
with st.sidebar:
    # --- LOGO CONCEPTUAL ---
    # Nota: Asegúrate de tener la imagen en la carpeta raíz o usar la URL directa
    try:
        st.image("logo.png", use_container_width=True)
    except:
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
    st.sidebar.markdown("---")
    st.sidebar.write("### 🌐 Estado del Sistema")
    st.sidebar.success("✅ Conectado a la Nube")
    ahora = datetime.now().strftime("%H:%M:%S")
    st.sidebar.info(f"Última sincronización:\n{ahora}")

# ==========================================
# 🚀 RENDERIZADO DE MÓDULOS
# ==========================================

if menu == "🏠 Inicio":
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")
    df_g = cargar_datos("gastos")
    df_cl = cargar_datos("clientes") # Cargamos clientes para las acciones de WA/Mail
    # Ahora pasamos df_cl para evitar el NameError
    render_inicio(df_v, df_p, df_g, df_cl, fmt_moneda)

elif menu == "📝 Ventas":
    df_v = cargar_datos("ventas")
    df_u = cargar_datos("ubicaciones")
    df_cl = cargar_datos("clientes")
    df_vd = cargar_datos("vendedores")
    render_ventas(df_v, df_u, df_cl, df_vd, conn, URL_SHEET, fmt_moneda)

elif menu == "📊 Detalle de Crédito":
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")
    render_detalle_credito(df_v, df_p, fmt_moneda)

elif menu == "💰 Cobranza":
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")
    render_cobranza(df_v, df_p, conn, URL_SHEET, fmt_moneda, cargar_datos)

elif menu == "💸 Gastos":
    df_g = cargar_datos("gastos")
    render_gastos(df_g, conn, URL_SHEET, fmt_moneda, cargar_datos)

elif menu == "📍 Ubicaciones":
    df_u = cargar_datos("ubicaciones")
    render_ubicaciones(df_u, conn, URL_SHEET, cargar_datos)

elif menu == "👥 Clientes":
    df_cl = cargar_datos("clientes")
    render_clientes(df_cl, conn, URL_SHEET, cargar_datos)
