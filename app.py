import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sistema Inmobiliario Pro", layout="wide")

# --- CONEXIÓN Y CARGA DE DATOS ---
URL_SHEET = "TU_URL_DE_GOOGLE_SHEETS_AQUÍ" # Reemplaza con tu URL real
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos(worksheet_name):
    try:
        return conn.read(spreadsheet=URL_SHEET, worksheet=worksheet_name)
    except:
        return pd.DataFrame()

def fmt_moneda(valor):
    return f"$ {valor:,.2f}"

# --- MENÚ LATERAL ---
with st.sidebar:
    st.title("🏢 Panel de Gestión")
    menu = st.radio("Menú Principal", [
        "🏠 Inicio", 
        "📝 Ventas", 
        "📊 Detalle de Crédito", 
        "💰 Cobranza", 
        "💸 Gastos", 
        "📍 Ubicaciones", 
        "👥 Clientes"
    ])
    st.info("Versión 2.0 | 2026")

# ==========================================
# 🏠 MÓDULO: INICIO
# ==========================================
if menu == "🏠 Inicio":
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")
    df_g = cargar_datos("gastos")
    
    # Métricas Globales
    total_recaudado = df_p["monto"].sum() if not df_p.empty else 0
    total_enganches = df_v["enganche"].sum() if not df_v.empty else 0
    ingresos_totales = total_recaudado + total_enganches
    gastos_totales = df_g["monto"].sum() if not df_g.empty else 0
    
    st.subheader("💰 Resumen Financiero Global")
    c1, c2, c3 = st.columns(3)
    c1.metric("Ingresos Reales", fmt_moneda(ingresos_totales))
    c2.metric("Gastos Totales", fmt_moneda(gastos_totales), delta=f"-{fmt_moneda(gastos_totales)}", delta_color="inverse")
    c3.metric("Utilidad Neta", fmt_moneda(ingresos_totales - gastos_totales))

    st.divider()

    # Monitor de Cartera
    col_h, col_s = st.columns([2, 1])
    col_h.subheader("🚩 Monitor de Cartera")
    solo_atrasos = col_s.toggle("Ocultar clientes Al Corriente", value=True)
    
    if not df_v.empty:
        monitor_data = []
        hoy = datetime.now()

        for _, v in df_v.iterrows():
            pagos_c = df_p[df_p['ubicacion'] == v['ubicacion']]['monto'].sum() if not df_p.empty else 0.0
            try: f_con = datetime.strptime(str(v['fecha']), '%Y-%m-%d')
            except: f_con = hoy
            
            diff = relativedelta(hoy, f_con)
            meses_trans = diff.years * 12 + diff.months
            monto_exigible = meses_trans * float(v['mensualidad'])
            deuda_vencida = monto_exigible - pagos_c
            
            if deuda_vencida > 1.0:
                f_venc = f_con + relativedelta(months=meses_trans)
                dias_m = (hoy - f_venc).days
                est = "🔴 ATRASO"
            else:
                est = "🟢 AL CORRIENTE"
                deuda_vencida, dias_m = 0.0, 0

            monitor_data.append({
                "Ubicación": v['ubicacion'], "Cliente": v['cliente'],
                "Estatus": est, "Días Mora": dias_m,
                "Deuda Vencida": deuda_vencida, "Saldo Restante": float(v['precio_total']) - float(v['enganche']) - pagos_c
            })

        df_mon = pd.DataFrame(monitor_data)
        if solo_atrasos: df_mon = df_mon[df_mon["Estatus"] == "🔴 ATRASO"]

        if df_mon.empty: st.success("🎉 Todo al corriente")
        else:
            st.dataframe(df_mon.style.applymap(lambda x: 'color: #FF4B4B; font-weight: bold' if "🔴" in str(x) else 'color: #09AB3B', subset=['Estatus']),
                         use_container_width=True, hide_index=True,
                         column_config={"Deuda Vencida": st.column_config.NumberColumn(format="$ %.2f"), "Saldo Restante": st.column_config.NumberColumn(format="$ %.2f")})

