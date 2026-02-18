import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Inmobiliaria Pro", layout="wide")

# 2. CONEXIÓN A GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)
# Reemplaza esta URL por la de tu Google Sheets si es distinta
URL_SHEET = "https://docs.google.com/spreadsheets/d/1d_G8VafPZp5jj3c1Io9kN3mG31GE70kK2Q2blxWzCCs/edit#gid=0"

# --- FUNCIÓN PARA FORMATO DE MONEDA ($) ---
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

# ==========================================
# 🛠️ BARRA LATERAL: NAVEGACIÓN Y ESTADO
# ==========================================
with st.sidebar:
    st.title("🏢 Panel de Gestión")
    
    # --- MENÚ DE NAVEGACIÓN ---
    menu = st.radio(
        "Seleccione un módulo:",
        ["🏠 Inicio", "📝 Ventas", "📊 Detalle de Crédito", "💰 Cobranza", "💸 Gastos", "📍 Ubicaciones", "👥 Clientes"]
    )
    
    st.divider()

    # --- BOTÓN DE ACTUALIZACIÓN ---
    st.subheader("🔄 Base de Datos")
    if st.button("Actualizar Información"):
        st.cache_data.clear()
        st.success("¡Datos actualizados!")
        st.rerun()

    # --- INDICADOR DE CONEXIÓN ---
    # Esto verifica si la URL está configurada
    if URL_SHEET != "TU_URL_AQUI":
        st.sidebar.markdown("---")
        st.sidebar.write("### 🌐 Estado del Sistema")
        st.sidebar.success("✅ Conectado a la Nube")
        
        # Mostrar hora de última sincronización
        ahora = datetime.now().strftime("%H:%M:%S")
        st.sidebar.info(f"Última sincronización:\n{ahora}")
    else:
        st.sidebar.error("❌ Desconectado (Falta URL)")

# ==========================================
# 🏠 MÓDULO: INICIO
# ==========================================
if menu == "🏠 Inicio":
    # FILA SUPERIOR: Título y Fecha
    col_tit, col_fec = st.columns([3, 1])
    with col_tit:
        st.title("🏠 Tablero de Control")
    with col_fec:
        fecha_hoy = datetime.now().strftime('%d / %m / %Y')
        st.markdown(f"<p style='text-align: right; color: gray; padding-top: 25px;'><b>Fecha Actual:</b><br>{fecha_hoy}</p>", unsafe_allow_html=True)

    # Carga de datos
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")
    df_g = cargar_datos("gastos")

    # MÉTRICAS PRINCIPALES
    c1, c2, c3 = st.columns(3)
    ingresos = (df_p["monto"].sum() if not df_p.empty else 0) + (df_v["enganche"].sum() if not df_v.empty else 0)
    egresos = df_g["monto"].sum() if not df_g.empty else 0
    
    c1.metric("Ingresos Totales", fmt_moneda(ingresos))
    c2.metric("Gastos Totales", fmt_moneda(egresos), delta=f"-{fmt_moneda(egresos)}", delta_color="inverse")
    c3.metric("Utilidad Neta", fmt_moneda(ingresos - egresos))

    st.divider()
    
    # MONITOR DE CARTERA DETALLADO
    st.subheader("🚩 Monitor de Cartera")
    if not df_v.empty:
        monitor = []
        hoy = datetime.now()
        
        for _, v in df_v.iterrows():
            # 1. Obtener pagos y fecha del último pago
            pagos_especificos = df_p[df_p['ubicacion'] == v['ubicacion']] if not df_p.empty else pd.DataFrame()
            total_pagado_cliente = pagos_especificos['monto'].sum() if not pagos_especificos.empty else 0
            
            if not pagos_especificos.empty:
                ultima_fecha_pago = pd.to_datetime(pagos_especificos['fecha']).max().strftime('%d/%m/%Y')
            else:
                ultima_fecha_pago = "Sin Pagos"
            
            # 2. Lógica de Atraso y Días
            f_contrato = pd.to_datetime(v['fecha'])
            mensualidad = float(v['mensualidad'])
            
            # Meses que han pasado desde el contrato hasta hoy
            diff = relativedelta(hoy, f_contrato)
            meses_transcurridos = (diff.years * 12) + diff.months
            
            deuda_teorica = meses_transcurridos * mensualidad
            deuda_vencida = deuda_teorica - total_pagado_cliente
            
            if deuda_vencida > 1.0:
                estatus = "🔴 ATRASO"
                # Calculamos cuántas cuotas ha cubierto realmente con su dinero
                cuotas_cubiertas = total_pagado_cliente / mensualidad
                # El atraso real es desde el primer mes que no completó
                fecha_vencimiento_pendiente = f_contrato + relativedelta(months=int(cuotas_cubiertas) + 1)
                dias_atraso = (hoy - fecha_vencimiento_pendiente).days if hoy > fecha_vencimiento_pendiente else 0
            else:
                estatus = "🟢 AL CORRIENTE"
                deuda_vencida = 0.0
                dias_atraso = 0
            
            saldo_restante = float(v['precio_total']) - float(v['enganche']) - total_pagado_cliente
            
            monitor.append({
                "Ubicación": v['ubicacion'], 
                "Cliente": v['cliente'], 
                "Estatus": estatus, 
                "Último Pago": ultima_fecha_pago,
                "Días de Atraso": dias_atraso,
                "Deuda Vencida": deuda_vencida,
                "Saldo Restante": saldo_restante
            })
        
        # MOSTRAR TABLA
        st.dataframe(
            pd.DataFrame(monitor), 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Deuda Vencida": st.column_config.NumberColumn(format="$ %.2f"),
                "Saldo Restante": st.column_config.NumberColumn(format="$ %.2f"),
                "Días de Atraso": st.column_config.NumberColumn(format="%d días")
            }
        )
    else:
        st.info("No hay ventas registradas.")

