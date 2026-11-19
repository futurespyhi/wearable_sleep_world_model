from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from sleep_g3 import data as g3
from stage_forecast.timestamp_policy import aggregate_with_policy


def audit(lines, rules=(), kind="hr", chunk_rows=2, sha="receipt", start=100):
    name = "hr.csv" if kind == "hr" else "motion.csv"
    path_id = f"P/1/{name}"
    events = [dict(path=path_id, sha256="receipt", **row) for row in rules]
    with tempfile.TemporaryDirectory() as tmp, patch.object(g3, "CSV_CHUNK_ROWS", chunk_rows):
        path = Path(tmp) / name
        header = "" if kind == "hr" else "Timestamp,x,y,z\n"
        path.write_text(header + "\n".join(lines) + "\n")
        return aggregate_with_policy(
            path, start, 3, kind, relative=path_id, receipt_sha256=sha,
            policy={"schema": "stage_event_time_v1", "events": events},
        )


class TimestampPolicyTests(unittest.TestCase):
    def test_outside_both_sides_half_open_and_cross_chunk_duplicate(self):
        # Each pair straddles a 2-row chunk, and the last timestamp equals end.
        values, report = audit(["97,9", "99,8", "98,7", "100,50", "100,50.00",
                                "189,90", "190,80", "190,70", "199,65", "198,65"])
        self.assertEqual(report["status"], "complete", report)
        self.assertEqual([e["kind"] for e in report["events"]], [
            "reversal", "identical_duplicate", "conflicting_duplicate", "reversal",
        ])
        self.assertEqual([e["relation"] for e in report["events"]], ["before", "inside", "after", "after"])
        self.assertEqual(report["events"][0]["rows"], [2, 3])
        self.assertTrue(report["events"][0]["cross_chunk"])
        self.assertTrue(report["events"][1]["cross_chunk"])
        self.assertEqual(report["outside_label_interval_rows"], 7)
        self.assertEqual(report["duplicates_dropped"], 1)
        np.testing.assert_array_equal(values["count"], [1, 0, 1])
        np.testing.assert_equal(values["mean"], [50, np.nan, 90])

    def test_only_registered_epoch_dropped_and_no_cross_epoch_differences(self):
        rows = ["100,0,0,0", "101,3,0,0", "130,4,0,0", "132,10,0,0",
                "131,6,0,0", "150,3,0,0", "160,100,0,0", "161,101,0,0"]
        rule = dict(rows=[5, 6], kind="reversal", timestamps=["132", "131"],
                    relation="inside", epoch=1, action="mask_acc_epoch")
        values, report = audit(rows, [rule], "acc")
        self.assertEqual(report["status"], "complete", report)
        self.assertEqual(report["masked_valid_sample_counts"], {"1": 4})
        self.assertEqual(report["masked_epochs"], [1])
        self.assertTrue(report["events"][0]["cross_chunk"])
        self.assertEqual(report["events"][0]["rows"], [5, 6])
        np.testing.assert_equal(values["count"], [2, 0, 2])
        for feature in ("mean", "std", "diff_rms"):
            self.assertTrue(np.isnan(values[feature][1]))
        np.testing.assert_equal(values["diff_rms"], [3, np.nan, 1])
        # File, physical rows, literal timestamp pair, and epoch must all agree.
        for invalid in ({**rule, "rows": [4, 5]}, {**rule, "timestamps": ["132.1", "131"]},
                        {**rule, "epoch": 0}):
            self.assertEqual(audit(rows, [invalid], "acc")[1]["status"], "failed")
        self.assertEqual(audit(rows, [rule], "acc", sha="other-file")[1]["status"], "failed")
        rows[5] = "130.5,3,0,0"
        values, report = audit(rows, [rule], "acc")
        self.assertIsNone(values)
        self.assertEqual([e["action"] for e in report["events"]], ["mask_acc_epoch", "block"])

    def test_new_inside_cross_boundary_and_unlocatable_all_recorded(self):
        values, report = audit(["99,60", "", "101,60", "101,65", "99,65", "150,60",
                                "195,60", "185,70", "oops,62"])
        self.assertIsNone(values)
        self.assertEqual(report["status"], "failed")
        events = report["events"]
        self.assertEqual([e["rows"] for e in events], [[3, 4], [4, 5], [7, 8], [9]])
        self.assertEqual([e["relation"] for e in events], [
            "inside", "cross_boundary", "cross_boundary", "unknown",
        ])
        self.assertTrue(all(e["action"] == "block" for e in events))
        self.assertEqual(events[2]["intersected_epochs"], [2, 2])

    def test_sub_float_precision_reversal_is_confirmed_from_literal(self):
        _, report = audit(["1600000000.00000002,60", "1600000000.00000001,60"],
                          chunk_rows=1, start=1600000000)
        self.assertEqual(report["events"][0]["kind"], "reversal")
        self.assertEqual(report["events"][0]["delta_seconds"], -1e-8)
        self.assertEqual(report["status"], "failed")
