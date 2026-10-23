"""The committed storage evidence and its checksum manifest verify, and fail closed."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "benchmarks" / "storage-scaling"
FILES = (
    "README.md",
    "SHA256SUMS.txt",
    "campaign-stop-f3907ad5.json",
    "e2-bounded-work.json",
    "verify_development_evidence.py",
)


def _copy(root: Path) -> Path:
    target = root / "storage-scaling"
    target.mkdir()
    for name in FILES:
        shutil.copyfile(SOURCE / name, target / name)
    shutil.copytree(SOURCE / "g2-eea96ba6", target / "g2-eea96ba6")
    return target


def _run(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(root / "verify_development_evidence.py")],
        check=False,
        capture_output=True,
        text=True,
    )


class DevelopmentEvidenceTests(unittest.TestCase):
    def test_committed_evidence_verifies(self) -> None:
        completed = _run(SOURCE)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("storage-scaling-development-evidence-ok", completed.stdout)

    def test_missing_g2_receipt_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = _copy(Path(temporary))
            (root / "g2-eea96ba6" / "tamper" / "disk_full.json").unlink()
            completed = _run(root)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("checksum files differ", completed.stderr)

    def test_missing_g2_receipt_and_manifest_entry_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = _copy(Path(temporary))
            (root / "g2-eea96ba6" / "tamper" / "disk_full.json").unlink()
            manifest = root / "SHA256SUMS.txt"
            manifest.write_text(
                "".join(
                    line + "\n"
                    for line in manifest.read_text(encoding="utf-8").splitlines()
                    if not line.endswith("/disk_full.json")
                ),
                encoding="utf-8",
            )
            completed = _run(root)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("G2 tamper case receipt is unbound: disk_full", completed.stderr)

    def test_altered_g2_report_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = _copy(Path(temporary))
            report = root / "g2-eea96ba6" / "gate-report.json"
            report.write_text(
                report.read_text(encoding="utf-8").replace('"PASS"', '"FAIL"'),
                encoding="utf-8",
            )
            completed = _run(root)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("checksum mismatch for g2-eea96ba6/gate-report.json", completed.stderr)

    def test_extra_g2_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = _copy(Path(temporary))
            (root / "g2-eea96ba6" / "extra.json").write_text("{}\n", encoding="utf-8")
            completed = _run(root)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("checksum files differ", completed.stderr)


if __name__ == "__main__":
    unittest.main()
