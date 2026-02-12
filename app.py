import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sistema Inmobiliario Pro", layout="wide")

# --- SEGURIDAD ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "Terrenos2026":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.text_input("Clave de acceso", type="password", on_change=password_entered, key="password")
        return False
    return st.session_state.get("password_correct", False)

if not check_password():
    st.stop()

# --- BASE DE DATOS ---
conn = sqlite3.connect('inmobiliaria.db', check_same_thread=False)
c = conn.cursor()

# Crear tablas incluyendo Comisiones
c.execute('CREATE TABLE IF NOT EXISTS terrenos (id INTEGER PRIMARY KEY AUTOINCREMENT, manzana TEXT, lote TEXT, costo REAL, estatus TEXT DEFAULT "Disponible")')
c.execute('CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS vendedores (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT)')
c.execute('''CREATE TABLE IF NOT EXISTS ventas 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, id_terreno INTEGER, id_cliente INTEGER, 
              id_vendedor INTEGER, enganche REAL, meses INTEGER, mensualidad REAL, 
              fecha TEXT, comision_total REAL)''')
c.execute('CREATE TABLE IF NOT EXISTS pagos (id INTEGER PRIMARY KEY AUTOINCREMENT, id_venta INTEGER, monto REAL, fecha TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS pagos_comisiones (id INTEGER PRIMARY KEY AUTOINCREMENT, id_venta INTEGER, monto_pagado REAL, fecha TEXT)')
conn.commit()

# --- FORMATOS ---
def f_money(v): return f"${float(v or 0):,.2f}"
def f_date(s): 
    try: return datetime.strptime(s, '%Y-%m-%d').strftime('%d-%m-%Y')
    except: return s

# --- MENÚ ---
menu = ["🏠 Cartera", "📊 Reportes", "💸 Cobranza Clientes", "🤝 Comisiones Vendedores", "📝 Nueva Venta", "🏗️ Inventario", "👥 Directorio"]
choice = st.sidebar.radio("Menú", menu)

# --- 1. CARTERA (FECHA DD-MM-AAAA) ---
if choice == "🏠 Cartera":
    st.header("📋 ESTADO DE CUENTA GENERAL")
    df = pd.read_sql_query('''
        SELECT v.id, 'M'||t.manzana||'-L'||t.lote as Lote, c.nombre as Cliente, 
        t.costo, v.enganche, v.fecha, 
        IFNULL((SELECT SUM(monto) FROM pagos WHERE id_venta = v.id), 0) as pagos
        FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id
    ''', conn)
    if not df.empty:
        df['Contrato'] = df['fecha'].apply(f_date)
        df['Pagado'] = (df['enganche'] + df['pagos']).apply(f_money)
        df['Saldo'] = (df['costo'] - (df['enganche'] + df['pagos'])).apply(f_money)
        st.dataframe(df[['Lote', 'Cliente', 'Contrato', 'Pagado', 'Saldo']], use_container_width=True, hide_index=True)

# --- 2. REPORTES (USANDO GRÁFICO NATIVO) ---
elif choice == "📊 Reportes":
    st.header("📊 RESUMEN DE VENTAS")
    df_v = pd.read_sql_query('''
        SELECT vn.nombre as Vendedor, SUM(t.costo) as Total_Vendido, SUM(v.comision_total) as Total_Comisiones
        FROM ventas v JOIN vendedores vn ON v.id_vendedor = vn.id JOIN terrenos t ON v.id_terreno = t.id
        GROUP BY vn.nombre
    ''', conn)
    if not df_v.empty:
        st.subheader("Ventas por Vendedor ($)")
        st.bar_chart(data=df_v, x="Vendedor", y="Total_Vendido")
        st.subheader("Comisiones Generadas por Vendedor ($)")
        st.area_chart(data=df_v, x="Vendedor", y="Total_Comisiones")

# --- 4. PAGO DE COMISIONES (NUEVA SECCIÓN) ---
elif choice == "🤝 Comisiones Vendedores":
    st.header("🤝 CONTROL DE COMISIONES")
    df_c = pd.read_sql_query('''
        SELECT v.id, 'M'||t.manzana||'-L'||t.lote as Lote, vn.nombre as Vendedor, v.comision_total,
        IFNULL((SELECT SUM(monto_pagado) FROM pagos_comisiones WHERE id_venta = v.id), 0) as pagado
        FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN vendedores vn ON v.id_vendedor = vn.id
    ''', conn)
    if not df_c.empty:
        df_c['Pendiente'] = df_c['comision_total'] - df_c['pagado']
        # Mostrar tabla
        view = df_c.copy()
        view['Total'] = view['comision_total'].apply(f_money)
        view['Pagado'] = view['pagado'].apply(f_money)
        view['Saldo'] = view['Pendiente'].apply(f_money)
        st.dataframe(view[['Lote', 'Vendedor', 'Total', 'Pagado', 'Saldo']], use_container_width=True, hide_index=True)
        
        with st.form("pago_v"):
            sel = st.selectbox("Lote a pagar:", df_c[df_c['Pendiente']>0]['Lote'] + " (" + df_c['Vendedor'] + ")")
            monto = st.number_input("Monto a pagar al vendedor ($)", min_value=0.0)
            if st.form_submit_button("REGISTRAR PAGO"):
                id_v = int(df_c[df_c['Lote'] + " (" + df_c['Vendedor'] + ")" == sel]['id'].values[0])
                c.execute("INSERT INTO pagos_comisiones (id_venta, monto_pagado, fecha) VALUES (?,?,?)", 
                          (id_v, monto, datetime.now().strftime('%Y-%m-%d')))
                conn.commit(); st.success("Pago guardado"); st.rerun()

