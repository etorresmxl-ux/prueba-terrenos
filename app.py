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

# --- 2. BARRA LATERAL CON ICONOS RENOVADOS ---
st.sidebar.title("Navegación")
menu = st.sidebar.radio(
    "Seleccione una sección:",
    [
        "🏠 Inicio", 
        "📝 Ventas", 
        "📊 Detalle de Crédito", 
        "💰 Cobranza", 
        "💸 Gastos", 
        "🎖️ Comisiones", 
        "📍 Catálogo", 
        "📇 Directorio"
    ]
)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Actualizar Base de Datos"):
    st.cache_data.clear()
    st.rerun()

# Esto actualiza el título dinámicamente según la opción elegida
st.title(f"Sistema Inmobiliario - {menu[2:]}")

# --- MÓDULO: INICIO (DASHBOARD CON SEMÁFORO DE 3 NIVELES) ---
if menu == "🏠 Inicio":
    # 1. CARGA DE DATOS
    df_v = cargar_datos("ventas")
    df_u = cargar_datos("ubicaciones")
    df_p = cargar_datos("pagos")
    df_g = cargar_datos("gastos")
    
    # 2. PROCESAMIENTO FINANCIERO
    if "estatus_pago" not in df_v.columns: 
        df_v["estatus_pago"] = "Activo"
    
    # Ingresos y Gastos
    total_recaudado = df_p["monto"].sum() if not df_p.empty else 0
    total_enganches = df_v["enganche"].sum() if not df_v.empty else 0
    flujo_total_ingresos = total_recaudado + total_enganches
    total_gastos = df_g["monto"].sum() if not df_g.empty else 0
    utilidad_neta = flujo_total_ingresos - total_gastos
    
    # Cartera
    total_contratado = df_v["precio_total"].sum() if not df_v.empty else 0
    cartera_pendiente = total_contratado - flujo_total_ingresos

    # --- FILA 1: MÉTRICAS FINANCIERAS ---
    st.subheader("💰 Resumen Financiero Global")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ingresos Reales", fmt_moneda(flujo_total_ingresos))
    c2.metric("Gastos Operativos", fmt_moneda(total_gastos), delta=f"-{fmt_moneda(total_gastos)}", delta_color="inverse")
    c3.metric("Utilidad Neta", fmt_moneda(utilidad_neta))
    c4.metric("Cartera por Cobrar", fmt_moneda(cartera_pendiente))

    # --- FILA 2: INVENTARIO Y METAS ---
    col_inv, col_cob = st.columns(2)
    with col_inv:
        st.subheader("📑 Inventario de Lotes")
        if not df_u.empty:
            disponibles = len(df_u[df_u["estatus"] == "Disponible"])
            vendidos = len(df_u[df_u["estatus"] == "Vendido"])
            total_lotes = len(df_u)
            perc_venta = (vendidos / total_lotes) if total_lotes > 0 else 0
            st.write(f"**Progreso de Ventas:** {int(perc_venta*100)}%")
            st.progress(perc_venta)
            ci1, ci2 = st.columns(2)
            ci1.write(f"✅ **Disponibles:** {disponibles}")
            ci2.write(f"🤝 **Vendidos:** {vendidos}")

    with col_cob:
        st.subheader("📅 Meta de Cobranza Mensual")
        if not df_v.empty:
            mensualidad_esperada = df_v[df_v["estatus_pago"] == "Activo"]["mensualidad"].sum()
            st.write("**Recaudación esperada este mes:**")
            st.info(f"### {fmt_moneda(mensualidad_esperada)}")

    st.divider()

    # --- FILA 3: MONITOR DE CARTERA (SITUACIÓN DE CLIENTES CON SEMÁFORO) ---
    st.subheader("🚩 Monitor de Cartera y Cobranza")
    
    if not df_v.empty:
        monitor_data = []
        hoy = datetime.now()

        for _, venta in df_v.iterrows():
            # Pagos del cliente
            pagos_cliente = df_p[df_p['ubicacion'] == venta['ubicacion']]['monto'].sum() if not df_p.empty else 0.0
            saldo_liquidar = float(venta['precio_total']) - float(venta['enganche']) - pagos_cliente
            
            # Cálculo de tiempo y atraso
            try: fecha_con = datetime.strptime(str(venta['fecha']), '%Y-%m-%d')
            except: fecha_con = hoy
            
            meses_transcurridos = (hoy.year - fecha_con.year) * 12 + (hoy.month - fecha_con.month)
            debe_a_la_fecha = meses_transcurridos * float(venta['mensualidad'])
            pago_para_corriente = debe_a_la_fecha - pagos_cliente
            
            # NUEVA LÓGICA DE SEMÁFORO (25 / 75 DÍAS)
            if pago_para_corriente > 1.0:
                dia_pago = fecha_con.day
                try:
                    f_venc_mes = hoy.replace(day=dia_pago)
                    if hoy < f_venc_mes: f_venc_mes = f_venc_mes - relativedelta(months=1)
                except: f_venc_mes = hoy.replace(day=1) - relativedelta(days=1)
                
                dias_atraso = (hoy - f_venc_mes).days
                
                if dias_atraso <= 25:
                    estatus_c = "🟢 AL CORRIENTE"
                elif 25 < dias_atraso <= 75:
                    estatus_c = "🟡 ATRASO"
                else:
                    estatus_c = "🔴 ATRASO MAYOR"
            else:
                estatus_c = "🟢 AL CORRIENTE"
                pago_para_corriente = 0.0
                dias_atraso = 0

            monitor_data.append({
                "Ubicación": venta['ubicacion'],
                "Cliente": venta['cliente'],
                "Estatus": estatus_c,
                "Días Atraso": dias_atraso,
                "Para Estar al Corriente": pago_para_corriente,
                "Saldo Liquidar": saldo_liquidar
            })

        df_monitor = pd.DataFrame(monitor_data)
        
        # Estilo para la tabla de monitor
        def estilo_monitor(val):
            if "🔴" in str(val): return 'color: #FF4B4B; font-weight: bold'
            if "🟡" in str(val): return 'color: #F1C40F; font-weight: bold'
            if "🟢" in str(val): return 'color: #09AB3B; font-weight: bold'
            return ''

        st.dataframe(
            df_monitor.style.applymap(estilo_monitor, subset=['Estatus']),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Para Estar al Corriente": st.column_config.NumberColumn(format="$ %.2f"),
                "Saldo Liquidar": st.column_config.NumberColumn(format="$ %.2f")
            }
        )
    else:
        st.info("No hay datos para mostrar.")

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

