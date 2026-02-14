import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# 1. Configuración
st.set_page_config(page_title="Inmobiliaria", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
URL_SHEET = "https://docs.google.com/spreadsheets/d/1d_G8VafPZp5jj3c1Io9kN3mG31GE70kK2Q2blxWzCCs/edit#gid=0"

# --- MENÚ ---
st.sidebar.title("Navegación")
menu = st.sidebar.radio(
    "Seleccione una sección:",
    ["🏠 Inicio", "📝 Ventas", "📊 Detalle de Crédito", "💰 Cobranza", "📅 Historial de Pagos", "📑 Catálogo", "📇 Directorio"]
)

# --- FUNCIONES ---
def cargar_datos(pestana):
    try: return conn.read(spreadsheet=URL_SHEET, worksheet=pestana)
    except: return pd.DataFrame()

st.title(f"Inmobiliaria - {menu}")

# --- MÓDULO: VENTAS (Se mantiene igual que el anterior) ---
if menu == "📝 Ventas":
    st.info("Aquí registras los nuevos contratos (usa el código anterior).")

# --- MÓDULO: DETALLE DE CRÉDITO (NUEVO) ---
elif menu == "📊 Detalle de Crédito":
    st.subheader("Consulta de Estado de Cuenta")
    
    df_ventas = cargar_datos("ventas")
    df_pagos = cargar_datos("pagos") # Asumiendo que aquí registrarás los abonos reales

    if df_ventas.empty:
        st.warning("No hay ventas registradas para consultar créditos.")
    else:
        # 1. Selector de Contrato
        opciones_contratos = df_ventas['ubicacion'].tolist()
        v_sel = st.selectbox("Seleccione la Ubicación/Contrato", options=opciones_contratos)
        
        # 2. Extraer datos generales
        datos = df_ventas[df_ventas['ubicacion'] == v_sel].iloc[0]
        
        # Cálculos de pagos realizados (simulado hasta tener módulo Cobranza)
        pagos_realizados = 0.0
        if not df_pagos.empty and 'ubicacion' in df_pagos.columns:
            pagos_realizados = df_pagos[df_pagos['ubicacion'] == v_sel]['monto'].sum()

        # --- DISEÑO DE DATOS GENERALES ---
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.write(f"**Ubicación:** {datos['ubicacion']}")
            st.write(f"**Cliente:** {datos['cliente']}")
        with c2:
            st.write(f"**Fecha Contrato:** {datos['fecha']}")
            st.write(f"**Enganche:** ${datos['enganche']:,.2f}")
        with c3:
            st.write(f"**Plazo:** {datos['plazo_meses']} meses")
            st.write(f"**Mensualidad:** ${datos['mensualidad']:,.2f}")
        with c4:
            saldo_restante = datos['precio_total'] - datos['enganche'] - pagos_realizados
            st.metric("Saldo Restante", f"${saldo_restante:,.2f}")
            st.metric("Total Pagado", f"${pagos_realizados:,.2f}")

        st.divider()
        st.subheader("Tabla de Proyección de Pagos (Amortización)")

        # 3. GENERAR TABLA GENÉRICA
        proyeccion = []
        fecha_inicial = datetime.strptime(str(datos['fecha']), '%Y-%m-%d')
        saldo_gradual = datos['precio_total'] - datos['enganche']
        
        for i in range(1, int(datos['plazo_meses']) + 1):
            fecha_pago = fecha_inicial + relativedelta(months=i)
            saldo_gradual -= datos['mensualidad']
            
            proyeccion.append({
                "Mes": i,
                "Fecha Programada": fecha_pago.strftime('%d/%m/%Y'),
                "Cuota": datos['mensualidad'],
                "Saldo tras Pago": max(saldo_gradual, 0),
                "Estatus": "Pendiente" # Esto se cruzará con Cobranza después
            })
        
        df_tabla = pd.DataFrame(proyeccion)
        
        st.dataframe(
            df_tabla, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Cuota": st.column_config.NumberColumn(format="$%,.2f"),
                "Saldo tras Pago": st.column_config.NumberColumn(format="$%,.2f")
            }
        )

# --- MANTENER OTROS MÓDULOS ---
elif menu == "📑 Catálogo":
    st.dataframe(cargar_datos("ubicaciones"), use_container_width=True, hide_index=True)

elif menu == "📇 Directorio":
    t1, t2 = st.tabs(["Clientes", "Vendedores"])
    with t1: st.dataframe(cargar_datos("clientes"), use_container_width=True)
    with t2: st.dataframe(cargar_datos("vendedores"), use_container_width=True)
