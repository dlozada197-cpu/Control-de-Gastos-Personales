import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DEL APLICATIVO WEB
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Control Financiero Personal",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo visual moderno y limpio
st.markdown("""
    <style>
    .main { background-color: #F8F9FA; }
    .stMetric {
        background-color: #FFFFFF;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0px 2px 8px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Control & Dashboard Financiero Personal")
st.caption("Sincronización en tiempo real con tu hoja en Google Drive")
st.markdown("---")

# URL directa de publicación que generaste
URL_PUBLIC_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS_6bYgfZj3uKZ_g-zxDZToMdk_17SSWKdszzbjaaqm60dAx-D5GtuA9h5Fq1rs_c4UZy5yBcEH0gwd/pub?gid=706875207&single=true&output=csv"

@st.cache_data(ttl=5) # Refresca datos automáticamente cada 5 segundos
def cargar_datos():
    try:
        # Cargar CSV desde el enlace publicado de Google Sheets
        df_raw = pd.read_csv(URL_PUBLIC_CSV)
        
        # Detectar la fila de encabezados si hay títulos iniciales
        if 'Categoría' not in df_raw.columns:
            header_idx = None
            for idx, row in df_raw.iterrows():
                if row.astype(str).str.contains('Categoría', case=False).any():
                    header_idx = idx
                    break
            
            if header_idx is not None:
                df_raw.columns = df_raw.iloc[header_idx].values
                df = df_raw.iloc[header_idx + 1:].copy()
            else:
                df = df_raw.copy()
        else:
            df = df_raw.copy()

        # Limpiar nombres de columnas
        df.columns = [str(c).strip() for c in df.columns if pd.notna(c)]
        
        # Filtrar solo filas válidas
        if 'Categoría' in df.columns and 'Monto ($)' in df.columns:
            df = df.dropna(subset=['Categoría', 'Monto ($)']).copy()
            
            # Formatear montos numéricos
            df['Monto ($)'] = (
                df['Monto ($)']
                .astype(str)
                .str.replace('$', '', regex=False)
                .str.replace(',', '', regex=False)
                .str.strip()
            )
            df['Monto ($)'] = pd.to_numeric(df['Monto ($)'], errors='coerce').fillna(0)
            df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Error al cargar la información: {e}")
        return pd.DataFrame()

df = cargar_datos()

if not df.empty:
    # Clasificación entre Ingresos y Gastos
    es_ingreso = df['Categoría'].str.contains('QUIN|Ingreso|Sueldo', case=False, na=False)
    df_ingresos = df[es_ingreso]
    df_gastos = df[~es_ingreso]

    total_ingresos = df_ingresos['Monto ($)'].sum()
    total_gastos = df_gastos['Monto ($)'].sum()
    balance = total_ingresos - total_gastos

    # -----------------------------------------------------------------------------
    # 2. METRICAS / KPIs PRINCIPALES
    # -----------------------------------------------------------------------------
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💰 Total Ingresos", f"${total_ingresos:,.0f} COP")
    k2.metric("💸 Total Gastos", f"${total_gastos:,.0f} COP")
    
    color_balance = "normal" if balance >= 0 else "inverse"
    k3.metric("📈 Balance Disponible", f"${balance:,.0f} COP", 
              delta=f"{(balance/total_ingresos)*100:.1f}% restante" if total_ingresos > 0 else "0%",
              delta_color=color_balance)

    deudas = df_gastos[df_gastos['Categoría'].str.contains('Tarjeta|Credito|Crédito', case=False, na=False)]['Monto ($)'].sum()
    porcentaje_deuda = (deudas / total_ingresos * 100) if total_ingresos > 0 else 0
    k4.metric("💳 Servicio de Deuda", f"${deudas:,.0f} COP", delta=f"{porcentaje_deuda:.1f}% del Ingreso", delta_color="inverse")

    st.markdown("---")

    # -----------------------------------------------------------------------------
    # 3. VISUALIZACIÓN GRÁFICA INTERACTIVA
    # -----------------------------------------------------------------------------
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🍩 Distribución de Gastos por Categoría")
        cat_summary = df_gastos.groupby('Categoría')['Monto ($)'].sum().reset_index()
        cat_summary = cat_summary.sort_values(by='Monto ($)', ascending=False)
        fig_donut = px.pie(cat_summary, values='Monto ($)', names='Categoría', hole=0.45,
                           color_discrete_sequence=px.colors.qualitative.Prism)
        fig_donut.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_donut, use_container_width=True)

    with col2:
        st.subheader("💳 Gastos por Método de Pago")
        pay_summary = df_gastos.groupby('Método de Pago')['Monto ($)'].sum().reset_index()
        fig_bar = px.bar(pay_summary, x='Método de Pago', y='Monto ($)', color='Método de Pago',
                         text_auto=',.0f', color_discrete_sequence=px.colors.qualitative.Safe)
        fig_bar.update_layout(showlegend=False, xaxis_title="", yaxis_title="Monto ($ COP)")
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # -----------------------------------------------------------------------------
    # 4. SEMÁFORO Y ALERTAS DE LÍMITES PRESUPUESTALES
    # -----------------------------------------------------------------------------
    st.subheader("🚨 Semáforo de Control Presupuestal")

    lim1, lim2, lim3 = st.columns(3)

    limite_deuda = total_ingresos * 0.35
    with lim1:
        st.caption("💳 **Tarjetas & Créditos (Máx 35% Ingresos)**")
        st.progress(min(deudas / limite_deuda, 1.0) if limite_deuda > 0 else 0)
        if deudas > limite_deuda:
            st.error(f"❌ Alerta Deuda: ${deudas:,.0f} (Límite: ${limite_deuda:,.0f})")
        else:
            st.success(f"✅ Rango Seguro: ${deudas:,.0f} COP")

    gastos_hormiga = df_gastos[df_gastos['Categoría'].isin(['Imprevistos', 'Alimentación', 'Entretenimiento'])]['Monto ($)'].sum()
    limite_hormiga = 250000
    with lim2:
        st.caption("🍔 **Gastos Variables & Ocio (Sugerido $250k)**")
        st.progress(min(gastos_hormiga / limite_hormiga, 1.0))
        if gastos_hormiga > limite_hormiga:
            st.warning(f"⚠️ Atención: ${gastos_hormiga:,.0f} COP")
        else:
            st.success(f"✅ Bajo Control: ${gastos_hormiga:,.0f} COP")

    servicios_fijos = df_gastos[df_gastos['Categoría'].str.contains('Servicios|Administracion', case=False, na=False)]['Monto ($)'].sum()
    with lim3:
        st.caption("🏠 **Servicios Fijos Hogar**")
        st.progress(min(servicios_fijos / 550000, 1.0))
        st.success(f"✅ Gastos Fijos: ${servicios_fijos:,.0f} COP")

    st.markdown("---")

    # -----------------------------------------------------------------------------
    # 5. TABLA Y REGISTROS
    # -----------------------------------------------------------------------------
    st.subheader("📝 Historial Completo de Movimientos")
    st.dataframe(df, use_container_width=True, hide_index=True)

else:
    st.error("No se encontraron registros válidos en la hoja. Asegúrate de guardar los cambios en Google Drive.")
