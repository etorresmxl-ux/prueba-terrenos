import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Inmobiliaria", layout="wide")

# --- SEGURIDAD ---
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

def color_atraso(row):
    dias = row['Días Atraso']
    if dias > 90: return ['background-color: #D35400; color: white'] * len(row)
    elif dias > 30: return ['background-color: #F4D03F; color: black'] * len(row)
    return [''] * len(row)

# --- MENÚ LATERAL ---
with st.sidebar:
    st.title("📂 Menú Principal")
    choice = st.radio("Navegación", ["Resumen", "Nueva Venta", "Cobranza", "Gestión de Pagos", "Detalle de Crédito", "Gestión de Contratos", "Ubicaciones", "Directorio"])

# --- PÁGINA: RESUMEN ---
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
            diferencia = (meses_transcurridos * row['mensualidad']) - row['PagosExtra']
            dias_atraso = 0
            if diferencia > 1.0:
                meses_cubiertos = row['PagosExtra'] // row['mensualidad']
                f_venc = f_contrato + relativedelta(months=int(meses_cubiertos) + 1)
                if hoy > f_venc: dias_atraso = (hoy - f_venc).days
            resultados.append({
                "Ubicación": row['Ubicación'], "Cliente": row['Cliente'], "Valor": row['Valor'],
                "Enganche": row['Enganche'], "Contrato": f_date_show(row['Fecha de Contrato']),
                "Total Pagado": total_pagado, "Último Pago": f_date_show(row['Fecha Ultimo Pago']) if row['Fecha Ultimo Pago'] else "N/A",
                "Estatus": "Al Corriente" if diferencia <= 1.0 else "Atrasado", "Días Atraso": dias_atraso, "Para Corriente": max(0, diferencia)
            })
        st.dataframe(pd.DataFrame(resultados).style.apply(color_atraso, axis=1).format({"Valor": f_money, "Enganche": f_money, "Total Pagado": f_money, "Para Corriente": f_money}), use_container_width=True, hide_index=True)

# --- PÁGINA: GESTIÓN DE PAGOS ---
elif choice == "Gestión de Pagos":
    st.header("⚙️ Editor Maestro de Pagos")
    st.info("Haz clic en Fecha o Monto para editar. Marca Eliminar para borrar.")
    f1, f2 = st.columns(2)
    f_cli, f_loc = f1.text_input("Buscar Cliente:"), f2.text_input("Buscar Ubicación:")
    query = "SELECT p.id, p.fecha as Fecha, c.nombre as Cliente, 'M'||t.manzana||'-L'||t.lote as Ubicación, p.monto as Monto FROM pagos p JOIN ventas v ON p.id_venta = v.id JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id"
    df_p = pd.read_sql_query(query, conn)
    if not df_p.empty:
        if f_cli: df_p = df_p[df_p['Cliente'].str.contains(f_cli, case=False)]
        if f_loc: df_p = df_p[df_p['Ubicación'].str.contains(f_loc, case=False)]
        df_p['Eliminar'] = False
        edited_df = st.data_editor(df_p, column_config={"id": None, "Fecha": st.column_config.TextColumn("Fecha (AAAA-MM-DD)"), "Monto": st.column_config.NumberColumn("Importe ($)", format="$%.2f"), "Cliente": st.column_config.TextColumn("Cliente", disabled=True), "Ubicación": st.column_config.TextColumn("Ubicación", disabled=True), "Eliminar": st.column_config.CheckboxColumn("Eliminar?")}, hide_index=True, use_container_width=True)
        if st.button("💾 Aplicar Cambios"):
            for index, row in edited_df.iterrows():
                orig = df_p.iloc[index]
                if row['Eliminar']: c.execute("DELETE FROM pagos WHERE id = ?", (int(row['id']),))
                elif row['Fecha'] != orig['Fecha'] or row['Monto'] != orig['Monto']:
                    try: 
                        datetime.strptime(row['Fecha'], '%Y-%m-%d')
                        c.execute("UPDATE pagos SET fecha = ?, monto = ? WHERE id = ?", (row['Fecha'], row['Monto'], int(row['id'])))
                    except: st.error(f"Fecha inválida en {row['Cliente']}")
            conn.commit(); st.success("Sincronizado"); st.rerun()