# --- MÓDULO: DETALLE DE CRÉDITO (VISTA COMPACTA) ---
elif menu == "📊 Detalle de Crédito":
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")
    if df_v.empty: 
        st.warning("No hay ventas registradas.")
    else:
        if "estatus_pago" not in df_v.columns: df_v["estatus_pago"] = "Activo"
        
        solo_activos = st.checkbox("Mostrar solo contratos activos", value=True)
        if solo_activos:
            df_v = df_v[df_v["estatus_pago"].fillna("Activo") == "Activo"]
            
        df_v['display'] = df_v['ubicacion'] + " | " + df_v['cliente']
        sel = st.selectbox("Seleccione Contrato", options=df_v['display'].tolist())
        d = df_v[df_v['display'] == sel].iloc[0]
        
        # --- LÓGICA DE CÁLCULOS ---
        pagado = round(df_p[df_p['ubicacion'] == d['ubicacion']]['monto'].sum(), 2) if not df_p.empty else 0.0
        m_finan = float(d['precio_total']) - float(d['enganche'])
        saldo_r = m_finan - pagado
        porcentaje = min(pagado / m_finan, 1.0) if m_finan > 0 else 0

        hoy = datetime.now()
        try: f_con = datetime.strptime(str(d['fecha']), '%Y-%m-%d')
        except: f_con = hoy
        
        meses_transcurridos = (hoy.year - f_con.year) * 12 + (hoy.month - f_con.month)
        debe_a_la_fecha = meses_transcurridos * float(d['mensualidad'])
        monto_para_corriente = debe_a_la_fecha - pagado
        
        if monto_para_corriente > 1.0:
            estatus_txt = "🔴 ATRASADO"
            color = "#FF4B4B" # Rojo Streamlit
            dia_pago = f_con.day
            try:
                f_venc_mes = hoy.replace(day=dia_pago)
                if hoy < f_venc_mes: f_venc_mes = f_venc_mes - relativedelta(months=1)
            except: f_venc_mes = hoy.replace(day=1) - relativedelta(days=1)
            dias_atraso = (hoy - f_venc_mes).days
        else:
            estatus_txt = "🟢 AL CORRIENTE"
            color = "#09AB3B" # Verde Streamlit
            monto_para_corriente = 0.0
            dias_atraso = 0

        # --- VISUALIZACIÓN COMPACTA ---
        st.subheader("📋 Resumen del Crédito")
        
        # Agrupamos todo en una sola rejilla de métricas
        col1, col2, col3 = st.columns(3)
        col1.metric("Saldo para Liquidar", fmt_moneda(saldo_r))
        col2.metric("Total Abonado", fmt_moneda(pagado))
        col3.metric("Progreso", f"{int(porcentaje*100)}%")
        st.progress(porcentaje)

        # Segunda fila de métricas (Sin st.write("---") ni divisiones pesadas)
        c_est, c_dias, c_monto = st.columns(3)
        with c_est:
            st.markdown(f"<p style='margin-bottom: -10px; font-size: 14px; opacity: 0.8;'>Estatus actual:</p><h2 style='color:{color}; margin-top: 0;'>{estatus_txt}</h2>", unsafe_allow_html=True)
        
        c_dias.metric("Días de Atraso", f"{dias_atraso} días")
        c_monto.metric("Para estar al Corriente", fmt_moneda(monto_para_corriente))
        
        if "comentarios" in d and pd.notna(d['comentarios']) and d['comentarios'] != "":
            st.caption(f"📌 **Notas:** {d['comentarios']}")

        # --- TABLA DE AMORTIZACIÓN ---
        st.subheader("📅 Plan de Pagos")
        tabla = []
        f_venc_loop = f_con
        acum_pagos = pagado
        cuota_fija = round(float(d['mensualidad']), 2)
        for i in range(1, int(d['plazo_meses']) + 1):
            f_venc_loop += relativedelta(months=1)
            if acum_pagos >= cuota_fija: 
                est = "✅ Pagado"
                acum_pagos = round(acum_pagos - cuota_fija, 2)
            elif acum_pagos > 0: 
                est = f"🔶 Parcial ({fmt_moneda(acum_pagos)})"
                acum_pagos = 0
            else: 
                est = "⏳ Pendiente"
            tabla.append({"Mes": i, "Vencimiento": f_venc_loop.strftime('%d/%m/%Y'), "Cuota": cuota_fija, "Estatus": est})
        
        st.dataframe(pd.DataFrame(tabla), use_container_width=True, hide_index=True, height=300)

