import streamlit as st
import pandas as pd

def render_reportes(df_v, df_p, df_g, fmt_moneda):
    st.title("📈 Dashboard de Resultados")

    # --- MÉTRICAS PRINCIPALES ---
    total_ventas_valor = df_v["precio_total"].sum() if not df_v.empty else 0
    total_ingresos = df_p["monto"].sum() if not df_p.empty else 0
    total_gastos = df_g["monto"].sum() if not df_g.empty else 0
    utilidad = total_ingresos - total_gastos

    c1, c2, c3 = st.columns(3)
    c1.metric("Ingresos Totales (Caja)", fmt_moneda(total_ingresos))
    c2.metric("Gastos Totales", fmt_moneda(total_gastos), delta_color="inverse", delta=f"-{fmt_moneda(total_gastos)}")
    c3.metric("Utilidad Actual", fmt_moneda(utilidad))

    st.divider()

    # --- GRÁFICAS SENCILLAS ---
    col_izq, col_der = st.columns(2)

    with col_izq:
        st.write("### 📂 Gastos por Categoría")
        if not df_g.empty:
            gastos_cat = df_g.groupby("categoria")["monto"].sum()
            st.bar_chart(gastos_cat)
        else:
            st.info("No hay datos de gastos.")

    with col_der:
        st.write("### 💵 Flujo de Ingresos (Mensual)")
        if not df_p.empty:
            df_p['fecha'] = pd.to_datetime(df_p['fecha'])
            ingresos_mes = df_p.resample('M', on='fecha')['monto'].sum()
            st.line_chart(ingresos_mes)
        else:
            st.info("No hay datos de pagos.")
