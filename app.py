import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestión Inmobiliaria Pro", layout="wide")

# --- SISTEMA DE SEGURIDAD ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "Terrenos2026":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.text_input("Introduce la clave de acceso", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Clave incorrecta", type="password", on_change=password_entered, key="password")
        return False
    return True

if not check_password():
    st.stop()

# --- CONEXIÓN A BASE DE DATOS ---
def get_db_connection():
    conn = sqlite3.connect('inmobiliaria.db', check_same_thread=False)
    return conn

conn = get_db_connection()
c = conn.cursor()

# Asegurar tablas básicas
c.execute('CREATE TABLE IF NOT EXISTS terrenos (id INTEGER PRIMARY KEY AUTOINCREMENT, manzana TEXT, lote TEXT, costo REAL, estatus TEXT DEFAULT "Disponible")')
c.execute('CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS vendedores (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS ventas (id INTEGER PRIMARY KEY AUTOINCREMENT, id_terreno INTEGER, id_cliente INTEGER, id_vendedor INTEGER, enganche REAL, meses INTEGER, mensualidad REAL, fecha TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS pagos (id INTEGER PRIMARY KEY AUTOINCREMENT, id_venta INTEGER, monto REAL, fecha TEXT)')
conn.commit()

def f_money(valor):
    try: return f"${float(valor or 0):,.2f}"
    except: return "$0.00"

# --- MANEJO DE NAVEGACIÓN ---
if 'lote_seleccionado' not in st.session_state:
    st.session_state['lote_seleccionado'] = None

# --- FECHA SUPERIOR ---
col_t1, col_t2 = st.columns([4, 1])
with col_t2:
    hoy_dt = datetime.now()
    st.markdown(f"**📅 Fecha:** {hoy_dt.strftime('%d/%m/%Y')}")

# --- MENÚ LATERAL ---
st.sidebar.title("📑 NAVEGACIÓN")
menu = ["🏠 Resumen de Cartera", "🔍 Detalle por Lote", "💸 Cobranza", "📈 Gestión de Ventas", "📝 Nueva Venta", "🏗️ Catálogo Terrenos", "👥 Clientes/Vendedores"]

# Cambiar de pestaña automáticamente si hay un lote seleccionado
if st.session_state['lote_seleccionado']:
    default_index = 1
else:
    default_index = 0

choice = st.sidebar.radio("Seleccione una opción:", menu, index=default_index)

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
    
    if df_raw.empty:
        st.warning("No hay ventas registradas todavía.")
    else:
        # Mostramos botones de acceso rápido antes de la tabla para evitar errores de versión
        st.subheader("🚀 Acceso Rápido al Detalle")
        cols = st.columns(4)
        for i, row in df_raw.iterrows():
            with cols[i % 4]:
                if st.button(f"🔎 Ver {row['ubicacion']}", key=f"btn_{row['id_venta']}"):
                    st.session_state['lote_seleccionado'] = row['ubicacion']
                    st.rerun()

        st.divider()
        
        res = []
        for _, r in df_raw.iterrows():
            total_pagado = (r['enganche'] or 0) + (r['suma_pagos'] or 0)
            saldo_hoy = (r['costo_total'] or 0) - total_pagado
            f_con = datetime.strptime(r['fecha_contrato'], '%Y-%m-%d')
            
            # Cálculo de meses
            m_deb = ((hoy_dt.year - f_con.year) * 12 + (hoy_dt.month - f_con.month)) - (1 if hoy_dt.day < f_con.day else 0)
            atr_m = max(0, (m_deb * (r['mensualidad'] or 0)) - (r['suma_pagos'] or 0))
            
            # Cálculo de días de atraso seguro
            ref_str = r['ultimo_pago_f'] if r['ultimo_pago_f'] else r['fecha_contrato']
            ref_dt = datetime.strptime(ref_str, '%Y-%m-%d')
            d_atr = (hoy_dt - ref_dt).days if atr_m > 10 else 0
            
            res.append({
                "Ubicación": r['ubicacion'], "Cliente": r['cliente'], "Costo": f_money(r['costo_total']),
                "Total Pagado": f_money(total_pagado), "Saldo Hoy": f_money(saldo_hoy),
                "Estatus": "✅ AL CORRIENTE" if atr_m <= 10 else "⚠️ MOROSO",
                "Atraso $": f_money(atr_m)
            })

        st.dataframe(pd.DataFrame(res), use_container_width=True, hide_index=True)

