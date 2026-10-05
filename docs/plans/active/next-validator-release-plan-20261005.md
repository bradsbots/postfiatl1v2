# Next validator release plan (after the conference)

Written 2026-10-05. Read by both lanes on 2026-10-07. Nothing is deployed
before 2026-10-07.

## Summary

1. The fleet (six validators of `postfiat-wan-devnet-2`) runs `combined-fastpay-20260928`: source `c93b2137`, executable `1f8b332d…`, deployed 2026-09-28 ([deployment](https://github.com/postfiatorg/postfiatl1v2/blob/main/deployments/combined-fastpay-20260928/README.md), [current state](../../status/chain-state-current.md)).
2. The next release carries the undeployed main changes plus an issuer-signed bridge policy update operation, which is required.
3. Optional if ready before the cut: an RPC accept loop without restart gaps, two `account_tx` truncation follow-ups and the other lane's delayed-precommit fix.
4. It is qualified and rolled out like 2026-09-28: ~90 min qualification after the full workspace suite, ~60 min rollout one validator at a time.
5. After rollout, both signer groups go back to six members, quorum 5 ([decision proposal](https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/review/validator-5-signer-committees-decision-proposal-20261001.md), lean A). The FastPay half cannot take effect before height 10001.

## Scope

`git diff --stat c93b2137 origin/main -- crates/` lists exactly the commits marked done below.

Done on main, undeployed:

- [x] `1bb15a78`: `deployment_manifest_verified` is `true` when a record written by `deployment-manifest-verify` is present. The release generator writes the new variable `POSTFIAT_DEPLOYMENT_VERIFIED_RECORD` into the unit environment (`crates/node/src/lifecycle_queries.rs:880`, `crates/node/src/batch_snapshot.rs:2556-2563`).
- [x] `b1d1928c` (PR #55): `account_tx` sets `truncated` only when rows are omitted (`crates/node/src/block_finality.rs`, `crates/node/src/tests/account_tx_truncation.rs`).
- [x] `0609cb01` (PR #48, contains `b560997c` and `72177cf3`): one Apple-only line in `crates/node/src/storage_migration.rs` (no Linux change), plus smoke and monitor tooling.
- [x] `dc7d9bb6` (PR #51): scripts only (`scripts/node-*`, `scripts/node-helper-smoke`). Not part of the binary.

Being built on main (2026-10-05 and 2026-10-06):

- [x] (1) Issuer-signed operation that updates an asset's Ethereum bridge policy (new `authority_epoch` and `committee_root`). At `c93b2137` the policy is written only at route creation (`crates/execution/src/nav_vault_asset_execution.rs:4292`) and no operation changes it. Done: `pftl_uniswap_route_bridge_policy_update` (`crates/types/src/transactions_mempool_receipts.rs:3105`, `crates/execution/src/nav_vault_asset_execution.rs:5643`).
- [ ] (2) FastPay committee record: six validators, quorum 5, under the recovery policy (`crates/types/src/fastpay_recovery_types.rs:130-140`, activation rule `:320`). This is a signed record, not new code; it is prepared with the release and submitted after it.
- [ ] (3) RPC accept budget replaced by behaviour without restart gaps. Today the release generator passes `--max-requests 10000` (`crates/node/src/batch_snapshot.rs:2403`). The loop stops at that count (`crates/node/src/rpc_serve_runtime.rs:105`, `crates/node/src/rpc_cli.rs:608`) and systemd restarts the service after 5 s (`RestartSec=5`).
- [ ] (3b) PR #55 follow-ups found in review on 2026-10-05:
    - [ ] Python fallback scan marks a result truncated when the matching rows exactly fill the limit (`python/postfiat_rpc/client.py:1609`, `:1636-1638`).
    - [ ] The archive scan reports truncated whenever the height range has more blocks than the limit, even when the skipped blocks hold no matching rows. Without a start height it returns the oldest rows of the window; the disk index returns the newest (`crates/node/src/block_finality.rs:576`).

Waiting on the other lane:

- [ ] (4) Fix for the delayed-precommit finding in the other lane's unreleased candidate. That candidate is not on main and must not be released until the fix lands. Included only when pushed and reviewed; not promised.

## Order and dependencies

Must land before the candidate is cut:

- [x] (1) on main with focused tests. It is the reason for this release; without it the bridge half of the signer-group change cannot happen.
- [ ] CI green on main at the cut commit.

Included if ready and reviewed by the cut, otherwise a later release:

- [ ] (3) and (3b). Neither blocks (1) or (2).
- [ ] (4), only after it is on main and reviewed.

Does not depend on the binary:

- [ ] (2) can be submitted on either release; its effect is limited by height (see Activation).

## Qualification

The 2026-09-28 pattern; about 90 min after the suite.

- [ ] Full workspace suite on the work server at the cut commit, started the day before (several hours). This is the release gate for the full suite.
- [ ] Cut `release/<new-release>` from that commit; create `deployments/<new-release>/` from `deployments/combined-fastpay-20260928/` (10 min).
- [ ] Two identical clean builds: same executable hash (30–40 min).
- [ ] History checks (15–20 min).
- [ ] Rotation and rollback rehearsal, including `rollback-one.sh` back to `combined-fastpay-20260928` (15–20 min).
- [ ] Signed deployment manifest; `deployment-manifest-verify` passes (10 min).
- [ ] Evidence packet in the release directory (10–15 min).

## Rollout

About 60 min, after the objection window closes.

- [ ] Before: `observe-fleet.py` shows six validators on `1f8b332d…` with the same height, tip and root (5 min).
- [ ] `scripts/postfiat-safe-rollout apply-next`, one validator at a time (validator-1 canary, then 0, 2, 3, 4, 5). One devnet faucet grant per validator; each must certify with the same tip and root on all six before the next (6 × 6–8 min).
- [ ] On divergence or a missed certification: stop, `rollback-one.sh` on the affected validator. The `combined-fastpay-20260928` executable and release directory stay on every host.
- [ ] Live checks: all 12 validator and RPC processes on the new hash; `deployment_manifest_verified=true` on every host; `account_tx` truncation reads (10 min).
- [ ] `deployments/combined-fastpay-20260928/demo-preflight.py` adapted to the new release directory, run read-only and passing (10 min).
- [ ] Update `docs/status/chain-state-current.md` and the deployment README.

## Activation after rollout

Both changes depend on the decision on the [proposal](https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/review/validator-5-signer-committees-decision-proposal-20261001.md). Validator-5 is a genesis member of both groups. Its key was rotated at heights 917 and 924, and neither group followed.

- [ ] Dry run of both changes on six local validators first, with before and after read-backs and a rollback note (FastPay half 1–2 h).
- [ ] Bridge group: the issuer signs the policy update from (1), with `authority_epoch 2` and a committee root that includes validator-5's checkpoint key. The epoch 2 committee is activated by a FastLane control certificate from validators 0–4 after the drained final epoch 1 checkpoint (`crates/execution/src/fastswap_control.rs:167-171`, `:386-410`). The dry run confirms the order. No Ethereum transaction.
- [ ] FastPay group: the governance key signs the epoch + 1 record (six validators, quorum 5); the dry run confirms which key. The committee cannot activate before the recovery policy (`fastpay_recovery_types.rs:320`). Its `valid_from_height` must equal the previous `new_orders_through_height` + 1, which is **10001** (`crates/execution/src/owned_transfer_recovery.rs:875-889`).
- **Limit:** the chain was at about height 1078 on 2026-10-01. Until height 10001, FastPay still needs validators 0–4 all online, and the current committee remains valid until then.

## Communication

- [ ] Inform the other lane; do not ask. Send the handoff and a Telegram message, both carrying this plan.
- [ ] The other lane may object until 2026-10-07 evening UTC. Rollout starts only after that.
- [ ] Ask for the activation signatures separately, under the decision proposal, after the dry run.

## Not in this release

- Relay units on the six hosts: host hygiene with its own window ([demo readiness](../../status/demo-readiness-20261001.md)).
- The SCT-06 traffic campaign.
- Anything that touches the conference-day setup.
- The other lane's unreleased candidate itself; at most the fix in (4).
