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
        df = df.dropna(axis=1, how='all').dropna(axis=0, how='all')
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

        if st.button("Confirmar Venta y Generar Contrato", type="primary"):
            try:
                with st.spinner("Guardando..."):
                    df_ventas_act = cargar_datos("ventas")
                    nueva_venta = pd.DataFrame([{
                        "fecha": v_fecha.strftime('%Y-%m-%d'),
                        "ubicacion": u_sel,
                        "cliente": v_cliente,
                        "vendedor": v_vendedor,
                        "precio_total": float(v_precio),
                        "enganche": float(v_enganche),
                        "plazo_meses": int(v_plazo),
                        "mensualidad": float(mensualidad),
                        "comision": float(v_comision),
                        "estatus_pago": "Activo"
                    }])
                    df_ubi.loc[df_ubi['ubicacion'] == u_sel, 'estatus'] = 'Vendido'
                    conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=pd.concat([df_ventas_act, nueva_venta], ignore_index=True))
                    conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_ubi)
                    if c_input == "+ Agregar Nuevo Cliente":
                        df_c_act = cargar_datos("clientes")
                        conn.update(spreadsheet=URL_SHEET, worksheet="clientes", data=pd.concat([df_c_act, pd.DataFrame([{"nombre": v_cliente}])], ignore_index=True))
                    st.success("¡Venta exitosa!")
                    st.balloons()
                    st.cache_data.clear()
            except Exception as e: st.error(e)

# --- MÓDULO: DETALLE DE CRÉDITO (CONECTADO A PAGOS) ---
elif menu == "📊 Detalle de Crédito":
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")
    
    if df_v.empty:
        st.warning("No hay ventas registradas.")
    else:
        df_v['display_name'] = df_v['ubicacion'] + " | " + df_v['cliente']
        u_busqueda = st.selectbox("Seleccione Contrato", options=df_v['display_name'].tolist())
        datos = df_v[df_v['display_name'] == u_busqueda].iloc[0]
        
        # Calcular abonos reales realizados
        total_abonado = df_p[df_p['ubicacion'] == datos['ubicacion']]['monto'].sum() if not df_p.empty else 0.0
        
        st.markdown("---")
        c_alt1, c_alt2 = st.columns([2, 1])
        with c_alt1:
            st.markdown(f"### 👤 Cliente: {datos['cliente']}")
            st.markdown(f"#### 📍 Ubicación: {datos['ubicacion']}")
            st.write(f"📅 **Fecha Contrato:** {datos['fecha']}")
            st.write(f"💰 **Precio de Venta:** {fmt_moneda(datos['precio_total'])}")
            st.write(f"💵 **Enganche:** {fmt_moneda(datos['enganche'])}")
            st.write(f"🔢 **Plazo:** {int(datos['plazo_meses'])} meses")
        with c_alt2:
            monto_financiar = float(datos['precio_total']) - float(datos['enganche'])
            saldo_real = monto_financiar - total_abonado
            st.metric("SALDO RESTANTE REAL", fmt_moneda(saldo_real))
            st.metric("TOTAL ABONADO", fmt_moneda(total_abonado))
            st.write(f"Mensualidad: {fmt_moneda(datos['mensualidad'])}")

        st.divider()
        st.subheader("🗓️ Estado de Cuenta de Mensualidades")
        
        tabla = []
        f_pago = datetime.strptime(str(datos['fecha']), '%Y-%m-%d')
        saldo_teorico = monto_financiar
        acumulado_pagos = total_abonado # Para ir restando a las cuotas
        
        for i in range(1, int(datos['plazo_meses']) + 1):
            f_pago += relativedelta(months=1)
            cuota = float(datos['mensualidad'])
            
            # Lógica de estatus: si el dinero abonado alcanza para cubrir esta cuota
            if acumulado_pagos >= cuota:
                estatus = "✅ Pagado"
                acumulado_pagos -= cuota
            elif acumulado_pagos > 0:
                estatus = f"🔶 Abono parcial ({fmt_moneda(acumulado_pagos)})"
                acumulado_pagos = 0
            else:
                estatus = "⏳ Pendiente"
            
            saldo_teorico -= cuota
            tabla.append({
                "Mes": int(i),
                "Vencimiento": f_pago.strftime('%d / %m / %Y'),
                "Cuota": cuota,
                "Saldo tras pago": max(saldo_teorico, 0),
                "Estatus": estatus
            })
        
        st.dataframe(pd.DataFrame(tabla), use_container_width=True, hide_index=True,
                     column_config={
                         "Cuota": st.column_config.NumberColumn(format="$%,.2f"),
                         "Saldo tras pago": st.column_config.NumberColumn(format="$%,.2f"),
                         "Mes": st.column_config.NumberColumn(format="%d")
                     })