# ==========================================
# 📝 MÓDULO: VENTAS (Diseño Equilibrado)
# ==========================================
elif menu == "📝 Ventas":
    st.title("📝 Gestión de Ventas")
    
    # Carga de bases de datos
    df_v = cargar_datos("ventas")
    df_u = cargar_datos("ubicaciones")
    df_cl = cargar_datos("clientes")
    df_vd = cargar_datos("vendedores")

    tab_nueva, tab_editar, tab_lista = st.tabs(["✨ Nueva Venta", "✏️ Editor de Ventas", "📋 Historial"])

    # ---------------------------------------------------------
    # PESTAÑA 1: NUEVA VENTA
    # ---------------------------------------------------------
    with tab_nueva:
        st.subheader("Registrar Contrato Nuevo")
        lotes_libres = df_u[df_u["estatus"] == "Disponible"]["ubicacion"].tolist()
        
        if not lotes_libres:
            st.warning("No hay lotes disponibles en el inventario.")
        else:
            f_lote = st.selectbox("📍 Seleccione Lote a Vender", ["--"] + lotes_libres, key="nv_lote")
            
            if f_lote != "--":
                row_u = df_u[df_u["ubicacion"] == f_lote].iloc[0]
                costo_base = float(row_u.get('precio', row_u.get('costo', 0.0)))
                st.info(f"💰 Costo de Lista para {f_lote}: {fmt_moneda(costo_base)}")

                with st.form("form_nueva_venta"):
                    # --- FILA 1: FECHA Y VENDEDOR ---
                    c1, c2 = st.columns(2)
                    f_fec = c1.date_input("📅 Fecha de Contrato", value=datetime.now())
                    
                    vendedores_list = ["-- SELECCIONAR --"] + (df_vd["nombre"].tolist() if not df_vd.empty else [])
                    col_v1, col_v2 = st.columns([2, 1])
                    f_vende_sel = col_v1.selectbox("👔 Vendedor Registrado", vendedores_list)
                    f_vende_nuevo = col_v2.text_input("🆕 Nuevo Vendedor")
                    
                    # --- FILA 2: CLIENTE ---
                    st.write("👤 **Información del Cliente**")
                    clientes_list = ["-- SELECCIONAR --"] + (df_cl["nombre"].tolist() if not df_cl.empty else [])
                    col_c1, col_c2 = st.columns([2, 1])
                    f_cli_sel = col_c1.selectbox("Cliente Registrado", clientes_list)
                    f_cli_nuevo = col_c2.text_input("🆕 Nuevo Cliente")
                    
                    st.markdown("---")

                    # --- FILA 3: FINANZAS (DISEÑO EQUILIBRADO) ---
                    st.write("💰 **Condiciones Financieras**")
                    cf1, cf2 = st.columns(2)
                    f_tot = cf1.number_input("Precio Final de Venta ($)", min_value=0.0, value=costo_base)
                    f_eng = cf2.number_input("Enganche Recibido ($)", min_value=0.0)
                    
                    # El plazo ahora está a la derecha
                    cf1_b, cf2_b = st.columns(2)
                    f_comision = cf1_b.number_input("Monto de Comisión ($)", min_value=0.0, value=0.0)
                    f_pla = cf2_b.number_input("🕒 Plazo en Meses", min_value=1, value=12)
                    
                    st.markdown("---")
                    
                    # --- FILA 4: MÉTRICA Y BOTÓN DE ACTUALIZACIÓN ---
                    m_calc = (f_tot - f_eng) / f_pla if f_pla > 0 else 0
                    
                    col_met, col_btn = st.columns([2, 1])
                    col_met.metric("Mensualidad Resultante", fmt_moneda(m_calc))
                    
                    # Este botón permite refrescar la mensualidad sin validar el cliente
                    if col_btn.form_submit_button("🔄 Actualizar Cálculos"):
                        st.rerun()

                    f_coment = st.text_area("📝 Comentarios de la venta")

                    # --- BOTÓN FINAL DE GUARDADO ---
                    if st.form_submit_button("💾 GUARDAR VENTA", type="primary"):
                        cliente_final = f_cli_nuevo if f_cli_nuevo else f_cli_sel
                        vendedor_final = f_vende_nuevo if f_vende_nuevo else f_vende_sel
                        
                        if cliente_final == "-- SELECCIONAR --" or not cliente_final:
                            st.error("❌ Error: Debe asignar un cliente para poder guardar la venta.")
                        else:
                            # Registro automático si son nuevos
                            if f_cli_nuevo:
                                nid_c = int(df_cl["id_cliente"].max() + 1) if not df_cl.empty else 1
                                df_cl = pd.concat([df_cl, pd.DataFrame([{"id_cliente": nid_c, "nombre": f_cli_nuevo, "telefono": "", "correo": ""}])], ignore_index=True)
                                conn.update(spreadsheet=URL_SHEET, worksheet="clientes", data=df_cl)
                            
                            if f_vende_nuevo:
                                nid_v = int(df_vd["id_vendedor"].max() + 1) if not df_vd.empty else 1
                                df_vd = pd.concat([df_vd, pd.DataFrame([{"id_vendedor": nid_v, "nombre": f_vende_nuevo, "telefono": "", "comision_base": 0}])], ignore_index=True)
                                conn.update(spreadsheet=URL_SHEET, worksheet="vendedores", data=df_vd)

                            # Guardar la Venta
                            nid_vta = int(df_v["id_venta"].max() + 1) if not df_v.empty else 1
                            nueva_v = pd.DataFrame([{
                                "id_venta": nid_vta, "fecha": f_fec.strftime('%Y-%m-%d'), "ubicacion": f_lote,
                                "cliente": cliente_final, "vendedor": vendedor_final, "precio_total": f_tot,
                                "enganche": f_eng, "plazo_meses": f_pla, "mensualidad": m_calc, 
                                "comision": f_comision, "comentarios": f_coment, "estatus_pago": "Activo"
                            }])
                            df_v = pd.concat([df_v, nueva_v], ignore_index=True)
                            
                            # Actualizar lote
                            df_u.loc[df_u["ubicacion"] == f_lote, "estatus"] = "Vendido"
                            
                            conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=df_v)
                            conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_u)
                            
                            st.success("✅ Venta registrada con éxito.")
                            st.cache_data.clear()
                            st.rerun()

    # ---------------------------------------------------------
    # PESTAÑA 2: EDITOR
    # ---------------------------------------------------------
    with tab_editar:
        st.subheader("Modificar Venta Existente")
        if df_v.empty:
            st.info("No hay ventas para editar.")
        else:
            lista_ventas = (df_v["ubicacion"] + " | " + df_v["cliente"]).tolist()
            edit_sel = st.selectbox("Seleccione la venta a corregir", ["--"] + lista_ventas)
            
            if edit_sel != "--":
                id_ubi = edit_sel.split(" | ")[0]
                datos_v = df_v[df_v["ubicacion"] == id_ubi].iloc[0]
                
                with st.form("form_editor_ventas"):
                    st.write(f"✏️ Editando: **{id_ubi}**")
                    ce1, ce2 = st.columns(2)
                    e_fec = ce1.date_input("Fecha", value=pd.to_datetime(datos_v["fecha"]))
                    e_cli = ce1.selectbox("Cliente", df_cl["nombre"].tolist() if not df_cl.empty else [], index=df_cl["nombre"].tolist().index(datos_v["cliente"]) if datos_v["cliente"] in df_cl["nombre"].tolist() else 0)
                    e_vende = ce2.selectbox("Vendedor", df_vd["nombre"].tolist() if not df_vd.empty else [], index=df_vd["nombre"].tolist().index(datos_v["vendedor"]) if datos_v["vendedor"] in df_vd["nombre"].tolist() else 0)
                    
                    e1, e2 = st.columns(2)
                    e_tot = e1.number_input("Precio Final ($)", min_value=0.0, value=float(datos_v["precio_total"]))
                    e_eng = e2.number_input("Enganche ($)", min_value=0.0, value=float(datos_v["enganche"]))
                    
                    e1_b, e2_b = st.columns(2)
                    e_com = e1_b.number_input("Comisión ($)", min_value=0.0, value=float(datos_v.get("comision", 0.0)))
                    e_pla = e2_b.number_input("Plazo (Meses)", min_value=1, value=int(datos_v["plazo_meses"]))
                    
                    e_mensu = (e_tot - e_eng) / e_pla
                    st.metric("Nueva Mensualidad", fmt_moneda(e_mensu))
                    
                    if st.form_submit_button("💾 Guardar Cambios"):
                        idx = df_v[df_v["ubicacion"] == id_ubi].index[0]
                        df_v.at[idx, "fecha"] = e_fec.strftime('%Y-%m-%d')
                        df_v.at[idx, "cliente"] = e_cli
                        df_v.at[idx, "vendedor"] = e_vende
                        df_v.at[idx, "precio_total"] = e_tot
                        df_v.at[idx, "enganche"] = e_eng
                        df_v.at[idx, "plazo_meses"] = e_pla
                        df_v.at[idx, "mensualidad"] = e_mensu
                        df_v.at[idx, "comision"] = e_com
                        
                        conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=df_v)
                        st.success("¡Datos actualizados!"); st.cache_data.clear(); st.rerun()

    # PESTAÑA 3: HISTORIAL
    with tab_lista:
        st.dataframe(df_v, use_container_width=True, hide_index=True)

