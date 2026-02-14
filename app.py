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

# --- FUNCIÓN PARA FORMATO DE MONEDA EN TEXTO ---
def fmt_moneda(valor):
    try:
        return f"$ {float(valor):,.2f}"
    except:
        return "$ 0.00"

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
        "💸 Comisiones",
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
            
            saldo_a_financiar = round(v_precio - v_enganche, 2)
            mensualidad = round(saldo_a_financiar / v_plazo, 2) if v_plazo > 0 else 0
            
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
                        "precio_total": round(float(v_precio), 2),
                        "enganche": round(float(v_enganche), 2),
                        "plazo_meses": int(v_plazo),
                        "mensualidad": round(float(mensualidad), 2),
                        "comision": round(float(v_comision), 2),
                        "estatus_pago": "Activo"
                    }])
                    df_ubi.loc[df_ubi['ubicacion'] == u_sel, 'estatus'] = 'Vendido'
                    conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=pd.concat([df_ventas_act, nueva_venta], ignore_index=True))
                    conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_ubi)
                    
                    if v_input == "+ Agregar Nuevo Vendedor":
                        df_v_act = cargar_datos("vendedores")
                        conn.update(spreadsheet=URL_SHEET, worksheet="vendedores", data=pd.concat([df_v_act, pd.DataFrame([{"nombre": v_vendedor}])], ignore_index=True))
                        
                    st.success("¡Venta exitosa!")
                    st.cache_data.clear()
                    st.rerun()
            except Exception as e: st.error(e)

# --- MÓDULO: DETALLE DE CRÉDITO ---
elif menu == "📊 Detalle de Crédito":
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")
    
    if df_v.empty:
        st.warning("No hay ventas registradas.")
    else:
        df_v['display_name'] = df_v['ubicacion'] + " | " + df_v['cliente']
        u_busqueda = st.selectbox("Seleccione Contrato", options=df_v['display_name'].tolist())
        datos = df_v[df_v['display_name'] == u_busqueda].iloc[0]
        
        total_abonado = round(df_p[df_p['ubicacion'] == datos['ubicacion']]['monto'].sum(), 2) if not df_p.empty else 0.0
        st.markdown("---")
        c_alt1, c_alt2 = st.columns([2, 1])
        with c_alt1:
            st.markdown(f"### 👤 Cliente: {datos['cliente']}")
            st.markdown(f"#### 📍 Ubicación: {datos['ubicacion']}")
        with c_alt2:
            monto_financiar = round(float(datos['precio_total']) - float(datos['enganche']), 2)
            saldo_real = round(monto_financiar - total_abonado, 2)
            st.metric("SALDO RESTANTE REAL", fmt_moneda(saldo_real))

        st.divider()
        st.subheader("🗓️ Estado de Cuenta")
        tabla = []
        f_pago = datetime.strptime(str(datos['fecha']), '%Y-%m-%d')
        saldo_teorico = monto_financiar
        acumulado_pagos = total_abonado
        
        for i in range(1, int(datos['plazo_meses']) + 1):
            f_pago += relativedelta(months=1)
            cuota = round(float(datos['mensualidad']), 2)
            if acumulado_pagos >= cuota:
                estatus = "✅ Pagado"
                acumulado_pagos = round(acumulado_pagos - cuota, 2)
            elif acumulado_pagos > 0:
                estatus = f"🔶 Parcial ({fmt_moneda(acumulado_pagos)})"
                acumulado_pagos = 0
            else: estatus = "⏳ Pendiente"
            
            saldo_teorico = round(saldo_teorico - cuota, 2)
            tabla.append({"Mes": int(i), "Vencimiento": f_pago.strftime('%d/%m/%Y'), "Cuota": cuota, "Saldo tras pago": max(saldo_teorico, 0), "Estatus": estatus})
        
        st.dataframe(pd.DataFrame(tabla), use_container_width=True, hide_index=True,
                     column_config={"Cuota": st.column_config.NumberColumn(format="$ %.2f"), "Saldo tras pago": st.column_config.NumberColumn(format="$ %.2f"), "Mes": st.column_config.NumberColumn(format="%d")})

