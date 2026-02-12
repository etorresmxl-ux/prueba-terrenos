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

# Actualización de tablas con Comisiones
c.execute('CREATE TABLE IF NOT EXISTS terrenos (id INTEGER PRIMARY KEY AUTOINCREMENT, manzana TEXT, lote TEXT, costo REAL, estatus TEXT DEFAULT "Disponible")')
c.execute('CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS vendedores (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT)')
# Nueva columna: comision_total
c.execute('''CREATE TABLE IF NOT EXISTS ventas 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, id_terreno INTEGER, id_cliente INTEGER, 
              id_vendedor INTEGER, enganche REAL, meses INTEGER, mensualidad REAL, 
              fecha TEXT, comision_total REAL)''')
c.execute('CREATE TABLE IF NOT EXISTS pagos (id INTEGER PRIMARY KEY AUTOINCREMENT, id_venta INTEGER, monto REAL, fecha TEXT)')
# Tabla para pagos de comisiones a vendedores
c.execute('''CREATE TABLE IF NOT EXISTS pagos_comisiones 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, id_venta INTEGER, monto_pagado REAL, fecha TEXT)''')
conn.commit()

# --- FUNCIONES DE FORMATO ---
def f_money(valor):
    try: return f"${float(valor or 0):,.2f}"
    except: return "$0.00"

def f_date(fecha_str):
    """Convierte AAAA-MM-DD a DD-MM-AAAA para mostrar al usuario"""
    try:
        dt = datetime.strptime(fecha_str, '%Y-%m-%d')
        return dt.strftime('%d-%m-%p-%Y').replace("-AM-", "-").replace("-PM-", "-") # Simplificado
    except:
        try:
            # Reintento simple
            dt = datetime.strptime(fecha_str, '%Y-%m-%d')
            return dt.strftime('%d-%m-%Y')
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
    df = pd.read_sql_query(query, conn)
    if not df.empty:
        df['Fecha Contrato'] = df['fecha_contrato'].apply(f_date)
        df['Total Pagado'] = (df['enganche'] + df['suma_pagos']).apply(f_money)
        df['Saldo'] = (df['costo_total'] - (df['enganche'] + df['suma_pagos'])).apply(f_money)
        st.dataframe(df[['ubicacion', 'cliente', 'Fecha Contrato', 'Total Pagado', 'Saldo']], use_container_width=True, hide_index=True)

# --- 2. REPORTES ---
elif choice == "📊 Reportes":
    st.header("📊 RENDIMIENTO")
    df_v = pd.read_sql_query("SELECT v.id, v.comision_total, vn.nombre as vendedor FROM ventas v JOIN vendedores vn ON v.id_vendedor = vn.id", conn)
    if not df_v.empty:
        fig = px.bar(df_v, x='vendedor', y='comision_total', title="Comisiones Generadas por Vendedor", labels={'comision_total':'Comisión $'})
        st.plotly_chart(fig, use_container_width=True)