# --- 2. DETALLE POR LOTE ---
elif choice == "🔍 Detalle por Lote":
    st.header("🔍 ESTADO DE CUENTA DETALLADO")
    df_u = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u FROM ventas v JOIN terrenos t ON v.id_terreno = t.id", conn)
    
    if df_u.empty:
        st.info("No hay ventas para mostrar.")
    else:
        lista_u = sorted(df_u['u'].tolist())
        idx_ini = lista_u.index(st.session_state['lote_seleccionado']) if st.session_state['lote_seleccionado'] in lista_u else 0
        
        c_sel, c_btn = st.columns([3, 1])
        lote_sel = c_sel.selectbox("Ubicación seleccionada:", lista_u, index=idx_ini)
        
        if c_btn.button("⬅️ Volver al Resumen"):
            st.session_state['lote_seleccionado'] = None
            st.rerun()

        id_v = int(df_u[df_u['u'] == lote_sel]['id'].values[0])
        q = f"SELECT c.nombre, t.costo, v.enganche, v.fecha, v.meses, v.mensualidad FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id WHERE v.id = {id_v}"
        d = pd.read_sql_query(q, conn).iloc[0]
        pagos_suma = pd.read_sql_query(f"SELECT SUM(monto) as s FROM pagos WHERE id_venta = {id_v}", conn)['s'].iloc[0] or 0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Cliente", d['nombre'])
        c2.metric("Costo", f_money(d['costo']))
        c3.metric("Pagado", f_money(d['enganche'] + pagos_suma))
        c4.metric("Saldo", f_money(d['costo'] - (d['enganche'] + pagos_suma)))

        st.subheader("📅 Tabla de Amortización")
        tabla = []
        saldo_i = d['costo'] - d['enganche']
        f_pago = datetime.strptime(d['fecha'], '%Y-%m-%d')
        acum = pagos_suma
        for i in range(1, int(d['meses']) + 1):
            nm = (f_pago.month % 12) + 1
            ny = f_pago.year + (1 if f_pago.month == 12 else 0)
            f_pago = f_pago.replace(month=nm, year=ny)
            p_m = min(d['mensualidad'], acum)
            acum -= p_m
            saldo_i -= p_m
            tabla.append({
                "Mes": i, "Vencimiento": f_pago.strftime('%d/%m/%Y'),
                "Cuota": f_money(d['mensualidad']), "Abonado": f_money(p_m),
                "Saldo": f_money(max(0, saldo_i)),
                "Estatus": "✅" if p_m >= d['mensualidad']-1 else "❌"
            })
        st.dataframe(pd.DataFrame(tabla), use_container_width=True, hide_index=True)

# --- 3. COBRANZA ---
elif choice == "💸 Cobranza":
    st.header("💰 REGISTRO DE ABONOS")
    df_v = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote || ' (' || c.nombre || ')' as label FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN clientes c ON v.id_cliente = c.id", conn)
    if not df_v.empty:
        with st.form("f_c"):
            sel = st.selectbox("Seleccionar Cuenta", df_v['label'])
            monto = st.number_input("Monto ($)", min_value=0.0)
            fec = st.date_input("Fecha")
            if st.form_submit_button("REGISTRAR PAGO"):
                id_v = int(df_v[df_v['label'] == sel]['id'].values[0])
                c.execute("INSERT INTO pagos (id_venta, monto, fecha) VALUES (?,?,?)", (id_v, monto, fec.strftime('%Y-%m-%d')))
                conn.commit(); st.success("Guardado!"); st.rerun()

