-- Overall operating KPIs. Cancelled/diverted flights are excluded from OTP15.
SELECT
    COUNT(*) AS scheduled_flights,
    COUNT(*) FILTER (WHERE NOT cancelled AND NOT diverted) AS operated_flights,
    AVG((NOT cancelled AND NOT diverted)::INT) AS completion_rate,
    AVG((arrival_delay_minutes < 15)::INT)
        FILTER (WHERE NOT cancelled AND NOT diverted AND arrival_delay_minutes IS NOT NULL) AS arrival_otp15,
    AVG(cancelled::INT) AS cancellation_rate,
    AVG((arrival_delay_minutes >= 60)::INT)
        FILTER (WHERE NOT cancelled AND NOT diverted AND arrival_delay_minutes IS NOT NULL) AS severe_delay_rate,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY arrival_delay_minutes)
        FILTER (WHERE NOT cancelled AND NOT diverted) AS p90_arrival_delay_minutes
FROM aviation.fact_flight;

-- Delay propagation by scheduled ground-time band.
SELECT
    CASE
        WHEN scheduled_ground_minutes <= 45 THEN '00-45'
        WHEN scheduled_ground_minutes <= 75 THEN '46-75'
        WHEN scheduled_ground_minutes <= 120 THEN '76-120'
        ELSE '121-720'
    END AS ground_time_band,
    COUNT(*) AS inbound_delayed_pairs,
    AVG(propagated::INT) AS propagation_rate,
    AVG(absorbed::INT) AS absorption_rate,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY recovered_minutes) AS median_recovered_minutes
FROM aviation.vw_rotation_pairs
WHERE eligible_inbound_delay
GROUP BY 1
ORDER BY 1;

