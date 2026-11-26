CREATE OR REPLACE VIEW aviation.vw_rotation_pairs AS
WITH sequenced AS (
    SELECT
        f.*,
        LAG(f.flight_id) OVER w AS prev_flight_id,
        LAG(f.destination_code) OVER w AS prev_destination_code,
        LAG(f.scheduled_arrival_ts) OVER w AS prev_scheduled_arrival_ts,
        LAG(f.actual_arrival_ts) OVER w AS prev_actual_arrival_ts,
        LAG(f.arrival_delay_minutes) OVER w AS prev_arrival_delay_minutes,
        LAG(f.cancelled) OVER w AS prev_cancelled,
        LAG(f.diverted) OVER w AS prev_diverted
    FROM aviation.fact_flight f
    WHERE f.tail_number IS NOT NULL
    WINDOW w AS (
        PARTITION BY f.tail_number
        ORDER BY f.scheduled_departure_ts, f.flight_id
    )
), paired AS (
    SELECT
        *,
        EXTRACT(EPOCH FROM (scheduled_departure_ts - prev_scheduled_arrival_ts)) / 60.0
            AS scheduled_ground_minutes,
        EXTRACT(EPOCH FROM (actual_departure_ts - prev_actual_arrival_ts)) / 60.0
            AS actual_ground_minutes,
        origin_code = prev_destination_code
            AND NOT cancelled AND NOT diverted
            AND NOT COALESCE(prev_cancelled, TRUE)
            AND NOT COALESCE(prev_diverted, TRUE)
            AND scheduled_departure_ts - prev_scheduled_arrival_ts BETWEEN INTERVAL '0 minute' AND INTERVAL '12 hours'
            AS valid_rotation
    FROM sequenced
)
SELECT
    *,
    valid_rotation AND prev_arrival_delay_minutes >= 15 AS eligible_inbound_delay,
    valid_rotation AND prev_arrival_delay_minutes >= 15 AND departure_delay_minutes >= 15 AS propagated,
    valid_rotation AND prev_arrival_delay_minutes >= 15 AND departure_delay_minutes < 15 AS absorbed,
    CASE WHEN valid_rotation THEN GREATEST(prev_arrival_delay_minutes - departure_delay_minutes, 0) END
        AS recovered_minutes
FROM paired;