# --- PÁGINA: DETALLE DE CRÉDITO (CON MENSUALIDAD AGREGADA) ---
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
        
        # FILA DE MÉTRICAS (Datos Generales con Mensualidad)
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Ubicación", res['u'])
        m1.metric("Valor Total", f_money(res['costo']))
        
        m2.metric("Cliente", res['nombre'])
        m2.metric("Enganche", f_money(res['enganche']))
        
        m3.metric("Fecha Contrato", f_date_show(res['fecha']))
        m3.metric("Mensualidad", f_money(res['mensualidad'])) # <--- NUEVO CAMPO
        
        m4.metric("Plazo", f"{int(res['meses'])} meses")
        m4.metric("Total Pagado", f_money(res['enganche'] + res['total_abonos']))
        
        m5.metric("Saldo Pendiente", f_money(res['costo'] - (res['enganche'] + res['total_abonos'])))
        
        st.markdown("---")
        # TABLA DE AMORTIZACIÓN
        pagos_reales = pd.read_sql_query(f"SELECT monto, fecha FROM pagos WHERE id_venta = {vid} ORDER BY fecha ASC", conn)
        tabla_amort = []; abonos_acum = res['total_abonos']; f_ini = datetime.strptime(res['fecha'], '%Y-%m-%d')
        for i in range(1, int(res['meses']) + 1):
            f_v = f_ini + relativedelta(months=i); cuota = res['mensualidad']
            if abonos_acum >= cuota:
                est, f_p, imp = "✅ Pagado", f_date_show(pagos_reales.iloc[i-1]['fecha']) if (i-1) < len(pagos_reales) else "Acumulado", f_money(cuota); abonos_acum -= cuota
            elif abonos_acum > 0:
                est, f_p, imp = "🟡 Parcial", "Pendiente", f_money(abonos_acum); abonos_acum = 0
            else: est, f_p, imp = "🔴 Pendiente", "---", f_money(0)
            tabla_amort.append({"Mes": i, "Vencimiento": f_date_show(f_v.strftime('%Y-%m-%d')), "Cuota": f_money(cuota), "Estatus": est, "Fecha Pago": f_p, "Pagado": imp})
        st.dataframe(pd.DataFrame(tabla_amort), use_container_width=True, hide_index=True)

# --- PÁGINA: NUEVA VENTA ---
elif choice == "Nueva Venta":
    st.header("📝 Registro de Nueva Venta")
    lt = pd.read_sql_query("SELECT * FROM terrenos WHERE estatus='Disponible'", conn)
    c_list = ["+ Añadir nuevo..."] + sorted(pd.read_sql_query("SELECT nombre FROM clientes", conn)['nombre'].tolist())
    v_list = ["+ Añadir nuevo..."] + sorted(pd.read_sql_query("SELECT nombre FROM vendedores", conn)['nombre'].tolist())
    if not lt.empty:
        with st.form("nv"):
            col1, col2 = st.columns(2)
            l_sel = col1.selectbox("Lote:", lt['manzana'] + "-" + lt['lote'])
            c_sel = col1.selectbox("Cliente:", c_list)
            c_new = col1.text_input("Nombre nuevo cliente:") if c_sel == "+ Añadir nuevo..." else ""
            v_sel = col1.selectbox("Vendedor:", v_list)
            v_new = col1.text_input("Nombre nuevo vendedor:") if v_sel == "+ Añadir nuevo..." else ""
            p_cat = float(lt[lt['manzana'] + "-" + lt['lote'] == l_sel]['costo'].values[0])
            costo = col2.number_input("Precio Final:", value=p_cat); eng = col2.number_input("Enganche:"); plz = col2.number_input("Plazo (Meses):", value=48)
            f_v = col2.date_input("Fecha", datetime.now())
            if st.form_submit_button("Registrar"):
                final_c = c_new if c_sel == "+ Añadir nuevo..." else c_sel
                final_v = v_new if v_sel == "+ Añadir nuevo..." else v_sel
                if final_c and final_v:
                    id_c, id_v = get_or_create_id('clientes', 'nombre', final_c), get_or_create_id('vendedores', 'nombre', final_v)
                    id_l = int(lt[lt['manzana'] + "-" + lt['lote'] == l_sel]['id'].values[0])
                    m = (costo - eng) / plz
                    c.execute("INSERT INTO ventas (id_terreno, id_cliente, id_vendedor, enganche, meses, mensualidad, fecha, comision_total) VALUES (?,?,?,?,?,?,?,0)", (id_l, id_c, id_v, eng, plz, m, f_v.strftime('%Y-%m-%d')))
                    c.execute("UPDATE terrenos SET estatus='Vendido', costo=? WHERE id=?", (costo, id_l))
                    conn.commit(); st.rerun()