# ==========================================
# 📝 MÓDULO: VENTAS
# ==========================================
elif menu == "📝 Ventas":
    st.header("Nueva Venta")
    df_v = cargar_datos("ventas")
    df_u = cargar_datos("ubicaciones")
    df_cl = cargar_datos("clientes")

    lotes_disp = df_u[df_u["estatus"] == "Disponible"]["ubicacion"].tolist()
    f_lote = st.selectbox("Seleccione Ubicación", ["--"] + lotes_disp)
    
    precio_sug = 0.0
    if f_lote != "--":
        precio_sug = float(df_u[df_u["ubicacion"] == f_lote].iloc[0]["precio"])
        st.info(f"Precio de lista: {fmt_moneda(precio_sug)}")

    with st.form("f_v"):
        c1, c2 = st.columns(2)
        cli = c1.selectbox("Cliente", df_cl["nombre"] if not df_cl.empty else ["No hay clientes"])
        fec = c2.date_input("Fecha Contrato")
        tot = c1.number_input("Precio Final ($)", value=precio_sug)
        eng = c2.number_input("Enganche ($)")
        pla = st.number_input("Plazo (Meses)", min_value=1, value=12)
        
        if st.form_submit_button("Registrar Contrato"):
            nid = int(pd.to_numeric(df_v["id_venta"], errors='coerce').max() + 1) if not df_v.empty else 1
            nv = pd.DataFrame([{"id_venta": nid, "fecha": fec.strftime('%Y-%m-%d'), "ubicacion": f_lote, "cliente": cli, "precio_total": tot, "enganche": eng, "plazo_meses": pla, "mensualidad": (tot-eng)/pla, "estatus_pago": "Activo"}])
            conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=pd.concat([df_v, nv]))
            df_u.loc[df_u["ubicacion"] == f_lote, "estatus"] = "Vendido"
            conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_u)
            st.cache_data.clear(); st.rerun()

# ==========================================
# 📊 MÓDULO: DETALLE DE CRÉDITO
# ==========================================
elif menu == "📊 Detalle de Crédito":
    st.header("Detalle de Crédito")
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")
    
    if not df_v.empty:
        sel = st.selectbox("Contrato", df_v["ubicacion"] + " | " + df_v["cliente"])
        d = df_v[df_v["ubicacion"] == sel.split(" | ")[0]].iloc[0]
        pagado = df_p[df_p["ubicacion"] == d["ubicacion"]]["monto"].sum() if not df_p.empty else 0
        
        hoy = datetime.now()
        f_c = datetime.strptime(str(d["fecha"]), '%Y-%m-%d')
        m_r = (relativedelta(hoy, f_c).years * 12) + relativedelta(hoy, f_c).months
        m_atraso = (m_r * float(d["mensualidad"])) - pagado
        
        est_t, col_t = ("🔴 ATRASO", "#FF4B4B") if m_atraso > 1 else ("🟢 AL CORRIENTE", "#09AB3B")

        st.markdown(f"<h2 style='color:{col_t}'>{est_t}</h2>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Saldo Restante", fmt_moneda(float(d["precio_total"]) - float(d["enganche"]) - pagado))
        c2.metric("Monto en Atraso", fmt_moneda(max(0, m_atraso)))
        c3.metric("Total Pagado", fmt_moneda(pagado))

# ==========================================
# 💰 MÓDULO: COBRANZA
# ==========================================
elif menu == "💰 Cobranza":
    st.header("Registro de Pagos")
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")
    
    sel_c = st.selectbox("Lote", ["--"] + df_v["ubicacion"].tolist())
    if sel_c != "--":
        with st.form("pago"):
            mon = st.number_input("Monto ($)", min_value=0.0)
            fec = st.date_input("Fecha")
            if st.form_submit_button("Aplicar Pago"):
                np = pd.DataFrame([{"id_pago": len(df_p)+1, "fecha": fec.strftime('%Y-%m-%d'), "ubicacion": sel_c, "monto": mon}])
                conn.update(spreadsheet=URL_SHEET, worksheet="pagos", data=pd.concat([df_p, np]))
                st.cache_data.clear(); st.rerun()

# ==========================================
# 💸 GASTOS
# ==========================================
elif menu == "💸 Gastos":
    st.header("Gastos Operativos")
    df_g = cargar_datos("gastos")
    with st.form("gastos"):
        con = st.text_input("Concepto")
        mon = st.number_input("Monto ($)", min_value=0.0)
        if st.form_submit_button("Guardar Gasto"):
            ng = pd.DataFrame([{"id_gasto": len(df_g)+1, "fecha": datetime.now().strftime('%Y-%m-%d'), "concepto": con, "monto": mon}])
            conn.update(spreadsheet=URL_SHEET, worksheet="gastos", data=pd.concat([df_g, ng]))
            st.cache_data.clear(); st.rerun()

