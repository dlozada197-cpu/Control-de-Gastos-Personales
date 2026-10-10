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

# Estilo visual moderno y pulido
st.markdown("""
    <style>
    .main { background-color: #F8F9FA; }
    .stMetric {
        background-color: #FFFFFF;
        padding: 16px;
        border-radius: 12px;
        box-shadow: 0px 3px 10px rgba(0,0,0,0.04);
        border-top: 4px solid #1E88E5;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Control & Dashboard Financiero Personal")
st.caption("Sincronización automática con tu archivo en Google Drive")
st.markdown("---")

# URL de publicación CSV proporcionada por Google Sheets
URL_PUBLIC_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS_6bYgfZj3uKZ_g-zxDZToMdk_17SSWKdszzbjaaqm60dAx-D5GtuA9h5Fq1rs_c4UZy5yBcEH0Gwd/pub?gid=706875207&single=true&output=csv"

@st.cache_data(ttl=5) # Refresca datos automáticamente cada 5 segundos
def cargar_y_limpiar_datos():
    try:
        # Cargar los datos crudos sin asumirlos como encabezado estricto
        df_raw = pd.read_csv(URL_PUBLIC_CSV, header=None)
        
        # Eliminar columnas completamente vacías (como la columna A)
        df_raw = df_raw.dropna(how='all', axis=1)
        
        # Buscar la fila donde se encuentran las cabeceras reales
        header_idx = None
        for idx, row in df_raw.iterrows():
            row_str = row.astype(str).str.lower()
            if row_str.str.contains('categoría|categoria', case=False).any():
                header_idx = idx
                break
        
        if header_idx is not None:
            # Asignar esa fila como encabezados
            headers = df_raw.iloc[header_idx].values
            df = df_raw.iloc[header_idx + 1:].copy()
            df.columns = [str(h).strip() for h in headers]
        else:
            df = df_raw.copy()

        # Eliminar espacios vacíos de los nombres de columnas
        df.columns = [str(c).strip() for c in df.columns]

        # Filtrar solo registros válidos que contengan 'Categoría' y 'Monto ($)'
        col_cat = [c for c in df.columns if 'categor' in c.lower()]
        col_monto = [c for c in df.columns if 'monto' in c.lower()]

        if col_cat and col_monto:
            name_cat = col_cat[0]
            name_monto = col_monto[0]

            df = df.dropna(subset=[name_cat, name_monto]).copy()

            # Renombrar estandarizadamente para el resto de la app
            df = df.rename(columns={name_cat: 'Categoría', name_monto: 'Monto ($)'})

            # Formatear la columna de Monto ($)
            df['Monto ($)'] = (
                df['Monto ($)']
                .astype(str)
                .str.replace('$', '', regex=False)
                .str.replace(',', '', regex=False)
                .str.strip()
            )
            df['Monto ($)'] = pd.to_numeric(df['Monto ($)'], errors='coerce').fillna(0)

            # Formatear fecha
            col_fecha = [c for c in df.columns if 'fecha' in c.lower()]
            if col_fecha:
                df['Fecha'] = pd.to_datetime(df[col_fecha[0]], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')

            return df
        else:
            return pd.DataFrame()

    except Exception as e:
        st.error(f"Error procesando la información: {e}")
        return pd.DataFrame()

df = cargar_y_limpiar_datos()

if not df.empty:
    # Clasificación automática entre Ingresos y Gastos
    es_ingreso = df['Categoría'].str.contains('QUIN|Ingreso|Sueldo', case=False, na=False)
    df_ingresos = df[es_ingreso]
    df_gastos = df[~es_ingreso]

    total_ingresos = df_ingresos['Monto ($)'].sum()
    total_gastos = df_gastos['Monto ($)'].sum()
    balance = total_ingresos - total_gastos

    # -----------------------------------------------------------------------------
    # 2. INDICADORES Y RESUMEN FINANCIERO (KPIs)
    # -----------------------------------------------------------------------------
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💰 Total Ingresos", f"${total_ingresos:,.0f} COP")
    k2.metric("💸 Total Gastos", f"${total_gastos:,.0f} COP")
    
    color_balance = "normal" if balance >= 0 else "inverse"
    k3.metric("📈 Balance Disponible", f"${balance:,.0f} COP", 
              delta=f"{(balance/total_ingresos)*100:.1f}% del ingreso" if total_ingresos > 0 else "0%",
              delta_color=color_balance)

    deudas = df_gastos[df_gastos['Categoría'].str.contains('Tarjeta|Credito|Crédito', case=False, na=False)]['Monto ($)'].sum()
    porcentaje_deuda = (deudas / total_ingresos * 100) if total_ingresos > 0 else 0
    k4.metric("💳 Servicio de Deuda", f"${deudas:,.0f} COP", delta=f"{porcentaje_deuda:.1f}% del Ingreso", delta_color="inverse")

    st.markdown("---")

    # -----------------------------------------------------------------------------
    # 3. GRÁFICOS INTERACTIVOS DE ENTRADA Y SALIDA
    # -----------------------------------------------------------------------------
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🍩 Distribución de Gastos por Categoría")
        cat_summary = df_gastos.groupby('Categoría')['Monto ($)'].sum().reset_index()
        cat_summary = cat_summary.sort_values(by='Monto ($)', ascending=False)
        
        fig_donut = px.pie(
            cat_summary, values='Monto ($)', names='Categoría', hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        fig_donut.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_donut, use_container_width=True)

    with col2:
        col_metodo = [c for c in df.columns if 'm\u00e9todo' in c.lower() or 'metodo' in c.lower() or 'pago' in c.lower()]
        nombre_metodo = col_metodo[0] if col_metodo else 'Método de Pago'
        
        st.subheader("💳 Gastos por Método de Pago")
        pay_summary = df_gastos.groupby(nombre_metodo)['Monto ($)'].sum().reset_index()
        fig_bar = px.bar(
            pay_summary, x=nombre_metodo, y='Monto ($)', color=nombre_metodo,
            text_auto=',.0f', color_discrete_sequence=px.colors.qualitative.Safe
        )
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
            st.error(f"❌ Alerta Deuda: ${deudas:,.0f} COP (Límite: ${limite_deuda:,.0f} COP)")
        else:
            st.success(f"✅ Rango Seguro: ${deudas:,.0f} COP")

    gastos_hormiga = df_gastos[df_gastos['Categoría'].isin(['Imprevistos', 'Alimentación', 'Entretenimiento'])]['Monto ($)'].sum()
    limite_hormiga = 250000
    with lim2:
        st.caption("🍔 **Gastos Variables & Ocio (Sugerido $250k)**")
        st.progress(min(gastos_hormiga / limite_hormiga, 1.0))
        if gastos_hormiga > limite_hormiga:
            st.warning(f"⚠️ Alerta Ocio/Imprevistos: ${gastos_hormiga:,.0f} COP")
        else:
            st.success(f"✅ Bajo Control: ${gastos_hormiga:,.0f} COP")

    servicios_fijos = df_gastos[df_gastos['Categoría'].str.contains('Servicios|Administracion', case=False, na=False)]['Monto ($)'].sum()
    with lim3:
        st.caption("🏠 **Servicios Fijos Hogar**")
        st.progress(min(servicios_fijos / 550000, 1.0))
        st.success(f"✅ Gastos Fijos: ${servicios_fijos:,.0f} COP")

    st.markdown("---")

    # -----------------------------------------------------------------------------
    # 5. TABLA Y REGISTROS FILTRABLES
    # -----------------------------------------------------------------------------
    st.subheader("📝 Historial Completo de Movimientos")
    st.dataframe(df, use_container_width=True, hide_index=True)

else:
    st.error("No se encontraron registros. Asegúrate de que la hoja en Google Drive tenga información en la fila de 'Categoría' y 'Monto ($)'.")
