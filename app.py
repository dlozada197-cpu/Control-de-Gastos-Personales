import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DEL APLICATIVO WEB
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Control Financiero Personal | Multi-Quincena",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    .card-deudas {
        background-color: #FFF3E0;
        border-left: 5px solid #FF9800;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
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
                df['Fecha_DT'] = pd.to_datetime(df[col_fecha[0]], dayfirst=True, errors='coerce')
                df['Fecha'] = df['Fecha_DT'].dt.strftime('%Y-%m-%d')
            else:
                df['Fecha_DT'] = pd.to_datetime('today')
                df['Fecha'] = df['Fecha_DT'].dt.strftime('%Y-%m-%d')

            # Asignación automática de Quincena por fecha
            def asignar_quincena(row):
                dt = row['Fecha_DT']
                if pd.isna(dt):
                    return "Sin Fecha"
                quin = "1ra Quincena" if dt.day <= 15 else "2da Quincena"
                mes_nombre = dt.strftime('%B %Y').capitalize()
                return f"{quin} ({mes_nombre})"

            df['Período Quincenal'] = df.apply(asignar_quincena, axis=1)

            return df
        else:
            return pd.DataFrame()

    except Exception as e:
        st.error(f"Error de conexión con Google Drive: {e}")
        return pd.DataFrame()

df_completo = cargar_datos()