# --- MÓDULO: COBRANZA (REGISTRO Y HISTORIAL ROBUSTO) ---
elif menu == "💰 Cobranza":
    tab1, tab2 = st.tabs(["💵 Registrar Abono", "📜 Historial y Edición"])
    
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")

    # --- PESTAÑA 1: REGISTRO ---
    with tab1:
        st.subheader("Nuevo Ingreso")
        if not df_v.empty:
            df_v['display'] = df_v['ubicacion'] + " | " + df_v['cliente']
            lista_cobro = df_v[df_v["estatus_pago"].fillna("Activo") == "Activo"]['display'].tolist()
            
            c_sel = st.selectbox("Seleccione el Contrato", options=lista_cobro)
            dv = df_v[df_v['display'] == c_sel].iloc[0]
            
            with st.form("pago_form", clear_on_submit=True):
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    monto_p = st.number_input("Monto ($)", value=float(dv['mensualidad']), min_value=0.0)
                    f_pago = st.date_input("Fecha", value=datetime.now())
                    metodo_p = st.selectbox("Método", ["Efectivo", "Transferencia", "Tarjeta", "Cheque"])
                with col_p2:
                    folio_p = st.text_input("Folio Físico")
                
                if st.form_submit_button("Guardar Abono", type="primary"):
                    if folio_p:
                        nuevo_p = pd.DataFrame([{
                            "fecha": str(f_pago),
                            "ubicacion": dv['ubicacion'],
                            "cliente": dv['cliente'],
                            "monto": round(monto_p, 2),
                            "metodo": metodo_p,
                            "folio": folio_p.upper()
                        }])
                        df_p_fin = pd.concat([df_p, nuevo_p], ignore_index=True)
                        conn.update(spreadsheet=URL_SHEET, worksheet="pagos", data=df_p_fin)
                        st.success("Registrado correctamente."); st.cache_data.clear(); st.rerun()
                    else:
                        st.error("El Folio es obligatorio.")
        else:
            st.info("No hay contratos activos.")

    # --- PESTAÑA 2: HISTORIAL (CORREGIDO PARA EVITAR EXCEPCIONES) ---
    with tab2:
        st.subheader("Historial de Pagos")
        if not df_p.empty:
            # Limpiamos datos para evitar el error de la Imagen 2
            df_p_edit = df_p.copy()
            # Convertimos todo a string excepto el monto para que el editor no falle
            df_p_edit['monto'] = pd.to_numeric(df_p_edit['monto'], errors='coerce').fillna(0)
            
            st.write("Edita directamente en la tabla y presiona el botón de abajo:")
            
            # Editor simplificado para evitar errores de compatibilidad
            edited_df = st.data_editor(
                df_p_edit.sort_index(ascending=False),
                use_container_width=True,
                column_config={
                    "monto": st.column_config.NumberColumn(format="$ %.2f"),
                }
            )

            if st.button("💾 Aplicar Cambios al Historial"):
                # Reemplazamos la base completa con lo editado
                # Es más seguro reconstruir el orden original antes de subir
                df_final_subir = edited_df.sort_index()
                conn.update(spreadsheet=URL_SHEET, worksheet="pagos", data=df_final_subir)
                st.success("¡Cambios guardados!"); st.cache_data.clear(); st.rerun()
        else:
            st.info("No hay pagos registrados.")

