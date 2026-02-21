import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

def render_reportes(df_v, df_p, df_g, fmt_moneda):
    st.title("📈 Análisis Financiero Maestro")
    
    if df_v.empty or df_p.empty or df_g.empty:
        st.warning("Se requieren datos de Ventas, Pagos y Gastos para generar este análisis.")
        return

    # --- CÁLCULOS BASE ---
    ingresos_pagos = df_p["monto"].sum()
    ingresos_enganches = df_v["enganche"].sum()
    ingresos_totales = ingresos_pagos + ingresos_enganches
    
    egresos_totales = df_g["monto"].sum()
    utilidad_neta = ingresos_totales - egresos_totales
    margen_utilidad = (utilidad_neta / ingresos_totales * 100) if ingresos_totales > 0 else 0

    # --- FILA 1: KPIs MAESTROS ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ingresos Acumulados", fmt_moneda(ingresos_totales))
    c2.metric("Egresos Acumulados", fmt_moneda(egresos_totales), delta=f"-{fmt_moneda(egresos_totales)}", delta_color="inverse")
    c3.metric("Utilidad Operativa", fmt_moneda(utilidad_neta))
    c4.metric("Margen de Utilidad", f"{margen_utilidad:.1f}%")

    st.divider()

    # --- FILA 2: GRÁFICAS DE FLUJO ---
    col_izq, col_der = st.columns(2)

    with col_izq:
        st.subheader("💰 Flujo de Caja (Ingresos vs Gastos)")
        datos_flujo = pd.DataFrame({
            "Categoría": ["Ingresos", "Egresos"],
            "Monto": [ingresos_totales, egresos_totales],
            "Color": ["#2ECC71", "#E74C3C"]
        })
        fig_flujo = px.bar(datos_flujo, x="Categoría", y="Monto", color="Categoría",
                          color_discrete_map={"Ingresos": "#2ECC71", "Egresos": "#E74C3C"},
                          text_auto='.2s')
        st.plotly_chart(fig_flujo, use_container_width=True)

    with col_der:
        st.subheader("📂 Distribución de Gastos")
        if "categoria" in df_g.columns:
            fig_gastos = px.pie(df_g, values="monto", names="categoria", hole=0.4,
                               color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_gastos, use_container_width=True)
        else:
            st.info("Agrega una columna 'categoria' en Gastos para ver este análisis.")

    st.divider()

    # --- FILA 3: SALUD DEL PROYECTO (CAPITAL EN CALLE) ---
    st.subheader("🏛️ Valor de la Cartera (Capital en Calle)")
    
    valor_total_proyecto = df_v["precio_total"].sum()
    capital_recuperado = ingresos_totales
    capital_pendiente = valor_total_proyecto - capital_recuperado
    
    c_a, c_b = st.columns([1, 2])
    
    with c_a:
        st.write("### Resumen")
        st.write(f"**Valor Total Vendido:** {fmt_moneda(valor_total_proyecto)}")
        st.write(f"**Total Cobrado:** {fmt_moneda(capital_recuperado)}")
        st.write(f"**Por Cobrar:** {fmt_moneda(capital_pendiente)}")
        
        progreso = (capital_recuperado / valor_total_proyecto) if valor_total_proyecto > 0 else 0
        st.progress(progreso, text=f"Progreso de Liquidación: {progreso*100:.1f}%")

    with c_b:
        # Gráfico de dona para ver la liquidación total
        df_cartera = pd.DataFrame({
            "Estatus": ["Cobrado", "Pendiente"],
            "Monto": [capital_recuperado, capital_pendiente]
        })
        fig_cartera = px.pie(df_cartera, values="Monto", names="Estatus", 
                            color_discrete_sequence=["#3498DB", "#ECF0F1"])
        st.plotly_chart(fig_cartera, use_container_width=True)

    # --- FILA 4: PROYECCIÓN MENSUAL ---
    st.subheader("📅 Proyección de Ingresos Mensuales")
    mensualidad_proyectada = df_v["mensualidad"].sum()
    st.info(f"Si todos los clientes pagaran puntualmente, tu ingreso mensual esperado es de: **{fmt_moneda(mensualidad_proyectada)}**")
