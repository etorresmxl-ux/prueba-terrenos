import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Inmobiliaria Premium v29", layout="wide")

# --- ESTILO CSS (Sencillo y Alineado a la Izquierda) ---
st.markdown("""
    <style>
    /* Fondo principal y sidebar */
    [data-testid="stAppViewContainer"] {
        background-color: #12141d;
    }
    [data-testid="stSidebar"] {
        background-color: #1c1e26;
    }
    
    /* Estilo para los títulos del menú */
    .menu-title {
        color: #888888;
        font-size: 0.8rem;
        font-weight: bold;
        margin-top: 20px;
        margin-bottom: 10px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Estilo de Tarjetas y Tablas */
    div.stForm, div[data-testid="stExpander"], .stTable {
        background-color: #252836 !important;
        border: 1px solid #323545 !important;
        border-radius: 12px !important;
    }
    
    /* Forzar color de texto en inputs para modo oscuro */
    input, select, .stSelectbox div {
        color: white !important;
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

# --- FUNCIONES DE APOYO ---
def f_money(v): return f"${float(v or 0):,.2f}"

def f_date_show(fecha_str):
    try: return datetime.strptime(fecha_str, '%Y-%m-%d').strftime('%d-%m-%Y')
    except: return fecha_str

def get_or_create_id(tabla, nombre_col, valor):
    valor = valor.strip()
    c.execute(f"SELECT id FROM {tabla} WHERE {nombre_col} = ?", (valor,))
    result = c.fetchone()
    if result: return result[0]
    c.execute(f"INSERT INTO {tabla} ({nombre_col}) VALUES (?)", (valor,))
    conn.commit()
    return c.lastrowid

# --- MENÚ LATERAL (ESTILO BÁSICO ALINEADO A LA IZQUIERDA) ---
with st.sidebar:
    st.markdown("<h2 style='color: white;'>💎 MENÚ</h2>", unsafe_allow_html=True)
    
    st.markdown('<p class="menu-title">Reportes</p>', unsafe_allow_html=True)
    choice = st.radio(
        "Seleccione una opción:",
        ["🏠 Resumen", "🤝 Comisiones", "📈 Gráficos", "📝 Nueva Venta", "💸 Cobranza", "🔍 Detalle de Crédito", "⚙️ Gestión", "📍 Ubicaciones", "👥 Directorio"],
        label_visibility="collapsed"
    )

# --- LÓGICA DE PÁGINAS ---

if choice == "🏠 Resumen":
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
        df['Valor Venta'] = df['Valor Venta'].apply(f_money); df['Enganche'] = df['Enganche'].apply(f_money)
        st.dataframe(df[['Lote', 'Cliente', 'Valor Venta', 'Enganche', 'Contrato', 'Total Pagado', 'Saldo Hoy']], use_container_width=True, hide_index=True)
    else: st.info("No hay ventas registradas.")

elif choice == "⚙️ Gestión":
    st.header("⚙️ GESTIÓN Y EDICIÓN DE CONTRATOS")
    df_g = pd.read_sql_query('''
        SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u, c.nombre as cli, vn.nombre as vend, 
        t.costo, v.enganche, v.meses, v.comision_total, v.fecha, v.id_terreno 
        FROM ventas v JOIN clientes c ON v.id_cliente = c.id 
        JOIN vendedores vn ON v.id_vendedor = vn.id JOIN terrenos t ON v.id_terreno = t.id
    ''', conn)
    
    if not df_g.empty:
        sel_contrato = st.selectbox("Seleccione contrato para Editar o Eliminar:", df_g['u'] + " - " + df_g['cli'])
        datos = df_g[df_g['u'] + " - " + df_g['cli'] == sel_contrato].iloc[0]
        
        with st.form("edit_form"):
            col1, col2 = st.columns(2)
            new_cli = col1.text_input("Cliente", value=datos['cli'])
            new_vend = col1.text_input("Vendedor", value=datos['vend'])
            new_fecha = col1.date_input("Fecha", value=datetime.strptime(datos['fecha'], '%Y-%m-%d'))
            new_costo = col2.number_input("Valor Venta ($)", value=float(datos['costo']))
            new_enganche = col2.number_input("Enganche ($)", value=float(datos['enganche']))
            new_plazo = col2.number_input("Plazo (Meses)", value=int(datos['meses']))
            new_comision = col2.number_input("Comisión ($)", value=float(datos['comision_total']))
            
            if st.form_submit_button("💾 GUARDAR CAMBIOS"):
                id_c = get_or_create_id('clientes', 'nombre', new_cli)
                id_v = get_or_create_id('vendedores', 'nombre', new_vend)
                new_mensu = (new_costo - new_enganche) / new_plazo
                c.execute('''UPDATE ventas SET id_cliente=?, id_vendedor=?, enganche=?, meses=?, mensualidad=?, fecha=?, comision_total=? 
                             WHERE id=?''', (id_c, id_v, new_enganche, new_plazo, new_mensu, new_fecha.strftime('%Y-%m-%d'), new_comision, int(datos['id'])))
                c.execute("UPDATE terrenos SET costo=? WHERE id=?", (new_costo, int(datos['id_terreno'])))
                conn.commit(); st.success("✅ Actualizado"); st.rerun()

        if st.button("🗑️ ELIMINAR CONTRATO"):
            c.execute("DELETE FROM ventas WHERE id=?", (int(datos['id']),)); c.execute("UPDATE terrenos SET estatus='Disponible' WHERE id=?", (int(datos['id_terreno']),))
            conn.commit(); st.rerun()

elif choice == "📝 Nueva Venta":
    st.header("📝 REGISTRAR NUEVO CONTRATO")
    lt = pd.read_sql_query("SELECT * FROM terrenos WHERE estatus='Disponible'", conn)
    if lt.empty: st.warning("No hay lotes disponibles.")
    else:
        with st.form("nv"):
            col1, col2 = st.columns(2)
            l_sel = col1.selectbox("Lote:", lt['manzana'] + "-" + lt['lote'])
            c_nombre = col1.text_input("Cliente:")
            v_nombre = col1.text_input("Vendedor:")
            p_cat = float(lt[lt['manzana'] + "-" + lt['lote'] == l_sel]['costo'].values[0])
            costo_v = col2.number_input("Precio Real ($)", value=p_cat)
            eng_v = col2.number_input("Enganche ($)")
            plz_v = col2.number_input("Plazo (Meses)", value=48)
            if st.form_submit_button("CERRAR VENTA"):
                if c_nombre and v_nombre:
                    id_c = get_or_create_id('clientes', 'nombre', c_nombre)
                    id_v = get_or_create_id('vendedores', 'nombre', v_nombre)
                    id_l = int(lt[lt['manzana'] + "-" + lt['lote'] == l_sel]['id'].values[0])
                    mensu = (costo_v - eng_v) / plz_v
                    c.execute('''INSERT INTO ventas (id_terreno, id_cliente, id_vendedor, enganche, meses, mensualidad, fecha, comision_total) 
                                 VALUES (?,?,?,?,?,?,?,0)''', (id_l, id_c, id_v, eng_v, plz_v, mensu, datetime.now().strftime('%Y-%m-%d')))
                    c.execute("UPDATE terrenos SET estatus='Vendido', costo=? WHERE id=?", (costo_v, id_l))
                    conn.commit(); st.success("Venta registrada"); st.rerun()

elif choice == "🔍 Detalle de Crédito":
    st.header("🔍 DETALLE POR LOTE")
    df_u = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u FROM ventas v JOIN terrenos t ON v.id_terreno = t.id", conn)
    if not df_u.empty:
        sel_u = st.selectbox("Seleccione el Lote:", df_u['u'])
        vid = int(df_u[df_u['u'] == sel_u]['id'].values[0])
        res = pd.read_sql_query(f'''SELECT c.nombre, t.costo, v.enganche, v.fecha, v.meses, v.mensualidad 
                                    FROM ventas v JOIN clientes c ON v.id_cliente = c.id 
                                    JOIN terrenos t ON v.id_terreno = t.id WHERE v.id = {vid}''', conn).iloc[0]
        st.subheader(f"Cliente: {res['nombre']}")
        tabla = []; saldo = res['costo'] - res['enganche']
        for i in range(1, int(res['meses']) + 1):
            saldo -= res['mensualidad']
            tabla.append({"Mes": i, "Cuota": f_money(res['mensualidad']), "Saldo Restante": f_money(max(0, saldo))})
        st.table(tabla[:24])

elif choice == "💸 Cobranza":
    st.header("💸 RECIBIR ABONOS")
    df_v = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote || ' - ' || c.nombre as l FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN clientes c ON v.id_cliente = c.id", conn)
    if not df_v.empty:
        with st.form("cob"):
            s = st.selectbox("Contrato:", df_v['l'])
            m = st.number_input("Monto ($)", format="%.2f")
            if st.form_submit_button("REGISTRAR PAGO"):
                id_v = int(df_v[df_v['l'] == s]['id'].values[0])
                c.execute("INSERT INTO pagos (id_venta, monto, fecha) VALUES (?,?,?)", (id_v, m, datetime.now().strftime('%Y-%m-%d')))
                conn.commit(); st.success("Pago guardado"); st.rerun()

elif choice == "🤝 Comisiones":
    st.header("🤝 REPORTE DE COMISIONES")
    df_c = pd.read_sql_query('''SELECT v.id, 'M'||t.manzana||'-L'||t.lote as Lote, vn.nombre as Vendedor, v.comision_total as Total,
                                IFNULL((SELECT SUM(monto_pagado) FROM pagos_comisiones WHERE id_venta = v.id), 0) as Pagado
                                FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN vendedores vn ON v.id_vendedor = vn.id''', conn)
    if not df_c.empty:
        df_c['Pendiente'] = df_c['Total'] - df_c['Pagado']
        st.dataframe(df_c[['Lote', 'Vendedor', 'Total', 'Pagado', 'Pendiente']], use_container_width=True, hide_index=True)

elif choice == "📈 Gráficos":
    st.header("📈 VENTAS POR VENDEDOR")
    df_g = pd.read_sql_query('''SELECT vn.nombre as Vendedor, SUM(t.costo) as Total FROM ventas v JOIN vendedores vn ON v.id_vendedor = vn.id JOIN terrenos t ON v.id_terreno = t.id GROUP BY vn.nombre''', conn)
    if not df_g.empty: st.bar_chart(data=df_g, x="Vendedor", y="Total")

elif choice == "📍 Ubicaciones":
    st.header("📍 CATÁLOGO")
    with st.form("cat"):
        m, l, p = st.columns(3)
        ma = m.text_input("Manzana"); lo = l.text_input("Lote"); pr = p.number_input("Precio ($)")
        if st.form_submit_button("Guardar"):
            c.execute("INSERT INTO terrenos (manzana, lote, costo) VALUES (?,?,?)", (ma, lo, pr)); conn.commit(); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT manzana, lote, costo, estatus FROM terrenos", conn), use_container_width=True)

elif choice == "👥 Directorio":
    st.header("👥 DIRECTORIO")
    c1, c2 = st.columns(2)
    with c1: st.subheader("Clientes"); st.dataframe(pd.read_sql_query("SELECT nombre FROM clientes", conn), hide_index=True)
    with c2: st.subheader("Vendedores"); st.dataframe(pd.read_sql_query("SELECT nombre FROM vendedores", conn), hide_index=True)
