import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# 1. Configuración de la página
st.set_page_config(page_title="Inmobiliaria Pro", layout="wide")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
URL_SHEET = "https://docs.google.com/spreadsheets/d/1d_G8VafPZp5jj3c1Io9kN3mG31GE70kK2Q2blxWzCCs/edit#gid=0"

# --- FUNCIÓN PARA FORMATO DE MONEDA ---
def fmt_moneda(valor):
    try:
        return f"${float(valor):,.2f}"
    except:
        return "$0.00"

# --- FUNCIONES DE APOYO ---
def cargar_datos(pestana):
    try:
        df = conn.read(spreadsheet=URL_SHEET, worksheet=pestana)
        return df
    except:
        return pd.DataFrame()

# --- BARRA LATERAL (MENÚ) ---
st.sidebar.title("Navegación")
menu = st.sidebar.radio(
    "Seleccione una sección:",
    [
        "🏠 Inicio", 
        "📝 Ventas", 
        "📊 Detalle de Crédito",
        "💰 Cobranza", 
        "📅 Historial", 
        "📑 Catálogo",
        "📇 Directorio"
    ]
)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Actualizar Base de Datos"):
    st.cache_data.clear()
    st.rerun()

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
        st.warning("No hay ubicaciones disponibles.")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            u_sel = st.selectbox("Seleccione la Ubicación", options=lista_ubi)
            
            lista_clientes = ["+ Agregar Nuevo Cliente"] + (df_cli["nombre"].tolist() if not df_cli.empty else [])
            c_input = st.selectbox("Nombre del Cliente", options=lista_clientes)
            v_cliente = st.text_input("Nombre del Nuevo Cliente") if c_input == "+ Agregar Nuevo Cliente" else c_input

            lista_vendedores = ["+ Agregar Nuevo Vendedor"] + (df_ven["nombre"].tolist() if not df_ven.empty else [])
            v_input = st.selectbox("Seleccione el Vendedor", options=lista_vendedores)
            v_vendedor = st.text_input("Nombre del Nuevo Vendedor") if v_input == "+ Agregar Nuevo Vendedor" else v_input

            v_fecha = st.date_input("Fecha de Contrato", value=datetime.now())

        with col2:
            # Obtener precio sugerido
            fila_ubi = df_ubi[df_ubi['ubicacion'] == u_sel]
            precio_sugerido = float(fila_ubi['precio'].values[0]) if not fila_ubi.empty else 0.0
            
            v_precio = st.number_input("Precio de Venta Final ($)", value=precio_sugerido, step=1000.0)
            v_enganche = st.number_input("Enganche ($)", min_value=0.0, step=1000.0)
            v_plazo = st.number_input("Plazo (Meses)", min_value=1, value=48, step=1)
            v_comision = st.number_input("Comisión del Vendedor ($)", min_value=0.0, step=100.0)
            
            saldo_a_financiar = v_precio - v_enganche
            mensualidad = saldo_a_financiar / v_plazo if v_plazo > 0 else 0
            
            st.markdown("---")
            st.metric("Saldo a Financiar", fmt_moneda(saldo_a_financiar))
            st.metric("Mensualidad Calculada", fmt_moneda(mensualidad))

        v_obs = st.text_area("Observaciones del contrato")

        if st.button("Confirmar Venta y Generar Contrato", type="primary"):
            try:
                with st.spinner("Guardando..."):
                    df_ventas_act = cargar_datos("ventas")
                    nueva_venta = pd.DataFrame([{
                        "fecha": v_fecha.strftime('%Y-%m-%d'),
                        "ubicacion": u_sel,
                        "cliente": v_cliente,
                        "vendedor": v_vendedor,
                        "precio_total": v_precio,
                        "enganche": v_enganche,
                        "plazo_meses": int(v_plazo),
                        "mensualidad": mensualidad,
                        "comision": v_comision,
                        "estatus_pago": "Activo",
                        "observaciones": v_obs
                    }])
                    
                    df_ubi.loc[df_ubi['ubicacion'] == u_sel, 'estatus'] = 'Vendido'
                    conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=pd.concat([df_ventas_act, nueva_venta], ignore_index=True))
                    conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_ubi)
                    
                    if c_input == "+ Agregar Nuevo Cliente":
                        df_c_act = cargar_datos("clientes")
                        conn.update(spreadsheet=URL_SHEET, worksheet="clientes", data=pd.concat([df_c_act, pd.DataFrame([{"nombre": v_cliente}])], ignore_index=True))
                    
                    if v_input == "+ Agregar Nuevo Vendedor":
                        df_v_act = cargar_datos("vendedores")
                        conn.update(spreadsheet=URL_SHEET, worksheet="vendedores", data=pd.concat([df_v_act, pd.DataFrame([{"nombre": v_vendedor}])], ignore_index=True))

                    st.success("¡Venta exitosa!")
                    st.balloons()
                    st.cache_data.clear()
            except Exception as e:
                st.error(f"Error: {e}")

