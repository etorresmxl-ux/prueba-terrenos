import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import urllib.parse  # Para codificar los mensajes

def render_inicio(df_v, df_p, df_g, df_cl, fmt_moneda): # Añadimos df_cl para sacar los correos/tels
    # FILA SUPERIOR: Título y Fecha
    col_tit, col_fec = st.columns([3, 1])
    with col_tit:
        st.title("🏠 Tablero de Control")
    with col_fec:
        fecha_hoy = datetime.now().strftime('%d / %m / %Y')
        st.markdown(f"<p style='text-align: right; color: gray; padding-top: 25px;'><b>Fecha Actual:</b><br>{fecha_hoy}</p>", unsafe_allow_html=True)

    # MÉTRICAS PRINCIPALES
    c1, c2, c3 = st.columns(3)
    ingresos = (df_p["monto"].sum() if not df_p.empty else 0) + (df_v["enganche"].sum() if not df_v.empty else 0)
    egresos = df_g["monto"].sum() if not df_g.empty else 0
    
    c1.metric("Ingresos Totales", fmt_moneda(ingresos))
    c2.metric("Gastos Totales", fmt_moneda(egresos), delta=f"-{fmt_moneda(egresos)}", delta_color="inverse")
    c3.metric("Utilidad Neta", fmt_moneda(ingresos - egresos))

    st.divider()
    
    # MONITOR DE CARTERA DETALLADO
    st.subheader("🚩 Monitor de Cartera")
    if not df_v.empty:
        monitor = []
        hoy = datetime.now()
        
        for _, v in df_v.iterrows():
            pagos_especificos = df_p[df_p['ubicacion'] == v['ubicacion']] if not df_p.empty else pd.DataFrame()
            total_pagado_cliente = pagos_especificos['monto'].sum() if not pagos_especificos.empty else 0
            
            ultima_fecha_pago = pd.to_datetime(pagos_especificos['fecha']).max().strftime('%d/%m/%Y') if not pagos_especificos.empty else "Sin Pagos"
            
            # Lógica de Atraso
            f_contrato = pd.to_datetime(v['fecha'])
            mensualidad = float(v['mensualidad'])
            diff = relativedelta(hoy, f_contrato)
            meses_transcurridos = (diff.years * 12) + diff.months
            
            deuda_teorica = meses_transcurridos * mensualidad
            deuda_vencida = deuda_teorica - total_pagado_cliente
            
            # Cálculo de meses de atraso para el reto
            meses_atraso = deuda_vencida / mensualidad if mensualidad > 0 else 0
            accion_link = ""

            if deuda_vencida > 1.0:
                estatus = "🔴 ATRASO"
                cuotas_cubiertas = total_pagado_cliente / mensualidad
                fecha_vencimiento_pendiente = f_contrato + relativedelta(months=int(cuotas_cubiertas) + 1)
                dias_atraso = (hoy - fecha_vencimiento_pendiente).days if hoy > fecha_vencimiento_pendiente else 0
                
                # --- RETO: GENERAR ACCIÓN SI HAY > 3 MESES ---
                if meses_atraso >= 3:
                    # Buscamos datos del cliente en df_cl
                    c_info = df_cl[df_cl['nombre'] == v['cliente']].iloc[0] if not df_cl.empty else {}
                    correo = c_info.get('correo', '')
                    
                    asunto = "Invitación Especial - Actualización de Proyecto"
                    cuerpo = f"Hola {v['cliente']}, le invitamos a nuestras oficinas para platicar sobre su lote en {v['ubicacion']} y ofrecerle alternativas de pago. Saludos."
                    
                    # Codificar para URL
                    asunto_esc = urllib.parse.quote(asunto)
                    cuerpo_esc = urllib.parse.quote(cuerpo)
                    accion_link = f"mailto:{correo}?subject={asunto_esc}&body={cuerpo_esc}"
            else:
                estatus = "🟢 AL CORRIENTE"
                deuda_vencida = 0.0
                dias_atraso = 0
            
            saldo_restante = float(v['precio_total']) - float(v['enganche']) - total_pagado_cliente
            
            monitor.append({
                "Ubicación": v['ubicacion'], 
                "Cliente": v['cliente'], 
                "Estatus": estatus, 
                "Último Pago": ultima_fecha_pago,
                "Días de Atraso": dias_atraso,
                "Deuda Vencida": deuda_vencida,
                "Acción": accion_link  # Nueva columna para el link
            })
        
        df_monitor = pd.DataFrame(monitor)
        
        # Estilos
        df_estilizado = df_monitor.style.format({
            "Deuda Vencida": "$ {:,.2f}",
            "Días de Atraso": "{:,.0f} días"
        })
        
        # --- RENDERIZADO CON CONFIGURACIÓN DE COLUMNA DE LINK ---
        st.dataframe(
            df_estilizado, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Acción": st.column_config.LinkColumn(
                    "📧 Invitación",
                    display_text="Enviar Correo",
                    help="Disponible para atrasos mayores a 3 meses"
                )
            }
        )
    else:
        st.info("No hay ventas registradas.")
