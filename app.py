import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Inmobiliaria Pro v20", layout="wide")

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

# --- DB ---
conn = sqlite3.connect('inmobiliaria.db', check_same_thread=False)
c = conn.cursor()

# Formatos
def f_money(v): return f"${float(v or 0):,.2f}"
def f_date(s): 
    try: return datetime.strptime(s, '%Y-%m-%d').strftime('%d-%m-%Y')
    except: return s

# --- MENÚ ---
menu = ["🏠 Cartera", "📊 Reportes", "🔍 Detalle por Lote", "💸 Cobranza Clientes", "🤝 Comisiones", "📈 Gestión de Ventas", "📝 Nueva Venta", "🏗️ Catálogo", "👥 Directorio"]
choice = st.sidebar.radio("Menú", menu)

# --- 1. CARTERA ---
if choice == "🏠 Cartera":
    st.header("📋 ESTADO DE CUENTA GENERAL")
    df = pd.read_sql_query('''
        SELECT v.id, 'M'||t.manzana||'-L'||t.lote as Lote, c.nombre as Cliente, 
        t.costo, v.enganche, v.fecha, v.mensualidad,
        IFNULL((SELECT SUM(monto) FROM pagos WHERE id_venta = v.id), 0) as pagos
        FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id
    ''', conn)
    if not df.empty:
        df['Contrato'] = df['fecha'].apply(f_date)
        df['Pagado'] = (df['enganche'] + df['pagos']).apply(f_money)
        df['Saldo'] = (df['costo'] - (df['enganche'] + df['pagos'])).apply(f_money)
        st.dataframe(df[['Lote', 'Cliente', 'Contrato', 'Pagado', 'Saldo']], use_container_width=True, hide_index=True)

# --- 2. REPORTES ---
elif choice == "📊 Reportes":
    st.header("📊 RESUMEN")
    df_v = pd.read_sql_query('''
        SELECT vn.nombre as Vendedor, SUM(t.costo) as Total 
        FROM ventas v JOIN vendedores vn ON v.id_vendedor = vn.id JOIN terrenos t ON v.id_terreno = t.id
        GROUP BY vn.nombre
    ''', conn)
    if not df_v.empty:
        st.bar_chart(data=df_v, x="Vendedor", y="Total")

# --- 3. DETALLE POR LOTE (RECUPERADO) ---
elif choice == "🔍 Detalle por Lote":
    st.header("🔍 DETALLE INDIVIDUAL")
    df_u = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u FROM ventas v JOIN terrenos t ON v.id_terreno = t.id", conn)
    if df_u.empty:
        st.info("No hay ventas registradas.")
    else:
        sel_u = st.selectbox("Seleccione Lote:", df_u['u'])
        vid = int(df_u[df_u['u'] == sel_u]['id'].values[0])
        
        # Datos de la venta
        det = pd.read_sql_query(f'''
            SELECT c.nombre, t.costo, v.enganche, v.fecha, v.meses, v.mensualidad 
            FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id 
            WHERE v.id = {vid}''', conn).iloc[0]
        
        pagos_totales = pd.read_sql_query(f"SELECT SUM(monto) as s FROM pagos WHERE id_venta = {vid}", conn)['s'].iloc[0] or 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Cliente", det['nombre'])
        c2.metric("Saldo Pendiente", f_money(det['costo'] - (det['enganche'] + pagos_totales)))
        c3.metric("Mensualidad", f_money(det['mensualidad']))

        st.subheader("📅 Proyección de Pagos (Amortización)")
        tabla = []
        saldo_m = det['costo'] - det['enganche']
        f_pago = datetime.strptime(det['fecha'], '%Y-%m-%d')
        for i in range(1, int(det['meses']) + 1):
            # Calcular siguiente mes
            m = (f_pago.month % 12) + 1
            y = f_pago.year + (1 if f_pago.month == 12 else 0)
            f_pago = f_pago.replace(month=m, year=y)
            saldo_m -= det['mensualidad']
            tabla.append({
                "Mes": i, "Vencimiento": f_pago.strftime('%d-%m-%Y'),
                "Cuota": f_money(det['mensualidad']), "Saldo rest.": f_money(max(0, saldo_m))
            })
        st.dataframe(pd.DataFrame(tabla), use_container_width=True, hide_index=True)

# --- 4. GESTIÓN DE VENTAS (RECUPERADO) ---
elif choice == "📈 Gestión de Ventas":
    st.header("📈 ADMINISTRAR CONTRATOS")
    df_g = pd.read_sql_query('''
        SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u, c.nombre as cli, v.id_terreno 
        FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id
    ''', conn)
    if not df_g.empty:
        st.subheader("🚨 Cancelar Venta")
        st.warning("Al cancelar una venta, el lote volverá a estar 'Disponible' y se borrará el registro del cliente de esta venta.")
        sel_can = st.selectbox("Seleccione contrato a eliminar:", df_g['u'] + " - " + df_g['cli'])
        if st.button("ELIMINAR VENTA DEFINITIVAMENTE"):
            row = df_g[df_g['u'] + " - " + df_g['cli'] == sel_can].iloc[0]
            c.execute("DELETE FROM ventas WHERE id=?", (int(row['id']),))
            c.execute("UPDATE terrenos SET estatus='Disponible' WHERE id=?", (int(row['id_terreno']),))
            conn.commit()
            st.error(f"Venta {row['u']} cancelada.")
            st.rerun()
    else:
        st.info("No hay ventas activas.")

