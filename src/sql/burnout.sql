CREATE OR REPLACE VIEW v_burnout_risk_matrix AS
SELECT 
    p.participant_id,
    p.shift_work,
    da.work_hours,
    sp.stress_score,
    sp.heart_rate_resting_bpm,
    ROUND(
        (sp.stress_score * 0.4) + 
        (da.work_hours / 24 * 0.4) + 
        (sp.sleep_disorder_risk * 0.2), 2
    ) AS burnout_index
FROM participants p
JOIN sleep_sessions ss ON p.participant_id = ss.Participants_participants_id
JOIN sleep_physiology sp ON ss.session_id = sp.sleep_sessions_session_id
JOIN dailyactivities da ON ss.session_id = da.sleep_sessions_session_id;