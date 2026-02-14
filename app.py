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
    except:
        return pd.DataFrame()

# --- LÓGICA DE LAS SECCIONES ---
st.title(f"Inmobiliaria - {menu[2:]}")

# --- MÓDULO: VENTAS ---
if menu == "📝 Ventas":
    st.subheader("Generación de Nuevo Contrato")
    
    df_ubi = cargar_datos("ubicaciones")
    df_cli = cargar_datos("clientes")
    df_ven = cargar_datos("vendedores")

    # Filtrar solo ubicaciones disponibles
    if not df_ubi.empty:
        df_disponibles = df_ubi[df_ubi['estatus'] == 'Disponible']
        lista_ubi = df_disponibles['ubicacion'].tolist()
    else:
        lista_ubi = []

    if not lista_ubi:
        st.warning("No hay ubicaciones disponibles en el Catálogo.")
    else:
        with st.form("registro_venta"):
            col1, col2 = st.columns(2)
            
            with col1:
                u_sel = st.selectbox("Seleccione la Ubicación", options=lista_ubi)
                
                # Obtener el precio sugerido de la ubicación seleccionada
                precio_sugerido = float(df_ubi[df_ubi['ubicacion'] == u_sel]['precio'].values[0])
                
                v_precio = st.number_input("Precio de Venta Final ($)", value=precio_sugerido, step=1000.0)
                v_cliente = st.selectbox("Nombre del Cliente", options=df_cli["nombre"].tolist() if not df_cli.empty else ["Registrar en Directorio"])
                v_vendedor = st.selectbox("Seleccione el Vendedor", options=df_ven["nombre"].tolist() if not df_ven.empty else ["Registrar en Directorio"])
                v_fecha = st.date_input("Fecha de Contrato", value=datetime.now())

            with col2:
                v_enganche = st.number_input("Enganche ($)", min_value=0.0, step=1000.0)
                v_plazo = st.number_input("Plazo (Meses)", min_value=1, value=12, step=1)
                v_comision = st.number_input("Comisión del Vendedor ($)", min_value=0.0, step=100.0)
                
                # CÁLCULO DE MENSUALIDAD (Tasa 0%)
                saldo_a_financiar = v_precio - v_enganche
                mensualidad = saldo_a_financiar / v_plazo if v_plazo > 0 else 0
                
                st.markdown("---")
                st.metric("Saldo a Financiar", f"$ {saldo_a_financiar}")
                st.metric("Mensualidad Calculada", f"$ {round(mensualidad, 2)}")
                st.caption("Fórmula: (Precio - Enganche) / Plazo")

            v_obs = st.text_area("Observaciones del contrato")
            
            if st.form_submit_button("Confirmar Venta y Generar Contrato"):
                try:
                    # 1. Registrar la venta en la pestaña 'ventas' (o 'contratos')
                    df_ventas = cargar_datos("ventas")
                    nueva_venta = pd.DataFrame([{
                        "fecha": v_fecha.strftime('%Y-%m-%d'),
                        "ubicacion": u_sel,
                        "cliente": v_cliente,
                        "vendedor": v_vendedor,
                        "precio_total": v_precio,
                        "enganche": v_enganche,
                        "plazo_meses": v_plazo,
                        "mensualidad": mensualidad,
                        "comision": v_comision,
                        "estatus_pago": "Activo"
                    }])
                    
                    # 2. Actualizar el estatus del lote en la pestaña 'ubicaciones'
                    df_ubi.loc[df_ubi['ubicacion'] == u_sel, 'estatus'] = 'Vendido'
                    
                    # 3. Guardar cambios
                    conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=pd.concat([df_ventas, nueva_venta], ignore_index=True))
                    conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_ubi)
                    
                    st.success(f"✅ ¡Venta registrada! El lote {u_sel} ahora aparece como VENDIDO.")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Error al procesar la venta: {e}")

# --- MÓDULO: CATALOGO ---
elif menu == "📑 Catálogo":
    st.subheader("Inventario de Ubicaciones")
    df_cat = cargar_datos("ubicaciones")
    if not df_cat.empty:
        # Quitamos el formato complejo por ahora para evitar el error
        st.dataframe(df_cat[["ubicacion", "precio", "estatus"]], use_container_width=True, hide_index=True)
    else:
        st.info("No hay ubicaciones registradas.")

# --- MÓDULO: DIRECTORIO ---
elif menu == "📇 Directorio":
    st.subheader("Clientes y Vendedores")
    t1, t2 = st.tabs(["Clientes", "Vendedores"])
    with t1: st.dataframe(cargar_datos("clientes"), use_container_width=True)
    with t2: st.dataframe(cargar_datos("vendedores"), use_container_width=True)

# Otros módulos (Estructura base)
elif menu == "🏠 Inicio": st.info("Panel de Resumen")
elif menu == "💰 Cobranza": st.subheader("Registro de Pagos")
elif menu == "📅 Historial de Pagos": st.subheader("Historial")
elif menu == "📂 Gestión de Contratos": st.subheader("Contratos")
elif menu == "📈 Comisiones": st.subheader("Comisiones")

st.sidebar.write("---")
st.sidebar.success("Conectado")
