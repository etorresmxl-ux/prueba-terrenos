import streamlit as st
import pandas as pd

def render_reportes(df_v, df_p, df_g, fmt_moneda):
    st.title("📈 Resumen Financiero")
    
    if df_v.empty or df_p.empty or df_g.empty:
        st.warning("Faltan datos para generar el reporte completo.")
        return

    # Cálculos Simples
    ingresos = df_p["monto"].sum() + df_v["enganche"].sum()
    egresos = df_g["monto"].sum()
    utilidad = ingresos - egresos

    # KPIs Maestros con diseño nativo
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Ingresos", fmt_moneda(ingresos))
    c2.metric("Total Gastos", fmt_moneda(egresos), delta=f"-{fmt_moneda(egresos)}", delta_color="inverse")
    c3.metric("Utilidad Neta", fmt_moneda(utilidad))

    st.divider()

    # Gráfica Nativa (No requiere Plotly)
    st.subheader("📊 Comparativo Ingresos vs Gastos")
    data_grafica = pd.DataFrame({
        "Concepto": ["Ingresos", "Gastos"],
        "Monto": [ingresos, egresos]
    }).set_index("Concepto")
    
    st.bar_chart(data_grafica)

    # Tabla de resumen de gastos
    st.subheader("💸 Detalle de Gastos por Categoría")
    if "categoria" in df_g.columns:
        resumen_g = df_g.groupby("categoria")["monto"].sum().reset_index()
        resumen_g.columns = ["Categoría", "Total"]
        st.table(resumen_g.style.format({"Total": "$ {:,.2f}"}))
