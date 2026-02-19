import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

def render_detalle_credito(df_v, df_p, fmt_moneda):
    st.title("📊 Detalle de Crédito y Estado de Cuenta")
    
    if df_v.empty:
        st.warning("No hay ventas registradas.")
        return

    # 1. SELECTOR DE CONTRATO
    opciones_vta = (df_v["ubicacion"] + " | " + df_v["cliente"]).tolist()
    seleccion = st.selectbox("🔍 Seleccione un Contrato:", opciones_vta)
    
    ubi_sel = seleccion.split(" | ")[0]
    v = df_v[df_v["ubicacion"] == ubi_sel].iloc[0]
    
    # --- CÁLCULOS FINANCIEROS ---
    precio_total_vta = float(v['precio_total'])
    enganche_vta = float(v['enganche'])
    monto_a_financiar = precio_total_vta - enganche_vta
    
    # Suma de abonos registrados en la tabla de pagos
    abonos_mensuales = df_p[df_p["ubicacion"] == ubi_sel]["monto"].sum() if not df_p.empty else 0
    
    # TOTAL PAGADO (Enganche + Abonos)
    total_pagado_acumulado = enganche_vta + abonos_mensuales
    
    # Cálculo de avance (Sobre el costo total)
    porcentaje_total = (total_pagado_acumulado / precio_total_vta) if precio_total_vta > 0 else 0
    porcentaje_total = min(1.0, porcentaje_total)

    # Lógica de morosidad
    mensualidad_pactada = float(v['mensualidad'])
    fecha_contrato = pd.to_datetime(v['fecha'])
    hoy = datetime.now()
    
    meses_transcurridos = (hoy.year - fecha_contrato.year) * 12 + (hoy.month - fecha_contrato.month)
    meses_a_deber = max(0, min(meses_transcurridos, int(v['plazo_meses'])))
    deuda_esperada_a_hoy = meses_a_deber * mensualidad_pactada
    
    saldo_vencido = max(0, deuda_esperada_a_hoy - abonos_mensuales)
    num_atrasos = saldo_vencido / mensualidad_pactada if mensualidad_pactada > 0 else 0

    # --- SECCIÓN: INFORMACIÓN GENERAL Y BARRA ---
    st.markdown("### 📋 Resumen del Crédito")
    
    st.write(f"**Avance Total de Pago: {int(porcentaje_total * 100)}%**")
    st.progress(porcentaje_total)
    st.write("") 

    c1, c2, c3 = st.columns(3)
    with c1:
        st.write(f"**📍 Ubicación:** {v['ubicacion']}")
        st.write(f"**👤 Cliente:** {v['cliente']}")
        st.write(f"**📅 Contrato:** {v['fecha']}")
    with c2:
        st.metric("Total Pagado", fmt_moneda(total_pagado_acumulado))
        st.write(f"**💰 Costo Total:** {fmt_moneda(precio_total_vta)}")
        st.write(f"**📥 Enganche:** {fmt_moneda(enganche_vta)}")
    with c3:
        st.metric("Saldo Vencido", fmt_moneda(saldo_vencido), 
                  delta=f"{int(num_atrasos)} meses" if num_atrasos >= 1 else "Al día", 
                  delta_color="inverse")
        st.write(f"**📉 Restante:** {fmt_moneda(max(0, precio_total_vta - total_pagado_acumulado))}")

    st.divider()

    # --- TABLA DE AMORTIZACIÓN CON DISEÑO PROFESIONAL ---
        st.subheader("📅 Cronograma de Pagos")

        # 1. Renombrar columnas para que se vean bien (Nombre Propio)
        # Ajusta los nombres de la izquierda según cómo se llamen originalmente en tu código
        nuevos_nombres_amort = {
            "n_cuota": "No. Cuota",
            "fecha_pago": "Fecha de Pago",
            "monto_cuota": "Monto de Cuota",
            "estado": "Estatus",
            "saldo_pendiente": "Saldo Restante"
        }

        # Aplicamos el filtro de columnas y el renombrado
        df_visual = df_amort.rename(columns=nuevos_nombres_amort)

        # 2. Asegurar que la fecha sea datetime para el formato
        if "Fecha de Pago" in df_visual.columns:
            df_visual["Fecha de Pago"] = pd.to_datetime(df_visual["Fecha de Pago"])

        # 3. Aplicar Estilos y Formatos
        df_amort_estilizado = df_visual.style.format({
            "Fecha de Pago": lambda t: t.strftime('%d-%b-%Y'),
            "Monto de Cuota": "$ {:,.2f}",
            "Saldo Restante": "$ {:,.2f}"
        }).set_table_styles([
            # Centrar encabezados y darles un toque visual
            {'selector': 'th', 'props': [('text-align', 'center'), ('background-color', '#f0f2f6'), ('color', '#1f1f1f')]},
            # Opcional: Centrar el contenido de las celdas
            {'selector': 'td', 'props': [('text-align', 'center')]}
        ])

        # 4. Renderizar
        st.dataframe(
            df_amort_estilizado,
            use_container_width=True,
            hide_index=True
        )
