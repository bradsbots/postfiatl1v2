"""The memo arguments in the Python payment docs are lowercase hex, as the node requires.

`PaymentMemo::validate` refuses a memo field that is not even-length lowercase hex, so a
documented `memo_type="invoice"` fails at `transfer_fee_quote`.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = (
    "docs/python/examples.md",
    "docs/python/xrp-style-transactions.md",
    "docs/runbooks/python-rpc-client.md",
)
# memo_<field>="literal", optionally followed by .encode().hex()
MEMO_LITERAL = re.compile(r"\bmemo_(type|format|data)\s*=\s*\"([^\"]*)\"(\.encode\(\)\.hex\(\))?")
LOWER_HEX = re.compile(r"(?:[0-9a-f]{2})*")


class DocumentedMemoArgumentsTest(unittest.TestCase):
    def test_memo_examples_send_lowercase_hex(self) -> None:
        found = 0
        bad = []
        for doc in DOCS:
            text = (REPO_ROOT / doc).read_text(encoding="utf-8")
            for match in MEMO_LITERAL.finditer(text):
                found += 1
                field, literal, encoded = match.groups()
                if encoded or LOWER_HEX.fullmatch(literal):
                    continue
                line = text[: match.start()].count("\n") + 1
                bad.append(f"{doc}:{line}: memo_{field}={literal!r}")
        self.assertGreater(found, 0, "no memo examples found; update DOCS")
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