# --- MÓDULO: COBRANZA ---
elif menu == "💰 Cobranza":
    st.subheader("Registro de Abonos")
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")
    if df_v.empty: st.info("No hay contratos activos.")
    else:
        df_v['display_name'] = df_v['ubicacion'] + " | " + df_v['cliente']
        c_sel = st.selectbox("Seleccione el Contrato", options=df_v['display_name'].tolist())
        datos_v = df_v[df_v['display_name'] == c_sel].iloc[0]
        pagos_hechos = round(df_p[df_p['ubicacion'] == datos_v['ubicacion']]['monto'].sum(), 2) if not df_p.empty else 0.0
        saldo_actual = round((float(datos_v['precio_total']) - float(datos_v['enganche'])) - pagos_hechos, 2)
        
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
                    nuevo_p = pd.DataFrame([{"fecha": fecha_pago.strftime('%Y-%m-%d'), "ubicacion": datos_v['ubicacion'], "cliente": datos_v['cliente'], "monto": round(float(monto_pago), 2), "metodo": met_pago}])
                    conn.update(spreadsheet=URL_SHEET, worksheet="pagos", data=pd.concat([df_p, nuevo_p], ignore_index=True))
                    st.success("¡Abono registrado!"); st.cache_data.clear(); st.rerun()
                except Exception as e: st.error(e)

# --- MÓDULO: COMISIONES (NUEVO) ---
elif menu == "💸 Comisiones":
    st.subheader("Gestión de Comisiones por Vendedor")
    df_v = cargar_datos("ventas")
    df_pc = cargar_datos("pagos_comisiones")
    df_vend = cargar_datos("vendedores")

    if df_v.empty:
        st.info("No hay ventas registradas para calcular comisiones.")
    else:
        vendedor_sel = st.selectbox("Seleccione un Vendedor", options=df_vend["nombre"].unique())
        
        # Filtrar ventas y pagos de comisiones del vendedor
        ventas_vendedor = df_v[df_v["vendedor"] == vendedor_sel]
        pagos_realizados = df_pc[df_pc["vendedor"] == vendedor_sel]
        
        total_comisiones_ganadas = round(ventas_vendedor["comision"].sum(), 2)
        total_comisiones_pagadas = round(pagos_realizados["monto"].sum(), 2)
        saldo_comision = round(total_comisiones_ganadas - total_comisiones_pagadas, 2)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Comisiones Ganadas", fmt_moneda(total_comisiones_ganadas))
        m2.metric("Comisiones Pagadas", fmt_moneda(total_comisiones_pagadas))
        m3.metric("Saldo por Pagar", fmt_moneda(saldo_comision), delta_color="inverse")
        
        st.divider()
        
        col_tabla, col_pago = st.columns([2, 1])
        
        with col_tabla:
            st.markdown("### 📋 Detalle de Ventas")
            if not ventas_vendedor.empty:
                # Mostrar qué se ha pagado de cada venta (simplificado)
                st.dataframe(ventas_vendedor[["fecha", "ubicacion", "cliente", "comision"]], 
                             use_container_width=True, hide_index=True,
                             column_config={"comision": st.column_config.NumberColumn(format="$ %.2f")})
            else:
                st.write("No hay ventas registradas.")

        with col_pago:
            st.markdown("### 💳 Registrar Pago")
            with st.form("pago_comision", clear_on_submit=True):
                fecha_pc = st.date_input("Fecha de Pago", value=datetime.now())
                monto_pc = st.number_input("Monto a Pagar ($)", min_value=0.0, max_value=float(saldo_comision) if saldo_comision > 0 else 0.01, step=100.0)
                referencia = st.text_input("Referencia (Banco/Recibo)")
                
                if st.form_submit_button("Confirmar Pago"):
                    if monto_pc > 0:
                        nuevo_p_com = pd.DataFrame([{
                            "fecha": fecha_pc.strftime('%Y-%m-%d'),
                            "vendedor": vendedor_sel,
                            "monto": round(float(monto_pc), 2),
                            "referencia": referencia
                        }])
                        conn.update(spreadsheet=URL_SHEET, worksheet="pagos_comisiones", data=pd.concat([df_pc, nuevo_p_com], ignore_index=True))
                        st.success("Pago de comisión registrado.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("El monto debe ser mayor a 0.")

# --- MÓDULO: CATALOGO ---
elif menu == "📑 Catálogo":
    st.subheader("Gestión de Inventario")
    df_cat = cargar_datos("ubicaciones")
    if not df_cat.empty:
        df_cat["precio"] = pd.to_numeric(df_cat["precio"], errors='coerce').round(2)
        st.dataframe(df_cat[["ubicacion", "precio", "estatus"]], use_container_width=True, hide_index=True,
                     column_config={"precio": st.column_config.NumberColumn(format="$ %.2f")})

# --- MÓDULO: DIRECTORIO ---
elif menu == "📇 Directorio":
    t1, t2 = st.tabs(["Clientes", "Vendedores"])
    with t1: st.dataframe(cargar_datos("clientes"), use_container_width=True, hide_index=True)
    with t2: st.dataframe(cargar_datos("vendedores"), use_container_width=True, hide_index=True)

st.sidebar.write("---")
st.sidebar.success("Módulo de Comisiones Activo")
