import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import math

# --- Configuración Inicial y Variables Globales ---
st.set_page_config(
    page_title="Cash winPredictor v4.1",
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 Cash winPredictor v4.1 - Laboratorio Interactivo")
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
                if 'fecha' in record: record['fecha'] = str(record['fecha']).split('T')[0]
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def guardar_datos(datos):
    with open(DATA_FILE, 'w') as f:
        json.dump(datos, f, indent=4)

# --- Inicialización del Estado de la Sesión ---
if "resultados" not in st.session_state: st.session_state.resultados = cargar_datos()
if "pesos" not in st.session_state: st.session_state.pesos = {n: 0 for n in numeros}

# --- Funciones de Lógica de Estrategias ---
def calcular_rotacion(df, numero):
    fechas = df[df["numero"] == numero]["fecha"].unique()
    fechas = sorted(pd.to_datetime(fechas))
    if len(fechas) < 2: return None
    diferencias = [(fechas[i+1] - fechas[i]).days for i in range(len(fechas)-1)]
    return round(sum(diferencias) / len(diferencias), 2) if diferencias else None

# <--- CORREGIDO: La definición de la función usa los nombres de parámetros correctos y consistentes
def generar_prediccion_corto_plazo(df_historico, fecha_actual_str, ventana_dias, numero_candidatos, tipo_ponderacion):
    if df_historico.empty: return []
    try:
        df_historico["fecha_dt"] = pd.to_datetime(df_historico["fecha"]).dt.date
        fecha_actual = pd.to_datetime(fecha_actual_str).date()
        hace_x_dias = fecha_actual - timedelta(days=ventana_dias)
    except Exception: return []
    
    df_filtrado = df_historico[df_historico["fecha_dt"] >= hace_x_dias].copy()
    if df_filtrado.empty: return []

    if tipo_ponderacion == 'Exponencial':
        def ponderacion(fecha):
            dias_pasados = (fecha_actual - fecha).days
            return math.ceil(1.5 ** (ventana_dias - dias_pasados))
    else: # Lineal
        def ponderacion(fecha):
            dias_pasados = (fecha_actual - fecha).days
            return max(1, (ventana_dias + 1) - dias_pasados)
    
    df_filtrado["peso"] = df_filtrado["fecha_dt"].apply(ponderacion)
    puntuaciones = df_filtrado.groupby("numero")["peso"].sum()
    predicciones = puntuaciones.sort_values(ascending=False).head(numero_candidatos)
    return predicciones.index.tolist()

# --- Módulos de la Aplicación ---

# MÓDULO 1: INGRESO DE RESULTADOS
def modulo_ingreso():
    st.header("🔢 Ingreso y Gestión de Resultados")
    st.subheader("🚀 Carga Masiva desde Archivo CSV")
    uploaded_file = st.file_uploader("Sube tu archivo con el historial (formato: fecha,franja,numero)", type="csv")
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
    with col1: fecha = st.date_input("Fecha del sorteo", value=datetime.today())
    with col2: franja = st.selectbox("Franja horaria", franjas)
    with col3: numero = st.selectbox("Número ganador", numeros)
    if st.button("➕ Agregar resultado"):
        nuevo_resultado = {"fecha": fecha.strftime("%Y-%m-%d"), "franja": franja, "numero": numero}
        if nuevo_resultado not in st.session_state.resultados:
            st.session_state.resultados.append(nuevo_resultado)
            guardar_datos(st.session_state.resultados)
            st.success("✅ Resultado agregado correctamente")
            st.rerun()
        else: st.warning("⚠️ Este resultado ya existe.")
    st.subheader("📋 Últimos Resultados")
    if st.session_state.resultados:
        enc_cols = st.columns([2, 2, 1, 1])
        enc_cols[0].write("**Fecha**"); enc_cols[1].write("**Franja**"); enc_cols[2].write("**Número**"); enc_cols[3].write("**Acción**")
        st.markdown("---")
        for i in reversed(range(len(st.session_state.resultados))):
            if len(st.session_state.resultados) - i > 10: break
            resultado = st.session_state.resultados[i]
            row_cols = st.columns([2, 2, 1, 1])
            row_cols[0].text(resultado["fecha"]); row_cols[1].text(resultado["franja"]); row_cols[2].text(resultado["numero"])
            if row_cols[3].button("❌", key=f"delete_button_{i}"):
                del st.session_state.resultados[i]
                guardar_datos(st.session_state.resultados)
                st.rerun()
    else: st.info("Aún no hay resultados para mostrar.")

# <--- CORREGIDO: La función que crea los parámetros ahora usa nombres consistentes.
def render_strategy_parameters(strategy_name):
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Parámetros de Estrategia")
    params = {}
    if "Doble Estrategia" in strategy_name:
        params['umbral_rotacion'] = st.sidebar.slider("Umbral de Rotación (días)", 1, 15, 4)
        params['numero_candidatos'] = st.sidebar.number_input("Número de Candidatos", min_value=3, max_value=9, value=7, step=1, key='nc_doble')
    
    if "Patrones de Corto Plazo" in strategy_name:
        params['ventana_dias'] = st.sidebar.number_input("Ventana de Análisis (días)", min_value=3, max_value=30, value=10, step=1)
        params['numero_candidatos'] = st.sidebar.number_input("Número de Candidatos", min_value=3, max_value=9, value=5, step=1, key='nc_corto')
        params['tipo_ponderacion'] = st.sidebar.selectbox("Tipo de Ponderación", ["Exponencial", "Lineal"], index=0)
    
    return params

# MÓDULO 2: GENERADOR DE PREDICCIÓN
def modulo_prediccion():
    st.header("🔮 Generador de Predicciones")
    
    strategy_name = st.selectbox(
        "¿Qué tipo de análisis deseas usar?",
        ["Patrones de Corto Plazo", "Doble Estrategia (Rotación + D'Alembert)"],
        help="Elige una estrategia y ajusta sus parámetros en la barra lateral."
    )
    
    params = render_strategy_parameters(strategy_name)

    if not st.session_state.resultados:
        st.warning("⚠️ No hay datos suficientes para generar predicciones."); return

    df = pd.DataFrame(st.session_state.resultados)
    mejores_candidatos = []
    
    if "Doble Estrategia" in strategy_name:
        st.markdown(f"🔁 **Doble Estrategia** — Usando umbral de `{params['umbral_rotacion']}` días.")
        rotaciones = {n: calcular_rotacion(df, n) for n in numeros}
        activos = [n for n, r in rotaciones.items() if r is not None and r <= params['umbral_rotacion']]
        if not activos:
            st.warning("No hay 'activos'. Usando todos los números como candidatos."); activos = numeros
        candidatos_ordenados = sorted(activos, key=lambda n: st.session_state.pesos.get(n, 0), reverse=True)
        mejores_candidatos = candidatos_ordenados[:params['numero_candidatos']]
    else: # Patrones de Corto Plazo
        st.markdown(f"📈 **Patrones de Corto Plazo** — Usando ventana de `{params['ventana_dias']}` días con ponderación `{params['tipo_ponderacion']}`.")
        hoy_str = datetime.today().strftime("%Y-%m-%d")
        # <--- CORREGIDO: La llamada a la función ahora pasa los parámetros correctamente.
        mejores_candidatos = generar_prediccion_corto_plazo(
            df_historico=df.copy(), 
            fecha_actual_str=hoy_str, 
            ventana_dias=params['ventana_dias'],
            numero_candidatos=params['numero_candidatos'],
            tipo_ponderacion=params['tipo_ponderacion']
        )
        
    if len(mejores_candidatos) < 3:
        st.warning(f"⚠️ Solo se generaron {len(mejores_candidatos)} candidatos. Se necesitan al menos 3."); return
    
    predicciones_finales = []
    for i, franja in enumerate(franjas):
        indices = [(i + j) % len(mejores_candidatos) for j in range(3)]
        prediccion_triple = list(set([mejores_candidatos[idx] for idx in indices]))
        numeros_str = ", ".join(map(str, sorted(prediccion_triple)))
        predicciones_finales.append({"Franja": franja, "Números Sugeridos": numeros_str})
        
    st.table(pd.DataFrame(predicciones_finales))

# MÓDULO 3: BACKTESTING
def modulo_backtesting():
    st.header("🧪 Backtesting Interactivo")
    
    strategy_name_bt = st.selectbox(
        "¿Qué estrategia quieres simular?",
        ["Patrones de Corto Plazo", "Doble Estrategia (Rotación + D'Alembert)"],
        key="bt_strategy_selector"
    )
    
    params_bt = render_strategy_parameters(strategy_name_bt)

    if len(st.session_state.resultados) < 20:
        st.warning("⚠️ Necesitas al menos 20 resultados para hacer backtesting efectivo"); return

    df = pd.DataFrame(st.session_state.resultados)
    df["fecha"] = pd.to_datetime(df["fecha"]).dt.strftime('%Y-%m-%d')
    fechas_disponibles = sorted(df["fecha"].unique())
    col1, col2 = st.columns(2)
    default_idx = len(fechas_disponibles) - 11 if len(fechas_disponibles) > 10 else 0
    fecha_inicio = col1.selectbox("Fecha inicio", fechas_disponibles, index=default_idx)
    opciones_fin = [f for f in fechas_disponibles if f >= fecha_inicio]
    fecha_fin = col2.selectbox("Fecha fin", opciones_fin, index=len(opciones_fin)-1)
    
    if st.button("▶️ Ejecutar Backtesting con Parámetros Actuales"):
        with st.spinner(f"🧠 Simulado la '{strategy_name_bt}'... por favor espera."):
            df_test = df[(df["fecha"] >= fecha_inicio) & (df["fecha"] <= fecha_fin)]
            resultados_bt = []
            pesos_bt = {n: 0 for n in numeros}
            
            for fecha_str in sorted(df_test["fecha"].unique()):
                dia_df_real = df_test[df_test["fecha"] == fecha_str]
                df_historico = df[df["fecha"] < fecha_str]
                
                candidatos_dia = []
                if "Doble Estrategia" in strategy_name_bt:
                    rotaciones_dia = [n for n in numeros if not df_historico.empty and (rot := calcular_rotacion(df_historico, n)) is not None and rot <= params_bt['umbral_rotacion']]
                    if not rotaciones_dia: activos = sorted(pesos_bt, key=pesos_bt.get, reverse=True)
                    else: activos = sorted(rotaciones_dia, key=lambda n: pesos_bt.get(n, 0), reverse=True)
                    candidatos_dia = activos[:params_bt['numero_candidatos']]
                else: # Patrones de Corto Plazo
                    # <--- CORREGIDO: La llamada a la función ahora pasa los parámetros correctamente.
                    candidatos_dia = generar_prediccion_corto_plazo(
                        df_historico=df_historico.copy(),
                        fecha_actual_str=fecha_str,
                        ventana_dias=params_bt['ventana_dias'],
                        numero_candidatos=params_bt['numero_candidatos'],
                        tipo_ponderacion=params_bt['tipo_ponderacion']
                    )

                if len(candidatos_dia) < 3: continue

                for i, franja in enumerate(franjas):
                    indices = [(i + j) % len(candidatos_dia) for j in range(3)]
                    prediccion_triple = list(set([candidatos_dia[idx] for idx in indices]))
                    
                    real_row = dia_df_real[dia_df_real["franja"] == franja]
                    if not real_row.empty:
                        real = real_row.iloc[0]["numero"]
                        acierto = real in prediccion_triple
                        predicho_str = ", ".join(map(str, sorted(prediccion_triple)))
                        resultados_bt.append({"fecha": fecha_str, "franja": franja, "predicho": predicho_str, "real": real, "acierto": acierto})
                        
                        if "Doble Estrategia" in strategy_name_bt:
                            if acierto: pesos_bt[real] = max(0, pesos_bt.get(real, 0) - 1)
                            else: 
                                if prediccion_triple: pesos_bt[prediccion_triple[0]] += 1
                                
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
    pagina = st.sidebar.selectbox("Selecciona un módulo:", ["🔮 Predicciones", "🧪 Backtesting", "🔢 Ingreso de Datos"])
    if pagina == "🔮 Predicciones": modulo_prediccion()
    elif pagina == "🧪 Backtesting": modulo_backtesting()
    elif pagina == "🔢 Ingreso de Datos": modulo_ingreso()

if __name__ == "__main__":
    main()