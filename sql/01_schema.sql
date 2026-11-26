-- PostgreSQL 15+
CREATE SCHEMA IF NOT EXISTS aviation;

CREATE TABLE IF NOT EXISTS aviation.fact_flight (
    flight_id BIGSERIAL PRIMARY KEY,
    flight_date DATE NOT NULL,
    carrier_code TEXT NOT NULL,
    tail_number TEXT,
    flight_number TEXT,
    origin_code TEXT NOT NULL,
    destination_code TEXT NOT NULL,
    scheduled_departure_ts TIMESTAMP,
    actual_departure_ts TIMESTAMP,
    scheduled_arrival_ts TIMESTAMP,
    actual_arrival_ts TIMESTAMP,
    departure_delay_minutes NUMERIC,
    arrival_delay_minutes NUMERIC,
    cancelled BOOLEAN NOT NULL DEFAULT FALSE,
    diverted BOOLEAN NOT NULL DEFAULT FALSE,
    carrier_delay_minutes NUMERIC,
    weather_delay_minutes NUMERIC,
    nas_delay_minutes NUMERIC,
    security_delay_minutes NUMERIC,
    late_aircraft_delay_minutes NUMERIC,
    distance_miles NUMERIC
);

CREATE INDEX IF NOT EXISTS ix_flight_tail_schedule
    ON aviation.fact_flight (tail_number, scheduled_departure_ts);
CREATE INDEX IF NOT EXISTS ix_flight_date_carrier
    ON aviation.fact_flight (flight_date, carrier_code);
CREATE INDEX IF NOT EXISTS ix_flight_route
    ON aviation.fact_flight (origin_code, destination_code, flight_date);

