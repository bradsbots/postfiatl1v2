# Signer committee rotation: local dry run (2026-10-05)

Dry run of the "Activation after rollout" section of the
[next validator release plan](../plans/active/next-validator-release-plan-20261005.md),
on the work server only, at `main` `a683475a`. Nothing touched
`postfiat-wan-devnet-2`, its hosts or tunnels, and no live key was read.

## Setup

- **Six validators as in-process fixtures, not six processes.** The plan names
  `scripts/testnet-local-harness` or the six-node fixtures of the 2026-09-28
  FastPay fix. The fixtures were used. The harness was not used for three reasons:
  its default RPC base port is 27650, the port of the live tunnels; it has no
  path that creates a NAV route with an Ethereum bridge policy; and a route
  checkpoint needs an Ethereum RPC. No port was bound and no process was started.
- **Bridge half:** `signer_committee_rotation_dry_run_six_validators`
  (`crates/execution/src/signer_committee_rotation_dry_run_tests.rs`), on the
  fixture of `9e4d80be`. That fixture has a NAV asset, a route at
  `authority_epoch 1` and committee epoch 1 over six keys with quorum 5. The
  checkpoint key is the validator key
  (`crates/node/src/ethereum_checkpoint_signing.rs:223-231`), so a rotation is
  modelled as validator-5 holding seed 16 instead of seed 6.
- **FastPay half:** `fastpay_signer_committee_rotation_dry_run`
  (`crates/node/src/tests/signer_committee_rotation_dry_run.rs`). Six validator
  data directories run `init`, then a FastPay epoch-1 bootstrap over the
  genesis keys with quorum 5. Validator-5's key is then rotated through
  `validator-registry-update`, as on the live chain. The epoch-1 window is
  shortened: orders are accepted through height 10 instead of 10000.
- Reproduce with
  `cargo test -p postfiat-execution --lib signer_committee_rotation_dry_run -- --nocapture`
  and `cargo test -p postfiat-node --lib signer_committee_rotation_dry_run -- --nocapture`.
  The FastPay test deletes its directories, and the bridge test writes none.

## Bridge half

Heights are fixture heights. "Code" is the receipt code or the error that the
consensus function returned.

| # | Step | Signer | Height | Code | ms |
| --- | --- | --- | --- | --- | --- |
| 1 | Defect: epoch-1 checkpoint signed by validators 0–3 plus validator-5 (rotated) | 0–3, 5 | – | `InvalidVoteSignature` | 439 |
| | Same with validators 0–3 only | 0–3 | – | `BelowQuorum` | |
| | Validators 0–4 | 0–4 | – | ok: all five are needed | |
| 2 | Issuer update before activation | issuer | 10 | `pftl_uniswap_bridge_policy_committee_not_governed` | 29 |
| 3 | First epoch-1 FastLane checkpoint `ef1e94fd…` anchored | 0–4 | – | ok | 162 |
| 4 | Final epoch-1 checkpoint `37244323…` (`drain_ready`, no exit claims) anchored | 0–4 | – | ok | 577 |
| | Activation before that anchor | 0–4 | 10 | `MissingFinalCheckpoint` | |
| | Anchor signed by validators 0–3 plus validator-5 | 0–3, 5 | – | `InvalidSignature` | |
| 5 | `ActivateCommittee` epoch 2 (root `0e5eb0e3…`), control certificate | 0–4 | 10 | ok; the route stays at epoch 1 | 408 |
| | Same certificate with validators 0–3 plus validator-5 | 0–3, 5 | 10 | `InvalidControlCertificate` | |
| 6 | Issuer update with an open handoff (claims > 0) | issuer | 10 | `pftl_uniswap_bridge_policy_handoff_active` | 93 |
| | Issuer `pftl_uniswap_route_bridge_policy_update` to epoch 2 | issuer | 10 | `accepted`; route at `authority_epoch 2` | |
| 7 | Epoch-2 checkpoint, validators 0–3 plus rotated validator-5, validator-4 absent | 0–3, 5 | – | ok (5 of 6) | 499 |
| | Same with validator-5's stale key | 0–3, 5 | – | `InvalidVoteSignature` | |
| | Epoch-1 checkpoint against the epoch-2 route | 0–4 | – | `CommitteeMismatch` | |

The run took 2.5 s. The order is confirmed. Validators 0–4 are all required up
to and including `ActivateCommittee`, because that certificate and the final
checkpoint belong to epoch 1. Before the issuer update the route still verifies
against epoch 1. After the update, five of six signers are enough.

## FastPay half

