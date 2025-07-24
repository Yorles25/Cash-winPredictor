import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json

# --- Configuración Inicial y Variables Globales ---
st.set_page_config(
    page_title="Cash winPredictor v3.1",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 Cash winPredictor v3.1 - Predicciones Múltiples")
st.sidebar.header("📋 Navegación")

franjas = ["mañana", "mediodía", "tarde", "noche", "madrugada"]
numeros = list(range(1, 10))
DATA_FILE = "resultados_guardados.json"

# --- Funciones para Guardar y Cargar Datos ---
def cargar_datos():
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            for record in data:
                if 'fecha' in record:
                    record['fecha'] = str(record['fecha']).split('T')[0]
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def guardar_datos(datos):
    with open(DATA_FILE, 'w') as f:
        json.dump(datos, f, indent=4)

# --- Inicialización del Estado de la Sesión ---
if "resultados" not in st.session_state:
    st.session_state.resultados = cargar_datos()
if "pesos" not in st.session_state:
    st.session_state.pesos = {n: 0 for n in numeros}

# --- Funciones de Lógica de Estrategias ---
def calcular_rotacion(df, numero):
    fechas = df[df["numero"] == numero]["fecha"].unique()
    fechas = sorted(pd.to_datetime(fechas))
    if len(fechas) < 2: return None
    diferencias = [(fechas[i+1] - fechas[i]).days for i in range(len(fechas)-1)]
    return round(sum(diferencias) / len(diferencias), 2) if diferencias else None

def generar_prediccion_corto_plazo(df_historico, fecha_actual_str):
    if df_historico.empty: return []
    try:
        df_historico["fecha_dt"] = pd.to_datetime(df_historico["fecha"]).dt.date
        fecha_actual = pd.to_datetime(fecha_actual_str).date()
        hace_14_dias = fecha_actual - timedelta(days=14)
    except Exception: return []
    df_filtrado = df_historico[df_historico["fecha_dt"] >= hace_14_dias].copy()
    if df_filtrado.empty: return []
    def ponderacion(fecha):
        dias_pasados = (fecha_actual - fecha).days
        return max(1, 15 - dias_pasados)
    df_filtrado["peso"] = df_filtrado["fecha_dt"].apply(ponderacion)
    puntuaciones = df_filtrado.groupby("numero")["peso"].sum()
    # <--- MODIFICADO: Pedimos más candidatos para tener variedad
    predicciones = puntuaciones.sort_values(ascending=False).head(7)
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
    estrategia = st.selectbox(
        "¿Qué tipo de análisis deseas usar?",
        ["Doble Estrategia (Rotación + D'Alembert)", "Patrones de Corto Plazo (Últimos 14 días)"],
        help="Elige entre una estrategia basada en frecuencia histórica o una que detecta tendencias emergentes recientes."
    )
    if not st.session_state.resultados:
        st.warning("⚠️ No hay datos suficientes para generar predicciones."); return

    df = pd.DataFrame(st.session_state.resultados)
    predicciones_finales = []
    mejores_candidatos = []

    if estrategia == "Doble Estrategia (Rotación + D'Alembert)":
        st.markdown("🔁 **Doble Estrategia** — Identifica números históricamente frecuentes y los prioriza con análisis de riesgo D'Alembert.")
        umbral = st.slider("Umbral de rotación activa", 1, 10, 4)
        rotaciones = {n: calcular_rotacion(df, n) for n in numeros}
        activos = [n for n, r in rotaciones.items() if r is not None and r <= umbral]
        if not activos:
            st.warning("No hay 'números activos' con el umbral seleccionado. Usando todos los números como candidatos.");
            activos = numeros
        candidatos_ordenados = sorted(activos, key=lambda n: st.session_state.pesos.get(n, 0), reverse=True)
        # <--- MODIFICADO: Pedimos más candidatos
        mejores_candidatos = candidatos_ordenados[:7]
    else:
        st.markdown("📈 **Patrones de Corto Plazo** — Detecta señales emergentes analizando los últimos 14 días con más peso en lo reciente.")
        hoy_str = datetime.today().strftime("%Y-%m-%d")
        mejores_candidatos = generar_prediccion_corto_plazo(df.copy(), hoy_str)

    # <--- MODIFICADO: Lógica unificada para generar 3 predicciones por franja
    if len(mejores_candidatos) < 3:
        st.warning("⚠️ No hay suficientes candidatos (<3) para generar predicciones de 3 números."); return
    
    for i, franja in enumerate(franjas):
        # Técnica de ventana deslizante para generar 3 números
        idx1 = i % len(mejores_candidatos)
        idx2 = (i + 1) % len(mejores_candidatos)
        idx3 = (i + 2) % len(mejores_candidatos)
        prediccion_triple = [mejores_candidatos[idx1], mejores_candidatos[idx2], mejores_candidatos[idx3]]
        
        # Formatear para mostrar en la tabla
        numeros_str = ", ".join(map(str, sorted(prediccion_triple)))
        predicciones_finales.append({
            "Franja": franja, "Números Sugeridos": numeros_str
        })
        
    pred_df = pd.DataFrame(predicciones_finales)
    st.subheader("🎯 Predicciones Sugeridas para Hoy"); st.table(pred_df)


# MÓDULO 3: BACKTESTING <--- MODIFICADO PROFUNDAMENTE
def modulo_backtesting():
    st.header("🧪 Backtesting Interactivo")
    if len(st.session_state.resultados) < 20:
        st.warning("⚠️ Necesitas al menos 20 resultados para hacer backtesting efectivo"); return

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
            pesos_bt = {n: 0 for n in numeros}
            
            for fecha_str in sorted(df_test["fecha"].unique()):
                dia_df_real = df_test[df_test["fecha"] == fecha_str]
                df_historico = df[df["fecha"] < fecha_str]
                
                candidatos_dia = []
                if estrategia_bt == "Doble Estrategia (Rotación + D'Alembert)":
                    rotaciones_dia = [n for n in numeros if not df_historico.empty and (rot := calcular_rotacion(df_historico, n)) is not None and rot <= 4]
                    if not rotaciones_dia:
                        activos = sorted(pesos_bt, key=pesos_bt.get, reverse=True)
                    else:
                        activos = sorted(rotaciones_dia, key=lambda n: pesos_bt.get(n, 0), reverse=True)
                    candidatos_dia = activos[:7]
                elif estrategia_bt == "Patrones de Corto Plazo (Últimos 14 días)":
                    candidatos_dia = generar_prediccion_corto_plazo(df_historico.copy(), fecha_str)

                if len(candidatos_dia) < 3: continue

                for i, franja in enumerate(franjas):
                    idx1 = i % len(candidatos_dia)
                    idx2 = (i + 1) % len(candidatos_dia)
                    idx3 = (i + 2) % len(candidatos_dia)
                    prediccion_triple = [candidatos_dia[idx1], candidatos_dia[idx2], candidatos_dia[idx3]]
                    
                    real_row = dia_df_real[dia_df_real["franja"] == franja]
                    
                    if not real_row.empty:
                        real = real_row.iloc[0]["numero"]
                        # <--- MODIFICADO: La nueva definición de acierto
                        acierto = real in prediccion_triple
                        
                        predicho_str = ", ".join(map(str, sorted(prediccion_triple)))
                        resultados_bt.append({"fecha": fecha_str, "franja": franja, "predicho": predicho_str, "real": real, "acierto": acierto})
                        
                        if estrategia_bt == "Doble Estrategia (Rotación + D'Alembert)":
                            if acierto:
                                pesos_bt[real] = max(0, pesos_bt.get(real, 0) - 1)
                            else:
                                # Aumentamos el peso del primer candidato del trío (el más probable)
                                pesos_bt[prediccion_triple[0]] += 1
                                
            st.session_state.bt_df = pd.DataFrame(resultados_bt) if resultados_bt else None

    if "bt_df" in st.session_state and st.session_state.bt_df is not None:
        bt_df = st.session_state.bt_df
        total = len(bt_df); aciertos = bt_df["acierto"].sum(); porcentaje = round((aciertos / total) * 100, 2) if total > 0 else 0
        st.subheader(f"Resultados para: {st.session_state.get('bt_strategy_selector')}")
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("Total Predicciones", total); m_col2.metric("Aciertos", aciertos); m_col3.metric("Precisión", f"{porcentaje}%")
        
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