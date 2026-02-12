import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px

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

# Actualización de tablas (Estructura robusta)
c.execute('CREATE TABLE IF NOT EXISTS terrenos (id INTEGER PRIMARY KEY AUTOINCREMENT, manzana TEXT, lote TEXT, costo REAL, estatus TEXT DEFAULT "Disponible")')
c.execute('CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS vendedores (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT)')
c.execute('''CREATE TABLE IF NOT EXISTS ventas 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, id_terreno INTEGER, id_cliente INTEGER, 
              id_vendedor INTEGER, enganche REAL, meses INTEGER, mensualidad REAL, 
              fecha TEXT, comision_total REAL)''')
c.execute('CREATE TABLE IF NOT EXISTS pagos (id INTEGER PRIMARY KEY AUTOINCREMENT, id_venta INTEGER, monto REAL, fecha TEXT)')
c.execute('''CREATE TABLE IF NOT EXISTS pagos_comisiones 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, id_venta INTEGER, monto_pagado REAL, fecha TEXT)''')
conn.commit()

# --- FUNCIONES DE FORMATO ---
def f_money(valor):
    try: return f"${float(valor or 0):,.2f}"
    except: return "$0.00"

def f_date_show(fecha_str):
    """Convierte AAAA-MM-DD a DD-MM-AAAA para visualización"""
    try:
        return datetime.strptime(fecha_str, '%Y-%m-%d').strftime('%d-%m-%Y')
    except:
        return fecha_str

# --- MENÚ LATERAL ---
st.sidebar.title("📑 NAVEGACIÓN")
menu = ["🏠 Resumen de Cartera", "📊 Reportes", "🔍 Detalle por Lote", "💸 Cobranza Clientes", "🤝 Pago Comisiones", "📈 Gestión de Ventas", "📝 Nueva Venta", "🏗️ Catálogo", "👥 Personal"]
choice = st.sidebar.radio("Seleccione una opción:", menu)

# --- 1. RESUMEN DE CARTERA ---
if choice == "🏠 Resumen de Cartera":
    st.header("📋 ESTADO DE CUENTA GENERAL")
    query = '''
        SELECT v.id as id_venta, 'M'||t.manzana||'-L'||t.lote as ubicacion, c.nombre as cliente, 
        t.costo as costo_total, v.enganche, v.fecha as fecha_contrato, v.mensualidad,
        IFNULL((SELECT SUM(monto) FROM pagos WHERE id_venta = v.id), 0) as suma_pagos
        FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id
    '''
    df_raw = pd.read_sql_query(query, conn)
    if df_raw.empty:
        st.warning("No hay ventas registradas.")
    else:
        res = []
        hoy_dt = datetime.now()
        for _, r in df_raw.iterrows():
            total_pagado = (r['enganche'] or 0) + (r['suma_pagos'] or 0)
            saldo_hoy = (r['costo_total'] or 0) - total_pagado
            f_con = datetime.strptime(r['fecha_contrato'], '%Y-%m-%d')
            m_deb = ((hoy_dt.year - f_con.year) * 12 + (hoy_dt.month - f_con.month)) - (1 if hoy_dt.day < f_con.day else 0)
            atr_m = max(0, (m_deb * (r['mensualidad'] or 0)) - (r['suma_pagos'] or 0))
            
            res.append({
                "Ubicación": r['ubicacion'], 
                "Cliente": r['cliente'], 
                "Fecha Contrato": f_date_show(r['fecha_contrato']),
                "Costo": f_money(r['costo_total']),
                "Total Pagado": f_money(total_pagado), 
                "Saldo Hoy": f_money(saldo_hoy),
                "Estatus": "✅ AL CORRIENTE" if atr_m <= 10 else "⚠️ MOROSO"
            })
        st.dataframe(pd.DataFrame(res), use_container_width=True, hide_index=True)

