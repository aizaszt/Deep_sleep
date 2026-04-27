import os
import pymysql
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")


def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        charset='utf8mb4'
    )


def _q(cursor, sql):
    cursor.execute(sql)
    return cursor.fetchall()


def get_data():
    conn = get_connection()
    out = []
    with conn.cursor() as c:

        # УРОВЕНЬ 1 — Базовая статистика
        r = _q(c, """
            SELECT ROUND(AVG(ss.sleep_duration_hrs), 2),
                   ROUND(AVG(ss.sleep_quality_score), 2),
                   ROUND(AVG(ss.sleep_latency_mins), 1),
                   ROUND(AVG(p.age), 1),
                   MIN(p.age), MAX(p.age),
                   ROUND(AVG(p.bmi), 1),
                   COUNT(DISTINCT p.participant_id),
                   ROUND(
                       100.0 * SUM(p.shift_work)
                       / COUNT(DISTINCT p.participant_id), 1
                   )
            FROM participants p
            JOIN sleep_sessions ss
                ON ss.Participants_participants_id = p.participant_id
        """)[0]
        out.append(
            f"[Базовая] участников={r[7]}, сон={r[0]}ч, "
            f"качество={r[1]}, латент={r[2]}мин, "
            f"возраст={r[3]}(мин={r[4]},макс={r[5]}), "
            f"bmi={r[6]}, сменщики={r[8]}%"
        )

        rows = _q(c, """
            SELECT gender, COUNT(*),
                   ROUND(AVG(age), 1), ROUND(AVG(bmi), 1)
            FROM participants GROUP BY gender
        """)
        out.append(
            "[Пол] " + "; ".join(
                f"{r[0]}:n={r[1]},возраст={r[2]},bmi={r[3]}"
                for r in rows
            )
        )

        rows = _q(c, """
            SELECT chronotype, COUNT(*),
                   ROUND(AVG(ss.sleep_quality_score), 2)
            FROM participants p
            JOIN sleep_sessions ss
                ON ss.Participants_participants_id = p.participant_id
            GROUP BY chronotype ORDER BY COUNT(*) DESC
        """)
        out.append(
            "[Хронотип] " + "; ".join(
                f"{r[0]}:n={r[1]},сон={r[2]}" for r in rows
            )
        )

        # УРОВЕНЬ 2 — Образ жизни
        rows = _q(c, """
            SELECT CASE
                WHEN caffeine_mg = 0    THEN '0мг'
                WHEN caffeine_mg <= 100 THEN '1-100мг'
                WHEN caffeine_mg <= 200 THEN '101-200мг'
                WHEN caffeine_mg <= 400 THEN '201-400мг'
                ELSE '400+мг'
            END g,
            COUNT(*),
            ROUND(AVG(ss.sleep_quality_score), 2),
            ROUND(AVG(ss.sleep_duration_hrs), 2),
            ROUND(AVG(ss.sleep_latency_mins), 1)
            FROM lifestylehabits lh
            JOIN sleep_sessions ss
                ON ss.session_id = lh.sleep_sessions_session_id
            GROUP BY g ORDER BY MIN(caffeine_mg)
        """)
        out.append(
            "[Кофеин->сон] " + "; ".join(
                f"{r[0]}:n={r[1]},кач={r[2]},"
                f"длит={r[3]}ч,лат={r[4]}мин"
                for r in rows
            )
        )

        rows = _q(c, """
            SELECT CASE
                WHEN alcohol_units = 0  THEN '0'
                WHEN alcohol_units <= 1 THEN '0.1-1'
                ELSE '1+'
            END g,
            ROUND(AVG(ss.sleep_quality_score), 2),
            ROUND(AVG(ss.sleep_duration_hrs), 2)
            FROM lifestylehabits lh
            JOIN sleep_sessions ss
                ON ss.session_id = lh.sleep_sessions_session_id
            GROUP BY g ORDER BY MIN(alcohol_units)
        """)
        out.append(
            "[Алкоголь->сон] " + "; ".join(
                f"{r[0]}ед:кач={r[1]},длит={r[2]}ч" for r in rows
            )
        )

        rows = _q(c, """
            SELECT CASE
                WHEN screen_time_mins <= 60  THEN '0-1ч'
                WHEN screen_time_mins <= 180 THEN '1-3ч'
                ELSE '3+ч'
            END g,
            ROUND(AVG(ss.sleep_quality_score), 2),
            ROUND(AVG(ss.sleep_latency_mins), 1)
            FROM lifestylehabits lh
            JOIN sleep_sessions ss
                ON ss.session_id = lh.sleep_sessions_session_id
            GROUP BY g ORDER BY MIN(screen_time_mins)
        """)
        out.append(
            "[Экран->сон] " + "; ".join(
                f"{r[0]}:кач={r[1]},лат={r[2]}мин" for r in rows
            )
        )

        rows = _q(c, """
            SELECT sleep_aid_used,
                   ROUND(AVG(ss.sleep_quality_score), 2),
                   ROUND(AVG(ss.sleep_duration_hrs), 2),
                   COUNT(*)
            FROM lifestylehabits lh
            JOIN sleep_sessions ss
                ON ss.session_id = lh.sleep_sessions_session_id
            GROUP BY sleep_aid_used
        """)
        out.append(
            "[Снотворное->сон] " + "; ".join(
                f"{'да' if r[0] else 'нет'}:"
                f"кач={r[1]},длит={r[2]}ч,n={r[3]}"
                for r in rows
            )
        )

        # Окружающая среда
        rows = _q(c, """
            SELECT season,
                   ROUND(AVG(ss.sleep_quality_score), 2),
                   ROUND(AVG(ss.sleep_duration_hrs), 2),
                   COUNT(*)
            FROM environmentalconditions ec
            JOIN sleep_sessions ss
                ON ss.session_id = ec.sleep_sessions_session_id
            GROUP BY season
            ORDER BY AVG(ss.sleep_quality_score) DESC
        """)
        out.append(
            "[Сезон->сон] " + "; ".join(
                f"{r[0]}:кач={r[1]},длит={r[2]}ч,n={r[3]}"
                for r in rows
            )
        )

        rows = _q(c, """
            SELECT day_type,
                   ROUND(AVG(ss.sleep_quality_score), 2),
                   ROUND(AVG(ss.sleep_duration_hrs), 2),
                   COUNT(*)
            FROM environmentalconditions ec
            JOIN sleep_sessions ss
                ON ss.session_id = ec.sleep_sessions_session_id
            GROUP BY day_type
        """)
        out.append(
            "[Тип_дня->сон] " + "; ".join(
                f"{r[0]}:кач={r[1]},длит={r[2]}ч,n={r[3]}"
                for r in rows
            )
        )

        rows = _q(c, """
            SELECT CASE
                WHEN room_temp_celsius < 18  THEN '<18°C'
                WHEN room_temp_celsius <= 22 THEN '18-22°C'
                ELSE '>22°C'
            END g,
            ROUND(AVG(ss.sleep_quality_score), 2),
            ROUND(AVG(ss.sleep_duration_hrs), 2),
            COUNT(*)
            FROM environmentalconditions ec
            JOIN sleep_sessions ss
                ON ss.session_id = ec.sleep_sessions_session_id
            GROUP BY g ORDER BY MIN(room_temp_celsius)
        """)
        out.append(
            "[Температура->сон] " + "; ".join(
                f"{r[0]}:кач={r[1]},длит={r[2]}ч,n={r[3]}"
                for r in rows
            )
        )

        # УРОВЕНЬ 3 — Сменная работа
        rows = _q(c, """
            SELECT
                CASE shift_work WHEN 1 THEN 'сменная' ELSE 'обычная' END,
                ROUND(avg_heart_rate, 1),
                ROUND(avg_sleep_quality, 2)
            FROM v_stress_summary ORDER BY shift_work DESC
        """)
        out.append(
            "[Сменная_работа] " + "; ".join(
                f"{r[0]}:пульс={r[1]},сон={r[2]}" for r in rows
            )
        )

        rows = _q(c, """
            SELECT
                CASE p.shift_work WHEN 1 THEN 'сменная' ELSE 'обычная' END,
                ROUND(AVG(sp.stress_score), 2),
                ROUND(AVG(sp.rem_percentage), 1),
                ROUND(AVG(sp.deep_sleep_percentage), 1),
                ROUND(AVG(sp.heart_rate_resting_bpm), 1),
                ROUND(100.0 * SUM(sp.felt_rested) / COUNT(*), 1)
            FROM participants p
            JOIN sleep_sessions ss
                ON ss.Participants_participants_id = p.participant_id
            JOIN sleep_physiology sp
                ON sp.sleep_sessions_session_id = ss.session_id
            GROUP BY p.shift_work ORDER BY p.shift_work DESC
        """)
        out.append(
            "[Физиология] " + "; ".join(
                f"{r[0]}:стресс={r[1]},REM={r[2]}%,"
                f"глубокий={r[3]}%,пульс={r[4]},выспался={r[5]}%"
                for r in rows
            )
        )

        rows = _q(c, """
            SELECT sleep_disorder_risk, COUNT(*),
                   ROUND(AVG(stress_score), 2)
            FROM sleep_physiology
            GROUP BY sleep_disorder_risk ORDER BY COUNT(*) DESC
        """)
        out.append(
            "[Риск_расстройства] " + "; ".join(
                f"{r[0]}:n={r[1]},стресс={r[2]}" for r in rows
            )
        )

        # УРОВЕНЬ 4 — Выгорание
        r = _q(c, """
            SELECT COUNT(*), ROUND(AVG(stress_score), 2),
                   ROUND(AVG(burnout_index), 2),
                   ROUND(AVG(work_hours), 1)
            FROM v_burnout_risk_matrix WHERE burnout_index >= 7.0
        """)[0]
        out.append(
            f"[Выгорание>=7.0] кол-во={r[0]}, "
            f"стресс={r[1]}, burnout={r[2]}, часов={r[3]}"
        )

        rows = _q(c, """
            SELECT pp.occupation,
                   ROUND(AVG(v.burnout_index), 2),
                   ROUND(AVG(v.stress_score), 2),
                   COUNT(*)
            FROM v_burnout_risk_matrix v
            JOIN participant_profiles pp
                ON pp.Participants_participants_id = v.participant_id
            GROUP BY pp.occupation
            ORDER BY AVG(v.burnout_index) DESC LIMIT 5
        """)
        out.append(
            "[Топ_профессий] " + "; ".join(
                f"{r[0]}:burnout={r[1]},стресс={r[2]},n={r[3]}"
                for r in rows
            )
        )

        rows = _q(c, """
            SELECT CASE
                WHEN ss.sleep_duration_hrs < 6  THEN '<6ч'
                WHEN ss.sleep_duration_hrs <= 7 THEN '6-7ч'
                WHEN ss.sleep_duration_hrs <= 8 THEN '7-8ч'
                ELSE '>8ч'
            END g,
            ROUND(AVG(sp.stress_score), 2) AS avg_stress,
            COUNT(*) AS n
            FROM sleep_sessions ss
            JOIN sleep_physiology sp
                ON sp.sleep_sessions_session_id = ss.session_id
            GROUP BY g ORDER BY MIN(ss.sleep_duration_hrs)
        """)
        out.append(
            "[Сон->стресс] " + "; ".join(
                f"{r[0]}:стресс={r[1]},n={r[2]}" for r in rows
            )
        )

    conn.close()
    return "\n".join(out)
