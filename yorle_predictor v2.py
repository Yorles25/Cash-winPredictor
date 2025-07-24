import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json

# --- Configuración Inicial y Variables Globales ---
st.set_page_config(
    page_title="Cash winPredictor v3.0",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 Cash winPredictor v3.0 - Motor de Estrategias")
st.sidebar.header("📋 Navegación")

franjas = ["mañana", "mediodía", "tarde", "noche", "madrugada"]
numeros = list(range(1, 10))
DATA_FILE = "resultados_guardados.json"

# --- Funciones para Guardar y Cargar Datos ---
def cargar_datos():
    """Carga los resultados desde un archivo JSON."""
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            # Asegurarse de que las fechas se carguen correctamente como strings
            for record in data:
                if 'fecha' in record:
                    record['fecha'] = str(record['fecha']).split('T')[0]
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def guardar_datos(datos):
    """Guarda los resultados en un archivo JSON."""
    with open(DATA_FILE, 'w') as f:
        json.dump(datos, f, indent=4)

# --- Inicialización del Estado de la Sesión ---
if "resultados" not in st.session_state:
    st.session_state.resultados = cargar_datos()
if "pesos" not in st.session_state:
    st.session_state.pesos = {n: 0 for n in numeros}
if "pendientes" not in st.session_state:
    st.session_state.pendientes = []

# --- Funciones de Lógica de Estrategias ---
def calcular_rotacion(df, numero):
    fechas = df[df["numero"] == numero]["fecha"].unique()
    fechas = sorted(pd.to_datetime(fechas))
    if len(fechas) < 2:
        return None
    diferencias = [(fechas[i+1] - fechas[i]).days for i in range(len(fechas)-1)]
    return round(sum(diferencias) / len(diferencias), 2) if diferencias else None

# <--- NUEVO: Función para la estrategia "Patrones de Corto Plazo"
def generar_prediccion_corto_plazo(df_historico, fecha_actual_str):
    if df_historico.empty:
        return []

    try:
        # Asegurarse que la columna de fecha es del tipo correcto
        df_historico["fecha_dt"] = pd.to_datetime(df_historico["fecha"]).dt.date
        fecha_actual = pd.to_datetime(fecha_actual_str).date()
        hace_14_dias = fecha_actual - timedelta(days=14)
    except Exception as e:
        st.error(f"Error procesando fechas en estrategia de corto plazo: {e}")
        return []

    # Filtrar últimos 14 días
    df_filtrado = df_historico[df_historico["fecha_dt"] >= hace_14_dias].copy()

    if df_filtrado.empty:
        return []

    # Asignar ponderaciones por "recency bias" (más peso a los datos recientes)
    def ponderacion(fecha):
        dias_pasados = (fecha_actual - fecha).days
        return max(1, 15 - dias_pasados)  # Ayer: 14, Anteayer: 13 ...

    df_filtrado["peso"] = df_filtrado["fecha_dt"].apply(ponderacion)

    # Agrupar por número y sumar las ponderaciones
    puntuaciones = df_filtrado.groupby("numero")["peso"].sum()

    # Generar predicción: top 5 con mayor puntuación
    predicciones = puntuaciones.sort_values(ascending=False).head(5)
    return predicciones.index.tolist()


# --- Módulos de la Aplicación ---

# MÓDULO 1: INGRESO DE RESULTADOS (Sin cambios)
def modulo_ingreso():
    st.header("🔢 Ingreso y Gestión de Resultados")
    # ... (El código de este módulo no cambia)
    st.subheader("🚀 Carga Masiva desde Archivo CSV")
    uploaded_file = st.file_uploader(
        "Sube tu archivo con el historial (formato: fecha,franja,numero)", type="csv"
    )
    if uploaded_file is not None:
        try:
            df_cargado = pd.read_csv(uploaded_file)
            nuevos_resultados = df_cargado.to_dict('records')
            st.session_state.resultados = nuevos_resultados
            guardar_datos(st.session_state.resultados)
            st.success(f"✅ ¡Se cargaron {len(nuevos_resultados)} resultados del archivo!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error al procesar el archivo: {e}")

    st.markdown("---")
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
            "fecha": fecha.strftime("%Y-%m-%d"), "franja": franja, "numero": numero
        }
        if nuevo_resultado not in st.session_state.resultados:
            st.session_state.resultados.append(nuevo_resultado)
            guardar_datos(st.session_state.resultados)
            st.success("✅ Resultado agregado correctamente")
            st.rerun()
        else:
            st.warning("⚠️ Este resultado ya existe.")

    st.subheader("📋 Últimos Resultados")
    if st.session_state.resultados:
        enc_cols = st.columns([2, 2, 1, 1])
        enc_cols[0].write("**Fecha**"); enc_cols[1].write("**Franja**"); enc_cols[2].write("**Número**"); enc_cols[3].write("**Acción**")
        st.markdown("---") 
        for i in reversed(range(len(st.session_state.resultados))):
            if len(st.session_state.resultados) - i > 10: break
            resultado = st.session_state.resultados[i]
            row_cols = st.columns([2, 2, 1, 1])
            row_cols[0].text(resultado["fecha"])
            row_cols[1].text(resultado["franja"])
            row_cols[2].text(resultado["numero"])
            if row_cols[3].button("❌", key=f"delete_button_{i}"):
                del st.session_state.resultados[i]
                guardar_datos(st.session_state.resultados)
                st.rerun()
    else:
        st.info("Aún no hay resultados para mostrar.")

