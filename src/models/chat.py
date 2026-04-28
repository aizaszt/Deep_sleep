import os
import re
import pymysql
from dotenv import load_dotenv
from groq import Groq
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SCHEMA = """
Allowed tables:
participants(participant_id, age, gender, bmi, chronotype, shift_work)
sleep_sessions(session_id, Participants_participants_id, sleep_duration_hrs, sleep_quality_score, sleep_latency_mins, wake_episodes)
sleep_physiology(phys_id, sleep_sessions_session_id, rem_percentage, deep_sleep_percentage, heart_rate_resting_bpm, felt_rested, sleep_disorder_risk, stress_score)
lifestylehabits(habit_id, sleep_sessions_session_id, caffeine_mg, alcohol_units, screen_time_mins, sleep_aid_used)
environmentalconditions(env_id, sleep_sessions_session_id, room_temp_celsius, season, day_type)
dailyactivities(activity_id, sleep_sessions_session_id, steps_count, exercise_day, work_hours, nap_duration_mins, cognitive_performance_score)
participant_profiles(profile_id, Participants_participants_id, country, occupation, mental_health_condition, weekend_sleep_diff_hrs)

Views:
v_stress_summary(shift_work, avg_heart_rate, avg_sleep_quality)
v_burnout_risk_matrix(participant_id, shift_work, work_hours, stress_score, heart_rate_resting_bpm, burnout_index)

Join rules:
sleep_sessions.Participants_participants_id = participants.participant_id
sleep_physiology.sleep_sessions_session_id = sleep_sessions.session_id
lifestylehabits.sleep_sessions_session_id = sleep_sessions.session_id
environmentalconditions.sleep_sessions_session_id = sleep_sessions.session_id
dailyactivities.sleep_sessions_session_id = sleep_sessions.session_id
participant_profiles.Participants_participants_id = participants.participant_id
"""

SQL_SYSTEM = f"""
You are a MySQL expert. Generate exactly one SQL query.

Rules:
- Return only SQL, no markdown, no explanation.
- Use only approved tables and views from the schema.
- occupation exists only in participant_profiles.
- Never use participants.occupation.
- For profession questions, prefer v_sleep_by_profession.
- For stress and burnout questions, always use v_burnout_risk_matrix.
- For queries about profession + sleep, use v_sleep_by_profession.
- For queries about stress factors, use v_sleep_factors or v_burnout_with_occupation if available.
- Never invent tables, columns, aliases, or joins.
- Use explicit aliases only when needed.
- Use LIMIT 20.
- Use ROUND(value, 2) for numeric outputs.
- If the question cannot be answered from the schema, return:
  SELECT 'Unsupported question' AS message LIMIT 1;

Schema:
{SCHEMA}
"""

ANSWER_SYSTEM = """
You are a data analyst. Given a question and SQL results, answer clearly and concisely in the same language as the question.
Use only the provided results. Do not invent data.
"""

def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )

def clean_sql(sql):
    sql = sql.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql

def is_safe_sql(sql):
    s = sql.lower().strip()
    if not s.startswith("select") and not s.startswith("with"):
        return False
    bad = ["insert ", "update ", "delete ", "drop ", "alter ", "truncate ", "create ", "grant ", "revoke "]
    return not any(b in s for b in bad)

def generate_sql(question):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SQL_SYSTEM},
            {"role": "user", "content": question}
        ],
        temperature=0.1,
        max_completion_tokens=300
    )
    sql = clean_sql(response.choices[0].message.content)
    return sql

def execute_sql(sql):
    if not is_safe_sql(sql):
        return "SQL Error: Unsafe or invalid SQL generated."

    conn = get_connection()
    try:
        with conn.cursor() as c:
            c.execute(sql)
            rows = c.fetchall()
            if not rows:
                return "No results found."
            cols = list(rows[0].keys())
            result = " | ".join(cols) + "\n"
            for row in rows:
                result += " | ".join(str(round(v, 2)) if isinstance(v, float) else str(v) for v in row.values()) + "\n"
            return result
    except Exception as e:
        return f"SQL Error: {e}"
    finally:
        conn.close()

def generate_answer(question, sql, results):
    content = f"Question: {question}\n\nSQL used: {sql}\n\nResults:\n{results}"
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": ANSWER_SYSTEM},
            {"role": "user", "content": content}
        ],
        temperature=0.2,
        max_completion_tokens=400
    )
    return response.choices[0].message.content