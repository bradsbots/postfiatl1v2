"""account_tx rows an exchange reconciles from: payment_v2 memo contents and
shielded-withdrawal credits, from the server result and from the client-side
archive fallback (which must number rows like the server archive scan)."""

from __future__ import annotations

import json
import unittest
from typing import Any
from unittest import mock

from postfiat_rpc import PostFiatRpcClient, RpcError

ADDRESS = "pf-exchange-deposit"
OTHER = "pf-other"
ASSET_ID = "a" * 96
DEPOSIT_TAG_HEX = "customer-4242".encode().hex()


def _fallback_rows(block: dict[str, Any], payload: dict[str, Any], receipts=None):
    client = PostFiatRpcClient("127.0.0.1:1234")
    refused = RpcError("account_tx", {"code": "rpc_method_not_allowed", "message": "off"})
    with (
        mock.patch.object(client, "_call", side_effect=refused),
        mock.patch.object(client, "blocks", return_value=[block]),
        mock.patch.object(
            client, "batch_archive", return_value=[{"payload_json": json.dumps(payload)}]
        ),
        mock.patch.object(client, "receipts", return_value=receipts or []),
    ):
        scan = client.account_tx(ADDRESS, from_height=1, limit=10)
    assert not scan.index_used
    return scan.rows


def _block(batch_kind: str, receipt_count: int) -> dict[str, Any]:
    return {
        "header": {"height": 1, "batch_kind": batch_kind, "batch_id": "b1"},
        "receipt_ids": [f"tx-{index}" for index in range(receipt_count)],
    }


class PaymentV2MemoRowTests(unittest.TestCase):
    def test_server_rows_keep_memo_contents(self) -> None:
        memos = [
            {
                "memo_type": "deposit_tag".encode().hex(),
                "memo_format": "",
                "memo_data": DEPOSIT_TAG_HEX,
                "memo_type_text": "deposit_tag",
                "memo_data_text": "customer-4242",
            }
        ]
        row = {
            "tx_id": "tx-0",
            "block_height": 1,
            "batch_kind": "transparent",
            "batch_id": "b1",
            "transaction_index": 0,
            "transaction_kind": "payment_v2",
            "from": OTHER,
            "to": ADDRESS,
            "amount": 10,
            "fee": 1,
            "sequence": 1,
            "memo_hash": "f" * 96,
            "memo_count": 1,
            "memo_bytes": 24,
            "memos": memos,
            "accepted": True,
            "receipt_code": "accepted",
        }
        result = {
            "address": ADDRESS,
            "from_height": None,
            "to_height": None,
            "scan_limit": 10,
            "row_count": 1,
            "truncated": False,
            "index_used": True,
            "rows": [row],
        }
        client = PostFiatRpcClient("127.0.0.1:1234")
        with mock.patch.object(client, "_call", return_value=result):
            scan = client.account_tx(ADDRESS, limit=10)
        parsed = scan.rows[0]
        self.assertEqual(parsed.memo_count, 1)
        self.assertEqual(parsed.memos, tuple(memos))
        self.assertEqual(parsed.to_dict()["memos"], memos)

    def test_fallback_decodes_memo_contents(self) -> None:
        payload = {
            "transactions": [],
            "payments_v2": [
                {
                    "unsigned": {
                        "from": OTHER,
                        "to": ADDRESS,
                        "amount": 10,
                        "fee": 1,
                        "sequence": 1,
                        "memos": [
                            {"memo_type": "", "memo_format": "", "memo_data": DEPOSIT_TAG_HEX},
                            {"memo_data": "ff00fe"},
                        ],
                    }
                }
            ],
        }
        rows = _fallback_rows(_block("transparent", 1), payload)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].memo_count, 2)
        self.assertEqual(
            rows[0].memos,
            (
                {
                    "memo_type": "",
                    "memo_format": "",
                    "memo_data": DEPOSIT_TAG_HEX,
                    "memo_data_text": "customer-4242",
                },
                {"memo_type": "", "memo_format": "", "memo_data": "ff00fe"},
            ),
        )

    def test_non_payment_rows_have_no_memos(self) -> None:
        payload = {"transactions": [{"unsigned": {"from": OTHER, "to": ADDRESS, "amount": 1}}]}
        rows = _fallback_rows(_block("transparent", 1), payload)
        self.assertIsNone(rows[0].memos)
        self.assertIsNone(rows[0].to_dict()["memos"])

    def test_issued_payment_v2_fallback_returns_deposit_tag(self) -> None:
        payload = {
            "asset_transactions": [{"unsigned": {
                "transaction_kind": "issued_payment_v2",
                "source": OTHER,
                "fee": 40,
                "sequence": 1,
                "operation": {
                    "operation": "issued_payment_v2",
                    "from": OTHER,
                    "to": ADDRESS,
                    "issuer": OTHER,
                    "asset_id": ASSET_ID,
                    "amount": 10,
                    "memos": [{"memo_type": "", "memo_format": "", "memo_data": DEPOSIT_TAG_HEX}],
                },
            }}],
        }
        rows = _fallback_rows(_block("transparent", 1), payload)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].memo_count, 1)
        self.assertEqual(rows[0].memos[0]["memo_data_text"], "customer-4242")