# --- MÓDULO: GASTOS DE OPERACIÓN ---
elif menu == "💸 Gastos":
    st.subheader("Registro de Gastos Operativos")
    df_g = cargar_datos("gastos")
    
    # Formulario de Registro
    with st.expander("➕ Registrar Nuevo Gasto", expanded=True):
        with st.form("form_gastos", clear_on_submit=True):
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                g_fecha = st.date_input("Fecha del Gasto", value=datetime.now())
                g_cat = st.selectbox("Categoría", [
                    "Marketing / Publicidad", 
                    "Administrativo", 
                    "Comisiones Externas", 
                    "Mantenimiento / Limpieza", 
                    "Servicios (Luz, Agua, Internet)",
                    "Impuestos / Legal",
                    "Otros"
                ])
                g_monto = st.number_input("Monto del Gasto ($)", min_value=0.0, step=100.0)
            with col_g2:
                g_desc = st.text_input("Descripción / Concepto (ej. Pago Facebook Ads)")
                g_metodo = st.selectbox("Método de Pago", ["Transferencia", "Efectivo", "Tarjeta", "Cheque"])
                st.write("---")
                btn_gasto = st.form_submit_button("Guardar Gasto", type="primary")

            if btn_gasto:
                if g_monto > 0 and g_desc:
                    nuevo_id_g = int(df_g["id_gasto"].max()) + 1 if (not df_g.empty and "id_gasto" in df_g.columns) else 1
                    nuevo_g = pd.DataFrame([{
                        "id_gasto": nuevo_id_g,
                        "fecha": g_fecha.strftime('%Y-%m-%d'),
                        "categoria": g_cat,
                        "descripcion": g_desc,
                        "monto": round(g_monto, 2),
                        "metodo_pago": g_metodo
                    }])
                    conn.update(spreadsheet=URL_SHEET, worksheet="gastos", data=pd.concat([df_g, nuevo_g], ignore_index=True))
                    st.success("Gasto registrado correctamente.")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Por favor ingresa un monto y descripción.")

    st.divider()
    
    # Visualización y Resumen
    st.subheader("Historial de Gastos")
    if not df_g.empty:
        # Filtros rápidos
        c_f1, c_f2 = st.columns(2)
        with c_f1:
            filtro_cat = st.multiselect("Filtrar por Categoría", options=df_g["categoria"].unique())
        
        df_g_filtrado = df_g.copy()
        if filtro_cat:
            df_g_filtrado = df_g_filtrado[df_g_filtrado["categoria"].isin(filtro_cat)]
        
        # Métricas de gastos
        total_g = df_g_filtrado["monto"].sum()
        st.metric("Total Gastado (Selección)", fmt_moneda(total_g))
        
        st.dataframe(
            df_g_filtrado.sort_values(by="fecha", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "monto": st.column_config.NumberColumn(format="$ %.2f")
            }
        )
    else:
        st.info("No hay gastos registrados aún.")

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