# ==========================================
# 📊 MÓDULO: DETALLE DE CRÉDITO (Estatus Inteligente)
# ==========================================
elif menu == "📊 Detalle de Crédito":
    st.title("📊 Detalle de Crédito y Estado de Cuenta")
    
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")

    if df_v.empty:
        st.warning("No hay ventas registradas.")
    else:
        opciones_vta = (df_v["ubicacion"] + " | " + df_v["cliente"]).tolist()
        seleccion = st.selectbox("🔍 Seleccione un Contrato:", opciones_vta)
        
        ubi_sel = seleccion.split(" | ")[0]
        v = df_v[df_v["ubicacion"] == ubi_sel].iloc[0]
        
        # --- CÁLCULOS FINANCIEROS ---
        pagos_cliente = df_p[df_p["ubicacion"] == ubi_sel] if not df_p.empty else pd.DataFrame()
        total_pagado_historico = pagos_cliente["monto"].sum() if not pagos_cliente.empty else 0
        
        precio_vta = float(v['precio_total'])
        enganche_vta = float(v['enganche'])
        monto_credito = precio_vta - enganche_vta
        mensualidad_pactada = float(v['mensualidad'])
        fecha_contrato = pd.to_datetime(v['fecha'])
        hoy = datetime.now()

        # Cálculos de cabecera
        meses_transcurridos = (hoy.year - fecha_contrato.year) * 12 + (hoy.month - fecha_contrato.month)
        meses_a_deber = max(0, min(meses_transcurridos, int(v['plazo_meses'])))
        deuda_a_la_fecha = meses_a_deber * mensualidad_pactada
        saldo_vencido = max(0, deuda_a_la_fecha - total_pagado_historico)
        num_atrasos = saldo_vencido / mensualidad_pactada if mensualidad_pactada > 0 else 0

        # --- SECCIÓN: INFORMACIÓN GENERAL ---
        st.markdown("### 📋 Resumen del Crédito")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.write(f"**📍 Ubicación:** {v['ubicacion']}")
            st.write(f"**👤 Cliente:** {v['cliente']}")
        with c2:
            st.metric("Total Pagado", fmt_moneda(total_pagado_historico))
            st.write(f"**💳 Mensualidad:** {fmt_moneda(mensualidad_pactada)}")
        with c3:
            st.metric("Saldo Vencido", fmt_moneda(saldo_vencido), 
                      delta=f"{int(num_atrasos)} meses" if num_atrasos >= 1 else None, 
                      delta_color="inverse")

        st.divider()

        # --- SECCIÓN: TABLA DE AMORTIZACIÓN CON ESTATUS DETALLADO ---
        st.subheader("📅 Plan de Pagos")
        
        amortizacion = []
        bolsa_pagos = total_pagado_historico

        for i in range(1, int(v['plazo_meses']) + 1):
            fecha_vencimiento = fecha_contrato + relativedelta(months=i)
            pago_realizado = 0.0
            
            # Determinar cuánto se abonó a esta mensualidad
            if bolsa_pagos >= mensualidad_pactada:
                pago_realizado = mensualidad_pactada
                bolsa_pagos -= mensualidad_pactada
                estatus = "🟢 PAGADO"
            elif bolsa_pagos > 0:
                pago_realizado = bolsa_pagos
                bolsa_pagos = 0
                estatus = "🟡 PAGO PARCIAL"
            else:
                pago_realizado = 0.0
                # Lógica de fecha para Pendiente vs Vencido
                if fecha_vencimiento.date() <= hoy.date():
                    estatus = "🔴 VENCIDO"
                else:
                    estatus = ""
            
            amortizacion.append({
                "Mes": i,
                "Fecha de Vencimiento": fecha_vencimiento.strftime('%d/%m/%Y'),
                "Concepto": f"Mensualidad {i}",
                "Importe": mensualidad_pactada,
                "Pago Realizado": pago_realizado,
                "Estatus": estatus
            })

        df_tab = pd.DataFrame(amortizacion)
        
        # Mostramos la tabla
        st.dataframe(
            df_tab, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Importe": st.column_config.NumberColumn(format="$ %.2f"),
                "Pago Realizado": st.column_config.NumberColumn(format="$ %.2f"),
                "Estatus": st.column_config.TextColumn()
            }
        )

