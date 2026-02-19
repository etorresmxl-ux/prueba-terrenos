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
    
    # --- MONITOR DE CARTERA CON ENLACES INTEGRADOS ---
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
            
            # Inicializamos variables de texto y link
            col_whatsapp = ""
            col_email = ""

            if deuda_vencida > 1.0:
                estatus = "🔴 ATRASO"
                cuotas_ok = total_pagado / mensualidad
                f_vence = f_con + relativedelta(months=int(cuotas_ok) + 1)
                dias_a = (hoy - f_vence).days if hoy > f_vence else 0
                
                # Acciones para morosidad >= 3 meses
                if m_atraso >= 3:
                    c_info = df_cl[df_cl['nombre'] == v['cliente']]
                    if not c_info.empty:
                        correo_real = str(c_info.iloc[0].get('correo', ''))
                        tel_real = str(c_info.iloc[0].get('telefono', ''))
                        
                        # Limpiar teléfono para el protocolo wa.me
                        tel_link = tel_real.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
                        
                        # Preparar mensaje
                        msj = f"Hola {v['cliente']}, le contactamos de Zona Valle respecto a su lote en {v['ubicacion']}..."
                        msj_enc = urllib.parse.quote(msj)
                        
                        # Construcción de los enlaces (esto es lo que se verá en la celda)
                        if tel_real:
                            col_whatsapp = f"https://wa.me/{tel_link}?text={msj_enc}"
                        if correo_real:
                            col_email = f"mailto:{correo_real}?subject=Invitación Especial&body={msj_enc}"
            else:
                estatus = "🟢 AL CORRIENTE"
                dias_a = 0

            # Guardamos los datos. Si no hay link, la celda dirá el dato pero no será link (o estará vacía)
            monitor.append({
                "Ubicación": v['ubicacion'], 
                "Cliente": v['cliente'], 
                "Estatus": estatus, 
                "Días de Atraso": dias_a,
                "Deuda Vencida": deuda_vencida,
                "WhatsApp": col_whatsapp, # Aquí va la URL completa
                "Email": col_email,        # Aquí va la URL completa
                "_tel_display": tel_real if 'tel_real' in locals() else "", # Guardamos texto plano para el display
                "_mail_display": correo_real if 'correo_real' in locals() else ""
            })
            # Limpiar variables locales para la siguiente iteración
            tel_real = ""; correo_real = ""
        
        df_mon = pd.DataFrame(monitor)

        # --- RENDERIZADO CON LINKS PERSONALIZADOS ---
        st.dataframe(
            df_mon.style.format({
                "Deuda Vencida": "$ {:,.2f}",
                "Días de Atraso": "{:,.0f} d"
            }),
            use_container_width=True,
            hide_index=True,
            column_config={
                "WhatsApp": st.column_config.LinkColumn(
                    "💬 WhatsApp", 
                    display_text=r"📲 (.*)", # Expresión regular para mostrar el número si existe el link
                    help="Haga clic para enviar mensaje"
                ),
                "Email": st.column_config.LinkColumn(
                    "📧 Correo", 
                    display_text=r"mailto:(.*)\?.*", # Muestra solo el correo quitando el resto del link mailto
                    help="Haga clic para enviar correo"
                ),
                "Días de Atraso": st.column_config.NumberColumn(format="%d días")
            }
        )
    else:
        st.info("No hay ventas registradas.")
