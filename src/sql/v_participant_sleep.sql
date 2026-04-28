CREATE VIEW v_participant_sleep AS
SELECT
    p.participant_id,
    pp.occupation,
    pp.country,
    pp.mental_health_condition,
    pp.weekend_sleep_diff_hrs,
    s.session_id,
    s.sleep_duration_hrs,
    s.sleep_quality_score,
    s.sleep_latency_mins,
    s.wake_episodes
FROM participants p
JOIN participant_profiles pp
    ON p.participant_id = pp.Participants_participants_id
JOIN sleep_sessions s
    ON p.participant_id = s.Participants_participants_id;