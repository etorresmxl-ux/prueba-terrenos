import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Inmobiliaria", layout="wide")

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
    except: return str(fecha_str)

def get_or_create_id(tabla, nombre_col, valor):
    valor = valor.strip()
    if not valor: return None
    c.execute(f"SELECT id FROM {tabla} WHERE {nombre_col} = ?", (valor,))
    result = c.fetchone()
    if result: return result[0]
    c.execute(f"INSERT INTO {tabla} ({nombre_col}) VALUES (?)", (valor,))
    conn.commit()
    return c.lastrowid

# --- FUNCIÓN DE ESTILO PARA EL RESUMEN ---
def color_atraso(row):
    dias = row['Días Atraso']
    if dias > 90:
        return ['background-color: #D35400; color: white'] * len(row)
    elif dias > 30:
        return ['background-color: #F4D03F; color: black'] * len(row)
    return [''] * len(row)

# --- MENÚ LATERAL ---
with st.sidebar:
    st.title("📂 Menú Principal")
    choice = st.radio(
        "Navegación",
        ["Resumen", "Nueva Venta", "Cobranza", "Detalle de Crédito", "Gestión de Contratos", "Comisiones", "Ubicaciones", "Directorio", "Gráficos"]
    )

# --- LÓGICA DE PÁGINAS ---

if choice == "Resumen":
    st.header("📋 Resumen General de Ventas")
    query = '''
        SELECT v.id, 'M'||t.manzana||'-L'||t.lote as Ubicación, c.nombre as Cliente, t.costo as Valor, 
        v.enganche as Enganche, v.fecha as [Fecha de Contrato], v.mensualidad, v.meses,
        IFNULL((SELECT SUM(monto) FROM pagos WHERE id_venta = v.id), 0) as PagosExtra,
        (SELECT MAX(fecha) FROM pagos WHERE id_venta = v.id) as [Fecha Ultimo Pago]
        FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id
    '''
    df_raw = pd.read_sql_query(query, conn)
    
    if not df_raw.empty:
        hoy = datetime.now()
        resultados = []
        for _, row in df_raw.iterrows():
            f_contrato = datetime.strptime(row['Fecha de Contrato'], '%Y-%m-%d')
            total_pagado = row['Enganche'] + row['PagosExtra']
            diff = relativedelta(hoy, f_contrato)
            meses_transcurridos = min(diff.years * 12 + diff.months, int(row['meses']))
            monto_obligatorio = meses_transcurridos * row['mensualidad']
            diferencia = monto_obligatorio - row['PagosExtra']
            
            dias_atraso = 0
            if diferencia > 1.0:
                meses_cubiertos = row['PagosExtra'] // row['mensualidad']
                f_vencimiento = f_contrato + relativedelta(months=int(meses_cubiertos) + 1)
                if hoy > f_vencimiento: dias_atraso = (hoy - f_vencimiento).days

            resultados.append({
                "Ubicación": row['Ubicación'], "Cliente": row['Cliente'], "Valor": row['Valor'],
                "Enganche": row['Enganche'], "Contrato": f_date_show(row['Fecha de Contrato']),
                "Total Pagado": total_pagado, "Último Pago": f_date_show(row['Fecha Ultimo Pago']) if row['Fecha Ultimo Pago'] else "N/A",
                "Estatus": "Al Corriente" if diferencia <= 1.0 else "Atrasado", 
                "Días Atraso": dias_atraso, "Para Corriente": max(0, diferencia)
            })
        
        df_final = pd.DataFrame(resultados)
        
        # Aplicar estilos y formatear monedas (el formateo se hace después del estilo para no perder el tipo numérico en el cálculo)
        styled_df = df_final.style.apply(color_atraso, axis=1).format({
            "Valor": f_money, "Enganche": f_money, "Total Pagado": f_money, "Para Corriente": f_money
        })
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        st.caption("💡 Amarillo > 30 días | Naranja > 90 días")
    else:
        st.info("No hay registros de ventas.")