# ==========================================
# 💰 MÓDULO: COBRANZA (Versión Final Corregida)
# ==========================================
elif menu == "💰 Cobranza":
    st.title("💰 Gestión de Cobranza")
    
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")

    tab_pago, tab_historial = st.tabs(["💵 Registrar Nuevo Pago", "📋 Historial y Edición"])

    # ---------------------------------------------------------
    # PESTAÑA 1: REGISTRAR NUEVO PAGO
    # ---------------------------------------------------------
    with tab_pago:
        if df_v.empty:
            st.warning("No hay ventas registradas.")
        else:
            opciones_vta = (df_v["ubicacion"] + " | " + df_v["cliente"]).tolist()
            seleccion = st.selectbox("🔍 Seleccione Contrato:", ["--"] + opciones_vta, key="sel_cobro")
            
            if seleccion != "--":
                ubi_sel = seleccion.split(" | ")[0]
                v = df_v[df_v["ubicacion"] == ubi_sel].iloc[0]
                
                # Cálculos de deuda sugerida
                p_previos = df_p[df_p["ubicacion"] == ubi_sel]["monto"].sum() if not df_p.empty and "monto" in df_p.columns else 0
                f_con = pd.to_datetime(v['fecha'])
                hoy = datetime.now()
                meses_t = (hoy.year - f_con.year) * 12 + (hoy.month - f_con.month)
                deuda_esp = max(0, min(meses_t, int(v['plazo_meses']))) * float(v['mensualidad'])
                s_vencido = max(0, deuda_esp - p_previos)
                
                monto_sug = s_vencido if s_vencido > 0 else float(v['mensualidad'])
                
                if s_vencido > 0:
                    st.error(f"⚠️ Atraso detectado: {fmt_moneda(s_vencido)}")
                else:
                    st.success(f"✅ Al corriente. Sugerido: {fmt_moneda(monto_sug)}")

                with st.form("form_nuevo_pago_v4"):
                    st.write(f"### Cobro para: {v['ubicacion']}")
                    c1, c2, c3 = st.columns(3)
                    f_fec = c1.date_input("📅 Fecha", value=datetime.now())
                    f_met = c2.selectbox("💳 Método", ["Efectivo", "Transferencia", "Depósito"])
                    f_fol = c3.text_input("🧾 Folio Comprobante")
                    
                    col_m, col_r = st.columns([2, 1])
                    f_mon = col_m.number_input("💵 Importe Recibido ($)", min_value=0.0, value=monto_sug)
                    if col_r.form_submit_button("🔄 Recalcular"): 
                        st.rerun()
                    
                    f_com = st.text_area("📝 Notas")
                    
                    if st.form_submit_button("✅ REGISTRAR PAGO", type="primary"):
                        if f_mon <= 0:
                            st.error("El monto debe ser mayor a $ 0")
                        else:
                            # Generación de ID segura
                            nuevo_id = 1
                            if not df_p.empty and "id_pago" in df_p.columns:
                                try:
                                    nuevo_id = int(float(df_p["id_pago"].max())) + 1
                                except:
                                    nuevo_id = len(df_p) + 1
                            
                            nuevo_reg = pd.DataFrame([{
                                "id_pago": nuevo_id,
                                "fecha": f_fec.strftime('%Y-%m-%d'),
                                "ubicacion": ubi_sel,
                                "cliente": v['cliente'],
                                "monto": f_mon,
                                "metodo": f_met,
                                "folio": f_fol,
                                "comentarios": f_com
                            }])
                            
                            df_p = pd.concat([df_p, nuevo_reg], ignore_index=True)
                            conn.update(spreadsheet=URL_SHEET, worksheet="pagos", data=df_p)
                            st.success(f"✅ Pago registrado con Folio: {f_fol}")
                            st.cache_data.clear()
                            st.rerun()

    # ---------------------------------------------------------
    # PESTAÑA 2: HISTORIAL Y EDICIÓN (Corregida)
    # ---------------------------------------------------------
    with tab_historial:
        st.subheader("Historial y Correcciones")
        if df_p.empty:
            st.info("No hay pagos registrados.")
        else:
            # Mostramos la tabla primero para referencia
            st.dataframe(df_p, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            # Selector de edición con corrección de ValueError
            opciones_edit = []
            for _, fila in df_p.iterrows():
                # Usamos float y luego int para evitar el error de la captura
                id_limpio = int(float(fila['id_pago']))
                opciones_edit.append(f"{id_limpio} | {fila['fecha']} | {fila['ubicacion']} | {fmt_moneda(fila['monto'])}")
            
            pago_sel = st.selectbox("✏️ Seleccione un pago para modificar/eliminar:", ["--"] + opciones_edit[::-1])
            
            if pago_sel != "--":
                # CORRECCIÓN CLAVE: Convertir a float antes que a int
                id_p_sel = int(float(pago_sel.split(" | ")[0]))
                
                # Buscar el registro
                idx_pago = df_p[df_p["id_pago"].astype(float).astype(int) == id_p_sel].index[0]
                datos_p = df_p.loc[idx_pago]

                with st.expander("🛠️ Panel de Edición", expanded=True):
                    with st.form("form_edit_final"):
                        st.warning(f"Modificando Pago ID: {id_p_sel}")
                        ec1, ec2, ec3 = st.columns(3)
                        e_fec = ec1.date_input("Fecha", value=pd.to_datetime(datos_p["fecha"]))
                        e_met = ec2.selectbox("Método", ["Efectivo", "Transferencia", "Depósito"], 
                                             index=["Efectivo", "Transferencia", "Depósito"].index(datos_p["metodo"]) if datos_p["metodo"] in ["Efectivo", "Transferencia", "Depósito"] else 0)
                        e_fol = ec3.text_input("Folio", value=str(datos_p.get("folio", "")))
                        
                        e_mon = st.number_input("Monto ($)", min_value=0.0, value=float(datos_p["monto"]))
                        e_com = st.text_area("Comentarios", value=str(datos_p.get("comentarios", "")))
                        
                        btn_c1, btn_c2 = st.columns(2)
                        if btn_c1.form_submit_button("💾 ACTUALIZAR"):
                            df_p.at[idx_pago, "fecha"] = e_fec.strftime('%Y-%m-%d')
                            df_p.at[idx_pago, "metodo"] = e_met
                            df_p.at[idx_pago, "folio"] = e_fol
                            df_p.at[idx_pago, "monto"] = e_mon
                            df_p.at[idx_pago, "comentarios"] = e_com
                            conn.update(spreadsheet=URL_SHEET, worksheet="pagos", data=df_p)
                            st.success("¡Cambios guardados!"); st.cache_data.clear(); st.rerun()
                            
                        if btn_c2.form_submit_button("🗑️ ELIMINAR"):
                            df_p = df_p.drop(idx_pago)
                            conn.update(spreadsheet=URL_SHEET, worksheet="pagos", data=df_p)
                            st.error("Pago borrado."); st.cache_data.clear(); st.rerun()

# ==========================================
# 💸 MÓDULO: GASTOS
# ==========================================
elif menu == "💸 Gastos":
    st.title("💸 Gastos")
    df_g = cargar_datos("gastos")
    with st.form("gas"):
        con = st.text_input("Concepto")
        mon = st.number_input("Monto ($)", min_value=0.0)
        if st.form_submit_button("Guardar"):
            id_g = int(df_g["id_gasto"].max() + 1) if not df_g.empty else 1
            nuevo = pd.DataFrame([{"id_gasto": id_g, "fecha": datetime.now().strftime('%Y-%m-%d'), "concepto": con, "monto": mon}])
            conn.update(spreadsheet=URL_SHEET, worksheet="gastos", data=pd.concat([df_g, nuevo]))
            st.success("Gasto guardado"); st.cache_data.clear(); st.rerun()

# ==========================================
# 📍 MÓDULO: UBICACIONES
# ==========================================
elif menu == "📍 Ubicaciones":
    st.title("📍 Ubicaciones")
    df_u = cargar_datos("ubicaciones")
    edit = st.data_editor(df_u, use_container_width=True, hide_index=True)
    if st.button("Guardar Cambios"):
        conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=edit)
        st.success("Actualizado"); st.cache_data.clear(); st.rerun()

# ==========================================
# 👥 MÓDULO: CLIENTES
# ==========================================
elif menu == "👥 Clientes":
    st.title("👥 Clientes")
    df_cl = cargar_datos("clientes")
    with st.form("cli"):
        n = st.text_input("Nombre")
        t = st.text_input("Teléfono")
        if st.form_submit_button("Agregar"):
            id_c = int(df_cl["id_cliente"].max() + 1) if not df_cl.empty else 1
            nuevo = pd.DataFrame([{"id_cliente": id_c, "nombre": n, "telefono": t}])
            conn.update(spreadsheet=URL_SHEET, worksheet="clientes", data=pd.concat([df_cl, nuevo]))
            st.success("Cliente agregado"); st.cache_data.clear(); st.rerun()
    st.dataframe(df_cl, use_container_width=True, hide_index=True)




















