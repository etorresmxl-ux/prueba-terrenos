import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Inmobiliaria Pro v21.1", layout="wide")

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

# Asegurar que todas las tablas existan con las columnas necesarias
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
def f_money(v): return f"${float(v or 0):,.2f}"
def f_date(s): 
    try: return datetime.strptime(s, '%Y-%m-%d').strftime('%d-%m-%Y')
    except: return s

# --- MENÚ LATERAL SEGMENTADO ---
st.sidebar.markdown("### 📊 **REPORTES Y SALDOS**")
menu_rep = ["🏠 Resumen de Cartera", "🤝 Comisiones", "📈 Gráficos"]

st.sidebar.markdown("---")
st.sidebar.markdown("### 🚀 **OPERACIONES / VENTAS**")
menu_ops = ["📝 Nueva Venta", "💸 Cobranza Clientes", "🔍 Detalle por Lote", "⚙️ Gestión de Contratos", "🏗️ Catálogo de Lotes", "👥 Directorio"]

# Unificamos para la navegación, pero el usuario los ve separados
choice = st.sidebar.radio("Seleccione una sección:", menu_rep + menu_ops)

# --- 1. RESUMEN DE CARTERA ---
if choice == "🏠 Resumen de Cartera":
    st.header("📋 ESTADO DE CUENTA GENERAL")
    df = pd.read_sql_query('''
        SELECT v.id, 'M'||t.manzana||'-L'||t.lote as Lote, c.nombre as Cliente, 
        t.costo, v.enganche, v.fecha, 
        IFNULL((SELECT SUM(monto) FROM pagos WHERE id_venta = v.id), 0) as pagos
        FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id
    ''', conn)
    if not df.empty:
        df['Contrato'] = df['fecha'].apply(f_date)
        df['Total Pagado'] = (df['enganche'] + df['pagos']).apply(f_money)
        df['Saldo Hoy'] = (df['costo'] - (df['enganche'] + df['pagos'])).apply(f_money)
        st.dataframe(df[['Lote', 'Cliente', 'Contrato', 'Total Pagado', 'Saldo Hoy']], use_container_width=True, hide_index=True)
    else:
        st.info("No hay ventas registradas aún.")

# --- 2. NUEVA VENTA ---
elif choice == "📝 Nueva Venta":
    st.header("📝 REGISTRAR NUEVO CONTRATO")
    lt = pd.read_sql_query("SELECT * FROM terrenos WHERE estatus='Disponible'", conn)
    cl = pd.read_sql_query("SELECT * FROM clientes", conn)
    vn = pd.read_sql_query("SELECT * FROM vendedores", conn)
    
    if lt.empty:
        st.warning("Debe añadir lotes disponibles en el Catálogo primero.")
    else:
        with st.form("form_v"):
            col1, col2 = st.columns(2)
            lote_txt = col1.selectbox("Seleccione Lote:", lt['manzana'] + "-" + lt['lote'])
            cli_txt = col1.selectbox("Cliente:", cl['nombre'])
            ven_txt = col1.selectbox("Vendedor:", vn['nombre'])
            f_v = col1.date_input("Fecha de hoy")
            
            # Recuperamos precio del catálogo para sugerirlo
            p_sug = float(lt[lt['manzana'] + "-" + lt['lote'] == lote_txt]['costo'].values[0])
            
            costo_v = col2.number_input("Valor de Venta Real ($):", min_value=0.0, value=p_sug)
            eng_v = col2.number_input("Enganche ($):", min_value=0.0)
            plz_v = col2.number_input("Plazo (Meses):", min_value=1, value=48)
            com_v = col2.number_input("Comisión Vendedor ($):", min_value=0.0)
            
            if st.form_submit_button("CERRAR VENTA"):
                id_l = int(lt[lt['manzana'] + "-" + lt['lote'] == lote_txt]['id'].values[0])
                id_c = int(cl[cl['nombre'] == cli_txt]['id'].values[0])
                id_v = int(vn[vn['nombre'] == ven_txt]['id'].values[0])
                m_mensual = (costo_v - eng_v) / plz_v
                
                c.execute('''INSERT INTO ventas (id_terreno, id_cliente, id_vendedor, enganche, meses, mensualidad, fecha, comision_total) 
                             VALUES (?,?,?,?,?,?,?,?)''', 
                          (id_l, id_c, id_v, eng_v, plz_v, m_mensual, f_v.strftime('%Y-%m-%d'), com_v))
                c.execute("UPDATE terrenos SET estatus='Vendido', costo=? WHERE id=?", (costo_v, id_l))
                conn.commit()
                st.success("¡Venta guardada exitosamente!")
                st.rerun()

