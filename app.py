import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestión Inmobiliaria Pro", layout="wide")

# --- FECHA SUPERIOR DERECHA ---
col_t1, col_t2 = st.columns([4, 1])
with col_t2:
    hoy_dt = datetime.now()
    st.markdown(f"**📅 Fecha:** {hoy_dt.strftime('%d/%m/%Y')}")

# --- BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('inmobiliaria.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS terrenos (id INTEGER PRIMARY KEY AUTOINCREMENT, manzana TEXT, lote TEXT, metros REAL, costo REAL, estatus TEXT DEFAULT "Disponible")')
    c.execute('CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, telefono TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS vendedores (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, telefono TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS ventas (id INTEGER PRIMARY KEY AUTOINCREMENT, id_terreno INTEGER, id_cliente INTEGER, id_vendedor INTEGER, enganche REAL, meses INTEGER, mensualidad REAL, comision_total REAL, fecha TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS pagos (id INTEGER PRIMARY KEY AUTOINCREMENT, id_venta INTEGER, monto REAL, fecha TEXT)')
    conn.commit()
    return conn

def f_money(valor):
    if valor is None or str(valor).lower() in ['nan', 'none', '']: return "$0.00"
    try: return f"${float(valor):,.2f}"
    except: return "$0.00"

conn = init_db()
c = conn.cursor()

# --- MENÚ ---
st.sidebar.title("📑 NAVEGACIÓN")
menu = ["🏠 Resumen de Cartera", "🔍 Detalle por Lote", "💸 Cobranza", "📈 Gestión de Ventas", "📝 Nueva Venta", "🏗️ Catálogo Terrenos", "👥 Clientes/Vendedores"]
choice = st.sidebar.radio("Seleccione una opción:", menu)

# --- 1. RESUMEN DE CARTERA ---
if choice == "🏠 Resumen de Cartera":
    st.header("📋 ESTADO DE CUENTA GENERAL")
    query = '''
        SELECT v.id as id_venta, 'M'||t.manzana||'-L'||t.lote as ubicacion, c.nombre as cliente, 
        t.costo as costo_total, v.enganche, v.fecha as fecha_contrato, v.mensualidad,
        IFNULL((SELECT SUM(monto) FROM pagos WHERE id_venta = v.id), 0) as suma_pagos,
        (SELECT MAX(fecha) FROM pagos WHERE id_venta = v.id) as ultimo_pago_f
        FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id
    '''
    df_raw = pd.read_sql_query(query, conn)
    res = []
    for _, r in df_raw.iterrows():
        total_pagado = (r['enganche'] or 0) + (r['suma_pagos'] or 0)
        saldo_hoy = (r['costo_total'] or 0) - total_pagado
        f_contrato = datetime.strptime(r['fecha_contrato'], '%Y-%m-%d')
        meses_deberia = (hoy_dt.year - f_contrato.year) * 12 + (hoy_dt.month - f_contrato.month)
        if hoy_dt.day < f_contrato.day: meses_deberia -= 1
        atraso_monto = max(0, (meses_deberia * (r['mensualidad'] or 0)) - (r['suma_pagos'] or 0))
        
        dias_atraso = 0
        if atraso_monto > 10:
            ref = datetime.strptime(r['ultimo_pago_f'], '%Y-%m-%d') if r['ultimo_pago_f'] else f_contrato
            dias_atraso = (hoy_dt - (ref + pd.DateOffset(months=1))).days

        res.append({
            "Ubicación": r['ubicacion'], "Cliente": r['cliente'], "Costo": f_money(r['costo_total']),
            "Enganche": f_money(r['enganche']), "Fecha de Contrato": r['fecha_contrato'],
            "Total Pagado": f_money(total_pagado), "Saldo Hoy": f_money(saldo_hoy),
            "Estatus": "✅ AL CORRIENTE" if atraso_monto <= 10 else "⚠️ MOROSO",
            "Último Pago": r['ultimo_pago_f'] if r['ultimo_pago_f'] else "N/A",
            "Días de Atraso": max(0, dias_atraso), "Pago para estar al corriente": f_money(atraso_monto)
        })
    st.dataframe(pd.DataFrame(res), use_container_width=True, hide_index=True)

