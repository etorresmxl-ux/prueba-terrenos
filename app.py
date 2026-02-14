import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Inmobiliaria Pro", layout="wide")

# 2. CONEXIÓN A GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)
URL_SHEET = "https://docs.google.com/spreadsheets/d/1d_G8VafPZp5jj3c1Io9kN3mG31GE70kK2Q2blxWzCCs/edit#gid=0"

# --- FUNCIÓN PARA FORMATO DE MONEDA ---
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
    ["🏠 Inicio", "📝 Ventas", "📊 Detalle de Crédito", "💰 Cobranza", "💸 Comisiones", "📑 Catálogo", "📇 Directorio"]
)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Actualizar Base de Datos"):
    st.cache_data.clear()
    st.rerun()

st.title(f"Sistema Inmobiliario - {menu[2:]}")

# --- MÓDULO: INICIO ---
if menu == "🏠 Inicio":
    st.subheader("Resumen de Operaciones")
    df_v = cargar_datos("ventas")
    df_u = cargar_datos("ubicaciones")
    c1, c2, c3 = st.columns(3)
    if not df_v.empty:
        c1.metric("Ventas Totales", fmt_moneda(df_v["precio_total"].sum()))
        c2.metric("Contratos Activos", len(df_v))
    if not df_u.empty:
        c3.metric("Lotes Disponibles", len(df_u[df_u["estatus"] == "Disponible"]))

# --- MÓDULO: VENTAS ---
elif menu == "📝 Ventas":
    st.subheader("Generación de Nuevo Contrato")
    df_ubi = cargar_datos("ubicaciones")
    df_cli = cargar_datos("clientes")
    df_ven = cargar_datos("vendedores")
    lista_ubi = df_ubi[df_ubi['estatus'] == 'Disponible']['ubicacion'].tolist() if not df_ubi.empty else []

    if not lista_ubi:
        st.warning("No hay ubicaciones disponibles.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            u_sel = st.selectbox("Seleccione la Ubicación", options=lista_ubi)
            c_input = st.selectbox("Cliente", options=df_cli["nombre"].tolist() if not df_cli.empty else [])
            v_input = st.selectbox("Vendedor", options=df_ven["nombre"].tolist() if not df_ven.empty else [])
            v_fecha = st.date_input("Fecha", value=datetime.now())
        with col2:
            fila_ubi = df_ubi[df_ubi['ubicacion'] == u_sel]
            v_precio = st.number_input("Precio Final ($)", value=float(fila_ubi['precio'].values[0]) if not fila_ubi.empty else 0.0)
            v_enganche = st.number_input("Enganche ($)", min_value=0.0)
            v_plazo = st.number_input("Plazo (Meses)", min_value=1, value=48)
            v_comision = st.number_input("Comisión ($)", min_value=0.0)
            mensual = round((v_precio - v_enganche) / v_plazo, 2) if v_plazo > 0 else 0
            st.metric("Mensualidad", fmt_moneda(mensual))

        if st.button("Confirmar Venta", type="primary"):
            df_v_act = cargar_datos("ventas")
            nueva = pd.DataFrame([{"fecha": v_fecha.strftime('%Y-%m-%d'), "ubicacion": u_sel, "cliente": c_input, "vendedor": v_input, "precio_total": round(v_precio, 2), "enganche": round(v_enganche, 2), "plazo_meses": int(v_plazo), "mensualidad": round(mensual, 2), "comision": round(v_comision, 2)}])
            df_ubi.loc[df_ubi['ubicacion'] == u_sel, 'estatus'] = 'Vendido'
            conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=pd.concat([df_v_act, nueva], ignore_index=True))
            conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_ubi)
            st.success("Venta Guardada"); st.cache_data.clear(); st.rerun()

# --- MÓDULO: DETALLE DE CRÉDITO (RESTAURADO) ---
elif menu == "📊 Detalle de Crédito":
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")
    if df_v.empty: 
        st.warning("No hay ventas registradas.")
    else:
        df_v['display'] = df_v['ubicacion'] + " | " + df_v['cliente']
        sel = st.selectbox("Seleccione Contrato", options=df_v['display'].tolist())
        d = df_v[df_v['display'] == sel].iloc[0]
        
        # Cálculos de saldos
        pagado = round(df_p[df_p['ubicacion'] == d['ubicacion']]['monto'].sum(), 2) if not df_p.empty else 0.0
        m_finan = float(d['precio_total']) - float(d['enganche'])
        saldo_r = m_finan - pagado

        c1, c2 = st.columns(2)
        c1.metric("Saldo Pendiente Real", fmt_moneda(saldo_r))
        c2.metric("Total Abonado a Mensualidades", fmt_moneda(pagado))

        st.subheader("📋 Tabla de Amortización Dinámica")
        tabla = []
        # Intentar convertir fecha de string a objeto datetime
        try:
            f_venc = datetime.strptime(str(d['fecha']), '%Y-%m-%d')
        except:
            f_venc = datetime.now()
            
        acum_pagos = pagado
        cuota_fija = round(float(d['mensualidad']), 2)
        
        for i in range(1, int(d['plazo_meses']) + 1):
            f_venc += relativedelta(months=1)
            
            if acum_pagos >= cuota_fija:
                estatus = "✅ Pagado"
                acum_pagos = round(acum_pagos - cuota_fija, 2)
            elif acum_pagos > 0:
                estatus = f"🔶 Parcial ({fmt_moneda(acum_pagos)})"
                acum_pagos = 0
            else:
                estatus = "⏳ Pendiente"
                
            tabla.append({
                "Mes": i, 
                "Vencimiento": f_venc.strftime('%d/%b/%Y'), 
                "Cuota Sugerida": cuota_fija, 
                "Estatus": estatus
            })
        
        st.dataframe(pd.DataFrame(tabla), use_container_width=True, hide_index=True, 
                     column_config={"Cuota Sugerida": st.column_config.NumberColumn(format="$ %.2f")})

