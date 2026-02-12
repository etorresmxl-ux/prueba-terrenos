import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Inmobiliaria Pro v22.5", layout="wide")

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

# --- MENÚ LATERAL ORGANIZADO ---
st.sidebar.markdown("### 📊 **REPORTES**")
menu_rep = ["🏠 Resumen de Cartera", "🤝 Comisiones"]

st.sidebar.markdown("---")
st.sidebar.markdown("### 🚀 **OPERACIONES**")
menu_ops = ["📝 Nueva Venta", "💸 Cobranza Clientes", "🔍 Detalle por Lote", "⚙️ Gestión de Contratos", "🏗️ Catálogo", "👥 Directorio", "📈 Gráficos"]

choice = st.sidebar.radio("Seleccione una opción:", menu_rep + menu_ops)

# --- 1. RESUMEN DE CARTERA ---
if choice == "🏠 Resumen de Cartera":
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

# --- 2. COMISIONES (AHORA EN REPORTES) ---
elif choice == "🤝 Comisiones":
    st.header("🤝 REPORTE DE COMISIONES")
    df_c = pd.read_sql_query('''
        SELECT v.id, 'M'||t.manzana||'-L'||t.lote as Lote, vn.nombre as Vendedor, v.comision_total as Total,
        IFNULL((SELECT SUM(monto_pagado) FROM pagos_comisiones WHERE id_venta = v.id), 0) as Pagado
        FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN vendedores vn ON v.id_vendedor = vn.id
    ''', conn)
    if not df_c.empty:
        df_c['Pendiente'] = df_c['Total'] - df_c['Pagado']
        # Formatear para vista
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
                c.execute("INSERT INTO pagos_comisiones (id_venta, monto_pagado, fecha) VALUES (?,?,?)", 
                          (id_v, monto_p, datetime.now().strftime('%Y-%m-%d')))
                conn.commit(); st.rerun()

# --- 3. NUEVA VENTA ---
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
            l_sel = col1.selectbox("Lote:", lt['manzana'] + "-" + lt['lote'])
            c_sel = col1.selectbox("Cliente:", cl['nombre'])
            v_sel = col1.selectbox("Vendedor:", vn['nombre'])
            f_cont = col1.date_input("Fecha de Contrato", datetime.now())
            
            p_cat = float(lt[lt['manzana'] + "-" + lt['lote'] == l_sel]['costo'].values[0])
            
            costo_v = col2.number_input("Valor de Venta Real ($)", min_value=0.0, value=p_cat, format="%.2f")
            eng_v = col2.number_input("Enganche Recibido ($)", min_value=0.0, format="%.2f")
            plz_v = col2.number_input("Plazo (Meses)", min_value=1, value=48)
            com_v = col2.number_input("Comisión del Vendedor ($)", min_value=0.0, format="%.2f")
            
            if st.form_submit_button("CERRAR VENTA"):
                id_l = int(lt[lt['manzana'] + "-" + lt['lote'] == l_sel]['id'].values[0])
                id_c = int(cl[cl['nombre'] == c_sel]['id'].values[0])
                id_v = int(vn[vn['nombre'] == v_sel]['id'].values[0])
                mensu = (costo_v - eng_v) / plz_v
                
                c.execute('''INSERT INTO ventas (id_terreno, id_cliente, id_vendedor, enganche, meses, mensualidad, fecha, comision_total) 
                             VALUES (?,?,?,?,?,?,?,?)''', 
                          (id_l, id_c, id_v, eng_v, plz_v, mensu, f_cont.strftime('%Y-%m-%d'), com_v))
                c.execute("UPDATE terrenos SET estatus='Vendido', costo=? WHERE id=?", (costo_v, id_l))
                conn.commit(); st.success("Venta realizada"); st.rerun()

# --- 4. COBRANZA ---
elif choice == "💸 Cobranza Clientes":
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

# --- 5. DETALLE POR LOTE ---
elif choice == "🔍 Detalle por Lote":
    st.header("🔍 CONSULTA INDIVIDUAL")
    df_u = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u FROM ventas v JOIN terrenos t ON v.id_terreno = t.id", conn)
    if not df_u.empty:
        sel_u = st.selectbox("Lote:", df_u['u'])
        vid = int(df_u[df_u['u'] == sel_u]['id'].values[0])
        res = pd.read_sql_query(f"SELECT c.nombre, t.costo, v.enganche, v.fecha, v.meses, v.mensualidad FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id WHERE v.id = {vid}", conn).iloc[0]
        
        c1, c2 = st.columns(2)
        c1.metric("Cliente", res['nombre'])
        c1.write(f"**Costo Total:** {f_money(res['costo'])}")
        c1.write(f"**Enganche:** {f_money(res['enganche'])}")
        
        c2.write(f"**Fecha de Venta:** {f_date_show(res['fecha'])}")
        c2.write(f"**Mensualidad:** {f_money(res['mensualidad'])}")
        c2.write(f"**Plazo:** {int(res['meses'])} meses")

# --- 6. GESTIÓN ---
elif choice == "⚙️ Gestión de Contratos":
    st.header("⚙️ ADMINISTRAR CONTRATOS")
    df_g = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u, c.nombre as cli, v.id_terreno FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id", conn)
    if not df_g.empty:
        sel = st.selectbox("Contrato a eliminar:", df_g['u'] + " - " + df_g['cli'])
        if st.button("ELIMINAR DEFINITIVAMENTE"):
            id_ven = int(df_g[df_g['u'] + " - " + df_g['cli'] == sel]['id'].values[0])
            id_ter = int(df_g[df_g['u'] + " - " + df_g['cli'] == sel]['id_terreno'].values[0])
            c.execute("DELETE FROM ventas WHERE id=?", (id_ven,))
            c.execute("UPDATE terrenos SET estatus='Disponible' WHERE id=?", (id_ter,))
            conn.commit(); st.rerun()

# --- 7. CATÁLOGO ---
elif choice == "🏗️ Catálogo":
    st.header("🏗️ INVENTARIO")
    with st.form("cat"):
        m_c = st.text_input("Manzana")
        l_c = st.text_input("Lote")
        p_cat = st.number_input("Precio Sugerido ($)", min_value=0.0, format="%.2f")
        if st.form_submit_button("Agregar al Sistema"):
            c.execute("INSERT INTO terrenos (manzana, lote, costo) VALUES (?,?,?)", (m_c, l_c, p_cat))
            conn.commit(); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT manzana, lote, costo, estatus FROM terrenos", conn), use_container_width=True)

# --- 8. DIRECTORIO ---
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

# --- 9. GRÁFICOS ---
elif choice == "📈 Gráficos":
    st.header("📈 ESTADÍSTICAS")
    df_g = pd.read_sql_query('''SELECT vn.nombre as Vendedor, SUM(t.costo) as Total FROM ventas v JOIN vendedores vn ON v.id_vendedor = vn.id JOIN terrenos t ON v.id_terreno = t.id GROUP BY vn.nombre''', conn)
    if not df_g.empty:
        st.bar_chart(data=df_g, x="Vendedor", y="Total")
