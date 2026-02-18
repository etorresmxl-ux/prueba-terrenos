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

# --- BARRA LATERAL (Navegación) ---
st.sidebar.title("Navegación")
menu = st.sidebar.radio(
    "Seleccione un módulo:",
    ["🏠 Inicio", "📝 Ventas", "📊 Detalle de Crédito", "💰 Cobranza", "💸 Gastos", "📍 Ubicaciones", "👥 Clientes"]
)

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
# 📝 MÓDULO: VENTAS (Corregido y Limpio)
# ==========================================
elif menu == "📝 Ventas":
    st.title("📝 Gestión de Ventas y Contratos")
    
    # Cargar bases de datos
    df_v = cargar_datos("ventas")
    df_u = cargar_datos("ubicaciones")
    df_cl = cargar_datos("clientes")
    df_vd = cargar_datos("vendedores")

    # Creamos dos pestañas: una para registrar/editar y otra para ver la lista
    tab1, tab2 = st.tabs(["✨ Registro y Edición", "📋 Ver Historial"])

    with tab1:
        # 1. Selector para saber si vamos a Crear o a Editar
        opciones_v = ["-- NUEVA VENTA --"]
        if not df_v.empty:
            opciones_v += (df_v["ubicacion"] + " | " + df_v["cliente"]).tolist()
        
        seleccion = st.selectbox("¿Qué desea hacer?", opciones_v)

        # Variables para rellenar el formulario
        editando = seleccion != "-- NUEVA VENTA --"
        val_fec = datetime.now()
        val_lote = "--"
        val_cli = "--"
        val_vende = "--"
        val_tot = 0.0
        val_eng = 0.0
        val_pla = 12
        val_coment = ""

        if editando:
            ubi_id = seleccion.split(" | ")[0]
            datos_v = df_v[df_v["ubicacion"] == ubi_id].iloc[0]
            val_fec = pd.to_datetime(datos_v["fecha"])
            val_lote = datos_v["ubicacion"]
            val_cli = datos_v["cliente"]
            val_vende = datos_v.get("vendedor", "--")
            val_tot = float(datos_v["precio_total"])
            val_eng = float(datos_v["enganche"])
            val_pla = int(datos_v["plazo_meses"])
            val_coment = datos_v.get("comentarios", "")

        with st.form("formulario_ventas"):
            c1, c2 = st.columns(2)
            
            # --- LOTE Y PRECIO ---
            lotes_list = ["--"] + df_u["ubicacion"].tolist()
            f_lote = c1.selectbox("📍 Seleccione Ubicación / Lote", lotes_list, 
                                 index=lotes_list.index(val_lote) if val_lote in lotes_list else 0)
            
            # LÓGICA DEL COSTO: Busca el precio en la tabla de ubicaciones
            costo_sugerido = 0.0
            if f_lote != "--":
                # Buscamos en la columna 'precio' o 'costo' de tu Excel de ubicaciones
                row_u = df_u[df_u["ubicacion"] == f_lote].iloc[0]
                # Intentamos obtener 'precio', si no existe buscamos 'costo'
                costo_sugerido = float(row_u.get('precio', row_u.get('costo', 0.0)))
                c1.info(f"💰 Costo en inventario: {fmt_moneda(costo_sugerido)}")

            f_fec = c2.date_input("📅 Fecha de Contrato", value=val_fec)
            
            # --- PARTICIPANTES ---
            clientes_list = ["--"] + (df_cl["nombre"].tolist() if not df_cl.empty else [])
            f_cli = c1.selectbox("👤 Cliente", clientes_list, 
                                index=clientes_list.index(val_cli) if val_cli in clientes_list else 0)
            
            vendedores_list = ["--"] + (df_vd["nombre"].tolist() if not df_vd.empty else [])
            f_vende = c2.selectbox("👔 Vendedor", vendedores_list,
                                  index=vendedores_list.index(val_vende) if val_vende in vendedores_list else 0)
            
            # --- FINANCIERO ---
            # Si es nueva venta y no hemos escrito nada, ponemos el costo que jala del inventario
            precio_final_default = val_tot if editando else costo_sugerido
            
            f_tot = c1.number_input("💵 Precio Final de Venta ($)", min_value=0.0, value=precio_final_default)
            f_eng = c2.number_input("📥 Enganche Recibido ($)", min_value=0.0, value=val_eng)
            f_pla = c1.number_input("🕒 Plazo en Meses", min_value=1, value=val_pla)
            
            # Cálculo de mensualidad visible
            mensu_calc = (f_tot - f_eng) / f_pla if f_pla > 0 else 0
            c2.write(f"**Mensualidad:** {fmt_moneda(mensu_calc)}")
            
            f_coment = st.text_area("📝 Comentarios de la venta", value=val_coment)

            # BOTÓN DE GUARDAR
            if st.form_submit_button("💾 Guardar Venta"):
                if f_lote == "--" or f_cli == "--":
                    st.error("Por favor seleccione Lote y Cliente.")
                else:
                    # Datos a guardar
                    nueva_fila = {
                        "fecha": f_fec.strftime('%Y-%m-%d'),
                        "ubicacion": f_lote,
                        "cliente": f_cli,
                        "vendedor": f_vende,
                        "precio_total": f_tot,
                        "enganche": f_eng,
                        "plazo_meses": f_pla,
                        "mensualidad": mensu_calc,
                        "comentarios": f_coment,
                        "estatus_pago": "Activo"
                    }

                    if not editando:
                        # Generar nuevo ID
                        nid = int(df_v["id_venta"].max() + 1) if not df_v.empty else 1
                        nueva_fila["id_venta"] = nid
                        df_v = pd.concat([df_v, pd.DataFrame([nueva_fila])], ignore_index=True)
                        # Cambiar estatus de la ubicación
                        df_u.loc[df_u["ubicacion"] == f_lote, "estatus"] = "Vendido"
                    else:
                        # Actualizar la fila existente
                        idx = df_v[df_v["ubicacion"] == ubi_id].index[0]
                        for col, val in nueva_fila.items():
                            df_v.at[idx, col] = val
                    
                    # Subir a Google Sheets
                    conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=df_v)
                    conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_u)
                    
                    st.success("✅ ¡Venta guardada exitosamente!")
                    st.cache_data.clear()
                    st.rerun()

    with tab2:
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


