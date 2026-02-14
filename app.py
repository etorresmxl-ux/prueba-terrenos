import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# 1. Configuración de la página
st.set_page_config(page_title="Inmobiliaria Pro", layout="wide")

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
        "📊 Detalle de Crédito",
        "💰 Cobranza", 
        "📅 Historial de Pagos", 
        "📂 Gestión de Contratos", 
        "📑 Catálogo",
        "📇 Directorio"
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
    except:
        return pd.DataFrame()

# --- LÓGICA DE LAS SECCIONES ---
st.title(f"Sistema Inmobiliario - {menu[2:]}")

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
        col1, col2 = st.columns(2)
        
        with col1:
            u_sel = st.selectbox("Seleccione la Ubicación", options=lista_ubi)
            
            # Selector de Cliente con opción de nuevo
            lista_clientes = ["+ Agregar Nuevo Cliente"] + (df_cli["nombre"].tolist() if not df_cli.empty else [])
            c_input = st.selectbox("Nombre del Cliente", options=lista_clientes)
            v_cliente = st.text_input("Nombre del Nuevo Cliente") if c_input == "+ Agregar Nuevo Cliente" else c_input

            # Selector de Vendedor con opción de nuevo
            lista_vendedores = ["+ Agregar Nuevo Vendedor"] + (df_ven["nombre"].tolist() if not df_ven.empty else [])
            v_input = st.selectbox("Seleccione el Vendedor", options=lista_vendedores)
            v_vendedor = st.text_input("Nombre del Nuevo Vendedor") if v_input == "+ Agregar Nuevo Vendedor" else v_input

            v_fecha = st.date_input("Fecha de Contrato", value=datetime.now())

        with col2:
            # Precio sugerido del catálogo
            precio_sugerido = float(df_ubi[df_ubi['ubicacion'] == u_sel]['precio'].values[0])
            v_precio = st.number_input("Precio de Venta Final ($)", value=precio_sugerido, step=1000.0)
            v_enganche = st.number_input("Enganche ($)", min_value=0.0, step=1000.0)
            v_plazo = st.number_input("Plazo (Meses)", min_value=1, value=48, step=1)
            v_comision = st.number_input("Comisión del Vendedor ($)", min_value=0.0, step=100.0)
            
            # Cálculos automáticos
            saldo_a_financiar = v_precio - v_enganche
            mensualidad = saldo_a_financiar / v_plazo if v_plazo > 0 else 0
            
            st.markdown("---")
            st.metric("Saldo a Financiar", f"$ {saldo_a_financiar:,.2f}")
            st.metric("Mensualidad Calculada (Tasa 0%)", f"$ {mensualidad:,.2f}")

        v_obs = st.text_area("Observaciones del contrato")
        
        if st.button("Confirmar Venta y Generar Contrato", type="primary"):
            if not v_cliente or v_cliente == "+ Agregar Nuevo Cliente":
                st.error("Debe ingresar un nombre de cliente.")
            else:
                try:
                    with st.spinner("Guardando contrato..."):
                        # 1. Registrar en pestaña ventas
                        df_ventas_act = cargar_datos("ventas")
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
                        
                        # 2. Actualizar estatus de ubicación
                        df_ubi.loc[df_ubi['ubicacion'] == u_sel, 'estatus'] = 'Vendido'
                        
                        # 3. Guardar cambios en la nube
                        conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=pd.concat([df_ventas_act, nueva_venta], ignore_index=True))
                        conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_ubi)
                        
                        # 4. Guardar nuevos si aplica
                        if c_input == "+ Agregar Nuevo Cliente":
                            df_c_act = cargar_datos("clientes")
                            conn.update(spreadsheet=URL_SHEET, worksheet="clientes", data=pd.concat([df_c_act, pd.DataFrame([{"nombre": v_cliente}])], ignore_index=True))
                        
                        st.success(f"¡Contrato generado para {u_sel}!")
                        st.balloons()
                        st.cache_data.clear()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

# --- MÓDULO: DETALLE DE CRÉDITO ---
elif menu == "📊 Detalle de Crédito":
    st.subheader("Estado de Cuenta y Tabla de Amortización")
    df_v = cargar_datos("ventas")
    
    if df_v.empty:
        st.info("No hay ventas registradas.")
    else:
        u_busqueda = st.selectbox("Seleccione la Ubicación Vendida", options=df_v['ubicacion'].tolist())
        datos = df_v[df_v['ubicacion'] == u_busqueda].iloc[0]
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.write(f"**Cliente:** {datos['cliente']}")
            st.write(f"**Fecha:** {datos['fecha']}")
        with c2:
            st.write(f"**Precio Total:** ${datos['precio_total']:,.2f}")
            st.write(f"**Enganche:** ${datos['enganche']:,.2f}")
        with c3:
            st.metric("Mensualidad", f"${datos['mensualidad']:,.2f}")
            st.write(f"**Plazo:** {datos['plazo_meses']} meses")

        st.divider()
        
        # Generar tabla proyectada
        tabla = []
        fecha_pago = datetime.strptime(str(datos['fecha']), '%Y-%m-%d')
        saldo_restante = float(datos['precio_total']) - float(datos['enganche'])
        
        for i in range(1, int(datos['plazo_meses']) + 1):
            fecha_pago += relativedelta(months=1)
            saldo_restante -= float(datos['mensualidad'])
            tabla.append({
                "No. Pago": i,
                "Fecha de Vencimiento": fecha_pago.strftime('%d/%m/%Y'),
                "Cuota Mensual": datos['mensualidad'],
                "Saldo Final": max(saldo_restante, 0),
                "Estatus": "Pendiente"
            })
        
        st.dataframe(pd.DataFrame(tabla), use_container_width=True, hide_index=True)

# --- MÓDULO: CATALOGO ---
elif menu == "📑 Catálogo":
    st.subheader("Inventario General")
    with st.expander("➕ Registrar Lote Nuevo"):
        with st.form("new_lote", clear_on_submit=True):
            col_a, col_b, col_c = st.columns(3)
            mz = col_a.number_input("Manzana", min_value=1)
            lt = col_b.number_input("Lote", min_value=1)
            pr = col_c.number_input("Precio ($)", min_value=0.0)
            if st.form_submit_button("Guardar en Catálogo"):
                df_c = cargar_datos("ubicaciones")
                nuevo_l = pd.DataFrame([{"ubicacion": f"M{mz}-L{lt}", "manzana": mz, "lote": lt, "precio": pr, "estatus": "Disponible"}])
                conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=pd.concat([df_c, nuevo_l], ignore_index=True))
                st.success("Lote registrado.")
                st.cache_data.clear()
                st.rerun()

    df_cat = cargar_datos("ubicaciones")
    if not df_cat.empty:
        st.dataframe(df_cat[["ubicacion", "precio", "estatus"]], use_container_width=True, hide_index=True)

# --- MÓDULO: DIRECTORIO ---
elif menu == "📇 Directorio":
    t1, t2 = st.tabs(["Clientes", "Vendedores"])
    with t1: st.dataframe(cargar_datos("clientes"), use_container_width=True, hide_index=True)
    with t2: st.dataframe(cargar_datos("vendedores"), use_container_width=True, hide_index=True)

# Footer de sistema
st.sidebar.write("---")
st.sidebar.success("Sistema Conectado y Operativo")