# --- 2. REPORTES (GRÁFICOS) ---
elif choice == "📊 Reportes":
    st.header("📊 RENDIMIENTO")
    df_v = pd.read_sql_query('''
        SELECT v.comision_total, vn.nombre as vendedor, t.costo 
        FROM ventas v 
        JOIN vendedores vn ON v.id_vendedor = vn.id
        JOIN terrenos t ON v.id_terreno = t.id
    ''', conn)
    
    if not df_v.empty:
        c1, c2 = st.columns(2)
        with c1:
            fig1 = px.pie(df_v, names='vendedor', values='costo', title="Ventas Totales por Vendedor")
            st.plotly_chart(fig1, use_container_width=True)
        with c2:
            fig2 = px.bar(df_v, x='vendedor', y='comision_total', title="Comisiones Generadas", color='vendedor')
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Sin datos para graficar.")

# --- 5. PAGO DE COMISIONES ---
elif choice == "🤝 Pago Comisiones":
    st.header("🤝 GESTIÓN DE COMISIONES")
    query = '''
        SELECT v.id as id_venta, 'M'||t.manzana||'-L'||t.lote as u, vn.nombre as vendedor, v.comision_total,
        IFNULL((SELECT SUM(monto_pagado) FROM pagos_comisiones WHERE id_venta = v.id), 0) as pagado
        FROM ventas v 
        JOIN terrenos t ON v.id_terreno = t.id 
        JOIN vendedores vn ON v.id_vendedor = vn.id
    '''
    df_com = pd.read_sql_query(query, conn)
    if not df_com.empty:
        df_com['Pendiente'] = df_com['comision_total'] - df_com['pagado']
        st.subheader("Saldos Pendientes")
        
        # Formatear tabla para vista
        view_df = df_com.copy()
        view_df['Comisión Total'] = view_df['comision_total'].apply(f_money)
        view_df['Pagado'] = view_df['pagado'].apply(f_money)
        view_df['Saldo Pendiente'] = view_df['Pendiente'].apply(f_money)
        st.dataframe(view_df[['u', 'vendedor', 'Comisión Total', 'Pagado', 'Saldo Pendiente']], use_container_width=True, hide_index=True)
        
        st.divider()
        with st.form("f_pago_com"):
            venta_sel = st.selectbox("Registrar pago para:", df_com[df_com['Pendiente'] > 0]['u'] + " (" + df_com['vendedor'] + ")")
            monto_p = st.number_input("Importe a pagar ($)", min_value=0.0)
            if st.form_submit_button("REGISTRAR PAGO AL VENDEDOR"):
                id_v_sel = int(df_com[df_com['u'] + " (" + df_com['vendedor'] + ")" == venta_sel]['id_venta'].values[0])
                c.execute("INSERT INTO pagos_comisiones (id_venta, monto_pagado, fecha) VALUES (?,?,?)", 
                          (id_v_sel, monto_p, datetime.now().strftime('%Y-%m-%d')))
                conn.commit()
                st.success("Pago registrado con éxito")
                st.rerun()

