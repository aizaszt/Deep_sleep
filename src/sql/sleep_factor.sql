CREATE VIEW v_sleep_factors AS
SELECT
    p.participant_id,
    pp.occupation,
    s.session_id,
    s.sleep_duration_hrs,
    s.sleep_quality_score,
    lh.caffeine_mg,
    lh.alcohol_units,
    lh.screen_time_mins,
    da.work_hours,
    da.steps_count,
    sp.stress_score
FROM participants p
JOIN participant_profiles pp
    ON p.participant_id = pp.Participants_participants_id
JOIN sleep_sessions s
    ON p.participant_id = s.Participants_participants_id
JOIN lifestylehabits lh
    ON s.session_id = lh.sleep_sessions_session_id
JOIN dailyactivities da
    ON s.session_id = da.sleep_sessions_session_id
JOIN sleep_physiology sp
    ON s.session_id = sp.sleep_sessions_session_id;