# --- MÓDULO: CATALOGO (INVENTARIO CON FASE) ---
elif menu == "📍 Catálogo":
    tab_cat1, tab_cat2 = st.tabs(["📋 Ver Inventario", "🏗️ Gestionar Lotes"])
    
    df_cat = cargar_datos("ubicaciones")
    
    # --- PESTAÑA 1: VISTA DE INVENTARIO ---
    with tab_cat1:
        st.subheader("Estado Actual del Inventario")
        if not df_cat.empty:
            # Filtros rápidos
            c_f1, c_f2 = st.columns(2)
            with c_f1:
                solo_dis = st.toggle("Mostrar solo disponibles", value=True)
            with c_f2:
                # Opcional: Filtro por Fase
                fases_disponibles = sorted(df_cat["fase"].unique().tolist()) if "fase" in df_cat.columns else []
                filtro_fase = st.multiselect("Filtrar por Fase", options=fases_disponibles)

            df_mostrar = df_cat.copy()
            if solo_dis:
                df_mostrar = df_mostrar[df_mostrar["estatus"] == "Disponible"]
            if filtro_fase:
                df_mostrar = df_mostrar[df_mostrar["fase"].isin(filtro_fase)]

            # Lógica de colores: Solo verde para disponibles
            def estilo_estatus(val):
                if val == 'Disponible':
                    return 'background-color: #09AB3B; color: white; font-weight: bold'
                return 'color: #808495'

            # Definimos el orden de las columnas: Ubicacion -> Fase -> Precio -> Estatus
            cols = ["ubicacion", "fase", "precio", "estatus"]
            
            # Aseguramos que existan las columnas para evitar errores de visualización
            for c in cols:
                if c not in df_mostrar.columns: df_mostrar[c] = 0

            st.dataframe(
                df_mostrar[cols].style.applymap(estilo_estatus, subset=['estatus']),
                hide_index=True,
                use_container_width=True,
                column_config={
                    "ubicacion": "Lote",
                    "fase": st.column_config.NumberColumn("Fase", format="%d"),
                    "precio": st.column_config.NumberColumn("Precio de Lista", format="$ %.2f"),
                    "estatus": "Estado"
                }
            )
            
            # Métricas
            c_m1, c_m2 = st.columns(2)
            c_m1.metric("Lotes Disponibles", len(df_cat[df_cat["estatus"] == "Disponible"]))
            c_m2.metric("Valor Total Disponible", fmt_moneda(df_cat[df_cat["estatus"] == "Disponible"]["precio"].sum()))
        else:
            st.info("No hay ubicaciones registradas.")

    # --- PESTAÑA 2: GESTIÓN Y ALTAS ---
    with tab_cat2:
        st.subheader("Control de Inventario")
        
        with st.expander("➕ Dar de alta nuevo Lote"):
            with st.form("nuevo_lote"):
                col_n1, col_n2 = st.columns(2)
                with col_n1:
                    n_ubi = st.text_input("Identificador del Lote (ej: L-01)")
                    n_fase = st.number_input("Fase", min_value=1, step=1, value=1)
                with col_n2:
                    n_pre = st.number_input("Precio ($)", min_value=0.0, step=1000.0)
                    n_est = st.selectbox("Estatus Inicial", ["Disponible", "Vendido", "Apartado"])
                
                if st.form_submit_button("Guardar en Inventario"):
                    if n_ubi and n_pre > 0:
                        nuevo_id = int(df_cat["id_ubi"].max()) + 1 if (not df_cat.empty and "id_ubi" in df_cat.columns) else 1
                        nuevo_reg = pd.DataFrame([{
                            "id_ubi": nuevo_id,
                            "ubicacion": n_ubi,
                            "fase": n_fase,
                            "precio": n_pre,
                            "estatus": n_est
                        }])
                        conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=pd.concat([df_cat, nuevo_reg], ignore_index=True))
                        st.success(f"Lote {n_ubi} (Fase {n_fase}) agregado."); st.cache_data.clear(); st.rerun()

        st.divider()
        
        if not df_cat.empty:
            st.write("🔧 **Edición Rápida del Catálogo**")
            # En el editor permitimos editar la fase también
            edited_cat = st.data_editor(
                df_cat,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id_ubi": None,
                    "fase": st.column_config.NumberColumn(step=1),
                    "precio": st.column_config.NumberColumn(format="$ %.2f"),
                    "estatus": st.column_config.SelectboxColumn(options=["Disponible", "Vendido", "Apartado"])
                }
            )
            
            if st.button("💾 Guardar Cambios"):
                conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=edited_cat)
                st.success("Catálogo actualizado."); st.cache_data.clear(); st.rerun()

