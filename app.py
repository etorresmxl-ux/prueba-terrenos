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

# --- MANEJO DE ESTADO DE NAVEGACIÓN ---
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

if st.session_state['lote_seleccionado']:
    default_index = 1
else:
    default_index = 0

choice = st.sidebar.radio("Seleccione una opción:", menu, index=default_index)

# --- 1. RESUMEN DE CARTERA ---
if choice == "🏠 Resumen de Cartera":
    st.header("📋 ESTADO DE CUENTA GENERAL")
    st.info("💡 Haz clic en cualquier fila para abrir el detalle de ese lote automáticamente.")
    
    query = '''
        SELECT v.id as id_venta, 'M'||t.manzana||'-L'||t.lote as ubicacion, c.nombre as cliente, 
        t.costo as costo_total, v.enganche, v.fecha as fecha_contrato, v.mensualidad,
        IFNULL((SELECT SUM(monto) FROM pagos WHERE id_venta = v.id), 0) as suma_pagos,
        (SELECT MAX(fecha) FROM pagos WHERE id_venta = v.id) as ultimo_pago_f
        FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id
    '''
    df_raw = pd.read_sql_query(query, conn)
    
    if df_raw.empty:
        st.warning("No hay ventas registradas.")
    else:
        res = []
        for _, r in df_raw.iterrows():
            total_pagado = (r['enganche'] or 0) + (r['suma_pagos'] or 0)
            saldo_hoy = (r['costo_total'] or 0) - total_pagado
            f_con = datetime.strptime(r['fecha_contrato'], '%Y-%m-%d')
            
            # Cálculo de meses que deberían estar pagados
            m_deb = ((hoy_dt.year - f_con.year) * 12 + (hoy_dt.month - f_con.month)) - (1 if hoy_dt.day < f_con.day else 0)
            atr_m = max(0, (m_deb * (r['mensualidad'] or 0)) - (r['suma_pagos'] or 0))
            
            # CORRECCIÓN DEL ERROR DE FECHA
            d_atr = 0
            if atr_m > 10:
                ref_str = r['ultimo_pago_f'] if r['ultimo_pago_f'] else r['fecha_contrato']
                ref_dt = datetime.strptime(ref_str, '%Y-%m-%d')
                d_atr = (hoy_dt - ref_dt).days - 30 # Aproximación de días después del último mes pagado
            
            res.append({
                "Ubicación": r['ubicacion'], "Cliente": r['cliente'], "Costo": f_money(r['costo_total']),
                "Pagado": f_money(total_pagado), "Saldo": f_money(saldo_hoy),
                "Estatus": "✅ AL CORRIENTE" if atr_m <= 10 else "⚠️ MOROSO",
                "Días Atraso": max(0, d_atr), "Monto Atraso": f_money(atr_m)
            })

        df_final = pd.DataFrame(res)
        seleccion = st.dataframe(df_final, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single_row")

        if len(seleccion.selection.rows) > 0:
            idx = seleccion.selection.rows[0]
            st.session_state['lote_seleccionado'] = df_final.iloc[idx]['Ubicación']
            st.rerun()

# --- 2. DETALLE POR LOTE ---
elif choice == "🔍 Detalle por Lote":
    st.header("🔍 ESTADO DE CUENTA DETALLADO")
    df_u = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u FROM ventas v JOIN terrenos t ON v.id_terreno = t.id", conn)
    
    if df_u.empty:
        st.info("No hay ventas para mostrar detalle.")
    else:
        lista_u = sorted(df_u['u'].tolist())
        idx_ini = lista_u.index(st.session_state['lote_seleccionado']) if st.session_state['lote_seleccionado'] in lista_u else 0
        
        col_sel, col_btn = st.columns([3, 1])
        lote_sel = col_sel.selectbox("Ubicación:", lista_u, index=idx_ini)
        
        if col_btn.button("⬅️ Volver al Resumen"):
            st.session_state['lote_seleccionado'] = None
            st.rerun()

        id_v = int(df_u[df_u['u'] == lote_sel]['id'].values[0])
        q = f"SELECT c.nombre, t.costo, v.enganche, v.fecha, v.meses, v.mensualidad FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id WHERE v.id = {id_v}"
        d = pd.read_sql_query(q, conn).iloc[0]
        pagos_suma = pd.read_sql_query(f"SELECT SUM(monto) as s FROM pagos WHERE id_venta = {id_v}", conn)['s'].iloc[0] or 0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Cliente", d['nombre'])
        c2.metric("Valor Terreno", f_money(d['costo']))
        c3.metric("Pagado Total", f_money(d['enganche'] + pagos_suma))
        c4.metric("Saldo Pendiente", f_money(d['costo'] - (d['enganche'] + pagos_suma)))

        st.subheader("📅 Plan de Pagos")
        tabla = []
        saldo_i = d['costo'] - d['enganche']
        f_pago = datetime.strptime(d['fecha'], '%Y-%m-%d')
        acum = pagos_suma
        for i in range(1, int(d['meses']) + 1):
            # Usamos un método de suma de meses más simple para evitar el error anterior
            nueva_mes = (f_pago.month % 12) + 1
            nueva_year = f_pago.year + (1 if f_pago.month == 12 else 0)
            f_pago = f_pago.replace(month=nueva_mes, year=nueva_year)
            
            pago_mes = min(d['mensualidad'], acum)
            acum -= pago_mes
            saldo_i -= pago_mes
            tabla.append({
                "Mes": i, "Fecha": f_pago.strftime('%d/%m/%Y'),
                "Cuota": f_money(d['mensualidad']), "Abonado": f_money(pago_mes),
                "Saldo": f_money(max(0, saldo_i)),
                "Estatus": "✅ PAGADO" if pago_mes >= d['mensualidad']-1 else "❌ PENDIENTE"
            })
        st.dataframe(pd.DataFrame(tabla), use_container_width=True, hide_index=True)

# (Siguen las demás secciones igual: Cobranza, Nueva Venta, etc.)
elif choice == "💸 Cobranza":
    st.header("💰 REGISTRO DE ABONOS")
    df_v = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote || ' (' || c.nombre || ')' as label FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN clientes c ON v.id_cliente = c.id", conn)
    if not df_v.empty:
        with st.form("f_cobro"):
            sel = st.selectbox("Seleccionar Cuenta", df_v['label'])
            monto = st.number_input("Monto del Abono ($)", min_value=0.0)
            fecha = st.date_input("Fecha de Pago")
            if st.form_submit_button("REGISTRAR"):
                id_v = int(df_v[df_v['label'] == sel]['id'].values[0])
                c.execute("INSERT INTO pagos (id_venta, monto, fecha) VALUES (?,?,?)", (id_v, monto, fecha.strftime('%Y-%m-%d')))
                conn.commit(); st.success("Pago registrado"); st.rerun()

elif choice == "📈 Gestión de Ventas":
    st.header("📈 ADMINISTRAR VENTAS")
    df_g = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u, c.nombre, v.id_terreno FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id", conn)
    if not df_g.empty:
        sel = st.selectbox("Venta a cancelar:", df_g['u'] + " - " + df_g['nombre'])
        if st.button("⚠️ CANCELAR VENTA"):
            row = df_g[df_g['u'] + " - " + df_g['nombre'] == sel].iloc[0]
            c.execute("DELETE FROM ventas WHERE id=?", (int(row['id']),))
            c.execute("UPDATE terrenos SET estatus='Disponible' WHERE id=?", (int(row['id_terreno']),))
            conn.commit(); st.rerun()

elif choice == "📝 Nueva Venta":
    st.header("📝 REGISTRAR VENTA")
    lt = pd.read_sql_query("SELECT * FROM terrenos WHERE estatus='Disponible'", conn)
    cl = pd.read_sql_query("SELECT * FROM clientes", conn)
    vn = pd.read_sql_query("SELECT * FROM vendedores", conn)
    if lt.empty: st.warning("No hay terrenos disponibles.")
    else:
        with st.form("f_venta"):
            s_lt = st.selectbox("Lote", lt['manzana'] + "-" + lt['lote'])
            s_cl = st.selectbox("Cliente", cl['nombre'])
            s_vn = st.selectbox("Vendedor", vn['nombre'])
            eng = st.number_input("Enganche", min_value=0.0)
            plz = st.number_input("Plazo (Meses)", min_value=1, value=48)
            fec = st.date_input("Fecha")
            if st.form_submit_button("CREAR CONTRATO"):
                id_l = int(lt[lt['manzana'] + "-" + lt['lote'] == s_lt]['id'].values[0])
                id_c = int(cl[cl['nombre'] == s_cl]['id'].values[0])
                id_v = int(vn[vn['nombre'] == s_vn]['id'].values[0])
                costo = float(lt[lt['id'] == id_l]['costo'].values[0])
                mens = (costo - eng) / plz
                c.execute("INSERT INTO ventas (id_terreno, id_cliente, id_vendedor, enganche, meses, mensualidad, fecha) VALUES (?,?,?,?,?,?,?)", (id_l, id_c, id_v, eng, plz, mens, fec.strftime('%Y-%m-%d')))
                c.execute("UPDATE terrenos SET estatus='Vendido' WHERE id=?", (id_l,))
                conn.commit(); st.rerun()

elif choice == "🏗️ Catálogo Terrenos":
    st.header("🏗️ CATÁLOGO")
    with st.form("f_t"):
        c1, c2, c3 = st.columns(3)
        m = c1.text_input("Manzana")
        l = c2.text_input("Lote")
        p = c3.number_input("Precio Total", min_value=0.0)
        if st.form_submit_button("Añadir"):
            c.execute("INSERT INTO terrenos (manzana, lote, costo) VALUES (?,?,?)", (m, l, p))
            conn.commit(); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT * FROM terrenos", conn), use_container_width=True, hide_index=True)

elif choice == "👥 Clientes/Vendedores":
    st.header("👥 REGISTROS")
    col1, col2 = st.columns(2)
    with col1:
        with st.form("f_c"):
            nom = st.text_input("Nuevo Cliente")
            if st.form_submit_button("Registrar Cliente"):
                c.execute("INSERT INTO clientes (nombre) VALUES (?)", (nom,))
                conn.commit(); st.rerun()
        st.write(pd.read_sql_query("SELECT nombre FROM clientes", conn))
    with col2:
        with st.form("f_v"):
            nom = st.text_input("Nuevo Vendedor")
            if st.form_submit_button("Registrar Vendedor"):
                c.execute("INSERT INTO vendedores (nombre) VALUES (?)", (nom,))
                conn.commit(); st.rerun()
        st.write(pd.read_sql_query("SELECT nombre FROM vendedores", conn))
