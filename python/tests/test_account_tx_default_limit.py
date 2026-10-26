from __future__ import annotations

import unittest
from typing import Any
from unittest import mock

from postfiat_rpc import PostFiatRpcClient

ADDRESS = "pf-account"
# The node's window when `limit` is absent: MAX_READ_QUERY_LIMIT
# (crates/node/src/block_finality.rs, bounded_read_query_limit_with_max).
NODE_DEFAULT_LIMIT = 512


def _node_account_tx(method: str, params: dict[str, Any]) -> dict[str, Any]:
    """Answer `account_tx` the way the node does: it echoes the limit it used."""
    assert method == "account_tx"
    return {
        "address": params["address"],
        "from_height": params.get("from_height"),
        "to_height": params.get("to_height"),
        "scan_limit": params.get("limit", NODE_DEFAULT_LIMIT),
        "row_count": 0,
        "truncated": False,
        "rows": [],
    }


class AccountTxDefaultLimitTests(unittest.TestCase):
    def test_default_call_sends_the_limit_it_checks(self) -> None:
        client = PostFiatRpcClient("127.0.0.1:1234")
        with mock.patch.object(client, "_call", side_effect=_node_account_tx) as call:
            scan = client.account_tx(ADDRESS)
            scan_from = client.account_tx(ADDRESS, from_height=0)
        self.assertEqual(scan.scan_limit, 100)
        self.assertEqual(scan_from.scan_limit, 100)
        for sent in call.call_args_list:
            self.assertEqual(sent.args[1]["limit"], 100)

    def test_explicit_limit_is_unchanged(self) -> None:
        client = PostFiatRpcClient("127.0.0.1:1234")
        with mock.patch.object(client, "_call", side_effect=_node_account_tx) as call:
            scan = client.account_tx(ADDRESS, limit=50)
        self.assertEqual(scan.scan_limit, 50)
        self.assertEqual(call.call_args.args[1]["limit"], 50)


if __name__ == "__main__":
    unittest.main()
