import os
import pymysql
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from groq import Groq
from dotenv import load_dotenv

# ── CONFIG ─────────────────────────────────────────────────────────────────────
load_dotenv()
st.set_page_config(page_title="Sleep Analytics AI", page_icon="🌙", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0b0e14; color: white; }
    section[data-testid="stSidebar"] { background-color: #0d1117; }
    .metric-card {
        background: #161b22;
        padding: 18px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #30363d;
    }
    .metric-value { font-size: 26px; font-weight: bold; color: #79c0ff; }
    .metric-label { font-size: 11px; color: #8b949e; text-transform: uppercase; margin-top: 4px; }
    div[data-testid="stChatMessage"] {
        background-color: #161b22;
        border: 1px solid #21262d;
        border-radius: 10px;
        padding: 4px;
    }
</style>
""", unsafe_allow_html=True)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── DB ─────────────────────────────────────────────────────────────────────────
def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )

SCHEMA = """
participants(participant_id, age, gender, bmi, chronotype, shift_work)
sleep_sessions(session_id, Participants_participants_id, sleep_duration_hrs, sleep_quality_score, sleep_latency_mins, wake_episodes)
lifestylehabits(id, Participants_participants_id, caffeine_mg_day, alcohol_units_week, screen_time_mins, stress_level)

JOIN условия:
  sleep_sessions.Participants_participants_id = participants.participant_id
  lifestylehabits.Participants_participants_id = participants.participant_id
"""

# ── AI HELPERS ─────────────────────────────────────────────────────────────────
def ask_ai(prompt: str, system_prompt: str) -> str:
    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1024
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"AI Error: {e}"


def clean_sql(raw: str) -> str:
    sql = raw.strip()
    # убираем ```sql ... ```
    if "```" in sql:
        lines = [l for l in sql.split("\n") if not l.strip().startswith("```")]
        sql = " ".join(lines).strip()
    # берём только часть начиная с SELECT
    up = sql.upper()
    if "SELECT" in up:
        sql = sql[up.find("SELECT"):]
    # исправляем частые галлюцинации модели
    fixes = {
        "caffeine_mg_day":   "caffeine_mg_day",   # правильное имя — оставляем
        "quality_of_sleep":  "sleep_quality_score",
        "caffeine_per_day":  "caffeine_mg_day",
        "alcohol_per_week":  "alcohol_units_week",
    }
    for wrong, right in fixes.items():
        sql = sql.replace(wrong, right)
    return sql.strip()


def run_sql(query: str):
    """Выполняет SQL, возвращает (DataFrame | None, error | None)."""
    try:
        conn = get_connection()
        with conn.cursor() as c:
            c.execute(query)
            rows = c.fetchall()
        conn.close()
        if not rows:
            return pd.DataFrame(), None
        return pd.DataFrame(rows), None
    except Exception as e:
        return None, str(e)


def auto_chart(df: pd.DataFrame):
    """Автоматически выбирает тип графика."""
    if df is None or df.empty or len(df) < 2:
        return None
    num = df.select_dtypes("number").columns.tolist()
    cat = df.select_dtypes("object").columns.tolist()

    if cat and num:
        fig = px.bar(df, x=cat[0], y=num[0],
                     color=cat[0],
                     color_discrete_sequence=px.colors.sequential.Blues_r,
                     template="plotly_dark")
    elif len(num) >= 2:
        fig = px.scatter(df, x=num[0], y=num[1], trendline="ols",
                         color_discrete_sequence=["#79c0ff"],
                         template="plotly_dark")
    elif len(num) == 1:
        fig = px.histogram(df, x=num[0],
                           color_discrete_sequence=["#388bfd"],
                           template="plotly_dark")
    else:
        return None

    fig.update_layout(height=300, margin=dict(t=30, b=10),
                      paper_bgcolor="rgba(0,0,0,0)")
    return fig


# ── HEADER ─────────────────────────────────────────────────────────────────────
st.markdown("<h1 style='text-align:center'>🌙 Sleep Analytics AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:#8b949e'>MySQL + Groq LLaMA 3.3 · Аналитика данных сна</p>",
            unsafe_allow_html=True)

# метрики из БД
@st.cache_data(ttl=60)
def header_stats():
    try:
        conn = get_connection()
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) as n FROM participants")
            n = c.fetchone()["n"]
            c.execute("SELECT ROUND(AVG(sleep_quality_score),1) as q FROM sleep_sessions")
            q = c.fetchone()["q"]
            c.execute("SELECT ROUND(AVG(sleep_duration_hrs),1) as d FROM sleep_sessions")
            d = c.fetchone()["d"]
        conn.close()
        return n, q, d
    except:
        return "—", "—", "—"

n, q, d = header_stats()
c1, c2, c3, c4 = st.columns(4)
for col, val, lbl in [
    (c1, n,        "Участников"),
    (c2, f"{q}/10","Ср. качество"),
    (c3, f"{d} ч", "Ср. длительность"),
    (c4, "LLaMA 3.3", "AI модель"),
]:
    col.markdown(
        f'<div class="metric-card"><div class="metric-value">{val}</div>'
        f'<div class="metric-label">{lbl}</div></div>',
        unsafe_allow_html=True
    )

st.markdown("---")

# ── SESSION STATE ───────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── TABS ────────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["💬 AI Агент", "🧬 Мой профиль сна"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — AI CHAT
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### Задай вопрос — ИИ напишет SQL, выполнит и объяснит результат")

    # быстрые вопросы
    CHIPS = [
        "Средняя продолжительность сна по полу",
        "Топ-5 по качеству сна",
        "Связь кофеина и качества сна",
        "Распределение хронотипов",
        "Влияние стресса на засыпание",
        "Пробуждения ночью по типу работы",
    ]
    cols = st.columns(3)
    chip_clicked = None
    for i, chip in enumerate(CHIPS):
        if cols[i % 3].button(chip, key=f"chip_{i}", use_container_width=True):
            chip_clicked = chip

    st.markdown("")

    # история
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sql"):
                with st.expander("📄 SQL", expanded=False):
                    st.code(msg["sql"], language="sql")
            if msg.get("df") is not None and not msg["df"].empty:
                st.dataframe(msg["df"].head(15), use_container_width=True)
            if msg.get("fig"):
                st.plotly_chart(msg["fig"], use_container_width=True)

    user_input = st.chat_input("Например: покажи связь стресса и качества сна")
    question = chip_clicked or user_input

    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            # 1. генерируем SQL
            with st.spinner("Генерирую SQL..."):
                sql_system = (
                    "You are a MySQL expert. Write a single valid MySQL SELECT query. "
                    "Return ONLY raw SQL, no markdown, no explanation.\n\n"
                    f"Schema:\n{SCHEMA}"
                )
                sql = clean_sql(ask_ai(question, sql_system))

            with st.expander("📄 SQL запрос", expanded=True):
                st.code(sql, language="sql")

            # 2. выполняем
            with st.spinner("Выполняю запрос..."):
                df, err = run_sql(sql)

            if err:
                st.error(f"Ошибка SQL: {err}")
                st.session_state.messages.append(
                    {"role": "assistant", "content": f"Ошибка: {err}", "sql": sql})

            elif df is None or df.empty:
                st.warning("Данные не найдены.")
                st.session_state.messages.append(
                    {"role": "assistant", "content": "Данные не найдены.", "sql": sql})

            else:
                st.dataframe(df.head(15), use_container_width=True)

                # 3. график
                fig = auto_chart(df)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

                # 4. инсайт
                with st.spinner("Анализирую..."):
                    insight = ask_ai(
                        f"Вопрос: {question}\nДанные:\n{df.head(15).to_string(index=False)}",
                        "Ты аналитик данных сна. Дай краткий вывод на русском (3–4 предложения), "
                        "опираясь только на предоставленные цифры."
                    )

                st.info(insight)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": insight,
                    "sql": sql,
                    "df": df,
                    "fig": fig
                })

    if st.session_state.messages:
        if st.button("🗑️ Очистить чат", key="clear"):
            st.session_state.messages = []
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PERSONAL PROFILE
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("## 🧬 Мой профиль сна")
    st.markdown("Введи свои данные — ИИ сравнит тебя с базой и даст персональные рекомендации.")

    col_form, col_res = st.columns([1, 1.4], gap="large")

    with col_form:
        st.markdown("#### Параметры сна")
        u_age     = st.slider("Возраст", 18, 80, 30)
        u_gender  = st.selectbox("Пол", ["Male", "Female"])
        u_hours   = st.slider("Часов сна", 3.0, 12.0, 7.0, 0.5)
        u_quality = st.slider("Качество сна (1–10)", 1, 10, 6)
        u_latency = st.slider("Время засыпания (мин)", 0, 90, 20, 5)
        u_wake    = st.slider("Ночных пробуждений", 0, 10, 1)

        st.markdown("#### Образ жизни")
        u_stress   = st.slider("Уровень стресса (1–10)", 1, 10, 5)
        u_caffeine = st.slider("Кофеин (мг/день)", 0, 1000, 200, 50)
        u_alcohol  = st.slider("Алкоголь (ед/нед)", 0, 20, 2)
        u_screen   = st.slider("Экран перед сном (мин)", 0, 300, 60, 10)

        st.markdown("#### Профиль")
        u_chrono = st.selectbox("Хронотип", ["Morning (Жаворонок)", "Neutral", "Evening (Сова)"])
        u_shift  = st.selectbox("Сменная работа", ["Нет", "Да"])

        btn = st.button("✨ Анализировать", type="primary", use_container_width=True)

    with col_res:
        if not btn:
            st.markdown("""
            <div style='text-align:center;padding:80px 20px;color:#8b949e'>
                <div style='font-size:52px;margin-bottom:16px'>🌙</div>
                <div>Заполни форму и нажми<br><b>«Анализировать»</b></div>
            </div>""", unsafe_allow_html=True)
        else:
            # ── score ──────────────────────────────────────────────
            score = round(min(100, max(0,
                u_hours / 9 * 35
                + (10 - u_stress) / 9 * 20
                - u_latency / 90 * 12
                - u_wake   / 10 * 10
                - u_caffeine / 1000 * 8
                - u_alcohol  / 20  * 5
                - u_screen   / 300 * 5
                + (5 if u_shift == "Нет" else -5)
                + 10
            )), 1)

            color = "#3fb950" if score >= 75 else "#d29922" if score >= 50 else "#f85149"
            label = ("Хороший сон 🟢" if score >= 75
                     else "Требует внимания 🟡" if score >= 50
                     else "Плохое качество 🔴")

            # gauge
            fig_g = go.Figure(go.Indicator(
                mode="gauge+number",
                value=score,
                number={"suffix": "/100", "font": {"color": color, "size": 34}},
                gauge={
                    "axis": {"range": [0, 100], "tickcolor": "#8b949e"},
                    "bar":  {"color": color, "thickness": 0.25},
                    "bgcolor": "#161b22", "borderwidth": 0,
                    "steps": [
                        {"range": [0,   50],  "color": "#1c2128"},
                        {"range": [50,  75],  "color": "#1c2128"},
                        {"range": [75, 100],  "color": "#1c2128"},
                    ],
                }
            ))
            fig_g.update_layout(
                height=220, margin=dict(t=10, b=10, l=30, r=30),
                paper_bgcolor="rgba(0,0,0,0)", font={"color": "#c9d1d9"}
            )
            st.plotly_chart(fig_g, use_container_width=True)
            st.markdown(f"<h3 style='text-align:center;color:{color}'>{label} · {score}/100</h3>",
                        unsafe_allow_html=True)
            st.markdown("---")

            # ── сравнение с БД ──────────────────────────────────────
            db = None
            try:
                conn = get_connection()
                with conn.cursor() as c:
                    c.execute("""
                        SELECT
                            ROUND(AVG(s.sleep_duration_hrs),2)  AS avg_d,
                            ROUND(AVG(s.sleep_quality_score),2) AS avg_q,
                            ROUND(AVG(s.sleep_latency_mins),1)  AS avg_l,
                            ROUND(AVG(s.wake_episodes),1)       AS avg_w
                        FROM sleep_sessions s
                        JOIN participants p
                          ON p.participant_id = s.Participants_participants_id
                        WHERE p.age BETWEEN %s AND %s
                          AND p.gender = %s
                    """, (u_age - 5, u_age + 5, u_gender))
                    db = c.fetchone()
                conn.close()
            except Exception as e:
                st.warning(f"Не удалось загрузить данные из БД: {e}")

            if db and db["avg_d"]:
                st.markdown("#### 📊 Вы vs База данных")
                cmp = pd.DataFrame({
                    "Параметр": ["Длительность (ч)", "Качество /10", "Засыпание (мин)", "Пробуждений"],
                    "Вы":       [u_hours, u_quality, u_latency, u_wake],
                    "База":     [float(db["avg_d"] or 0), float(db["avg_q"] or 0),
                                 float(db["avg_l"] or 0), float(db["avg_w"] or 0)]
                })
                fig_c = px.bar(cmp, x="Параметр", y=["Вы", "База"],
                               barmode="group",
                               color_discrete_sequence=["#1f6feb", "#388bfd50"],
                               template="plotly_dark")
                fig_c.update_layout(height=260, margin=dict(t=20, b=10),
                                    paper_bgcolor="rgba(0,0,0,0)",
                                    legend=dict(orientation="h", y=1.1))
                st.plotly_chart(fig_c, use_container_width=True)

            # ── AI советы ──────────────────────────────────────────
            st.markdown("#### 💡 Рекомендации ИИ")
            with st.spinner("Анализирую данные..."):
                db_line = ""
                if db and db["avg_d"]:
                    db_line = (f"\nСреднее по базе ({u_gender}, {u_age}±5 лет): "
                               f"сон {db['avg_d']}ч, качество {db['avg_q']}/10, "
                               f"засыпание {db['avg_l']}мин, пробуждений {db['avg_w']}.")

                advice = ask_ai(
                    f"""Данные пользователя:
- Возраст: {u_age}, пол: {u_gender}
- Сон: {u_hours}ч, качество: {u_quality}/10
- Засыпание: {u_latency}мин, пробуждений: {u_wake}
- Стресс: {u_stress}/10, кофеин: {u_caffeine}мг, алкоголь: {u_alcohol}ед, экран: {u_screen}мин
- Хронотип: {u_chrono}, сменная работа: {u_shift}
- Sleep Score: {score}/100
{db_line}

Напиши:
1. Краткую оценку (2 предложения)
2. Сравнение с базой (если есть)
3. 4-5 конкретных советов с эмодзи
4. Что улучшить в первую очередь""",
                    "Ты врач-сомнолог. Давай конкретные советы на русском языке, "
                    "основанные строго на цифрах пользователя. Без общих фраз."
                )

            st.success(advice)
            