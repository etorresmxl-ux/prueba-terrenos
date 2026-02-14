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

    if not df_ubi.empty:
        df_disponibles = df_ubi[df_ubi['estatus'] == 'Disponible']
        lista_ubi = df_disponibles['ubicacion'].tolist()
    else:
        lista_ubi = []

    if not lista_ubi:
        st.warning("No hay ubicaciones disponibles en el Catálogo.")
    else:
        # Quitamos el FORM para permitir actualización en tiempo real
        col1, col2 = st.columns(2)
        
        with col1:
            u_sel = st.selectbox("Seleccione la Ubicación", options=lista_ubi)
            
            # PREGUNTAR POR CLIENTE (Seleccionar o Nuevo)
            lista_clientes = ["+ Agregar Nuevo Cliente"] + (df_cli["nombre"].tolist() if not df_cli.empty else [])
            c_input = st.selectbox("Nombre del Cliente", options=lista_clientes)
            if c_input == "+ Agregar Nuevo Cliente":
                v_cliente = st.text_input("Escriba el nombre del Nuevo Cliente")
            else:
                v_cliente = c_input

            # PREGUNTAR POR VENDEDOR (Seleccionar o Nuevo)
            lista_vendedores = ["+ Agregar Nuevo Vendedor"] + (df_ven["nombre"].tolist() if not df_ven.empty else [])
            v_input = st.selectbox("Seleccione el Vendedor", options=lista_vendedores)
            if v_input == "+ Agregar Nuevo Vendedor":
                v_vendedor = st.text_input("Escriba el nombre del Nuevo Vendedor")
            else:
                v_vendedor = v_input

            v_fecha = st.date_input("Fecha de Contrato", value=datetime.now())

        with col2:
            # Precio movido a la derecha como solicitaste
            precio_sugerido = float(df_ubi[df_ubi['ubicacion'] == u_sel]['precio'].values[0])
            v_precio = st.number_input("Precio de Venta Final ($)", value=precio_sugerido, step=1000.0)
            
            v_enganche = st.number_input("Enganche ($)", min_value=0.0, step=1000.0)
            v_plazo = st.number_input("Plazo (Meses)", min_value=1, value=48, step=1)
            v_comision = st.number_input("Comisión del Vendedor ($)", min_value=0.0, step=100.0)
            
            # CÁLCULO AUTOMÁTICO E INSTANTÁNEO
            saldo_a_financiar = v_precio - v_enganche
            mensualidad = saldo_a_financiar / v_plazo if v_plazo > 0 else 0
            
            st.markdown("---")
            st.metric("Saldo a Financiar", f"$ {saldo_a_financiar:,.2f}")
            st.metric("Mensualidad Calculada", f"$ {mensualidad:,.2f}")
            st.caption("Fórmula: (Precio - Enganche) / Plazo")

        v_obs = st.text_area("Observaciones del contrato")
        
        # Botón de acción fuera de un form
        if st.button("Confirmar Venta y Generar Contrato", type="primary"):
            if not v_cliente or not v_vendedor or v_cliente == "+ Agregar Nuevo Cliente" or v_vendedor == "+ Agregar Nuevo Vendedor":
                st.error("Por favor, ingrese un nombre válido para Cliente y Vendedor.")
            else:
                try:
                    with st.spinner("Procesando venta..."):
                        # 1. Registrar Venta
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
                        
                        # 2. Si son nuevos, agregarlos al directorio
                        if c_input == "+ Agregar Nuevo Cliente":
                            df_c_act = cargar_datos("clientes")
                            nuevo_c = pd.DataFrame([{"id_cliente": len(df_c_act)+1, "nombre": v_cliente}])
                            conn.update(spreadsheet=URL_SHEET, worksheet="clientes", data=pd.concat([df_c_act, nuevo_c], ignore_index=True))
                        
                        if v_input == "+ Agregar Nuevo Vendedor":
                            df_v_act = cargar_datos("vendedores")
                            nuevo_v = pd.DataFrame([{"id_vendedor": len(df_v_act)+1, "nombre": v_vendedor}])
                            conn.update(spreadsheet=URL_SHEET, worksheet="vendedores", data=pd.concat([df_v_act, nuevo_v], ignore_index=True))

                        # 3. Marcar lote como Vendido
                        df_ubi.loc[df_ubi['ubicacion'] == u_sel, 'estatus'] = 'Vendido'
                        
                        # 4. Guardar Todo
                        conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=pd.concat([df_ventas, nueva_venta], ignore_index=True))
                        conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_ubi)
                        
                        st.success(f"✅ ¡Venta registrada exitosamente para {v_cliente}!")
                        st.cache_data.clear()
                        st.balloons()
                except Exception as e:
                    st.error(f"Error: {e}")

# --- MÓDULO: CATALOGO ---
elif menu == "📑 Catálogo":
    st.subheader("Inventario de Ubicaciones")
    df_cat = cargar_datos("ubicaciones")
    if not df_cat.empty:
        st.dataframe(df_cat[["ubicacion", "precio", "estatus"]], use_container_width=True, hide_index=True)
    else:
        st.info("No hay ubicaciones registradas.")

# --- MÓDULO: DIRECTORIO ---
elif menu == "📇 Directorio":
    st.subheader("Clientes y Vendedores")
    t1, t2 = st.tabs(["Clientes", "Vendedores"])
    with t1: st.dataframe(cargar_datos("clientes"), use_container_width=True, hide_index=True)
    with t2: st.dataframe(cargar_datos("vendedores"), use_container_width=True, hide_index=True)

# Otros módulos (Estructura base)
elif menu == "🏠 Inicio": st.info("Panel de Resumen")
elif menu == "💰 Cobranza": st.subheader("Registro de Pagos")
elif menu == "📅 Historial de Pagos": st.subheader("Historial")
elif menu == "📂 Gestión de Contratos": st.subheader("Contratos")
elif menu == "📈 Comisiones": st.subheader("Comisiones")

st.sidebar.write("---")
st.sidebar.success("Conectado")
