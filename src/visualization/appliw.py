import os
import pymysql
import streamlit as st
import pandas as pd
import plotly.express as px
from groq import Groq
from dotenv import load_dotenv

# ---------------- CONFIG ----------------
load_dotenv()
st.set_page_config(page_title="Sleep Analytics AI PRO", page_icon="🌙", layout="wide")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ---------------- STYLE ----------------
st.markdown("""
<style>
.stApp {background:#0b0e14;color:white;}
.card {background:#161b22;padding:15px;border-radius:10px;border:1px solid #30363d;}
</style>
""", unsafe_allow_html=True)

# ---------------- DB ----------------
def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        charset="utf8mb4"
    )

# ---------------- SCHEMA ----------------
SCHEMA = """
participants(participant_id, age, gender, bmi, chronotype, shift_work)
sleep_sessions(session_id, Participants_participants_id, sleep_duration_hrs, sleep_quality_score, sleep_latency_mins, wake_episodes)
lifestylehabits(id, Participants_participants_id, caffeine_mg, alcohol_units_week, screen_time_mins)
sleep_physiology(deep_sleep_percentage, stress_score, felt_rested)
"""

# ---------------- AI ----------------
def ask_ai(prompt, system=""):
    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ]
    )
    return res.choices[0].message.content

# ---------------- CLEAN SQL ----------------
def clean_sql(sql):
    sql = sql.strip()
    sql = sql.replace("```sql", "").replace("```", "")

    if sql.lower().startswith("sql"):
        sql = sql[3:].strip()

    if "SELECT" in sql.upper():
        sql = sql[sql.upper().index("SELECT"):]

    return sql

# ---------------- AUTO FIX SQL ----------------
def run_sql_with_fix(question):

    system = f"""
You are a MySQL expert.

RULES:
- ONLY SQL
- START with SELECT
- NO markdown

Schema:
{SCHEMA}
"""

    sql = clean_sql(ask_ai(question, system))

    for _ in range(3):
        try:
            conn = get_connection()
            df = pd.read_sql(sql, conn)
            conn.close()
            return df, sql, None

        except Exception as e:
            error = str(e)

            fix_prompt = f"""
Fix SQL query.

SQL:
{sql}

Error:
{error}

Return ONLY corrected SQL.
"""
            sql = clean_sql(ask_ai(fix_prompt))

    return None, sql, error

# ---------------- HEADER ----------------
st.title("🌙 Sleep Analytics AI PRO")

tab1, tab2 = st.tabs(["💬 AI Chat", "🧬 Personal"])

# =========================================================
# TAB 1
# =========================================================
with tab1:

    if "chat" not in st.session_state:
        st.session_state.chat = []

    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "df" in msg:
                st.dataframe(msg["df"])

    if prompt := st.chat_input("Спроси про данные сна..."):

        st.session_state.chat.append({"role":"user","content":prompt})

        with st.chat_message("assistant"):
            with st.spinner("AI анализ..."):

                df, sql, err = run_sql_with_fix(prompt)

                st.code(sql)

                if err:
                    st.error(err)
                    answer = err
                else:
                    st.dataframe(df.head(10))

                    # график
                    if len(df) > 1:
                        num = df.select_dtypes("number").columns
                        cat = df.select_dtypes("object").columns

                        if len(cat)>0 and len(num)>0:
                            fig = px.bar(df, x=cat[0], y=num[0])
                            st.plotly_chart(fig, use_container_width=True)

                    # анализ
                    answer = ask_ai(
                        f"Data:\n{df.head(10).to_string()}\nQuestion:{prompt}",
                        "Ты аналитик данных. Кратко объясни вывод на русском."
                    )
                    st.markdown(answer)

                st.session_state.chat.append({
                    "role":"assistant",
                    "content":answer,
                    "df":df
                })

# =========================================================
# TAB 2
# =========================================================
with tab2:

    st.subheader("Персональный анализ")

    sleep = st.slider("Сон (часы)", 3.0, 12.0, 7.0, key="sleep_p")
    stress = st.slider("Стресс", 1, 10, 5, key="stress_p")
    caffeine = st.slider("Кофеин", 0, 500, 100, key="caffeine_p")

    if st.button("Анализ", key="btn_p"):

        score = round((sleep*10) - stress*2 - caffeine/20,1)

        st.metric("Sleep Score", score)

        df = pd.DataFrame({
            "factor":["sleep","stress","caffeine"],
            "value":[sleep,stress,caffeine]
        })

        fig = px.bar(df, x="factor", y="value")
        st.plotly_chart(fig, use_container_width=True)

        advice = ask_ai(
            f"Sleep:{sleep}, Stress:{stress}, Caffeine:{caffeine}",
            "Дай 3 совета по улучшению сна на русском"
        )

        st.info(advice)