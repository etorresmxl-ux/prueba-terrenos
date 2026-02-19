import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import urllib.parse

def render_inicio(df_v, df_p, df_g, df_cl, fmt_moneda):
    # --- FILA SUPERIOR ---
    col_tit, col_fec = st.columns([3, 1])
    with col_tit:
        st.title("🏠 Tablero de Control")
    with col_fec:
        fecha_hoy = datetime.now().strftime('%d / %m / %Y')
        st.markdown(f"<p style='text-align: right; color: gray; padding-top: 25px;'><b>Fecha Actual:</b><br>{fecha_hoy}</p>", unsafe_allow_html=True)

    # --- MÉTRICAS ---
    c1, c2, c3 = st.columns(3)
    ingresos = (df_p["monto"].sum() if not df_p.empty else 0) + (df_v["enganche"].sum() if not df_v.empty else 0)
    egresos = df_g["monto"].sum() if not df_g.empty else 0
    
    c1.metric("Ingresos Totales", fmt_moneda(ingresos))
    c2.metric("Gastos Totales", fmt_moneda(egresos), delta=f"-{fmt_moneda(egresos)}", delta_color="inverse")
    c3.metric("Utilidad Neta", fmt_moneda(ingresos - egresos))

    st.divider()
    
    # --- MONITOR DE CARTERA CON DOBLE ACCIÓN Y VALIDACIÓN ---
    st.subheader("🚩 Monitor de Cartera")
    if not df_v.empty:
        monitor = []
        hoy = datetime.now()
        
        for _, v in df_v.iterrows():
            pagos_esp = df_p[df_p['ubicacion'] == v['ubicacion']] if not df_p.empty else pd.DataFrame()
            total_pagado = pagos_esp['monto'].sum() if not pagos_esp.empty else 0
            
            # Lógica de Atraso
            f_con = pd.to_datetime(v['fecha'])
            mensualidad = float(v['mensualidad'])
            diff = relativedelta(hoy, f_con)
            m_transcurridos = (diff.years * 12) + diff.months
            deuda_vencida = max(0.0, (m_transcurridos * mensualidad) - total_pagado)
            m_atraso = deuda_vencida / mensualidad if mensualidad > 0 else 0
            
            link_mail = ""
            link_wa = ""
            val_tel = ""   # Variable para mostrar el texto del teléfono
            val_cor = ""   # Variable para mostrar el texto del correo

            if deuda_vencida > 1.0:
                estatus = "🔴 ATRASO"
                cuotas_ok = total_pagado / mensualidad
                f_vence = f_con + relativedelta(months=int(cuotas_ok) + 1)
                dias_a = (hoy - f_vence).days if hoy > f_vence else 0
                
                # --- ACCIONES PARA MOROSIDAD > 3 MESES ---
                if m_atraso >= 3:
                    c_info = df_cl[df_cl['nombre'] == v['cliente']]
                    if not c_info.empty:
                        val_cor = str(c_info.iloc[0].get('correo', ''))
                        val_tel = str(c_info.iloc[0].get('telefono', ''))
                        
                        # Limpiar teléfono para el link
                        tel_link = val_tel.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
                        
                        msj = f"Hola {v['cliente']}, le contactamos de Zona Valle respecto a su lote en {v['ubicacion']}. Nos gustaría invitarle a la oficina para revisar su plan de pagos. ¿Qué día podría visitarnos?"
                        msj_enc = urllib.parse.quote(msj)
                        
                        link_mail = f"mailto:{val_cor}?subject=Invitación Especial&body={msj_enc}"
                        link_wa = f"https://wa.me/{tel_link}?text={msj_enc}"
            else:
                estatus = "🟢 AL CORRIENTE"
                dias_a = 0

            monitor.append({
                "Ubicación": v['ubicacion'], 
                "Cliente": v['cliente'], 
                "Estatus": estatus, 
                "Días de Atraso": dias_a,
                "Deuda Vencida": deuda_vencida,
                "WhatsApp": link_wa,
                "Confirmar Tel": val_tel, # Nueva columna visible
                "Email": link_mail,
                "Confirmar Correo": val_cor # Nueva columna visible
            })
        
        df_mon = pd.DataFrame(monitor)
        
        # Configuración de la tabla con validación a la derecha de los botones
        st.dataframe(
            df_mon.style.format({
                "Deuda Vencida": "$ {:,.2f}",
                "Días de Atraso": "{:,.0f} d"
            }),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Deuda Vencida": st.column_config.TextColumn("Deuda Vencida"),
                "WhatsApp": st.column_config.LinkColumn("💬 WA", display_text="📲 Enviar"),
                "Confirmar Tel": st.column_config.TextColumn("📞 Teléfono"),
                "Email": st.column_config.LinkColumn("📧 Correo", display_text="📩 Enviar"),
                "Confirmar Correo": st.column_config.TextColumn("📩 Correo Electrónico"),
                "Días de Atraso": st.column_config.NumberColumn(format="%d días")
            }
        )
    else:
        st.info("No hay ventas registradas.")