# --- 5. NUEVA VENTA (CON COMISIÓN) ---
elif choice == "📝 Nueva Venta":
    st.header("📝 REGISTRAR VENTA")
    lt = pd.read_sql_query("SELECT * FROM terrenos WHERE estatus='Disponible'", conn)
    cl = pd.read_sql_query("SELECT * FROM clientes", conn)
    vn = pd.read_sql_query("SELECT * FROM vendedores", conn)
    if lt.empty: st.warning("No hay lotes libres.")
    else:
        with st.form("v"):
            c1, c2 = st.columns(2)
            lote = c1.selectbox("Lote:", lt['manzana'] + "-" + lt['lote'])
            cli = c1.selectbox("Cliente:", cl['nombre'])
            ven = c1.selectbox("Vendedor:", vn['nombre'])
            fec = c1.date_input("Fecha")
            eng = c2.number_input("Enganche ($)", min_value=0.0)
            plz = c2.number_input("Meses", min_value=1, value=48)
            com = c2.number_input("Comisión acordada ($)", min_value=0.0)
            if st.form_submit_button("GUARDAR"):
                id_l = int(lt[lt['manzana'] + "-" + lt['lote'] == lote]['id'].values[0])
                id_c = int(cl[cl['nombre'] == cli]['id'].values[0])
                id_v = int(vn[vn['nombre'] == ven]['id'].values[0])
                costo = float(lt[lt['id'] == id_l]['costo'].values[0])
                mens = (costo - eng) / plz
                c.execute("INSERT INTO ventas (id_terreno, id_cliente, id_vendedor, enganche, meses, mensualidad, fecha, comision_total) VALUES (?,?,?,?,?,?,?,?)", 
                          (id_l, id_c, id_v, eng, plz, mens, fec.strftime('%Y-%m-%d'), com))
                c.execute("UPDATE terrenos SET estatus='Vendido' WHERE id=?", (id_l,))
                conn.commit(); st.success("Venta exitosa"); st.rerun()

# --- SECCIONES RESTANTES ---
elif choice == "💸 Cobranza Clientes":
    st.header("💰 ABONOS")
    df_v = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote || ' - ' || c.nombre as l FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN clientes c ON v.id_cliente = c.id", conn)
    if not df_v.empty:
        with st.form("p"):
            s = st.selectbox("Lote:", df_v['l'])
            m = st.number_input("Monto:", min_value=0.0)
            if st.form_submit_button("REGISTRAR ABONO"):
                id_v = int(df_v[df_v['l'] == s]['id'].values[0])
                c.execute("INSERT INTO pagos (id_venta, monto, fecha) VALUES (?,?,?)", (id_v, m, datetime.now().strftime('%Y-%m-%d')))
                conn.commit(); st.rerun()

elif choice == "🏗️ Inventario":
    st.header("🏗️ LOTES")
    with st.form("t"):
        m, l, p = st.columns(3)
        man = m.text_input("Manzana")
        lot = l.text_input("Lote")
        pre = p.number_input("Precio", min_value=0.0)
        if st.form_submit_button("Añadir"):
            c.execute("INSERT INTO terrenos (manzana, lote, costo) VALUES (?,?,?)", (man, lot, pre))
            conn.commit(); st.rerun()
    st.write(pd.read_sql_query("SELECT * FROM terrenos", conn))

elif choice == "👥 Directorio":
    st.header("👥 REGISTROS")
    c1, c2 = st.columns(2)
    with c1:
        n_c = st.text_input("Nuevo Cliente")
        if st.button("Guardar Cliente"):
            c.execute("INSERT INTO clientes (nombre) VALUES (?)", (n_c,))
            conn.commit(); st.rerun()
    with c2:
        n_v = st.text_input("Nuevo Vendedor")
        if st.button("Guardar Vendedor"):
            c.execute("INSERT INTO vendedores (nombre) VALUES (?)", (n_v,))
            conn.commit(); st.rerun()
