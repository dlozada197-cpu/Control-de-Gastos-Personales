import streamlit as st
import pandas as pd
import plotly.express as px
import time

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DEL APLICATIVO WEB
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Control Financiero Personal | Pro Dashboard",
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
    .card-cuenta {
        background-color: #E8F5E9;
        border-left: 5px solid #2E7D32;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
    }
    .card-deudas {
        background-color: #FFF3E0;
        border-left: 5px solid #FF9800;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
    }
    .card-historico {
        background-color: #E3F2FD;
        border-left: 5px solid #1565C0;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# Encabezado con Botón de Actualización Directa
col_title, col_btn = st.columns([4, 1])
with col_title:
    st.title("📊 Control & Inteligencia Financiera Personal")
    st.caption("Sincronización directa con Google Drive | Análisis Quincenal, Mensual y Anual")
with col_btn:
    st.write("")
    if st.button("🔄 Actualizar Información", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.session_state["last_refresh"] = time.time()
        st.toast("¡Datos actualizados desde Google Drive!", icon="✅")
        st.rerun()

st.markdown("---")

SHEET_ID = "1izhKwlt6UnFHF9UFjq5aU6QEpVwVV8xgr-kOz3678Rg"

MESES_ES = {
    1: '01. Enero', 2: '02. Febrero', 3: '03. Marzo', 4: '04. Abril',
    5: '05. Mayo', 6: '06. Junio', 7: '07. Julio', 8: '08. Agosto',
    9: '09. Septiembre', 10: '10. Octubre', 11: '11. Noviembre', 12: '12. Diciembre'
}

MESES_CORTOS = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

@st.cache_data(ttl=15)
def cargar_datos(refresh_token=0):
    try:
        # Cache-busting URL para forzar a Google Sheets a entregar el último cambio guardado
        url_gviz = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&t={int(time.time())}"
        df_raw = pd.read_csv(url_gviz)
        df_raw = df_raw.loc[:, ~df_raw.columns.str.contains('^Unnamed')].dropna(how='all', axis=1)
        
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

            # Columnas de Tiempo para Análisis Mensual y Anual
            df['Año'] = df['Fecha_DT'].dt.year.fillna(2026).astype(int)
            df['Mes_Num'] = df['Fecha_DT'].dt.month.fillna(1).astype(int)
            df['Mes_Nombre'] = df['Mes_Num'].map(MESES_ES)
            df['Periodo_Mes'] = df['Fecha_DT'].dt.strftime('%Y-%m')

            # Asignación de Ciclos Reales de Nómina
            def asignar_ciclo(row):
                dt = row['Fecha_DT']
                if pd.isna(dt):
                    return "Sin Fecha"
                if dt.day >= 15 and dt.day < 30:
                    return f"1ra Quincena {MESES_CORTOS[dt.month]} {dt.year} (Ciclo 15 al 29)"
                elif dt.day >= 30:
                    return f"2da Quincena {MESES_CORTOS[dt.month]} {dt.year} (Ciclo 30 {MESES_CORTOS[dt.month][:3]} al 14 prox)"
                else:
                    prev_m = dt.month - 1 if dt.month > 1 else 12
                    prev_y = dt.year if dt.month > 1 else dt.year - 1
                    return f"2da Quincena {MESES_CORTOS[prev_m]} {prev_y} (Ciclo 30 {MESES_CORTOS[prev_m][:3]} al 14 prox)"

            df['Ciclo de Pago'] = df.apply(asignar_ciclo, axis=1)

            return df
        else:
            return pd.DataFrame()

    except Exception as e:
        st.error(f"Error de conexión con Google Drive: {e}")
        return pd.DataFrame()

if "last_refresh" not in st.session_state:
    st.session_state["last_refresh"] = 0

df_completo = cargar_datos(st.session_state["last_refresh"])

if not df_completo.empty:
    col_metodo = [c for c in df_completo.columns if 'metodo' in c.lower() or 'pago' in c.lower()][0]
    col_estado = [c for c in df_completo.columns if 'estado' in c.lower()][0]
    col_banco_list = [c for c in df_completo.columns if 'banco' in c.lower() or 'entidad' in c.lower()]
    col_banco = col_banco_list[0] if col_banco_list else None

    # -------------------------------------------------------------------------
    # BARRA LATERAL: BOTÓN DE ACTUALIZAR Y SELECTOR DE QUINCENA
    # -------------------------------------------------------------------------
    st.sidebar.header("⚡ Acciones Rápidas")
    if st.sidebar.button("🔄 Actualizar Datos Ahora", use_container_width=True):
        st.cache_data.clear()
        st.session_state["last_refresh"] = time.time()
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.header("🗓️ Filtro de Ciclo Quincenal")
    ciclos_disponibles = sorted(list(df_completo['Ciclo de Pago'].dropna().unique()), reverse=True)
    opciones_periodo = ["Todo el Historial (Acumulado)"] + ciclos_disponibles
    
    periodo_seleccionado = st.sidebar.selectbox(
        "Selecciona la quincena a auditar:",
        opciones_periodo,
        index=1 if len(opciones_periodo) > 1 else 0
    )

    if periodo_seleccionado != "Todo el Historial (Acumulado)":
        df = df_completo[df_completo['Ciclo de Pago'] == periodo_seleccionado].copy()
        st.info(f"📍 Audición activa: **{periodo_seleccionado}**")
    else:
        df = df_completo.copy()
        st.warning("⚠️ Viendo **Todo el Historial Acumulado**.")

    # -------------------------------------------------------------------------
    # SEPARACIÓN CONTABLE ESTRICTA (CUENTA BANCARIA VS DEUDA TC)
    # -------------------------------------------------------------------------
    es_ingreso = df['Categoría'].str.contains('QUIN|Ingreso|Sueldo', case=False, na=False)
    df_ingresos = df[es_ingreso]
    total_ingresos = df_ingresos['Monto ($)'].sum()

    df_gastos_todos = df[~es_ingreso]

    # Pagos efectivos que ya salieron de la cuenta
    df_pagados_reales = df_gastos_todos[df_gastos_todos[col_estado].str.contains('Pagado', case=False, na=False)]
    total_pagado_efectivo = df_pagados_reales['Monto ($)'].sum()

    # Deuda en Tarjeta de Crédito (Estado: Crédito)
    df_credito_tc = df_gastos_todos[df_gastos_todos[col_estado].str.contains('Credito|Crédito', case=False, na=False)]
    total_deuda_tc = df_credito_tc['Monto ($)'].sum()

    saldo_real_cuenta = total_ingresos - total_pagado_efectivo
    balance_libre_proyectado = saldo_real_cuenta - total_deuda_tc

    # 5 PESTAÑAS ESPECIALIZADAS
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📌 Resumen Quincenal", 
        "💳 Deudas TC (Crédito)", 
        "🏠 Gastos Fijos (Hogar)", 
        "🚨 Sondeo de Imprevistos",
        "📈 Histórico Mensual & Anual"
    ])

    # =========================================================================
    # TAB 1: RESUMEN GENERAL AL DÍA
    # =========================================================================
    with tab1:
        st.subheader(f"📌 Flujo de Caja Real: {periodo_seleccionado}")
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("💰 Ingresos del Ciclo", f"${total_ingresos:,.0f} COP")
        k2.metric("💸 Pagos Realizados (Efectivos)", f"${total_pagado_efectivo:,.0f} COP")
        
        color_saldo = "normal" if saldo_real_cuenta >= 0 else "inverse"
        k3.metric("🏦 Saldo Real en Cuenta Hoy", f"${saldo_real_cuenta:,.0f} COP", 
                  delta=f"{(saldo_real_cuenta/total_ingresos)*100:.1f}% disponible" if total_ingresos > 0 else "0%",
                  delta_color=color_saldo)

        k4.metric("💳 Deuda en Tarjeta (Pendiente)", f"${total_deuda_tc:,.0f} COP", 
                  delta=f"{len(df_credito_tc)} compras a crédito", delta_color="inverse")

        st.markdown(f"""
        <div class="card-cuenta">
            <h4 style="margin:0; color:#1B5E20;">💵 Balance Libre después de Tarjetas: ${balance_libre_proyectado:,.0f} COP</h4>
            <p style="margin:5px 0 0 0; color:#2E7D32;">
                En tu cuenta bancaria tienes <b>${saldo_real_cuenta:,.0f} COP</b> disponibles hoy. 
                Apartando los <b>${total_deuda_tc:,.0f} COP</b> de compras con tarjeta de crédito, te quedan libres <b>${balance_libre_proyectado:,.0f} COP</b>.
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("🍩 Distribución de Pagos Efectivos")
            if not df_pagados_reales.empty:
                cat_sum = df_pagados_reales.groupby('Categoría')['Monto ($)'].sum().reset_index().sort_values(by='Monto ($)', ascending=False)
                fig_pie = px.pie(cat_sum, values='Monto ($)', names='Categoría', hole=0.45, color_discrete_sequence=px.colors.qualitative.Prism)
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)

        with col_g2:
            st.subheader("💳 Salidas por Método de Pago")
            if not df_pagados_reales.empty:
                pay_sum = df_pagados_reales.groupby(col_metodo)['Monto ($)'].sum().reset_index()
                fig_bar = px.bar(pay_sum, x=col_metodo, y='Monto ($)', color=col_metodo, text_auto=',.0f', color_discrete_sequence=px.colors.qualitative.Safe)
                fig_bar.update_layout(showlegend=False, xaxis_title="", yaxis_title="Monto ($ COP)")
                st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("---")
        st.subheader("📝 Movimientos del Ciclo Seleccionado")
        st.dataframe(df[['Fecha', 'Categoría', 'Descripción', col_metodo, col_estado, 'Monto ($)']], use_container_width=True, hide_index=True)

    # =========================================================================
    # TAB 2: AUDITORÍA DE DEUDAS EN ESTADO CRÉDITO
    # =========================================================================
    with tab2:
        st.subheader("💳 Compras en Estado 'Crédito' por Pagar")
        d1, d2, d3 = st.columns(3)
        d1.metric("🏛️ Total Deuda en Tarjeta", f"${total_deuda_tc:,.0f} COP")
        d2.metric("🔢 Cantidad de Deudas", f"{len(df_credito_tc)} obligaciones")
        d3.metric("📊 Compromiso del Saldo Real", f"{(total_deuda_tc/saldo_real_cuenta*100):.1f}%" if saldo_real_cuenta > 0 else "0%")

        st.markdown("---")
        if not df_credito_tc.empty:
            col_d1, col_d2 = st.columns([1, 1])
            with col_d1:
                deuda_cat = df_credito_tc.groupby('Categoría')['Monto ($)'].sum().reset_index().sort_values(by='Monto ($)', ascending=False)
                fig_deuda_cat = px.bar(deuda_cat, x='Categoría', y='Monto ($)', color='Categoría', text_auto=',.0f', color_discrete_sequence=px.colors.sequential.Oranges_r)
                fig_deuda_cat.update_layout(showlegend=False, xaxis_title="", yaxis_title="Monto ($ COP)")
                st.plotly_chart(fig_deuda_cat, use_container_width=True)

            with col_d2:
                if col_banco:
                    st.markdown("##### 🏦 Deuda Agrupada por Banco / Entidad")
                    st.dataframe(df_credito_tc.groupby(col_banco)['Monto ($)'].sum().reset_index(), use_container_width=True, hide_index=True)
                st.dataframe(df_credito_tc[['Fecha', 'Categoría', 'Descripción', col_metodo, col_estado, 'Monto ($)']], use_container_width=True, hide_index=True)
        else:
            st.success("🎉 ¡Excelente! No tienes compras pendientes en estado 'Crédito' en este ciclo.")

    # =========================================================================
    # TAB 3: GASTOS FIJOS DEL CICLO
    # =========================================================================
    with tab3:
        st.subheader("🏠 Gastos Fijos del Hogar en este Ciclo")
        cats_fijas = [
            'Servicios - Energía', 'Servicios - Agua', 'Servicios - Gas', 
            'Servicios- Internet Hogar', 'Servicios - Internet Movil',
            'Pago Administracion/parqueadero', 'Mercado'
        ]
        df_fijos = df_pagados_reales[df_pagados_reales['Categoría'].isin(cats_fijas)]
        total_fijos = df_fijos['Monto ($)'].sum()

        f1, f2, f3 = st.columns(3)
        f1.metric("🏠 Total Gastos Fijos Pagados", f"${total_fijos:,.0f} COP")
        f2.metric("📊 % de los Ingresos", f"{(total_fijos/total_ingresos*100):.1f}%" if total_ingresos > 0 else "0%")
        f3.metric("📌 Recibos Pagados", f"{len(df_fijos)} pagos")

        st.markdown("---")
        if not df_fijos.empty:
            fijos_sum = df_fijos.groupby('Categoría')['Monto ($)'].sum().reset_index().sort_values(by='Monto ($)', ascending=False)
            fig_fijos = px.bar(fijos_sum, x='Categoría', y='Monto ($)', color='Categoría', text_auto=',.0f', color_discrete_sequence=px.colors.sequential.Blues_r)
            fig_fijos.update_layout(showlegend=False, xaxis_title="", yaxis_title="Monto ($ COP)")
            st.plotly_chart(fig_fijos, use_container_width=True)
            st.dataframe(df_fijos[['Fecha', 'Categoría', 'Descripción', col_metodo, 'Monto ($)']], use_container_width=True, hide_index=True)

    # =========================================================================
    # TAB 4: IMPREVISTOS
    # =========================================================================
    with tab4:
        st.subheader("🚨 Sondeo de Imprevistos & Fugas")
        df_imprevistos = df_gastos_todos[df_gastos_todos['Categoría'].str.contains('Imprevistos', case=False, na=False)]
        total_imprevistos = df_imprevistos['Monto ($)'].sum()

        i1, i2, i3 = st.columns(3)
        i1.metric("🚨 Total Imprevistos (Pagados + TC)", f"${total_imprevistos:,.0f} COP")
        i2.metric("📊 Impacto en Ingreso", f"{(total_imprevistos/total_ingresos*100):.1f}%" if total_ingresos > 0 else "0%")
        i3.metric("🔢 Eventos", f"{len(df_imprevistos)} eventos")

        st.markdown("---")
        if not df_imprevistos.empty:
            fig_imp = px.bar(df_imprevistos, x='Descripción', y='Monto ($)', color=col_estado, text_auto=',.0f')
            st.plotly_chart(fig_imp, use_container_width=True)
            st.dataframe(df_imprevistos[['Fecha', 'Descripción', col_metodo, col_estado, 'Monto ($)']], use_container_width=True, hide_index=True)

    # =========================================================================
    # TAB 5: HISTÓRICO MENSUAL & ANUAL (SERVICIOS Y MESES MÁS COSTOSOS)
    # =========================================================================
    with tab5:
        st.subheader("📈 Inteligencia Anual: Comportamiento Mensual y Histórico de Servicios")
        st.markdown("Esta pestaña analiza **toda tu base de datos anual** (sin importar qué quincena tengas seleccionada a la izquierda) para mostrarte **qué meses son más costosos, cuáles son más económicos y cómo evolucionan tus facturas mes a mes**.")

        # Usamos df_completo para ver todo el año
        es_ing_hist = df_completo['Categoría'].str.contains('QUIN|Ingreso|Sueldo', case=False, na=False)
        df_gastos_hist = df_completo[~es_ing_hist].copy()

        # Agrupación por Mes para hallar el mes más costoso y el más bajo
        gastos_por_mes = df_gastos_hist.groupby('Mes_Nombre')['Monto ($)'].sum().reset_index().sort_values(by='Mes_Nombre')
        
        if not gastos_por_mes.empty:
            mes_mas_caro = gastos_por_mes.loc[gastos_por_mes['Monto ($)'].idxmax()]
            mes_mas_bajo = gastos_por_mes.loc[gastos_por_mes['Monto ($)'].idxmin()]
            promedio_mensual = gastos_por_mes['Monto ($)'].mean()
            total_anual = gastos_por_mes['Monto ($)'].sum()

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📅 Gasto Acumulado Anual", f"${total_anual:,.0f} COP")
            m2.metric("📊 Promedio Mensual de Gastos", f"${promedio_mensual:,.0f} COP")
            m3.metric("🔥 Mes Más Costoso", f"{mes_mas_caro['Mes_Nombre'][4:]}", f"${mes_mas_caro['Monto ($)']:,.0f} COP", delta_color="inverse")
            m4.metric("❄️ Mes Más Económico", f"{mes_mas_bajo['Mes_Nombre'][4:]}", f"${mes_mas_bajo['Monto ($)']:,.0f} COP", delta_color="normal")

        st.markdown("---")

        col_h1, col_h2 = st.columns(2)

        with col_h1:
            st.markdown("##### 📊 Comparativa de Gastos Totales Mes a Mes")
            fig_meses = px.bar(
                gastos_por_mes, x='Mes_Nombre', y='Monto ($)', color='Monto ($)',
                text_auto=',.0f', color_continuous_scale='Tealgrn'
            )
            fig_meses.update_layout(xaxis_title="Mes del Año", yaxis_title="Total Gastos ($ COP)", coloraxis_showscale=False)
            st.plotly_chart(fig_meses, use_container_width=True)

        with col_h2:
            st.markdown("##### 💡 Evolución Histórica de Facturas de Servicios Públicos")
            mask_serv_hist = df_gastos_hist['Categoría'].str.contains('Servicios|Administracion', case=False, na=False)
            df_serv_hist = df_gastos_hist[mask_serv_hist]

            if not df_serv_hist.empty:
                serv_evol = df_serv_hist.groupby(['Mes_Nombre', 'Categoría'])['Monto ($)'].sum().reset_index().sort_values(by='Mes_Nombre')
                fig_serv_line = px.line(
                    serv_evol, x='Mes_Nombre', y='Monto ($)', color='Categoría',
                    markers=True, text='Monto ($)'
                )
                fig_serv_line.update_traces(textposition="top center")
                fig_serv_line.update_layout(xaxis_title="Mes", yaxis_title="Valor Factura ($ COP)")
                st.plotly_chart(fig_serv_line, use_container_width=True)

        st.markdown("---")
        st.markdown("##### 📋 Matriz Anual de Servicios Públicos y Administración (Mes vs. Servicio)")
        if not df_serv_hist.empty:
            matriz_servicios = df_serv_hist.pivot_table(
                index='Categoría', 
                columns='Mes_Nombre', 
                values='Monto ($)', 
                aggfunc='sum', 
                fill_value=0
            )
            matriz_servicios['Promedio Mensual'] = matriz_servicios.mean(axis=1)
            matriz_servicios['Total Año'] = matriz_servicios.drop(columns='Promedio Mensual').sum(axis=1)
            st.dataframe(matriz_servicios.style.format("${:,.0f}"), use_container_width=True)

else:
    st.error("No se encontraron registros en Google Sheets.")
