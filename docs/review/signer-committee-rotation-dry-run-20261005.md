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

- **No signer for the activation.** No production command signs the
  `ActivateCommittee` control certificate (`FastLaneControlVoteV1`,
  `FASTLANE_CONTROL_CONTEXT_V1`); only tests do. Checkpoint votes exist through
  the FastSwap service request `fastswap_checkpoint_status`
  (`crates/node/src/rpc_cli.rs:1200`, `fastswap_service.rs:1402`). Anchoring and
  control go through `mempool_submit_fastlane_primary_finality`
  (`AnchorCheckpoint`, `Control`). A control-vote sign and assemble command must
  exist before release day.
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
- **Live membership differs.** The [decision proposal](validator-5-signer-committees-decision-proposal-20261001.md)
  describes the live FastPay committee as validators 0–4, not six members with a
  stale key. Either way, all of 0–4 must sign today. The prepare command builds
  the six-member record in both cases.

## Live procedure for release day

The release must be rolled out first. "Validators" means this lane's six
validator keys; "issuer" means the other lane's A666 issuer key.

| # | Step | Who signs | Rollback |
| --- | --- | --- | --- |
| 0 | Read-only: check that route `outstanding_bridge_claims_atoms` and pending returns are 0, list `fastswap_policy_snapshots`, and build epoch-2 `FastSwapCommitteeV1` from the six current registry keys (quorum 5) and record its root | none | none needed |
| 1 | Bridge: one epoch-1 `StopPrepare` per FastSwap policy epoch, if any | validators 0–4 | not reversible; stops new epoch-1 FastSwap prepares, which the handoff requires |
| 2 | Bridge: final drained epoch-1 checkpoint (`fastswap_checkpoint_status` votes, `AnchorCheckpoint`) | validators 0–4 | none needed; epoch 1 keeps signing |
| 3 | Bridge: `ActivateCommittee` epoch 2 with that checkpoint | validators 0–4 (validator-5 cannot) | not reversible, and harmless until step 4 because the route stays at epoch 1. A wrong committee is not followed by step 4; a correction is epoch 3 after a new drained checkpoint |
| 4 | Bridge: `pftl_uniswap_route_bridge_policy_update` (`scripts/a666-build-route-epoch-advance.py bridge-policy-update`, `--committee-root` from step 0) | issuer | no reverse operation: the epoch only increases. Undoing it means another update to epoch 3 after steps 1–3 |
| 5 | Bridge: next checkpoint with `ethereum-checkpoint-vote-sign`, validator-5 using its current key; assemble 5 of 6 | validators | none needed |
| 6 | FastPay: `fastpay-committee-prepare` on one validator; confirm valid from 10001, six members, quorum 5 | none | discard |
| 7 | FastPay: `governance-authorization-sign` by all six at the agreed proposal slot, then `governance-amendment-assemble`, `fastpay-recovery-governance-bootstrap-assemble` and submit, all below height 10001 | all six validators, validator-5 with its current key | before commit: discard. After commit: no removal. Epoch 1 serves through 10000, and epoch 2 can only be followed by epoch 3 at its own end + 1 |

The FastPay record is signed by the six validators, not by a separate
governance key (`crates/node/src/governance.rs:521`). If nothing is
installed by height 10000, FastPay accepts no new orders after 10000.
