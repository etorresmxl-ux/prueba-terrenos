import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Inmobiliaria Pro v38", layout="wide")

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

def color_atraso(row):
    dias = row['Días Atraso']
    if dias > 90: return ['background-color: #D35400; color: white'] * len(row)
    elif dias > 30: return ['background-color: #F4D03F; color: black'] * len(row)
    return [''] * len(row)

# --- MENÚ LATERAL ---
with st.sidebar:
    st.title("📂 Menú Principal")
    choice = st.radio(
        "Navegación",
        ["Resumen", "Nueva Venta", "Cobranza", "Gestión de Pagos", "Detalle de Crédito", "Gestión de Contratos", "Comisiones", "Ubicaciones", "Directorio"]
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
        df_f = pd.DataFrame(resultados)
        st.dataframe(df_f.style.apply(color_atraso, axis=1).format({"Valor": f_money, "Enganche": f_money, "Total Pagado": f_money, "Para Corriente": f_money}), use_container_width=True, hide_index=True)

elif choice == "Nueva Venta":
    st.header("📝 Registro de Nueva Venta")
    
    # Obtener datos existentes para los selectores
    lt = pd.read_sql_query("SELECT * FROM terrenos WHERE estatus='Disponible'", conn)
    clientes_existentes = ["+ Añadir nuevo cliente..."] + sorted(pd.read_sql_query("SELECT nombre FROM clientes", conn)['nombre'].tolist())
    vendedores_existentes = ["+ Añadir nuevo vendedor..."] + sorted(pd.read_sql_query("SELECT nombre FROM vendedores", conn)['nombre'].tolist())
    
    if not lt.empty:
        with st.form("nv"):
            col_a, col_b = st.columns(2)
            
            # --- SECCIÓN CLIENTE ---
            lote_sel = col_a.selectbox("Seleccione Lote disponible:", lt['manzana'] + "-" + lt['lote'])
            cliente_sel = col_a.selectbox("Cliente:", clientes_existentes)
            # Campo extra si es nuevo
            cliente_input = ""
            if cliente_sel == "+ Añadir nuevo cliente...":
                cliente_input = col_a.text_input("Escriba el nombre del nuevo Cliente:")
            
            # --- SECCIÓN VENDEDOR ---
            vendedor_sel = col_a.selectbox("Vendedor:", vendedores_existentes)
            vendedor_input = ""
            if vendedor_sel == "+ Añadir nuevo vendedor...":
                vendedor_input = col_a.text_input("Escriba el nombre del nuevo Vendedor:")
            
            # --- DATOS FINANCIEROS ---
            p_cat = float(lt[lt['manzana'] + "-" + lt['lote'] == lote_sel]['costo'].values[0])
            costo = col_b.number_input("Precio Final de Venta ($):", value=p_cat)
            enganche = col_b.number_input("Monto de Enganche ($):")
            plazo = col_b.number_input("Plazo en Meses:", value=48, step=1)
            fecha_v = col_b.date_input("Fecha de Firma", datetime.now())
            comision = col_b.number_input("Comisión pactada ($):", value=0.0)
            
            if st.form_submit_button("🚀 Registrar Contrato"):
                # Determinar nombres finales
                nombre_c = cliente_input if cliente_sel == "+ Añadir nuevo cliente..." else cliente_sel
                nombre_v = vendedor_input if vendedor_sel == "+ Añadir nuevo vendedor..." else vendedor_sel
                
                if nombre_c and nombre_v:
                    id_c = get_or_create_id('clientes', 'nombre', nombre_c)
                    id_v = get_or_create_id('vendedores', 'nombre', nombre_v)
                    id_l = int(lt[lt['manzana'] + "-" + lt['lote'] == lote_sel]['id'].values[0])
                    mensualidad = (costo - enganche) / plazo
                    
                    c.execute('''INSERT INTO ventas (id_terreno, id_cliente, id_vendedor, enganche, meses, mensualidad, fecha, comision_total) 
                                 VALUES (?,?,?,?,?,?,?,?)''', (id_l, id_c, id_v, enganche, plazo, mensualidad, fecha_v.strftime('%Y-%m-%d'), comision))
                    c.execute("UPDATE terrenos SET estatus='Vendido', costo=? WHERE id=?", (costo, id_l))
                    conn.commit()
                    st.success(f"¡Venta de Lote {lote_sel} registrada a nombre de {nombre_c}!")
                    st.rerun()
                else:
                    st.error("Por favor, asegúrese de asignar un Cliente y un Vendedor.")
    else:
        st.warning("No hay terrenos disponibles en el catálogo.")

elif choice == "Gestión de Pagos":
    st.header("⚙️ Gestión y Corrección de Pagos")
    tab1, tab2 = st.tabs(["📝 Editar/Eliminar Pagos", "📜 Historial Completo"])
    
    with tab1:
        st.subheader("Corregir un registro")
        query_pagos = '''
            SELECT p.id, p.fecha, p.monto, c.nombre as Cliente, 'M'||t.manzana||'-L'||t.lote as Lote
            FROM pagos p JOIN ventas v ON p.id_venta = v.id JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id
            ORDER BY p.fecha DESC
        '''
        df_pagos_edit = pd.read_sql_query(query_pagos, conn)
        if not df_pagos_edit.empty:
            df_pagos_edit['label'] = df_pagos_edit['fecha'] + " | " + df_pagos_edit['Cliente'] + " (" + df_pagos_edit['Lote'] + ") - $" + df_pagos_edit['monto'].astype(str)
            pago_sel = st.selectbox("Seleccione el pago a modificar:", df_pagos_edit['label'])
            pago_data = df_pagos_edit[df_pagos_edit['label'] == pago_sel].iloc[0]
            with st.form("form_edit_pago"):
                col1, col2 = st.columns(2)
                nuevo_monto = col1.number_input("Monto Correcto ($)", value=float(pago_data['monto']))
                nueva_fecha = col2.date_input("Fecha Correcta", value=datetime.strptime(pago_data['fecha'], '%Y-%m-%d'))
                c1, c2 = st.columns(2)
                if c1.form_submit_button("💾 Guardar"):
                    c.execute("UPDATE pagos SET monto=?, fecha=? WHERE id=?", (nuevo_monto, nueva_fecha.strftime('%Y-%m-%d'), int(pago_data['id'])))
                    conn.commit(); st.rerun()
                if c2.form_submit_button("🗑️ Eliminar"):
                    c.execute("DELETE FROM pagos WHERE id=?", (int(pago_data['id']),)); conn.commit(); st.rerun()

    with tab2:
        st.subheader("Búsqueda de Movimientos")
        f_col1, f_col2 = st.columns(2)
        filtro_cliente = f_col1.text_input("Filtrar por Cliente:")
        filtro_lote = f_col2.text_input("Filtrar por Ubicación:")
        h_eng = pd.read_sql_query("SELECT v.fecha, c.nombre as Cliente, 'M'||t.manzana||'-L'||t.lote as Ubicación, v.enganche as Monto, 'ENGANCHE' as Tipo FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id", conn)
        h_abo = pd.read_sql_query("SELECT p.fecha, c.nombre as Cliente, 'M'||t.manzana||'-L'||t.lote as Ubicación, p.monto as Monto, 'ABONO' as Tipo FROM pagos p JOIN ventas v ON p.id_venta = v.id JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id", conn)
        hist_total = pd.concat([h_eng, h_abo]).sort_values(by='fecha', ascending=False)
        if filtro_cliente: hist_total = hist_total[hist_total['Cliente'].str.contains(filtro_cliente, case=False, na=False)]
        if filtro_lote: hist_total = hist_total[hist_total['Ubicación'].str.contains(filtro_lote, case=False, na=False)]
        if not hist_total.empty:
            display_df = hist_total.copy()
            display_df['Monto'] = display_df['Monto'].apply(f_money)
            display_df['fecha'] = display_df['fecha'].apply(f_date_show)
            st.dataframe(display_df, use_container_width=True, hide_index=True)

elif choice == "Cobranza":
    st.header("💸 Registro de Cobranza")
    df_v = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote || ' - ' || c.nombre as l FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN clientes c ON v.id_cliente = c.id", conn)
    if not df_v.empty:
        with st.form("pago"):
            s = st.selectbox("Contrato:", df_v['l']); m = st.number_input("Monto:", format="%.2f"); f_pago = st.date_input("Fecha", datetime.now())
            if st.form_submit_button("Confirmar Pago"):
                id_v = int(df_v[df_v['l'] == s]['id'].values[0])
                c.execute("INSERT INTO pagos (id_venta, monto, fecha) VALUES (?,?,?)", (id_v, m, f_pago.strftime('%Y-%m-%d')))
                conn.commit(); st.rerun()

elif choice == "Detalle de Crédito":
    st.header("🔍 Estado de Cuenta")
    df_u = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote || ' - ' || c.nombre as info FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN clientes c ON v.id_cliente = c.id", conn)
    if not df_u.empty:
        sel_u = st.selectbox("Contrato:", df_u['info'])
        vid = int(df_u[df_u['info'] == sel_u]['id'].values[0])
        res = pd.read_sql_query(f"SELECT v.*, c.nombre, 'M'||t.manzana||'-L'||t.lote as u, t.costo, IFNULL((SELECT SUM(monto) FROM pagos WHERE id_venta = v.id), 0) as total_abonos FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN terrenos t ON v.id_terreno = t.id WHERE v.id = {vid}", conn).iloc[0]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Ubicación", res['u']); col1.metric("Valor", f_money(res['costo']))
        col2.metric("Cliente", res['nombre']); col2.metric("Enganche", f_money(res['enganche']))
        col3.metric("Fecha", f_date_show(res['fecha'])); col3.metric("Pagado", f_money(res['enganche'] + res['total_abonos']))
        col4.metric("Saldo", f_money(res['costo'] - (res['enganche'] + res['total_abonos'])))
        st.markdown("---")
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

elif choice == "Gestión de Contratos":
    st.header("⚙️ Edición de Contratos")
    df_g = pd.read_sql_query('''SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u, c.nombre as cli, vn.nombre as vend, t.costo, v.enganche, v.meses, v.fecha, v.comision_total, v.id_terreno FROM ventas v JOIN clientes c ON v.id_cliente = c.id JOIN vendedores vn ON v.id_vendedor = vn.id JOIN terrenos t ON v.id_terreno = t.id''', conn)
    if not df_g.empty:
        sel = st.selectbox("Contrato:", df_g['u'] + " - " + df_g['cli'])
        datos = df_g[df_g['u'] + " - " + df_g['cli'] == sel].iloc[0]
        with st.form("edit"):
            c1, c2 = st.columns(2)
            nc, nv = c1.text_input("Cliente", value=datos['cli']), c1.text_input("Vendedor", value=datos['vend'])
            nf = c1.date_input("Fecha", value=datetime.strptime(datos['fecha'], '%Y-%m-%d'))
            ncos, neng = c2.number_input("Valor", value=float(datos['costo'])), c2.number_input("Enganche", value=float(datos['enganche']))
            npla, ncom = c2.number_input("Plazo", value=int(datos['meses'])), c2.number_input("Comisión", value=float(datos['comision_total']))
            if st.form_submit_button("Actualizar"):
                id_c, id_v = get_or_create_id('clientes', 'nombre', nc), get_or_create_id('vendedores', 'nombre', nv)
                m = (ncos - neng) / npla
                c.execute("UPDATE ventas SET id_cliente=?, id_vendedor=?, enganche=?, meses=?, mensualidad=?, fecha=?, comision_total=? WHERE id=?", (id_c, id_v, neng, npla, m, nf.strftime('%Y-%m-%d'), ncom, int(datos['id'])))
                c.execute("UPDATE terrenos SET costo=? WHERE id=?", (ncos, int(datos['id_terreno'])))
                conn.commit(); st.rerun()

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
