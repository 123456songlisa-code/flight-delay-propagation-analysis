import unittest

import pandas as pd

from src.analyze import add_timestamps, build_rotation_pairs, hhmm_to_minutes, safe_rate


class PipelineTests(unittest.TestCase):
    def test_hhmm_conversion(self):
        self.assertEqual(hhmm_to_minutes(5), 5)
        self.assertEqual(hhmm_to_minutes(930), 570)
        self.assertEqual(hhmm_to_minutes(2400), 1440)
        self.assertTrue(pd.isna(hhmm_to_minutes(1260)))

    def test_safe_rate(self):
        self.assertEqual(safe_rate(1, 4), 0.25)
        self.assertIsNone(safe_rate(1, 0))

    def test_rotation_propagation(self):
        frame = pd.DataFrame([
            {
                "flight_id": 1, "flight_date": "2024-01-01", "carrier": "XX", "tail_number": "N1",
                "flight_number": 1, "origin": "AAA", "destination": "BBB",
                "scheduled_departure": 800, "actual_departure": 800, "departure_delay": 0,
                "scheduled_arrival": 900, "actual_arrival": 930, "arrival_delay": 30,
                "cancelled": 0, "diverted": 0, "carrier_delay": 0, "weather_delay": 0,
                "nas_delay": 0, "security_delay": 0, "late_aircraft_delay": 30, "distance": 100,
            },
            {
                "flight_id": 2, "flight_date": "2024-01-01", "carrier": "XX", "tail_number": "N1",
                "flight_number": 2, "origin": "BBB", "destination": "CCC",
                "scheduled_departure": 945, "actual_departure": 1010, "departure_delay": 25,
                "scheduled_arrival": 1045, "actual_arrival": 1110, "arrival_delay": 25,
                "cancelled": 0, "diverted": 0, "carrier_delay": 0, "weather_delay": 0,
                "nas_delay": 0, "security_delay": 0, "late_aircraft_delay": 25, "distance": 100,
            },
        ])
        frame["flight_date"] = pd.to_datetime(frame["flight_date"])
        pairs = build_rotation_pairs(add_timestamps(frame))
        second = pairs.iloc[1]
        self.assertTrue(bool(second["valid_rotation"]))
        self.assertTrue(bool(second["eligible_inbound_delay"]))
        self.assertTrue(bool(second["propagated"]))
        self.assertEqual(second["scheduled_ground_minutes"], 45)


if __name__ == "__main__":
    unittest.main()

