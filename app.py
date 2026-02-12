import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Inmobiliaria Pro v30", layout="wide")

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
    if not valor: return None
    c.execute(f"SELECT id FROM {tabla} WHERE {nombre_col} = ?", (valor,))
    result = c.fetchone()
    if result: return result[0]
    c.execute(f"INSERT INTO {tabla} ({nombre_col}) VALUES (?)", (valor,))
    conn.commit()
    return c.lastrowid

# --- MENÚ LATERAL (ESTÁNDAR) ---
with st.sidebar:
    st.title("📂 Sistema Inmobiliario")
    choice = st.radio(
        "Navegación",
        ["Resumen", "Nueva Venta", "Cobranza", "Detalle de Crédito", "Gestión de Contratos", "Comisiones", "Ubicaciones", "Directorio", "Gráficos"]
    )

# --- LÓGICA DE PÁGINAS ---

if choice == "Resumen":
    st.header("📋 Resumen General de Ventas")
    df = pd.read_sql_query('''
        SELECT v.id, 'M'||t.manzana||'-L'||t.lote as Lote, c.nombre as Cliente, 
        t.costo as [Valor Venta], v.enganche as Enganche, v.fecha, 
        IFNULL((SELECT SUM(monto) FROM pagos WHERE id_venta = v.id), 0) as pagos_abonos
        FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id
    ''', conn)
    if not df.empty:
        df['Contrato'] = df['fecha'].apply(f_date_show)
        df['Total Pagado'] = (df['Enganche'] + df['pagos_abonos']).apply(f_money)
        df['Saldo'] = (df['Valor Venta'] - (df['Enganche'] + df['pagos_abonos'])).apply(f_money)
        df['Valor Venta'] = df['Valor Venta'].apply(f_money)
        df['Enganche'] = df['Enganche'].apply(f_money)
        st.dataframe(df[['Lote', 'Cliente', 'Valor Venta', 'Enganche', 'Contrato', 'Total Pagado', 'Saldo']], use_container_width=True, hide_index=True)
    else:
        st.info("No hay registros disponibles.")

elif choice == "Nueva Venta":
    st.header("📝 Registro de Nueva Venta")
    lt = pd.read_sql_query("SELECT * FROM terrenos WHERE estatus='Disponible'", conn)
    if lt.empty:
        st.warning("No hay lotes disponibles en el catálogo.")
    else:
        with st.form("form_venta"):
            col1, col2 = st.columns(2)
            lote_sel = col1.selectbox("Seleccione Lote:", lt['manzana'] + "-" + lt['lote'])
            cliente_nom = col1.text_input("Nombre del Cliente:")
            vendedor_nom = col1.text_input("Nombre del Vendedor:")
            
            p_sugerido = float(lt[lt['manzana'] + "-" + lt['lote'] == lote_sel]['costo'].values[0])
            precio_real = col2.number_input("Precio de Venta Final ($):", value=p_sugerido)
            enganche = col2.number_input("Enganche Recibido ($):", min_value=0.0)
            plazo = col2.number_input("Plazo en Meses:", value=48, min_value=1)
            
            if st.form_submit_button("Finalizar Venta"):
                if cliente_nom and vendedor_nom:
                    id_c = get_or_create_id('clientes', 'nombre', cliente_nom)
                    id_v = get_or_create_id('vendedores', 'nombre', vendedor_nom)
                    id_l = int(lt[lt['manzana'] + "-" + lt['lote'] == lote_sel]['id'].values[0])
                    mensualidad = (precio_real - enganche) / plazo
                    
                    c.execute('''INSERT INTO ventas (id_terreno, id_cliente, id_vendedor, enganche, meses, mensualidad, fecha, comision_total) 
                                 VALUES (?,?,?,?,?,?,?,0)''', (id_l, id_c, id_v, enganche, plazo, mensualidad, datetime.now().strftime('%Y-%m-%d')))
                    c.execute("UPDATE terrenos SET estatus='Vendido', costo=? WHERE id=?", (precio_real, id_l))
                    conn.commit()
                    st.success("Venta guardada exitosamente.")
                    st.rerun()