if not df_completo.empty:
    col_metodo = [c for c in df_completo.columns if 'metodo' in c.lower() or 'pago' in c.lower()][0]
    col_estado = [c for c in df_completo.columns if 'estado' in c.lower()][0]
    col_banco_list = [c for c in df_completo.columns if 'banco' in c.lower() or 'entidad' in c.lower()]
    col_banco = col_banco_list[0] if col_banco_list else None

    # -------------------------------------------------------------------------
    # BARRA LATERAL: CONTROL DE PERIODO / AL DÍA
    # -------------------------------------------------------------------------
    st.sidebar.header("🗓️ Selector de Período (Al Día)")
    opciones_periodo = ["Todo el Historial (Acumulado)"] + sorted(list(df_completo['Período Quincenal'].dropna().unique()), reverse=True)
    
    periodo_seleccionado = st.sidebar.selectbox(
        "Ver finanzas de:",
        opciones_periodo,
        index=1 if len(opciones_periodo) > 1 else 0
    )

    if periodo_seleccionado != "Todo el Historial (Acumulado)":
        df = df_completo[df_completo['Período Quincenal'] == periodo_seleccionado].copy()
        st.info(f"📍 Mostrando datos específicos de: **{periodo_seleccionado}**")
    else:
        df = df_completo.copy()
        st.warning("⚠️ Mostrando **Todo el Historial Acumulado**. Para evaluar tu dinero al día, selecciona la quincena actual en el menú izquierdo.")

    # Clasificación de Ingresos y Gastos del Período
    es_ingreso = df['Categoría'].str.contains('QUIN|Ingreso|Sueldo', case=False, na=False)
    df_ingresos = df[es_ingreso]
    df_gastos = df[~es_ingreso]

    total_ingresos = df_ingresos['Monto ($)'].sum()
    total_gastos = df_gastos['Monto ($)'].sum()
    balance = total_ingresos - total_gastos

    # TABS MULTIPESTAÑA
    tab1, tab2, tab3, tab4 = st.tabs([
        "📌 Resumen General (Al Día)", 
        "💳 Deudas TC (Estado Crédito)", 
        "🏠 Gastos Fijos (Hogar)", 
        "🚨 Sondeo de Imprevistos"
    ])

    # =========================================================================
    # TAB 1: RESUMEN GENERAL AL DÍA
    # =========================================================================
    with tab1:
        st.subheader(f"📌 Estado Financiero: {periodo_seleccionado}")
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("💰 Ingresos del Período", f"${total_ingresos:,.0f} COP")
        k2.metric("💸 Gastos del Período", f"${total_gastos:,.0f} COP")
        
        color_balance = "normal" if balance >= 0 else "inverse"
        k3.metric("📈 Balance Disponible Real", f"${balance:,.0f} COP", 
                  delta=f"{(balance/total_ingresos)*100:.1f}% remanente" if total_ingresos > 0 else "0%",
                  delta_color=color_balance)

        mask_credito = df[col_estado].str.contains('Credito|Crédito', case=False, na=False)
        df_solo_credito = df[mask_credito]
        total_credito_pendiente = df_solo_credito['Monto ($)'].sum()
        k4.metric("💳 Pendiente Crédito", f"${total_credito_pendiente:,.0f} COP", 
                  delta=f"{len(df_solo_credito)} compras diferidas", delta_color="inverse")

        st.markdown("---")

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("🍩 Distribución de Gastos")
            if not df_gastos.empty:
                cat_sum = df_gastos.groupby('Categoría')['Monto ($)'].sum().reset_index().sort_values(by='Monto ($)', ascending=False)
                fig_pie = px.pie(cat_sum, values='Monto ($)', names='Categoría', hole=0.45, color_discrete_sequence=px.colors.qualitative.Prism)
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No hay gastos registrados en esta quincena aún.")

        with col_g2:
            st.subheader("💳 Salidas por Método de Pago")
            if not df_gastos.empty:
                pay_sum = df_gastos.groupby(col_metodo)['Monto ($)'].sum().reset_index()
                fig_bar = px.bar(pay_sum, x=col_metodo, y='Monto ($)', color=col_metodo, text_auto=',.0f', color_discrete_sequence=px.colors.qualitative.Safe)
                fig_bar.update_layout(showlegend=False, xaxis_title="", yaxis_title="Monto ($ COP)")
                st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("---")
        st.subheader("📝 Registros del Período")
        st.dataframe(df[['Fecha', 'Categoría', 'Descripción', col_metodo, col_estado, 'Monto ($)']], use_container_width=True, hide_index=True)

    # =========================================================================
    # TAB 2: AUDITORÍA DE DEUDAS
    # =========================================================================
    with tab2:
        st.subheader("💳 Deudas Pendientes de Liquidar (Estado Crédito)")
        d1, d2, d3 = st.columns(3)
        d1.metric("🏛️ Total Deuda Pendiente", f"${total_credito_pendiente:,.0f} COP")
        d2.metric("🔢 Compras Activas", f"{len(df_solo_credito)} compras")
        d3.metric("📊 Peso sobre Quincena", f"{(total_credito_pendiente/total_ingresos*100):.1f}%" if total_ingresos > 0 else "0%")

        st.markdown("---")
        if not df_solo_credito.empty:
            col_d1, col_d2 = st.columns([1, 1])
            with col_d1:
                deuda_cat = df_solo_credito.groupby('Categoría')['Monto ($)'].sum().reset_index().sort_values(by='Monto ($)', ascending=False)
                fig_deuda_cat = px.bar(
                    deuda_cat, x='Categoría', y='Monto ($)', color='Categoría',
                    text_auto=',.0f', color_discrete_sequence=px.colors.sequential.Oranges_r
                )
                fig_deuda_cat.update_layout(showlegend=False, xaxis_title="", yaxis_title="Monto ($ COP)")
                st.plotly_chart(fig_deuda_cat, use_container_width=True)

            with col_d2:
                st.markdown(f"""
                <div class="card-deudas">
                    <h4 style="margin:0; color:#E65100;">📌 Resumen de Deuda a Liquidar</h4>
                    <p style="margin:5px 0 0 0; color:#BF360C;">
                        Compras diferidas pendientes por pagar con esta quincena: <b>${total_credito_pendiente:,.0f} COP</b>.
                    </p>
                </div>
                """, unsafe_allow_html=True)
                if col_banco:
                    st.dataframe(df_solo_credito.groupby(col_banco)['Monto ($)'].sum().reset_index(), use_container_width=True, hide_index=True)

            st.dataframe(df_solo_credito[['Fecha', 'Categoría', 'Descripción', col_metodo, col_estado, 'Monto ($)']], use_container_width=True, hide_index=True)
        else:
            st.success("🎉 No tienes consumos pendientes en estado 'Crédito' en este período.")

    # =========================================================================
    # TAB 3: GASTOS FIJOS
    # =========================================================================
    with tab3:
        st.subheader("🏠 Gastos Fijos Obligatorios (Hogar)")
        cats_fijas = [
            'Servicios - Energía', 'Servicios - Agua', 'Servicios - Gas', 
            'Servicios- Internet Hogar', 'Pago Administracion/parqueadero', 'Mercado'
        ]
        df_fijos = df_gastos[df_gastos['Categoría'].isin(cats_fijas)]
        total_fijos = df_fijos['Monto ($)'].sum()

        f1, f2, f3 = st.columns(3)
        f1.metric("🏠 Total Gastos Fijos", f"${total_fijos:,.0f} COP")
        f2.metric("📊 % del Ingreso", f"{(total_fijos/total_ingresos*100):.1f}%" if total_ingresos > 0 else "0%")
        f3.metric("📌 Rubros Activos", f"{len(df_fijos)} pagos")

        st.markdown("---")
        if not df_fijos.empty:
            fijos_sum = df_fijos.groupby('Categoría')['Monto ($)'].sum().reset_index().sort_values(by='Monto ($)', ascending=False)
            fig_fijos = px.bar(fijos_sum, x='Categoría', y='Monto ($)', color='Categoría', text_auto=',.0f', color_discrete_sequence=px.colors.sequential.Blues_r)
            fig_fijos.update_layout(showlegend=False, xaxis_title="", yaxis_title="Monto ($ COP)")
            st.plotly_chart(fig_fijos, use_container_width=True)
            st.dataframe(df_fijos[['Fecha', 'Categoría', 'Descripción', col_metodo, col_estado, 'Monto ($)']], use_container_width=True, hide_index=True)
        else:
            st.info("No se han registrado pagos de servicios fijos en este período.")

    # =========================================================================
    # TAB 4: IMPREVISTOS
    # =========================================================================
    with tab4:
        st.subheader("🚨 Sondeo de Imprevistos & Fugas")
        df_imprevistos = df_gastos[df_gastos['Categoría'].str.contains('Imprevistos', case=False, na=False)]
        total_imprevistos = df_imprevistos['Monto ($)'].sum()

        i1, i2, i3 = st.columns(3)
        i1.metric("🚨 Total Imprevistos", f"${total_imprevistos:,.0f} COP")
        i2.metric("📊 Impacto en Ingreso", f"{(total_imprevistos/total_ingresos*100):.1f}%" if total_ingresos > 0 else "0%")
        i3.metric("🔢 Eventos", f"{len(df_imprevistos)} eventos")

        st.markdown("---")
        if not df_imprevistos.empty:
            fig_imp = px.bar(df_imprevistos, x='Descripción', y='Monto ($)', color='Descripción', text_auto=',.0f', color_discrete_sequence=px.colors.sequential.Reds_r)
            fig_imp.update_layout(showlegend=False, xaxis_title="", yaxis_title="Monto ($ COP)")
            st.plotly_chart(fig_imp, use_container_width=True)
            st.dataframe(df_imprevistos[['Fecha', 'Descripción', col_metodo, 'Monto ($)']], use_container_width=True, hide_index=True)
        else:
            st.success("🎉 Sin imprevistos en este período.")

else:
    st.error("No se encontraron datos en la hoja de Google Sheets.")