class ShieldedWithdrawalRowTests(unittest.TestCase):
    def test_fallback_lists_shielded_withdrawal_credits(self) -> None:
        payload = {
            "batch_id": "b1",
            "actions": [
                {
                    "kind": "orchard_withdraw_v1",
                    "action_json": json.dumps({"pool_id": "orchard-v1"}),
                    "to": ADDRESS,
                    "amount": 2500,
                    "fee": 7,
                    "policy_id": "p",
                    "disclosure_hash": "d",
                },
                {"kind": "orchard_action_v1", "action_json": "{}"},
                {
                    "kind": "asset_orchard_private_egress_v1",
                    "pool_id": "asset-orchard-v1",
                    "to": ADDRESS,
                    "asset_id": ASSET_ID,
                    "amount": 900,
                    "fee": 0,
                },
                {
                    "kind": "orchard_withdraw_v1",
                    "action_json": "{}",
                    "to": OTHER,
                    "amount": 1,
                    "fee": 1,
                },
            ],
        }
        receipts = [{"tx_id": "tx-0", "accepted": True, "code": "accepted"}]
        rows = _fallback_rows(_block("shielded", 4), payload, receipts)
        self.assertEqual(
            [
                (
                    row.transaction_index,
                    row.tx_id,
                    row.transaction_kind,
                    row.tx_role,
                    row.sender,
                    row.recipient,
                    row.amount,
                    row.fee,
                    row.asset_id,
                    row.batch_kind,
                )
                for row in rows
            ],
            [
                (
                    0,
                    "tx-0",
                    "orchard_withdraw_v1",
                    "shielded_withdrawal",
                    "orchard-v1",
                    ADDRESS,
                    2500,
                    7,
                    None,
                    "shielded",
                ),
                (
                    2,
                    "tx-2",
                    "asset_orchard_private_egress_v1",
                    "shielded_withdrawal",
                    "asset-orchard-v1",
                    ADDRESS,
                    900,
                    0,
                    ASSET_ID,
                    "shielded",
                ),
            ],
        )
        self.assertEqual((rows[0].accepted, rows[0].receipt_code), (True, "accepted"))
        self.assertEqual(rows[0].sequence, 0)


class FastLaneReceiptOffsetTests(unittest.TestCase):
    def test_fastlane_primary_receipts_shift_escrow_rows(self) -> None:
        # Receipt ids: 0 transfer, 1 FastLane primary, 2 escrow.
        payload = {
            "transactions": [{"unsigned": {"from": ADDRESS, "to": OTHER, "amount": 1}}],
            "fastlane_primary_transactions": [{"operation": {"kind": "anchor_checkpoint"}}],
            "escrow_transactions": [
                {
                    "unsigned": {
                        "transaction_kind": "escrow_create",
                        "fee": 1,
                        "sequence": 2,
                        "operation": {
                            "operation": "escrow_create",
                            "owner": ADDRESS,
                            "recipient": OTHER,
                            "amount": 4,
                        },
                    }
                }
            ],
        }
        rows = _fallback_rows(_block("transparent", 3), payload)
        self.assertEqual(
            [(row.transaction_index, row.tx_id) for row in rows],
            [(0, "tx-0"), (2, "tx-2")],
        )


if __name__ == "__main__":
    unittest.main()
