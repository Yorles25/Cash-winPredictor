import streamlit as st
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import json
DATA_FILE = "resultados_guardados.json"

def cargar_datos():
    """Carga los resultados desde un archivo JSON."""
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return [] # Si el archivo no existe, empieza con una lista vacía

def guardar_datos(datos):
    """Guarda los resultados en un archivo JSON."""
    with open(DATA_FILE, 'w') as f:
        json.dump(datos, f, indent=4)
# Configuración inicial
st.set_page_config(
    page_title="Cash winPredictor", 
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 Cash winPredictor - Sistema Inteligente")
st.sidebar.header("📋 Navegación")

# Variables globales
franjas = ["mañana", "mediodía", "tarde", "noche", "madrugada"]
numeros = list(range(1, 10))

# Inicializar session state
if "resultados" not in st.session_state:
    st.session_state.resultados = cargar_datos()
if "pesos" not in st.session_state:
    st.session_state.pesos = {n: 1 for n in numeros}
if "pendientes" not in st.session_state:
    st.session_state.pendientes = []
  
# Función de cálculo de rotación
def calcular_rotacion(df, numero):
    fechas = df[df["numero"] == numero]["fecha"].unique()
    fechas = sorted(pd.to_datetime(fechas))
    if len(fechas) < 2:
        return None
    diferencias = [(fechas[i+1] - fechas[i]).days for i in range(len(fechas)-1)]
    return round(sum(diferencias) / len(diferencias), 2)

# MÓDULO 1: INGRESO DE RESULTADOS
def modulo_ingreso():
    st.header("🔢 Ingreso y Gestión de Resultados")
    
    # SECCIÓN DE CARGA MASIVA
    st.subheader("🚀 Carga Masiva desde Archivo CSV")
    uploaded_file = st.file_uploader(
        "Sube tu archivo con el historial de resultados (formato: fecha,franja,numero)", 
        type="csv"
    )
    if uploaded_file is not None:
        try:
            df_cargado = pd.read_csv(uploaded_file)
            nuevos_resultados = df_cargado.to_dict('records')
            st.session_state.resultados = nuevos_resultados
            guardar_datos(st.session_state.resultados) # GUARDAMOS LOS DATOS
            st.success(f"✅ ¡Se cargaron {len(nuevos_resultados)} resultados del archivo!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error al procesar el archivo: {e}")

    st.markdown("---")

    # SECCIÓN DE INGRESO MANUAL
    st.subheader("✍️ Ingreso Manual de Resultados")
    col1, col2, col3 = st.columns(3)
    with col1:
        fecha = st.date_input("Fecha del sorteo", value=datetime.today())
    with col2:
        franja = st.selectbox("Franja horaria", franjas)
    with col3:
        numero = st.selectbox("Número ganador", numeros)
    
    if st.button("➕ Agregar resultado"):
        nuevo_resultado = {
            "fecha": fecha.strftime("%Y-%m-%d"),
            "franja": franja,
            "numero": numero
        }
        if nuevo_resultado not in st.session_state.resultados:
            st.session_state.resultados.append(nuevo_resultado)
            guardar_datos(st.session_state.resultados) # GUARDAMOS LOS DATOS
            st.success("✅ Resultado agregado correctamente")
            st.rerun()
        else:
            st.warning("⚠️ Este resultado ya existe.")

    # SECCIÓN PARA MOSTRAR Y ELIMINAR RESULTADOS
    st.subheader("📋 Últimos Resultados")
    
    if st.session_state.resultados:
        encabezado_cols = st.columns([2, 2, 1, 1])
        encabezado_cols[0].write("**Fecha**")
        encabezado_cols[1].write("**Franja**")
        encabezado_cols[2].write("**Número**")
        encabezado_cols[3].write("**Acción**")
        st.markdown("---") 

        for i in reversed(range(len(st.session_state.resultados))):
            if len(st.session_state.resultados) - i > 10 and i < len(st.session_state.resultados) - 10:
                continue

            resultado = st.session_state.resultados[i]
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            col1.text(resultado["fecha"])
            col2.text(resultado["franja"])
            col3.text(resultado["numero"])
            
            if col4.button("❌", key=f"delete_button_{i}"):
                del st.session_state.resultados[i]
                guardar_datos(st.session_state.resultados) # GUARDAMOS LOS DATOS
                st.rerun()
    else:
        st.info("Aún no hay resultados para mostrar.")

# MÓDULO 2: ANÁLISIS DE ROTACIÓN
def modulo_rotacion():
    st.header("🔁 Análisis de Rotación")
    
    df = pd.DataFrame(st.session_state.resultados)
    
    if df.empty:
        st.warning("⚠️ No hay datos suficientes para calcular rotación")
        return None
    
    # Calcular rotaciones
    rotaciones = []
    for n in numeros:
        rot = calcular_rotacion(df, n)
        if rot is not None:
            rotaciones.append({"Número": n, "Rotación (días)": rot})
    
    if rotaciones:
        rot_df = pd.DataFrame(rotaciones)
        st.dataframe(rot_df)
        
        # Números activos
        umbral = st.slider("Umbral de rotación activa", 1, 10, 3)
        activos = rot_df[rot_df["Rotación (días)"] <= umbral]
        
        st.subheader("🎯 Números Activos")
        if not activos.empty:
            st.success(f"Números con rotación ≤ {umbral} días:")
            st.table(activos)
        else:
            st.info("No hay números activos con este umbral")
        
        return activos
    
    return None

# MÓDULO 3: GENERADOR DE PREDICCIÓN
def modulo_prediccion(activos):
    st.header("🔮 Generador de Predicción D'Alembert")
    
    if activos is None or activos.empty:
        st.warning("⚠️ No hay números activos para generar predicciones")
        return
    
    # Generar predicción
    prediccion = []
    candidatos = activos["Número"].tolist()
    
    for franja in franjas:
        if candidatos:
            mejor = max(candidatos, key=lambda n: st.session_state.pesos[n])
            prediccion.append({
                "Franja": franja, 
                "Número Sugerido": mejor,
                "Peso D'Alembert": st.session_state.pesos[mejor]
            })
    
    pred_df = pd.DataFrame(prediccion)
    st.table(pred_df)
    
    # Guardar predicción
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Guardar Predicción"):
            hoy = datetime.today().strftime("%Y-%m-%d")
            for _, row in pred_df.iterrows():
                st.session_state.pendientes.append({
                    "fecha": hoy,
                    "franja": row["Franja"],
                    "numero_predicho": row["Número Sugerido"],
                    "peso": row["Peso D'Alembert"]
                })
            st.success("✅ Predicción guardada")
    
    with col2:
        if st.button("🔄 Actualizar Pesos"):
            # Lógica de actualización de pesos basada en resultados
            df = pd.DataFrame(st.session_state.resultados)
            for numero in numeros:
                # Simplificado: ajustar según frecuencia reciente
                recientes = df.tail(20)
                apariciones = len(recientes[recientes["numero"] == numero])
                if apariciones > 4:  # Apareció mucho
                    st.session_state.pesos[numero] = max(1, st.session_state.pesos[numero] - 1)
                elif apariciones < 2:  # Apareció poco
                    st.session_state.pesos[numero] += 1
            st.success("✅ Pesos actualizados")

# MÓDULO 4: BACKTESTING
def modulo_backtesting():
    st.header("🧪 Backtesting Interactivo")
    
    df = pd.DataFrame(st.session_state.resultados)
    
    if len(df) < 20:
        st.warning("⚠️ Necesitas al menos 20 resultados para hacer backtesting efectivo")
        return
    
    # --- Interfaz para iniciar el backtesting ---
    fechas_disponibles = sorted(df["fecha"].unique())
    col1, col2 = st.columns(2)
    with col1:
        default_index_inicio = 0
        if len(fechas_disponibles) > 10:
            default_index_inicio = len(fechas_disponibles) - 11
        fecha_inicio = st.selectbox("Fecha inicio", fechas_disponibles, index=default_index_inicio)
    with col2:
        opciones_fin = [f for f in fechas_disponibles if f >= fecha_inicio]
        fecha_fin = st.selectbox("Fecha fin", opciones_fin, index=len(opciones_fin)-1)
    
    if st.button("▶️ Ejecutar Backtesting"):
        with st.spinner("🧠 Simulado estrategia... por favor espera."):
            df_test = df[(df["fecha"] >= fecha_inicio) & (df["fecha"] <= fecha_fin)]
            resultados_bt = []
            pesos_bt = {n: 1 for n in numeros}
            
            for fecha in sorted(df_test["fecha"].unique()):
                dia_df = df_test[df_test["fecha"] == fecha]
                df_historico = df[df["fecha"] < fecha]
                rotaciones_dia = []
                
                if not df_historico.empty:
                    for n in numeros:
                        rot = calcular_rotacion(df_historico, n)
                        if rot is not None and rot <= 3:
                            rotaciones_dia.append(n)
                
                for franja in franjas:
                    if rotaciones_dia:
                        predicho = max(rotaciones_dia, key=lambda n: pesos_bt[n])
                        real_row = dia_df[dia_df["franja"] == franja]
                        
                        if not real_row.empty:
                            real = real_row.iloc[0]["numero"]
                            acierto = (predicho == real)
                            resultados_bt.append({
                                "fecha": fecha, "franja": franja, "predicho": predicho,
                                "real": real, "acierto": acierto
                            })
                            if acierto:
                                pesos_bt[predicho] = max(1, pesos_bt[predicho] - 1)
                            else:
                                pesos_bt[predicho] += 1
            
            if resultados_bt:
                bt_df = pd.DataFrame(resultados_bt)
                st.session_state.bt_df = bt_df # <-- AQUÍ GUARDAMOS EL RESULTADO
            else:
                st.session_state.bt_df = None # Si no hay resultados, lo marcamos
                st.warning("No se generaron resultados de backtesting para el rango de fechas seleccionado.")

    # --- Sección para MOSTRAR los resultados si existen ---
    if "bt_df" in st.session_state and st.session_state.bt_df is not None:
        bt_df = st.session_state.bt_df # <-- AQUÍ RECUPERAMOS EL RESULTADO
        
        # --- Métricas generales ---
        total = len(bt_df)
        aciertos = bt_df["acierto"].sum()
        porcentaje = round((aciertos / total) * 100, 2) if total > 0 else 0
        
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("Total Predicciones", total)
        m_col2.metric("Aciertos", aciertos)
        m_col3.metric("Precisión", f"{porcentaje}%")
        
        # --- Detalle de Predicciones y Resultados (NUEVO) ---
        st.markdown("---")
        st.subheader("📋 Detalle de Predicciones y Resultados (Últimos 50)")
        enc_cols = st.columns([2, 2, 2, 2, 3])
        enc_cols[0].write("**Fecha**")
        enc_cols[1].write("**Franja**")
        enc_cols[2].write("**Predicción**")
        enc_cols[3].write("**Resultado Real**")
        enc_cols[4].write("**Status**")
        
        for index, row in bt_df.tail(50).iloc[::-1].iterrows():
            with st.container():
                res_cols = st.columns([2, 2, 2, 2, 3])
                res_cols[0].text(row['fecha'])
                res_cols[1].text(row['franja'].capitalize())
                res_cols[2].markdown(f"**{row['predicho']}**")
                res_cols[3].markdown(f"**{row['real']}**")
                if row['acierto']:
                    res_cols[4].success("✅ Acierto")
                else:
                    res_cols[4].error("❌ Fallo")
                st.divider()

        # --- Gráficos y tablas agregadas ---
        st.subheader("📈 Evolución de Aciertos")
        aciertos_por_dia = bt_df.groupby("fecha")["acierto"].sum().reset_index()
        st.line_chart(aciertos_por_dia.set_index("fecha")["acierto"])
        
        st.subheader("🎯 Rendimiento por Franja")
        rendimiento_franja = bt_df.groupby("franja").agg(
            aciertos_totales=('acierto', 'sum'),
            predicciones_totales=('acierto', 'count')
        ).reset_index()
        rendimiento_franja['precision'] = (rendimiento_franja['aciertos_totales'] / rendimiento_franja['predicciones_totales']).round(3)
        st.dataframe(rendimiento_franja)
# MÓDULO 5: VISUALIZACIÓN DE RENDIMIENTO
def modulo_graficos():
    st.header("📊 Gráficos de Rendimiento")
    
    df = pd.DataFrame(st.session_state.resultados)
    
    if df.empty:
        st.warning("⚠️ No hay datos para visualizar")
        return
    
    # Gráfico de frecuencia por número
    st.subheader("🔢 Frecuencia de Números")
    freq_numeros = df.groupby("numero").size().sort_index()
    st.bar_chart(freq_numeros)
    
    # Gráfico de actividad por franja
    st.subheader("⏰ Actividad por Franja")
    freq_franja = df.groupby("franja").size()
    st.bar_chart(freq_franja)
    
    # Tendencia temporal
    st.subheader("📅 Tendencia Temporal")
    df["fecha"] = pd.to_datetime(df["fecha"])
    actividad_diaria = df.groupby("fecha").size()
    st.line_chart(actividad_diaria)

# INTERFAZ PRINCIPAL
def main():
    # Sidebar para navegación
    pagina = st.sidebar.selectbox(
        "Selecciona un módulo:",
        [
            "📋 Resumen General",
            "🔢 Ingreso de Datos", 
            "🔁 Análisis de Rotación",
            "🔮 Predicción D'Alembert",
            "🧪 Backtesting",
            "📊 Gráficos y Análisis"
        ]
    )
    
    if pagina == "📋 Resumen General":
        st.markdown("""
        ## 🎯 Bienvenido al Cash winPredictor
        
        Sistema inteligente para predecir números de Cash winYorle usando:
        - **Análisis de Rotación**: Identifica números con patrones de frecuencia
        - **Sistema D'Alembert**: Optimiza selección según rendimiento histórico
        - **Backtesting**: Valida estrategias con datos reales
        - **Visualización**: Gráficos de rendimiento y tendencias
        
        ### 📊 Estado Actual
        """)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Resultados Cargados", len(st.session_state.resultados))
        with col2:
            st.metric("Predicciones Pendientes", len(st.session_state.pendientes))
        with col3:
            pendientes_df = pd.DataFrame(st.session_state.pendientes)
            if not pendientes_df.empty and st.session_state.resultados:
                df_resultados = pd.DataFrame(st.session_state.resultados)
                aciertos = 0
                for _, pred in pendientes_df.iterrows():
                    match = df_resultados[
                        (df_resultados["fecha"] == pred["fecha"]) & 
                        (df_resultados["franja"] == pred["franja"]) &
                        (df_resultados["numero"] == pred["numero_predicho"])
                    ]
                    if not match.empty:
                        aciertos += 1
                st.metric("Aciertos Confirmados", aciertos)
            else:
                st.metric("Aciertos Confirmados", 0)
        with col4:
            if st.session_state.resultados:
                ultimo = max(st.session_state.resultados, key=lambda x: datetime.strptime(x["fecha"], "%Y-%m-%d"))
                st.metric("Último Registro", ultimo["fecha"])
            else:
                st.metric("Último Registro", "N/A")
    
    elif pagina == "🔢 Ingreso de Datos":
        modulo_ingreso()
    
    elif pagina == "🔁 Análisis de Rotación":
        activos = modulo_rotacion()
        if activos is not None:
            st.session_state.activos = activos
    
    elif pagina == "🔮 Predicción D'Alembert":
        activos = st.session_state.get("activos", pd.DataFrame())
        modulo_prediccion(activos)
    
    elif pagina == "🧪 Backtesting":
        modulo_backtesting()
    
    elif pagina == "📊 Gráficos y Análisis":
        modulo_graficos()

# Bloque de arranque
if __name__ == "__main__":
    main()