# --- 5. PAGO DE COMISIONES (NUEVA SECCIÓN) ---
elif choice == "🤝 Pago Comisiones":
    st.header("🤝 GESTIÓN DE COMISIONES A VENDEDORES")
    
    query = '''
        SELECT v.id as id_venta, 'M'||t.manzana||'-L'||t.lote as u, vn.nombre as vendedor, v.comision_total,
        IFNULL((SELECT SUM(monto_pagado) FROM pagos_comisiones WHERE id_venta = v.id), 0) as pagado
        FROM ventas v 
        JOIN terrenos t ON v.id_terreno = t.id 
        JOIN vendedores vn ON v.id_vendedor = vn.id
    '''
    df_com = pd.read_sql_query(query, conn)
    
    if df_com.empty:
        st.info("No hay comisiones registradas.")
    else:
        df_com['Pendiente'] = df_com['comision_total'] - df_com['pagado']
        
        # Mostrar tabla de saldos
        st.subheader("Saldos de Comisiones")
        disp = df_com.copy()
        disp['Comisión Total'] = disp['comision_total'].apply(f_money)
        disp['Pagado'] = disp['pagado'].apply(f_money)
        disp['Saldo Pendiente'] = disp['Pendiente'].apply(f_money)
        st.dataframe(disp[['u', 'vendedor', 'Comisión Total', 'Pagado', 'Saldo Pendiente']], use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("Registrar Pago de Comisión")
        with st.form("pago_com"):
            venta_sel = st.selectbox("Seleccionar Venta:", df_com[df_com['Pendiente'] > 0]['u'] + " (" + df_com['vendedor'] + ")")
            monto_p = st.number_input("Monto a pagar al vendedor ($)", min_value=0.0)
            fecha_p = st.date_input("Fecha de pago")
            if st.form_submit_button("REGISTRAR PAGO DE COMISIÓN"):
                id_v_sel = int(df_com[df_com['u'] + " (" + df_com['vendedor'] + ")" == venta_sel]['id_venta'].values[0])
                c.execute("INSERT INTO pagos_comisiones (id_venta, monto_pagado, fecha) VALUES (?,?,?)", 
                          (id_v_sel, monto_p, fecha_p.strftime('%Y-%m-%d')))
                conn.commit()
                st.success("Comisión pagada correctamente")
                st.rerun()

# --- 7. NUEVA VENTA (CON COMISIÓN) ---
elif choice == "📝 Nueva Venta":
    st.header("📝 REGISTRAR NUEVA VENTA")
    lt = pd.read_sql_query("SELECT * FROM terrenos WHERE estatus='Disponible'", conn)
    cl = pd.read_sql_query("SELECT * FROM clientes", conn)
    vn = pd.read_sql_query("SELECT * FROM vendedores", conn)
    
    if lt.empty:
        st.warning("No hay terrenos disponibles.")
    else:
        with st.form("venta_com"):
            col1, col2 = st.columns(2)
            lote = col1.selectbox("Terreno:", lt['manzana'] + "-" + lt['lote'])
            cliente = col1.selectbox("Cliente:", cl['nombre'])
            vendedor = col1.selectbox("Vendedor:", vn['nombre'])
            fecha_v = col1.date_input("Fecha de Venta")
            
            enganche = col2.number_input("Enganche ($)", min_value=0.0)
            plazo = col2.number_input("Plazo (Meses)", min_value=1, value=48)
            # AQUÍ AGREGAMOS EL IMPORTE DE LA COMISIÓN
            comision = col2.number_input("Importe de Comisión para Vendedor ($)", min_value=0.0)
            
            if st.form_submit_button("CERRAR VENTA Y GENERAR COMISIÓN"):
                id_l = int(lt[lt['manzana'] + "-" + lt['lote'] == lote]['id'].values[0])
                id_c = int(cl[cl['nombre'] == cliente]['id'].values[0])
                id_v = int(vn[vn['nombre'] == vendedor]['id'].values[0])
                costo_t = float(lt[lt['id'] == id_l]['costo'].values[0])
                mensu = (costo_t - enganche) / plazo
                
                c.execute('''INSERT INTO ventas (id_terreno, id_cliente, id_vendedor, enganche, meses, mensualidad, fecha, comision_total) 
                             VALUES (?,?,?,?,?,?,?,?)''', 
                          (id_l, id_c, id_v, enganche, plazo, mensu, fecha_v.strftime('%Y-%m-%d'), comision))
                c.execute("UPDATE terrenos SET estatus='Vendido' WHERE id=?", (id_l,))
                conn.commit()
                st.success(f"Venta registrada. Comisión de {f_money(comision)} asignada a {vendedor}.")
                st.rerun()

# --- REESTABLECER EL RESTO DE SECCIONES (Cobranza, Catálogo, etc.) ---
elif choice == "💸 Cobranza Clientes":
    st.header("💰 ABONOS DE CLIENTES")
    df_v = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote || ' - ' || c.nombre as label FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN clientes c ON v.id_cliente = c.id", conn)
    if not df_v.empty:
        with st.form("pago_cliente"):
            sel = st.selectbox("Cuenta:", df_v['label'])
            monto = st.number_input("Monto:", min_value=0.0)
            fec = st.date_input("Fecha:")
            if st.form_submit_button("REGISTRAR ABONO"):
                id_v = int(df_v[df_v['label'] == sel]['id'].values[0])
                c.execute("INSERT INTO pagos (id_venta, monto, fecha) VALUES (?,?,?)", (id_v, monto, fec.strftime('%Y-%m-%d')))
                conn.commit(); st.rerun()

elif choice == "🏗️ Catálogo":
    st.header("🏗️ TERRENOS")
    with st.form("t"):
        m, l, p = st.columns(3)
        man = m.text_input("Manzana")
        lot = l.text_input("Lote")
        pre = p.number_input("Precio", min_value=0.0)
        if st.form_submit_button("Añadir"):
            c.execute("INSERT INTO terrenos (manzana, lote, costo) VALUES (?,?,?)", (man, lot, pre))
            conn.commit(); st.rerun()
    st.write(pd.read_sql_query("SELECT manzana, lote, costo as Precio FROM terrenos", conn))

elif choice == "👥 Personal":
    st.header("👥 CLIENTES Y VENDEDORES")
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