# --- MÓDULO: COBRANZA ---
elif menu == "💰 Cobranza":
    st.subheader("Registro de Abonos")
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")

    if df_v.empty:
        st.info("No hay contratos activos.")
    else:
        df_v['display_name'] = df_v['ubicacion'] + " | " + df_v['cliente']
        c_sel = st.selectbox("Seleccione el Contrato", options=df_v['display_name'].tolist())
        datos_v = df_v[df_v['display_name'] == c_sel].iloc[0]
        
        pagos_hechos = df_p[df_p['ubicacion'] == datos_v['ubicacion']]['monto'].sum() if not df_p.empty else 0.0
        saldo_actual = (float(datos_v['precio_total']) - float(datos_v['enganche'])) - pagos_hechos
        
        col_c1, col_c2, col_c3 = st.columns(3)
        col_c1.metric("Mensualidad", fmt_moneda(datos_v['mensualidad']))
        col_c2.metric("Total Abonado", fmt_moneda(pagos_hechos))
        col_c3.metric("Saldo Pendiente", fmt_moneda(saldo_actual))
        
        with st.form("form_abono", clear_on_submit=True):
            f1, f2, f3 = st.columns(3)
            fecha_pago = f1.date_input("Fecha", value=datetime.now())
            monto_pago = f2.number_input("Monto ($)", min_value=0.0, value=float(datos_v['mensualidad']), step=100.0)
            met_pago = f3.selectbox("Método", ["Transferencia", "Efectivo", "Depósito"])
            if st.form_submit_button("Registrar"):
                try:
                    nuevo_p = pd.DataFrame([{"fecha": fecha_pago.strftime('%Y-%m-%d'), "ubicacion": datos_v['ubicacion'], "cliente": datos_v['cliente'], "monto": float(monto_pago), "metodo": met_pago}])
                    conn.update(spreadsheet=URL_SHEET, worksheet="pagos", data=pd.concat([df_p, nuevo_p], ignore_index=True))
                    st.success("¡Abono registrado!"); st.cache_data.clear(); st.rerun()
                except Exception as e: st.error(e)

# --- MÓDULO: CATALOGO ---
elif menu == "📑 Catálogo":
    st.subheader("Gestión de Inventario")
    df_cat = cargar_datos("ubicaciones")
    if not df_cat.empty:
        df_cat["precio"] = pd.to_numeric(df_cat["precio"], errors='coerce')
        st.dataframe(df_cat[["ubicacion", "precio", "estatus"]], use_container_width=True, hide_index=True,
                     column_config={"precio": st.column_config.NumberColumn(format="$%,.2f")})

# --- MÓDULO: DIRECTORIO ---
elif menu == "📇 Directorio":
    t1, t2 = st.tabs(["Clientes", "Vendedores"])
    with t1: st.dataframe(cargar_datos("clientes"), use_container_width=True, hide_index=True)
    with t2: st.dataframe(cargar_datos("vendedores"), use_container_width=True, hide_index=True)

st.sidebar.write("---")
st.sidebar.success("Sistema Sincronizado")
