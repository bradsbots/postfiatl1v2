# Next validator release plan (after exchange-readiness-20261023)

Skeleton written 2026-10-23. The date suffix is a name, not a date. No date is promised: this
release starts after `exchange-readiness-20261023` is deployed and its three activations are done
([current plan](next-validator-release-plan-20261101.md)).

## Summary

1. `exchange-readiness-20261023` is cut at `6b1a0585`, the release merge of main `d9260e93`. It is being installed now ([current plan](next-validator-release-plan-20261101.md)).
2. Main past that cut changes no node behaviour so far. It adds an offline node tool, the wallet-proxy primed-route pin, storage packet tooling and docs (list below).
3. Rule kept from the current plan: changes that alter a consensus or state result get their own qualification; read-path and tooling changes ride along.
4. Qualification and rollout follow the current plan; nothing starts before the "Not before" rules hold.

## Already on main past the cut

`git log --oneline --first-parent d9260e93..origin/main`. Node behaviour changes are the lines that name `crates/node` or `crates/types` code that the node binary runs.

- [x] `62c0d56a`: `fastswap_bootstrap_payload --committee-file` writes the wallet's FastSwap activation payload for the committee an `ActivateCommittee` installed. Epoch-1 output is unchanged, and the tool reads validator state files through their `pftmac1:` line (`crates/node/src/bin/fastswap_bootstrap_payload.rs`; [runbook](../../runbooks/fastpay-committee-recovery.md#the-wallets-activation-payload-for-the-current-committee)). Offline operator tool, not the node binary.
- [x] `bb742ec7` (PR #95): wallet-proxy pins the finalized block hash as the parent of a primed proposer route, and readiness needs a matching `block_tip_hash` (`wallet-proxy/rpc-routing.js`). No valid request changes on an unforked chain. Wallet-proxy runtime, not the node binary.
- [x] `aa1ebd05`, `6e0e3df0`, `b055543c`, `4d8d2a72`: the storage packet verifier and packager (`python/postfiat_rpc/storage_scaling*.py`, `benchmarks/storage-scaling/package_packet.py`). They carry the runner's work gates, the stall rule and the 5 ms floor, and bind the gate reports and the verify-only output. `4d8d2a72` applies the 2026-10-23 review's changes. Tooling, not the node binary.
- [x] Docs only: `0f852110`, `9e4e267a`, `2cd26f4f`, `a364eaed`, `475436b4`, `35d0d477`, `92c388c2`.

## Candidates

Included only when ready and reviewed by the cut; none is promised.

- [ ] Storage packet verifier and packager. [Reviewed 2026-10-23](../../review/storage-verifier-acceptance-review-20261023.md): ACCEPT WITH CHANGES (keep the original window-report hashes; add refusal tests for the ported gates). `4d8d2a72` applies the changes; they are not yet checked. Tooling; it rides along once checked.
- [ ] Wallet helper for the epoch-2 activation payload. `fastswap_wallet_payload` (`read_payload`) still calls `validate_payload`, which accepts only committee epoch 1 (`crates/types/src/fastswap_types.rs:1519`). It therefore refuses the payload `62c0d56a` writes. That blocks StakeHub rehearsal precondition (a). Owner: this lane. Wallet tool; the three wallet binaries must be rebuilt.
- [ ] Z2 step 1b, when it lands ([Z2 plan](z2-advisory-flag-execution-plan-20261022.md)): the fork module, the manifest section, sidecar vendoring and prompt v13. Mostly in the fork and the sidecar; this repository records the hashes.
- [ ] SCT-08: bounded read-only evidence campaign, carried from the current plan ([inventory](../../review/defect-inventory-20260910.md)). Owner: this lane.
- [ ] Per-height vote records for the native reliability input (SCT-08 item 4, [decision](../../review/sct08-evidence-campaign-20261023.md#decision-the-native-reliability-input-2026-10-23)). For every finalized height, the node keeps each requested validator's vote outcome (accepted with vote ID, refused, or no answer by the round deadline), including votes after the quorum, and exports it in the signed snapshot. Without these records the reliability fact is "not available". Owner: this lane. Node change: it adds a stored and exported artifact without changing a consensus or state result, and gets its own qualification if review finds otherwise.
- [x] The account history index follows block commits. Done on main in the commit "Append account history index rows at block commit so the index follows the chain", and it ships with this release. After the block's receipts are durable, the commit appends its `account_tx` rows to the disk index. The append is idempotent on restart, never fails the commit, and leaves the archive scan in use while the index is behind. `account_tx_index_status` reports `disk_index_lag_blocks` and the disk range against the tip (`crates/node/src/block_finality.rs`, `storage_commit.rs`; [runbook](../../runbooks/account-tx-index.md#following-the-chain)). This is a node change to an operator cache, with no consensus, execution or state-commitment change. Before this, the index built on 2026-10-23 went stale after the next block.
- [ ] Bound the account history index rewrite per commit. Today each commit rewrites every touched account's history file and the aggregate `account_tx_index.json` whole. On the 1137 import (964 rows, 255 accounts) that is up to 373 rows (290 KB) for the busiest account, plus 1,757 row entries (1.36 MB) for the aggregate, and it grows with history. An append-only or chunked shard layout, and a metadata-only aggregate, need a new index schema with a rebuild on upgrade ([runbook](../../runbooks/account-tx-index.md#following-the-chain)). Owner: this lane. Operator-cache format change, no consensus change.
- [x] Python fallback gaps (no atomic-swap rows; shifted escrow, NFT and offer indexes). Closed on main by #57 (`1736aebb`, 2026-10-13) and #137. The current plan's row is stale.
- [ ] Still-open candidates of the current plan carry over: draft PRs #43–#46, archive-scan `truncated`, and the other lane's delayed-precommit fix. The delayed-precommit fix is a **consensus change and needs its own qualification**.

## Not before

- [ ] `exchange-readiness-20261023` deployed on all six validators, with `account-tx-index-build` run on each.
- [ ] Its three activations done: `recipient_format_activation_height` (#143), `rejected_tx_fee_activation_height` and `require_memo_activation_height` (#144).
- [ ] CI green on main at the cut commit (`docs-build`, `rust-ci`, `product-security-ci`).
- [ ] Full workspace suite at the cut commit (the release gate for the full suite; `rust-ci` `test` runs `cargo test --workspace --locked`).

## Qualification and rollout

As in the current plan: [Qualification](next-validator-release-plan-20261005.md#qualification) (~90 min after the suite) and [Rollout](next-validator-release-plan-20261005.md#rollout) (~60 min, one validator at a time, `rollback-one.sh` back to `exchange-readiness-20261023`). A consensus candidate adds its own qualification before the cut.

- [ ] Cut: release name, main commit, branch, two identical clean builds.
- [ ] History: signed canaries and their exact replays, checkpoint and full replay, recorded roots.
- [ ] Six new-build services on disposable copies; the rollback build reads them.
- [ ] Signed manifest, units, `systemd-analyze verify`, focused suites of this release's changes.
- [ ] Canary backup, fleet before-state, rollout (release day, operator's go).
