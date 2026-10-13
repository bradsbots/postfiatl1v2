from __future__ import annotations

import unittest
from unittest import mock

from postfiat_rpc import PostFiatRpcClient

BATCH_JSON = '{"batch_id":"00"}'
PARENT_HASH = "11" * 48
STATE_ROOT = "22" * 48


class ShieldBatchFinalityPinsTest(unittest.TestCase):
    """The proxy parent pins are all-or-none around the height: a parent hash
    or state root only means something relative to ``required_current_height``,
    and the node rejects a pin sent without it, so the wrapper refuses to build
    that request instead of sending it."""

    def setUp(self) -> None:
        self.client = PostFiatRpcClient("127.0.0.1:1234")

    def test_parent_hash_without_height_is_refused_before_the_call(self) -> None:
        with mock.patch.object(self.client, "_call") as call:
            with self.assertRaisesRegex(
                ValueError, "required_parent_hash requires required_current_height"
            ):
                self.client.shield_batch_finality(BATCH_JSON, required_parent_hash=PARENT_HASH)
        call.assert_not_called()

    def test_state_root_without_height_is_refused_before_the_call(self) -> None:
        with mock.patch.object(self.client, "_call") as call:
            with self.assertRaisesRegex(
                ValueError, "required_state_root requires required_current_height"
            ):
                self.client.shield_batch_finality(BATCH_JSON, required_state_root=STATE_ROOT)
        call.assert_not_called()

    def test_height_alone_is_sent_as_before(self) -> None:
        with mock.patch.object(self.client, "_call", return_value={"ok": True}) as call:
            self.client.shield_batch_finality(BATCH_JSON, required_current_height=7)
        call.assert_called_once_with(
            "shield_batch_finality",
            {"batch_json": BATCH_JSON, "proxy_required_current_height": 7},
        )

    def test_full_pins_are_sent_as_before(self) -> None:
        with mock.patch.object(self.client, "_call", return_value={"ok": True}) as call:
            self.client.shield_batch_finality(
                BATCH_JSON,
                required_current_height=7,
                required_parent_hash=PARENT_HASH,
                required_state_root=STATE_ROOT,
            )
        call.assert_called_once_with(
            "shield_batch_finality",
            {
                "batch_json": BATCH_JSON,
                "proxy_required_current_height": 7,
                "proxy_required_parent_hash": PARENT_HASH,
                "proxy_required_state_root": STATE_ROOT,
            },
        )

    def test_existing_argument_checks_are_kept(self) -> None:
        with mock.patch.object(self.client, "_call") as call:
            with self.assertRaisesRegex(ValueError, "required_current_height must be non-negative"):
                self.client.shield_batch_finality(BATCH_JSON, required_current_height=-1)
            with self.assertRaisesRegex(ValueError, "required_parent_hash must not be empty"):
                self.client.shield_batch_finality(
                    BATCH_JSON, required_current_height=7, required_parent_hash=""
                )
            with self.assertRaisesRegex(ValueError, "required_state_root must not be empty"):
                self.client.shield_batch_finality(
                    BATCH_JSON, required_current_height=7, required_state_root=""
                )
        call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
