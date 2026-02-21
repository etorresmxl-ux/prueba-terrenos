import streamlit as st

def render_inicio(df_v, df_p, df_cl, fmt_moneda):
    st.title("🏠 Sistema Zona Valle")
    st.success("✅ ¡Conexión exitosa!")
    
    st.info("El sistema está restableciendo los módulos. Una vez que el archivo de requisitos termine de instalarse, verás las gráficas avanzadas aquí.")
    
    c1, c2 = st.columns(2)
    c1.metric("Ventas Registradas", len(df_v) if not df_v.empty else 0)
    c2.metric("Clientes Activos", len(df_cl) if not df_cl.empty else 0)
