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

# --- BARRA LATERAL ---
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
    st.subheader("Resumen General")
    df_v = cargar_datos("ventas")
    df_u = cargar_datos("ubicaciones")
    
    c1, c2, c3 = st.columns(3)
    if not df_v.empty:
        total_v = df_v["precio_total"].sum()
        c1.metric("Ventas Totales", fmt_moneda(total_v))
        c2.metric("Contratos Activos", len(df_v))
    
    if not df_u.empty:
        dispo = len(df_u[df_u["estatus"] == "Disponible"])
        c3.metric("Lotes Disponibles", dispo)
    
    st.info("Utilice el menú lateral para gestionar la operación.")

# --- MÓDULO: VENTAS ---
elif menu == "📝 Ventas":
    st.subheader("Generación de Nuevo Contrato")
    df_ubi = cargar_datos("ubicaciones")
    df_cli = cargar_datos("clientes")
    df_ven = cargar_datos("vendedores")

    if not df_ubi.empty:
        df_disponibles = df_ubi[df_ubi['estatus'] == 'Disponible']
        lista_ubi = df_disponibles['ubicacion'].tolist()
    else: lista_ubi = []

    if not lista_ubi:
        st.warning("No hay ubicaciones disponibles en el catálogo.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            u_sel = st.selectbox("Seleccione la Ubicación", options=lista_ubi)
            lista_clientes = ["+ Agregar Nuevo Cliente"] + (df_cli["nombre"].tolist() if not df_cli.empty else [])
            c_input = st.selectbox("Nombre del Cliente", options=lista_clientes)
            v_cliente = st.text_input("Nuevo Cliente") if c_input == "+ Agregar Nuevo Cliente" else c_input
            lista_vendedores = ["+ Agregar Nuevo Vendedor"] + (df_ven["nombre"].tolist() if not df_ven.empty else [])
            v_input = st.selectbox("Vendedor", options=lista_vendedores)
            v_vendedor = st.text_input("Nuevo Vendedor") if v_input == "+ Agregar Nuevo Vendedor" else v_input
            v_fecha = st.date_input("Fecha de Contrato", value=datetime.now())
        
        with col2:
            fila_ubi = df_ubi[df_ubi['ubicacion'] == u_sel]
            p_sugerido = float(fila_ubi['precio'].values[0]) if not fila_ubi.empty else 0.0
            v_precio = st.number_input("Precio Final ($)", value=p_sugerido, step=1000.0)
            v_enganche = st.number_input("Enganche ($)", min_value=0.0, step=1000.0)
            v_plazo = st.number_input("Plazo (Meses)", min_value=1, value=48, step=1)
            v_comision = st.number_input("Comisión ($)", min_value=0.0, step=100.0)
            
            saldo_fin = round(v_precio - v_enganche, 2)
            mensual = round(saldo_fin / v_plazo, 2) if v_plazo > 0 else 0
            
            st.metric("Saldo a Financiar", fmt_moneda(saldo_fin))
            st.metric("Mensualidad", fmt_moneda(mensual))

        if st.button("Confirmar Venta", type="primary"):
            try:
                df_v_act = cargar_datos("ventas")
                nueva = pd.DataFrame([{
                    "fecha": v_fecha.strftime('%Y-%m-%d'), "ubicacion": u_sel, "cliente": v_cliente,
                    "vendedor": v_vendedor, "precio_total": round(v_precio, 2), "enganche": round(v_enganche, 2),
                    "plazo_meses": int(v_plazo), "mensualidad": round(mensual, 2), "comision": round(v_comision, 2), "estatus_pago": "Activo"
                }])
                df_ubi.loc[df_ubi['ubicacion'] == u_sel, 'estatus'] = 'Vendido'
                conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=pd.concat([df_v_act, nueva], ignore_index=True))
                conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_ubi)
                if c_input == "+ Agregar Nuevo Cliente":
                    df_c_act = cargar_datos("clientes")
                    conn.update(spreadsheet=URL_SHEET, worksheet="clientes", data=pd.concat([df_c_act, pd.DataFrame([{"nombre": v_cliente}])], ignore_index=True))
                if v_input == "+ Agregar Nuevo Vendedor":
                    df_vend_act = cargar_datos("vendedores")
                    conn.update(spreadsheet=URL_SHEET, worksheet="vendedores", data=pd.concat([df_vend_act, pd.DataFrame([{"nombre": v_vendedor}])], ignore_index=True))
                st.success("Venta Guardada"); st.cache_data.clear(); st.rerun()
            except Exception as e: st.error(e)