# --- 5. COMISIONES ---
elif choice == "🤝 Comisiones":
    st.header("🤝 PAGOS A VENDEDORES")
    df_c = pd.read_sql_query('''
        SELECT v.id, 'M'||t.manzana||'-L'||t.lote as Lote, vn.nombre as Vendedor, v.comision_total,
        IFNULL((SELECT SUM(monto_pagado) FROM pagos_comisiones WHERE id_venta = v.id), 0) as pagado
        FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN vendedores vn ON v.id_vendedor = vn.id
    ''', conn)
    if not df_c.empty:
        df_c['Pendiente'] = df_c['comision_total'] - df_c['pagado']
        st.dataframe(df_c[['Lote', 'Vendedor', 'comision_total', 'pagado', 'Pendiente']], use_container_width=True)
        with st.form("pc"):
            s = st.selectbox("Pagar a:", df_c[df_c['Pendiente']>0]['Lote'] + " (" + df_c['Vendedor'] + ")")
            m = st.number_input("Monto:", min_value=0.0)
            if st.form_submit_button("PAGAR"):
                id_v = int(df_c[df_c['Lote'] + " (" + df_c['Vendedor'] + ")" == s]['id'].values[0])
                c.execute("INSERT INTO pagos_comisiones (id_venta, monto_pagado, fecha) VALUES (?,?,?)", (id_v, m, datetime.now().strftime('%Y-%m-%d')))
                conn.commit(); st.rerun()

# --- 6. COBRANZA ---
elif choice == "💸 Cobranza Clientes":
    st.header("💸 RECIBIR ABONOS")
    df_v = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote || ' - ' || c.nombre as l FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN clientes c ON v.id_cliente = c.id", conn)
    if not df_v.empty:
        with st.form("p"):
            s = st.selectbox("Lote:", df_v['l'])
            m = st.number_input("Monto:", min_value=0.0)
            if st.form_submit_button("REGISTRAR PAGO"):
                id_v = int(df_v[df_v['l'] == s]['id'].values[0])
                c.execute("INSERT INTO pagos (id_venta, monto, fecha) VALUES (?,?,?)", (id_v, m, datetime.now().strftime('%Y-%m-%d')))
                conn.commit(); st.success("Abono registrado"); st.rerun()

# --- 7. NUEVA VENTA ---
elif choice == "📝 Nueva Venta":
    st.header("📝 NUEVO CONTRATO")
    lt = pd.read_sql_query("SELECT * FROM terrenos WHERE estatus='Disponible'", conn)
    cl = pd.read_sql_query("SELECT * FROM clientes", conn)
    vn = pd.read_sql_query("SELECT * FROM vendedores", conn)
    if not lt.empty:
        with st.form("v"):
            lote = st.selectbox("Lote:", lt['manzana'] + "-" + lt['lote'])
            cli = st.selectbox("Cliente:", cl['nombre'])
            ven = st.selectbox("Vendedor:", vn['nombre'])
            eng = st.number_input("Enganche:", min_value=0.0)
            com = st.number_input("Comisión ($):", min_value=0.0)
            if st.form_submit_button("VENDER"):
                id_l = int(lt[lt['manzana'] + "-" + lt['lote'] == lote]['id'].values[0])
                id_c = int(cl[cl['nombre'] == cli]['id'].values[0])
                id_v = int(vn[vn['nombre'] == ven]['id'].values[0])
                costo = float(lt[lt['id'] == id_l]['costo'].values[0])
                mens = (costo - eng) / 48
                c.execute("INSERT INTO ventas (id_terreno, id_cliente, id_vendedor, enganche, meses, mensualidad, fecha, comision_total) VALUES (?,?,?,?,?,?,?,?)", 
                          (id_l, id_c, id_v, eng, 48, mens, datetime.now().strftime('%Y-%m-%d'), com))
                c.execute("UPDATE terrenos SET estatus='Vendido' WHERE id=?", (id_l,))
                conn.commit(); st.rerun()

# --- 8. CATÁLOGO ---
elif choice == "🏗️ Catálogo":
    st.header("🏗️ INVENTARIO")
    with st.form("t"):
        man = st.text_input("Manzana")
        lot = st.text_input("Lote")
        pre = st.number_input("Precio", min_value=0.0)
        if st.form_submit_button("Añadir"):
            c.execute("INSERT INTO terrenos (manzana, lote, costo) VALUES (?,?,?)", (man, lot, pre))
            conn.commit(); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT * FROM terrenos", conn), use_container_width=True)

# --- 9. DIRECTORIO ---
elif choice == "👥 Directorio":
    st.header("👥 CONTACTOS")
    n_c = st.text_input("Nuevo Cliente")
    if st.button("Guardar Cliente"):
        c.execute("INSERT INTO clientes (nombre) VALUES (?)", (n_c,))
        conn.commit(); st.rerun()
    n_v = st.text_input("Nuevo Vendedor")
    if st.button("Guardar Vendedor"):
        c.execute("INSERT INTO vendedores (nombre) VALUES (?)", (n_v,))
        conn.commit(); st.rerun()