elif choice == "Detalle de Crédito":
    st.header("🔍 Estado de Cuenta Individual")
    df_u = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote || ' - ' || c.nombre as info FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN clientes c ON v.id_cliente = c.id", conn)
    if not df_u.empty:
        sel_u = st.selectbox("Seleccione Contrato:", df_u['info'])
        vid = int(df_u[df_u['info'] == sel_u]['id'].values[0])
        res = pd.read_sql_query(f'''
            SELECT v.*, c.nombre, 'M'||t.manzana||'-L'||t.lote as u, t.costo,
            IFNULL((SELECT SUM(monto) FROM pagos WHERE id_venta = v.id), 0) as total_abonos
            FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id
            WHERE v.id = {vid}''', conn).iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Ubicación", res['u']); col1.metric("Valor Total", f_money(res['costo']))
        col2.metric("Cliente", res['nombre']); col2.metric("Enganche", f_money(res['enganche']))
        col3.metric("Fecha Contrato", f_date_show(res['fecha'])); col3.metric("Total Pagado", f_money(res['enganche'] + res['total_abonos']))
        col4.metric("Saldo Pendiente", f_money(res['costo'] - (res['enganche'] + res['total_abonos'])))
        
        st.markdown("---")
        pagos_reales = pd.read_sql_query(f"SELECT monto, fecha FROM pagos WHERE id_venta = {vid} ORDER BY fecha ASC", conn)
        tabla_amort = []; abonos_acumulados = res['total_abonos']; f_inicio = datetime.strptime(res['fecha'], '%Y-%m-%d')
        
        for i in range(1, int(res['meses']) + 1):
            f_venc = f_inicio + relativedelta(months=i)
            cuota = res['mensualidad']
            if abonos_acumulados >= cuota:
                estatus, f_p_real, imp_p = "✅ Pagado", f_date_show(pagos_reales.iloc[i-1]['fecha']) if (i-1) < len(pagos_reales) else "Acumulado", f_money(cuota)
                abonos_acumulados -= cuota
            elif abonos_acumulados > 0:
                estatus, f_p_real, imp_p = "🟡 Parcial", "Pendiente", f_money(abonos_acumulados)
                abonos_acumulados = 0
            else:
                estatus, f_p_real, imp_p = "🔴 Pendiente", "---", f_money(0)
            
            tabla_amort.append({"Mes": i, "Vencimiento": f_date_show(f_venc.strftime('%Y-%m-%d')), "Importe Mes": f_money(cuota), "Estatus": estatus, "Fecha de Pago": f_p_real, "Monto Pagado": imp_p})
        st.dataframe(pd.DataFrame(tabla_amort), use_container_width=True, hide_index=True)

elif choice == "Nueva Venta":
    st.header("📝 Registro de Nueva Venta")
    lt = pd.read_sql_query("SELECT * FROM terrenos WHERE estatus='Disponible'", conn)
    if not lt.empty:
        with st.form("nv"):
            c1, c2 = st.columns(2)
            l_sel = c1.selectbox("Lote:", lt['manzana'] + "-" + lt['lote'])
            c_nom = c1.text_input("Nombre del Cliente:")
            v_nom = c1.text_input("Nombre del Vendedor:")
            p_cat = float(lt[lt['manzana'] + "-" + lt['lote'] == l_sel]['costo'].values[0])
            costo = c2.number_input("Precio Final ($):", value=p_cat)
            eng = c2.number_input("Enganche ($):")
            plz = c2.number_input("Plazo (Meses):", value=48)
            f_cont = c1.date_input("Fecha de Contrato", datetime.now())
            com_t = c2.number_input("Comisión Total ($):", value=0.0)
            if st.form_submit_button("Registrar Venta"):
                if c_nom and v_nom:
                    id_c = get_or_create_id('clientes', 'nombre', c_nom)
                    id_v = get_or_create_id('vendedores', 'nombre', v_nom)
                    id_l = int(lt[lt['manzana'] + "-" + lt['lote'] == l_sel]['id'].values[0])
                    m = (costo - eng) / plz
                    c.execute("INSERT INTO ventas (id_terreno, id_cliente, id_vendedor, enganche, meses, mensualidad, fecha, comision_total) VALUES (?,?,?,?,?,?,?,?)", (id_l, id_c, id_v, eng, plz, m, f_cont.strftime('%Y-%m-%d'), com_t))
                    c.execute("UPDATE terrenos SET estatus='Vendido', costo=? WHERE id=?", (costo, id_l))
                    conn.commit(); st.rerun()

