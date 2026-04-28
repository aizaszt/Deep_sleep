import sys
import os
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# ── ПУТИ И ИМПОРТЫ ──────────────────────────────────────────────────────────
# Поднимаемся до /src, чтобы видеть папки models и файлы в корне src
src_path = str(Path(__file__).resolve().parent.parent)
if src_path not in sys.path:
    sys.path.append(src_path)

try:
    from models.chat import generate_sql, execute_sql, generate_answer
    from db_queries import get_data
except ImportError as e:
    st.error(f"Ошибка импорта: {e}. Проверьте структуру папок!")

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Deep Sleep AI", page_icon="🌙", layout="wide")

# Загрузка данных для контекста
df = get_data()

# ─────────────────────────────────────────────────────────────────────────────
# ЛОГИКА АНАЛИЗА (НОВАЯ СТРАНИЦА)
# ─────────────────────────────────────────────────────────────────────────────
def analyze_stress_level(sleep, quality, caffeine, work_hrs):
    # Упрощенная логика оценки (можно заменить на вызов ML-модели)
    score = 0
    if sleep < 6: score += 30
    if quality < 5: score += 20
    if caffeine > 300: score += 15
    if work_hrs > 9: score += 25
    
    if score > 70: return "Высокий 🔥", "Срочно сократите кофеин и увеличьте время сна. Риск выгорания максимален."
    if score > 40: return "Средний ⚠️", "Ваши показатели нестабильны. Рекомендуется наладить режим сна."
    return "Низкий ✅", "Отличные показатели! Продолжайте в том же духе."

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🧠 Deep Sleep Nav")
    page = st.radio("Перейти к:", ["📊 Дашборд", "🤖 AI Чат-бот", "🌡️ Анализ рисков"])
    st.divider()
    st.info(f"Записей в базе: {len(df)}")

# ─────────────────────────────────────────────────────────────────────────────
# СТРАНИЦА 3: АНАЛИЗ РИСКОВ (ВАШ ЗАПРОС)
# ─────────────────────────────────────────────────────────────────────────────
if page == "🌡️ Анализ рисков":
    st.header("🌡️ Индивидуальный прогноз стресса", divider="orange")
    st.write("Настройте метрики ниже, чтобы ИИ проанализировал ваш возможный уровень стресса.")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Ваши показатели")
        s_sleep = st.slider("Сон (часы)", 3.0, 12.0, 7.0)
        s_qual = st.slider("Качество сна (1-10)", 1, 10, 6)
        s_caff = st.select_slider("Кофеин (мг)", options=[0, 50, 100, 200, 300, 400, 500], value=100)
        s_work = st.slider("Рабочие часы", 0, 16, 8)

    with col2:
        level, advice = analyze_stress_level(s_sleep, s_qual, s_caff, s_work)
        
        st.subheader("Результат анализа")
        st.metric("Уровень стресса", level)
        
        st.warning(f"**Совет:** {advice}")
        
        # Визуализация для наглядности
        gauge_df = pd.DataFrame({"Метрика": ["Сон", "Качество", "Работа"], 
                                 "Значение": [s_sleep, s_qual, s_work]})
        fig = px.bar(gauge_df, x="Метрика", y="Значение", color="Метрика", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# СТРАНИЦА 2: AI ЧАТ-БОТ
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🤖 AI Чат-бот":
    st.header("🤖 Чат с данными сна", divider="green")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Например: 'Какой средний пульс у тех, кто пьет много кофе?'")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Генерирую SQL и ищу ответ..."):
                sql = generate_sql(user_input)
                results = execute_sql(sql)
                answer = generate_answer(user_input, sql, results)
                
                with st.expander("Техническая информация (SQL)"):
                    st.code(sql, language="sql")
                
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})

# ─────────────────────────────────────────────────────────────────────────────
# СТРАНИЦА 1: ДАШБОРД
# ─────────────────────────────────────────────────────────────────────────────
else:
    st.header("📊 Общий обзор данных", divider="blue")
    m1, m2, m3 = st.columns(3)
    m1.metric("Ср. сон", f"{df['sleep'].mean():.1f} ч")
    m2.metric("Ср. стресс", f"{df['stress'].mean():.1f}/10")
    m3.metric("Кофеин", f"{df['caffeine'].mean():.0f} мг")
    
    fig_hist = px.histogram(df, x="age", color="sleep_disorder_risk", barmode="group", template="plotly_dark")
    st.plotly_chart(fig_hist, use_container_width=True)