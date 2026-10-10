import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DEL APLICATIVO WEB
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Control Financiero Personal",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Control & Dashboard Financiero Personal")
st.caption("Sincronización en tiempo real con Google Drive / Google Sheets")
st.markdown("---")

# ID de tu archivo de Google Sheets
SHEET_ID = "1izhKwlt6UnFHF9UFjq5aU6QEpVwVV8xgr-kOz3678Rg"
# URL en formato Google Viz Query (Evita errores HTTP 400 / 404)
URL_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Hoja%201"

@st.cache_data(ttl=5) # Refresca los datos automáticamente cada 5 segundos
def cargar_datos():
    try:
        # Cargar los datos crudos
        df_raw = pd.read_csv(URL_CSV)
        
        # Si la primera fila es título de presentación, buscar la fila con las cabeceras reales
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
        
        # Filtrar solo registros con Categoría y Monto válidos
        if 'Categoría' in df.columns and 'Monto ($)' in df.columns:
            df = df.dropna(subset=['Categoría', 'Monto ($)']).copy()
            
            # Formatear la columna de Monto ($)
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
        st.error(f"Error al conectar con la hoja de cálculo: {e}")
        return pd.DataFrame()

df = cargar_datos()

if not df.empty:
    # Separar Ingresos de Gastos
    es_ingreso = df['Categoría'].str.contains('QUIN|Ingreso|Sueldo', case=False, na=False)
    df_ingresos = df[es_ingreso]
    df_gastos = df[~es_ingreso]

    total_ingresos = df_ingresos['Monto ($)'].sum()
    total_gastos = df_gastos['Monto ($)'].sum()
    balance = total_ingresos - total_gastos

    # -----------------------------------------------------------------------------
    # 2. INDICADORES CLAVE (KPIs)
    # -----------------------------------------------------------------------------
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💰 Total Ingresos", f"${total_ingresos:,.0f} COP")
    k2.metric("💸 Total Gastos", f"${total_gastos:,.0f} COP")
    
    color_balance = "normal" if balance >= 0 else "inverse"
    k3.metric("📈 Balance Disponible", f"${balance:,.0f} COP", 
              delta=f"{(balance/total_ingresos)*100:.1f}% del Ingreso" if total_ingresos > 0 else "0%",
              delta_color=color_balance)

    deudas = df_gastos[df_gastos['Categoría'].str.contains('Tarjeta|Credito|Crédito', case=False, na=False)]['Monto ($)'].sum()
    porcentaje_deuda = (deudas / total_ingresos * 100) if total_ingresos > 0 else 0
    k4.metric("💳 Compromiso de Deuda", f"${deudas:,.0f} COP", delta=f"{porcentaje_deuda:.1f}% del Ingreso", delta_color="inverse")

    st.markdown("---")

    # -----------------------------------------------------------------------------
    # 3. GRÁFICOS DIDÁCTICOS DE SALIDA Y ENTRADA DE DINERO
    # -----------------------------------------------------------------------------
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🍩 Gastos por Categoría")
        cat_summary = df_gastos.groupby('Categoría')['Monto ($)'].sum().reset_index()
        cat_summary = cat_summary.sort_values(by='Monto ($)', ascending=False)
        fig_donut = px.pie(cat_summary, values='Monto ($)', names='Categoría', hole=0.45,
                           color_discrete_sequence=px.colors.qualitative.Prism)
        fig_donut.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_donut, use_container_width=True)

    with col2:
        st.subheader("💳 Distribución por Método de Pago")
        pay_summary = df_gastos.groupby('Método de Pago')['Monto ($)'].sum().reset_index()
        fig_bar = px.bar(pay_summary, x='Método de Pago', y='Monto ($)', color='Método de Pago',
                         text_auto=',.0f', color_discrete_sequence=px.colors.qualitative.Safe)
        fig_bar.update_layout(showlegend=False, xaxis_title="", yaxis_title="Monto ($ COP)")
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # -----------------------------------------------------------------------------
    # 4. SEMÁFORO DE LÍMITES PRESUPUESTALES SUGERIDOS
    # -----------------------------------------------------------------------------
    st.subheader("🚨 Semáforo de Control de Dinero y Limites")

    lim1, lim2, lim3 = st.columns(3)

    limite_deuda = total_ingresos * 0.35
    with lim1:
        st.caption("💳 **Servicio de Deuda (Tarjetas & Créditos)**")
        st.progress(min(deudas / limite_deuda, 1.0) if limite_deuda > 0 else 0)
        if deudas > limite_deuda:
            st.error(f"❌ Sobrepasado: ${deudas:,.0f} (Máx sugerido: ${limite_deuda:,.0f})")
        else:
            st.success(f"✅ Rango Seguro: ${deudas:,.0f} de ${limite_deuda:,.0f}")

    gastos_hormiga = df_gastos[df_gastos['Categoría'].isin(['Imprevistos', 'Alimentación', 'Entretenimiento'])]['Monto ($)'].sum()
    limite_hormiga = 250000
    with lim2:
        st.caption("🍔 **Gastos Hormiga & Ocio**")
        st.progress(min(gastos_hormiga / limite_hormiga, 1.0))
        if gastos_hormiga > limite_hormiga:
            st.warning(f"⚠️ Alerta: ${gastos_hormiga:,.0f} (Tope recomendado: ${limite_hormiga:,.0f})")
        else:
            st.success(f"✅ Bajo Control: ${gastos_hormiga:,.0f} de ${limite_hormiga:,.0f}")

    servicios_fijos = df_gastos[df_gastos['Categoría'].str.contains('Servicios|Administracion', case=False, na=False)]['Monto ($)'].sum()
    limite_servicios = 550000
    with lim3:
        st.caption("🏠 **Gastos Fijos Hogar**")
        st.progress(min(servicios_fijos / limite_servicios, 1.0))
        st.success(f"✅ Gastos Fijos en Rango: ${servicios_fijos:,.0f}")

    st.markdown("---")

    # -----------------------------------------------------------------------------
    # 5. TABLA FILTRABLE DE TRANSACCIONES
    # -----------------------------------------------------------------------------
    st.subheader("📝 Historial de Entradas y Salidas")
    st.dataframe(df, use_container_width=True, hide_index=True)

else:
    st.warning("⚠️ No se pudieron cargar datos desde la hoja. Asegúrate de haber completado la opción 'Publicar en la web' en Google Sheets.")