# --- PÁGINA: COBRANZA ---
elif choice == "Cobranza":
    st.header("💸 Registro de Cobranza")
    df_v = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote || ' - ' || c.nombre as l FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN clientes c ON v.id_cliente = c.id", conn)
    if not df_v.empty:
        with st.form("pago"):
            s = st.selectbox("Contrato:", df_v['l']); m = st.number_input("Monto:", format="%.2f"); f_pago = st.date_input("Fecha", datetime.now())
            if st.form_submit_button("Confirmar Pago"):
                id_v = int(df_v[df_v['l'] == s]['id'].values[0])
                c.execute("INSERT INTO pagos (id_venta, monto, fecha) VALUES (?,?,?)", (id_v, m, f_pago.strftime('%Y-%m-%d')))
                conn.commit(); st.success("Registrado"); st.rerun()

# --- PÁGINA: GESTIÓN DE CONTRATOS ---
elif choice == "Gestión de Contratos":
    st.header("⚙️ Edición de Contratos")
    df_g = pd.read_sql_query('''SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u, c.nombre as cli, vn.nombre as vend, t.costo, v.enganche, v.meses, v.fecha, v.id_terreno FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN vendedores vn ON v.id_vendedor = vn.id JOIN terrenos t ON v.id_terreno = t.id''', conn)
    if not df_g.empty:
        sel = st.selectbox("Contrato:", df_g['u'] + " - " + df_g['cli'])
        datos = df_g[df_g['u'] + " - " + df_g['cli'] == sel].iloc[0]
        with st.form("edit"):
            c1, c2 = st.columns(2)
            nc, nv = c1.text_input("Cliente", value=datos['cli']), c1.text_input("Vendedor", value=datos['vend'])
            nf = c1.date_input("Fecha", value=datetime.strptime(datos['fecha'], '%Y-%m-%d'))
            ncos, neng = c2.number_input("Valor", value=float(datos['costo'])), c2.number_input("Enganche", value=float(datos['enganche']))
            npla = c2.number_input("Plazo", value=int(datos['meses']))
            if st.form_submit_button("Actualizar"):
                id_c, id_v = get_or_create_id('clientes', 'nombre', nc), get_or_create_id('vendedores', 'nombre', nv)
                m = (ncos - neng) / npla
                c.execute("UPDATE ventas SET id_cliente=?, id_vendedor=?, enganche=?, meses=?, mensualidad=?, fecha=? WHERE id=?", (id_c, id_v, neng, npla, m, nf.strftime('%Y-%m-%d'), int(datos['id'])))
                c.execute("UPDATE terrenos SET costo=? WHERE id=?", (ncos, int(datos['id_terreno'])))
                conn.commit(); st.rerun()

# --- PÁGINA: UBICACIONES Y DIRECTORIO ---
elif choice == "Ubicaciones":
    st.header("📍 Ubicaciones")
    with st.form("cat"):
        m, l, p = st.columns(3); ma, lo = m.text_input("Manzana"), l.text_input("Lote"); pr = p.number_input("Precio ($)")
        if st.form_submit_button("Añadir"):
            c.execute("INSERT INTO terrenos (manzana, lote, costo) VALUES (?,?,?)", (ma, lo, pr)); conn.commit(); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT manzana, lote, costo, estatus FROM terrenos", conn), use_container_width=True, hide_index=True)

elif choice == "Directorio":
    st.header("👥 Directorio")
    c1, c2 = st.columns(2)
    c1.subheader("Clientes"); c1.dataframe(pd.read_sql_query("SELECT nombre FROM clientes ORDER BY nombre", conn), hide_index=True, use_container_width=True)
    c2.subheader("Vendedores"); c2.dataframe(pd.read_sql_query("SELECT nombre FROM vendedores ORDER BY nombre", conn), hide_index=True, use_container_width=True)
