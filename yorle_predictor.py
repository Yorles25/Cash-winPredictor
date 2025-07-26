import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import math
from collections import Counter

# --- Configuración Inicial y Variables Globales ---
st.set_page_config(
    page_title="Cash winPredictor v9.0",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Cash winPredictor v9.0 - Motor Reactivo (Sorteo a Sorteo)")
st.sidebar.header("📋 Navegación")

franjas = ["mañana", "mediodía", "tarde", "noche", "madrugada"]
DATA_FILE = "resultados_guardados.json"

# --- Funciones de Datos ---
def cargar_datos():
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            for record in data:
                if 'fecha' in record: record['fecha'] = str(record['fecha']).split('T')[0]
            return data
    except (FileNotFoundError, json.JSONDecodeError): return []

def guardar_datos(datos):
    with open(DATA_FILE, 'w') as f: json.dump(datos, f, indent=4)

if "resultados" not in st.session_state: st.session_state.resultados = cargar_datos()
if "pesos" not in st.session_state: st.session_state.pesos = {}

# --- Funciones de Lógica de Estrategias ---
def calcular_rotacion(df, numero):
    fechas = df[df["numero"] == numero]["fecha"].unique()
    fechas = sorted(pd.to_datetime(fechas))
    if len(fechas) < 2: return None
    diferencias = [(fechas[i+1] - fechas[i]).days for i in range(len(fechas)-1)]
    return round(sum(diferencias) / len(diferencias), 2) if diferencias else None

def generar_prediccion_corto_plazo(df_historico, fecha_actual_str, ventana_dias, num_candidatos, tipo_ponderacion):
    if df_historico.empty: return []
    try:
        df_historico_copy = df_historico.copy()
        df_historico_copy["fecha_dt"] = pd.to_datetime(df_historico_copy["fecha"]).dt.date
        fecha_actual = pd.to_datetime(fecha_actual_str).date()
        hace_x_dias = fecha_actual - timedelta(days=ventana_dias)
    except Exception: return []
    df_filtrado = df_historico_copy[df_historico_copy["fecha_dt"] >= hace_x_dias].copy()
    if df_filtrado.empty: return []
    if tipo_ponderacion == 'Exponencial':
        def ponderacion(fecha):
            dias_pasados = (fecha_actual - fecha).days
            return math.ceil(1.5 ** (ventana_dias - dias_pasados))
    else:
        def ponderacion(fecha):
            dias_pasados = (fecha_actual - fecha).days
            return max(1, (ventana_dias + 1) - dias_pasados)
    df_filtrado["peso"] = df_filtrado["fecha_dt"].apply(ponderacion)
    puntuaciones = df_filtrado.groupby("numero")["peso"].sum()
    return puntuaciones.sort_values(ascending=False).head(num_candidatos).index.tolist()

def calcular_puntuacion_sorpresa(numero, df_historico, fecha_actual):
    apariciones = df_historico[df_historico['numero'] == numero]
    if apariciones.empty: return 100
    ultima_aparicion = pd.to_datetime(apariciones['fecha']).max().date()
    return (fecha_actual.date() - ultima_aparicion).days

def calcular_puntuacion_consistencia(numero, df_historico):
    total_sorteos = len(df_historico)
    if total_sorteos == 0: return 0
    return (len(df_historico[df_historico['numero'] == numero]) / total_sorteos) * 100

def generar_prediccion_detective(df_historico, fecha_str, params):
    fecha_actual = pd.to_datetime(fecha_str)
    todos_los_numeros = df_historico['numero'].unique()
    puntuaciones_finales = {}
    if df_historico.empty: return []
    puntuaciones_racha = generar_prediccion_corto_plazo(df_historico.copy(), fecha_str, 10, len(todos_los_numeros), 'Exponencial')
    puntuaciones_racha_dict = {num: score for score, num in enumerate(reversed(puntuaciones_racha), 1)}
    for numero in todos_los_numeros:
        p_racha = puntuaciones_racha_dict.get(numero, 0)
        p_sorpresa = calcular_puntuacion_sorpresa(numero, df_historico, fecha_actual)
        p_consistencia = calcular_puntuacion_consistencia(numero, df_historico)
        score = (p_racha * params.get('peso_racha', 1.0) +
                 p_sorpresa * params.get('peso_sorpresa', 1.0) +
                 p_consistencia * params.get('peso_consistencia', 1.0))
        puntuaciones_finales[numero] = score
    candidatos_ordenados = sorted(puntuaciones_finales, key=puntuaciones_finales.get, reverse=True)
    return candidatos_ordenados[:params.get('numero_candidatos', 7)]

@st.cache_data
def build_affinity_map(_df):
    affinity_map = {}
    df_sorted = _df.sort_values(by=['fecha', 'franja_order']).reset_index(drop=True)
    for i in range(len(df_sorted) - 1):
        current_num = df_sorted.loc[i, 'numero']
        next_num = df_sorted.loc[i + 1, 'numero']
        if current_num not in affinity_map: affinity_map[current_num] = []
        affinity_map[current_num].append(next_num)
    for num, next_nums in affinity_map.items():
        affinity_map[num] = Counter(next_nums)
    return affinity_map

def generar_prediccion_afinidad(df_historico, params):
    if len(df_historico) < 2: return []
    affinity_map = build_affinity_map(df_historico.copy())
    last_num = df_historico.sort_values(by=['fecha', 'franja_order']).iloc[-1]['numero']
    if last_num not in affinity_map: return []
    followers = affinity_map[last_num]
    confiables = {num: count for num, count in followers.items() if count >= params.get('umbral_confianza', 2)}
    if not confiables: return []
    return sorted(confiables, key=confiables.get, reverse=True)[:params.get('numero_candidatos', 5)]

def generar_prediccion_persistencia(df_historico, params):
    retraso = params.get('retraso_sorteos', 5)
    if len(df_historico) < retraso: return []
    numeros_base = df_historico.tail(retraso)['numero'].unique().tolist()
    return numeros_base

# --- Funciones Auxiliares de la Interfaz ---
def render_strategy_parameters(strategy_name, key_prefix):
    st.sidebar.markdown("---"); st.sidebar.header(f"⚙️ Parámetros: {strategy_name}")
    params = {}
    if "Persistencia" in strategy_name:
        params['retraso_sorteos'] = st.sidebar.slider("Usar últimos N sorteos como base", 1, 10, 5, key=f"{key_prefix}_rs_pers")
    elif "Afinidad" in strategy_name:
        params['numero_candidatos'] = st.sidebar.number_input("Candidatos a Mostrar", 3, 20, 5, 1, key=f"{key_prefix}_nc_afinidad")
        params['umbral_confianza'] = st.sidebar.number_input("Umbral de Confianza", 1, 10, 2, 1, key=f"{key_prefix}_uc_afinidad")
    elif "Detective" in strategy_name:
        params['numero_candidatos'] = st.sidebar.number_input("Candidatos", 3, 20, 5, 1, key=f"{key_prefix}_nc_detective")
        params['peso_racha'] = st.sidebar.number_input("🔥 Peso Racha", 0.0, 5.0, 1.5, 0.1, "%.1f", key=f"{key_prefix}_pr")
        params['peso_sorpresa'] = st.sidebar.number_input("💣 Peso Sorpresa", 0.0, 5.0, 0.7, 0.1, "%.1f", key=f"{key_prefix}_ps")
        params['peso_consistencia'] = st.sidebar.number_input("🛡️ Peso Consistencia", 0.0, 5.0, 0.3, 0.1, "%.1f", key=f"{key_prefix}_pc")
    elif "Doble Estrategia" in strategy_name:
        params['umbral_rotacion'] = st.sidebar.slider("Umbral Rotación (días)", 1, 15, 4, key=f"{key_prefix}_ur")
        params['numero_candidatos'] = st.sidebar.number_input("Candidatos", 3, 20, 7, 1, key=f"{key_prefix}_nc_doble")
    elif "Patrones de Corto Plazo" in strategy_name:
        params['ventana_dias'] = st.sidebar.number_input("Ventana (días)", 3, 30, 10, 1, key=f"{key_prefix}_vd")
        params['numero_candidatos'] = st.sidebar.number_input("Candidatos", 3, 20, 5, 1, key=f"{key_prefix}_nc_corto")
        params['tipo_ponderacion'] = st.sidebar.selectbox("Ponderación", ["Exponencial", "Lineal"], 0, key=f"{key_prefix}_tp")
    return params

def get_next_sorteo(df):
    if df.empty: return "mañana", datetime.today().strftime("%Y-%m-%d")
    df_sorted = df.sort_values(by=['fecha', 'franja_order'])
    last_sorteo = df_sorted.iloc[-1]
    last_franja_index = franjas.index(last_sorteo['franja'])
    
    if last_franja_index == len(franjas) - 1:
        next_franja = franjas[0]
        next_date = (pd.to_datetime(last_sorteo['fecha']) + timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        next_franja = franjas[last_franja_index + 1]
        next_date = last_sorteo['fecha']
    return next_franja, next_date

# --- Módulos de la Aplicación ---
def modulo_prediccion():
    st.header("🔮 Generador de Predicciones")
    strategy_options = ["Estrategia de Afinidad 🤝", "Estrategia de Persistencia (Eco) 📢", "Estrategia del Detective 🕵️", "Patrones de Corto Plazo 📈", "Doble Estrategia 🔁"]
    strategy_name = st.selectbox("¿Qué tipo de análisis deseas usar?", strategy_options)
    params = render_strategy_parameters(strategy_name, key_prefix='pred')
    
    if not st.session_state.resultados:
        st.warning("⚠️ No hay datos suficientes."); return
    
    df = pd.DataFrame(st.session_state.resultados)
    franja_map = {franja: i for i, franja in enumerate(franjas)}
    df['franja_order'] = df['franja'].map(franja_map)

    next_franja, next_date = get_next_sorteo(df)
    st.subheader(f"🎯 Predicción para el próximo sorteo: {next_franja.capitalize()} ({next_date})")

    candidatos = []
    if "Afinidad" in strategy_name: candidatos = generar_prediccion_afinidad(df.copy(), params)
    elif "Persistencia" in strategy_name: candidatos = generar_prediccion_persistencia(df.copy(), params)
    elif "Detective" in strategy_name: candidatos = generar_prediccion_detective(df.copy(), next_date, params)
    elif "Doble Estrategia" in strategy_name:
        numeros_en_datos = df['numero'].unique()
        rotaciones = {n: calcular_rotacion(df, n) for n in numeros_en_datos}
        activos = [n for n, r in rotaciones.items() if r is not None and r <= params['umbral_rotacion']]
        if not activos: activos = list(numeros_en_datos)
        candidatos_ordenados = sorted(activos, key=lambda n: st.session_state.pesos.get(n, 0), reverse=True)
        candidatos = candidatos_ordenados[:params['numero_candidatos']]
    else: # Corto Plazo
        candidatos = generar_prediccion_corto_plazo(df.copy(), next_date, params['ventana_dias'], params['numero_candidatos'], params['tipo_ponderacion'])
        
    if not candidatos or len(candidatos) < 3:
        st.error("La estrategia no pudo generar suficientes candidatos. Prueba a ajustar los parámetros.")
        return
    
    prediccion_final = ", ".join(map(str, sorted(candidatos[:3])))
    st.metric("Números Sugeridos", prediccion_final)

def modulo_backtesting():
    st.header("🧪 Backtesting Interactivo (Análisis por Sorteo)")
    strategy_options_bt = ["Estrategia de Afinidad 🤝", "Estrategia de Persistencia (Eco) 📢", "Estrategia del Detective 🕵️", "Patrones de Corto Plazo 📈", "Doble Estrategia 🔁"]
    strategy_name_bt = st.selectbox("¿Qué estrategia quieres simular?", strategy_options_bt, key="bt_strategy_selector")
    params_bt = render_strategy_parameters(strategy_name_bt, key_prefix='bt')
    
    if len(st.session_state.resultados) < 20:
        st.warning("⚠️ Necesitas al menos 20 resultados."); return
        
    df = pd.DataFrame(st.session_state.resultados)
    df["fecha"] = pd.to_datetime(df["fecha"]).dt.strftime('%Y-%m-%d')
    franja_map = {franja: i for i, franja in enumerate(franjas)}
    df['franja_order'] = df['franja'].map(franja_map)
    df_sorted = df.sort_values(by=['fecha', 'franja_order']).reset_index(drop=True)
    
    fechas_disponibles = sorted(df_sorted["fecha"].unique())
    col1, col2 = st.columns(2)
    default_idx = len(fechas_disponibles) - 11 if len(fechas_disponibles) > 10 else 0
    fecha_inicio = col1.selectbox("Fecha inicio", fechas_disponibles, index=default_idx)
    opciones_fin = [f for f in fechas_disponibles if f >= fecha_inicio]
    fecha_fin = col2.selectbox("Fecha fin", opciones_fin, index=len(opciones_fin)-1)
    
    if st.button("▶️ Ejecutar Backtesting Reactivo"):
        with st.spinner(f"🧠 Simulado la '{strategy_name_bt}' sorteo a sorteo..."):
            
            try:
                start_index = df_sorted[df_sorted['fecha'] == fecha_inicio].index.min()
                end_index = df_sorted[df_sorted['fecha'] == fecha_fin].index.max()
            except ValueError:
                st.error("El rango de fechas seleccionado no contiene datos. Por favor, elige otras fechas.")
                return

            resultados_bt = []
            
            todos_numeros = df_sorted['numero'].unique()
            pesos_bt = {n: 0 for n in todos_numeros}
            sorteos_sin_acertar = {n: 0 for n in todos_numeros}
            sorteos_desde_ultimo_acierto_general = 0
            
            for i in range(start_index, end_index + 1):
                sorteo_actual = df_sorted.loc[i]
                df_historico = df_sorted.iloc[:i]
                
                candidatos = []
                if "Afinidad" in strategy_name_bt: candidatos = generar_prediccion_afinidad(df_historico.copy(), params_bt)
                elif "Persistencia" in strategy_name_bt: candidatos = generar_prediccion_persistencia(df_historico.copy(), params_bt)
                elif "Detective" in strategy_name_bt: candidatos = generar_prediccion_detective(df_historico.copy(), sorteo_actual['fecha'], params_bt)
                elif "Doble Estrategia" in strategy_name_bt:
                    numeros_en_historico = df_historico['numero'].unique()
                    rotaciones_dia = [n for n in numeros_en_historico if (rot := calcular_rotacion(df_historico, n)) is not None and rot <= params_bt['umbral_rotacion']]
                    if not rotaciones_dia: activos = sorted(pesos_bt, key=lambda k: pesos_bt.get(k, 0), reverse=True)
                    else: activos = sorted(rotaciones_dia, key=lambda n: pesos_bt.get(n, 0), reverse=True)
                    candidatos = activos[:params_bt['numero_candidatos']]
                else: # Corto Plazo
                    candidatos = generar_prediccion_corto_plazo(df_historico.copy(), sorteo_actual['fecha'], params_bt['ventana_dias'], params_bt['numero_candidatos'], params_bt['tipo_ponderacion'])
                
                if not candidatos: continue

                prediccion_triple = sorted(candidatos[:3])
                real = int(sorteo_actual["numero"])
                acierto = real in prediccion_triple
                
                sorteos_espera = sorteos_sin_acertar.get(real, 0)
                racha_general = ""
                if acierto:
                    racha_general = sorteos_desde_ultimo_acierto_general
                    sorteos_desde_ultimo_acierto_general = 0
                    sorteos_sin_acertar[real] = 0
                else:
                    sorteos_desde_ultimo_acierto_general += 1
                
                for n in sorteos_sin_acertar: sorteos_sin_acertar[n] += 1

                resultados_bt.append({
                    "fecha": sorteo_actual['fecha'], "franja": sorteo_actual['franja'], "predicho": ", ".join(map(str, prediccion_triple)), 
                    "real": real, "acierto": acierto, "sorteos_espera": sorteos_espera, "racha_general": racha_general
                })
                
                if "Doble Estrategia" in strategy_name_bt and prediccion_triple:
                    if acierto: pesos_bt[real] = max(0, pesos_bt.get(real, 0) - 1)
                    else: pesos_bt[prediccion_triple[0]] = pesos_bt.get(prediccion_triple[0], 0) + 1
                                    
            st.session_state.bt_df = pd.DataFrame(resultados_bt) if resultados_bt else None

    if "bt_df" in st.session_state and st.session_state.bt_df is not None:
        bt_df = st.session_state.bt_df
        total=len(bt_df); aciertos=bt_df["acierto"].sum(); porcentaje=round((aciertos/total)*100,2) if total>0 else 0
        st.subheader(f"Resultados para: {st.session_state.get('bt_strategy_selector')}")
        m_col1,m_col2,m_col3=st.columns(3)
        m_col1.metric("Predicciones",total); m_col2.metric("Aciertos",aciertos); m_col3.metric("Precisión",f"{porcentaje}%")
        st.markdown("---"); st.subheader("📋 Detalle de Resultados (Últimos 50)")
        enc_cols=st.columns([2,2,2,1,2,2,2])
        enc_cols[0].write("**Fecha**"); enc_cols[1].write("**Franja**"); enc_cols[2].write("**Predicción**")
        enc_cols[3].write("**Real**"); enc_cols[4].write("**Status**"); enc_cols[5].write("**Espera (Ind.)**"); enc_cols[6].write("**Racha (Gral.)**")
        for _, row in bt_df.tail(50).iloc[::-1].iterrows():
            with st.container():
                res_cols = st.columns([2, 2, 2, 1, 2, 2, 2])
                res_cols[0].text(row['fecha']); res_cols[1].text(row['franja'].capitalize()); res_cols[2].markdown(f"**{row['predicho']}**"); res_cols[3].markdown(f"**{row['real']}**")
                if row['acierto']:
                    res_cols[4].success("✅ Acierto")
                    res_cols[5].info(f"{row['sorteos_espera']} sorteos")
                    res_cols[6].warning(f"{row['racha_general']} sorteos")
                else:
                    res_cols[4].error("❌ Fallo")
                    res_cols[5].text(""); res_cols[6].text("")
                st.divider()
        st.subheader("📈 Evolución de Aciertos Diarios")
        aciertos_por_dia = bt_df.groupby("fecha")["acierto"].sum().reset_index()
        st.line_chart(aciertos_por_dia.set_index("fecha")["acierto"])
        st.subheader("🎯 Rendimiento por Franja Horaria")
        rend_franja = bt_df.groupby("franja").agg(aciertos_totales=('acierto', 'sum'), predicciones_totales=('acierto', 'count')).reset_index()
        rend_franja['precision'] = (rend_franja['aciertos_totales'] / rend_franja['predicciones_totales']).round(3) * 100
        st.dataframe(rend_franja.style.format({'precision': '{:.1f}%'}))

def main():
    pagina = st.sidebar.selectbox("Selecciona un módulo:", ["🔮 Predicciones", "🧪 Backtesting", "🔢 Ingreso de Datos"])
    if pagina == "🔮 Predicciones": modulo_prediccion()
    elif pagina == "🧪 Backtesting": modulo_backtesting()
    elif pagina == "🔢 Ingreso de Datos": modulo_ingreso()

def modulo_ingreso():
    st.header("🔢 Ingreso y Gestión de Resultados")
    st.subheader("🚀 Carga Masiva desde Archivo CSV")
    uploaded_file=st.file_uploader("Sube tu archivo con el historial (formato: fecha,franja,numero)", type="csv")
    if uploaded_file is not None:
        try:
            df_cargado=pd.read_csv(uploaded_file)
            nuevos_resultados=df_cargado.to_dict('records')
            st.session_state.resultados=nuevos_resultados
            guardar_datos(st.session_state.resultados)
            st.success(f"✅ ¡Se cargaron {len(nuevos_resultados)} resultados del archivo!")
            st.rerun()
        except Exception as e: st.error(f"❌ Error al procesar el archivo: {e}")
    st.markdown("---")
    st.subheader("✍️ Ingreso Manual de Resultados")
    col1,col2,col3=st.columns(3)
    with col1: fecha=st.date_input("Fecha del sorteo", value=datetime.today())
    with col2: franja=st.selectbox("Franja horaria", franjas)
    with col3: numero_ganador=st.number_input("Número ganador", min_value=0, step=1)
    if st.button("➕ Agregar resultado"):
        nuevo_resultado={"fecha": fecha.strftime("%Y-%m-%d"), "franja": franja, "numero": numero_ganador}
        if nuevo_resultado not in st.session_state.resultados:
            st.session_state.resultados.append(nuevo_resultado)
            guardar_datos(st.session_state.resultados)
            st.success("✅ Resultado agregado correctamente")
            st.rerun()
        else: st.warning("⚠️ Este resultado ya existe.")
    st.subheader("📋 Últimos Resultados")
    if st.session_state.resultados:
        enc_cols=st.columns([2,2,1,1])
        enc_cols[0].write("**Fecha**"); enc_cols[1].write("**Franja**"); enc_cols[2].write("**Número**"); enc_cols[3].write("**Acción**")
        st.markdown("---")
        for i in reversed(range(len(st.session_state.resultados))):
            if len(st.session_state.resultados)-i > 10: break
            resultado=st.session_state.resultados[i]
            row_cols=st.columns([2,2,1,1])
            row_cols[0].text(resultado["fecha"]); row_cols[1].text(resultado["franja"]); row_cols[2].text(resultado["numero"])
            if row_cols[3].button("❌", key=f"delete_button_{i}"):
                del st.session_state.resultados[i]
                guardar_datos(st.session_state.resultados)
                st.rerun()
    else: st.info("Aún no hay resultados para mostrar.")

if __name__ == "__main__":
    main()