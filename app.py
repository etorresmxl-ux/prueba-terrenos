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

st.title(f"Sistema Inmobiliario - Resumen")

# --- MÓDULO: INICIO (DASHBOARD ESTRATÉGICO) ---
if menu == "🏠 Inicio":
    df_v = cargar_datos("ventas")
    df_u = cargar_datos("ubicaciones")
    df_p = cargar_datos("pagos")
    
    # --- PROCESAMIENTO DE DATOS ---
    # Aseguramos que existan las columnas clave para evitar errores si la hoja está vacía
    if "estatus_pago" not in df_v.columns: df_v["estatus_pago"] = "Activo"
    
    # Cálculos financieros
    total_ventas_usd = df_v["precio_total"].sum() if not df_v.empty else 0
    total_recaudado = df_p["monto"].sum() if not df_p.empty else 0
    total_enganches = df_v["enganche"].sum() if not df_v.empty else 0
    flujo_total = total_recaudado + total_enganches
    
    # Conteo de contratos
    contratos_activos = len(df_v[df_v["estatus_pago"].fillna("Activo") == "Activo"]) if not df_v.empty else 0
    
    # --- FILA 1: MÉTRICAS FINANCIERAS ---
    st.subheader("💰 Resumen Financiero")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ventas Totales (Contratado)", fmt_moneda(total_ventas_usd))
    c2.metric("Flujo Total Entrante", fmt_moneda(flujo_total), help="Suma de Enganches + Abonos registrados")
    c3.metric("Por Cobrar (Cartera)", fmt_moneda(total_ventas_usd - flujo_total))
    c4.metric("Contratos Activos", contratos_activos)
    
    st.divider()
    
    # --- FILA 2: INVENTARIO Y COBRANZA ---
    col_inv, col_cob = st.columns(2)
    
    with col_inv:
        st.subheader("📑 Inventario de Lotes")
        if not df_u.empty:
            disponibles = len(df_u[df_u["estatus"] == "Disponible"])
            vendidos = len(df_u[df_u["estatus"] == "Vendido"])
            total_lotes = len(df_u)
            perc_venta = (vendidos / total_lotes) if total_lotes > 0 else 0
            
            st.write(f"**Progreso de Desplazamiento:** {int(perc_venta*100)}%")
            st.progress(perc_venta)
            
            ci1, ci2 = st.columns(2)
            ci1.write(f"✅ **Disponibles:** {disponibles}")
            ci2.write(f"🤝 **Vendidos:** {vendidos}")
        else:
            st.info("Cargue datos en Ubicaciones para ver el inventario.")

    with col_cob:
        st.subheader("📅 Cobranza Mensual")
        if not df_v.empty:
            # Sumamos las mensualidades de los contratos que están "Activos"
            mensualidad_esperada = df_v[df_v["estatus_pago"] == "Activo"]["mensualidad"].sum()
            st.write("**Meta de Recaudación Mensual (Activos):**")
            st.info(f"### {fmt_moneda(mensualidad_esperada)}")
        else:
            st.info("No hay contratos activos para calcular mensualidades.")

    st.divider()

    # --- FILA 3: ÚLTIMOS MOVIMIENTOS ---
    st.subheader("⚡ Últimos 5 Pagos Registrados")
    if not df_p.empty:
        # tail(5) toma los últimos 5 y sort_values los ordena por fecha
        ultimos_p = df_p.tail(5).sort_values(by="fecha", ascending=False)
        st.table(ultimos_p[["fecha", "cliente", "monto"]].assign(monto=ultimos_p["monto"].apply(fmt_moneda)))
    else:
        st.write("No hay abonos registrados recientemente.")

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
            opciones_cli = ["+ Agregar Nuevo Cliente"] + (df_cli["nombre"].tolist() if not df_cli.empty else [])
            c_sel = st.selectbox("Cliente", options=opciones_cli)
            c_nombre = st.text_input("Nombre del Nuevo Cliente") if c_sel == "+ Agregar Nuevo Cliente" else c_sel
            
            opciones_ven = ["+ Agregar Nuevo Vendedor"] + (df_ven["nombre"].tolist() if not df_ven.empty else [])
            v_sel = st.selectbox("Vendedor", options=opciones_ven)
            vn_nombre = st.text_input("Nombre del Nuevo Vendedor") if v_sel == "+ Agregar Nuevo Vendedor" else v_sel
            v_fecha = st.date_input("Fecha", value=datetime.now())
        with col2:
            fila_ubi = df_ubi[df_ubi['ubicacion'] == u_sel]
            v_precio = st.number_input("Precio Final ($)", value=float(fila_ubi['precio'].values[0]) if not fila_ubi.empty else 0.0)
            v_enganche = st.number_input("Enganche ($)", min_value=0.0)
            v_plazo = st.number_input("Plazo (Meses)", min_value=1, value=48)
            v_comision = st.number_input("Comisión ($)", min_value=0.0)
            mensual = round((v_precio - v_enganche) / v_plazo, 2) if v_plazo > 0 else 0
            st.metric("Mensualidad", fmt_moneda(mensual))
        
        v_comentarios = st.text_area("Comentarios / Referencias")

        if st.button("Confirmar Venta", type="primary"):
            try:
                if c_sel == "+ Agregar Nuevo Cliente" and c_nombre:
                    new_id_c = int(df_cli["id_cliente"].max()) + 1 if (not df_cli.empty and "id_cliente" in df_cli.columns) else 1
                    df_new_c = pd.DataFrame([{"id_cliente": new_id_c, "nombre": c_nombre, "telefono": "", "correo": ""}])
                    conn.update(spreadsheet=URL_SHEET, worksheet="clientes", data=pd.concat([df_cli, df_new_c], ignore_index=True))
                if v_sel == "+ Agregar Nuevo Vendedor" and vn_nombre:
                    new_id_vnd = int(df_ven["id_vendedor"].max()) + 1 if (not df_ven.empty and "id_vendedor" in df_ven.columns) else 1
                    df_new_v = pd.DataFrame([{"id_vendedor": new_id_vnd, "nombre": vn_nombre, "telefono": "", "correo": ""}])
                    conn.update(spreadsheet=URL_SHEET, worksheet="vendedores", data=pd.concat([df_ven, df_new_v], ignore_index=True))

                df_v_act = cargar_datos("ventas")
                nuevo_id_v = int(df_v_act["id_venta"].max()) + 1 if (not df_v_act.empty and "id_venta" in df_v_act.columns) else 1
                
                nueva_v = pd.DataFrame([{
                    "id_venta": nuevo_id_v, "fecha": v_fecha.strftime('%Y-%m-%d'), "ubicacion": u_sel, 
                    "cliente": c_nombre, "vendedor": vn_nombre, "precio_total": round(v_precio, 2), 
                    "enganche": round(v_enganche, 2), "plazo_meses": int(v_plazo), 
                    "mensualidad": round(mensual, 2), "comision": round(v_comision, 2),
                    "comentarios": v_comentarios, "estatus_pago": "Activo"
                }])
                
                df_ubi.loc[df_ubi['ubicacion'] == u_sel, 'estatus'] = 'Vendido'
                conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=pd.concat([df_v_act, nueva_v], ignore_index=True))
                conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_ubi)
                st.success("Venta guardada exitosamente."); st.cache_data.clear(); st.rerun()
            except Exception as e: st.error(f"Error: {e}")

