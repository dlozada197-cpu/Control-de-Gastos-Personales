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

st.title("📊 Control & Dashboard Financiero Personal")
st.caption("Sincronización en tiempo real con Google Drive / Google Sheets")
st.markdown("---")

# ID de tu archivo de Google Sheets
SHEET_ID = "1izhKwlt6UnFHF9UFjq5aU6QEpVwVV8xgr-kOz3678Rg"
# URL en formato Google Viz Query (No requiere publicar en la web y no expira)
URL_GVIZ = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=5) # Refresca datos automáticamente cada 5 segundos
def cargar_datos():
    try:
        # Cargar tabla desde Google Viz API
        df_raw = pd.read_csv(URL_GVIZ)
        
        # Eliminar columnas sin nombre o vacías
        df_raw = df_raw.loc[:, ~df_raw.columns.str.contains('^Unnamed')].dropna(how='all', axis=1)
        
        # Si los encabezados reales están en una fila inferior, buscarlos
        if 'Categoría' not in df_raw.columns and 'Categoria' not in df_raw.columns:
            header_idx = None
            for idx, row in df_raw.iterrows():
                row_str = row.astype(str).str.lower()
                if row_str.str.contains('categoría|categoria', case=False).any():
                    header_idx = idx
                    break
            
            if header_idx is not None:
                headers = df_raw.iloc[header_idx].values
                df = df_raw.iloc[header_idx + 1:].copy()
                df.columns = [str(h).strip() for h in headers]
            else:
                df = df_raw.copy()
        else:
            df = df_raw.copy()

        # Normalizar nombres de columnas
        df.columns = [str(c).strip() for c in df.columns]

        # Identificar columnas principales
        col_cat = [c for c in df.columns if 'categor' in c.lower()]
        col_monto = [c for c in df.columns if 'monto' in c.lower()]

        if col_cat and col_monto:
            name_cat = col_cat[0]
            name_monto = col_monto[0]

            df = df.dropna(subset=[name_cat, name_monto]).copy()
            df = df.rename(columns={name_cat: 'Categoría', name_monto: 'Monto ($)'})

            # Limpiar y convertir montos a números
            df['Monto ($)'] = (
                df['Monto ($)']
                .astype(str)
                .str.replace('$', '', regex=False)
                .str.replace(',', '', regex=False)
                .str.strip()
            )
            df['Monto ($)'] = pd.to_numeric(df['Monto ($)'], errors='coerce').fillna(0)

            # Formatear la fecha
            col_fecha = [c for c in df.columns if 'fecha' in c.lower()]
            if col_fecha:
                df['Fecha'] = pd.to_datetime(df[col_fecha[0]], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')

            return df
        else:
            return pd.DataFrame()

    except Exception as e:
        st.error(f"Error procesando la información de la nube: {e}")
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

    # -----------------------------------------------------------------------------
    # 2. METRICAS PRINCIPALES (KPIs)
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
    # 3. VISUALIZACIÓN GRÁFICA DIDÁCTICA
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
        col_metodo = [c for c in df.columns if 'metodo' in c.lower() or 'pago' in c.lower()]
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
    # 4. SEMÁFORO PRESUPUESTAL DE CONTROL DE LÍMITES
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
    # 5. HISTORIAL Y TABLA DE MOVIMIENTOS
    # -----------------------------------------------------------------------------
    st.subheader("📝 Historial Completo de Movimientos")
    st.dataframe(df, use_container_width=True, hide_index=True)

else:
    st.info("💡 Asegúrate de que el archivo en Google Sheets esté compartido con acceso 'Cualquier persona con el enlace puede ver'.")
