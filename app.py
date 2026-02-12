import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_config = st.set_page_config(page_title="Inmobiliaria Pro v25", layout="wide")

# --- ESTILO CSS PERSONALIZADO (Alineación de menú) ---
st.markdown("""
    <style>
    div.stButton > button {
        text-align: left !important;
        justify-content: flex-start !important;
        padding-left: 20px !important;
    }
    </style>
""", unsafe_allow_html=True)

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

# --- FUNCIONES DE FORMATO ---
def f_money(v): 
    return f"${float(v or 0):,.2f}"

def f_date_show(fecha_str):
    try:
        return datetime.strptime(fecha_str, '%Y-%m-%d').strftime('%d-%m-%Y')
    except:
        return fecha_str

def get_or_create_id(tabla, nombre_col, valor):
    valor = valor.strip()
    c.execute(f"SELECT id FROM {tabla} WHERE {nombre_col} = ?", (valor,))
    result = c.fetchone()
    if result: return result[0]
    c.execute(f"INSERT INTO {tabla} ({nombre_col}) VALUES (?)", (valor,))
    conn.commit()
    return c.lastrowid

# --- MENÚ LATERAL ---
with st.sidebar:
    st.title("📂 MENÚ PRINCIPAL")
    if 'menu_option' not in st.session_state:
        st.session_state.menu_option = "Resumen"

    st.markdown("### 📊 **REPORTES**")
    if st.button("🏠 Resumen", use_container_width=True): st.session_state.menu_option = "Resumen"
    if st.button("🤝 Comisiones", use_container_width=True): st.session_state.menu_option = "Comisiones"
    if st.button("📈 Gráficos", use_container_width=True): st.session_state.menu_option = "Gráficos"

    st.markdown("---")
    st.markdown("### 🚀 **OPERACIONES**")
    if st.button("📝 Nueva Venta", use_container_width=True): st.session_state.menu_option = "Nueva Venta"
    if st.button("💸 Cobranza Clientes", use_container_width=True): st.session_state.menu_option = "Cobranza"
    if st.button("🔍 Detalle de Crédito", use_container_width=True): st.session_state.menu_option = "Detalle"
    if st.button("⚙️ Gestión de Contratos", use_container_width=True): st.session_state.menu_option = "Gestion"

    st.markdown("---")
    st.markdown("### 📂 **CATÁLOGO**")
    if st.button("📍 Ubicaciones", use_container_width=True): st.session_state.menu_option = "Ubicaciones"
    if st.button("👥 Directorio", use_container_width=True): st.session_state.menu_option = "Directorio"

choice = st.session_state.menu_option

# --- PÁGINAS ---

if choice == "Resumen":
    st.header("📋 ESTADO DE CUENTA GENERAL")
    df = pd.read_sql_query('''
        SELECT v.id, 'M'||t.manzana||'-L'||t.lote as Lote, c.nombre as Cliente, 
        t.costo as [Valor Venta], v.enganche as Enganche, v.fecha, 
        IFNULL((SELECT SUM(monto) FROM pagos WHERE id_venta = v.id), 0) as pagos_abonos
        FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id
    ''', conn)
    if not df.empty:
        df['Contrato'] = df['fecha'].apply(f_date_show)
        df['Total Pagado'] = (df['Enganche'] + df['pagos_abonos']).apply(f_money)
        df['Saldo Hoy'] = (df['Valor Venta'] - (df['Enganche'] + df['pagos_abonos'])).apply(f_money)
        df['Valor Venta'] = df['Valor Venta'].apply(f_money)
        df['Enganche'] = df['Enganche'].apply(f_money)
        st.dataframe(df[['Lote', 'Cliente', 'Valor Venta', 'Enganche', 'Contrato', 'Total Pagado', 'Saldo Hoy']], use_container_width=True, hide_index=True)
    else:
        st.info("No hay ventas registradas.")

