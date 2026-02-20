import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import urllib.parse

# NOTA: Asegúrate de pasar df_u (ubicaciones) desde app.py al llamar esta función
def render_inicio(df_v, df_p, df_g, df_cl, df_u, fmt_moneda):
    # --- FILA SUPERIOR ---
    col_tit, col_fec = st.columns([3, 1])
    with col_tit:
        st.title("🏠 Tablero de Control")
    with col_fec:
        fecha_hoy = datetime.now().strftime('%d / %m / %Y')
        st.markdown(f"<p style='text-align: right; color: gray; padding-top: 25px;'><b>Fecha Actual:</b><br>{fecha_hoy}</p>", unsafe_allow_html=True)

    # --- MÉTRICAS FINANCIERAS (FLUJO DE CAJA) ---
    st.subheader("📊 Resumen de Flujo")
    c1, c2, c3 = st.columns(3)
    ingresos = (df_p["monto"].sum() if not df_p.empty else 0) + (df_v["enganche"].sum() if not df_v.empty else 0)
    egresos = df_g["monto"].sum() if not df_g.empty else 0
    
    c1.metric("Ingresos Totales", fmt_moneda(ingresos))
    c2.metric("Gastos Totales", fmt_moneda(egresos), delta=f"-{fmt_moneda(egresos)}", delta_color="inverse")
    c3.metric("Utilidad Neta", fmt_moneda(ingresos - egresos))

    # --- NUEVA SECCIÓN: KPIs DE INVENTARIO Y CRÉDITO ---
    st.divider()
    st.subheader("🏢 Estado del Proyecto e Inventario")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    # Cálculos de Inventario
    total_lotes = len(df_u) if not df_u.empty else 0
    lotes_vendidos = len(df_v) if not df_v.empty else 0
    lotes_disponibles = total_lotes - lotes_vendidos
    porcentaje_ventas = (lotes_vendidos / total_lotes * 100) if total_lotes > 0 else 0

    # Cálculos de Cartera (Lo que falta por cobrar)
    valor_total_ventas = df_v["precio_total"].sum() if not df_v.empty else 0
    pagado_a_capital = ingresos # Enganches + Pagos
    cartera_pendiente = valor_total_ventas - pagado_a_capital
    porcentaje_liquidacion = (pagado_a_capital / valor_total_ventas * 100) if valor_total_ventas > 0 else 0

    kpi1.metric("Lotes Vendidos", f"{lotes_vendidos} / {total_lotes}", f"{porcentaje_ventas:.1f}%")
    kpi2.metric("Disponibles", lotes_disponibles)
    kpi3.metric("Capital en Calle", fmt_moneda(cartera_pendiente), help="Monto total pendiente de cobro de todos los lotes vendidos.")
    kpi4.metric("% Liquidación", f"{porcentaje_liquidacion:.1f}%", help="Porcentaje del valor total de ventas que ya ha sido cobrado.")

    st.divider()
    
    # --- MONITOR DE CARTERA ---
    st.subheader("🚩 Monitor de Cartera")
    if not df_v.empty:
        monitor = []
        hoy = datetime.now()
        
        for _, v in df_v.iterrows():
            pagos_esp = df_p[df_p['ubicacion'] == v['ubicacion']] if not df_p.empty else pd.DataFrame()
            total_pagado = pagos_esp['monto'].sum() if not pagos_esp.empty else 0
            
            # --- LÓGICA DE ÚLTIMO PAGO ---
            if not pagos_esp.empty:
                ultimo_registro = pagos_esp.sort_values('fecha', ascending=False).iloc[0]
                fecha_pago = pd.to_datetime(ultimo_registro['fecha']).strftime('%d/%m/%Y')
                monto_pago = fmt_moneda(ultimo_registro['monto'])
                txt_ultimo_pago = f"{fecha_pago} - {monto_pago}"
            else:
                txt_ultimo_pago = "Sin pagos"

            # 2. Lógica de Atraso
            f_con = pd.to_datetime(v['fecha'])
            mensualidad = float(v['mensualidad'])
            diff = relativedelta(hoy, f_con)
            m_transcurridos = (diff.years * 12) + diff.months
            deuda_vencida = max(0.0, (m_transcurridos * mensualidad) - total_pagado)
            m_atraso = deuda_vencida / mensualidad if mensualidad > 0 else 0
            
            link_wa = ""; link_mail = ""; dias_a = 0

            if deuda_vencida > 1.0:
                estatus = "🔴 ATRASO"
                cuotas_ok = total_pagado / mensualidad
                f_vence = f_con + relativedelta(months=int(cuotas_ok) + 1)
                dias_a = (hoy - f_vence).days if hoy > f_vence else 0
                
                if m_atraso >= 3:
                    c_info = df_cl[df_cl['nombre'] == v['cliente']]
                    if not c_info.empty:
                        correo = str(c_info.iloc[0].get('correo', ''))
                        tel = str(c_info.iloc[0].get('telefono', '')).replace(" ", "").replace("-", "")
                        msj = urllib.parse.quote(f"Hola {v['cliente']}, le contactamos de Zona Valle respecto a su lote en {v['ubicacion']}. Nos gustaría invitarle a la oficina para revisar su plan de pagos.")
                        if tel: link_wa = f"https://wa.me/{tel}?text={msj}"
                        if correo: link_mail = f"mailto:{correo}?subject=Invitación Especial&body={msj}"
            else:
                estatus = "🟢 AL CORRIENTE"
                dias_a = 0

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

        def destacar_atrasos(row):
            dias = row["Días de Atraso"]
            if dias > 75: return ['background-color: #FFB347; color: black'] * len(row)
            elif dias > 25: return ['background-color: #FDFD96; color: black'] * len(row)
            return [''] * len(row)

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
                "Días de Atraso": st.column_config.NumberColumn(format="%d días"),
                "Último Pago": st.column_config.TextColumn("📅 Último Pago")
            }
        )
    else:
        st.info("No hay ventas registradas.")