# --- 3. COMISIONES ---
elif choice == "🤝 Comisiones":
    st.header("🤝 CONTROL DE COMISIONES")
    df_c = pd.read_sql_query('''
        SELECT v.id, 'M'||t.manzana||'-L'||t.lote as Lote, vn.nombre as Vendedor, v.comision_total as Total,
        IFNULL((SELECT SUM(monto_pagado) FROM pagos_comisiones WHERE id_venta = v.id), 0) as Pagado
        FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN vendedores vn ON v.id_vendedor = vn.id
    ''', conn)
    if not df_c.empty:
        df_c['Pendiente'] = df_c['Total'] - df_c['Pagado']
        st.dataframe(df_c[['Lote', 'Vendedor', 'Total', 'Pagado', 'Pendiente']].style.format({'Total': f_money, 'Pagado': f_money, 'Pendiente': f_money}), use_container_width=True)
        
        with st.expander("Registrar Pago a Vendedor"):
            sel = st.selectbox("Lote/Vendedor:", df_c[df_c['Pendiente']>0]['Lote'] + " (" + df_c['Vendedor'] + ")")
            m_p = st.number_input("Monto a pagar ahora ($):", min_value=0.0)
            if st.button("GUARDAR PAGO COMISIÓN"):
                id_v = int(df_c[df_c['Lote'] + " (" + df_c['Vendedor'] + ")" == sel]['id'].values[0])
                c.execute("INSERT INTO pagos_comisiones (id_venta, monto_pagado, fecha) VALUES (?,?,?)", (id_v, m_p, datetime.now().strftime('%Y-%m-%d')))
                conn.commit(); st.rerun()

# --- 4. COBRANZA ---
elif choice == "💸 Cobranza Clientes":
    st.header("💸 RECIBIR PAGOS DE CLIENTES")
    df_v = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote || ' - ' || c.nombre as l FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN clientes c ON v.id_cliente = c.id", conn)
    if not df_v.empty:
        with st.form("c"):
            s = st.selectbox("Contrato:", df_v['l'])
            m = st.number_input("Monto recibido ($):", min_value=0.0)
            if st.form_submit_button("REGISTRAR ABONO"):
                id_v = int(df_v[df_v['l'] == s]['id'].values[0])
                c.execute("INSERT INTO pagos (id_venta, monto, fecha) VALUES (?,?,?)", (id_v, m, datetime.now().strftime('%Y-%m-%d')))
                conn.commit(); st.success("Pago registrado"); st.rerun()

# --- 5. DETALLE POR LOTE ---
elif choice == "🔍 Detalle por Lote":
    st.header("🔍 DETALLE Y AMORTIZACIÓN")
    df_u = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u FROM ventas v JOIN terrenos t ON v.id_terreno = t.id", conn)
    if not df_u.empty:
        sel_u = st.selectbox("Ver Lote:", df_u['u'])
        vid = int(df_u[df_u['u'] == sel_u]['id'].values[0])
        det = pd.read_sql_query(f"SELECT c.nombre, t.costo, v.enganche, v.fecha, v.meses, v.mensualidad FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id WHERE v.id = {vid}", conn).iloc[0]
        
        st.write(f"### Cliente: {det['nombre']}")
        st.write(f"**Costo:** {f_money(det['costo'])} | **Fecha:** {f_date(det['fecha'])} | **Mensualidad:** {f_money(det['mensualidad'])}")
        
        # Tabla rápida
        tabla = []
        s_rest = det['costo'] - det['enganche']
        for i in range(1, 13): # Mostramos un año de ejemplo
            s_rest -= det['mensualidad']
            tabla.append({"Mes": i, "Cuota": f_money(det['mensualidad']), "Saldo Proyectado": f_money(max(0, s_rest))})
        st.table(tabla)

# --- 6. GESTIÓN DE CONTRATOS ---
elif choice == "⚙️ Gestión de Contratos":
    st.header("⚙️ ADMINISTRAR VENTAS ACTIVAS")
    df_g = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u, c.nombre as cli, v.id_terreno FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id", conn)
    if not df_g.empty:
        sel_can = st.selectbox("Contrato a eliminar:", df_g['u'] + " - " + df_g['cli'])
        if st.button("⚠️ ELIMINAR VENTA (LIBERAR LOTE)"):
            row = df_g[df_g['u'] + " - " + df_g['cli'] == sel_can].iloc[0]
            c.execute("DELETE FROM ventas WHERE id=?", (int(row['id']),))
            c.execute("UPDATE terrenos SET estatus='Disponible' WHERE id=?", (int(row['id_terreno']),))
            conn.commit(); st.rerun()

# --- 7. CATÁLOGO ---
elif choice == "🏗️ Catálogo de Lotes":
    st.header("🏗️ CATÁLOGO DE TERRENOS")
    with st.form("t"):
        m, l, p = st.columns(3)
        ma = m.text_input("Manzana")
        lo = l.text_input("Lote")
        pr = p.number_input("Precio Base ($)", min_value=0.0)
        if st.form_submit_button("Guardar Terreno"):
            c.execute("INSERT INTO terrenos (manzana, lote, costo) VALUES (?,?,?)", (ma, lo, pr))
            conn.commit(); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT manzana, lote, costo, estatus FROM terrenos", conn), use_container_width=True)

# --- 8. DIRECTORIO ---
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

# --- 9. GRÁFICOS ---
elif choice == "📈 Gráficos":
    st.header("📈 ESTADÍSTICAS")
    df_v = pd.read_sql_query('''SELECT vn.nombre as Vendedor, SUM(t.costo) as Ventas FROM ventas v JOIN vendedores vn ON v.id_vendedor = vn.id JOIN terrenos t ON v.id_terreno = t.id GROUP BY vn.nombre''', conn)
    if not df_v.empty:
        st.bar_chart(data=df_v, x="Vendedor", y="Ventas")
