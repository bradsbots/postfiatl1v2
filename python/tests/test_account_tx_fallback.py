from __future__ import annotations

import json
import unittest
from typing import Any
from unittest import mock

from postfiat_rpc import PostFiatRpcClient, RpcError

ADDRESS = "pf-account"


def _chain(transfers_per_block: list[list[str]]) -> list[dict[str, Any]]:
    """Blocks at heights 1..n; each inner list holds the recipients of its transfers."""
    return [
        {
            "header": {"height": height, "batch_kind": "transparent", "batch_id": f"b{height}"},
            "receipt_ids": [f"tx{height}-{index}" for index in range(len(recipients))],
            "recipients": recipients,
        }
        for height, recipients in enumerate(transfers_per_block, start=1)
    ]


class AccountTxFallbackScanTests(unittest.TestCase):
    def _scan(
        self,
        chain: list[dict[str, Any]],
        *,
        limit: int,
        from_height: int | None = 1,
        to_height: int | None = None,
    ):
        client = PostFiatRpcClient("127.0.0.1:1234")

        def blocks(*, from_height: int | None = None, limit: int | None = None):
            if from_height is None:
                return chain[-limit:]
            return [b for b in chain if b["header"]["height"] >= from_height][:limit]

        def batch_archive(*, batch_kind: str, batch_id: str, limit: int):
            block = next(b for b in chain if b["header"]["batch_id"] == batch_id)
            payload = {
                "transactions": [
                    {"unsigned": {"from": ADDRESS, "to": to, "amount": 1}}
                    for to in block["recipients"]
                ]
            }
            return [{"payload_json": json.dumps(payload)}]

        refused = RpcError("account_tx", {"code": "rpc_method_not_allowed", "message": "off"})
        with (
            mock.patch.object(client, "_call", side_effect=refused),
            mock.patch.object(client, "blocks", side_effect=blocks),
            mock.patch.object(client, "batch_archive", side_effect=batch_archive),
            mock.patch.object(client, "receipts", return_value=[]),
        ):
            scan = client.account_tx(
                ADDRESS, from_height=from_height, to_height=to_height, limit=limit
            )
        self.assertFalse(scan.index_used)
        return scan

    @staticmethod
    def _ids(scan) -> list[str]:
        return [row.tx_id for row in scan.rows]

    def test_exactly_full_page_is_not_truncated(self) -> None:
        scan = self._scan(_chain([["a", "b"]]), limit=2)
        self.assertEqual(self._ids(scan), ["tx1-0", "tx1-1"])
        self.assertFalse(scan.truncated)

    def test_exactly_full_block_window_is_not_truncated(self) -> None:
        scan = self._scan(_chain([["a"], ["b"]]), limit=2)
        self.assertEqual(self._ids(scan), ["tx1-0", "tx2-0"])
        self.assertFalse(scan.truncated)

    def test_one_more_row_is_truncated(self) -> None:
        scan = self._scan(_chain([["a", "b", "c"]]), limit=2)
        self.assertEqual(self._ids(scan), ["tx1-0", "tx1-1"])
        self.assertTrue(scan.truncated)

    def test_without_start_height_returns_the_newest_rows(self) -> None:
        scan = self._scan(_chain([["a", "b", "c"]]), limit=2, from_height=None)
        self.assertEqual(self._ids(scan), ["tx1-1", "tx1-2"])
        self.assertTrue(scan.truncated)

    def test_unscanned_blocks_in_range_mark_the_result_possibly_incomplete(self) -> None:
        # Same answer as the server scan: blocks past the window are not read.
        scan = self._scan(_chain([["a"], [], []]), limit=2)
        self.assertEqual(self._ids(scan), ["tx1-0"])
        self.assertTrue(scan.truncated)
        bounded = self._scan(_chain([["a"], [], []]), limit=2, to_height=2)
        self.assertFalse(bounded.truncated)

    def test_end_height_below_tip_without_start_height_reads_that_range(self) -> None:
        # The server reads the newest `limit` blocks at or below `to_height`.
        chain = _chain([["a"], ["b"], ["c"], ["d"]])
        whole = self._scan(chain, limit=3, from_height=None, to_height=3)
        self.assertEqual(self._ids(whole), ["tx1-0", "tx2-0", "tx3-0"])
        self.assertFalse(whole.truncated)
        newest = self._scan(chain, limit=2, from_height=None, to_height=3)
        self.assertEqual(self._ids(newest), ["tx2-0", "tx3-0"])
        self.assertTrue(newest.truncated)

    def test_start_and_end_height_read_the_exact_window(self) -> None:
        chain = _chain([["a"], ["b"], ["c"], ["d"]])
        scan = self._scan(chain, limit=3, from_height=2, to_height=3)
        self.assertEqual(self._ids(scan), ["tx2-0", "tx3-0"])
        self.assertFalse(scan.truncated)


if __name__ == "__main__":
    unittest.main()