# MÓDULO 2: GENERADOR DE PREDICCIÓN <--- MODIFICADO
def modulo_prediccion():
    st.header("🔮 Generador de Predicciones")

    # <--- NUEVO: Selector de estrategia
    estrategia = st.selectbox(
        "¿Qué tipo de análisis deseas usar?",
        ["Doble Estrategia (Rotación + D'Alembert)", "Patrones de Corto Plazo (Últimos 14 días)"],
        help="Elige entre una estrategia basada en frecuencia histórica o una que detecta tendencias emergentes recientes."
    )

    if not st.session_state.resultados:
        st.warning("⚠️ No hay datos suficientes para generar predicciones."); return

    df = pd.DataFrame(st.session_state.resultados)
    predicciones_finales = []
    
    # --- Lógica para Doble Estrategia ---
    if estrategia == "Doble Estrategia (Rotación + D'Alembert)":
        st.markdown("🔁 **Doble Estrategia** — Identifica números históricamente frecuentes y los prioriza con análisis de riesgo D'Alembert.")
        umbral = st.slider("Umbral de rotación activa", 1, 10, 4)
        rotaciones = {n: calcular_rotacion(df, n) for n in numeros}
        activos = [n for n, r in rotaciones.items() if r is not None and r <= umbral]
        
        if not activos:
            st.warning("No hay 'números activos' con el umbral seleccionado. Usando todos los números como candidatos.");
            activos = numeros

        candidatos_ordenados = sorted(activos, key=lambda n: st.session_state.pesos.get(n, 0), reverse=True)
        mejores_candidatos = candidatos_ordenados[:5]

        if not mejores_candidatos:
            st.warning("⚠️ No se pudieron determinar los mejores candidatos."); return
        
        for i, franja in enumerate(franjas):
            num_predicho = mejores_candidatos[i % len(mejores_candidatos)]
            predicciones_finales.append({
                "Franja": franja, "Número Sugerido": num_predicho,
                "Razón": f"Peso D'Alembert: {st.session_state.pesos.get(num_predicho, 0)}"
            })
    
    # --- Lógica para Patrones de Corto Plazo ---
    else:
        st.markdown("📈 **Patrones de Corto Plazo** — Detecta señales emergentes analizando los últimos 14 días con más peso en lo reciente.")
        hoy_str = datetime.today().strftime("%Y-%m-%d")
        mejores_candidatos = generar_prediccion_corto_plazo(df.copy(), hoy_str)

        if not mejores_candidatos:
            st.warning("⚠️ No hay suficientes datos en los últimos 14 días para generar predicciones."); return

        for i, franja in enumerate(franjas):
            num_predicho = mejores_candidatos[i % len(mejores_candidatos)]
            predicciones_finales.append({
                "Franja": franja, "Número Sugerido": num_predicho,
                "Razón": "Tendencia Reciente"
            })

    pred_df = pd.DataFrame(predicciones_finales)
    st.subheader("🎯 Predicciones Sugeridas para Hoy"); st.table(pred_df)