elif choice == "Gestión de Contratos":
    st.header("⚙️ Edición y Gestión de Contratos")
    df_g = pd.read_sql_query('''
        SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u, c.nombre as cli, vn.nombre as vend, 
        t.costo, v.enganche, v.meses, v.comision_total, v.fecha, v.id_terreno 
        FROM ventas v JOIN clientes c ON v.id_cliente = c.id 
        JOIN vendedores vn ON v.id_vendedor = vn.id JOIN terrenos t ON v.id_terreno = t.id
    ''', conn)
    
    if not df_g.empty:
        sel = st.selectbox("Seleccione Contrato:", df_g['u'] + " - " + df_g['cli'])
        datos = df_g[df_g['u'] + " - " + df_g['cli'] == sel].iloc[0]
        
        with st.form("edit"):
            c1, c2 = st.columns(2)
            n_cli = c1.text_input("Cliente", value=datos['cli'])
            n_ven = c1.text_input("Vendedor", value=datos['vend'])
            n_fec = c1.date_input("Fecha", value=datetime.strptime(datos['fecha'], '%Y-%m-%d'))
            n_cos = c2.number_input("Costo", value=float(datos['costo']))
            n_eng = c2.number_input("Enganche", value=float(datos['enganche']))
            n_pla = c2.number_input("Meses", value=int(datos['meses']))
            
            if st.form_submit_button("Guardar Cambios"):
                id_c = get_or_create_id('clientes', 'nombre', n_cli)
                id_v = get_or_create_id('vendedores', 'nombre', n_ven)
                n_men = (n_cos - n_eng) / n_pla
                c.execute('''UPDATE ventas SET id_cliente=?, id_vendedor=?, enganche=?, meses=?, mensualidad=?, fecha=? WHERE id=?''', 
                          (id_c, id_v, n_eng, n_pla, n_men, n_fec.strftime('%Y-%m-%d'), int(datos['id'])))
                c.execute("UPDATE terrenos SET costo=? WHERE id=?", (n_cos, int(datos['id_terreno'])))
                conn.commit(); st.success("Actualizado"); st.rerun()
        
        if st.button("Eliminar Contrato Definitivamente"):
            c.execute("DELETE FROM ventas WHERE id=?", (int(datos['id']),))
            c.execute("UPDATE terrenos SET estatus='Disponible' WHERE id=?", (int(datos['id_terreno']),))
            conn.commit(); st.rerun()

elif choice == "Detalle de Crédito":
    st.header("🔍 Tabla de Amortización")
    df_u = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u FROM ventas v JOIN terrenos t ON v.id_terreno = t.id", conn)
    if not df_u.empty:
        sel_u = st.selectbox("Lote:", df_u['u'])
        vid = int(df_u[df_u['u'] == sel_u]['id'].values[0])
        res = pd.read_sql_query(f"SELECT * FROM ventas v JOIN clientes c ON v.id_cliente=c.id JOIN terrenos t ON v.id_terreno=t.id WHERE v.id={vid}", conn).iloc[0]
        
        st.write(f"**Cliente:** {res['nombre']} | **Mensualidad:** {f_money(res['mensualidad'])}")
        tabla = []; saldo = res['costo'] - res['enganche']
        for i in range(1, int(res['meses']) + 1):
            saldo -= res['mensualidad']
            tabla.append({"Mes": i, "Pago": f_money(res['mensualidad']), "Saldo": f_money(max(0, saldo))})
        st.table(tabla[:24])

elif choice == "Cobranza":
    st.header("💸 Registro de Abonos")
    df_v = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote || ' - ' || c.nombre as l FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN clientes c ON v.id_cliente = c.id", conn)
    if not df_v.empty:
        with st.form("pago"):
            s = st.selectbox("Contrato:", df_v['l'])
            m = st.number_input("Monto:", format="%.2f")
            if st.form_submit_button("Registrar"):
                id_v = int(df_v[df_v['l'] == s]['id'].values[0])
                c.execute("INSERT INTO pagos (id_venta, monto, fecha) VALUES (?,?,?)", (id_v, m, datetime.now().strftime('%Y-%m-%d')))
                conn.commit(); st.success("Abono registrado"); st.rerun()

elif choice == "Ubicaciones":
    st.header("📍 Catálogo de Lotes")
    with st.form("cat"):
        m, l, p = st.columns(3)
        ma = m.text_input("Manzana"); lo = l.text_input("Lote"); pr = p.number_input("Precio ($)")
        if st.form_submit_button("Agregar"):
            c.execute("INSERT INTO terrenos (manzana, lote, costo) VALUES (?,?,?)", (ma, lo, pr)); conn.commit(); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT manzana, lote, costo, estatus FROM terrenos", conn), use_container_width=True)

elif choice == "Directorio":
    st.header("👥 Directorio")
    c1, c2 = st.columns(2)
    c1.subheader("Clientes"); c1.dataframe(pd.read_sql_query("SELECT nombre FROM clientes ORDER BY nombre", conn), hide_index=True)
    c2.subheader("Vendedores"); c2.dataframe(pd.read_sql_query("SELECT nombre FROM vendedores ORDER BY nombre", conn), hide_index=True)

elif choice == "Comisiones":
    st.header("🤝 Reporte de Comisiones")
    df_c = pd.read_sql_query('''SELECT 'M'||t.manzana||'-L'||t.lote as Lote, vn.nombre as Vendedor, v.comision_total as Total 
                                FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN vendedores vn ON v.id_vendedor = vn.id''', conn)
    st.dataframe(df_c, use_container_width=True)

elif choice == "Gráficos":
    st.header("📈 Desempeño")
    df_g = pd.read_sql_query('''SELECT vn.nombre as Vendedor, SUM(t.costo) as Total FROM ventas v JOIN vendedores vn ON v.id_vendedor = vn.id JOIN terrenos t ON v.id_terreno = t.id GROUP BY vn.nombre''', conn)
    if not df_g.empty: st.bar_chart(data=df_g, x="Vendedor", y="Total")
