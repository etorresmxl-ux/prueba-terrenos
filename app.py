import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestión Inmobiliaria Pro", layout="wide")

# --- SISTEMA DE SEGURIDAD (PASSWORD) ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "Terrenos2026": # <--- ESTA ES TU CLAVE
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.text_input("Introduce la clave de acceso", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Clave incorrecta, intenta de nuevo", type="password", on_change=password_entered, key="password")
        return False
    return True

if not check_password():
    st.stop()

# --- FECHA SUPERIOR DERECHA ---
col_t1, col_t2 = st.columns([4, 1])
with col_t2:
    hoy_dt = datetime.now()
    st.markdown(f"**📅 Fecha:** {hoy_dt.strftime('%d/%m/%Y')}")

# --- BASE DE DATOS ---
@st.cache_resource
def init_db():
    conn = sqlite3.connect('inmobiliaria.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS terrenos (id INTEGER PRIMARY KEY AUTOINCREMENT, manzana TEXT, lote TEXT, metros REAL, costo REAL, estatus TEXT DEFAULT "Disponible")')
    c.execute('CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, telefono TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS vendedores (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, telefono TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS ventas (id INTEGER PRIMARY KEY AUTOINCREMENT, id_terreno INTEGER, id_cliente INTEGER, id_vendedor INTEGER, enganche REAL, meses INTEGER, mensualidad REAL, fecha TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS pagos (id INTEGER PRIMARY KEY AUTOINCREMENT, id_venta INTEGER, monto REAL, fecha TEXT)')
    conn.commit()
    return conn

def f_money(valor):
    if valor is None or str(valor).lower() in ['nan', 'none', '']: return "$0.00"
    try: return f"${float(valor):,.2f}"
    except: return "$0.00"

conn = init_db()
c = conn.cursor()

# --- MENÚ LATERAL ---
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

# --- 2. DETALLE POR LOTE ---
elif choice == "🔍 Detalle por Lote":
    st.header("🔍 ESTADO DE CUENTA DETALLADO")
    query_u = "SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u FROM ventas v JOIN terrenos t ON v.id_terreno = t.id"
    df_u = pd.read_sql_query(query_u, conn)
    if not df_u.empty:
        lote_sel = st.selectbox("Seleccione Ubicación:", df_u['u'])
        id_venta = int(df_u[df_u['u'] == lote_sel]['id'].values[0])
        q_gen = f"SELECT c.nombre, t.costo, v.enganche, v.fecha, v.meses, v.mensualidad FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id WHERE v.id = {id_venta}"
        d_gen = pd.read_sql_query(q_gen, conn).iloc[0]
        total_abonos = pd.read_sql_query(f"SELECT SUM(monto) as s FROM pagos WHERE id_venta = {id_venta}", conn)['s'].iloc[0] or 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Cliente", d_gen['nombre'])
        c2.metric("Valor", f_money(d_gen['costo']))
        c3.metric("Saldo", f_money(d_gen['costo'] - (d_gen['enganche'] + total_abonos)))
        
        st.divider()
        tabla_am = []
        saldo_insoluto = d_gen['costo'] - d_gen['enganche']
        fecha_pago = datetime.strptime(d_gen['fecha'], '%Y-%m-%d')
        acum = total_abonos
        for i in range(1, int(d_gen['meses']) + 1):
            fecha_pago += pd.DateOffset(months=1)
            pago_mes = min(d_gen['mensualidad'], acum)
            acum -= pago_mes
            saldo_insoluto -= pago_mes
            tabla_am.append({
                "Mes": i, "Fecha": fecha_pago.strftime('%d/%m/%Y'),
                "Cuota": f_money(d_gen['mensualidad']), "Abonado": f_money(pago_mes),
                "Saldo": f_money(max(0, saldo_insoluto)),
                "Estatus": "✅" if pago_mes >= d_gen['mensualidad']-1 else "❌"
            })
        st.dataframe(pd.DataFrame(tabla_am), use_container_width=True, hide_index=True)

# --- 3. COBRANZA ---
elif choice == "💸 Cobranza":
    st.header("💰 REGISTRO DE ABONOS")
    query_c = "SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u, c.nombre as cl FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id"
    df_c = pd.read_sql_query(query_c, conn)
    if not df_c.empty:
        mapa = {row['u']: row for _, row in df_c.iterrows()}
        u_sel = st.selectbox("📍 UBICACIÓN", sorted(list(mapa.keys())))
        st.info(f"Cliente: {mapa[u_sel]['cl']}")
        with st.form("p"):
            m = st.number_input("MONTO", min_value=0.0)
            f = st.date_input("FECHA")
            if st.form_submit_button("REGISTRAR"):
                c.execute("INSERT INTO pagos (id_venta, monto, fecha) VALUES (?,?,?)", (int(mapa[u_sel]['id']), m, f.strftime('%Y-%m-%d')))
                conn.commit(); st.rerun()

# --- 4. GESTIÓN DE VENTAS ---
elif choice == "📈 Gestión de Ventas":
    st.header("📈 ADMINISTRAR VENTAS")
    query_g = "SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u, c.nombre, v.id_terreno FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id"
    df_g = pd.read_sql_query(query_g, conn)
    if not df_g.empty:
        sel = st.selectbox("Venta a cancelar:", df_g['u'] + " - " + df_g['nombre'])
        if st.button("❌ ELIMINAR VENTA Y LIBERAR LOTE"):
            row = df_g[df_g['u'] + " - " + df_g['nombre'] == sel].iloc[0]
            c.execute("DELETE FROM ventas WHERE id=?", (int(row['id']),))
            c.execute("UPDATE terrenos SET estatus='Disponible' WHERE id=?", (int(row['id_terreno']),))
            conn.commit(); st.rerun()

# --- 5. NUEVA VENTA ---
elif choice == "📝 Nueva Venta":
    st.header("📝 REGISTRAR VENTA")
    lotes = pd.read_sql_query("SELECT * FROM terrenos WHERE estatus='Disponible'", conn)
    clis = pd.read_sql_query("SELECT * FROM clientes", conn)
    vends = pd.read_sql_query("SELECT * FROM vendedores", conn)
    if lotes.empty: st.warning("No hay terrenos disponibles.")
    elif clis.empty: st.warning("Debe registrar clientes primero.")
    else:
        with st.form("nv"):
            l_sel = st.selectbox("Terreno", lotes['manzana'] + "-" + lotes['lote'])
            c_sel = st.selectbox("Cliente", clis['nombre'])
            v_sel = st.selectbox("Vendedor", vends['nombre'])
            eng = st.number_input("Enganche ($)", min_value=0.0)
            plz = st.number_input("Plazo (Meses)", min_value=1, value=48)
            fec = st.date_input("Fecha Contrato")
            if st.form_submit_button("GUARDAR VENTA"):
                id_l = int(lotes[lotes['manzana'] + "-" + lotes['lote'] == l_sel]['id'].values[0])
                id_c = int(clis[clis['nombre'] == c_sel]['id'].values[0])
                id_v = int(vends[vends['nombre'] == v_sel]['id'].values[0])
                costo = float(lotes[lotes['id'] == id_l]['costo'].values[0])
                ms = (costo - eng) / plz
                c.execute("INSERT INTO ventas (id_terreno, id_cliente, id_vendedor, enganche, meses, mensualidad, fecha) VALUES (?,?,?,?,?,?,?)", (id_l, id_c, id_v, eng, plz, ms, fec.strftime('%Y-%m-%d')))
                c.execute("UPDATE terrenos SET estatus='Vendido' WHERE id=?", (id_l,))
                conn.commit(); st.rerun()

# --- 6. CATÁLOGO TERRENOS ---
elif choice == "🏗️ Catálogo Terrenos":
    st.header("🏗️ CATÁLOGO DE TERRENOS")
    with st.expander("➕ Añadir Nuevo Terreno"):
        with st.form("at"):
            c1, c2, c3 = st.columns(3)
            mz = c1.text_input("Manzana")
            lt = c2.text_input("Lote")
            cos = c3.number_input("Precio Total ($)", min_value=0.0)
            if st.form_submit_button("Guardar Terreno"):
                c.execute("INSERT INTO terrenos (manzana, lote, costo) VALUES (?,?,?)", (mz, lt, cos))
                conn.commit(); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT manzana, lote, costo, estatus FROM terrenos", conn), use_container_width=True)

# --- 7. CLIENTES/VENDEDORES ---
elif choice == "👥 Clientes/Vendedores":
    st.header("👥 REGISTRO DE PERSONAS")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Clientes")
        with st.form("fc"):
            n_c = st.text_input("Nombre del Cliente")
            if st.form_submit_button("Registrar Cliente"):
                c.execute("INSERT INTO clientes (nombre) VALUES (?)", (n_c,))
                conn.commit(); st.rerun()
        st.dataframe(pd.read_sql_query("SELECT nombre FROM clientes", conn), use_container_width=True)
    with col2:
        st.subheader("Vendedores")
        with st.form("fv"):
            n_v = st.text_input("Nombre del Vendedor")
            if st.form_submit_button("Registrar Vendedor"):
                c.execute("INSERT INTO vendedores (nombre) VALUES (?)", (n_v,))
                conn.commit(); st.rerun()
        st.dataframe(pd.read_sql_query("SELECT nombre FROM vendedores", conn), use_container_width=True)