# --- MÓDULO: COBRANZA ---
elif menu == "💰 Cobranza":
    st.subheader("Registro de Abonos")
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")
    if not df_v.empty:
        df_v['display'] = df_v['ubicacion'] + " | " + df_v['cliente']
        c_sel = st.selectbox("Contrato", options=df_v['display'].tolist())
        dv = df_v[df_v['display'] == c_sel].iloc[0]
        with st.form("pago_form"):
            monto_p = st.number_input("Monto ($)", value=float(dv['mensualidad']))
            if st.form_submit_button("Registrar Abono"):
                nuevo_p = pd.DataFrame([{"fecha": datetime.now().strftime('%Y-%m-%d'), "ubicacion": dv['ubicacion'], "cliente": dv['cliente'], "monto": round(monto_p, 2)}])
                conn.update(spreadsheet=URL_SHEET, worksheet="pagos", data=pd.concat([df_p, nuevo_p], ignore_index=True))
                st.success("Pago registrado"); st.cache_data.clear(); st.rerun()

# --- MÓDULO: COMISIONES ---
elif menu == "💸 Comisiones":
    st.subheader("Gestión de Comisiones")
    df_v = cargar_datos("ventas")
    df_pc = cargar_datos("pagos_comisiones")
    df_vend = cargar_datos("vendedores")
    if not df_vend.empty:
        v_sel = st.selectbox("Vendedor", options=df_vend["nombre"].unique())
        ganado = round(df_v[df_v["vendedor"] == v_sel]["comision"].sum(), 2) if not df_v.empty else 0.0
        pagado = round(df_pc[df_pc["vendedor"] == v_sel]["monto"].sum(), 2) if not df_pc.empty else 0.0
        st.metric("Saldo Pendiente", fmt_moneda(ganado - pagado))
        with st.form("p_com"):
            m_pago = st.number_input("Monto ($)", min_value=0.0)
            if st.form_submit_button("Pagar"):
                nuevo = pd.DataFrame([{"fecha": datetime.now().strftime('%Y-%m-%d'), "vendedor": v_sel, "monto": round(m_pago, 2)}])
                conn.update(spreadsheet=URL_SHEET, worksheet="pagos_comisiones", data=pd.concat([df_pc, nuevo], ignore_index=True))
                st.success("Pagado"); st.cache_data.clear(); st.rerun()

# --- MÓDULO: CATALOGO ---
elif menu == "📑 Catálogo":
    st.subheader("Inventario de Ubicaciones")
    df_cat = cargar_datos("ubicaciones")
    if not df_cat.empty:
        def estilo_disponible(row):
            return ['background-color: green; color: white' if row.estatus == 'Disponible' else '' for _ in row]
        cols = [c for c in ["ubicacion", "precio", "estatus"] if c in df_cat.columns]
        st.dataframe(df_cat[cols].style.apply(estilo_disponible, axis=1), hide_index=True, use_container_width=True, column_config={"precio": st.column_config.NumberColumn(format="$ %.2f")})

# --- MÓDULO: DIRECTORIO ---
elif menu == "📇 Directorio":
    tipo = st.radio("Seleccione Directorio", ["Clientes", "Vendedores"], horizontal=True)
    pestana = "clientes" if tipo == "Clientes" else "vendedores"
    col_id = "id_cliente" if tipo == "Clientes" else "id_vendedor"
    df_dir = cargar_datos(pestana)
    
    with st.expander(f"➕ Registrar Nuevo {tipo[:-1]}"):
        with st.form("form_dir", clear_on_submit=True):
            f_nom = st.text_input("Nombre Completo")
            f_tel = st.text_input("Teléfono")
            f_cor = st.text_input("Correo Electrónico")
            if st.form_submit_button("Guardar"):
                if f_nom:
                    nuevo_id = int(df_dir[col_id].max()) + 1 if (not df_dir.empty and col_id in df_dir.columns) else 1
                    nuevo_reg = pd.DataFrame([{col_id: nuevo_id, "nombre": f_nom, "telefono": f_tel, "correo": f_cor}])
                    conn.update(spreadsheet=URL_SHEET, worksheet=pestana, data=pd.concat([df_dir, nuevo_reg], ignore_index=True))
                    st.success(f"Registrado con ID: {nuevo_id}"); st.cache_data.clear(); st.rerun()
                else: st.error("Nombre obligatorio")

    st.write(f"### Lista de {tipo}")
    if not df_dir.empty:
        vistas = [c for c in ["nombre", "telefono", "correo"] if c in df_dir.columns]
        st.dataframe(df_dir[vistas], use_container_width=True, hide_index=True)

st.sidebar.write("---")
st.sidebar.success("Sistema Sincronizado")
