import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- IMPORTACION DE MODULOS ---
from modulos.cobranza import render_cobranza
from modulos.gastos import render_gastos
from modulos.ubicaciones import render_ubicaciones
from modulos.clientes import render_clientes


# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Inmobiliaria Pro", layout="wide")

# 2. CONEXIÓN A GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)

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
# 🛠️ BARRA LATERAL
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
# 📝 MÓDULO: VENTAS
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
# 📊 MÓDULO: DETALLE DE CRÉDITO
# ==========================================
elif menu == "📊 Detalle de Crédito":
    st.title("📊 Detalle de Crédito y Estado de Cuenta")
    
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")

    if df_v.empty:
        st.warning("No hay ventas registradas.")
    else:
        # 1. SELECTOR DE CONTRATO
        opciones_vta = (df_v["ubicacion"] + " | " + df_v["cliente"]).tolist()
        seleccion = st.selectbox("🔍 Seleccione un Contrato:", opciones_vta)
        
        ubi_sel = seleccion.split(" | ")[0]
        v = df_v[df_v["ubicacion"] == ubi_sel].iloc[0]
        
        # --- CÁLCULOS FINANCIEROS ACTUALIZADOS ---
        # 1. Montos base del contrato
        precio_total_vta = float(v['precio_total'])
        enganche_vta = float(v['enganche'])
        monto_a_financiar = precio_total_vta - enganche_vta
        
        # 2. Suma de abonos mensuales
        abonos_mensuales = df_p[df_p["ubicacion"] == ubi_sel]["monto"].sum() if not df_p.empty else 0
        
        # 3. TOTAL PAGADO (Enganche + Abonos)
        total_pagado_acumulado = enganche_vta + abonos_mensuales
        
        # 4. Cálculo de avance (Sobre el costo total)
        porcentaje_total = (total_pagado_acumulado / precio_total_vta) if precio_total_vta > 0 else 0
        porcentaje_total = min(1.0, porcentaje_total)

        # 5. Cálculos de morosidad (Estos se basan solo en las mensualidades vencidas)
        mensualidad_pactada = float(v['mensualidad'])
        fecha_contrato = pd.to_datetime(v['fecha'])
        hoy = datetime.now()
        
        meses_transcurridos = (hoy.year - fecha_contrato.year) * 12 + (hoy.month - fecha_contrato.month)
        meses_a_deber = max(0, min(meses_transcurridos, int(v['plazo_meses'])))
        deuda_esperada_a_hoy = meses_a_deber * mensualidad_pactada
        
        # El saldo vencido solo considera si los ABONOS cubren las MENSUALIDADES programadas
        saldo_vencido = max(0, deuda_esperada_a_hoy - abonos_mensuales)
        num_atrasos = saldo_vencido / mensualidad_pactada if mensualidad_pactada > 0 else 0

        # --- SECCIÓN: INFORMACIÓN GENERAL ---
        st.markdown("### 📋 Resumen del Crédito")
        
        # Barra de progreso considerando el Enganche
        st.write(f"**Avance Total de Pago (incluye enganche): {int(porcentaje_total * 100)}%**")
        st.progress(porcentaje_total)
        st.write("") 

        c1, c2, c3 = st.columns(3)
        with c1:
            st.write(f"**📍 Ubicación:** {v['ubicacion']}")
            st.write(f"**👤 Cliente:** {v['cliente']}")
            st.write(f"**📅 Fecha Contrato:** {v['fecha']}")
        with c2:
            st.metric("Total Pagado", fmt_moneda(total_pagado_acumulado))
            st.write(f"**💰 Costo Total:** {fmt_moneda(precio_total_vta)}")
            st.write(f"**📥 Enganche Pagado:** {fmt_moneda(enganche_vta)}")
        with c3:
            st.metric("Saldo Vencido", fmt_moneda(saldo_vencido), 
                      delta=f"{int(num_atrasos)} meses" if num_atrasos >= 1 else "Al día", 
                      delta_color="inverse")
            st.write(f"**💳 Mensualidad:** {fmt_moneda(mensualidad_pactada)}")
            st.write(f"**📉 Saldo Restante:** {fmt_moneda(max(0, precio_total_vta - total_pagado_acumulado))}")

        st.divider()

        # --- SECCIÓN: TABLA DE AMORTIZACIÓN ---
        st.subheader("📅 Plan de Pagos Mensuales")
        
        amortizacion = []
        bolsa_pagos = abonos_mensuales # Los abonos mensuales cubren la tabla

        for i in range(1, int(v['plazo_meses']) + 1):
            fecha_vencimiento = fecha_contrato + relativedelta(months=i)
            pago_realizado = 0.0
            
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
                if fecha_vencimiento.date() <= hoy.date():
                    estatus = "🔴 VENCIDO"
                else:
                    estatus = "PENDIENTE"
            
            amortizacion.append({
                "Mes": i,
                "Fecha de Vencimiento": fecha_vencimiento.strftime('%d/%m/%Y'),
                "Concepto": f"Mensualidad {i}",
                "Importe": mensualidad_pactada,
                "Pago Realizado": pago_realizado,
                "Estatus": estatus
            })

        df_tab = pd.DataFrame(amortizacion)
        st.dataframe(df_tab, use_container_width=True, hide_index=True)

if menu == "💰 Cobranza":
    df_ventas = cargar_datos("ventas")
    df_pagos = cargar_datos("pagos")
    render_cobranza(df_ventas, df_pagos, conn, URL_SHEET, fmt_moneda, cargar_datos)

if menu == "💸 Gastos":
    df_gastos = cargar_datos("gastos")
    render_gastos(df_gastos, conn, URL_SHEET, fmt_moneda, cargar_datos)

if menu == "📍 Ubicaciones":
    df_ubicaciones = cargar_datos("ubicaciones")
    render_ubicaciones(df_ubicaciones, conn, URL_SHEET, cargar_datos)

elif menu == "👥 Clientes":
    df_clientes = cargar_datos("clientes")
    render_clientes(df_clientes, conn, URL_SHEET, cargar_datos)