# ==========================================
# 📍 UBICACIONES
# ==========================================
elif menu == "📍 Ubicaciones":
    st.header("Inventario de Ubicaciones")
    df_u = cargar_datos("ubicaciones")
    st.data_editor(df_u, use_container_width=True, hide_index=True)
    if st.button("Guardar Cambios"):
        conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_u)
        st.success("Catálogo actualizado"); st.cache_data.clear()

# ==========================================
# 👥 CLIENTES
# ==========================================
elif menu == "👥 Clientes":
    st.header("Directorio de Clientes")
    df_cl = cargar_datos("clientes")
    if not df_cl.empty:
        st.dataframe(df_cl, use_container_width=True, hide_index=True)
    with st.expander("Nuevo Cliente"):
        with st.form("cli"):
            nom = st.text_input("Nombre")
            tel = st.text_input("Teléfono")
            if st.form_submit_button("Registrar"):
                nc = pd.DataFrame([{"id_cliente": len(df_cl)+1, "nombre": nom, "telefono": tel}])
                conn.update(spreadsheet=URL_SHEET, worksheet="clientes", data=pd.concat([df_cl, nc]))
                st.cache_data.clear(); st.rerun()

import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURACIÓN Y CONEXIÓN (LOS CIMIENTOS) ---
st.set_page_config(page_title="Sistema Inmobiliario", layout="wide")

URL_SHEET = "TU_URL_DE_GOOGLE_SHEETS" 
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos(worksheet_name):
    try:
        return conn.read(spreadsheet=URL_SHEET, worksheet=worksheet_name)
    except:
        return pd.DataFrame()

def fmt_moneda(valor):
    return f"$ {valor:,.2f}"

# --- 2. MENÚ LATERAL (EL ORDEN QUE SOLICITASTE) ---
with st.sidebar:
    st.title("🏢 Panel de Control")
    menu = st.radio("Menú Principal", [
        "🏠 Inicio", 
        "📝 Ventas", 
        "📊 Detalle de Crédito", 
        "💰 Cobranza", 
        "💸 Gastos", 
        "📍 Ubicaciones", 
        "👥 Clientes"
    ])
    st.info("Versión Personalizada 2026")

# --- 3. EJECUCIÓN DE MÓDULOS (ORDENADOS SEGÚN EL MENÚ) ---

# ==========================================
# 🏠 MÓDULO: INICIO
# ==========================================
if menu == "🏠 Inicio":
    df_v = cargar_datos("ventas")
    df_u = cargar_datos("ubicaciones")
    df_p = cargar_datos("pagos")
    df_g = cargar_datos("gastos")
    
    # Métricas Globales
    total_recaudado = df_p["monto"].sum() if not df_p.empty else 0
    total_enganches = df_v["enganche"].sum() if not df_v.empty else 0
    ingresos_totales = total_recaudado + total_enganches
    gastos_totales = df_g["monto"].sum() if not df_g.empty else 0
    
    st.subheader("💰 Resumen Financiero")
    c1, c2, c3 = st.columns(3)
    c1.metric("Ingresos Reales", fmt_moneda(ingresos_totales))
    c2.metric("Gastos", fmt_moneda(gastos_totales), delta=f"-{fmt_moneda(gastos_totales)}", delta_color="inverse")
    c3.metric("Utilidad Neta", fmt_moneda(ingresos_totales - gastos_totales))

    st.divider()

    # Monitor de Cartera
    col_h, col_s = st.columns([2, 1])
    col_h.subheader("🚩 Monitor de Cartera")
    solo_atrasos = col_s.toggle("Mostrar solo clientes con ATRASO", value=True)
    
    if not df_v.empty:
        monitor_data = []
        hoy = datetime.now()

        for _, v in df_v.iterrows():
            pagos_c = df_p[df_p['ubicacion'] == v['ubicacion']]['monto'].sum() if not df_p.empty else 0.0
            try: f_con = datetime.strptime(str(v['fecha']), '%Y-%m-%d')
            except: f_con = hoy
            
            diff = relativedelta(hoy, f_con)
            meses_trans = diff.years * 12 + diff.months
            monto_exigible = meses_trans * float(v['mensualidad'])
            deuda_vencida = monto_exigible - pagos_c
            
            # Estatus Convencional
            if deuda_vencida > 1.0:
                f_venc = f_con + relativedelta(months=meses_trans)
                dias_m = (hoy - f_venc).days
                est = "🔴 ATRASO"
            else:
                est = "🟢 AL CORRIENTE"
                deuda_vencida, dias_m = 0.0, 0

            monitor_data.append({
                "Ubicación": v['ubicacion'], "Cliente": v['cliente'],
                "Estatus": est, "Días Mora": dias_m,
                "Deuda Vencida": deuda_vencida, "Saldo Total": float(v['precio_total']) - float(v['enganche']) - pagos_c
            })

        df_mon = pd.DataFrame(monitor_data)
        if solo_atrasos: df_mon = df_mon[df_mon["Estatus"] == "🔴 ATRASO"]

        if df_mon.empty: st.success("✅ Todo al corriente")
        else:
            st.dataframe(df_mon.style.applymap(lambda x: 'color: #FF4B4B; font-weight: bold' if "🔴" in str(x) else '', subset=['Estatus']),
                         use_container_width=True, hide_index=True,
                         column_config={"Deuda Vencida": st.column_config.NumberColumn(format="$ %.2f"), "Saldo Total": st.column_config.NumberColumn(format="$ %.2f")})

