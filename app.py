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
    ["🏠 Inicio", "📝 Ventas", "📊 Detalle de Crédito", "💰 Cobranza", "💸 Gastos", "💸 Comisiones", "📑 Catálogo", "📇 Directorio"]
)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Actualizar Base de Datos"):
    st.cache_data.clear()
    st.rerun()

st.title(f"Sistema Inmobiliario - Resumen")

# --- MÓDULO: INICIO (DASHBOARD ESTRATÉGICO) ---
if menu == "🏠 Inicio":
    # 1. CARGA DE DATOS
    df_v = cargar_datos("ventas")
    df_u = cargar_datos("ubicaciones")
    df_p = cargar_datos("pagos")
    
    # 2. PROCESAMIENTO Y CÁLCULOS BASE
    if "estatus_pago" not in df_v.columns: 
        df_v["estatus_pago"] = "Activo"
    
    total_ventas = df_v["precio_total"].sum() if not df_v.empty else 0
    total_recaudado = df_p["monto"].sum() if not df_p.empty else 0
    total_enganches = df_v["enganche"].sum() if not df_v.empty else 0
    flujo_total = total_recaudado + total_enganches
    
    contratos_activos = len(df_v[df_v["estatus_pago"].fillna("Activo") == "Activo"]) if not df_v.empty else 0
    
    # --- FILA 1: MÉTRICAS FINANCIERAS ---
    st.subheader("💰 Resumen Financiero")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ventas Totales (Contratado)", fmt_moneda(total_ventas))
    c2.metric("Flujo Total Entrante", fmt_moneda(flujo_total), help="Suma de Enganches + Abonos registrados")
    c3.metric("Por Cobrar (Cartera)", fmt_moneda(total_ventas - flujo_total))
    c4.metric("Contratos Activos", contratos_activos)
    
    # --- FILA 2: INVENTARIO Y COBRANZA (SIN DIVIDER INTERMEDIO) ---
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
            # Suma de mensualidades de contratos activos
            mensualidad_esperada = df_v[df_v["estatus_pago"] == "Activo"]["mensualidad"].sum()
            st.write("**Meta de Recaudación Mensual (Activos):**")
            st.info(f"### {fmt_moneda(mensualidad_esperada)}")
        else:
            st.info("Sin contratos activos.")

    st.divider()

    # --- FILA 3: MONITOR DE CARTERA (SITUACIÓN DE CLIENTES) ---
    st.subheader("🚩 Monitor de Cartera y Cobranza")
    
    if not df_v.empty:
        monitor_data = []
        hoy = datetime.now()

        for _, venta in df_v.iterrows():
            # Cálculo de pagos realizados para esta ubicación
            pagos_cliente = df_p[df_p['ubicacion'] == venta['ubicacion']]['monto'].sum() if not df_p.empty else 0.0
            saldo_liquidar = float(venta['precio_total']) - float(venta['enganche']) - pagos_cliente
            
            # Lógica de atraso basada en meses transcurridos
            try:
                fecha_con = datetime.strptime(str(venta['fecha']), '%Y-%m-%d')
            except:
                fecha_con = hoy
            
            meses_transcurridos = (hoy.year - fecha_con.year) * 12 + (hoy.month - fecha_con.month)
            debe_a_la_fecha = meses_transcurridos * float(venta['mensualidad'])
            pago_para_corriente = debe_a_la_fecha - pagos_cliente
            
            if pago_para_corriente > 1.0:
                estatus_c = "🔴 Atrasado"
                # Calculamos días desde el día que debió pagar este mes
                dia_pago = fecha_con.day
                try:
                    fecha_venc_mes = hoy.replace(day=dia_pago)
                    if hoy < fecha_venc_mes:
                        fecha_venc_mes = fecha_venc_mes - relativedelta(months=1)
                except: # Por si el día es 31 y el mes tiene 30
                    fecha_venc_mes = hoy.replace(day=1) - relativedelta(days=1)
                
                dias_atraso = (hoy - fecha_venc_mes).days
            else:
                estatus_c = "🟢 Corriente"
                pago_para_corriente = 0.0
                dias_atraso = 0

            monitor_data.append({
                "Ubicación": venta['ubicacion'],
                "Cliente": venta['cliente'],
                "Fecha Contrato": venta['fecha'],
                "Costo": float(venta['precio_total']),
                "Enganche": float(venta['enganche']),
                "Total Pagado": pagos_cliente,
                "Estatus": estatus_c,
                "Días Atraso": dias_atraso,
                "Para estar al corriente": pago_para_corriente,
                "Saldo Liquidar": saldo_liquidar
            })

        df_monitor = pd.DataFrame(monitor_data)
        
        # Mostrar tabla interactiva con formatos de moneda
        st.dataframe(
            df_monitor,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Costo": st.column_config.NumberColumn(format="$ %.2f"),
                "Enganche": st.column_config.NumberColumn(format="$ %.2f"),
                "Total Pagado": st.column_config.NumberColumn(format="$ %.2f"),
                "Para estar al corriente": st.column_config.NumberColumn(format="$ %.2f"),
                "Saldo Liquidar": st.column_config.NumberColumn(format="$ %.2f")
            }
        )
    else:
        st.info("No hay ventas registradas para el monitor.")

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

