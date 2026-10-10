import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

# -----------------------------------------------------------------------------
# CONFIGURACIÓN GENERAL DE LA PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Control Financiero Personal | Dashboard",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados para darle un toque limpio y profesional
st.markdown("""
    <style>
    .main { background-color: #F8F9FA; }
    .metric-card {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.05);
        border-left: 5px solid #1E88E5;
    }
    .stMetric label { font-size: 0.9rem !important; color: #555 !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Control & Dashboard Financiero Personal")
st.caption("Sincronizado automáticamente con tu archivo en Google Drive")
st.markdown("---")

# -----------------------------------------------------------------------------
# CONEXIÓN AUTOMÁTICA CON GOOGLE DRIVE (GOOGLE SHEETS)
# -----------------------------------------------------------------------------
# ttl=5 asegura que los datos se refresquen automáticamente cada 5 segundos
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=5)
except Exception as e:
    st.info("💡 **Nota:** Conecta la clave API de Google Sheets en tus Secrets de Streamlit para sincronización directa.")
    # Carga de respaldo local para pruebas
    df = pd.DataFrame()

# Limpieza y preparación de datos
if not df.empty:
    # Normalizar nombres de columnas
    df.columns = [str(col).strip() for col in df.columns]
    
    # Filtrar filas válidas que contengan monto y categoría
    df = df.dropna(subset=['Categoría', 'Monto ($)'])
    df['Monto ($)'] = pd.to_numeric(df['Monto ($)'], errors='coerce').fillna(0)
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce').dt.strftime('%Y-%m-%d')

    # Separar Ingresos y Gastos
    es_ingreso = df['Categoría'].str.contains('QUIN|Ingreso|Sueldo', case=False, na=False)
    df_ingresos = df[es_ingreso]
    df_gastos = df[~es_ingreso]

    total_ingresos = df_ingresos['Monto ($)'].sum()
    total_gastos = df_gastos['Monto ($)'].sum()
    balance = total_ingresos - total_gastos

    # -----------------------------------------------------------------------------
    # 1. INDICADORES CLAVE DE PERFORMANCE (KPIs)
    # -----------------------------------------------------------------------------
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    kpi1.metric("💰 Total Ingresos", f"${total_ingresos:,.0f} COP")
    kpi2.metric("💸 Total Gastos", f"${total_gastos:,.0f} COP")
    kpi3.metric("📈 Balance Neto", f"${balance:,.0f} COP", 
                delta=f"{(balance/total_ingresos)*100:.1f}% del ingreso" if total_ingresos > 0 else "0%",
                delta_color="normal" if balance >= 0 else "inverse")
    
    # Calcular compromiso de deuda (Tarjetas y Créditos)
    deudas = df_gastos[df_gastos['Categoría'].str.contains('Tarjeta|Credito|Crédito', case=False, na=False)]['Monto ($)'].sum()
    porcentaje_deuda = (deudas / total_ingresos * 100) if total_ingresos > 0 else 0
    kpi4.metric("💳 Compromiso de Deuda", f"${deudas:,.0f} COP", delta=f"{porcentaje_deuda:.1f}% de Ingresos", delta_color="inverse")

    st.markdown("---")

    # -----------------------------------------------------------------------------
    # 2. GRÁFICOS INTERACTIVOS DE COMPORTAMIENTO
    # -----------------------------------------------------------------------------
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("🍩 Distribución de Gastos por Categoría")
        gastos_cat = df_gastos.groupby('Categoría')['Monto ($)'].sum().reset_index()
        gastos_cat = gastos_cat.sort_values(by='Monto ($)', ascending=False)
        
        fig_donut = px.pie(
            gastos_cat, 
            values='Monto ($)', 
            names='Categoría', 
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        fig_donut.update_traces(textposition='inside', textinfo='percent+label')
        fig_donut.update_layout(showlegend=False, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_right:
        st.subheader("💳 Gastos por Método de Pago")
        gastos_metodo = df_gastos.groupby('Método de Pago')['Monto ($)'].sum().reset_index()
        
        fig_bar = px.bar(
            gastos_metodo, 
            x='Método de Pago', 
            y='Monto ($)', 
            color='Método de Pago',
            text_auto=',.0f',
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        fig_bar.update_layout(xaxis_title="", yaxis_title="Monto ($ COP)", showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

    # -----------------------------------------------------------------------------
    # 3. ALERTAS DE LÍMITES PRESUPUESTALES (SEMÁFOROS)
    # -----------------------------------------------------------------------------
    st.subheader("🚨 Semáforo de Límites Presupuestales")

    lim_col1, lim_col2, lim_col3 = st.columns(3)

    # Límite de Deuda (Máx 35% del Ingreso)
    limite_deuda = total_ingresos * 0.35
    with lim_col1:
        st.caption("💳 **Servicio de Deuda / Tarjetas**")
        prog_deuda = min(deudas / limite_deuda, 1.0) if limite_deuda > 0 else 0
        st.progress(prog_deuda)
        if deudas > limite_deuda:
            st.error(f"❌ Excedido: ${deudas:,.0f} de ${limite_deuda:,.0f} máx.")
        else:
            st.success(f"✅ En Rango: ${deudas:,.0f} de ${limite_deuda:,.0f} máx.")

    # Límite de Gastos Hormiga e Imprevistos (Máx $250,000)
    gastos_hormiga = df_gastos[df_gastos['Categoría'].isin(['Imprevistos', 'Alimentación', 'Entretenimiento'])]['Monto ($)'].sum()
    limite_hormiga = 250000
    with lim_col2:
        st.caption("🍔 **Gastos Variables & Ocio**")
        prog_hormiga = min(gastos_hormiga / limite_hormiga, 1.0)
        st.progress(prog_hormiga)
        if gastos_hormiga > limite_hormiga:
            st.warning(f"⚠️ Atención: ${gastos_hormiga:,.0f} de ${limite_hormiga:,.0f} sugeridos.")
        else:
            st.success(f"✅ Bajo Control: ${gastos_hormiga:,.0f} de ${limite_hormiga:,.0f} máx.")

    # Límite Servicios Fijos (Máx $550,000)
    servicios_fijos = df_gastos[df_gastos['Categoría'].str.contains('Servicios|Administracion', case=False, na=False)]['Monto ($)'].sum()
    limite_servicios = 550000
    with lim_col3:
        st.caption("🏠 **Servicios Fijos & Administración**")
        prog_servicios = min(servicios_fijos / limite_servicios, 1.0)
        st.progress(prog_servicios)
        st.success(f"✅ Fijo Controlado: ${servicios_fijos:,.0f} de ${limite_servicios:,.0f} estimado.")

    st.markdown("---")

    # -----------------------------------------------------------------------------
    # 4. TABLA DETALLADA CON FILTROS Y BÚSQUEDA
    # -----------------------------------------------------------------------------
    st.subheader("📝 Historial Detallado de Movimientos")
    
    col_filtro1, col_filtro2 = st.columns(2)
    with col_filtro1:
        cat_filtro = st.multiselect("Filtrar por Categoría:", options=df['Categoría'].unique())
    with col_filtro2:
        estado_filtro = st.multiselect("Filtrar por Estado:", options=df['Estado'].unique())

    df_filtered = df.copy()
    if cat_filtro:
        df_filtered = df_filtered[df_filtered['Categoría'].isin(cat_filtro)]
    if estado_filtro:
        df_filtered = df_filtered[df_filtered['Estado'].isin(estado_filtro)]

    st.dataframe(df_filtered, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# BARRA LATERAL: REGISTRO RÁPIDO DE DATOS HACIA GOOGLE DRIVE
# -----------------------------------------------------------------------------
st.sidebar.header("➕ Ingresar Nuevo Registro")
st.sidebar.caption("Se guardará solo en tu Google Drive")

with st.sidebar.form("formulario_registro", clear_on_submit=True):
    f_fecha = st.date_input("Fecha")
    f_cat = st.selectbox("Categoría", [
        "Debito 1 QUIN", "Debito 2 QUIN", "Servicios - Energía", "Servicios - Agua", 
        "Servicios - Gas", "Servicios- Internet Hogar", "Pago Administracion/parqueadero",
        "Pago Tarjeta de Credito", "Pago Credito", "Alimentación", "Mercado", 
        "Transporte", "Entretenimiento", "Imprevistos"
    ])
    f_desc = st.text_input("Descripción (Ej: Compra supermercado)")
    f_metodo = st.selectbox("Método de Pago", ["Transferencia", "Tarjeta debito", "Tarjeta credito", "Efectivo", "Consignacion bancaria"])
    f_estado = st.selectbox("Estado", ["Pagado", "Consignado", "Credito"])
    f_monto = st.number_input("Monto ($ COP)", min_value=0, step=5000, value=20000)
    
    submitted = st.form_submit_button("💾 Guardar Registro")
    
    if submitted:
        nuevo_registro = pd.DataFrame([{
            "Fecha": str(f_fecha),
            "Categoría": f_cat,
            "Descripción": f_desc,
            "Método de Pago": f_metodo,
            "Estado": f_estado,
            "Monto ($)": f_monto
        }])
        
        try:
            df_actualizado = pd.concat([df, nuevo_registro], ignore_index=True)
            conn.update(data=df_actualizado)
            st.sidebar.success("✅ ¡Guardado con éxito en Google Drive!")
            st.rerun()
        except Exception as err:
            st.sidebar.error("Error al escribir en la nube. Verifica los permisos de edición.")