# ==========================================
# 📝 MÓDULO: VENTAS
# ==========================================
elif menu == "📝 Ventas":
    df_v = cargar_datos("ventas")
    df_u = cargar_datos("ubicaciones")
    df_cl = cargar_datos("clientes")
    
    with st.expander("➕ Registrar Venta", expanded=True):
        lotes_disp = df_u[df_u["estatus"] == "Disponible"]["ubicacion"].tolist()
        f_lote = st.selectbox("Seleccione Lote", ["--"] + lotes_disp)
        
        precio_sug = 0.0
        if f_lote != "--":
            precio_sug = float(df_u[df_u["ubicacion"] == f_lote].iloc[0]["precio"])
            st.info(f"Precio sugerido: {fmt_moneda(precio_sug)}")

        with st.form("f_v"):
            c1, c2 = st.columns(2)
            cli = c1.selectbox("Cliente", df_cl["id_cliente"].astype(str) + " | " + df_cl["nombre"])
            ven = c1.selectbox("Vendedor", ["Directo", "Asesor A"])
            fec = c2.date_input("Fecha")
            tot = c2.number_input("Precio Final ($)", value=precio_sug)
            eng = c1.number_input("Enganche ($)")
            pla = c2.number_input("Plazo (Meses)", min_value=1, value=12)
            
            if st.form_submit_button("Vender"):
                nid = int(pd.to_numeric(df_v["id_venta"], errors='coerce').max() + 1) if not df_v.empty else 1
                nv = pd.DataFrame([{"id_venta": nid, "fecha": fec.strftime('%Y-%m-%d'), "ubicacion": f_lote, "cliente": cli.split(" | ")[1], "precio_total": tot, "enganche": eng, "plazo_meses": pla, "mensualidad": (tot-eng)/pla, "estatus_pago": "Activo"}])
                conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=pd.concat([df_v, nv]))
                df_u.loc[df_u["ubicacion"] == f_lote, "estatus"] = "Vendido"
                conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_u)
                st.cache_data.clear(); st.rerun()

# ==========================================
# 📍 MÓDULO: UBICACIONES
# ==========================================
elif menu == "📍 Ubicaciones":
    tab1, tab2 = st.tabs(["📋 Inventario", "🏗️ Gestión"])
    df_cat = cargar_datos("ubicaciones")

    with tab1:
        if not df_cat.empty:
            solo_disp = st.toggle("Solo Disponibles", value=True)
            df_m = df_cat.copy()
            if solo_disp: df_m = df_m[df_m["estatus"] == "Disponible"]
            
            def style_cat(val):
                return 'background-color: #09AB3B; color: white; font-weight: bold' if val == 'Disponible' else 'color: #808495'

            st.dataframe(df_m[["ubicacion", "fase", "precio", "estatus"]].style.applymap(style_cat, subset=['estatus']),
                         use_container_width=True, hide_index=True,
                         column_config={"precio": st.column_config.NumberColumn(format="$ %.2f"), "fase": "Fase"})
    
    with tab2:
        with st.expander("➕ Nuevo Lote"):
            with st.form("n_lote"):
                c1, c2 = st.columns(2)
                u = c1.text_input("Lote")
                f = c1.number_input("Fase", min_value=1, step=1)
                p = c2.number_input("Precio ($)", min_value=0.0)
                e = c2.selectbox("Estatus", ["Disponible", "Vendido", "Apartado"])
                if st.form_submit_button("Guardar"):
                    nuevo = pd.DataFrame([{"id_ubi": len(df_cat)+1, "ubicacion": u, "fase": f, "precio": p, "estatus": e}])
                    conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=pd.concat([df_cat, nuevo]))
                    st.cache_data.clear(); st.rerun()