elif choice == "Detalle":
    st.header("🔍 DETALLE DE CRÉDITO Y PROYECCIÓN")
    df_u = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u FROM ventas v JOIN terrenos t ON v.id_terreno = t.id", conn)
    if not df_u.empty:
        sel_u = st.selectbox("Seleccione el Lote para ver su tabla de pagos:", df_u['u'])
        vid = int(df_u[df_u['u'] == sel_u]['id'].values[0])
        
        res = pd.read_sql_query(f'''
            SELECT c.nombre, t.costo, v.enganche, v.fecha, v.meses, v.mensualidad 
            FROM ventas v JOIN clientes c ON v.id_cliente = c.id 
            JOIN terrenos t ON v.id_terreno = t.id WHERE v.id = {vid}
        ''', conn).iloc[0]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Cliente", res['nombre'])
        col2.metric("Valor Venta", f_money(res['costo']))
        col3.metric("Mensualidad", f_money(res['mensualidad']))
        
        st.markdown("---")
        st.subheader("📅 Tabla Proyectada de Pagos")
        
        # Generar tabla de amortización simple
        tabla = []
        saldo_insoluto = res['costo'] - res['enganche']
        fecha_pago = datetime.strptime(res['fecha'], '%Y-%m-%d')
        
        for i in range(1, int(res['meses']) + 1):
            saldo_insoluto -= res['mensualidad']
            # Evitar saldos negativos por decimales
            if saldo_insoluto < 0: saldo_insoluto = 0
            
            tabla.append({
                "Mes": i,
                "Cuota Sugerida": f_money(res['mensualidad']),
                "Saldo Restante": f_money(saldo_insoluto)
            })
            
        st.table(tabla[:24]) # Mostramos los primeros 24 meses por legibilidad
        if res['meses'] > 24:
            st.info(f"Mostrando primeros 24 de {int(res['meses'])} meses totales.")

elif choice == "Nueva Venta":
    st.header("📝 REGISTRAR NUEVO CONTRATO")
    lt = pd.read_sql_query("SELECT * FROM terrenos WHERE estatus='Disponible'", conn)
    if lt.empty: 
        st.warning("No hay terrenos disponibles.")
    else:
        with st.form("nv"):
            col1, col2 = st.columns(2)
            l_sel = col1.selectbox("Lote Disponible:", lt['manzana'] + "-" + lt['lote'])
            c_nombre = col1.text_input("Nombre del Cliente:")
            v_nombre = col1.text_input("Nombre del Vendedor:")
            f_cont = col1.date_input("Fecha de Contrato", datetime.now())
            
            p_cat = float(lt[lt['manzana'] + "-" + lt['lote'] == l_sel]['costo'].values[0])
            costo_v = col2.number_input("Valor de Venta Real ($)", min_value=0.0, value=p_cat, format="%.2f")
            eng_v = col2.number_input("Enganche Recibido ($)", min_value=0.0, format="%.2f")
            plz_v = col2.number_input("Plazo (Meses)", min_value=1, value=48)
            com_v = col2.number_input("Comisión del Vendedor ($)", min_value=0.0, format="%.2f")
            
            if st.form_submit_button("CERRAR VENTA"):
                if c_nombre and v_nombre:
                    id_c = get_or_create_id('clientes', 'nombre', c_nombre)
                    id_v = get_or_create_id('vendedores', 'nombre', v_nombre)
                    id_l = int(lt[lt['manzana'] + "-" + lt['lote'] == l_sel]['id'].values[0])
                    mensu = (costo_v - eng_v) / plz_v
                    c.execute('''INSERT INTO ventas (id_terreno, id_cliente, id_vendedor, enganche, meses, mensualidad, fecha, comision_total) 
                                 VALUES (?,?,?,?,?,?,?,?)''', (id_l, id_c, id_v, eng_v, plz_v, mensu, f_cont.strftime('%Y-%m-%d'), com_v))
                    c.execute("UPDATE terrenos SET estatus='Vendido', costo=? WHERE id=?", (costo_v, id_l))
                    conn.commit()
                    st.success("¡Venta Exitosa!")
                    st.rerun()