The 10001 rule is not a constant. It is the previous record's
`new_orders_through_height` + 1 (`crates/execution/src/owned_transfer_recovery.rs:875-889`).
That field is chosen in the epoch-1 record, so a local chain can reach it. On
the live chain it is 10000.

| # | Step | Signer | Height | Code | ms |
| --- | --- | --- | --- | --- | --- |
| 1 | Epoch-1 bootstrap: six genesis keys, quorum 5, valid 2–10 | fixture | 1 | `fastpay_recovery_bootstrap_applied` | 1309 |
| 2 | Validator-5 key rotation (registry update) | fixture | 2 | accepted | 957 |
| 3 | `fastpay_committee_prepare` (the `fastpay-committee-prepare` code) | none | 3 | epoch 2, valid 11–19, replaced `validator-5`, 6 signers required | 1206 |
| | Same with `--valid-from 30` | none | 3 | refused: must start at exactly 11 | |
| 4 | Six `governance-authorization-sign`, assemble, `fastpay-recovery-governance-bootstrap-assemble`, apply | 0–5, validator-5 rotated key | 4 | `fastpay_recovery_committee_rotated` | 2281 |
| | Assembly with five authorizations | 0–4 | 4 | refused: one authorization per support vote | |
| | Validator-5 signing with its stale key | 5 | 4 | refused: key does not match the registry | |
| 5 | Blocks up to the epoch-2 start | fixture | 11 | – | 8520 |
| 6 | FastPay payment: `owned_sign_v3` and `owned_apply_v3` | 0–3, 5 (4 absent) | 11 | certified; five signed apply acks verified | 3797 |

The run took 18.1 s.

## What did not work or was not exercised

