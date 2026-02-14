import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. Configuración de la página
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
    except Exception:
        return pd.DataFrame()

# --- LÓGICA DE LAS SECCIONES ---

st.title(f"Inmobiliaria - {menu[2:]}")

if menu == "🏠 Inicio":
    st.subheader("Resumen de Créditos Activos")
    st.info("Panel principal con indicadores clave.")

elif menu == "📝 Ventas":
    st.subheader("Registro de Nuevo Contrato")
    df_ubicaciones = cargar_datos("ubicaciones")
    df_vendedores = cargar_datos("vendedores")
    df_clientes = cargar_datos("clientes")

    with st.form("form_ventas"):
        col1, col2 = st.columns(2)
        with col1:
            if not df_ubicaciones.empty:
                # Generamos M##-L## para el listado de ventas
                df_ubicaciones['etiqueta'] = "M" + df_ubicaciones['manzana'].astype(str) + "-L" + df_ubicaciones['lote'].astype(str)
                opciones_ubi = df_ubicaciones[df_ubicaciones['estatus'] == 'Disponible']['etiqueta'].tolist()
            else:
                opciones_ubi = ["No hay ubicaciones"]
            
            st.selectbox("Seleccione la Ubicación", options=opciones_ubi)
            st.selectbox("Nombre del Cliente", options=df_clientes["nombre"].tolist() if not df_clientes.empty else ["No hay"])
            st.selectbox("Seleccione el Vendedor", options=df_vendedores["nombre"].tolist() if not df_vendedores.empty else ["No hay"])

        with col2:
            st.date_input("Fecha de Contrato", value=datetime.now())
            st.number_input("Monto de Comisión ($)", min_value=0.0)
            st.text_area("Observaciones")

        if st.form_submit_button("Generar Contrato"):
            st.success("Contrato registrado exitosamente.")

elif menu == "💰 Cobranza":
    st.subheader("Registro de Pagos / Abonos")

elif menu == "📅 Historial de Pagos":
    st.subheader("Consulta de Movimientos")
    st.dataframe(cargar_datos("pagos"), use_container_width=True)

elif menu == "📂 Gestión de Contratos":
    st.subheader("Base de Datos de Contratos")

elif menu == "📑 Catálogo":
    st.subheader("Inventario de Ubicaciones")
    
    # 1. Formulario para agregar nuevas ubicaciones
    with st.expander("➕ Agregar Nueva Ubicación para Venta"):
        with st.form("nuevo_lote"):
            c1, c2, c3 = st.columns(3)
            with c1:
                nueva_manzana = st.number_input("Manzana", min_value=1, step=1)
            with c2:
                nuevo_lote = st.number_input("Lote", min_value=1, step=1)
            with c3:
                nuevo_precio = st.number_input("Precio de Lista ($)", min_value=0.0, step=1000.0)
            
            # Generación automática de la etiqueta para mostrar al usuario
            etiqueta_auto = f"M{nueva_manzana}-L{nuevo_lote}"
            st.write(f"**Ubicación a generar:** {etiqueta_auto}")
            
            if st.form_submit_button("Registrar Ubicación"):
                st.info(f"Se registraría: {etiqueta_auto} con precio de ${nuevo_precio}")
                st.warning("Nota: La escritura directa a Google Sheets requiere configuración adicional. Por ahora, agrégalo manualmente al Excel y presiona 'Actualizar'.")

    st.divider()

    # 2. Listado de ubicaciones existentes
    df_cat = cargar_datos("ubicaciones")
    if not df_cat.empty:
        # Aseguramos que la columna 'ubicacion' se vea como M##-L##
        df_cat['ubicacion'] = "M" + df_cat['manzana'].astype(str) + "-L" + df_cat['lote'].astype(str)
        
        # Reordenamos columnas para que sea fácil de leer
        cols = ['ubicacion', 'manzana', 'lote', 'precio', 'estatus']
        # Filtramos solo las columnas que existan para evitar errores
        df_display = df_cat[[c for c in cols if c in df_cat.columns]]
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.write("No hay datos en la pestaña 'ubicaciones'.")

elif menu == "📇 Directorio":
    st.subheader("Registro de Clientes y Vendedores")
    t1, t2 = st.tabs(["Clientes", "Vendedores"])
    with t1:
        st.dataframe(cargar_datos("clientes"), use_container_width=True)
    with t2:
        st.dataframe(cargar_datos("vendedores"), use_container_width=True)

elif menu == "📈 Comisiones":
    st.subheader("Resumen de Comisiones")

# --- FOOTER ---
st.sidebar.write("---")
st.sidebar.success("Conectado a Google Sheets")
