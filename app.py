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

# Estilo visual limpio y profesional
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
    .card-tc {
        background-color: #FFF3E0;
        border-left: 5px solid #FF9800;
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
        
        # Si la cabecera no está en la fila 0, buscarla dinámicamente
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
        st.error(f"Error cargando los datos desde Google Drive: {e}")
        return pd.DataFrame()

df = cargar_datos()

if not df.empty:
    # Identificar columnas opcionales / flexibles
    col_metodo = [c for c in df.columns if 'metodo' in c.lower() or 'pago' in c.lower()][0]
    col_estado = [c for c in df.columns if 'estado' in c.lower()][0]
    
    # Detectar columna Banco / Entidad
    col_banco_list = [c for c in df.columns if 'banco' in c.lower() or 'entidad' in c.lower() or 'franquicia' in c.lower()]
    col_banco = col_banco_list[0] if col_banco_list else None

    # Separación general entre Ingresos y Gastos
    es_ingreso = df['Categoría'].str.contains('QUIN|Ingreso|Sueldo', case=False, na=False)
    df_ingresos = df[es_ingreso]
    df_gastos = df[~es_ingreso]

    total_ingresos = df_ingresos['Monto ($)'].sum()
    total_gastos = df_gastos['Monto ($)'].sum()
    balance = total_ingresos - total_gastos

    # -----------------------------------------------------------------------------
    # 2. INDICADORES CLAVE GENERALES (KPIs)
    # -----------------------------------------------------------------------------
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💰 Total Ingresos", f"${total_ingresos:,.0f} COP")
    k2.metric("💸 Total Gastos Registrados", f"${total_gastos:,.0f} COP")
    
    color_balance = "normal" if balance >= 0 else "inverse"
    k3.metric("📈 Balance Disponible", f"${balance:,.0f} COP", 
              delta=f"{(balance/total_ingresos)*100:.1f}% del ingreso" if total_ingresos > 0 else "0%",
              delta_color=color_balance)

    # Filtrar compras a crédito
    mask_tc_credito = (
        df[col_metodo].str.contains('Tarjeta credito|Credito', case=False, na=False) & 
        df[col_estado].str.contains('Credito', case=False, na=False)
    )
    df_tc_pendiente = df[mask_tc_credito]
    total_tc_pendiente = df_tc_pendiente['Monto ($)'].sum()

    porcentaje_tc_quincena = (total_tc_pendiente / total_ingresos * 100) if total_ingresos > 0 else 0
    k4.metric("💳 Deuda TC Próxima Quincena", f"${total_tc_pendiente:,.0f} COP", 
              delta=f"{porcentaje_tc_quincena:.1f}% de la quincena", delta_color="inverse")

    st.markdown("---")

    # -----------------------------------------------------------------------------
    # 3. MÓDULO DE SEGMENTACIÓN POR BANCO Y TARJETA DE CRÉDITO
    # -----------------------------------------------------------------------------
    st.subheader("💳 Segmentación de Tarjetas de Crédito por Banco / Entidad")
    st.markdown("Analiza exactamente **a qué entidad financiera** pertenece cada consumo en estado **'Crédito'** a pagar en la próxima quincena.")

    tc_col1, tc_col2 = st.columns([1, 2])

    with tc_col1:
        st.markdown(f"""
        <div class="card-tc">
            <h3 style="margin:0; color:#E65100;">🏛️ Total Deuda Tarjetas</h3>
            <h2 style="margin:5px 0; color:#B71C1C;">${total_tc_pendiente:,.0f} COP</h2>
            <p style="margin:0; font-size:0.9em; color:#5D4037;">
                <b>Total de consumos a liquidar:</b> {len(df_tc_pendiente)}<br>
                <b>Impacto sobre la quincena:</b> {porcentaje_tc_quincena:.1f}%
            </p>
        </div>
        """, unsafe_allow_html=True)

    with tc_col2:
        if not df_tc_pendiente.empty:
            # Si existe la columna Banco / Entidad, agrupar por Banco
            if col_banco:
                st.markdown("##### 🏦 Distribución de Deuda por Banco / Entidad")
                banco_summary = df_tc_pendiente.groupby(col_banco)['Monto ($)'].sum().reset_index()
                fig_banco = px.bar(
                    banco_summary, x=col_banco, y='Monto ($)', text_auto=',.0f',
                    color=col_banco, color_discrete_sequence=px.colors.qualitative.Dark2
                )
                fig_banco.update_layout(showlegend=False, xaxis_title="", yaxis_title="Monto ($ COP)", height=260)
                st.plotly_chart(fig_banco, use_container_width=True)
            else:
                st.markdown("##### 📊 Distribución del Crédito Pendiente por Categoría")
                cat_tc = df_tc_pendiente.groupby('Categoría')['Monto ($)'].sum().reset_index()
                fig_tc = px.bar(
                    cat_tc, x='Categoría', y='Monto ($)', text_auto=',.0f',
                    color='Categoría', color_discrete_sequence=px.colors.qualitative.Oranges
                )
                fig_tc.update_layout(showlegend=False, xaxis_title="", yaxis_title="Monto ($ COP)", height=260)
                st.plotly_chart(fig_tc, use_container_width=True)
                st.info("💡 **Consejo:** Agrega la columna `'Banco / Entidad'` a tu hoja de Google Sheets para ver el desglose por Banco aquí.")
        else:
            st.success("🎉 ¡Excelente! No tienes consumos pendientes en estado 'Crédito' para la próxima quincena.")

    # Mostrar la tabla de detalles con la columna del Banco
    if not df_tc_pendiente.empty:
        st.markdown("##### 📝 Detalle de Compras Diferidas por Banco")
        cols_mostrar = ['Fecha', 'Categoría', 'Descripción']
        if col_banco:
            cols_mostrar.append(col_banco)
        cols_mostrar.extend([col_metodo, col_estado, 'Monto ($)'])
        
        st.dataframe(
            df_tc_pendiente[cols_mostrar], 
            use_container_width=True, 
            hide_index=True
        )

    st.markdown("---")

    # -----------------------------------------------------------------------------
    # 4. GRÁFICOS GENERALES DEL FLUJO DE DINERO
    # -----------------------------------------------------------------------------
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🍩 Distribución Global de Gastos")
        cat_summary = df_gastos.groupby('Categoría')['Monto ($)'].sum().reset_index()
        cat_summary = cat_summary.sort_values(by='Monto ($)', ascending=False)
        
        fig_donut = px.pie(
            cat_summary, values='Monto ($)', names='Categoría', hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        fig_donut.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_donut, use_container_width=True)

    with col2:
        st.subheader("💳 Gastos por Método de Pago")
        pay_summary = df_gastos.groupby(col_metodo)['Monto ($)'].sum().reset_index()
        fig_bar = px.bar(
            pay_summary, x=col_metodo, y='Monto ($)', color=col_metodo,
            text_auto=',.0f', color_discrete_sequence=px.colors.qualitative.Safe
        )
        fig_bar.update_layout(showlegend=False, xaxis_title="", yaxis_title="Monto ($ COP)")
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # -----------------------------------------------------------------------------
    # 5. HISTORIAL Y TABLA COMPLETA CON FILTROS
    # -----------------------------------------------------------------------------
    st.subheader("📝 Historial General de Movimientos")
    st.dataframe(df, use_container_width=True, hide_index=True)

else:
    st.error("No se detectaron registros. Verifica que la hoja en Google Drive contenga la información.")
