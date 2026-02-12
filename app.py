import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Inmobiliaria Pro v32", layout="wide")

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
        SELECT 
            v.id, 
            'M'||t.manzana||'-L'||t.lote as Ubicación, 
            c.nombre as Cliente, 
            t.costo as Valor, 
            v.enganche as Enganche, 
            v.fecha as [Fecha de Contrato],
            v.mensualidad,
            v.meses,
            IFNULL((SELECT SUM(monto) FROM pagos WHERE id_venta = v.id), 0) as PagosExtra,
            (SELECT MAX(fecha) FROM pagos WHERE id_venta = v.id) as [Fecha Ultimo Pago]
        FROM ventas v 
        JOIN clientes c ON v.id_cliente = c.id 
        JOIN terrenos t ON v.id_terreno = t.id
    '''
    df = pd.read_sql_query(query, conn)
    
    if not df.empty:
        resultados = []
        hoy = datetime.now()

        for index, row in df.iterrows():
            f_contrato = datetime.strptime(row['Fecha de Contrato'], '%Y-%m-%d')
            total_pagado = row['Enganche'] + row['PagosExtra']
            
            # Calcular meses que deberían haber transcurrido
            diff = relativedelta(hoy, f_contrato)
            meses_transcurridos = diff.years * 12 + diff.months
            meses_a_deber = min(meses_transcurridos, int(row['meses']))
            
            monto_obligatorio = meses_a_deber * row['mensualidad']
            monto_abonado = row['PagosExtra']
            
            diferencia = monto_obligatorio - monto_abonado
            pago_corriente = max(0, diferencia)
            
            # Cálculo de Días de Atraso
            dias_atraso = 0
            if diferencia > 1.0:  # Si debe más de 1 peso (margen decimal)
                # Calculamos cuántos meses de abono cubren los pagos actuales
                meses_cubiertos = monto_abonado // row['mensualidad']
                # La fecha en la que debió pagar el siguiente mes
                fecha_vencimiento_pendiente = f_contrato + relativedelta(months=int(meses_cubiertos) + 1)
                if hoy > fecha_vencimiento_pendiente:
                    dias_atraso = (hoy - fecha_vencimiento_pendiente).days

            estatus = "Al Corriente" if diferencia <= 1.0 else "Atrasado"

            resultados.append({
                "Ubicación": row['Ubicación'],
                "Cliente": row['Cliente'],
                "Valor": f_money(row['Valor']),
                "Enganche": f_money(row['Enganche']),
                "Contrato": f_date_show(row['Fecha de Contrato']),
                "Total Pagado": f_money(total_pagado),
                "Último Pago": f_date_show(row['Fecha Ultimo Pago']) if row['Fecha Ultimo Pago'] else "N/A",
                "Estatus": estatus,
                "Días Atraso": dias_atraso,
                "Para Corriente": f_money(pago_corriente)
            })
        
        # Mostrar tabla con formato
        res_df = pd.DataFrame(resultados)
        st.dataframe(res_df, use_container_width=True, hide_index=True)
    else:
        st.info("No hay registros de ventas.")

elif choice == "Nueva Venta":
    st.header("📝 Registro de Nueva Venta")
    lt = pd.read_sql_query("SELECT * FROM terrenos WHERE estatus='Disponible'", conn)
    if lt.empty:
        st.warning("No hay lotes disponibles.")
    else:
        with st.form("nv"):
            col1, col2 = st.columns(2)
            l_sel = col1.selectbox("Seleccione Lote:", lt['manzana'] + "-" + lt['lote'])
            c_nom = col1.text_input("Nombre del Cliente:")
            v_nom = col1.text_input("Nombre del Vendedor:")
            p_cat = float(lt[lt['manzana'] + "-" + lt['lote'] == l_sel]['costo'].values[0])
            costo = col2.number_input("Precio Final ($):", value=p_cat)
            eng = col2.number_input("Enganche ($):")
            plz = col2.number_input("Plazo (Meses):", value=48)
            f_cont = col2.date_input("Fecha de Contrato", datetime.now())
            if st.form_submit_button("Registrar Venta"):
                if c_nom and v_nom:
                    id_c = get_or_create_id('clientes', 'nombre', c_nom)
                    id_v = get_or_create_id('vendedores', 'nombre', v_nom)
                    id_l = int(lt[lt['manzana'] + "-" + lt['lote'] == l_sel]['id'].values[0])
                    mensu = (costo - eng) / plz
                    c.execute('''INSERT INTO ventas (id_terreno, id_cliente, id_vendedor, enganche, meses, mensualidad, fecha, comision_total) 
                                 VALUES (?,?,?,?,?,?,?,0)''', (id_l, id_c, id_v, eng, plz, mensu, f_cont.strftime('%Y-%m-%d')))
                    c.execute("UPDATE terrenos SET estatus='Vendido', costo=? WHERE id=?", (costo, id_l))
                    conn.commit(); st.success("Venta Exitosa"); st.rerun()

elif choice == "Cobranza":
    st.header("💸 Registro de Cobranza")
    df_v = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote || ' - ' || c.nombre as l FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN clientes c ON v.id_cliente = c.id", conn)
    if not df_v.empty:
        with st.form("pago"):
            s = st.selectbox("Contrato:", df_v['l'])
            m = st.number_input("Monto del Abono ($):", format="%.2f")
            f_pago = st.date_input("Fecha de Pago", datetime.now())
            if st.form_submit_button("Confirmar Pago"):
                id_v = int(df_v[df_v['l'] == s]['id'].values[0])
                c.execute("INSERT INTO pagos (id_venta, monto, fecha) VALUES (?,?,?)", (id_v, m, f_pago.strftime('%Y-%m-%d')))
                conn.commit(); st.success("Pago registrado"); st.rerun()

elif choice == "Detalle de Crédito":
    st.header("🔍 Detalle Amortización")
    df_u = pd.read_sql_query("SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u FROM ventas v JOIN terrenos t ON v.id_terreno = t.id", conn)
    if not df_u.empty:
        sel_u = st.selectbox("Lote:", df_u['u'])
        vid = int(df_u[df_u['u'] == sel_u]['id'].values[0])
        res = pd.read_sql_query(f"SELECT * FROM ventas v JOIN clientes c ON v.id_cliente=c.id JOIN terrenos t ON v.id_terreno=t.id WHERE v.id={vid}", conn).iloc[0]
        st.write(f"**Cliente:** {res['nombre']} | **Plan:** {int(res['meses'])} meses de {f_money(res['mensualidad'])}")
        tabla = []; saldo = res['costo'] - res['enganche']
        for i in range(1, int(res['meses']) + 1):
            saldo -= res['mensualidad']
            tabla.append({"Mes": i, "Pago Sugerido": f_money(res['mensualidad']), "Saldo Proyectado": f_money(max(0, saldo))})
        st.table(tabla[:24])

elif choice == "Gestión de Contratos":
    st.header("⚙️ Gestión de Contratos")
    df_g = pd.read_sql_query('''
        SELECT v.id, 'M'||t.manzana||'-L'||t.lote as u, c.nombre as cli, vn.nombre as vend, 
        t.costo, v.enganche, v.meses, v.fecha, v.id_terreno 
        FROM ventas v JOIN clientes c ON v.id_cliente = c.id 
        JOIN vendedores vn ON v.id_vendedor = vn.id JOIN terrenos t ON v.id_terreno = t.id
    ''', conn)
    if not df_g.empty:
        sel = st.selectbox("Contrato:", df_g['u'] + " - " + df_g['cli'])
        datos = df_g[df_g['u'] + " - " + df_g['cli'] == sel].iloc[0]
        with st.form("edicion"):
            c1, c2 = st.columns(2)
            nc = c1.text_input("Cliente", value=datos['cli'])
            nv = c1.text_input("Vendedor", value=datos['vend'])
            nf = c1.date_input("Fecha", value=datetime.strptime(datos['fecha'], '%Y-%m-%d'))
            ncos = c2.number_input("Valor", value=float(datos['costo']))
            neng = c2.number_input("Enganche", value=float(datos['enganche']))
            npla = c2.number_input("Plazo", value=int(datos['meses']))
            if st.form_submit_button("Actualizar Contrato"):
                id_c = get_or_create_id('clientes', 'nombre', nc)
                id_v = get_or_create_id('vendedores', 'nombre', nv)
                n_men = (ncos - neng) / npla
                c.execute("UPDATE ventas SET id_cliente=?, id_vendedor=?, enganche=?, meses=?, mensualidad=?, fecha=? WHERE id=?", 
                          (id_c, id_v, neng, npla, n_men, nf.strftime('%Y-%m-%d'), int(datos['id'])))
                c.execute("UPDATE terrenos SET costo=? WHERE id=?", (ncos, int(datos['id_terreno'])))
                conn.commit(); st.success("Cambios guardados"); st.rerun()
        if st.button("Eliminar Contrato"):
            c.execute("DELETE FROM ventas WHERE id=?", (int(datos['id']),)); c.execute("UPDATE terrenos SET estatus='Disponible' WHERE id=?", (int(datos['id_terreno']),))
            conn.commit(); st.rerun()

elif choice == "Ubicaciones":
    st.header("📍 Catálogo de Ubicaciones")
    with st.form("cat"):
        m, l, p = st.columns(3)
        ma = m.text_input("Manzana"); lo = l.text_input("Lote"); pr = p.number_input("Precio ($)")
        if st.form_submit_button("Añadir"):
            c.execute("INSERT INTO terrenos (manzana, lote, costo) VALUES (?,?,?)", (ma, lo, pr)); conn.commit(); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT manzana, lote, costo, estatus FROM terrenos", conn), use_container_width=True)

elif choice == "Directorio":
    st.header("👥 Directorio")
    c1, c2 = st.columns(2)
    c1.subheader("Clientes"); c1.dataframe(pd.read_sql_query("SELECT nombre FROM clientes ORDER BY nombre", conn), hide_index=True)
    c2.subheader("Vendedores"); c2.dataframe(pd.read_sql_query("SELECT nombre FROM vendedores ORDER BY nombre", conn), hide_index=True)

elif choice == "Comisiones":
    st.header("🤝 Comisiones")
    st.dataframe(pd.read_sql_query("SELECT vn.nombre as Vendedor, 'M'||t.manzana||'-L'||t.lote as Lote, v.comision_total as Total FROM ventas v JOIN terrenos t ON v.id_terreno = t.id JOIN vendedores vn ON v.id_vendedor = vn.id", conn), use_container_width=True)

elif choice == "Gráficos":
    st.header("📈 Desempeño")
    df_g = pd.read_sql_query("SELECT vn.nombre as Vendedor, SUM(t.costo) as Total FROM ventas v JOIN vendedores vn ON v.id_vendedor = vn.id JOIN terrenos t ON v.id_terreno = t.id GROUP BY vn.nombre", conn)
    if not df_g.empty: st.bar_chart(data=df_g, x="Vendedor", y="Total")
