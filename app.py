import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------------------------------------------------------------
# CONFIGURACIÓN DEL APLICATIVO WEB
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Control Financiero Personal | Dashboard",
    page_icon="💳",
    layout="wide"
)

st.title("📊 Control de Gastos & Finanzas Personales")
st.caption("Sincronización en tiempo real con Google Drive")
st.markdown("---")

# URL del archivo publicado en Google Sheets (Hoja 1)
URL_CSV = "https://docs.google.com/spreadsheets/d/1izhKwlt6UnFHF9UFjq5aU6QEpVwVV8xgr-kOz3678Rg/export?format=csv&gid=0"

@st.cache_data(ttl=5) # Refresca los datos automáticamente cada 5 segundos
def cargar_datos():
    try:
        # Cargar ignorando las primeras filas de título de presentación
        df_raw = pd.read_csv(URL_CSV, skiprows=2)
        # Limpieza de nombres de columnas
        df_raw.columns = [str(c).strip() for c in df_raw.columns]
        
        # Filtrar solo filas con datos en Categoría
        if 'Categoría' in df_raw.columns and 'Monto ($)' in df_raw.columns:
            df_clean = df_raw.dropna(subset=['Categoría', 'Monto ($)']).copy()
            
            # Limpiar columna de monto
            df_clean['Monto ($)'] = (
                df_clean['Monto ($)']
                .astype(str)
                .str.replace('$', '', regex=False)
                .str.replace(',', '', regex=False)
                .str.strip()
            )
            df_clean['Monto ($)'] = pd.to_numeric(df_clean['Monto ($)'], errors='coerce').fillna(0)
            df_clean['Fecha'] = pd.to_datetime(df_clean['Fecha'], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
            return df_clean
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al leer la hoja de cálculo: {e}")
        return pd.DataFrame()

df = cargar_datos()

if not df.empty:
    # Separación de Ingresos y Gastos
    es_ingreso = df['Categoría'].str.contains('QUIN|Ingreso|Sueldo', case=False, na=False)
    df_ingresos = df[es_ingreso]
    df_gastos = df[~es_ingreso]

    total_ingresos = df_ingresos['Monto ($)'].sum()
    total_gastos = df_gastos['Monto ($)'].sum()
    balance = total_ingresos - total_gastos

    # 1. METRICAS / KPIs PRINCIPALES
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💰 Total Ingresos", f"${total_ingresos:,.0f} COP")
    k2.metric("💸 Total Gastos", f"${total_gastos:,.0f} COP")
    
    color_delta = "normal" if balance >= 0 else "inverse"
    k3.metric("📈 Balance Disponible", f"${balance:,.0f} COP", 
              delta=f"{(balance/total_ingresos)*100:.1f}% restante" if total_ingresos > 0 else "0%", 
              delta_color=color_delta)

    deudas = df_gastos[df_gastos['Categoría'].str.contains('Tarjeta|Credito|Crédito', case=False, na=False)]['Monto ($)'].sum()
    k4.metric("💳 Servicio de Deuda", f"${deudas:,.0f} COP", delta=f"{(deudas/total_ingresos)*100:.1f}% del Ingreso", delta_color="inverse")

    st.markdown("---")

    # 2. GRÁFICOS DINÁMICOS
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("🍩 Gastos por Categoría")
        cat_summary = df_gastos.groupby('Categoría')['Monto ($)'].sum().reset_index()
        fig_donut = px.pie(cat_summary, values='Monto ($)', names='Categoría', hole=0.4,
                           color_discrete_sequence=px.colors.qualitative.Prism)
        st.plotly_chart(fig_donut, use_container_width=True)

    with c2:
        st.subheader("💳 Distribución por Método de Pago")
        pay_summary = df_gastos.groupby('Método de Pago')['Monto ($)'].sum().reset_index()
        fig_bar = px.bar(pay_summary, x='Método de Pago', y='Monto ($)', color='Método de Pago',
                         text_auto=',.0f', color_discrete_sequence=px.colors.qualitative.Safe)
        fig_bar.update_layout(showlegend=False, xaxis_title="", yaxis_title="COP ($)")
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # 3. TABLA DE REGISTROS
    st.subheader("📝 Historial de Transacciones")
    st.dataframe(df, use_container_width=True, hide_index=True)

else:
    st.warning("No se pudieron cargar los datos. Verifica los permisos de acceso de tu Google Sheet.")