elif choice == "Comisiones":
    st.header("🤝 REPORTE DE COMISIONES")
    df_c = pd.read_sql_query('''
        SELECT v.id, 'M'||t.manzana||'-L'||t.lote as Lote, vn.nombre as Vendedor, v.comision_total as Total,
        IFNULL((SELECT SUM(monto_pagado) FROM pagos_comisiones WHERE id_venta = v.id), 0) as Pagado
        FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN vendedores vn ON v.id_vendedor = vn.id
    ''', conn)
    if not df_c.empty:
        df_c['Pendiente'] = df_c['Total'] - df_c['Pagado']
        view = df_c.copy()
        view['Total'] = view['Total'].apply(f_money)
        view['Pagado'] = view['Pagado'].apply(f_money)
        view['Pendiente'] = view['Pendiente'].apply(f_money)
        st.dataframe(view[['Lote', 'Vendedor', 'Total', 'Pagado', 'Pendiente']], use_container_width=True, hide_index=True)
        
        with st.expander("Registrar pago a vendedor"):
            sel = st.selectbox("Contrato:", df_c[df_c['Pendiente']>0]['Lote'] + " (" + df_c['Vendedor'] + ")")
            monto_p = st.number_input("Monto a pagar ($)", min_value=0.0, format="%.2f")
            if st.button("CONFIRMAR PAGO COMISIÓN"):
                id_v = int(df_c[df_c['Lote'] + " (" + df_c['Vendedor'] + ")" == sel]['id'].values[0])
                c.execute("INSERT INTO pagos_comisiones (id_venta, monto_pagado, fecha) VALUES (?,?,?)", (id_v, monto_p, datetime.now().strftime('%Y-%m-%d')))
                conn.commit(); st.rerun()

elif choice == "Cobranza":
    st.header("💸 RECIBIR ABONOS")
    df_v = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote || ' - ' || c.nombre as l FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN clientes c ON v.id_cliente = c.id", conn)
    if not df_v.empty:
        with st.form("cob"):
            s = st.selectbox("Seleccione Contrato:", df_v['l'])
            m = st.number_input("Monto a abonar ($)", min_value=0.0, format="%.2f")
            if st.form_submit_button("REGISTRAR PAGO"):
                id_v = int(df_v[df_v['l'] == s]['id'].values[0])
                c.execute("INSERT INTO pagos (id_venta, monto, fecha) VALUES (?,?,?)", (id_v, m, datetime.now().strftime('%Y-%m-%d')))
                conn.commit(); st.success("Pago guardado"); st.rerun()

elif choice == "Gestion":
    st.header("⚙️ GESTIÓN DE CONTRATOS")
    df_g = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u, c.nombre as cli, v.id_terreno FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id", conn)
    if not df_g.empty:
        sel = st.selectbox("Contrato a eliminar:", df_g['u'] + " - " + df_g['cli'])
        if st.button("BORRAR CONTRATO DEFINITIVAMENTE"):
            row = df_g[df_g['u'] + " - " + df_g['cli'] == sel].iloc[0]
            c.execute("DELETE FROM ventas WHERE id=?", (int(row['id']),)); c.execute("UPDATE terrenos SET estatus='Disponible' WHERE id=?", (int(row['id_terreno']),))
            conn.commit(); st.rerun()

elif choice == "Ubicaciones":
    st.header("📍 UBICACIONES (CATÁLOGO)")
    with st.form("cat"):
        m_c, l_c, p_c = st.columns(3)
        ma = m_c.text_input("Manzana")
        lo = l_c.text_input("Lote")
        pr = p_c.number_input("Precio Sugerido ($)", min_value=0.0, format="%.2f")
        if st.form_submit_button("Guardar Ubicación"):
            c.execute("INSERT INTO terrenos (manzana, lote, costo) VALUES (?,?,?)", (ma, lo, pr))
            conn.commit(); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT manzana, lote, costo, estatus FROM terrenos", conn), use_container_width=True)

elif choice == "Directorio":
    st.header("👥 DIRECTORIO")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Clientes")
        st.dataframe(pd.read_sql_query("SELECT nombre FROM clientes ORDER BY nombre", conn), hide_index=True)
    with c2:
        st.subheader("Vendedores")
        st.dataframe(pd.read_sql_query("SELECT nombre FROM vendedores ORDER BY nombre", conn), hide_index=True)

elif choice == "Gráficos":
    st.header("📈 GRÁFICOS DE VENTAS")
    df_g = pd.read_sql_query('''SELECT vn.nombre as Vendedor, SUM(t.costo) as Total FROM ventas v JOIN vendedores vn ON v.id_vendedor = vn.id JOIN terrenos t ON v.id_terreno = t.id GROUP BY vn.nombre''', conn)
    if not df_g.empty: st.bar_chart(data=df_g, x="Vendedor", y="Total")
