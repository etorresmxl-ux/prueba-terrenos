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

    # --- SECCIÓN: TABLA DE AMORTIZACIÓN ---
    st.subheader("📅 Plan de Pagos Mensuales")
    
    amortizacion = []
    bolsa_pagos = abonos_mensuales

    for i in range(1, int(v['plazo_meses']) + 1):
        fecha_vencimiento = fecha_contrato + relativedelta(months=i)
        pago_realizado = 0.0
        
        if bolsa_pagos >= mensualidad_pactada:
            pago_realizado = mensualidad_pactada
            bolsa_pagos -= mensualidad_pactada
            estatus = "🟢 PAGADO"
        elif bolsa_pagos > 0:
            pago_realizado = bolsa_pagos
            bolsa_pagos = 0
            estatus = "🟡 PAGO PARCIAL"
        else:
            pago_realizado = 0.0
            if fecha_vencimiento.date() <= hoy.date():
                estatus = "🔴 VENCIDO"
            else:
                estatus = "PENDIENTE"
        
        amortizacion.append({
            "Mes": i,
            "Vencimiento": fecha_vencimiento.strftime('%d/%m/%Y'),
            "Importe": mensualidad_pactada,
            "Pagado": pago_realizado,
            "Estatus": estatus
        })

    df_tab = pd.DataFrame(amortizacion)
    st.dataframe(df_tab, use_container_width=True, hide_index=True)
