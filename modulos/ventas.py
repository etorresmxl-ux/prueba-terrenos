import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

def render_ventas(df_v, df_c, df_u, conn, URL_SHEET, fmt_moneda, cargar_datos):
    st.title("🤝 Registro de Ventas")

    if df_c.empty or df_u.empty:
        st.warning("⚠️ Se requieren Clientes y Ubicaciones (Disponibles) para registrar una venta.")
        return

    # --- FILTRO DE UBICACIONES DISPONIBLES ---
    lotes_disponibles = df_u[df_u["estatus"] == "Disponible"]["ubicacion"].tolist()
    clientes_lista = df_c["nombre"].tolist()

    with st.form("form_nueva_venta"):
        st.subheader("Nueva Operación")
        c1, c2 = st.columns(2)
        
        f_ubi = c1.selectbox("📍 Seleccionar Ubicación", lotes_disponibles)
        f_cli = c2.selectbox("👤 Seleccionar Cliente", clientes_lista)
        
        # Obtener precio sugerido de la ubicación seleccionada
        precio_sug = float(df_u[df_u["ubicacion"] == f_ubi]["precio"].iloc[0])
        
        f_pre = c1.number_input("💰 Precio Pactado ($)", min_value=0.0, value=precio_sug)
        f_fec = c2.date_input("📅 Fecha de Venta", value=datetime.now())
        
        st.divider()
        st.write("📊 **Condiciones del Crédito**")
        cc1, cc2, cc3 = st.columns(3)
        
        f_eng = cc1.number_input("📥 Enganche ($)", min_value=0.0, value=f_pre * 0.1) # Sugiere 10%
        f_pla = cc2.number_input("📅 Plazo (Meses)", min_value=1, value=12, step=1)
        
        # Cálculo automático de mensualidad
        monto_financiar = f_pre - f_eng
        mensualidad_sug = monto_financiar / f_pla if f_pla > 0 else 0
        f_men = cc3.number_input("💳 Mensualidad ($)", min_value=0.0, value=mensualidad_sug)
        
        if st.form_submit_button("🚀 FINALIZAR VENTA", type="primary"):
            # 1. Generar ID de Venta
            id_v = 1
            if not df_v.empty and "id_venta" in df_v.columns:
                try: id_v = int(float(df_v["id_venta"].max())) + 1
                except: id_v = len(df_v) + 1
            
            # 2. Crear registro de venta
            nueva_vta = pd.DataFrame([{
                "id_venta": id_v,
                "fecha": f_fec.strftime('%Y-%m-%d'),
                "cliente": f_cli,
                "ubicacion": f_ubi,
                "precio_total": f_pre,
                "enganche": f_eng,
                "plazo_meses": f_pla,
                "mensualidad": f_men
            }])
            
            # 3. Actualizar Estatus de la Ubicación a 'Vendido'
            idx_u = df_u[df_u["ubicacion"] == f_ubi].index[0]
            df_u.at[idx_u, "estatus"] = "Vendido"
            
            # 4. Guardar en Google Sheets (Ambas tablas)
            df_v = pd.concat([df_v, nueva_vta], ignore_index=True)
            conn.update(spreadsheet=URL_SHEET, worksheet="ventas", data=df_v)
            conn.update(spreadsheet=URL_SHEET, worksheet="ubicaciones", data=df_u)
            
            st.success(f"✅ Venta registrada: {f_ubi} para {f_cli}")
            st.cache_data.clear()
            st.rerun()

    st.divider()
    st.write("### 📜 Ventas Recientes")
    st.dataframe(df_v, use_container_width=True, hide_index=True)