- **Missing tool, resolved.** No production command signed the
  `ActivateCommittee` or `StopPrepare` control certificate
  (`FastLaneControlVoteV1`, `FASTLANE_CONTROL_CONTEXT_V1`); only tests did.
  `fastswap-control-prepare`, `fastswap-control-vote-sign` and
  `fastswap-control-assemble` now do, one vote per validator key file
  ([commands](../navcoins/pftl-tools.md#fastswap-control-certificates)).
  Final-checkpoint votes still come from the FastSwap service request
  `fastswap_checkpoint_status` (`crates/node/src/rpc_cli.rs:1200`,
  `fastswap_service.rs:1402`), not from `ethereum-checkpoint-vote-sign`.
  Anchoring and control go through `mempool_submit_fastlane_primary_finality`
  (`AnchorCheckpoint`, `Control`).
- **Bridge steps at the consensus layer.** The bridge steps called the consensus
  functions directly (`anchor_fastlane_checkpoint`, `execute_fastlane_control`,
  `execute_asset_transaction`), not RPC or blocks. The open handoff was set as a
  ledger field, not produced by a real export. The Ethereum votes were signed
  directly; the node signing path with a rotated key is covered by
  `bridge_policy_update_moves_checkpoint_signing_to_rotated_committee`.
- **Drain with no FastSwap policy.** The fixture has no FastSwap policy, so
  draining needs no `StopPrepare` fence. On the live chain, every policy epoch
  in `fastswap_policy_snapshots` needs an epoch-1 `StopPrepare` fence (signed by
  0–4) before the final checkpoint (`fastswap_control.rs:391-405`).
- **Unsigned setup steps.** The FastPay epoch-1 bootstrap and the key rotation
  used the unsigned governance test fixture. Both are only setup; the epoch-2
  install was fully signed.
- **Live membership.** The live FastPay committee has six members, and
  validator-5's entry holds its stale genesis key. The
  [decision proposal](validator-5-signer-committees-decision-proposal-20261001.md)
  now says so too (corrected 2026-10-05). All of 0–4 must sign today. The prepare
  command builds the six-member record with current keys.

## Live FastSwap control path (2026-10-05 read)

This was a read-only check of validator-1 (`95.179.184.122`) against the code at
`c93b2137`. On the host: no node command, no RPC call and no write. Files were
read with `systemctl cat`, `ls`, `stat`, `jq` and `grep`. The WAL was streamed
to the work server for checking and then deleted there.

**Why the RPC answers `fastswap_unavailable`.** No flag, unit argument or
policy switches FastSwap on. `rpc-serve` opens the service on the first
`fastswap_*` or `fastlane_*` request (`crates/node/src/rpc_cli.rs:686-706`,
dispatch `:1019-1044`). Any error from that open is returned as
`fastswap_unavailable` (`:1314`), and the public message hides the cause
(`:4598`). The open (`crates/node/src/fastswap_service.rs:48-182`) runs these
checks in order: the ledger, `fastswap-v1/committee.json` and
`base-state.json`, the local key against the committee, and the committee
against the ledger. Then it opens the local store (`:113`). On validator-1,
the store open fails:

- All 26 records of `fastswap-v1.wal` (last written 2026-07-23) carry the
  legacy unkeyed checksum. Keyed integrity landed on 2026-08-08 (`4dbd80c2`).
  A normal open rejects legacy tags with "legacy WAL tag rejected; use explicit
  offline migration open" (`crates/storage/src/fastswap_store.rs:1707-1718`).
- Only `FastSwapStore::open_for_legacy_migration` accepts legacy tags
  (`fastswap_store.rs:475`). No command calls it, at `c93b2137` or on `main`.
  `storage-integrity-migrate-legacy` does not touch `fastswap-v1/`.
- The checks before the store open passed. This morning's two failed opens, at
  10:53:21 UTC, rewrote `fastswap-v1.lock` and created
  `fastswap-v1/.integrity.key`. Only the store open does either
  (`fastswap_store.rs:495-519`). So validator-1's key matches the committee,
  and that committee is registered in the ledger. This also means a
  `fastswap_*` request writes into the data directory.
- `rpc-events.ndjson` has 427 successful FastSwap requests, all within its first
  1,812 lines (July), and 7 `fastswap_unavailable`. The last two are this
  morning's `fastswap_capabilities` and `fastswap_checkpoint_status`.

**Control admission does not depend on the service.** `StopPrepare` and
`ActivateCommittee` are `FastLanePrimaryOperationV1::Control`. Admission
(`crates/node/src/mempool_proposals.rs:736-835`, reached from
`mempool_submit_fastlane_primary_finality` at `rpc_cli.rs:2377`) and blocks
(`execution_actions.rs:107`, `:516`) both run `execute_fastlane_control` on
ledger state only (`crates/execution/src/fastlane_primary.rs:205-215`,
`fastswap_control.rs:137-188`). `AnchorCheckpoint` works the same way
(`fastlane_primary.rs:166`). `fastswap-control-prepare` reads only the ledger.
Only the final-checkpoint votes need the service (`fastswap_checkpoint_status`,
`fastswap_service.rs:1402`). Each validator signs a checkpoint built from its
own `fastswap-v1` state.

**Where the records live.**

- **Canonical:** these `LedgerState` fields hold the records:
  `fastswap_policy_snapshots`, `fastswap_committees`,
  `fast_lane_prepare_fences`, `fast_lane_checkpoint_anchors` and
  `fastswap_activation_height` (`crates/types/src/market_nav_asset_types.rs:3716-3724`).
  Transactional storage is the default. Validator-1 has no
  `storage_backend_mode.json`, and its pointer names
  `transactional-generation-927/`. So the records are the `ledger` row of
  table `current_state_v1` in `postfiat-state-v1.redb`
  (`crates/storage/src/transactional.rs:46,72,85`). Without transactional
  storage they would be in `ledger.json`.
- **Local service state:** `<data-dir>/fastswap-v1/` holds `committee.json`
  and `base-state.json` (`fastswap_service.rs:31-33`). It also holds
  `fastswap-v1.wal`, `fastswap-v1.snapshot.json`, `fastswap-v1.lock`,
  `.integrity.key` and `vote-artifacts/` (`fastswap_store.rs:21-24`).
  Anchored checkpoints appear as `anchor_checkpoint` WAL records.

**What validator-1 shows.**

| Item | Value |
| --- | --- |
| Release | `combined-fastpay-20260928`; manifest `git_revision` `c93b2137`, executable `1f8b332d…` |
| RPC unit | `rpc-serve --unsafe-devnet-json-storage --data-dir /var/lib/postfiat/validator-1 … --allow-mempool-submit-finality --finality-* --keep-alive`. No FastSwap argument (none exists). The env file holds only deployment paths |
| `fastswap-v1/` | `committee.json` 42,673 B and `base-state.json` 2,003 B (2026-07-21); `fastswap-v1.wal` 177,899 B (2026-07-23); no snapshot; `vote-artifacts/` 25 files, newest 2026-07-23; `fastswap-v1.lock` 11 B and `.integrity.key` 48 B, both 2026-10-05 10:53:21 |
| Committee | Epoch 1, `validator-0` to `validator-5`, quorum 5, root `a2eebcbaa026e9a527861001dcc8f362f1173c5c2001a0eb4b3b7b5114e959c4ccdc6b01cc400f985e34fbc02095968e`. This is the A666 policy root in the [decision proposal](validator-5-signer-committees-decision-proposal-20261001.md#history-and-ethereum-side-2026-10-02) |
| WAL | 26 records: 5 `import_deposit`, 6 `reserve`, 6 `decision_lock`, 6 `apply_confirm`, 3 `apply_exit`. No `anchor_checkpoint`. All legacy tags |
| Canonical anchors | Not readable safely. The live ledger is in the 539 MB redb file, which any open locks. It was not opened or copied |
| `ledger.json` (2026-09-25; not the active store) | One committee (epoch 1), 0 anchors, no fences, one policy (epoch 1, heights 152–10000), activation 152, 3 redeemed exit claims |

**Result.** Validator-1's state has no drained final checkpoint for epoch 1,
so there is no id to record. Its WAL holds no anchor, and the stale
`ledger.json` holds none. The checkpoint has to be produced on release day,
and producing it needs the service.

**What release day must add or change.**

1. **Code (release scope):** an offline command that opens `fastswap-v1/` with
   `open_for_legacy_migration` and rewrites the WAL tags with the keyed MAC. It
   must refuse to run while a unit is running. No unit argument is needed.
2. **Rollout:** run that command on each validator while its two units are
   stopped in `apply-next`, before the new release starts. Before step 1,
   `fastswap_capabilities` and `fastswap_checkpoint_status` must answer on
   validators 0–4.
3. **Step 0:** read `fastswap_policy_snapshots` and
   `fast_lane_checkpoint_anchors` from the live ledger. The stale
   `ledger.json` suggests one policy epoch (1), so one `StopPrepare`.
4. **Step 2:** all of validators 0–4 must return matching `drain_ready` votes.
   If any one of them cannot open its store, the rotation is blocked.
5. **The other five hosts were not read.** Their `fastswap-v1` stores are from
   the same July releases, so the same refusal is expected. Before release
   day, confirm it read-only (`stat` the WAL and `.integrity.key`).

## Live procedure for release day

The release must be rolled out first. "Validators" means this lane's six
validator keys; "issuer" means the other lane's A666 issuer key.

| # | Step | Who signs | Rollback |
| --- | --- | --- | --- |
| 0 | Read-only: check that route `outstanding_bridge_claims_atoms` and pending returns are 0, list `fastswap_policy_snapshots`, and build epoch-2 `FastSwapCommitteeV1` from the six current registry keys (quorum 5) and record its root. Confirm that `fastswap_checkpoint_status` answers on validators 0–4; this needs the FastSwap WAL migration ([above](#live-fastswap-control-path-2026-10-05-read)) | none | none needed |
| 1 | Bridge: one epoch-1 `StopPrepare` per FastSwap policy epoch, if any: `fastswap-control-prepare --kind stop-prepare --policy-epoch N`, `fastswap-control-vote-sign` on each signer, `fastswap-control-assemble` | validators 0–4 | not reversible; stops new epoch-1 FastSwap prepares, which the handoff requires |
| 2 | Bridge: final drained epoch-1 checkpoint (`fastswap_checkpoint_status` votes, `AnchorCheckpoint`) | validators 0–4 | none needed; epoch 1 keeps signing |
| 3 | Bridge: `ActivateCommittee` epoch 2 with that checkpoint: `fastswap-control-prepare --kind activate-committee --epoch 2 --committee-root <step 0 root>`, `fastswap-control-vote-sign` on each of 0–4, `fastswap-control-assemble`, submit as `Control` | validators 0–4 (validator-5 cannot) | not reversible, and harmless until step 4 because the route stays at epoch 1. A wrong committee is not followed by step 4; a correction is epoch 3 after a new drained checkpoint |
| 4 | Bridge: `pftl_uniswap_route_bridge_policy_update` (`scripts/a666-build-route-epoch-advance.py bridge-policy-update`, `--committee-root` from step 0) | issuer | no reverse operation: the epoch only increases. Undoing it means another update to epoch 3 after steps 1–3 |
| 5 | Bridge: next checkpoint with `ethereum-checkpoint-vote-sign`, validator-5 using its current key; assemble 5 of 6 | validators | none needed |
| 6 | FastPay: `fastpay-committee-prepare` on one validator; confirm valid from 10001, six members, quorum 5 | none | discard |
| 7 | FastPay: `governance-authorization-sign` by all six at the agreed proposal slot, then `governance-amendment-assemble`, `fastpay-recovery-governance-bootstrap-assemble` and submit, all below height 10001 | all six validators, validator-5 with its current key | before commit: discard. After commit: no removal. Epoch 1 serves through 10000, and epoch 2 can only be followed by epoch 3 at its own end + 1 |

The FastPay record is signed by the six validators, not by a separate
governance key (`crates/node/src/governance.rs:521`). If nothing is
installed by height 10000, FastPay accepts no new orders after 10000.