# --- MÓDULO: DETALLE DE CRÉDITO ---
elif menu == "📊 Detalle de Crédito":
    df_v = cargar_datos("ventas")
    
    if df_v.empty:
        st.warning("No hay ventas registradas.")
    else:
        df_v['display_name'] = df_v['ubicacion'] + " | " + df_v['cliente']
        u_busqueda = st.selectbox("Seleccione Contrato", options=df_v['display_name'].tolist())
        datos = df_v[df_v['display_name'] == u_busqueda].iloc[0]
        
        st.markdown("---")
        c_alt1, c_alt2 = st.columns([2, 1])
        with c_alt1:
            st.markdown(f"### 👤 Cliente: {datos['cliente']}")
            st.markdown(f"#### 📍 Ubicación: {datos['ubicacion']}")
            st.write(f"📅 **Fecha de Contrato:** {datos['fecha']}")
            st.write(f"💰 **Precio de Venta:** {fmt_moneda(datos['precio_total'])}")
            st.write(f"💵 **Enganche:** {fmt_moneda(datos['enganche'])}")
            st.write(f"🔢 **Plazo:** {int(datos['plazo_meses'])} meses")
        with c_alt2:
            saldo_r = float(datos['precio_total']) - float(datos['enganche'])
            st.metric("SALDO RESTANTE", fmt_moneda(saldo_r))
            st.metric("MENSUALIDAD", fmt_moneda(datos['mensualidad']))

        st.divider()
        st.subheader("🗓️ Tabla de Amortización Proyectada")
        
        tabla = []
        f_pago = datetime.strptime(str(datos['fecha']), '%Y-%m-%d')
        s_restante = float(datos['precio_total']) - float(datos['enganche'])
        
        for i in range(1, int(datos['plazo_meses']) + 1):
            f_pago += relativedelta(months=1)
            s_restante -= float(datos['mensualidad'])
            tabla.append({
                "Mes": int(i),
                "Vencimiento": f_pago.strftime('%d / %m / %Y'),
                "Monto Cuota": datos['mensualidad'],
                "Saldo tras el pago": max(s_restante, 0),
                "Estado": "⏳ Pendiente"
            })
        
        st.dataframe(pd.DataFrame(tabla), use_container_width=True, hide_index=True,
                     column_config={
                         "Monto Cuota": st.column_config.NumberColumn(format="$%,.2f"),
                         "Saldo tras el pago": st.column_config.NumberColumn(format="$%,.2f"),
                         "Mes": st.column_config.NumberColumn(format="%d")
                     })

# --- MÓDULO: CATALOGO ---
elif menu == "📑 Catálogo":
    st.subheader("Gestión de Inventario")
    with st.expander("➕ Agregar Nueva Ubicación"):
        with st.form("nuevo_lote"):
            ca, cb, cc = st.columns(3)
            m = ca.number_input("Manzana", min_value=1, step=1)
            l = cb.number_input("Lote", min_value=1, step=1)
            p = cc.number_input("Precio ($)", min_value=0.0, step=1000.0)
            if st.form_submit_button("Registrar"):
                df_c = cargar_datos("ubicaciones")
                nuevo = pd.DataFrame([{"ubicacion": f"M{m}-L{l}", "manzana": m, "lote": l, "precio": p, "estatus": "Disponible"}])
                conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=pd.concat([df_c, nuevo], ignore_index=True))
                st.success("Registrado.")
                st.cache_data.clear()
                st.rerun()

    df_cat = cargar_datos("ubicaciones")
    if not df_cat.empty:
        st.dataframe(
            df_cat[["ubicacion", "precio", "estatus"]], 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "precio": st.column_config.NumberColumn(format="$%,.2f")
            }
        )

# --- MÓDULO: DIRECTORIO ---
elif menu == "📇 Directorio":
    t1, t2 = st.tabs(["Clientes", "Vendedores"])
    with t1: 
        st.dataframe(cargar_datos("clientes"), use_container_width=True, hide_index=True)
    with t2: 
        st.dataframe(cargar_datos("vendedores"), use_container_width=True, hide_index=True)

# Módulos restantes
elif menu == "🏠 Inicio": st.info("Panel General de la Inmobiliaria")
elif menu == "💰 Cobranza": st.info("Módulo de Cobranza - Próximamente")
elif menu == "📅 Historial": st.info("Historial de movimientos y pagos")

st.sidebar.write("---")
st.sidebar.success("Sistema Conectado y Operativo")