# --- 2. DETALLE POR LOTE (NUEVO MÓDULO) ---
elif choice == "🔍 Detalle por Lote":
    st.header("🔍 ESTADO DE CUENTA DETALLADO")
    
    # Selector de ubicación
    query_u = "SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u FROM ventas v JOIN terrenos t ON v.id_terreno = t.id"
    df_u = pd.read_sql_query(query_u, conn)
    
    if df_u.empty:
        st.info("No hay ventas para mostrar.")
    else:
        lote_sel = st.selectbox("Seleccione Ubicación para ver detalle:", df_u['u'])
        id_venta = int(df_u[df_u['u'] == lote_sel]['id'].values[0])
        
        # Obtener Datos Generales
        q_gen = f'''SELECT c.nombre, t.costo, v.enganche, v.fecha, v.meses, v.mensualidad 
                    FROM ventas v JOIN clientes c ON v.id_cliente = c.id 
                    JOIN terrenos t ON v.id_terreno = t.id WHERE v.id = {id_venta}'''
        d_gen = pd.read_sql_query(q_gen, conn).iloc[0]
        
        # Obtener Pagos realizados
        q_pagos = f"SELECT monto, fecha FROM pagos WHERE id_venta = {id_venta} ORDER BY fecha ASC"
        df_pagos_reg = pd.read_sql_query(q_pagos, conn)
        total_abonos = df_pagos_reg['monto'].sum()
        
        # --- BLOQUE DE DATOS GENERALES ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Cliente", d_gen['nombre'])
        c1.metric("Valor Terreno", f_money(d_gen['costo']))
        
        c2.metric("Fecha Contrato", d_gen['fecha'])
        c2.metric("Enganche", f_money(d_gen['enganche']))
        
        total_p = d_gen['enganche'] + total_abonos
        c3.metric("Pagos Totales", f_money(total_p))
        c3.metric("Saldo Restante", f_money(d_gen['costo'] - total_p))
        
        c4.metric("Mensualidad", f_money(d_gen['mensualidad']))
        c4.metric("Plazo", f"{d_gen['meses']} meses")

        st.divider()
        st.subheader("📅 Plan de Pagos vs Abonos Reales")

        # --- CONSTRUCCIÓN DE TABLA DE AMORTIZACIÓN ---
        tabla_am = []
        saldo_insoluto = d_gen['costo'] - d_gen['enganche']
        fecha_pago = datetime.strptime(d_gen['fecha'], '%Y-%m-%d')
        abonos_acumulados = total_abonos

        for i in range(1, int(d_gen['meses']) + 1):
            fecha_pago += pd.DateOffset(months=1)
            cuota = d_gen['mensualidad']
            
            # Determinar cuánto de los abonos reales cubre esta cuota
            pago_aplicado = min(cuota, abonos_acumulados)
            abonos_acumulados -= pago_aplicado
            saldo_insoluto -= pago_aplicado
            
            estatus_pago = "✅ PAGADO" if pago_aplicado >= (cuota - 1) else ("🟡 PARCIAL" if pago_aplicado > 0 else "❌ PENDIENTE")
            
            tabla_am.append({
                "Mes": i,
                "Fecha Programada": fecha_pago.strftime('%d/%m/%Y'),
                "Cuota Pactada": f_money(cuota),
                "Abonado a esta letra": f_money(pago_aplicado),
                "Saldo tras este mes": f_money(max(0, saldo_insoluto)),
                "Estatus": estatus_pago
            })
            
        st.dataframe(pd.DataFrame(tabla_am), use_container_width=True, hide_index=True)

# --- 3. COBRANZA (VINCULADA) ---
elif choice == "💸 Cobranza":
    st.header("💰 REGISTRO DE ABONOS")
    query_c = "SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u, c.nombre as cl FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id"
    df_c = pd.read_sql_query(query_c, conn)
    if not df_c.empty:
        mapa = {row['u']: row for _, row in df_c.iterrows()}
        u_sel = st.selectbox("📍 UBICACIÓN", sorted(list(mapa.keys())))
        st.text_input("👤 CLIENTE", value=mapa[u_sel]['cl'], disabled=True)
        with st.form("p"):
            m = st.number_input("MONTO", min_value=0.0)
            f = st.date_input("FECHA")
            if st.form_submit_button("REGISTRAR"):
                c.execute("INSERT INTO pagos (id_venta, monto, fecha) VALUES (?,?,?)", (int(mapa[u_sel]['id']), m, f.strftime('%Y-%m-%d')))
                conn.commit(); st.rerun()

# --- (RESTO DE MÓDULOS IGUALES) ---
elif choice == "📈 Gestión de Ventas":
    st.header("📈 ADMINISTRAR OPERACIONES")
    # ... Lógica de cancelación ...
elif choice == "📝 Nueva Venta":
    st.header("📝 REGISTRAR VENTA")
    # ... Lógica de venta ...
elif choice == "🏗️ Catálogo Terrenos":
    st.header("🏗️ INVENTARIO")
    # ... Lógica de terrenos ...
elif choice == "👥 Clientes/Vendedores":
    st.header("👥 REGISTROS")