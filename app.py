import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DEL APLICATIVO WEB Multi-Pestaña
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Control Financiero Personal | Multi-Tab",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo profesional moderno
st.markdown("""
    <style>
    .main { background-color: #F8F9FA; }
    .stMetric {
        background-color: #FFFFFF;
        padding: 16px;
        border-radius: 12px;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.05);
        border-top: 4px solid #1E88E5;
    }
    .card-fijos {
        background-color: #E3F2FD;
        border-left: 5px solid #1976D2;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
    }
    .card-imprevistos {
        background-color: #FFEBEE;
        border-left: 5px solid #D32F2F;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Control & Dashboard Financiero Personal")
st.caption("Sincronizado automáticamente en tiempo real con Google Drive")
st.markdown("---")

SHEET_ID = "1izhKwlt6UnFHF9UFjq5aU6QEpVwVV8xgr-kOz3678Rg"
URL_GVIZ = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=5) # Refresca datos automáticamente cada 5 segundos
def cargar_datos():
    try:
        df_raw = pd.read_csv(URL_GVIZ)
        df_raw = df_raw.loc[:, ~df_raw.columns.str.contains('^Unnamed')].dropna(how='all', axis=1)
        
        # Detectar cabecera real
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

        df.columns = [str(c).strip() for c in df.columns]

        col_cat = [c for c in df.columns if 'categor' in c.lower()]
        col_monto = [c for c in df.columns if 'monto' in c.lower()]

        if col_cat and col_monto:
            name_cat = col_cat[0]
            name_monto = col_monto[0]

            df = df.dropna(subset=[name_cat, name_monto]).copy()
            df = df.rename(columns={name_cat: 'Categoría', name_monto: 'Monto ($)'})

            df['Monto ($)'] = (
                df['Monto ($)']
                .astype(str)
                .str.replace('$', '', regex=False)
                .str.replace(',', '', regex=False)
                .str.strip()
            )
            df['Monto ($)'] = pd.to_numeric(df['Monto ($)'], errors='coerce').fillna(0)

            col_fecha = [c for c in df.columns if 'fecha' in c.lower()]
            if col_fecha:
                df['Fecha'] = pd.to_datetime(df[col_fecha[0]], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')

            return df
        else:
            return pd.DataFrame()

    except Exception as e:
        st.error(f"Error de conexión con Google Drive: {e}")
        return pd.DataFrame()

df = cargar_datos()

if not df.empty:
    col_metodo = [c for c in df.columns if 'metodo' in c.lower() or 'pago' in c.lower()][0]
    col_estado = [c for c in df.columns if 'estado' in c.lower()][0]
    col_banco_list = [c for c in df.columns if 'banco' in c.lower() or 'entidad' in c.lower()]
    col_banco = col_banco_list[0] if col_banco_list else None

    # Clasificación General
    es_ingreso = df['Categoría'].str.contains('QUIN|Ingreso|Sueldo', case=False, na=False)
    df_ingresos = df[es_ingreso]
    df_gastos = df[~es_ingreso]

    total_ingresos = df_ingresos['Monto ($)'].sum()
    total_gastos = df_gastos['Monto ($)'].sum()
    balance = total_ingresos - total_gastos

    # CREACIÓN DE PESTAÑAS
    tab1, tab2, tab3 = st.tabs([
        "📌 Resumen General & Dashboard", 
        "🏠 Detalle de Gastos Fijos (Hogar)", 
        "🚨 Sondeo de Imprevistos & Fugas"
    ])

    # =========================================================================
    # PESTAÑA 1: RESUMEN GENERAL
    # =========================================================================
    with tab1:
        st.subheader("📌 Resumen General del Flujo de Dinero")
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("💰 Total Ingresos", f"${total_ingresos:,.0f} COP")
        k2.metric("💸 Total Gastos Registrados", f"${total_gastos:,.0f} COP")
        
        color_balance = "normal" if balance >= 0 else "inverse"
        k3.metric("📈 Balance Disponible", f"${balance:,.0f} COP", 
                  delta=f"{(balance/total_ingresos)*100:.1f}% del ingreso" if total_ingresos > 0 else "0%",
                  delta_color=color_balance)

        mask_tc_credito = (
            df[col_metodo].str.contains('Tarjeta credito|Credito', case=False, na=False) & 
            df[col_estado].str.contains('Credito', case=False, na=False)
        )
        df_tc_pendiente = df[mask_tc_credito]
        total_tc_pendiente = df_tc_pendiente['Monto ($)'].sum()
        k4.metric("💳 Deuda TC Próxima Quincena", f"${total_tc_pendiente:,.0f} COP", 
                  delta=f"{(total_tc_pendiente/total_ingresos)*100:.1f}% de la quincena" if total_ingresos > 0 else "0%", delta_color="inverse")

        st.markdown("---")

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("🍩 Distribución Global por Categoría")
            cat_sum = df_gastos.groupby('Categoría')['Monto ($)'].sum().reset_index().sort_values(by='Monto ($)', ascending=False)
            fig_pie = px.pie(cat_sum, values='Monto ($)', names='Categoría', hole=0.45, color_discrete_sequence=px.colors.qualitative.Prism)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_g2:
            st.subheader("💳 Gastos por Método de Pago")
            pay_sum = df_gastos.groupby(col_metodo)['Monto ($)'].sum().reset_index()
            fig_bar = px.bar(pay_sum, x=col_metodo, y='Monto ($)', color=col_metodo, text_auto=',.0f', color_discrete_sequence=px.colors.qualitative.Safe)
            fig_bar.update_layout(showlegend=False, xaxis_title="", yaxis_title="Monto ($ COP)")
            st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("---")
        st.subheader("📝 Historial General de Movimientos")
        st.dataframe(df, use_container_width=True, hide_index=True)

    # =========================================================================
    # PESTAÑA 2: DETALLE DE GASTOS FIJOS (SERVICIOS, ADMON, MERCADO)
    # =========================================================================
    with tab2:
        st.subheader("🏠 Análisis Detallado de Gastos Fijos (Piso Base Mensual)")
        st.markdown("En esta pestaña se audita el presupuesto mínimo obligatorio para operar el hogar: **Energía, Agua, Gas, Internet, Administración y Mercado**.")

        # Filtro de categorías fijas
        cats_fijas = [
            'Servicios - Energía', 'Servicios - Agua', 'Servicios - Gas', 
            'Servicios- Internet Hogar', 'Pago Administracion/parqueadero', 'Mercado'
        ]
        df_fijos = df_gastos[df_gastos['Categoría'].isin(cats_fijas)]
        total_fijos = df_fijos['Monto ($)'].sum()
        porcentaje_fijos = (total_fijos / total_ingresos * 100) if total_ingresos > 0 else 0

        f1, f2, f3 = st.columns(3)
        f1.metric("🏠 Total Gastos Fijos Hogar", f"${total_fijos:,.0f} COP")
        f2.metric("📊 % del Ingreso Quincenal", f"{porcentaje_fijos:.1f}%")
        f3.metric("📌 Promedio Estimado por Rubro", f"${(total_fijos/len(cats_fijas)):,.0f} COP")

        st.markdown("---")

        col_f1, col_f2 = st.columns([1, 1])

        with col_f1:
            st.markdown("##### 💡 Desglose por Servicio / Rubro Fijo")
            fijos_sum = df_fijos.groupby('Categoría')['Monto ($)'].sum().reset_index().sort_values(by='Monto ($)', ascending=False)
            fig_fijos = px.bar(
                fijos_sum, x='Categoría', y='Monto ($)', color='Categoría',
                text_auto=',.0f', color_discrete_sequence=px.colors.qualitative.Blues_r
            )
            fig_fijos.update_layout(showlegend=False, xaxis_title="", yaxis_title="COP ($)")
            st.plotly_chart(fig_fijos, use_container_width=True)

        with col_f2:
            st.markdown("""
            <div class="card-fijos">
                <h4 style="margin:0; color:#0D47A1;">📌 Cuadro Resumen de Facturación Fija</h4>
                <p style="margin:5px 0 0 0; color:#1565C0;">
                    Valores liquidados en el ciclo actual de servicios fijos e insumos.
                </p>
            </div>
            """, unsafe_allow_html=True)
            st.dataframe(fijos_sum, use_container_width=True, hide_index=True)

        st.markdown("##### 📝 Registros Específicos de Gastos Fijos")
        st.dataframe(df_fijos[['Fecha', 'Categoría', 'Descripción', col_metodo, col_estado, 'Monto ($)']], use_container_width=True, hide_index=True)

    # =========================================================================
    # PESTAÑA 3: SONDEO DE IMPREVISTOS Y FUGAS DE DINERO
    # =========================================================================
    with tab3:
        st.subheader("🚨 Sondeo de Imprevistos & Fugas de Dinero")
        st.markdown("Módulo de auditoría para identificar **transferencias de emergencia, compras fuera de programa y gastos imprevistos**.")

        df_imprevistos = df_gastos[df_gastos['Categoría'].str.contains('Imprevistos', case=False, na=False)]
        total_imprevistos = df_imprevistos['Monto ($)'].sum()
        porcentaje_imprevistos = (total_imprevistos / total_ingresos * 100) if total_ingresos > 0 else 0

        i1, i2, i3 = st.columns(3)
        i1.metric("🚨 Total Imprevistos Registrados", f"${total_imprevistos:,.0f} COP")
        i2.metric("📊 Impacto sobre Ingresos", f"{porcentaje_imprevistos:.1f}%")
        i3.metric("🔢 Número de Eventos", f"{len(df_imprevistos)} eventos")

        st.markdown("---")

        col_i1, col_i2 = st.columns([1, 1])

        with col_i1:
            st.markdown("##### 💸 Top Imprevistos / Fugas Registradas")
            if not df_imprevistos.empty:
                fig_imp = px.bar(
                    df_imprevistos, x='Descripción', y='Monto ($)', color='Descripción',
                    text_auto=',.0f', color_discrete_sequence=px.colors.qualitative.Reds_r
                )
                fig_imp.update_layout(showlegend=False, xaxis_title="", yaxis_title="COP ($)")
                st.plotly_chart(fig_imp, use_container_width=True)

        with col_i2:
            st.markdown("""
            <div class="card-imprevistos">
                <h4 style="margin:0; color:#B71C1C;">🛡️ Plan de Mitigación de Fugas</h4>
                <p style="margin:5px 0 0 0; color:#C62828;">
                    <b>Recomendación:</b> Para evitar que los imprevistos descompensen el presupuesto operativo del hogar, destina un <b>fondo de reserva del 5% al 10%</b> al inicio de cada quincena exclusivamente para este rubro.
                </p>
            </div>
            """, unsafe_allow_html=True)
            if not df_imprevistos.empty:
                st.dataframe(df_imprevistos[['Fecha', 'Descripción', col_metodo, 'Monto ($)']], use_container_width=True, hide_index=True)

else:
    st.error("No se encontraron registros. Verifica la información en tu Google Sheet.")