# --- MÓDULO: DIRECTORIO (GESTIÓN CON ID) ---
elif menu == "📇 Directorio":
    tipo = st.radio("Seleccione Directorio", ["Clientes", "Vendedores"], horizontal=True)
    pestana = "clientes" if tipo == "Clientes" else "vendedores"
    col_id = "id_cliente" if tipo == "Clientes" else "id_vendedor"
    
    df_dir = cargar_datos(pestana)
    
    if df_dir.empty:
        st.warning(f"No hay {tipo.lower()} registrados.")
        with st.expander(f"➕ Registrar primer {tipo[:-1]}"):
            with st.form("form_nuevo_vacio"):
                n_nom = st.text_input("Nombre Completo")
                n_tel = st.text_input("Teléfono")
                n_cor = st.text_input("Correo")
                if st.form_submit_button("Guardar"):
                    nuevo_reg = pd.DataFrame([{col_id: 1, "nombre": n_nom, "telefono": n_tel, "correo": n_cor}])
                    conn.update(spreadsheet=URL_SHEET, worksheet=pestana, data=nuevo_reg)
                    st.success("Registrado."); st.cache_data.clear(); st.rerun()
    else:
        st.subheader(f"Gestionar {tipo}")
        
        # --- BUSCADOR CON ID ---
        # Creamos una lista que muestre "ID - Nombre" para facilitar la búsqueda
        df_dir['display_name'] = df_dir[col_id].astype(str) + " | " + df_dir['nombre']
        opciones_lista = ["-- Seleccionar para editar o agregar nuevo --"] + sorted(df_dir["display_name"].tolist())
        seleccion = st.selectbox(f"Buscar {tipo[:-1]} (ID | Nombre)", options=opciones_lista)
        
        if seleccion != "-- Seleccionar para editar o agregar nuevo --":
            datos_actuales = df_dir[df_dir["display_name"] == seleccion].iloc[0]
            label_boton = "Actualizar Información"
            msg_exito = "Datos actualizados."
            id_actual = datos_actuales[col_id]
        else:
            datos_actuales = {"nombre": "", "telefono": "", "correo": ""}
            label_boton = "Registrar como Nuevo"
            msg_exito = "Nuevo contacto registrado."
            id_actual = "Auto-generado"

        with st.form("form_edicion"):
            c_id, c_nom = st.columns([1, 3])
            c_id.text_input("ID", value=str(id_actual), disabled=True) # El ID no se debe editar manualmente
            
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                edit_nom = st.text_input("Nombre Completo", value=datos_actuales["nombre"])
                edit_tel = st.text_input("Teléfono", value=datos_actuales["telefono"])
            with col_e2:
                edit_cor = st.text_input("Correo Electrónico", value=datos_actuales["correo"])
                st.write("---")
                enviar = st.form_submit_button(label_boton, type="primary")

            if enviar:
                if not edit_nom:
                    st.error("El nombre es obligatorio.")
                else:
                    if seleccion != "-- Seleccionar para editar o agregar nuevo --":
                        # Actualizar usando el ID como referencia única
                        df_dir.loc[df_dir[col_id] == id_actual, ["nombre", "telefono", "correo"]] = [edit_nom, edit_tel, edit_cor]
                    else:
                        # Nuevo registro con ID incremental
                        nuevo_id = int(df_dir[col_id].max()) + 1
                        nuevo_reg = pd.DataFrame([{col_id: nuevo_id, "nombre": edit_nom, "telefono": edit_tel, "correo": edit_cor}])
                        df_dir = pd.concat([df_dir, nuevo_reg], ignore_index=True)
                    
                    # Limpiamos la columna auxiliar antes de guardar en Excel
                    if 'display_name' in df_dir.columns: df_dir = df_dir.drop(columns=['display_name'])
                    
                    conn.update(spreadsheet=URL_SHEET, worksheet=pestana, data=df_dir)
                    st.success(msg_exito); st.cache_data.clear(); st.rerun()

        st.divider()
        st.write(f"### Lista Completa de {tipo}")
        # Mostramos la tabla incluyendo el ID al principio
        columnas_vista = [col_id, "nombre", "telefono", "correo"]
        st.dataframe(df_dir[columnas_vista], use_container_width=True, hide_index=True)