# --- 7. NUEVA VENTA (CON COMISIÓN Y FECHA DD-MM-AAAA) ---
elif choice == "📝 Nueva Venta":
    st.header("📝 REGISTRAR VENTA")
    lt = pd.read_sql_query("SELECT * FROM terrenos WHERE estatus='Disponible'", conn)
    cl = pd.read_sql_query("SELECT * FROM clientes", conn)
    vn = pd.read_sql_query("SELECT * FROM vendedores", conn)
    
    if lt.empty:
        st.warning("No hay lotes disponibles.")
    else:
        with st.form("nv"):
            c1, c2 = st.columns(2)
            lote_txt = c1.selectbox("Lote:", lt['manzana'] + "-" + lt['lote'])
            cli_txt = c1.selectbox("Cliente:", cl['nombre'])
            ven_txt = c1.selectbox("Vendedor:", vn['nombre'])
            f_venta = c1.date_input("Fecha de Venta (DD-MM-AAAA)")
            
            eng = c2.number_input("Enganche ($)", min_value=0.0)
            mes = c2.number_input("Plazo (Meses)", min_value=1, value=48)
            comi = c2.number_input("Importe Comisión ($)", min_value=0.0)
            
            if st.form_submit_button("GUARDAR VENTA"):
                id_l = int(lt[lt['manzana'] + "-" + lote_txt == lote_txt]['id'].values[0])
                id_c = int(cl[cl['nombre'] == cli_txt]['id'].values[0])
                id_v = int(vn[vn['nombre'] == ven_txt]['id'].values[0])
                costo_t = float(lt[lt['id'] == id_l]['costo'].values[0])
                mensu = (costo_t - eng) / mes
                
                c.execute('''INSERT INTO ventas (id_terreno, id_cliente, id_vendedor, enganche, meses, mensualidad, fecha, comision_total) 
                             VALUES (?,?,?,?,?,?,?,?)''', 
                          (id_l, id_c, id_v, eng, mes, mensu, f_venta.strftime('%Y-%m-%d'), comi))
                c.execute("UPDATE terrenos SET estatus='Vendido' WHERE id=?", (id_l,))
                conn.commit()
                st.success("Venta y Comisión registradas")
                st.rerun()

# --- SECCIONES RESTANTES (SIMPLIFICADAS PARA EVITAR ERRORES) ---
elif choice == "🔍 Detalle por Lote":
    st.header("🔍 CONSULTA")
    df_u = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u FROM ventas v JOIN terrenos t ON v.id_terreno = t.id", conn)
    if not df_u.empty:
        l_sel = st.selectbox("Lote:", sorted(df_u['u'].tolist()))
        st.info("Información del lote seleccionada correctamente.")

elif choice == "💸 Cobranza Clientes":
    st.header("💰 ABONOS")
    df_v = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote || ' - ' || c.nombre as label FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN clientes c ON v.id_cliente = c.id", conn)
    if not df_v.empty:
        with st.form("p"):
            s = st.selectbox("Cuenta:", df_v['label'])
            m = st.number_input("Monto:", min_value=0.0)
            if st.form_submit_button("REGISTRAR ABONO"):
                id_v = int(df_v[df_v['label'] == s]['id'].values[0])
                c.execute("INSERT INTO pagos (id_venta, monto, fecha) VALUES (?,?,?)", (id_v, m, datetime.now().strftime('%Y-%m-%d')))
                conn.commit(); st.rerun()

elif choice == "📈 Gestión de Ventas":
    st.header("🚨 ELIMINAR")
    df_g = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u, v.id_terreno FROM ventas v JOIN terrenos t ON v.id_terreno = t.id", conn)
    if not df_g.empty:
        s = st.selectbox("Cancelar venta de:", df_g['u'])
        if st.button("CONFIRMAR CANCELACIÓN"):
            rid = int(df_g[df_g['u'] == s]['id'].values[0])
            tid = int(df_g[df_g['u'] == s]['id_terreno'].values[0])
            c.execute("DELETE FROM ventas WHERE id=?", (rid,))
            c.execute("UPDATE terrenos SET estatus='Disponible' WHERE id=?", (tid,))
            conn.commit(); st.rerun()

elif choice == "🏗️ Catálogo":
    st.header("🏗️ LOTES")
    with st.form("t"):
        m, l, p = st.columns(3)
        man = m.text_input("Manzana")
        lot = l.text_input("Lote")
        pre = p.number_input("Precio", min_value=0.0)
        if st.form_submit_button("Guardar"):
            c.execute("INSERT INTO terrenos (manzana, lote, costo) VALUES (?,?,?)", (man, lot, pre))
            conn.commit(); st.rerun()
    st.write(pd.read_sql_query("SELECT * FROM terrenos", conn))

elif choice == "👥 Personal":
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