# --- MÓDULO: DETALLE DE CRÉDITO ---
elif menu == "📊 Detalle de Crédito":
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")
    if df_v.empty: st.warning("No hay ventas.")
    else:
        if "estatus_pago" not in df_v.columns: df_v["estatus_pago"] = "Activo"
        solo_activos = st.checkbox("Mostrar solo contratos activos", value=True)
        if solo_activos:
            df_v = df_v[df_v["estatus_pago"].fillna("Activo") == "Activo"]
        df_v['display'] = df_v['ubicacion'] + " | " + df_v['cliente']
        sel = st.selectbox("Seleccione Contrato", options=df_v['display'].tolist())
        d = df_v[df_v['display'] == sel].iloc[0]
        pagado = round(df_p[df_p['ubicacion'] == d['ubicacion']]['monto'].sum(), 2) if not df_p.empty else 0.0
        m_finan = float(d['precio_total']) - float(d['enganche'])
        saldo_r = m_finan - pagado
        porcentaje = min(pagado / m_finan, 1.0) if m_finan > 0 else 0
        c1, c2 = st.columns(2)
        c1.metric("Saldo Pendiente", fmt_moneda(saldo_r))
        c2.metric("Total Abonado", fmt_moneda(pagado))
        st.progress(porcentaje)
        if "comentarios" in d and pd.notna(d['comentarios']) and d['comentarios'] != "":
            st.info(f"**Notas:** {d['comentarios']}")
        st.subheader("📋 Tabla de Amortización")
        tabla = []
        try: f_venc = datetime.strptime(str(d['fecha']), '%Y-%m-%d')
        except: f_venc = datetime.now()
        acum_pagos = pagado
        cuota_fija = round(float(d['mensualidad']), 2)
        for i in range(1, int(d['plazo_meses']) + 1):
            f_venc += relativedelta(months=1)
            if acum_pagos >= cuota_fija: est = "✅ Pagado"; acum_pagos = round(acum_pagos - cuota_fija, 2)
            elif acum_pagos > 0: est = f"🔶 Parcial ({fmt_moneda(acum_pagos)})"; acum_pagos = 0
            else: est = "⏳ Pendiente"
            tabla.append({"Mes": i, "Vencimiento": f_venc.strftime('%d/%m/%Y'), "Cuota": cuota_fija, "Estatus": est})
        st.dataframe(pd.DataFrame(tabla), use_container_width=True, hide_index=True)

