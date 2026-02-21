import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

def render_inicio(df_v, df_p, df_cl, fmt_moneda):
    st.title("🏠 Gestión de Cartera")
    st.info("Módulo enfocado en el seguimiento de cobranza.")

    if not df_v.empty:
        monitor = []
        hoy = datetime.now()
        
        for _, v in df_v.iterrows():
            # Filtro de pagos
            pagos_esp = df_p[df_p['ubicacion'] == v['ubicacion']] if not df_p.empty else pd.DataFrame()
            total_pagado = pagos_esp['monto'].sum() if not pagos_esp.empty else 0
            
            # Cálculo de deuda
            f_con = pd.to_datetime(v['fecha'])
            mensualidad = float(v['mensualidad'])
            diff = relativedelta(hoy, f_con)
            m_transcurridos = (diff.years * 12) + diff.months
            deuda_vencida = max(0.0, (m_transcurridos * mensualidad) - total_pagado)
            
            estatus = "🔴 ATRASO" if deuda_vencida > 1.0 else "🟢 AL CORRIENTE"
            
            monitor.append({
                "Ubicación": v['ubicacion'], 
                "Cliente": v['cliente'], 
                "Estatus": estatus, 
                "Deuda Vencida": deuda_vencida
            })
        
        df_mon = pd.DataFrame(monitor)

        # Métricas
        c1, c2 = st.columns(2)
        c1.metric("Clientes en Atraso", len(df_mon[df_mon["Estatus"] == "🔴 ATRASO"]))
        c2.metric("Monto Vencido Total", fmt_moneda(df_mon["Deuda Vencida"].sum()))

        st.subheader("🚩 Monitor de Cobranza")
        st.dataframe(df_mon, use_container_width=True, hide_index=True)
    else:
        st.info("No hay ventas registradas.")
