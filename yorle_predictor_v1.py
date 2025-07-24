import streamlit as st
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import json

# --- Configuración Inicial y Variables Globales ---
st.set_page_config(
    page_title="Cash winPredictor",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 Cash winPredictor - Sistema Inteligente v2.0")
st.sidebar.header("📋 Navegación")

franjas = ["mañana", "mediodía", "tarde", "noche", "madrugada"]
numeros = list(range(1, 10))
DATA_FILE = "resultados_guardados.json"

# --- Funciones para Guardar y Cargar Datos ---
def cargar_datos():
    """Carga los resultados desde un archivo JSON."""
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def guardar_datos(datos):
    """Guarda los resultados en un archivo JSON."""
    with open(DATA_FILE, 'w') as f:
        json.dump(datos, f, indent=4)

# --- Inicialización del Estado de la Sesión ---
if "resultados" not in st.session_state:
    st.session_state.resultados = cargar_datos()
if "pesos" not in st.session_state:
    # <-- CAMBIO 1: Inicializar los pesos en 0
    st.session_state.pesos = {n: 0 for n in numeros}
if "pendientes" not in st.session_state:
    st.session_state.pendientes = []

# --- Funciones de Lógica ---
def calcular_rotacion(df, numero):
    fechas = df[df["numero"] == numero]["fecha"].unique()
    fechas = sorted(pd.to_datetime(fechas))
    if len(fechas) < 2:
        return None
    diferencias = [(fechas[i+1] - fechas[i]).days for i in range(len(fechas)-1)]
    return round(sum(diferencias) / len(diferencias), 2)

# --- Módulos de la Aplicación ---

# MÓDULO 1: INGRESO DE RESULTADOS
def modulo_ingreso():
    st.header("🔢 Ingreso y Gestión de Resultados")

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

# MÓDULO 2: ANÁLISIS DE ROTACIÓN
def modulo_rotacion():
    st.header("🔁 Análisis de Rotación")
    if not st.session_state.resultados:
        st.warning("⚠️ No hay datos suficientes para calcular rotación"); return None
    df = pd.DataFrame(st.session_state.resultados)
    rotaciones = [{"Número": n, "Rotación (días)": calcular_rotacion(df, n)} for n in numeros]
    rotaciones = [r for r in rotaciones if r["Rotación (días)"] is not None]
    if rotaciones:
        rot_df = pd.DataFrame(rotaciones)
        st.dataframe(rot_df)
        # <-- CAMBIO 2: Umbral de rotación por defecto cambiado a 4.
        umbral = st.slider("Umbral de rotación activa", 1, 10, 4)
        activos = rot_df[rot_df["Rotación (días)"] <= umbral]
        st.subheader("🎯 Números Activos")
        if not activos.empty:
            st.success(f"Números con rotación ≤ {umbral} días:"); st.table(activos)
        else:
            st.info("No hay números activos con este umbral")
        return activos
    return None

# MÓDULO 3: GENERADOR DE PREDICCIÓN
def modulo_prediccion(activos):
    st.header("🔮 Generador de Predicción D'Alembert")
    if activos is None or activos.empty:
        st.warning("⚠️ No hay números activos para generar predicciones"); return
    candidatos = activos["Número"].tolist()
    candidatos_ordenados = sorted(candidatos, key=lambda n: st.session_state.pesos[n], reverse=True)
    mejores_candidatos = candidatos_ordenados[:5]
    if not mejores_candidatos:
        st.warning("⚠️ No hay candidatos suficientes."); return
    prediccion = []
    for i, franja in enumerate(franjas):
        num_predicho = mejores_candidatos[i % len(mejores_candidatos)]
        prediccion.append({
            "Franja": franja, "Número Sugerido": num_predicho,
            "Peso D'Alembert": st.session_state.pesos[num_predicho]
        })
    pred_df = pd.DataFrame(prediccion)
    st.subheader("🎯 Predicciones Sugeridas para Hoy"); st.table(pred_df)

    b_col1, b_col2 = st.columns(2)
    if b_col1.button("💾 Guardar Predicción"):
        hoy = datetime.today().strftime("%Y-%m-%d")
        for _, row in pred_df.iterrows():
            st.session_state.pendientes.append({
                "fecha": hoy, "franja": row["Franja"],
                "numero_predicho": row["Número Sugerido"], "peso": row["Peso D'Alembert"]
            })
        st.success("✅ Predicción guardada")
    if b_col2.button("🔄 Actualizar Pesos"):
        df = pd.DataFrame(st.session_state.resultados)
        if not df.empty:
            for numero in numeros:
                # Lógica de actualización de pesos D'Alembert simplificada
                # Esta parte podría necesitar una revisión más profunda si quisiéramos
                # una actualización de pesos manual compleja.
                # Por ahora, la lógica principal está en el backtesting.
                # Aquí simplemente simulamos un comportamiento basado en apariciones recientes.
                apariciones = len(df.tail(20)[df["numero"] == numero])
                if apariciones > 4: # Si ha salido mucho, bajamos peso
                    st.session_state.pesos[numero] = max(0, st.session_state.pesos[numero] - 1)
                elif apariciones < 2: # Si no ha salido, subimos peso
                    st.session_state.pesos[numero] += 1
            st.success("✅ Pesos actualizados según resultados recientes")
        else:
            st.warning("No hay resultados para actualizar pesos.")

# MÓDULO 4: BACKTESTING
def modulo_backtesting():
    st.header("🧪 Backtesting Interactivo")
    if len(st.session_state.resultados) < 20:
        st.warning("⚠️ Necesitas al menos 20 resultados para hacer backtesting efectivo"); return
    df = pd.DataFrame(st.session_state.resultados)
    fechas_disponibles = sorted(df["fecha"].unique())
    col1, col2 = st.columns(2)
    default_idx = len(fechas_disponibles) - 11 if len(fechas_disponibles) > 10 else 0
    fecha_inicio = col1.selectbox("Fecha inicio", fechas_disponibles, index=default_idx)
    opciones_fin = [f for f in fechas_disponibles if f >= fecha_inicio]
    fecha_fin = col2.selectbox("Fecha fin", opciones_fin, index=len(opciones_fin)-1)

    if st.button("▶️ Ejecutar Backtesting"):
        with st.spinner("🧠 Simulado estrategia... por favor espera."):
            df_test = df[(df["fecha"] >= fecha_inicio) & (df["fecha"] <= fecha_fin)]
            resultados_bt = []
            # <-- CAMBIO 1: Inicializar los pesos en 0 también para el backtesting
            pesos_bt = {n: 0 for n in numeros}
            for fecha in sorted(df_test["fecha"].unique()):
                dia_df = df_test[df_test["fecha"] == fecha]
                df_historico = df[df["fecha"] < fecha]
                
                # <-- CAMBIO 2: Umbral de rotación fijado a 4 en el backtesting.
                rotaciones_dia = [n for n in numeros if not df_historico.empty and (rot := calcular_rotacion(df_historico, n)) is not None and rot <= 4]
                
                # Si no hay activos, predecimos usando los de mayor peso sin filtro de rotación
                if not rotaciones_dia:
                    rotaciones_dia = sorted(pesos_bt, key=pesos_bt.get, reverse=True)

                for franja in franjas:
                    if rotaciones_dia:
                        predicho = max(rotaciones_dia, key=lambda n: pesos_bt[n])
                        real_row = dia_df[dia_df["franja"] == franja]
                        if not real_row.empty:
                            real = real_row.iloc[0]["numero"]
                            acierto = (predicho == real)
                            resultados_bt.append({"fecha": fecha, "franja": franja, "predicho": predicho, "real": real, "acierto": acierto})
                            
                            # <-- CAMBIO 3: La regla de decremento ahora puede llegar a 0
                            if acierto:
                                pesos_bt[predicho] = max(0, pesos_bt[predicho] - 1)
                            else:
                                pesos_bt[predicho] += 1
            st.session_state.bt_df = pd.DataFrame(resultados_bt) if resultados_bt else None

    if "bt_df" in st.session_state and st.session_state.bt_df is not None:
        bt_df = st.session_state.bt_df
        total = len(bt_df); aciertos = bt_df["acierto"].sum(); porcentaje = round((aciertos / total) * 100, 2) if total > 0 else 0
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

        st.subheader("📈 Evolución de Aciertos")
        aciertos_por_dia = bt_df.groupby("fecha")["acierto"].sum().reset_index()
        st.line_chart(aciertos_por_dia.set_index("fecha")["acierto"])

        st.subheader("🎯 Rendimiento por Franja")
        rend_franja = bt_df.groupby("franja").agg(aciertos_totales=('acierto', 'sum'), predicciones_totales=('acierto', 'count')).reset_index()
        rend_franja['precision'] = (rend_franja['aciertos_totales'] / rend_franja['predicciones_totales']).round(3)
        st.dataframe(rend_franja)

# MÓDULO 5: VISUALIZACIÓN DE RENDIMIENTO
def modulo_graficos():
    st.header("📊 Gráficos de Rendimiento")
    if not st.session_state.resultados:
        st.warning("⚠️ No hay datos para visualizar"); return
    df = pd.DataFrame(st.session_state.resultados)
    st.subheader("🔢 Frecuencia de Números"); st.bar_chart(df.groupby("numero").size().sort_index())
    st.subheader("⏰ Actividad por Franja"); st.bar_chart(df.groupby("franja").size())
    st.subheader("📅 Tendencia Temporal"); df["fecha"] = pd.to_datetime(df["fecha"]); st.line_chart(df.groupby("fecha").size())

# --- INTERFAZ PRINCIPAL Y ARRANQUE ---
def main():
    pagina = st.sidebar.selectbox("Selecciona un módulo:", [
        "🔢 Ingreso de Datos", "🔁 Análisis de Rotación",
        "🔮 Predicción D'Alembert", "🧪 Backtesting", "📊 Gráficos y Análisis"
    ])

    if pagina == "🔢 Ingreso de Datos": modulo_ingreso()
    elif pagina == "🔁 Análisis de Rotación":
        # Se guarda el resultado en session_state para que otros módulos lo usen
        st.session_state.activos = modulo_rotacion()
    elif pagina == "🔮 Predicción D'Alembert":
        # Asegurarse de que el análisis de rotación se ha ejecutado al menos una vez
        if "activos" not in st.session_state:
            st.session_state.activos = modulo_rotacion() # Ejecutarlo si no existe
        modulo_prediccion(st.session_state.get("activos"))
    elif pagina == "🧪 Backtesting": modulo_backtesting()
    elif pagina == "📊 Gráficos y Análisis": modulo_graficos()

if __name__ == "__main__":
    main()