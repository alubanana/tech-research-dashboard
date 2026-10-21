"""Behavior tests for cutoff, scenario math and immutable forecasting records."""
import copy
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
from system_core import probability, estimate, prepare, validate_hierarchy

ROOT = Path(__file__).resolve().parent
SYSTEM = json.loads((ROOT / "system.json").read_text(encoding="utf-8"))
IDS = [b["direction"] for b in SYSTEM["bets"]]
HIERARCHY = json.loads((ROOT / "hierarchy.json").read_text(encoding="utf-8"))

class ForecastTests(unittest.TestCase):
    def test_one_primary_theme_for_every_technology(self):
        validate_hierarchy(HIERARCHY, IDS)
        invalid = copy.deepcopy(HIERARCHY)
        invalid["themes"][0]["primaryDirections"].append("tandem")
        with self.assertRaises(AssertionError):
            validate_hierarchy(invalid, IDS)
    def test_hierarchy_revision_preserves_old_forecasts_and_snapshot(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            root = Path(temp)
            first = prepare(copy.deepcopy(SYSTEM), root, IDS)
            old = first["snapshots"][0]
            path = root / "snapshots" / (old["id"] + ".json")
            content = path.read_bytes()
            result = prepare(copy.deepcopy(SYSTEM), root, IDS, HIERARCHY)
            self.assertEqual(path.read_bytes(), content)
            current = next(s for s in result["snapshots"] if "hierarchy" in s)
            self.assertEqual(current["recordedAt"], max(SYSTEM["asOf"], HIERARCHY["reviewedAt"]))
            self.assertEqual(current["forecasts"], old["forecasts"])
            self.assertNotIn("hierarchy", old)
    def test_neutral_evidence_keeps_prior(self):
        self.assertAlmostEqual(probability([0]*5), .2)
    def test_order_and_bounds(self):
        self.assertLess(probability([-1]*5), probability([0]*5))
        self.assertLess(probability([0]*5), probability([1]*5))
        for scores in ([-2]*5, [0]*5, [2]*5):
            e = estimate(scores)
            self.assertTrue(0 < e["low"] <= e["p"] <= e["high"] < 1)
    def test_hindsight_leak_rejected(self):
        candidate = copy.deepcopy(SYSTEM)
        candidate["history"][0]["evidence"][0]["date"] = "2023-01-01"
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            with self.assertRaises(AssertionError):
                prepare(candidate, Path(temp), IDS)
    def test_undated_evidence_uses_access_date_and_rejects_future_access(self):
        candidate = copy.deepcopy(SYSTEM)
        source = candidate["bets"][0]["evidence"][0]["sources"][0]
        source["date"] = None
        source["availableAt"] = SYSTEM["asOf"]
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            prepare(candidate, Path(temp), IDS)
            source["availableAt"] = "2099-01-01"
            with self.assertRaises(AssertionError):
                prepare(candidate, Path(temp), IDS)
    def test_snapshot_never_overwritten_and_revisions_append(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            root = Path(temp)
            first = prepare(copy.deepcopy(SYSTEM), root, IDS)
            path = root / "snapshots" / (first["snapshots"][0]["id"] + ".json")
            original = path.read_bytes()
            prepare(copy.deepcopy(SYSTEM), root, IDS)
            self.assertEqual(path.read_bytes(), original)
            changed = copy.deepcopy(SYSTEM)
            changed["bets"][0]["evidence"][0]["score"] = 0
            second = prepare(changed, root, IDS)
            self.assertEqual(len(second["snapshots"]), 2)
            self.assertEqual(path.read_bytes(), original)
            self.assertTrue(first["snapshots"][0]["forecasts"][0]["evidence"])
    def test_premature_negative_settlement_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            root = Path(temp)
            initial = prepare(copy.deepcopy(SYSTEM), root, IDS)
            candidate = copy.deepcopy(SYSTEM)
            candidate["settlement"]["results"] = [{"snapshotId": initial["snapshots"][0]["id"],
                "forecastId": "worlds:industry", "outcome": 0, "sourceUrl": "https://example.org/result",
                "resolvedAt": SYSTEM["asOf"]}]
            with self.assertRaises(AssertionError):
                prepare(candidate, root, IDS)
    def test_brier_not_calibration_without_samples(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            result = prepare(copy.deepcopy(SYSTEM), Path(temp), IDS)
            self.assertEqual(result["validation"]["prospectiveResolved"], 0)
            self.assertIsNone(result["validation"]["brier"])
            self.assertFalse(result["validation"]["calibrated"])
    def test_consumer_snapshot_keeps_event_specific_evidence(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            result = prepare(copy.deepcopy(SYSTEM), Path(temp), IDS)
            forecasts = result["snapshots"][0]["forecasts"]
            b = next(b for b in SYSTEM["bets"] if b["id"] == "spatial")
            f = next(f for f in forecasts if f["id"] == "spatial:consumer")
            self.assertEqual(f["scores"], [e["score"] for e in f["evidence"]])
            self.assertEqual(f["evidence"], b["consumerEvidence"])
            self.assertNotEqual(f["evidence"], b["evidence"])
            self.assertFalse(any(f["id"] in ("editing:consumer", "organs:consumer") for f in forecasts))

if __name__ == "__main__":
    unittest.main()
