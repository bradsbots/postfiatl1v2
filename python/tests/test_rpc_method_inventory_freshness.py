"""The committed RPC method inventory must match what the generator derives
from the current source, so docs/runbooks/rpc-method-inventory.{json,md}
cannot silently lag the node's method surface (they lagged by eleven methods
between 2026-07-17 and 2026-10-09, and by fifteen python_client flags once the
detector learned to read black-wrapped calls)."""

from __future__ import annotations

import difflib
import importlib.machinery
import importlib.util
import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GENERATOR = REPO / "scripts" / "testnet-rpc-method-inventory"
INVENTORY_JSON = REPO / "docs" / "runbooks" / "rpc-method-inventory.json"
INVENTORY_MD = REPO / "docs" / "runbooks" / "rpc-method-inventory.md"
METHOD_COVERAGE = REPO / "docs" / "rpc" / "method-coverage.md"


def _load_generator():
    loader = importlib.machinery.SourceFileLoader("testnet_rpc_method_inventory", str(GENERATOR))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def _methods(inventory: dict) -> dict[str, dict]:
    return {row["method"]: row for row in inventory["methods"]}


def _markdown_drift(expected: str, actual: str) -> str:
    """Unified diff of the rendered vs committed Markdown; empty when identical."""
    return "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile="render_markdown(rpc-method-inventory.json)",
            tofile=str(INVENTORY_MD),
        )
    )


# One in-memory corruption per rendered section: (section, exact committed
# text, replacement). Each original must occur exactly once in the committed
# Markdown; the committed file itself is never modified.
MARKDOWN_ROW_CORRUPTIONS = (
    (
        "methods",
        "| yolo_target_receipt | read_only_public |",
        "| yolo_target_receipt | operator_or_local_only |",
    ),
    (
        "xrp_like_coverage",
        "| server_info | covered | server_info |",
        "| server_info | missing | server_info |",
    ),
    (
        "gaps",
        "| public_write_edge_not_default | intentional_gate |",
        "| public_write_edge_not_default | scale_follow_up |",
    ),
    (
        "summary",
        "- Operator/local-only methods: ",
        "- Operator/local-only methods: 9",
    ),
)


class RpcMethodInventoryFreshnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.committed = json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))
        cls.generated = _load_generator().build_inventory()

    def test_committed_inventory_lists_exactly_the_methods_the_source_defines(self) -> None:
        committed = set(_methods(self.committed))
        generated = set(_methods(self.generated))
        self.assertEqual(
            sorted(generated - committed),
            [],
            "methods in the source but missing from the committed inventory; "
            "regenerate with scripts/testnet-rpc-method-inventory "
            "--output docs/runbooks/rpc-method-inventory.json "
            "--markdown docs/runbooks/rpc-method-inventory.md",
        )
        self.assertEqual(sorted(committed - generated), [], "stale methods in the committed inventory")

    def test_committed_rows_and_counts_match_the_generator(self) -> None:
        committed = _methods(self.committed)
        generated = _methods(self.generated)
        for name, row in generated.items():
            with self.subTest(method=name):
                # The whole derived row (posture, every gate flag, python_client,
                # sdk_constant, notes), so a detector or posture change cannot
                # leave the committed inventory stale in any column.
                self.assertEqual(committed[name], row)
        self.assertEqual(self.committed["counts"], self.generated["counts"])
        self.assertTrue(all(self.committed["checks"].values()), self.committed["checks"])

    def test_every_documented_public_read_is_a_read_only_public_method(self) -> None:
        rows = re.findall(r"^\| `([a-z_]+)` \| public read \|", METHOD_COVERAGE.read_text(encoding="utf-8"), re.M)
        self.assertGreaterEqual(len(rows), 21, rows)
        committed = _methods(self.committed)
        wrong = {name: committed.get(name, {}).get("posture") for name in rows if committed.get(name, {}).get("posture") != "read_only_public"}
        self.assertEqual(wrong, {})

    def _rendered_markdown(self) -> str:
        return _load_generator().render_markdown(self.committed, INVENTORY_JSON)

    def test_markdown_report_matches_the_committed_json_summary(self) -> None:
        # The whole document: header, date, every summary line, every
        # XRP-like coverage row, every gap row, and every method row.
        drift = _markdown_drift(self._rendered_markdown(), INVENTORY_MD.read_text(encoding="utf-8"))
        if drift:
            self.fail(
                "docs/runbooks/rpc-method-inventory.md differs from render_markdown(committed json); "
                "regenerate with scripts/testnet-rpc-method-inventory "
                "--output docs/runbooks/rpc-method-inventory.json "
                "--markdown docs/runbooks/rpc-method-inventory.md\n" + drift
            )

    def test_whole_document_comparison_detects_a_corrupted_row_in_every_section(self) -> None:
        rendered = self._rendered_markdown()
        committed = INVENTORY_MD.read_text(encoding="utf-8")
        self.assertEqual(_markdown_drift(rendered, committed), "")
        for section, original, corrupted in MARKDOWN_ROW_CORRUPTIONS:
            with self.subTest(section=section):
                self.assertEqual(committed.count(original), 1, original)
                tampered = committed.replace(original, corrupted, 1)
                drift = _markdown_drift(rendered, tampered)
                self.assertTrue(drift, f"{section} corruption was not detected")
                removed = [line for line in drift.splitlines() if line.startswith("-") and not line.startswith("---")]
                added = [line for line in drift.splitlines() if line.startswith("+") and not line.startswith("+++")]
                self.assertEqual(len(removed), 1, drift)
                self.assertEqual(len(added), 1, drift)
                self.assertIn(original, removed[0])
                self.assertIn(corrupted, added[0])


if __name__ == "__main__":
    unittest.main()
