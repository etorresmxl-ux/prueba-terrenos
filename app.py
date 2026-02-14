import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. Configuración de la página
st.set_page_config(page_title="Inmobiliaria", layout="wide")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. URL de tu base de datos real
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

# --- FUNCIONES DE APOYO ---
def cargar_datos(pestana):
    try:
        return conn.read(spreadsheet=URL_SHEET, worksheet=pestana)
    except Exception:
        return pd.DataFrame()

# --- LÓGICA DE LAS SECCIONES ---
st.title(f"Inmobiliaria - {menu[2:]}")

# --- MÓDULO: INICIO ---
if menu == "🏠 Inicio":
    st.subheader("Resumen de Créditos Activos")
    st.info("Panel de control para visualizar el estado de la cartera inmobiliaria.")

# --- MÓDULO: VENTAS ---
elif menu == "📝 Ventas":
    st.subheader("Registro de Nuevo Contrato")
    df_ubi = cargar_datos("ubicaciones")
    df_cli = cargar_datos("clientes")
    df_ven = cargar_datos("vendedores")

    with st.form("form_ventas"):
        col1, col2 = st.columns(2)
        with col1:
            # Solo mostrar disponibles y generar formato M-L
            if not df_ubi.empty:
                df_ubi['etiqueta'] = "M" + df_ubi['manzana'].astype(str) + "-L" + df_ubi['lote'].astype(str)
                # Filtrar si existe columna estatus
                if 'estatus' in df_ubi.columns:
                    opciones_ubi = df_ubi[df_ubi['estatus'] == 'Disponible']['etiqueta'].tolist()
                else:
                    opciones_ubi = df_ubi['etiqueta'].tolist()
            else:
                opciones_ubi = ["No hay ubicaciones"]

            u_sel = st.selectbox("Seleccione la Ubicación", options=opciones_ubi)
            c_sel = st.selectbox("Nombre del Cliente", options=df_cli["nombre"].tolist() if not df_cli.empty else ["No hay"])
            v_sel = st.selectbox("Seleccione el Vendedor", options=df_ven["nombre"].tolist() if not df_ven.empty else ["No hay"])

        with col2:
            f_cont = st.date_input("Fecha de Contrato", value=datetime.now())
            com_monto = st.number_input("Monto de Comisión ($)", min_value=0.0)
            obs = st.text_area("Observaciones")

        if st.form_submit_button("Generar Contrato"):
            st.success(f"Contrato de {c_sel} procesado para {u_sel}.")

# --- MÓDULO: CATALOGO (INVENTARIO) ---
elif menu == "📑 Catálogo":
    st.subheader("Gestión de Inventario")
    
    with st.expander("➕ Agregar Nueva Ubicación para Venta"):
        with st.form("nuevo_lote", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1: m = st.number_input("Manzana", min_value=1, step=1)
            with c2: l = st.number_input("Lote", min_value=1, step=1)
            with c3: p = st.number_input("Precio de Lista ($)", min_value=0.0, step=1000.0)
            
            etiqueta = f"M{m}-L{l}"
            st.write(f"**Se creará la ubicación:** {etiqueta}")
            
            if st.form_submit_button("Registrar Ubicación"):
                try:
                    df_actual = cargar_datos("ubicaciones")
                    nuevo = pd.DataFrame([{"id_lote": len(df_actual)+1, "ubicacion": etiqueta, "manzana": m, "lote": l, "precio": p, "estatus": "Disponible"}])
                    df_final = pd.concat([df_actual, nuevo], ignore_index=True)
                    conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_final)
                    st.success(f"✅ {etiqueta} guardado exitosamente.")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Error: {e}")

    df_cat = cargar_datos("ubicaciones")
    if not df_cat.empty:
        st.dataframe(df_cat, use_container_width=True, hide_index=True)

# --- MÓDULO: DIRECTORIO ---
elif menu == "📇 Directorio":
    st.subheader("Registro de Personas")
    tab_c, tab_v = st.tabs(["Clientes", "Vendedores"])
    
    with tab_c:
        with st.expander("➕ Registrar Cliente"):
            with st.form("f_cli", clear_on_submit=True):
                nom_c = st.text_input("Nombre Completo")
                tel_c = st.text_input("Teléfono")
                if st.form_submit_button("Guardar Cliente"):
                    try:
                        df_c = cargar_datos("clientes")
                        nuevo_c = pd.DataFrame([{"id_cliente": len(df_c)+1, "nombre": nom_c, "telefono": tel_c}])
                        df_c_final = pd.concat([df_c, nuevo_c], ignore_index=True)
                        conn.update(spreadsheet=URL_SHEET, worksheet="clientes", data=df_c_final)
                        st.success("Cliente guardado.")
                        st.cache_data.clear()
                    except Exception as e: st.error(e)
        st.dataframe(cargar_datos("clientes"), use_container_width=True)

    with tab_v:
        with st.expander("➕ Registrar Vendedor"):
            with st.form("f_ven", clear_on_submit=True):
                nom_v = st.text_input("Nombre del Asesor")
                if st.form_submit_button("Guardar Vendedor"):
                    try:
                        df_v = cargar_datos("vendedores")
                        nuevo_v = pd.DataFrame([{"id_vendedor": len(df_v)+1, "nombre": nom_v}])
                        df_v_final = pd.concat([df_v, nuevo_v], ignore_index=True)
                        conn.update(spreadsheet=URL_SHEET, worksheet="vendedores", data=df_v_final)
                        st.success("Vendedor guardado.")
                        st.cache_data.clear()
                    except Exception as e: st.error(e)
        st.dataframe(cargar_datos("vendedores"), use_container_width=True)

# --- MÓDULOS RESTANTES (ESTRUCTURA) ---
elif menu == "💰 Cobranza":
    st.subheader("Registro de Pagos")
elif menu == "📅 Historial de Pagos":
    st.dataframe(cargar_datos("pagos"), use_container_width=True)
elif menu == "📂 Gestión de Contratos":
    st.info("Módulo para administrar contratos existentes.")
elif menu == "📈 Comisiones":
    st.info("Cálculo de pagos para vendedores.")

# Footer
st.sidebar.write("---")
st.sidebar.success("Conectado a Google Sheets")
