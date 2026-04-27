import os
import pymysql
from dotenv import load_dotenv
from groq import Groq
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SCHEMA = """
Tables:
- participants(participant_id, age, gender, bmi, chronotype, shift_work)
- sleep_sessions(session_id, Participants_participants_id, sleep_duration_hrs,
    sleep_quality_score, sleep_latency_mins, wake_episodes)
- sleep_physiology(phys_id, sleep_sessions_session_id, rem_percentage,
    deep_sleep_percentage, heart_rate_resting_bpm, felt_rested,
    sleep_disorder_risk, stress_score)
- lifestylehabits(habit_id, sleep_sessions_session_id, caffeine_mg,
    alcohol_units, screen_time_mins, sleep_aid_used)
- environmentalconditions(env_id, sleep_sessions_session_id,
    room_temp_celsius, season, day_type)
- dailyactivities(activity_id, sleep_sessions_session_id, steps_count,
    exercise_day, work_hours, nap_duration_mins, cognitive_performance_score)
- participant_profiles(profile_id, Participants_participants_id, country,
    occupation, mental_health_condition, weekend_sleep_diff_hrs)
Views:
- v_stress_summary(shift_work, avg_heart_rate, avg_sleep_quality)
- v_burnout_risk_matrix(participant_id, shift_work, work_hours, stress_score,
    heart_rate_resting_bpm, burnout_index)

Foreign keys:
- sleep_sessions.Participants_participants_id -> participants.participant_id
- sleep_physiology.sleep_sessions_session_id -> sleep_sessions.session_id
- lifestylehabits.sleep_sessions_session_id -> sleep_sessions.session_id
- environmentalconditions.sleep_sessions_session_id -> sleep_sessions.session_id
- dailyactivities.sleep_sessions_session_id -> sleep_sessions.session_id
- participant_profiles.Participants_participants_id -> participants.participant_id
"""

SQL_SYSTEM = f"""You are a MySQL expert. Given a question, generate ONE valid MySQL query.
Rules:
- Return ONLY the SQL query, nothing else
- No markdown, no backticks, no explanation
- Use LIMIT 20 for queries returning individual rows
- Use ROUND() for decimal numbers
- Always use proper JOINs based on the schema below
- Use views v_stress_summary and v_burnout_risk_matrix when relevant

Database schema:
{SCHEMA}
"""

ANSWER_SYSTEM = """You are a data analyst. Given a question and SQL query results,
give a clear, concise answer with specific numbers.
Answer in the same language as the question.
Do not make up data - use only the provided results.
"""


def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        charset='utf8mb4'
    )


def generate_sql(question):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SQL_SYSTEM},
            {"role": "user", "content": question}
        ],
        max_tokens=300
    )
    sql = response.choices[0].message.content.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql


def execute_sql(sql):
    conn = get_connection()
    try:
        with conn.cursor() as c:
            c.execute(sql)
            rows = c.fetchall()
            cols = [desc[0] for desc in c.description]
            if not rows:
                return "No results found."
            result = " | ".join(cols) + "\n"
            for row in rows:
                result += " | ".join(
                    str(round(v, 2) if isinstance(v, float) else v)
                    for v in row
                ) + "\n"
            return result
    except Exception as e:
        return f"SQL Error: {e}"
    finally:
        conn.close()


def generate_answer(question, sql, results):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": ANSWER_SYSTEM},
            {"role": "user", "content": (
                f"Question: {question}\n\n"
                f"SQL used: {sql}\n\n"
                f"Results:\n{results}"
            )}
        ],
        max_tokens=400
    )
    return response.choices[0].message.content


def chat():
    print("🤖 Text-to-SQL чатбот готов!")
    print("💬 Задай любой вопрос по базе данных сна.")
    print("Введи 'выход' для выхода.\n")

    while True:
        user_input = input("Ты: ").strip()
        if user_input.lower() in ["выход", "exit"]:
            print("До свидания!")
            break
        if not user_input:
            continue

        print("⏳ Генерирую SQL...")
        try:
            sql = generate_sql(user_input)
            print(f"📝 SQL: {sql}\n")
        except Exception as e:
            print(f"❌ Ошибка генерации SQL: {e}\n")
            continue

        print("⏳ Выполняю запрос...")
        results = execute_sql(sql)

        if "SQL Error" in results:
            print(f"❌ {results}\n")
            continue

        print("⏳ Формирую ответ...")
        try:
            answer = generate_answer(user_input, sql, results)
            print(f"\n🤖 {answer}\n")
        except Exception as e:
            print(f"❌ Ошибка: {e}\n")


if __name__ == "__main__":
    chat()
    