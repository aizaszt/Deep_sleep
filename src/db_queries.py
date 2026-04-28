"""
db_queries.py
Подключение к MySQL через SQLAlchemy.
burnout_index считается в pandas — без JOIN с вьюхой.
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)
load_dotenv(os.path.join(_root, ".env"), override=True)


def get_engine():
    host     = os.getenv("DB_HOST", "127.0.0.1")
    port     = os.getenv("DB_PORT", "3306")
    database = os.getenv("DB_NAME", "deep_sleep")
    user     = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
    return create_engine(url, pool_pre_ping=True)


def get_data() -> pd.DataFrame:
    """
    Грузим данные без JOIN с v_burnout_risk_matrix.
    burnout_index = round(stress * 0.6 + (work_hours / 2) * 0.4, 2)
    считается в pandas после загрузки.
    """
    query = """
        SELECT
            p.participant_id,
            p.age,
            p.gender,
            p.bmi,
            p.chronotype,
            p.shift_work,

            ss.session_id,
            ss.sleep_duration_hrs   AS sleep,
            ss.sleep_quality_score  AS sleep_quality,
            ss.sleep_latency_mins,
            ss.wake_episodes,

            sp.rem_percentage,
            sp.deep_sleep_percentage,
            sp.heart_rate_resting_bpm,
            sp.felt_rested,
            sp.sleep_disorder_risk,
            sp.stress_score         AS stress,

            lh.caffeine_mg          AS caffeine,
            lh.alcohol_units,
            lh.screen_time_mins,
            lh.sleep_aid_used,

            da.steps_count,
            da.exercise_day,
            da.work_hours,
            da.nap_duration_mins,
            da.cognitive_performance_score,

            ec.room_temp_celsius,
            ec.season,
            ec.day_type,

            pp.country,
            pp.occupation,
            pp.mental_health_condition,
            pp.weekend_sleep_diff_hrs

        FROM sleep_sessions ss

        JOIN participants p
            ON p.participant_id = ss.Participants_participants_id

        LEFT JOIN sleep_physiology sp
            ON sp.sleep_sessions_session_id = ss.session_id

        LEFT JOIN lifestylehabits lh
            ON lh.sleep_sessions_session_id = ss.session_id

        LEFT JOIN dailyactivities da
            ON da.sleep_sessions_session_id = ss.session_id

        LEFT JOIN environmentalconditions ec
            ON ec.sleep_sessions_session_id = ss.session_id

        LEFT JOIN participant_profiles pp
            ON pp.Participants_participants_id = p.participant_id
    """

    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)

    # Считаем burnout_index по той же формуле что и в вьюхе
    df["burnout"] = (
        (df["stress"] * 0.6) + (df["work_hours"] / 2 * 0.4)
    ).round(2)

    return df


if __name__ == "__main__":
    print("Тест: загружаю данные...")
    df = get_data()
    print(type(df))
    print(df.shape)
    print(df[["sleep", "stress", "caffeine", "burnout"]].head(3))