# --- MÓDULO: COBRANZA ---
elif menu == "💰 Cobranza":
    st.subheader("Registro de Abonos")
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")
    if not df_v.empty:
        if "estatus_pago" not in df_v.columns: df_v["estatus_pago"] = "Activo"
        df_v['display'] = df_v['ubicacion'] + " | " + df_v['cliente']
        lista_cobro = df_v[df_v["estatus_pago"].fillna("Activo") == "Activo"]['display'].tolist()
        c_sel = st.selectbox("Contrato", options=lista_cobro)
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

# --- MÓDULO: CATALOGO (NUEVO FILTRO TOGGLE) ---
elif menu == "📑 Catálogo":
    st.subheader("Inventario de Ubicaciones")
    df_cat = cargar_datos("ubicaciones")
    if not df_cat.empty:
        # Toggle para filtrar disponibles
        solo_disponibles = st.toggle("Mostrar solo disponibles", value=True)
        
        df_mostrar = df_cat.copy()
        if solo_disponibles:
            df_mostrar = df_mostrar[df_mostrar["estatus"] == "Disponible"]

        def estilo_disponible(row):
            return ['background-color: green; color: white' if row.estatus == 'Disponible' else '' for _ in row]
        
        cols = [c for c in ["ubicacion", "precio", "estatus"] if c in df_mostrar.columns]
        st.dataframe(
            df_mostrar[cols].style.apply(estilo_disponible, axis=1), 
            hide_index=True, 
            use_container_width=True, 
            column_config={"precio": st.column_config.NumberColumn(format="$ %.2f")}
        )
        st.caption(f"Mostrando {len(df_mostrar)} ubicaciones.")

# --- MÓDULO: DIRECTORIO ---
elif menu == "📇 Directorio":
    tipo = st.radio("Seleccione Directorio", ["Clientes", "Vendedores"], horizontal=True)
    pestana = "clientes" if tipo == "Clientes" else "vendedores"
    col_id = "id_cliente" if tipo == "Clientes" else "id_vendedor"
    df_dir = cargar_datos(pestana)
    with st.expander(f"➕ Registrar / Editar {tipo[:-1]}"):
        with st.form("form_dir", clear_on_submit=True):
            f_nom = st.text_input("Nombre Completo")
            f_tel = st.text_input("Teléfono")
            f_cor = st.text_input("Correo Electrónico")
            if st.form_submit_button("Guardar"):
                if f_nom:
                    if not df_dir.empty and f_nom in df_dir["nombre"].values:
                        df_dir.loc[df_dir["nombre"] == f_nom, ["telefono", "correo"]] = [f_tel, f_cor]
                        conn.update(spreadsheet=URL_SHEET, worksheet=pestana, data=df_dir)
                    else:
                        nuevo_id = int(df_dir[col_id].max()) + 1 if (not df_dir.empty and col_id in df_dir.columns) else 1
                        nuevo_reg = pd.DataFrame([{col_id: nuevo_id, "nombre": f_nom, "telefono": f_tel, "correo": f_cor}])
                        conn.update(spreadsheet=URL_SHEET, worksheet=pestana, data=pd.concat([df_dir, nuevo_reg], ignore_index=True))
                    st.success("Guardado."); st.cache_data.clear(); st.rerun()
                else: st.error("Nombre obligatorio")
    st.write(f"### Lista de {tipo}")
    if not df_dir.empty:
        st.dataframe(df_dir[["nombre", "telefono", "correo"]], use_container_width=True, hide_index=True)

st.sidebar.write("---")
st.sidebar.success("Sistema Sincronizado")