# --- 4. GESTIÓN DE VENTAS ---
elif choice == "📈 Gestión de Ventas":
    st.header("📈 CANCELACIONES")
    df_g = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u, c.nombre, v.id_terreno FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id", conn)
    if not df_g.empty:
        sel = st.selectbox("Venta a cancelar:", df_g['u'] + " - " + df_g['nombre'])
        if st.button("🚨 ELIMINAR VENTA"):
            row = df_g[df_g['u'] + " - " + df_g['nombre'] == sel].iloc[0]
            c.execute("DELETE FROM ventas WHERE id=?", (int(row['id']),))
            c.execute("UPDATE terrenos SET estatus='Disponible' WHERE id=?", (int(row['id_terreno']),))
            conn.commit(); st.rerun()

# --- 5. NUEVA VENTA ---
elif choice == "📝 Nueva Venta":
    st.header("📝 NUEVO CONTRATO")
    lt = pd.read_sql_query("SELECT * FROM terrenos WHERE estatus='Disponible'", conn)
    cl = pd.read_sql_query("SELECT * FROM clientes", conn)
    vn = pd.read_sql_query("SELECT * FROM vendedores", conn)
    if lt.empty: st.warning("No hay lotes disponibles.")
    else:
        with st.form("f_v"):
            s_lt = st.selectbox("Lote", lt['manzana'] + "-" + lt['lote'])
            s_cl = st.selectbox("Cliente", cl['nombre'])
            s_vn = st.selectbox("Vendedor", vn['nombre'])
            eng = st.number_input("Enganche", min_value=0.0)
            plz = st.number_input("Plazo (Meses)", min_value=1, value=48)
            fec = st.date_input("Fecha")
            if st.form_submit_button("REGISTRAR VENTA"):
                id_l = int(lt[lt['manzana'] + "-" + lt['lote'] == s_lt]['id'].values[0])
                id_c = int(cl[cl['nombre'] == s_cl]['id'].values[0])
                id_v = int(vn[vn['nombre'] == s_vn]['id'].values[0])
                costo = float(lt[lt['id'] == id_l]['costo'].values[0])
                mens = (costo - eng) / plz
                c.execute("INSERT INTO ventas (id_terreno, id_cliente, id_vendedor, enganche, meses, mensualidad, fecha) VALUES (?,?,?,?,?,?,?)", (id_l, id_c, id_v, eng, plz, mens, fec.strftime('%Y-%m-%d')))
                c.execute("UPDATE terrenos SET estatus='Vendido' WHERE id=?", (id_l,))
                conn.commit(); st.rerun()

# --- 6. CATÁLOGO TERRENOS ---
elif choice == "🏗️ Catálogo Terrenos":
    st.header("🏗️ GESTIÓN DE LOTES")
    with st.form("f_t"):
        c1, c2, c3 = st.columns(3)
        m = c1.text_input("Manzana")
        l = c2.text_input("Lote")
        p = c3.number_input("Precio", min_value=0.0)
        if st.form_submit_button("Añadir"):
            c.execute("INSERT INTO terrenos (manzana, lote, costo) VALUES (?,?,?)", (m, l, p))
            conn.commit(); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT * FROM terrenos", conn), use_container_width=True)

# --- 7. CLIENTES/VENDEDORES ---
elif choice == "👥 Clientes/Vendedores":
    st.header("👥 DIRECTORIO")
    c1, c2 = st.columns(2)
    with c1:
        with st.form("f_cli"):
            n = st.text_input("Nuevo Cliente")
            if st.form_submit_button("Guardar"):
                c.execute("INSERT INTO clientes (nombre) VALUES (?)", (n,))
                conn.commit(); st.rerun()
        st.write(pd.read_sql_query("SELECT nombre FROM clientes", conn))
    with c2:
        with st.form("f_ven"):
            n = st.text_input("Nuevo Vendedor")
            if st.form_submit_button("Guardar"):
                c.execute("INSERT INTO vendedores (nombre) VALUES (?)", (n,))
                conn.commit(); st.rerun()
        st.write(pd.read_sql_query("SELECT nombre FROM vendedores", conn))
