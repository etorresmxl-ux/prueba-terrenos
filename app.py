import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Inmobiliaria Pro v22", layout="wide")

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
    return st.session_state.get("password_correct", False)

if not check_password():
    st.stop()

# --- CONEXIÓN A BASE DE DATOS ---
conn = sqlite3.connect('inmobiliaria.db', check_same_thread=False)
c = conn.cursor()

# Tablas base
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

# --- FUNCIONES DE FORMATO ---
def f_money(v): 
    return f"${float(v or 0):,.2f}"

def f_date_show(fecha_str):
    """Convierte AAAA-MM-DD (DB) a DD-MM-AAAA (Vista)"""
    try:
        return datetime.strptime(fecha_str, '%Y-%m-%d').strftime('%d-%m-%Y')
    except:
        return fecha_str

# --- MENÚ LATERAL ---
st.sidebar.markdown("### 📊 **REPORTES**")
menu_rep = ["🏠 Resumen de Cartera", "🤝 Comisiones", "📈 Gráficos"]
st.sidebar.markdown("---")
st.sidebar.markdown("### 🚀 **OPERACIONES**")
menu_ops = ["📝 Nueva Venta", "💸 Cobranza Clientes", "🔍 Detalle por Lote", "⚙️ Gestión de Contratos", "🏗️ Catálogo", "👥 Directorio"]

choice = st.sidebar.radio("Seleccione:", menu_rep + menu_ops)

# --- 1. RESUMEN DE CARTERA (FECHA DD-MM-AAAA) ---
if choice == "🏠 Resumen de Cartera":
    st.header("📋 ESTADO DE CUENTA GENERAL")
    query = '''
        SELECT v.id, 'M'||t.manzana||'-L'||t.lote as Lote, c.nombre as Cliente, 
        t.costo as [Valor Venta], v.enganche as Enganche, v.fecha, 
        IFNULL((SELECT SUM(monto) FROM pagos WHERE id_venta = v.id), 0) as pagos_abonos
        FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id
    '''
    df = pd.read_sql_query(query, conn)
    if not df.empty:
        # Aplicar formatos de moneda y fecha
        df['Contrato'] = df['fecha'].apply(f_date_show)
        df['Total Pagado'] = (df['Enganche'] + df['pagos_abonos']).apply(f_money)
        df['Saldo Hoy'] = (df['Valor Venta'] - (df['Enganche'] + df['pagos_abonos'])).apply(f_money)
        df['Valor Venta'] = df['Valor Venta'].apply(f_money)
        df['Enganche'] = df['Enganche'].apply(f_money)
        
        # Mostrar tabla limpia
        st.dataframe(df[['Lote', 'Cliente', 'Valor Venta', 'Enganche', 'Contrato', 'Total Pagado', 'Saldo Hoy']], use_container_width=True, hide_index=True)
    else:
        st.info("No hay ventas registradas.")

# --- 2. NUEVA VENTA (VALOR $ EN INPUTS) ---
elif choice == "📝 Nueva Venta":
    st.header("📝 REGISTRAR NUEVO CONTRATO")
    lt = pd.read_sql_query("SELECT * FROM terrenos WHERE estatus='Disponible'", conn)
    cl = pd.read_sql_query("SELECT * FROM clientes", conn)
    vn = pd.read_sql_query("SELECT * FROM vendedores", conn)
    
    if lt.empty:
        st.warning("No hay terrenos disponibles.")
    else:
        with st.form("nv"):
            col1, col2 = st.columns(2)
            l_sel = col1.selectbox("Seleccione Lote:", lt['manzana'] + "-" + lt['lote'])
            c_sel = col1.selectbox("Cliente:", cl['nombre'])
            v_sel = col1.selectbox("Vendedor:", vn['nombre'])
            f_cont = col1.date_input("Fecha de Contrato", datetime.now())
            
            p_cat = float(lt[lt['manzana'] + "-" + lt['lote'] == l_sel]['costo'].values[0])
            
            # Formato moneda en inputs mediante label o prefijo
            costo_v = col2.number_input("Valor de Venta Real ($)", min_value=0.0, value=p_cat, format="%.2f")
            eng_v = col2.number_input("Enganche Recibido ($)", min_value=0.0, format="%.2f")
            plz_v = col2.number_input("Plazo (Meses)", min_value=1, value=48)
            com_v = col2.number_input("Comisión del Vendedor ($)", min_value=0.0, format="%.2f")
            
            if st.form_submit_button("CERRAR VENTA Y GENERAR DEUDA"):
                id_l = int(lt[lt['manzana'] + "-" + lt['lote'] == l_sel]['id'].values[0])
                id_c = int(cl[cl['nombre'] == c_sel]['id'].values[0])
                id_v = int(vn[vn['nombre'] == v_sel]['id'].values[0])
                mensu = (costo_v - eng_v) / plz_v
                
                c.execute('''INSERT INTO ventas (id_terreno, id_cliente, id_vendedor, enganche, meses, mensualidad, fecha, comision_total) 
                             VALUES (?,?,?,?,?,?,?,?)''', 
                          (id_l, id_c, id_v, eng_v, plz_v, mensu, f_cont.strftime('%Y-%m-%d'), com_v))
                c.execute("UPDATE terrenos SET estatus='Vendido', costo=? WHERE id=?", (costo_v, id_l))
                conn.commit()
                st.success("Contrato guardado correctamente.")
                st.rerun()

