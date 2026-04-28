CREATE  VIEW v_stress_summary AS
SELECT 
    p.shift_work,
    ROUND(AVG(sp.heart_rate_resting_bpm), 2) AS avg_heart_rate,
    ROUND(AVG(ss.sleep_quality_score), 2) AS avg_sleep_quality
FROM participants p
JOIN sleep_sessions ss ON p.participant_id = ss.Participants_participants_id
JOIN sleep_physiology sp ON ss.session_id = sp.sleep_sessions_session_id
GROUP BY p.shift_work;