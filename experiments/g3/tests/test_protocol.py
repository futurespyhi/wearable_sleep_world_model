import tempfile
import unittest
from pathlib import Path

from sleep_g3.protocol import participant_split, read_catalog, select_records


class ProtocolTests(unittest.TestCase):
    def test_split_is_order_independent_and_disjoint(self):
        roster = [f"Bidslab{i:02d}" for i in range(47)]
        a = participant_split(roster)
        self.assertEqual(a, participant_split(list(reversed(roster))))
        self.assertIn("Bidslab00", a["train"])
        self.assertEqual([len(a[k]) for k in ("train", "validation", "test_sealed")], [33, 7, 7])
        self.assertEqual(len(set(sum(a.values(), []))), 47)

    def test_selection_never_loads_test_or_uses_label_values(self):
        roster = [f"Bidslab{i:02d}" for i in range(47)]
        split = participant_split(roster)
        catalog = {f"{p}/{n}/{f}": "0" * 64 for p in roster for n in (1, 2)
                   for f in ("hr.csv", "motion.csv", "labels.mat")}
        chosen = select_records(catalog, split)
        self.assertEqual(len(chosen), 6)
        self.assertFalse(set(r["participant"] for r in chosen) & set(split["test_sealed"]))
        self.assertEqual({r["night"] for r in chosen}, {"1"})

    def test_catalog_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "SHA256SUMS.txt"
            p.write_text("0" * 64 + " ../unexpected\n")
            with self.assertRaises(ValueError):
                read_catalog(p)


if __name__ == "__main__":
    unittest.main()
