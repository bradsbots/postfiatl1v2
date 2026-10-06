# Account History

Account history is exposed through server-side bounded `account_tx` reads and a
disk-backed retained-history index.

## What It Solves

Wallets, explorers, custodians, and operators need a way to ask:

- which transactions affected this account;
- when did a transaction finalize;
- which receipt proves it;
- can the history index be rebuilt from retained data.

## Current Capabilities

- bounded account transaction reads;
- disk-backed per-account shards;
- index status reporting;
- catch-up after archive pruning;
- Python client access;
- CSV-style export support.

## Result Window and `truncated`

`account_tx` returns at most `limit` rows in ascending height order. With
`from_height` it returns the oldest matching rows of the range; without it, the
newest. The disk index, the archive scan and the Python client fallback agree
on this.

`truncated` is `true` when a matching row was omitted. The archive scan (used
when no index is usable; `index_used: false`) and the Python fallback read at
most `limit` blocks. If the height range holds more blocks than that, the
unread blocks are not checked and `truncated` is `true` even if none of them
match: for these paths the flag means "possibly incomplete". Narrow the range
with `from_height`/`to_height`, or use `account_tx_history`, to page through
it.

## Evidence

- `docs/runbooks/account-tx-index.md`
- `scripts/postfiat-rpc-account-tx`
- `reports/testnet-six-wallet-account-tx-smoke/`
- `reports/testnet-account-tx-disk-index-smoke/`
