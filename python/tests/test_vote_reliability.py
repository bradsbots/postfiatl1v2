"""The vote reliability window derives the SCT-08 native reliability fact.

Fixtures (python/tests/fixtures/vote_reliability/window), one directory per
proposer, four validators:
- height 1, proposed by validator-0: all four accepted;
- height 2, proposed by validator-1: validator-2 refused, validator-3 accepted
  after the quorum;
- height 3, proposed by validator-2: the round did not ask validator-3;
- height 4: no record anywhere.
The conflict directory holds a second record for height 2 from validator-3.
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from postfiat_rpc.vote_reliability import (
    NOT_AVAILABLE,
    VoteRecordConflict,
    VoteRecordError,
    derive_reliability,
    main,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "vote_reliability"
WINDOW = FIXTURES / "window"
CONFLICT = FIXTURES / "conflict"


def _by_validator(report: dict) -> dict[str, dict]:
    return {row["validator"]: row for row in report["validators"]}


class VoteReliabilityWindowTests(unittest.TestCase):
    def test_late_after_deadline_keeps_its_vote_id_and_does_not_count_as_accepted(self) -> None:
        # VR-01: a vote the writer still saw after the round deadline.
        record = json.loads((WINDOW / "validator-1" / "block-vote-records" / "height-00000000000000000002.json").read_text())
        for entry in record["entries"]:
            if entry["validator"] == "validator-3":
                entry["outcome"] = "late_after_deadline"
        with tempfile.TemporaryDirectory() as root:
            records = Path(root) / "block-vote-records"
            records.mkdir()
            (records / "height-00000000000000000002.json").write_text(json.dumps(record))
            rows = _by_validator(derive_reliability([records], 2, 2))
        self.assertEqual(rows["validator-3"]["late_after_deadline"], 1)
        self.assertEqual(rows["validator-3"]["accepted"], 0)
        self.assertEqual(rows["validator-3"]["no_answer"], 0)
        self.assertEqual(rows["validator-3"]["uptime_window_bps"], 0)

    def test_counts_per_validator(self) -> None:
        rows = _by_validator(derive_reliability([str(WINDOW)], 1, 3))
        self.assertEqual(sorted(rows), ["validator-0", "validator-1", "validator-2", "validator-3"])
        self.assertEqual(rows["validator-0"]["heights_requested"], 3)
        self.assertEqual(rows["validator-0"]["accepted"], 3)
        self.assertEqual(rows["validator-2"]["accepted"], 2)
        self.assertEqual(rows["validator-2"]["refused"], 1)
        self.assertEqual(rows["validator-2"]["refused_by_class"], {"block_view_is_stale": 1})
        self.assertEqual(rows["validator-3"]["heights_requested"], 2)
        self.assertEqual(rows["validator-3"]["answered_after_quorum"], 1)
        self.assertEqual(rows["validator-3"]["no_answer"], 0)

    def test_ratio_is_accepted_votes_over_window_heights_in_bps(self) -> None:
        report = derive_reliability([str(WINDOW)], 1, 3)
        rows = _by_validator(report)
        self.assertEqual(report["window_heights"], 3)
        self.assertEqual(report["status"], "available")
        self.assertEqual(rows["validator-0"]["uptime_window_bps"], 10_000)
        self.assertEqual(rows["validator-1"]["uptime_window_bps"], 10_000)
        # 2 of 3 heights, floored: 6666 bps.
        self.assertEqual(rows["validator-2"]["uptime_window_bps"], 6_666)

    def test_validator_missing_from_a_record_is_not_available(self) -> None:
        row = _by_validator(derive_reliability([str(WINDOW)], 1, 3))["validator-3"]
        self.assertEqual(row["uptime_window_bps"], NOT_AVAILABLE)
        self.assertEqual(row["heights_without_entry"], ["3"])

    def test_height_without_any_record_makes_every_validator_not_available(self) -> None:
        report = derive_reliability([str(WINDOW)], 1, 4)
        self.assertEqual(report["status"], "not_available")
        self.assertEqual(report["heights_without_record"], ["4"])
        for row in report["validators"]:
            self.assertEqual(row["uptime_window_bps"], NOT_AVAILABLE, row["validator"])

    def test_named_validator_without_entries_is_not_available(self) -> None:
        rows = _by_validator(derive_reliability([str(WINDOW)], 1, 3, validators=["validator-4"]))
        self.assertEqual(rows["validator-4"]["heights_requested"], 0)
        self.assertEqual(rows["validator-4"]["uptime_window_bps"], NOT_AVAILABLE)

    def test_one_directory_per_validator_combines_like_the_parent_folder(self) -> None:
        separate = [str(WINDOW / name) for name in ("validator-0", "validator-1", "validator-2")]
        self.assertEqual(
            derive_reliability(separate, 1, 3)["validators"],
            derive_reliability([str(WINDOW)], 1, 3)["validators"],
        )

    def test_identical_duplicate_record_is_not_a_conflict(self) -> None:
        report = derive_reliability([str(WINDOW), str(WINDOW / "validator-1")], 1, 3)
        self.assertEqual(report["status"], "available")

    def test_two_proposers_claiming_one_height_are_refused(self) -> None:
        with self.assertRaises(VoteRecordConflict) as caught:
            derive_reliability([str(WINDOW), str(CONFLICT)], 1, 3)
        [conflict] = caught.exception.conflicts
        self.assertEqual(conflict["height"], 2)
        self.assertEqual(
            sorted(source["proposer"] for source in conflict["records"]),
            ["validator-1", "validator-3"],
        )

    def test_inconsistent_record_is_refused(self) -> None:
        record = json.loads(
            (WINDOW / "validator-0" / "block-vote-records" / "height-00000000000000000001.json").read_text()
        )
        del record["entries"][1]["vote_id"]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "block-vote-records"
            target.mkdir()
            (target / "height-00000000000000000001.json").write_text(json.dumps(record))
            with self.assertRaises(VoteRecordError):
                derive_reliability([tmp], 1, 1)

    def test_cli_prints_json_and_refuses_conflicts(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(["--records", str(WINDOW), "--from-height", "1", "--to-height", "3"])
        self.assertEqual(code, 0)
        self.assertEqual(_by_validator(json.loads(out.getvalue()))["validator-2"]["uptime_window_bps"], 6_666)

        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = main(
                ["--records", str(WINDOW), "--records", str(CONFLICT), "--from-height", "1", "--to-height", "3"]
            )
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out.getvalue())["status"], "refused_conflicting_records")

    def test_cli_table(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(["--records", str(WINDOW), "--from-height", "1", "--to-height", "4", "--table"])
        self.assertEqual(code, 0)
        text = out.getvalue()
        self.assertIn("validator-2", text)
        self.assertIn(NOT_AVAILABLE, text)
        self.assertIn("heights without a record: 4", text)

    def test_cli_table_shows_late_after_deadline(self) -> None:
        # The table's columns add up to `requested`, also for a vote the writer
        # saw after the round deadline (VR-01), and the answered_after_quorum
        # count has its own column.
        record = json.loads((WINDOW / "validator-1" / "block-vote-records" / "height-00000000000000000002.json").read_text())
        for entry in record["entries"]:
            if entry["validator"] == "validator-3":
                entry["outcome"] = "late_after_deadline"
        with tempfile.TemporaryDirectory() as root:
            records = Path(root) / "block-vote-records"
            records.mkdir()
            (records / "height-00000000000000000002.json").write_text(json.dumps(record))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["--records", str(records), "--from-height", "2", "--to-height", "2", "--table"])
        self.assertEqual(code, 0)
        lines = out.getvalue().splitlines()
        self.assertEqual(
            lines[1].split(),
            [
                "validator",
                "requested",
                "accepted",
                "refused",
                "no_answer",
                "late_after_deadline",
                "after_quorum",
                "uptime_window_bps",
            ],
        )
        row = next(line.split() for line in lines if line.startswith("validator-3 "))
        self.assertEqual(row, ["validator-3", "1", "0", "0", "0", "1", "1", "0"])


if __name__ == "__main__":
    unittest.main()