# --- SECCIONES RESTANTES CON FORMATOS ---
elif choice == "🤝 Comisiones":
    st.header("🤝 COMISIONES")
    df_c = pd.read_sql_query('''
        SELECT v.id, 'M'||t.manzana||'-L'||t.lote as Lote, vn.nombre as Vendedor, v.comision_total as Total,
        IFNULL((SELECT SUM(monto_pagado) FROM pagos_comisiones WHERE id_venta = v.id), 0) as Pagado
        FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN vendedores vn ON v.id_vendedor = vn.id
    ''', conn)
    if not df_c.empty:
        df_c['Pendiente'] = df_c['Total'] - df_c['Pagado']
        df_c['Total'] = df_c['Total'].apply(f_money)
        df_c['Pagado'] = df_c['Pagado'].apply(f_money)
        df_c['Pendiente'] = df_c['Pendiente'].apply(f_money)
        st.dataframe(df_c[['Lote', 'Vendedor', 'Total', 'Pagado', 'Pendiente']], use_container_width=True, hide_index=True)

elif choice == "💸 Cobranza Clientes":
    st.header("💸 COBRANZA")
    df_v = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote || ' - ' || c.nombre as l FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN clientes c ON v.id_cliente = c.id", conn)
    if not df_v.empty:
        with st.form("cob"):
            s = st.selectbox("Contrato:", df_v['l'])
            m = st.number_input("Monto a abonar ($)", min_value=0.0, format="%.2f")
            if st.form_submit_button("REGISTRAR PAGO"):
                id_v = int(df_v[df_v['l'] == s]['id'].values[0])
                c.execute("INSERT INTO pagos (id_venta, monto, fecha) VALUES (?,?,?)", (id_v, m, datetime.now().strftime('%Y-%m-%d')))
                conn.commit(); st.rerun()

elif choice == "🔍 Detalle por Lote":
    st.header("🔍 AMORTIZACIÓN")
    df_u = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u FROM ventas v JOIN terrenos t ON v.id_terreno = t.id", conn)
    if not df_u.empty:
        sel_u = st.selectbox("Seleccione Lote:", df_u['u'])
        vid = int(df_u[df_u['u'] == sel_u]['id'].values[0])
        res = pd.read_sql_query(f"SELECT c.nombre, t.costo, v.enganche, v.fecha, v.meses, v.mensualidad FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id WHERE v.id = {vid}", conn).iloc[0]
        st.write(f"**Cliente:** {res['nombre']} | **Costo:** {f_money(res['costo'])}")
        st.write(f"**Fecha Venta:** {f_date_show(res['fecha'])} | **Mensualidad:** {f_money(res['mensualidad'])}")

elif choice == "⚙️ Gestión de Contratos":
    st.header("⚙️ ADMINISTRACIÓN")
    df_g = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u, c.nombre as cli, v.id_terreno FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id", conn)
    if not df_g.empty:
        sel = st.selectbox("Eliminar:", df_g['u'] + " - " + df_g['cli'])
        if st.button("BORRAR CONTRATO Y LIBERAR TERRENO"):
            id_ven = int(df_g[df_g['u'] + " - " + df_g['cli'] == sel]['id'].values[0])
            id_ter = int(df_g[df_g['u'] + " - " + df_g['cli'] == sel]['id_terreno'].values[0])
            c.execute("DELETE FROM ventas WHERE id=?", (id_ven,))
            c.execute("UPDATE terrenos SET estatus='Disponible' WHERE id=?", (id_ter,))
            conn.commit(); st.rerun()

elif choice == "🏗️ Catálogo":
    st.header("🏗️ CATÁLOGO")
    with st.form("cat"):
        m_c = st.text_input("Manzana")
        l_c = st.text_input("Lote")
        p_c = st.number_input("Precio Lista ($)", min_value=0.0, format="%.2f")
        if st.form_submit_button("Añadir"):
            c.execute("INSERT INTO terrenos (manzana, lote, costo) VALUES (?,?,?)", (m_c, l_c, p_c))
            conn.commit(); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT * FROM terrenos", conn), use_container_width=True)

elif choice == "👥 Directorio":
    st.header("👥 REGISTROS")
    c1, c2 = st.columns(2)
    with c1:
        n_c = st.text_input("Nombre Cliente")
        if st.button("Guardar Cliente"):
            c.execute("INSERT INTO clientes (nombre) VALUES (?)", (n_c,))
            conn.commit(); st.rerun()
    with c2:
        n_v = st.text_input("Nombre Vendedor")
        if st.button("Guardar Vendedor"):
            c.execute("INSERT INTO vendedores (nombre) VALUES (?)", (n_v,))
            conn.commit(); st.rerun()

elif choice == "📈 Gráficos":
    st.header("📈 VENTAS")
    df_g = pd.read_sql_query('''SELECT vn.nombre as Vendedor, SUM(t.costo) as Total FROM ventas v JOIN vendedores vn ON v.id_vendedor = vn.id JOIN terrenos t ON v.id_terreno = t.id GROUP BY vn.nombre''', conn)
    if not df_g.empty:
        st.bar_chart(data=df_g, x="Vendedor", y="Total")
