USE deep_sleep;

CREATE PROCEDURE GetHighRiskParticipants(IN p_min DOUBLE)
BEGIN
    IF p_min IS NULL OR p_min = 0 THEN
        SET p_min = 7.0;
    END IF;
    DROP TEMPORARY TABLE IF EXISTS tmp_burnout;
    CREATE TEMPORARY TABLE tmp_burnout AS
    SELECT
        p.participant_id,
        p.age,
        p.gender,
        pp.occupation,
        pp.country,
        p.shift_work,
        da.work_hours,
        sp.stress_score,
        sp.heart_rate_resting_bpm,
        ROUND((sp.stress_score * 0.6) + ((da.work_hours / 2) * 0.4), 2) AS burnout_index
    FROM participants p
    JOIN participant_profiles pp ON pp.Participants_participants_id = p.participant_id
    JOIN sleep_sessions ss ON ss.Participants_participants_id = p.participant_id
    JOIN sleep_physiology sp ON sp.sleep_sessions_session_id = ss.session_id
    JOIN dailyactivities da ON da.sleep_sessions_session_id = ss.session_id;
    SELECT * FROM tmp_burnout WHERE burnout_index >= p_min ORDER BY burnout_index DESC LIMIT 100;
    DROP TEMPORARY TABLE IF EXISTS tmp_burnout;
END
CALL GetHighRiskParticipants(5.0);