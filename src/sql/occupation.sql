USE deep_sleep;


CREATE PROCEDURE GetOccupationHealthReport(IN job_title VARCHAR(50))
BEGIN
    SELECT
        shift_work,
        ROUND(AVG(burnout_index), 2) AS avg_burnout,
        ROUND(AVG(stress_score), 2)  AS avg_stress
    FROM v_burnout_risk_matrix
    WHERE participant_id IN (
        SELECT Participants_participants_id
        FROM participant_profiles
        WHERE occupation = job_title
    )
    GROUP BY shift_work;
END
 

CALL GetOccupationHealthReport('Doctor');

