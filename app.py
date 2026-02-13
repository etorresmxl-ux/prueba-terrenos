import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Inmobiliaria - Drive Mode", layout="wide")

# --- CONFIGURACIÓN DE LA HOJA (Pega aquí tu link) ---
URL_SHEET = "https://docs.google.com/spreadsheets/d/1TIeJ2fjJ6WHnl24b8iL9LgTNuRZ_5OYyekSad0uK1jE/edit?usp=sharing"

# --- CONEXIÓN A GOOGLE SHEETS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Error de conexión. Revisa los Secrets en Streamlit Cloud.")
    st.stop()

# Funciones de lectura y escritura
def leer(pestana):
    return conn.read(spreadsheet=URL_SHEET, worksheet=pestana)

def guardar(df, pestana):
    conn.update(spreadsheet=URL_SHEET, worksheet=pestana, data=df)
    st.cache_data.clear()

# --- SEGURIDAD ---
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    with st.container():
        st.title("🔐 Acceso Restringido")
        pwd = st.text_input("Introduce la clave maestra:", type="password")
        if st.button("Entrar"):
            if pwd == "Terrenos2026":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Clave incorrecta")
    st.stop()

# --- MENÚ LATERAL ---
with st.sidebar:
    st.title("🏢 Inmobiliaria Pro")
    choice = st.radio("Navegación", ["Resumen", "Nueva Venta", "Cobranza", "Gestión de Pagos", "Detalle de Crédito", "Ubicaciones", "Directorio"])
    st.info("Conectado a Google Drive ✅")

# --- SECCIÓN: UBICACIONES ---
if choice == "Ubicaciones":
    st.header("📍 Inventario de Terrenos")
    df = leer("terrenos")
    
    with st.form("nuevo"):
        c1, c2, c3 = st.columns(3)
        m = c1.text_input("Manzana")
        l = c2.text_input("Lote")
        p = c3.number_input("Precio ($)", min_value=0.0)
        if st.form_submit_button("Guardar en Drive"):
            if m and l:
                nueva = pd.DataFrame([{"manzana": m, "lote": l, "costo": p, "estatus": "Disponible"}])
                df_final = pd.concat([df, nueva], ignore_index=True)
                guardar(df_final, "terrenos")
                st.success("Guardado correctamente")
                st.rerun()
    st.dataframe(df, use_container_width=True, hide_index=True)

# --- SECCIÓN: COBRANZA ---
elif choice == "Cobranza":
    st.header("💸 Registro de Pagos")
    # Cargar datos necesarios
    df_ventas = leer("ventas")
    df_clientes = leer("clientes")
    df_pagos = leer("pagos")
    
    if not df_ventas.empty:
        with st.form("pago"):
            # Crear lista de contratos: Manzana-Lote - Cliente
            opciones = df_ventas.index.tolist() # Usamos el índice como ID temporal
            sel = st.selectbox("Seleccionar Contrato:", opciones, format_func=lambda x: f"Venta ID: {x}")
            monto = st.number_input("Monto del Pago:", min_value=0.0)
            fecha = st.date_input("Fecha de Pago", datetime.now())
            
            if st.form_submit_button("Registrar Pago"):
                nuevo_pago = pd.DataFrame([{"id_venta": sel, "monto": monto, "fecha": fecha.strftime('%Y-%m-%d')}])
                df_pagos_final = pd.concat([df_pagos, nuevo_pago], ignore_index=True)
                guardar(df_pagos_final, "pagos")
                st.success("Pago registrado en la nube")
                st.rerun()
    else:
        st.warning("No hay ventas registradas para cobrar.")

# --- SECCIÓN: RESUMEN ---
elif choice == "Resumen":
    st.header("📋 Vista General de Negocio")
    try:
        df_t = leer("terrenos")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Terrenos", len(df_t))
        col2.metric("Vendidos", len(df_t[df_t['estatus'] == 'Vendido']))
        col3.metric("Disponibles", len(df_t[df_t['estatus'] == 'Disponible']))
        st.subheader("Lista de Propiedades")
        st.table(df_t)
    except:
        st.info("Agrega tu primer terreno en la sección de Ubicaciones")

# --- SECCIÓN: DIRECTORIO ---
elif choice == "Directorio":
    st.header("👥 Directorio de Contactos")
    tab1, tab2 = st.tabs(["Clientes", "Vendedores"])
    
    with tab1:
        df_c = leer("clientes")
        st.dataframe(df_c, use_container_width=True)
        with st.expander("Añadir Cliente"):
            nom = st.text_input("Nombre Completo")
            if st.button("Guardar Cliente"):
                n_c = pd.concat([df_c, pd.DataFrame([{"nombre": nom}])], ignore_index=True)
                guardar(n_c, "clientes")
                st.rerun()

