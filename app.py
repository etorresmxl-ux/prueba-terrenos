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
# 📝 MÓDULO: VENTAS
# ==========================================
elif menu == "📝 Ventas":
    st.title("📝 Gestión de Ventas")
    
    # Carga de bases de datos
    df_v = cargar_datos("ventas")
    df_u = cargar_datos("ubicaciones")
    df_cl = cargar_datos("clientes")
    df_vd = cargar_datos("vendedores")

    # CREACIÓN DE PESTAÑAS
    tab_nueva, tab_editar, tab_lista = st.tabs(["✨ Nueva Venta", "✏️ Editor de Ventas", "📋 Historial"])

    # ---------------------------------------------------------
    # PESTAÑA 1: NUEVA VENTA (Incluye Comisiones)
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
                    c1, c2 = st.columns(2)
                    f_fec = c1.date_input("📅 Fecha de Contrato", value=datetime.now())
                    
                    st.markdown("---")
                    # Sección Cliente y Vendedor
                    col_c1, col_c2 = st.columns([2, 1])
                    f_cli_sel = col_c1.selectbox("👤 Cliente Existente", ["--"] + (df_cl["nombre"].tolist() if not df_cl.empty else []))
                    f_cli_nuevo = col_c2.text_input("🆕 ¿Nuevo Cliente?")
                    
                    col_v1, col_v2 = st.columns([2, 1])
                    f_vende_sel = col_v1.selectbox("👔 Vendedor Existente", ["--"] + (df_vd["nombre"].tolist() if not df_vd.empty else []))
                    f_vende_nuevo = col_v2.text_input("🆕 ¿Nuevo Vendedor?")
                    
                    st.markdown("---")
                    # Sección Financiera
                    f_tot = c1.number_input("💵 Precio Final de Venta ($)", min_value=0.0, value=costo_base)
                    f_eng = c2.number_input("📥 Enganche Recibido ($)", min_value=0.0)
                    f_pla = c1.number_input("🕒 Plazo (Meses)", min_value=1, value=12)
                    
                    # CÁLCULO DE MENSUALIDAD EN VIVO
                    mensu_calc = (f_tot - f_eng) / f_pla if f_pla > 0 else 0
                    c2.metric("Mensualidad Resultante", fmt_moneda(mensu_calc))

                    st.markdown("### 💸 Comisión de Venta")
                    cc1, cc2 = st.columns(2)
                    
                    # Opción de elegir entre % o monto fijo
                    tipo_comision = cc1.radio("Calcular por:", ["Porcentaje %", "Monto Fijo $"], horizontal=True)
                    
                    if tipo_comision == "Porcentaje %":
                        pct_com = cc2.number_input("Porcentaje de comisión (%)", min_value=0.0, max_value=100.0, value=3.0, step=0.5)
                        monto_comision = f_tot * (pct_com / 100)
                        cc2.write(f"**Monto a pagar:** {fmt_moneda(monto_comision)}")
                    else:
                        monto_comision = cc2.number_input("Monto de comisión cerrado ($)", min_value=0.0, value=0.0)
                    
                    st.markdown("---")
                    f_coment = st.text_area("📝 Comentarios / Notas de la venta")

                    if st.form_submit_button("🚀 Finalizar y Registrar Venta"):
                        cliente_final = f_cli_nuevo if f_cli_nuevo else f_cli_sel
                        vendedor_final = f_vende_nuevo if f_vende_nuevo else f_vende_sel
                        
                        if cliente_final == "--" or not cliente_final:
                            st.error("❌ Por favor, asigne un cliente a la venta.")
                        else:
                            # 1. Registro automático de Cliente/Vendedor
                            if f_cli_nuevo:
                                nid_c = int(df_cl["id_cliente"].max() + 1) if not df_cl.empty else 1
                                df_cl = pd.concat([df_cl, pd.DataFrame([{"id_cliente": nid_c, "nombre": f_cli_nuevo, "telefono": "", "correo": ""}])], ignore_index=True)
                                conn.update(spreadsheet=URL_SHEET, worksheet="clientes", data=df_cl)
                            
                            if f_vende_nuevo:
                                nid_v = int(df_vd["id_vendedor"].max() + 1) if not df_vd.empty else 1
                                df_vd = pd.concat([df_vd, pd.DataFrame([{"id_vendedor": nid_v, "nombre": f_vende_nuevo, "telefono": "", "comision_base": 0}])], ignore_index=True)
                                conn.update(spreadsheet=URL_SHEET, worksheet="vendedores", data=df_vd)

                            # 2. Guardar la Venta (Incluyendo la nueva columna de comisión)
                            nid_vta = int(df_v["id_venta"].max() + 1) if not df_v.empty else 1
                            nueva_v = pd.DataFrame([{
                                "id_venta": nid_vta, 
                                "fecha": f_fec.strftime('%Y-%m-%d'), 
                                "ubicacion": f_lote,
                                "cliente": cliente_final, 
                                "vendedor": vendedor_final, 
                                "precio_total": f_tot,
                                "enganche": f_eng, 
                                "plazo_meses": f_pla, 
                                "mensualidad": mensu_calc, 
                                "comision": monto_comision, # <--- NUEVA COLUMNA
                                "comentarios": f_coment, 
                                "estatus_pago": "Activo"
                            }])
                            df_v = pd.concat([df_v, nueva_v], ignore_index=True)
                            
                            # 3. Marcar lote como vendido
                            df_u.loc[df_u["ubicacion"] == f_lote, "estatus"] = "Vendido"
                            
                            conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=df_v)
                            conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_u)
                            
                            st.success(f"✅ Venta registrada. Comisión de {fmt_moneda(monto_comision)} asignada.")
                            st.cache_data.clear()
                            st.rerun()

    # ---------------------------------------------------------
    # PESTAÑA 2: EDITOR (Para corregir montos o comisiones)
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
                    c1, c2 = st.columns(2)
                    e_fec = c1.date_input("Fecha", value=pd.to_datetime(datos_v["fecha"]))
                    e_cli = c1.selectbox("Cliente", df_cl["nombre"].tolist() if not df_cl.empty else [], index=df_cl["nombre"].tolist().index(datos_v["cliente"]) if datos_v["cliente"] in df_cl["nombre"].tolist() else 0)
                    e_vende = c2.selectbox("Vendedor", df_vd["nombre"].tolist() if not df_vd.empty else [], index=df_vd["nombre"].tolist().index(datos_v["vendedor"]) if datos_v["vendedor"] in df_vd["nombre"].tolist() else 0)
                    
                    e_tot = c1.number_input("Precio Final ($)", min_value=0.0, value=float(datos_v["precio_total"]))
                    e_eng = c2.number_input("Enganche ($)", min_value=0.0, value=float(datos_v["enganche"]))
                    e_pla = c1.number_input("Plazo (Meses)", min_value=1, value=int(datos_v["plazo_meses"]))
                    
                    # Comisión en el editor
                    e_com = c2.number_input("Comisión Registrada ($)", min_value=0.0, value=float(datos_v.get("comision", 0.0)))
                    
                    e_mensu = (e_tot - e_eng) / e_pla
                    c2.metric("Nueva Mensualidad", fmt_moneda(e_mensu))
                    
                    e_coment = st.text_area("Comentarios", value=datos_v.get("comentarios", ""))

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
                        df_v.at[idx, "comentarios"] = e_coment
                        
                        conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=df_v)
                        st.success("¡Venta y comisión actualizadas!"); st.cache_data.clear(); st.rerun()

    with tab_lista:
        st.dataframe(df_v, use_container_width=True, hide_index=True)