# ==========================================
# 💰 MÓDULO: COBRANZA
# ==========================================
elif menu == "💰 Cobranza":
    st.header("💰 Registro de Cobranza")
    
    df_v = cargar_datos("ventas")
    df_p = cargar_datos("pagos")
    
    if df_v.empty:
        st.warning("No hay ventas registradas. No se pueden procesar pagos.")
    else:
        with st.expander("➕ Registrar Nuevo Pago / Abono", expanded=True):
            # 1. SELECCIÓN DE CONTRATO
            # Solo mostramos contratos activos para cobrar
            df_activos = df_v[df_v["estatus_pago"].fillna("Activo") == "Activo"]
            
            opciones_v = df_activos["ubicacion"] + " | " + df_activos["cliente"]
            sel_v = st.selectbox("Seleccione el Lote para aplicar pago:", options=["-- Seleccionar --"] + opciones_v.tolist())
            
            if sel_v != "-- Seleccionar --":
                # Extraer datos del contrato
                ubi_sel = sel_v.split(" | ")[0]
                datos_v = df_v[df_v["ubicacion"] == ubi_sel].iloc[0]
                
                # Calcular deuda a la fecha para informar al usuario
                pagos_previos = df_p[df_p["ubicacion"] == ubi_sel]["monto"].sum() if not df_p.empty else 0.0
                
                hoy = datetime.now()
                try: f_con = datetime.strptime(str(datos_v['fecha']), '%Y-%m-%d')
                except: f_con = hoy
                
                diff = relativedelta(hoy, f_con)
                meses_t = diff.years * 12 + diff.months
                monto_exigible = meses_t * float(datos_v['mensualidad'])
                deuda_vencida = max(0.0, monto_que_deberia_llevar := monto_exigible - pagos_previos)
                
                # Mostrar resumen rápido al cobrador
                st.info(f"👤 **Cliente:** {datos_v['cliente']} | 📅 **Mensualidad:** {fmt_moneda(datos_v['mensualidad'])}")
                if deuda_vencida > 1:
                    st.warning(f"⚠️ **Deuda Pendiente a la fecha:** {fmt_moneda(deuda_vencida)}")
                else:
                    st.success("✅ El cliente está al corriente.")

                # 2. FORMULARIO DE PAGO
                with st.form("form_pago", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    f_pago_monto = c1.number_input("Monto a pagar ($)", min_value=0.0, step=100.0, value=float(datos_v['mensualidad']))
                    f_pago_fecha = c2.date_input("Fecha de recepción", value=datetime.now())
                    
                    c3, c4 = st.columns(2)
                    f_pago_metodo = c3.selectbox("Método de Pago", ["Transferencia", "Efectivo", "Depósito", "Cheque"])
                    f_pago_folio = c4.text_input("Folio de Recibo / Referencia")
                    
                    f_pago_nota = st.text_input("Notas del pago")
                    
                    if st.form_submit_button("Registrar Pago", type="primary"):
                        if f_pago_monto <= 0:
                            st.error("El monto debe ser mayor a cero.")
                        else:
                            # Crear registro de pago
                            nuevo_p = pd.DataFrame([{
                                "id_pago": int(df_p["id_pago"].max() + 1) if not df_p.empty and "id_pago" in df_p.columns else 1,
                                "fecha": f_pago_fecha.strftime('%Y-%m-%d'),
                                "ubicacion": ubi_sel,
                                "cliente": datos_v['cliente'],
                                "monto": round(f_pago_monto, 2),
                                "metodo": f_pago_metodo,
                                "folio": f_pago_folio,
                                "notas": f_pago_nota
                            }])
                            
                            # Guardar en Sheets
                            df_p_final = pd.concat([df_p, nuevo_p], ignore_index=True)
                            conn.update(spreadsheet=URL_SHEET, worksheet="pagos", data=df_p_final)
                            
                            st.success(f"✅ Pago de {fmt_moneda(f_pago_monto)} registrado correctamente para el lote {ubi_sel}.")
                            st.cache_data.clear()
                            st.rerun()

    st.divider()
    
    # 3. HISTORIAL DE PAGOS RECIENTES
    st.subheader("📋 Historial Recente de Ingresos")
    if not df_p.empty:
        # Mostramos los últimos 15 pagos realizados
        df_p_ver = df_p.sort_index(ascending=False).head(15)
        st.dataframe(
            df_p_ver,
            use_container_width=True,
            hide_index=True,
            column_config={
                "monto": st.column_config.NumberColumn("Monto", format="$ %.2f"),
                "fecha": st.column_config.DateColumn("Fecha"),
                "id_pago": None # Ocultamos el ID interno
            }
        )
    else:
        st.info("No se han registrado pagos todavía.")

# ==========================================
# 💸 MÓDULO: GASTOS
# ==========================================
elif menu == "💸 Gastos":
    st.header("💸 Control de Gastos Operativos")
    
    df_g = cargar_datos("gastos")
    
    # --- FORMULARIO DE REGISTRO ---
    with st.expander("➕ Registrar Nuevo Gasto", expanded=True):
        with st.form("form_gastos", clear_on_submit=True):
            c1, c2 = st.columns(2)
            
            with c1:
                f_gasto_fecha = st.date_input("Fecha del Gasto", value=datetime.now())
                f_gasto_cat = st.selectbox("Categoría", [
                    "Nómina", 
                    "Comisiones", 
                    "Publicidad", 
                    "Mantenimiento", 
                    "Impuestos", 
                    "Servicios (Luz/Agua)", 
                    "Oficina",
                    "Otros"
                ])
            
            with c2:
                f_gasto_monto = st.number_input("Monto del Gasto ($)", min_value=0.0, step=100.0)
                f_gasto_concepto = st.text_input("Concepto / Descripción")
            
            f_gasto_pago = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Tarjeta", "Cheque"])

            if st.form_submit_button("Guardar Gasto", type="primary"):
                if f_gasto_monto <= 0:
                    st.error("El monto debe ser mayor a cero.")
                elif f_gasto_concepto == "":
                    st.error("Por favor, ingresa una descripción para el gasto.")
                else:
                    # Crear nuevo registro
                    nuevo_g = pd.DataFrame([{
                        "id_gasto": int(df_g["id_gasto"].max() + 1) if not df_g.empty and "id_gasto" in df_g.columns else 1,
                        "fecha": f_gasto_fecha.strftime('%Y-%m-%d'),
                        "categoria": f_gasto_cat,
                        "concepto": f_gasto_concepto,
                        "monto": round(f_gasto_monto, 2),
                        "metodo": f_gasto_pago
                    }])
                    
                    # Actualizar Sheets
                    df_g_final = pd.concat([df_g, nuevo_g], ignore_index=True)
                    conn.update(spreadsheet=URL_SHEET, worksheet="gastos", data=df_g_final)
                    
                    st.success(f"✅ Gasto por {fmt_moneda(f_gasto_monto)} registrado correctamente.")
                    st.cache_data.clear()
                    st.rerun()

    st.divider()

    # --- RESUMEN Y TABLA ---
    if not df_g.empty:
        # Métricas rápidas del mes actual
        hoy = datetime.now()
        df_g['fecha_dt'] = pd.to_datetime(df_g['fecha'])
        gastos_mes = df_g[df_g['fecha_dt'].dt.month == hoy.month]['monto'].sum()
        
        c_res1, c_res2 = st.columns(2)
        c_res1.metric("Gastos del Mes Actual", fmt_moneda(gastos_mes))
        c_res2.metric("Total Histórico de Gastos", fmt_moneda(df_g['monto'].sum()))

        st.subheader("📋 Listado de Egresos")
        
        # Filtro por categoría
        cats = ["Todos"] + df_g["categoria"].unique().tolist()
        filtro_cat = st.selectbox("Filtrar por categoría:", cats)
        
        df_mostrar = df_g.sort_values("fecha", ascending=False)
        if filtro_cat != "Todos":
            df_mostrar = df_mostrar[df_mostrar["categoria"] == filtro_cat]

        st.dataframe(
            df_mostrar[["fecha", "categoria", "concepto", "monto", "metodo"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "monto": st.column_config.NumberColumn("Monto", format="$ %.2f"),
                "fecha": st.column_config.DateColumn("Fecha"),
                "categoria": "Tipo",
                "concepto": "Descripción"
            }
        )
    else:
        st.info("No se han registrado gastos todavía.")

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

# ==========================================
# 📍 MÓDULO: CATÁLOGO (UBICACIONES)
# ==========================================
elif menu == "📍 Catálogo":
    st.header("📍 Inventario de Ubicaciones")
    
    tab1, tab2 = st.tabs(["📋 Vista de Inventario", "🏗️ Gestión y Altas"])
    df_cat = cargar_datos("ubicaciones")

    # --- PESTAÑA 1: VISTA DE INVENTARIO ---
    with tab1:
        if not df_cat.empty:
            # Filtros rápidos en la parte superior
            c_f1, c_f2 = st.columns([1, 1])
            with c_f1:
                solo_disp = st.toggle("Mostrar solo lotes DISPONIBLES", value=True)
            with c_f2:
                # Extraer fases únicas para el filtro
                if "fase" in df_cat.columns:
                    fases_lista = sorted(df_cat["fase"].unique().tolist())
                    filtro_fase = st.multiselect("Filtrar por Fase:", options=fases_lista)
                else:
                    filtro_fase = []

            # Aplicar filtros al DataFrame
            df_mostrar = df_cat.copy()
            if solo_disp:
                df_mostrar = df_mostrar[df_mostrar["estatus"] == "Disponible"]
            if filtro_fase:
                df_mostrar = df_mostrar[df_mostrar["fase"].isin(filtro_fase)]

            # Lógica de colores (Solo verde para disponibles)
            def estilo_inventario(val):
                if val == 'Disponible':
                    return 'background-color: #09AB3B; color: white; font-weight: bold'
                return 'color: #808495'

            # Configuración de columnas
            st.dataframe(
                df_mostrar[["ubicacion", "fase", "precio", "estatus"]].style.applymap(estilo_inventario, subset=['estatus']),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ubicacion": "Identificador Lote",
                    "fase": st.column_config.NumberColumn("Fase", format="%d"),
                    "precio": st.column_config.NumberColumn("Precio de Lista", format="$ %.2f"),
                    "estatus": "Estado Actual"
                }
            )
            
            # Resumen de esta vista
            st.caption(f"Mostrando {len(df_mostrar)} ubicaciones.")
        else:
            st.info("El catálogo está vacío. Ve a la pestaña de 'Gestión' para agregar el primer lote.")

    # --- PESTAÑA 2: GESTIÓN Y ALTAS ---
    with tab2:
        st.subheader("Control de Inventario")
        
        # Formulario para nuevo lote
        with st.expander("➕ Dar de alta nuevo Lote", expanded=False):
            with st.form("form_nuevo_lote", clear_on_submit=True):
                c1, c2 = st.columns(2)
                n_ubi = c1.text_input("Nombre/Número del Lote (ej: L-01)")
                n_fase = c1.number_input("Fase del desarrollo", min_value=1, step=1, value=1)
                n_pre = c2.number_input("Precio de Lista ($)", min_value=0.0, step=1000.0)
                n_est = c2.selectbox("Estatus Inicial", ["Disponible", "Apartado", "Vendido"])
                
                if st.form_submit_button("Registrar en Catálogo"):
                    if n_ubi:
                        # Generar ID
                        nuevo_id = int(df_cat["id_ubi"].max() + 1) if not df_cat.empty and "id_ubi" in df_cat.columns else 1
                        
                        nuevo_reg = pd.DataFrame([{
                            "id_ubi": nuevo_id,
                            "ubicacion": n_ubi,
                            "fase": n_fase,
                            "precio": n_pre,
                            "estatus": n_est
                        }])
                        
                        df_cat_final = pd.concat([df_cat, nuevo_reg], ignore_index=True)
                        conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_cat_final)
                        
                        st.success(f"✅ Lote {n_ubi} (Fase {n_fase}) agregado correctamente.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("El nombre de la ubicación es obligatorio.")

        st.divider()
        
        # Edición rápida de precios y estatus
        if not df_cat.empty:
            st.write("🔧 **Edición Rápida de Datos**")
            st.caption("Puedes editar directamente en la tabla y presionar 'Guardar Cambios'")
            
            df_editado = st.data_editor(
                df_cat,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id_ubi": None, # Ocultar ID
                    "fase": st.column_config.NumberColumn("Fase", step=1),
                    "precio": st.column_config.NumberColumn("Precio ($)", format="$ %.2f"),
                    "estatus": st.column_config.SelectboxColumn("Estado", options=["Disponible", "Apartado", "Vendido"])
                }
            )
            
            if st.button("💾 Guardar Cambios en el Catálogo"):
                conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_editado)
                st.success("¡Catálogo actualizado correctamente!")
                st.cache_data.clear()
                st.rerun()

