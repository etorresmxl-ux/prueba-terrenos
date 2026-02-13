import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Inmobiliaria - Drive", layout="wide")

# --- CREDENCIALES DIRECTAS ---
# He formateado tu JSON para que Streamlit lo reconozca directamente
creds = creds = {
  "type": "service_account",
  "project_id": "inmobiliaria-487222",
  "private_key_id": "5e3fa80e51ca83ba8c1fcc4d56347400ec45816f",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCzCReqLm7+QMuJ\niUaoYbTN4rKrg+VzD62VbM7a5e9Zb1MNTzDDiIXbuAC127Q0DuKes4NoJf8vaKlg\n3ZLoRoxnqn7gKgN7UDs04wW7gtmGICXL1F8TxWfrIbyfHJY179K4E0f/u+KE8s/3\n8EKXpOpQFMHeZzrkJF99Jq9hQscO3K0fQADhZfTQA/EZkBqmfNQKLA8jEPH49hJH\nIK+QNFh3uxZtFYV1FBR0oP7b4R937ySVJ98WLjW79B78YtDz3GZNrzSU72XWy4Ti\njNFbZUBWxSlYThjAuYrUI+8cZhKhM1ShbYEC+usgIzlY6ejMVnf75pGbZjPxE5Ha\nsAF7FiaFAgMBAAECggEAEelEdVGc6BHaawGRUJIp0Pkvj8orv9WfM5ZFoY+kYOmq\nwOedxMoZPjCL3aXDwvuEP4VNDbPTck5Bt7+jDVrVfB+J/uolHAacTb+ymJ5QHcOE\nlH5EHsm+ij7/TFnDS1UZWzIOn26QDGXwWWkveFVW3bkd5h6kvSNIbFBc9lmEaZ+O\nLwAMz4F2QEdgOg0tW+5N80/tmWdQpIDJAUk2poe/doAhQ/i8RrXJv66LSOiGOPGI\ngDYNTF+D1ZaJQQgSaynRgQ2oxxlDIh56c4o0cbZS4Amu0JgJDlKqXfK8v3AorzLD\nYaG+bq43zs8gsWrx9M+U8MZAiYDQL/TuT6AY2JU0JwKBgQDp9lGB74PIcXHoiXUx\n9tuW3lBr9SD509MsxQZyWLUbo3vGglqQqnj2r7dVcDDJFqnI84eNE1kkCi5sQt5G\nEdA7W9TrCVhn2AZ+pWyzgFqVhrofRBf58bSPjCjjZS8QQ5BeVj2ScGjYHEGL/dlj\nv8Ml3qGm5EdVh7fp+Gq0xujbFwKBgQDD5kq1ZCiA1ZhHzKsCQacPstePhtjBUCq+\nic4ud7r6IVGnLdRYb9zAvsBubNkddAqs1fvci+No/tpC+YAI5GuHd6d+/PTADfkv\noEFTQNJ1Tn0ioKm1N2XxZfabQjMykpp8dQnwPCNcrEQ/KxeSgn2VEB961z26AsgX\n7AQdX71cwwKBgC6yvJgbz4j9o8fPT/YWGMRnQVQbDGbxMdBYzy2ZqSSIIBeCQ0Nm\n01ghwI0sJICuplr2yNKOzxcTdSqkuirwOUjvznLPXbb0dm9m42h8sRfxWUsOU17P\nMMQKLMsekiND6Rf7TLTi/PpNwYOIupBfYTs40bk3DUn0GfB4ZgwJO8cnAoGAFMcN\nL3YDEb8V2q+rh569AF5AnLl5re85yWHGW4lZbIQyK+AhgIvExzC0KkIjOQuAwloj\nz32Kzi0Rqz7ZRJgti322ZzKfJuuUfWeq5hCfAdAkV5LgzRamGldtM4Ru97My7XZg\nanmGaqLezjBc3K44caH3JMlFg8AdxuPCf/cSl48CgYAyNcVSp3Ms0ZWmOarRhur6\nqciXpd7+tkIPn9dAzK+QZD0HgJVAYEO5BmSRpQdBoETbNc3j/Y5iXWUJW/L7ly2Y\niv/exwZffbABCVqglOn6aqyyoY81YzsdYBPJxAs6AK+vXO/mZyiYn7TjOgF4/ZPQ\nklUH/gsZNA67tlQySVewtQ==\n-----END PRIVATE KEY-----\n",
  "client_email": "inmobiliaria@inmobiliaria-487222.iam.gserviceaccount.com",
  "client_id": "118429869319608246472",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/inmobiliaria%40inmobiliaria-487222.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

URL_SHEET = "https://docs.google.com/spreadsheets/d/1TIeJ2fjJ6WHn124b8iL9LgTNuRZ_50YyekSad0uK1jE/"

# --- CONEXIÓN DEFINITIVA ---
try:
    # Usamos GSheetsConnection directamente para evitar el error de 'service_account'
    conn = st.connection("gsheets", type=GSheetsConnection, **creds)
except Exception as e:
    st.error(f"Error de conexión con Google Drive: {e}")
    st.stop()

# --- FUNCIONES DE APOYO ---
def leer(pestana):
    try:
        return conn.read(spreadsheet=URL_SHEET, worksheet=pestana)
    except:
        return pd.DataFrame()

def guardar(df, pestana):
    conn.update(spreadsheet=URL_SHEET, worksheet=pestana, data=df)
    st.cache_data.clear()

def f_money(v): return f"${float(v or 0):,.2f}"

# --- SEGURIDAD ---
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    st.title("🔐 Acceso")
    pwd = st.text_input("Clave maestra:", type="password")
    if st.button("Entrar"):
        if pwd == "Terrenos2026":
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("Incorrecto")
    st.stop()

# --- NAVEGACIÓN ---
choice = st.sidebar.radio("Menú", ["Resumen", "Nueva Venta", "Cobranza", "Ubicaciones", "Directorio"])

# --- SECCIÓN: UBICACIONES ---
if choice == "Ubicaciones":
    st.header("📍 Inventario en Drive")
    df_t = leer("terrenos")
    
    with st.form("nuevo_lote"):
        c1, c2, c3 = st.columns(3)
        m = c1.text_input("Manzana")
        l = c2.text_input("Lote")
        p = c3.number_input("Precio ($)", min_value=0.0)
        if st.form_submit_button("Guardar"):
            if m and l:
                nueva = pd.DataFrame([{"manzana": m, "lote": l, "costo": p, "estatus": "Disponible"}])
                df_f = pd.concat([df_t, nueva], ignore_index=True)
                guardar(df_f, "terrenos")
                st.success("Guardado")
                st.rerun()
    st.dataframe(df_t, use_container_width=True, hide_index=True)

# --- SECCIÓN: COBRANZA ---
elif choice == "Cobranza":
    st.header("💸 Cobranza")
    df_v = leer("ventas")
    df_p = leer("pagos")
    
    if not df_v.empty:
        with st.form("pago"):
            id_v = st.selectbox("ID Venta:", df_v.index.tolist())
            monto = st.number_input("Monto:", min_value=0.0)
            fecha = st.date_input("Fecha", datetime.now())
            if st.form_submit_button("Registrar"):
                n_p = pd.DataFrame([{"id_venta": id_v, "monto": monto, "fecha": fecha.strftime('%Y-%m-%d')}])
                df_pf = pd.concat([df_p, n_p], ignore_index=True)
                guardar(df_pf, "pagos")
                st.success("Registrado")
                st.rerun()
    else:
        st.info("No hay ventas registradas.")

# --- SECCIÓN: RESUMEN ---
elif choice == "Resumen":
    st.header("📋 Resumen")
    df_t = leer("terrenos")
    if not df_t.empty:
        st.metric("Total Lotes", len(df_t))
        st.dataframe(df_t, use_container_width=True)
    else:
        st.warning("Sin datos.")

# --- SECCIÓN: DIRECTORIO ---
elif choice == "Directorio":
    st.header("👥 Clientes")
    df_c = leer("clientes")
    st.dataframe(df_c, use_container_width=True)
    with st.expander("Nuevo Cliente"):
        nom = st.text_input("Nombre")
        if st.button("Agregar"):
            n_df = pd.concat([df_c, pd.DataFrame([{"nombre": nom}])], ignore_index=True)
            guardar(n_df, "clientes")
            st.rerun()


