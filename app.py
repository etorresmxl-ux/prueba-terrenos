import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Inmobiliaria", layout="wide")

# --- TUS CREDENCIALES (Copiadas de tu JSON) ---
# Al ponerlas aquí, la app no necesita el cuadro de "Secrets" de Streamlit
creds = {
    "type": "service_account",
    "project_id": "inmobiliaria-487222",
    "private_key_id": "5e3fa80e51ca83ba8c1fcc4d56347400ec45816f",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCzCReqLm7+QMuJ\niUaoYbTN4rKrg+VzD62VbM7a5e9Zb1MNTzDDiIXbuAC127Q0DuKes4NoJf8vaKlg\n3ZLoRoxnqn7gKgN7UDs04wW7gtmGICXL1F8TxWfrIbyfHJY179K4E0f/u+KE8s/3\n8EKXpOpQFMHeZzrkJF99Jq9hQscO3K0fQADhZfTQA/EZkBqmfNQKLA8jEPH49hJH\nIK+QNFh3uxZtFYV1FBR0oP7b4R937ySVJ98WLjW79B78YtDz3GZNrzSU72XWy4Ti\njNFbZUBWxSlYThjAuYrUI+8cZhKhM1ShbYEC+usgIzlY6ejMVnf75pGbZjPxE5Ha\nsAF7FiaFAgMBAAECggEAEelEdVGc6BHaawGRUJIp0Pkvj8orv9WfM5ZFoY+kYOmq\nwOedxMoZPjCL3aXDwvuEP4VNDbPTck5Bt7+jDVrVfB+J/uolHAacTb+ymJ5QHcOE\nlH5EHsm+ij7/TFnDS1UZWzIOn26QDGXwWWkveFVW3bkd5h6kvSNIbFBc9lmEaZ+O\nLwAMz4F2QEdgOg0tW+5N80/tmWdQpIDJAUk2poe/doAhQ/i8RrXJv66LSOiGOPGI\ngDYNTF+D1ZaJQQgSaynRgQ2oxxlDIh56c4o0cbZS4Amu0JgJDlKqXfK8v3AorzLD\nYaG+bq43zs8gsWrx9M+U8MZAiYDQL/TuT6AY2JU0JwKBgQDp9lGB74PIcXHoiXUx\n9tuW3lBr9SD509MsxQZyWLUbo3vGglqQqnj2r7dVcDDJFqnI84eNE1kkCi5sQt5G\nEdA7W9TrCVhn2AZ+pWyzgFqVhrofRBf58bSPjCjjZS8QQ5BeVj2ScGjYHEGL/dlj\nv8Ml3qGm5EdVh7fp+Gq0xujbFwKBgQDD5kq1ZCiA1ZhHzKsCQacPstePhtjBUCq+\nic4ud7r6IVGnLdRYb9zAvsBubNkddAqs1fvci+No/tpC+YAI5GuHd6d+/PTADfkv\noEFTQNJ1Tn0ioKm1N2XxZfabQjMykpp8dQnwPCNcrEQ/KxeSgn2VEB961z26AsgX\n7AQdX71cwwKBgC6yvJgbz4j9o8fPT/YWGMRnQVQbDGbxMdBYzy2ZqSSIIBeCQ0Nm\01ghwI0sJICuplr2yNKOzxcTdSqkuirwOUjvznLPXbb0dm9m42h8sRfxWUsOU17P\nMMQKLMsekiND6Rf7TLTi/PpNwYOIupBfYTs40bk3DUn0GfB4ZgwJO8cnAoGAFMcN\nL3YDEb8V2q+rh569AF5AnLl5re85yWHGW4lZbIQyK+AhgIvExzC0KkIjOQuAwloj\nz32Kzi0Rqz7ZRJgti322ZzKfJuuUfWeq5hCfAdAkV5LgzRamGldtM4Ru97My7XZg\nanmGaqLezjBc3K44caH3JMlFg8AdxuPCf/cSl48CgYAyNcVSp3Ms0ZWmOarRhur6\nqciXpd7+tkIPn9dAzK+QZD0HgJVAYEO5BmSRpQdBoETbNc3j/Y5iXWUJW/L7ly2Y\niv/exwZffbABCVqglOn6aqyyoY81YzsdYBPJxAs6AK+vXO/mZyiYn7TjOgF4/ZPQ\nklUH/gsZNA67tlQySVewtQ==\n-----END PRIVATE KEY-----\n",
    "client_email": "inmobiliaria@inmobiliaria-487222.iam.gserviceaccount.com",
    "client_id": "118429869319608246472",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/inmobiliaria%40inmobiliaria-487222.iam.gserviceaccount.com"
}

# Link de tu Google Sheet
URL_SHEET = "https://docs.google.com/spreadsheets/d/1TIeJ2fjJ6WHn124b8iL9LgTNuRZ_50YyekSad0uK1jE/"

# --- CONEXIÓN A GOOGLE SHEETS ---
try:
    # IMPORTANTE: Aquí pasamos 'creds' directamente para que funcione sin Secrets
    conn = st.connection("gsheets", type=GSheetsConnection, **creds)
except Exception as e:
    st.error(f"Error al conectar con Google: {e}")
    st.stop()

# --- FUNCIONES PARA LEER Y GUARDAR ---
def leer_datos(pestaña):
    return conn.read(spreadsheet=URL_SHEET, worksheet=pestaña)

def guardar_datos(df, pestaña):
    conn.update(spreadsheet=URL_SHEET, worksheet=pestaña, data=df)
    st.cache_data.clear()

# --- INTERFAZ DE LA APP ---
st.title("🏡 Sistema de Gestión Inmobiliaria")

menu = st.sidebar.selectbox("Selecciona una opción", ["Ver Inventario", "Registrar Terreno"])

if menu == "Ver Inventario":
    st.subheader("📊 Lotes Registrados en Google Sheets")
    try:
        df = leer_datos("terrenos")
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("La hoja está vacía.")
    except Exception as e:
        st.error(f"No se pudo leer la pestaña 'terrenos'. Revisa que el nombre sea exacto en tu Excel. Error: {e}")

elif menu == "Registrar Terreno":
    st.subheader("📝 Agregar Nuevo Lote")
    df_actual = leer_datos("terrenos")
    
    with st.form("formulario_registro"):
        col1, col2 = st.columns(2)
        manzana = col1.text_input("Número de Manzana")
        lote = col2.text_input("Número de Lote")
        precio = st.number_input("Precio de Venta", min_value=0.0)
        
        enviar = st.form_submit_button("Guardar Terreno")
        
        if enviar:
            if manzana and lote:
                # Crear la nueva fila
                nueva_fila = pd.DataFrame([{
                    "manzana": manzana,
                    "lote": lote,
                    "costo": precio,
                    "estatus": "Disponible"
                }])
                
                # Unir con lo que ya existe
                df_nuevo = pd.concat([df_actual, nueva_fila], ignore_index=True)
                
                # Subir a Google Sheets
                guardar_datos(df_nuevo, "terrenos")
                st.success(f"✅ ¡Terreno Mz {manzana} Lote {lote} guardado con éxito!")
                st.balloons()
            else:
                st.warning("Por favor rellena Manzana y Lote.")