# ==========================================
# 📇 MÓDULO: DIRECTORIO
# ==========================================
elif menu == "📇 Directorio":
    st.header("📇 Directorio de Contactos")
    
    tab_cl, tab_vd = st.tabs(["👥 Clientes", "💼 Vendedores"])
    
    # --- PESTAÑA: CLIENTES ---
    with tab_cl:
        df_cl = cargar_datos("clientes")
        
        with st.expander("➕ Registrar Nuevo Cliente", expanded=False):
            with st.form("form_nuevo_cliente", clear_on_submit=True):
                c1, c2 = st.columns(2)
                n_nom = c1.text_input("Nombre Completo")
                n_tel = c1.text_input("Teléfono / WhatsApp")
                n_corr = c2.text_input("Correo Electrónico")
                n_dir = c2.text_input("Dirección de Contacto")
                
                if st.form_submit_button("Guardar Cliente"):
                    if n_nom:
                        # Generar ID de cliente
                        nuevo_id = int(df_cl["id_cliente"].max() + 1) if not df_cl.empty and "id_cliente" in df_cl.columns else 1
                        
                        nuevo_reg = pd.DataFrame([{
                            "id_cliente": nuevo_id,
                            "nombre": n_nom,
                            "telefono": n_tel,
                            "correo": n_corr,
                            "direccion": n_dir,
                            "fecha_registro": datetime.now().strftime('%Y-%m-%d')
                        }])
                        
                        df_cl_final = pd.concat([df_cl, nuevo_reg], ignore_index=True)
                        conn.update(spreadsheet=URL_SHEET, worksheet="clientes", data=df_cl_final)
                        
                        st.success(f"✅ Cliente '{n_nom}' registrado con éxito (ID: {nuevo_id}).")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("El nombre del cliente es obligatorio.")

        if not df_cl.empty:
            st.subheader("Listado de Clientes")
            # Buscador de clientes
            busqueda = st.text_input("🔍 Buscar cliente por nombre o ID", placeholder="Ej: Juan Pérez")
            
            df_cl_ver = df_cl.copy()
            if busqueda:
                df_cl_ver = df_cl_ver[df_cl_ver['nombre'].str.contains(busqueda, case=False, na=False) | 
                                      df_cl_ver['id_cliente'].astype(str).str.contains(busqueda)]
            
            st.dataframe(
                df_cl_ver[["id_cliente", "nombre", "telefono", "correo", "fecha_registro"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id_cliente": st.column_config.NumberColumn("ID", width="small"),
                    "nombre": "Nombre Completo",
                    "telefono": "WhatsApp/Cel",
                    "correo": "Email",
                    "fecha_registro": "Alta"
                }
            )
        else:
            st.info("No hay clientes registrados.")

    # --- PESTAÑA: VENDEDORES ---
    with tab_vd:
        df_vd = cargar_datos("vendedores")
        
        with st.expander("➕ Dar de alta Vendedor", expanded=False):
            with st.form("form_vendedor", clear_on_submit=True):
                v_nom = st.text_input("Nombre del Asesor")
                v_tel = st.text_input("Teléfono de Contacto")
                v_com = st.number_input("Porcentaje de Comisión Sugerido (%)", min_value=0.0, max_value=100.0, value=3.0)
                
                if st.form_submit_button("Registrar Vendedor"):
                    if v_nom:
                        # Generar ID
                        v_id = int(df_vd["id_vendedor"].max() + 1) if not df_vd.empty and "id_vendedor" in df_vd.columns else 1
                        
                        nuevo_v = pd.DataFrame([{
                            "id_vendedor": v_id,
                            "nombre": v_nom,
                            "telefono": v_tel,
                            "comision_base": v_com,
                            "estatus": "Activo"
                        }])
                        
                        df_vd_final = pd.concat([df_vd, nuevo_v], ignore_index=True)
                        conn.update(spreadsheet=URL_SHEET, worksheet="vendedores", data=df_vd_final)
                        
                        st.success(f"✅ Vendedor '{v_nom}' registrado correctamente.")
                        st.cache_data.clear()
                        st.rerun()

        if not df_vd.empty:
            st.subheader("Equipo de Ventas")
            st.table(df_vd[["id_vendedor", "nombre", "telefono", "comision_base", "estatus"]])
        else:
            st.info("No hay vendedores registrados en el equipo.")