# --- MÓDULO: DETALLE DE CRÉDITO ---
elif menu == "📊 Detalle de Crédito":
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")
    if df_v.empty: st.warning("No hay ventas registradas.")
    else:
        df_v['display'] = df_v['ubicacion'] + " | " + df_v['cliente']
        sel = st.selectbox("Seleccione Contrato", options=df_v['display'].tolist())
        d = df_v[df_v['display'] == sel].iloc[0]
        pagado = round(df_p[df_p['ubicacion'] == d['ubicacion']]['monto'].sum(), 2) if not df_p.empty else 0.0
        m_finan = float(d['precio_total']) - float(d['enganche'])
        saldo_r = m_finan - pagado
        c1, c2 = st.columns(2)
        c1.metric("Saldo Restante Real", fmt_moneda(saldo_r))
        c2.metric("Total Abonado", fmt_moneda(pagado))
        st.subheader("Estado de Mensualidades")
        tabla = []
        f_ini = datetime.strptime(str(d['fecha']), '%Y-%m-%d')
        acum = pagado
        for i in range(1, int(d['plazo_meses']) + 1):
            f_ini += relativedelta(months=1)
            cuota = round(float(d['mensualidad']), 2)
            if acum >= cuota: est = "✅ Pagado"; acum = round(acum - cuota, 2)
            elif acum > 0: est = f"🔶 Parcial ({fmt_moneda(acum)})"; acum = 0
            else: est = "⏳ Pendiente"
            tabla.append({"Mes": i, "Vencimiento": f_ini.strftime('%d/%m/%Y'), "Cuota": cuota, "Estatus": est})
        st.dataframe(pd.DataFrame(tabla), use_container_width=True, hide_index=True, column_config={"Cuota": st.column_config.NumberColumn(format="$ %.2f")})

# --- MÓDULO: COBRANZA ---
elif menu == "💰 Cobranza":
    st.subheader("Registro de Abonos")
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")
    if df_v.empty: st.info("Sin ventas activas.")
    else:
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
    if df_vend.empty: st.warning("Registre vendedores.")
    else:
        v_sel = st.selectbox("Seleccione Vendedor", options=df_vend["nombre"].unique())
        ganado = round(df_v[df_v["vendedor"] == v_sel]["comision"].sum(), 2) if not df_v.empty else 0.0
        pagado = round(df_pc[df_pc["vendedor"] == v_sel]["monto"].sum(), 2) if not df_pc.empty else 0.0
        saldo = round(ganado - pagado, 2)
        c1, c2, c3 = st.columns(3)
        c1.metric("Comisiones Ganadas", fmt_moneda(ganado))
        c2.metric("Comisiones Pagadas", fmt_moneda(pagado))
        c3.metric("Saldo Pendiente", fmt_moneda(saldo))
        st.divider()
        col_t, col_f = st.columns([2, 1])
        with col_t:
            if not df_v.empty: st.dataframe(df_v[df_v["vendedor"] == v_sel][["fecha", "ubicacion", "comision"]], hide_index=True, use_container_width=True, column_config={"comision": st.column_config.NumberColumn(format="$ %.2f")})
        with col_f:
            with st.form("f_p_c"):
                m_pago = st.number_input("Monto ($)", min_value=0.0, max_value=float(saldo) if saldo > 0 else 0.01)
                if st.form_submit_button("Pagar"):
                    nuevo_p = pd.DataFrame([{"fecha": datetime.now().strftime('%Y-%m-%d'), "vendedor": v_sel, "monto": round(m_pago, 2)}])
                    conn.update(spreadsheet=URL_SHEET, worksheet="pagos_comisiones", data=pd.concat([df_pc, nuevo_p], ignore_index=True))
                    st.success("Pago guardado"); st.cache_data.clear(); st.rerun()

# --- MÓDULO: CATALOGO (CON RESALTADO AMARILLO) ---
elif menu == "📑 Catálogo":
    st.subheader("Inventario de Ubicaciones")
    df_cat = cargar_datos("ubicaciones")
    
    if not df_cat.empty:
        # Función para aplicar el color amarillo a las filas con estatus 'Disponible'
        def resaltar_disponibles(row):
            return ['background-color: yellow' if row.estatus == 'Disponible' else '' for _ in row]

        # Aplicamos el estilo al dataframe antes de mostrarlo
        df_estilizado = df_cat.style.apply(resaltar_disponibles, axis=1)

        st.dataframe(df_estilizado, hide_index=True, use_container_width=True,
                     column_config={
                         "precio": st.column_config.NumberColumn(format="$ %.2f")
                     })
    
    with st.expander("Añadir Nueva Ubicación"):
        with st.form("add_ubi"):
            n_ubi = st.text_input("Identificador (Ej: M1-L5)")
            n_pre = st.number_input("Precio ($)", min_value=0.0, step=1000.0)
            if st.form_submit_button("Guardar en Catálogo"):
                nueva_u = pd.DataFrame([{"ubicacion": n_ubi, "precio": n_pre, "estatus": "Disponible"}])
                conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=pd.concat([df_cat, nueva_u], ignore_index=True))
                st.success("Ubicación añadida"); st.cache_data.clear(); st.rerun()

# --- MÓDULO: DIRECTORIO ---
elif menu == "📇 Directorio":
    t1, t2 = st.tabs(["Clientes", "Vendedores"])
    t1.dataframe(cargar_datos("clientes"), use_container_width=True, hide_index=True)
    t2.dataframe(cargar_datos("vendedores"), use_container_width=True, hide_index=True)

st.sidebar.write("---")
st.sidebar.success("Sistema Sincronizado")

