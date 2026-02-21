import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import urllib.parse

def render_inicio(df_v, df_p, df_cl, fmt_moneda):
    # --- FILA SUPERIOR ---
    col_tit, col_fec = st.columns([3, 1])
    with col_tit:
        st.title("🏠 Gestión de Cartera")

    with col_fec:
        fecha_hoy = datetime.now().strftime('%d / %m / %Y')
        st.markdown(f"<p style='text-align: right; color: gray; padding-top: 25px;'><b>Fecha Actual:</b><br>{fecha_hoy}</p>", unsafe_allow_html=True)

    # --- LÓGICA DE DATOS ---
    if not df_v.empty:
        monitor = []
        hoy = datetime.now()
        
        for _, v in df_v.iterrows():
            pagos_esp = df_p[df_p['ubicacion'] == v['ubicacion']] if not df_p.empty else pd.DataFrame()
            total_pagado = pagos_esp['monto'].sum() if not pagos_esp.empty else 0
            
            # --- ÚLTIMO PAGO ---
            if not pagos_esp.empty:
                ultimo_registro = pagos_esp.sort_values('fecha', ascending=False).iloc[0]
                fecha_pago = pd.to_datetime(ultimo_registro['fecha']).strftime('%d/%m/%Y')
                monto_pago = fmt_moneda(ultimo_registro['monto'])
                txt_ultimo_pago = f"{fecha_pago} - {monto_pago}"
            else:
                txt_ultimo_pago = "Sin pagos"

            # --- ATRASO ---
            f_con = pd.to_datetime(v['fecha'])
            mensualidad = float(v['mensualidad'])
            diff = relativedelta(hoy, f_con)
            m_transcurridos = (diff.years * 12) + diff.months
            deuda_vencida = max(0.0, (m_transcurridos * mensualidad) - total_pagado)
            
            link_wa = ""; link_mail = ""; dias_a = 0

            if deuda_vencida > 1.0:
                estatus = "🔴 ATRASO"
                cuotas_ok = total_pagado / mensualidad
                f_vence = f_con + relativedelta(months=int(cuotas_ok) + 1)
                dias_a = (hoy - f_vence).days if hoy > f_vence else 0
                
                m_atraso = deuda_vencida / mensualidad if mensualidad > 0 else 0
                if m_atraso >= 3:
                    c_info = df_cl[df_cl['nombre'] == v['cliente']]
                    if not c_info.empty:
                        correo = str(c_info.iloc[0].get('correo', ''))
                        tel = str(c_info.iloc[0].get('telefono', '')).replace(" ", "").replace("-", "")
                        msj = urllib.parse.quote(f"Hola {v['cliente']}, le contactamos de Zona Valle...")
                        if tel: link_wa = f"https://wa.me/{tel}?text={msj}"
                        if correo: link_mail = f"mailto:{correo}?subject=Aviso&body={msj}"
            else:
                estatus = "🟢 AL CORRIENTE"

            monitor.append({
                "Ubicación": v['ubicacion'], 
                "Cliente": v['cliente'], 
                "Estatus": estatus, 
                "Último Pago": txt_ultimo_pago,
                "Días de Atraso": dias_a,
                "Deuda Vencida": deuda_vencida,
                "WhatsApp": link_wa,
                "Email": link_mail
            })
        
        df_mon = pd.DataFrame(monitor)

        # --- MÉTRICAS ---
        c1, c2, c3 = st.columns(3)
        c1.metric("Clientes en Atraso", len(df_mon[df_mon["Estatus"] == "🔴 ATRASO"]))
        c2.metric("Casos Críticos (>75 d)", len(df_mon[df_mon["Días de Atraso"] > 75]))
        c3.metric("Monto Vencido", fmt_moneda(df_mon["Deuda Vencida"].sum()))

        st.divider()

        # --- CORRECCIÓN DE ESTILO (Aquí estaba el error de comillas) ---
        def destacar_atrasos(row):
            dias = row["Días de Atraso"]
            if dias > 75:
                return ['background-color: #FFB347; color: black'] * len(row)
            elif dias > 25:
                return ['background-color: #FDFD96; color: black'] * len(row)
            return [''] * len(row)

        st.subheader("🚩 Monitor de Cobranza")
        df_estilizado = df_mon.style.apply(destacar_atrasos, axis=1).format({
            "Deuda Vencida": "$ {:,.2f}",
            "Días de Atraso": "{:,.0f} d"
        })

        st.dataframe(
            df_estilizado,
            use_container_width=True,
            hide_index=True,
            column_config={
                "WhatsApp": st.column_config.LinkColumn("💬 WA", display_text="📲 Enviar"),
                "Email": st.column_config.LinkColumn("📧 Correo", display_text="📩 Enviar"),
                "Días de Atraso": st.column_config.NumberColumn(format="%d días")
            }
        )