elif choice == "Gestión de Contratos":
    st.header("⚙️ Edición de Contratos")
    df_g = pd.read_sql_query('''SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u, c.nombre as cli, vn.nombre as vend, t.costo, v.enganche, v.meses, v.fecha, v.comision_total, v.id_terreno FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN vendedores vn ON v.id_vendedor = vn.id JOIN terrenos t ON v.id_terreno = t.id''', conn)
    if not df_g.empty:
        sel = st.selectbox("Contrato:", df_g['u'] + " - " + df_g['cli'])
        datos = df_g[df_g['u'] + " - " + df_g['cli'] == sel].iloc[0]
        with st.form("edit"):
            c1, c2 = st.columns(2)
            nc = c1.text_input("Cliente", value=datos['cli']); nv = c1.text_input("Vendedor", value=datos['vend'])
            nf = c1.date_input("Fecha", value=datetime.strptime(datos['fecha'], '%Y-%m-%d'))
            ncos = c2.number_input("Valor", value=float(datos['costo'])); neng = c2.number_input("Enganche", value=float(datos['enganche']))
            npla = c2.number_input("Plazo", value=int(datos['meses'])); ncom = c2.number_input("Comisión", value=float(datos['comision_total']))
            if st.form_submit_button("Actualizar"):
                id_c = get_or_create_id('clientes', 'nombre', nc); id_v = get_or_create_id('vendedores', 'nombre', nv)
                m = (ncos - neng) / npla
                c.execute("UPDATE ventas SET id_cliente=?, id_vendedor=?, enganche=?, meses=?, mensualidad=?, fecha=?, comision_total=? WHERE id=?", (id_c, id_v, neng, npla, m, nf.strftime('%Y-%m-%d'), ncom, int(datos['id'])))
                c.execute("UPDATE terrenos SET costo=? WHERE id=?", (ncos, int(datos['id_terreno'])))
                conn.commit(); st.rerun()
        if st.button("Eliminar Contrato"):
            c.execute("DELETE FROM ventas WHERE id=?", (int(datos['id']),)); c.execute("UPDATE terrenos SET estatus='Disponible' WHERE id=?", (int(datos['id_terreno']),))
            conn.commit(); st.rerun()

elif choice == "Cobranza":
    st.header("💸 Cobranza")
    df_v = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote || ' - ' || c.nombre as l FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN clientes c ON v.id_cliente = c.id", conn)
    if not df_v.empty:
        with st.form("pago"):
            s = st.selectbox("Contrato:", df_v['l']); m = st.number_input("Monto:", format="%.2f"); f_pago = st.date_input("Fecha", datetime.now())
            if st.form_submit_button("Confirmar"):
                id_v = int(df_v[df_v['l'] == s]['id'].values[0])
                c.execute("INSERT INTO pagos (id_venta, monto, fecha) VALUES (?,?,?)", (id_v, m, f_pago.strftime('%Y-%m-%d')))
                conn.commit(); st.rerun()

elif choice == "Ubicaciones":
    st.header("📍 Ubicaciones")
    with st.form("cat"):
        m, l, p = st.columns(3); ma = m.text_input("Manzana"); lo = l.text_input("Lote"); pr = p.number_input("Precio ($)")
        if st.form_submit_button("Añadir"):
            c.execute("INSERT INTO terrenos (manzana, lote, costo) VALUES (?,?,?)", (ma, lo, pr)); conn.commit(); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT manzana, lote, costo, estatus FROM terrenos", conn), use_container_width=True, hide_index=True)

elif choice == "Directorio":
    st.header("👥 Directorio")
    c1, c2 = st.columns(2)
    c1.subheader("Clientes"); c1.dataframe(pd.read_sql_query("SELECT nombre FROM clientes ORDER BY nombre", conn), hide_index=True, use_container_width=True)
    c2.subheader("Vendedores"); c2.dataframe(pd.read_sql_query("SELECT nombre FROM vendedores ORDER BY nombre", conn), hide_index=True, use_container_width=True)

elif choice == "Comisiones":
    st.header("🤝 Comisiones")
    st.dataframe(pd.read_sql_query("SELECT vn.nombre as Vendedor, 'M'||t.manzana||'-L'||t.lote as Lote, v.comision_total as Total FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN vendedores vn ON v.id_vendedor = vn.id", conn), use_container_width=True, hide_index=True)

elif choice == "Gráficos":
    st.header("📈 Desempeño")
    df_g = pd.read_sql_query("SELECT vn.nombre as Vendedor, SUM(t.costo) as Total FROM ventas v JOIN vendedores vn ON v.id_vendedor = vn.id JOIN terrenos t ON v.id_terreno = t.id GROUP BY vn.nombre", conn)
    if not df_g.empty: st.bar_chart(data=df_g, x="Vendedor", y="Total")