# ==========================================
# 📊 MÓDULO: DETALLE DE CRÉDITO
# ==========================================
elif menu == "📊 Detalle de Crédito":
    st.title("📊 Detalle de Crédito")
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")
    if not df_v.empty:
        sel = st.selectbox("Lote", df_v["ubicacion"].unique())
        v = df_v[df_v["ubicacion"] == sel].iloc[0]
        pagado = df_p[df_p["ubicacion"] == sel]["monto"].sum() if not df_p.empty else 0
        st.metric("Saldo Pendiente", fmt_moneda(float(v['precio_total']) - float(v['enganche']) - pagado))
        st.write("### Historial")
        st.dataframe(df_p[df_p["ubicacion"] == sel], use_container_width=True)

# ==========================================
# 💰 MÓDULO: COBRANZA
# ==========================================
elif menu == "💰 Cobranza":
    st.title("💰 Cobranza")
    df_p = cargar_datos("pagos")
    df_v = cargar_datos("ventas")
    with st.form("cobro"):
        u = st.selectbox("Lote", df_v["ubicacion"].tolist())
        m = st.number_input("Monto ($)", min_value=0.0)
        f = st.date_input("Fecha")
        if st.form_submit_button("Registrar"):
            id_p = int(df_p["id_pago"].max() + 1) if not df_p.empty else 1
            nuevo = pd.DataFrame([{"id_pago": id_p, "fecha": f.strftime('%Y-%m-%d'), "ubicacion": u, "monto": m}])
            conn.update(spreadsheet=URL_SHEET, worksheet="pagos", data=pd.concat([df_p, nuevo]))
            st.success("Cobro guardado"); st.cache_data.clear(); st.rerun()

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