# --- MÓDULO: DIRECTORIO (EDITOR DE CONTACTOS) ---
elif menu == "📇 Directorio":
    tipo = st.radio("Seleccione Directorio", ["Clientes", "Vendedores"], horizontal=True)
    pestana = "clientes" if tipo == "Clientes" else "vendedores"
    col_id = "id_cliente" if tipo == "Clientes" else "id_vendedor"
    
    df_dir = cargar_datos(pestana)
    
    if df_dir.empty:
        st.warning(f"No hay {tipo.lower()} registrados.")
        # Opción para crear el primer registro si está vacío
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
        # --- BUSCADOR Y EDITOR ---
        st.subheader(f"Gestionar {tipo}")
        
        opciones_lista = ["-- Seleccionar para editar o agregar nuevo --"] + sorted(df_dir["nombre"].tolist())
        seleccion = st.selectbox(f"Buscar {tipo[:-1]}", options=opciones_lista)
        
        # Si selecciona a alguien, extraemos sus datos actuales
        if seleccion != "-- Seleccionar para editar o agregar nuevo --":
            datos_actuales = df_dir[df_dir["nombre"] == seleccion].iloc[0]
            label_boton = "Actualizar Información"
            msg_exito = "Datos actualizados correctamente."
        else:
            datos_actuales = {"nombre": "", "telefono": "", "correo": ""}
            label_boton = "Registrar como Nuevo"
            msg_exito = "Nuevo contacto registrado."

        with st.form("form_edicion"):
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
                        # LÓGICA DE ACTUALIZACIÓN: Buscamos por el nombre original
                        df_dir.loc[df_dir["nombre"] == seleccion, ["nombre", "telefono", "correo"]] = [edit_nom, edit_tel, edit_cor]
                    else:
                        # LÓGICA DE NUEVO REGISTRO
                        nuevo_id = int(df_dir[col_id].max()) + 1 if not df_dir.empty else 1
                        nuevo_reg = pd.DataFrame([{col_id: nuevo_id, "nombre": edit_nom, "telefono": edit_tel, "correo": edit_cor}])
                        df_dir = pd.concat([df_dir, nuevo_reg], ignore_index=True)
                    
                    conn.update(spreadsheet=URL_SHEET, worksheet=pestana, data=df_dir)
                    st.success(msg_exito)
                    st.cache_data.clear()
                    st.rerun()

        st.divider()
        st.write(f"### Vista Rápida de {tipo}")
        st.dataframe(df_dir[["nombre", "telefono", "correo"]], use_container_width=True, hide_index=True)

st.sidebar.write("---")
st.sidebar.success("Sistema Sincronizado")









