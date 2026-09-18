import tempfile
import unittest
from pathlib import Path

import pandas as pd

from cs_ahf_ml.error_audit import merge_event_time


class EventTimeMergeTest(unittest.TestCase):
    def test_requested_column_can_come_from_external_csv(self):
        dataset = pd.DataFrame({"stay_id": [1, 2], "primary_outcome_flag": [0, 1]})
        event_time = pd.DataFrame(
            {"stay_id": [1, 2], "primary_event_hour_after_landmark": [None, 8.0]}
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "event_time.csv"
            event_time.to_csv(path, index=False)
            merged, _ = merge_event_time(
                dataset,
                event_time_csv=path,
                event_time_col="primary_event_hour_after_landmark",
            )

        self.assertIn("event_hour_after_landmark", merged.columns)
        self.assertEqual(merged.loc[1, "event_hour_after_landmark"], 8.0)


if __name__ == "__main__":
    unittest.main()