# MÓDULO 3: BACKTESTING <--- MODIFICADO PROFUNDAMENTE
def modulo_backtesting():
    st.header("🧪 Backtesting Interactivo")
    if len(st.session_state.resultados) < 20:
        st.warning("⚠️ Necesitas al menos 20 resultados para hacer backtesting efectivo"); return

    # <--- NUEVO: Selector de estrategia para el backtesting
    estrategia_bt = st.selectbox(
        "¿Qué estrategia quieres simular?",
        ["Doble Estrategia (Rotación + D'Alembert)", "Patrones de Corto Plazo (Últimos 14 días)"],
        key="bt_strategy_selector"
    )
    
    df = pd.DataFrame(st.session_state.resultados)
    df["fecha"] = pd.to_datetime(df["fecha"]).dt.strftime('%Y-%m-%d')
    fechas_disponibles = sorted(df["fecha"].unique())
    
    col1, col2 = st.columns(2)
    default_idx = len(fechas_disponibles) - 11 if len(fechas_disponibles) > 10 else 0
    fecha_inicio = col1.selectbox("Fecha inicio", fechas_disponibles, index=default_idx)
    opciones_fin = [f for f in fechas_disponibles if f >= fecha_inicio]
    fecha_fin = col2.selectbox("Fecha fin", opciones_fin, index=len(opciones_fin)-1)
    
    if st.button("▶️ Ejecutar Backtesting"):
        with st.spinner(f"🧠 Simulado la '{estrategia_bt}'... por favor espera."):
            df_test = df[(df["fecha"] >= fecha_inicio) & (df["fecha"] <= fecha_fin)]
            resultados_bt = []
            pesos_bt = {n: 0 for n in numeros} # Solo para la Doble Estrategia
            
            for fecha_str in sorted(df_test["fecha"].unique()):
                dia_df_real = df_test[df_test["fecha"] == fecha_str]
                df_historico = df[df["fecha"] < fecha_str]

                predicciones_dia = []
                # --- Generar predicciones del día según la estrategia ---
                if estrategia_bt == "Doble Estrategia (Rotación + D'Alembert)":
                    rotaciones_dia = [n for n in numeros if not df_historico.empty and (rot := calcular_rotacion(df_historico, n)) is not None and rot <= 4]
                    if not rotaciones_dia:
                        candidatos = sorted(pesos_bt, key=pesos_bt.get, reverse=True)
                    else:
                        candidatos = sorted(rotaciones_dia, key=lambda n: pesos_bt.get(n, 0), reverse=True)
                    predicciones_dia = candidatos[:5]

                elif estrategia_bt == "Patrones de Corto Plazo (Últimos 14 días)":
                    predicciones_dia = generar_prediccion_corto_plazo(df_historico.copy(), fecha_str)

                if not predicciones_dia:
                    continue # No se puede predecir para este día, saltar

                # --- Comparar predicciones con resultados reales ---
                for i, franja in enumerate(franjas):
                    predicho = predicciones_dia[i % len(predicciones_dia)]
                    real_row = dia_df_real[dia_df_real["franja"] == franja]
                    
                    if not real_row.empty:
                        real = real_row.iloc[0]["numero"]
                        acierto = (predicho == real)
                        resultados_bt.append({"fecha": fecha_str, "franja": franja, "predicho": predicho, "real": real, "acierto": acierto})
                        
                        # Actualizar pesos solo si es la estrategia D'Alembert
                        if estrategia_bt == "Doble Estrategia (Rotación + D'Alembert)":
                            if acierto:
                                pesos_bt[predicho] = max(0, pesos_bt.get(predicho, 0) - 1)
                            else:
                                pesos_bt[predicho] += 1
                                
            st.session_state.bt_df = pd.DataFrame(resultados_bt) if resultados_bt else None

    if "bt_df" in st.session_state and st.session_state.bt_df is not None:
        bt_df = st.session_state.bt_df
        total = len(bt_df); aciertos = bt_df["acierto"].sum(); porcentaje = round((aciertos / total) * 100, 2) if total > 0 else 0
        st.subheader(f"Resultados para: {st.session_state.get('bt_strategy_selector')}")
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("Total Predicciones", total); m_col2.metric("Aciertos", aciertos); m_col3.metric("Precisión", f"{porcentaje}%")
        
        # ... (El código para mostrar los resultados del backtesting no cambia) ...
        st.markdown("---"); st.subheader("📋 Detalle de Predicciones y Resultados (Últimos 50)")
        enc_cols = st.columns([2, 2, 2, 2, 3]); enc_cols[0].write("**Fecha**"); enc_cols[1].write("**Franja**"); enc_cols[2].write("**Predicción**"); enc_cols[3].write("**Resultado Real**"); enc_cols[4].write("**Status**")
        for _, row in bt_df.tail(50).iloc[::-1].iterrows():
            with st.container():
                res_cols = st.columns([2, 2, 2, 2, 3])
                res_cols[0].text(row['fecha']); res_cols[1].text(row['franja'].capitalize()); res_cols[2].markdown(f"**{row['predicho']}**"); res_cols[3].markdown(f"**{row['real']}**")
                if row['acierto']: res_cols[4].success("✅ Acierto")
                else: res_cols[4].error("❌ Fallo")
                st.divider()

        st.subheader("📈 Evolución de Aciertos Diarios")
        aciertos_por_dia = bt_df.groupby("fecha")["acierto"].sum().reset_index()
        st.line_chart(aciertos_por_dia.set_index("fecha")["acierto"])
        
        st.subheader("🎯 Rendimiento por Franja Horaria")
        rend_franja = bt_df.groupby("franja").agg(aciertos_totales=('acierto', 'sum'), predicciones_totales=('acierto', 'count')).reset_index()
        rend_franja['precision'] = (rend_franja['aciertos_totales'] / rend_franja['predicciones_totales']).round(3) * 100
        st.dataframe(rend_franja.style.format({'precision': '{:.1f}%'}))


# --- INTERFAZ PRINCIPAL Y ARRANQUE ---
def main():
    pagina = st.sidebar.selectbox("Selecciona un módulo:", [
        "🔮 Predicciones", "🧪 Backtesting", "🔢 Ingreso de Datos"
    ])
    
    if pagina == "🔮 Predicciones": modulo_prediccion()
    elif pagina == "🧪 Backtesting": modulo_backtesting()
    elif pagina == "🔢 Ingreso de Datos": modulo_ingreso()

if __name__ == "__main__":
    main()