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
    ["🏠 Inicio", "📝 Ventas", "💰 Cobranza", "📅 Historial de Pagos", "📂 Gestión de Contratos", "📑 Catálogo", "📇 Directorio", "📈 Comisiones"]
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

# --- MÓDULO: CATALOGO (INVENTARIO) ---
if menu == "📑 Catálogo":
    st.subheader("Inventario de Ubicaciones")
    
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
                    nuevo = pd.DataFrame([{
                        "id_lote": len(df_actual)+1, 
                        "ubicacion": etiqueta, 
                        "manzana": m, 
                        "lote": l, 
                        "precio": p, 
                        "estatus": "Disponible"
                    }])
                    df_final = pd.concat([df_actual, nuevo], ignore_index=True)
                    conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_final)
                    st.success(f"✅ {etiqueta} guardado exitosamente.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    st.divider()

    # --- TABLA DE UBICACIONES PULIDA ---
    df_cat = cargar_datos("ubicaciones")
    if not df_cat.empty:
        # 1. Seleccionamos solo las columnas que queremos mostrar
        # 2. Configuramos el formato de moneda para la columna 'precio'
        st.dataframe(
            df_cat[["ubicacion", "precio", "estatus"]], 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "ubicacion": "Ubicación",
                "precio": st.column_config.NumberColumn(
                    "Precio de Venta",
                    format="$ %.2f"
                ),
                "estatus": "Estatus"
            }
        )
    else:
        st.info("No hay ubicaciones registradas aún.")

# --- MÓDULO: VENTAS ---
elif menu == "📝 Ventas":
    st.subheader("Registro de Nuevo Contrato")
    df_ubi = cargar_datos("ubicaciones")
    df_cli = cargar_datos("clientes")
    df_ven = cargar_datos("vendedores")

    with st.form("form_ventas"):
        col1, col2 = st.columns(2)
        with col1:
            if not df_ubi.empty:
                # Usamos directamente la columna 'ubicacion' que ya tiene el formato M-L
                opciones_ubi = df_ubi[df_ubi['estatus'] == 'Disponible']['ubicacion'].tolist()
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
                        st.rerun()
                    except Exception as e: st.error(e)
        st.dataframe(cargar_datos("clientes")[["nombre", "telefono"]], use_container_width=True, hide_index=True)

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
                        st.rerun()
                    except Exception as e: st.error(e)
        st.dataframe(cargar_datos("vendedores")[["nombre"]], use_container_width=True, hide_index=True)

# (Secciones de relleno para mantener el menú)
elif menu == "🏠 Inicio": st.info("Panel de control.")
elif menu == "💰 Cobranza": st.subheader("Registro de Pagos")
elif menu == "📅 Historial de Pagos": st.dataframe(cargar_datos("pagos"), use_container_width=True)
elif menu == "📂 Gestión de Contratos": st.info("Módulo de contratos.")
elif menu == "📈 Comisiones": st.info("Cálculo de comisiones.")

st.sidebar.write("---")
st.sidebar.success("Conectado a Google Sheets")
