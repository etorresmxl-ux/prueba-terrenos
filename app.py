import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. Configuración de la página (Título fijo)
st.set_page_config(page_title="Inmobiliaria", layout="wide")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. URL de tu base de datos
URL_SHEET = "https://docs.google.com/spreadsheets/d/1d_G8VafPZp5jj3c1Io9kN3mG31GE70kK2Q2blxWzCCs/edit#gid=0"

# --- BARRA LATERAL (MENÚ) ---
st.sidebar.title("Navegación")

menu = st.sidebar.radio(
    "Seleccione una sección:",
    [
        "🏠 Inicio", 
        "📝 Ventas", 
        "💰 Cobranza", 
        "📅 Historial de Pagos", 
        "📂 Gestión de Contratos", 
        "📑 Catálogo",
        "📇 Directorio",
        "📈 Comisiones"
    ]
)

st.sidebar.markdown("---")

if st.sidebar.button("🔄 Actualizar Base de Datos"):
    st.cache_data.clear()
    st.rerun()

# --- FUNCIONES DE CARGA DE DATOS ---
def cargar_datos(pestana):
    try:
        return conn.read(spreadsheet=URL_SHEET, worksheet=pestana)
    except Exception as e:
        return pd.DataFrame()

# --- LÓGICA DE LAS SECCIONES ---

st.title(f"Inmobiliaria - {menu[2:]}")

if menu == "🏠 Inicio":
    st.subheader("Resumen de Créditos Activos")
    st.info("Panel principal con indicadores clave de la cartera.")

elif menu == "📝 Ventas":
    st.subheader("Registro de Nuevo Contrato")
    
    # Cargamos datos para las listas desplegables
    df_ubicaciones = cargar_datos("ubicaciones")
    df_vendedores = cargar_datos("vendedores")
    df_clientes = cargar_datos("clientes")

    with st.form("form_ventas"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Procesar Ubicaciones al formato M##-L##
            if not df_ubicaciones.empty:
                # Creamos la etiqueta combinando Manzana y Lote
                df_ubicaciones['etiqueta'] = "M" + df_ubicaciones['manzana'].astype(str) + "-L" + df_ubicaciones['lote'].astype(str)
                opciones_ubi = df_ubicaciones['etiqueta'].tolist()
            else:
                opciones_ubi = ["No hay ubicaciones registradas"]
            
            ubicacion_sel = st.selectbox("Seleccione la Ubicación (Manzana-Lote)", options=opciones_ubi)
            
            # Cliente (del Directorio)
            opciones_cli = df_clientes["nombre"].tolist() if not df_clientes.empty else ["No hay clientes"]
            cliente_sel = st.selectbox("Nombre del Cliente", options=opciones_cli)
            
            # Vendedor (del Directorio)
            opciones_ven = df_vendedores["nombre"].tolist() if not df_vendedores.empty else ["No hay vendedores"]
            vendedor_sel = st.selectbox("Seleccione el Vendedor", options=opciones_ven)

        with col2:
            fecha_contrato = st.date_input("Fecha de Contrato", value=datetime.now())
            comision_monto = st.number_input("Monto de Comisión ($)", min_value=0.0, step=100.0)
            observaciones = st.text_area("Observaciones adicionales")

        if st.form_submit_button("Generar Contrato"):
            st.success(f"Contrato registrado: {cliente_sel} compró {ubicacion_sel} con el vendedor {vendedor_sel}")

elif menu == "💰 Cobranza":
    st.subheader("Registro de Pagos / Abonos")

elif menu == "📅 Historial de Pagos":
    st.subheader("Consulta de Movimientos")
    st.dataframe(cargar_datos("pagos"), use_container_width=True)

elif menu == "📂 Gestión de Contratos":
    st.subheader("Base de Datos de Contratos")

elif menu == "📑 Catálogo":
    st.subheader("Gestión de Ubicaciones")
    st.write("Datos actuales en la pestaña 'ubicaciones':")
    st.dataframe(cargar_datos("ubicaciones"), use_container_width=True, hide_index=True)

elif menu == "📇 Directorio":
    st.subheader("Registro de Clientes y Vendedores")
    t1, t2 = st.tabs(["Clientes", "Vendedores"])
    with t1:
        st.dataframe(cargar_datos("clientes"), use_container_width=True)
    with t2:
        st.dataframe(cargar_datos("vendedores"), use_container_width=True)

elif menu == "📈 Comisiones":
    st.subheader("Resumen de Comisiones por Vendedor")

# --- FOOTER ---
st.sidebar.write("---")
st.sidebar.success("Conectado a Google Sheets")
