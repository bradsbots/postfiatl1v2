# Validator-5 and the two signer committees: decision proposal

- **Operator:** Domagoj Ravlić (`dravlic`)
- **Date:** 2026-10-01 UTC
- **Asks:** one letter from the other lane, A, B or C (see the end).

## The situation in five lines

1. The live network `postfiat-wan-devnet-2` has six validators, all on `c93b2137`
   (`release/combined-fastpay-20260928`). Ordinary blocks need five of the six
   votes, and validator-5 counts there.
2. The **FastPay committee** (fast payments) lists validators 0–4 only, with
   quorum 5: every one of the five must sign
   ([r4 handoff][r4], "FastPay still needs validators 0–4 all online (quorum 5)").
   Since 2026-09-28 a payment before validator-5's turn no longer stalls the
   chain ([fix][fix28]), but validator-5 still signs no payment.
3. The **Ethereum bridge checkpoint committee** (`authority_epoch 1`) expects a
   checkpoint key with hash `b8d197ab…`; validator-5's key hash is `aad48519…`.
   Checkpoint certificates for every export to Ethereum and every return are
   therefore quorum-5 certificates signed by validators 0–4
   ([the other lane's 2026-10-01 handoff][nazgul];
   [`rollout-record.json`][rollout], `certificate_quorum: 5`).
4. **Consequence:** both groups need all five of validators 0–4. When any one
   of them is down (reboot, full disk, network), fast payments and every coin
   transfer to or from Ethereum stop until it is back. There is no spare
   signer.
5. The other lane asked for "a deliberate decision before the bridge committee
   is next rotated". This document is that decision, prepared.

## Options

| | What changes | What the other lane signs | What this lane prepares | Effort | Risk |
| --- | --- | --- | --- | --- | --- |
| **A. Both committees to six members, quorum stays 5** | FastPay: a new committee record (`committee_epoch` + 1, `valid_from_height`, six validators, quorum 5) under the recovery policy. Bridge: a new Ethereum policy with `authority_epoch 2` and a committee root that includes validator-5's checkpoint key, on the A666 asset. | The FastPay committee record (governance key); the bridge committee epoch 2 activation (a FastLane control certificate from validators 0–4); the A666 policy update, once an operation for it exists. No Ethereum transaction ([see below](#history-and-ethereum-side-2026-10-02)). | The unsigned transactions, a six-validator fork dry run of both rotations, the before and after read-backs, a rollback note (the previous committee stays valid until its `new_orders_through_height`). For the bridge: a governed route-policy update operation, which does not exist at `c93b2137`, and its release. | FastPay half: this lane 1–2 h. Bridge half: new code, tests and a six-validator release (days, estimated). The other lane: two or three signatures, no gas. | Low on PFTL (a committee record is additive and bounded by heights). The FastPay half takes effect only from height 10001. Nothing on the Ethereum side. Not during the conference week unless a quiet window exists. |
| **B. Bridge committee only** | The bridge half of A. FastPay stays as it is (validators 0–4 must all sign). | The epoch 2 activation and the A666 policy update, as in A. | The bridge half of A, including the new operation. | This lane: new code and a release (days, estimated); one or two signatures. | As A for the bridge; payments keep the single point of failure. |
| **C. Leave as is** | Nothing. | Nothing. | Nothing; the demo-day preflight command watches validators 0–4. | None. | One validator down stops payments and Ethereum transfers. That path is the demo path. |

**Lean: A, prepared now and executed in the first quiet window after the
conference.** B is half the work for half the benefit. C keeps a single point
of failure in the exact path the demos use.

## What is verified and what is inferred

- **Verified from records and code at `c93b2137`:**
  - Quorum 5 for the bridge certificates:
    [`deployments/combined-fastpay-20260928/observed/rollout-record.json`][rollout]
    (`certificate_quorum: 5`), and the quorum is read from the committee
    domain in [`crates/node/src/ethereum_checkpoint_signing.rs:2027`][ecs].
  - The FastPay committee record carries `committee_epoch`,
    `valid_from_height`, `new_orders_through_height`, `quorum` and the
    validator list
    ([`crates/types/src/fastpay_recovery_types.rs:130-140`][fprt]), and a
    committee cannot activate before the recovery policy
    ([`:320`][fprt320]).
  - The bridge committee is part of the asset's Ethereum policy
    (`ethereum_policy.authority_epoch`, `ethereum_policy.committee_root`,
    [`crates/types/src/market_nav_asset_types.rs:3190`][mnat]).
  - Validator-5's key hash differs from the committee's
    ([the other lane's handoff][nazgul]).
- **Inferred, to be confirmed in the dry run:** which governance key signs the
  FastPay committee record; the effort ranges. The Ethereum-side question is
  settled [below](#history-and-ethereum-side-2026-10-02): no Ethereum
  transaction.

## The question

Answer with one letter: **A**, **B** or **C**. If A or B, name a day for the
signatures, and this lane has the unsigned transactions and the dry-run record
ready before it.

## History and Ethereum side (2026-10-02)

A read-only check of the repository history and of the code at `c93b2137`.
No host was accessed.

**Validator-5 was not left out on purpose. Both committees were built with it,
and it dropped out when its key was rotated twice after that.**

1. **2026-07-18:** validator-5 is a genesis validator. Six validators finalized
   height 1 of `postfiat-wan-devnet-2` (genesis `ce22ca8c…`)
   ([`1643f23e`][genesis]).
2. **Both committees list six validators with the genesis keys, quorum 5 of 6.**
   - FastPay (`fastpay_recovery_committees`): epoch 1, valid from height 11,
     new orders through 10000 ([2026-09-25 stale-committee handoff][stale]).
   - Bridge (`fastswap_committees`): epoch 1. The A666 policy's `committee_root`
     is `a2eebcba…` ([route init][a666init]). Recomputing
     `FastSwapCommitteeV1::computed_root` over the six keys in the
     [A666 registry snapshot][a666reg] gives exactly `a2eebcba…`; validators
     0–4 alone give `006656f6…`.
   - `9f7ce761…` is a different root: the Consensus v2 block committee
     (`postfiat.consensus.committee-root.v2`), not the bridge committee.
3. **`b8d197ab…` is validator-5's own genesis key** (SHA-256 of its public key
   in that snapshot), not another validator's key.
4. **2026-08-25, height 917:** first Cobalt-authorized rotation, validator-5
   `b8d197ab…` → `d4b611b5…` ([activation packet][h917]).
5. **2026-08-26, height 924:** E5 drill rotation `d4b611b5…` → `aad48519…`
   ([`h924-registry-update.json`][h924]). Neither committee was rotated with
   it. The checkpoint key is the validator key file
   ([`ethereum_checkpoint_signing.rs:223-231`][ecs223]), so it was rotated in
   both steps.

Correction to line 2 above: the FastPay committee lists six validators, not
0–4. Validator-5's entry holds its genesis key, so only validators 0–4 can
sign, and quorum 5 needs all of them.

**Ethereum side: option A needs no Ethereum transaction.**

- The bridge committee is checked only on PFTL: at signing
  ([`ethereum_checkpoint_signing.rs:211-231`][ecs211]) and when a return is
  executed ([`pftl_uniswap_ethereum_verification.rs:357`][puev357], lookup by
  `authority_epoch` and `committee_root` at [`:380-400`][puev380]).
- On Ethereum, the A666 controller's `receipt_verifier` is immutable
  ([`PFTLUniswapHandoffController.sol:1454`][phc1454]). It is a
  `PFTLReceiptFinalityVerifierV1`
  ([`DeployA666PrimaryMarket.s.sol:144`][deploy144];
  [deployment record][a666eth]). That contract holds no committee, signer set
  or `authority_epoch` ([`PFTLReceiptFinalityVerifierV1.sol:110-129`][prfv110]).
  It accepts SP1 proofs, and the committee appears only as commitments that
  must be non-zero ([`:303-304`][prfv303]).
- The verifier that does hold a signer set, `ThresholdPFTLReceiptVerifier`
  ([`PFTLUniswapHandoffController.sol:185-189`][phc185]), is not used by A666.

**New facts from the code, and why the table changed:**

- **Bridge policy.** The route's `ethereum_verification_policy` is written
  only at route init ([`nav_vault_asset_execution.rs:4292`][nvae4292]);
  `PftlUniswapRouteEpochAdvanceOperation` does not carry it
  ([`transactions_mempool_receipts.rs:3037`][tmr3037]). No transaction at
  `c93b2137` can move A666 to `authority_epoch 2`, so B and the bridge half of A
  need a new operation and a release. A new route is no shortcut: the Ethereum
  verifier pins the route ID ([`PFTLReceiptFinalityVerifierV1.sol:115`][prfv115]).
- **Update 2026-10-05:** the issuer-signed `pftl_uniswap_route_bridge_policy_update`
  exists on `main` from the commit "Add an issuer-signed operation that updates a
  route's Ethereum bridge committee". It ships in the next validator release
  ([operation reference](../navcoins/navcoin-create-and-swap-spec.md#rotating-the-routes-ethereum-bridge-committee)).
- **Bridge committee epoch 2.** It is activated by a FastLane control
  certificate from the epoch 1 committee
  ([`fastswap_control.rs:167-171`][fsc167]) and needs a drained final epoch 1
  checkpoint ([`:386-410`][fsc386]). Validators 0–4 sign it. It is not an
  issuer-key signature.
- **FastPay.** The epoch 2 committee must start at the previous
  `new_orders_through_height` + 1, which is height 10001
  ([`owned_transfer_recovery.rs:875-889`][otr875]). The chain was at about
  1078 on 2026-10-01, so the FastPay half has no effect for roughly 8,900
  blocks unless that rule changes. The 2026-09-25 handoff noted the same limit.

## References

- [The other lane's 2026-10-01 handoff][nazgul]
- [FastPay stale-committee handoff, 2026-09-25][stale]
- [r4 handoff, 2026-09-25][r4]
- [FastPay effect-anchoring fix, 2026-09-28][fix28]
- [`docs/status/chain-state-current.md`][state]

[nazgul]: ../handoffs/2026-10-01___nazgul__navcoin_create_and_swap_build_phase0_and_bmnrc_opening.md
[r4]: ../handoffs/2026-09-25___postfiatchad__r4_view_recovery_chain_unstuck.md
[fix28]: ../handoffs/2026-09-28___dravlic__fastpay_stall_fixed_live_and_main_line_caught_up.md
[state]: ../status/chain-state-current.md
[rollout]: https://github.com/postfiatorg/postfiatl1v2/blob/release/combined-fastpay-20260928/deployments/combined-fastpay-20260928/observed/rollout-record.json
[ecs]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/node/src/ethereum_checkpoint_signing.rs#L2027
[fprt]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/types/src/fastpay_recovery_types.rs#L130-L140
[fprt320]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/types/src/fastpay_recovery_types.rs#L320
[mnat]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/types/src/market_nav_asset_types.rs#L3190
[stale]: ../handoffs/2026-09-25___postfiatchad__fastpay_down_stale_committee.md
[genesis]: https://github.com/postfiatorg/postfiatl1v2/tree/1643f23e86417174f416128f3fc231b7a714d4bb/docs/evidence/pfusdc-tier4-checkpoint-20260718T034713Z
[a666init]: https://github.com/postfiatorg/postfiatl1v2/blob/830dc9c731698e0c5e212cd04de3e88a0a378f6f/deployments/a666-mainnet-20260727/09-production-route-init/signed.json
[a666reg]: https://github.com/postfiatorg/postfiatl1v2/blob/830dc9c731698e0c5e212cd04de3e88a0a378f6f/deployments/a666-mainnet-20260727/12-opening-export-proof-snapshot/validator_registry.json
[a666eth]: https://github.com/postfiatorg/postfiatl1v2/blob/830dc9c731698e0c5e212cd04de3e88a0a378f6f/deployments/a666-mainnet-20260727/ethereum/deployment-state.json
[h917]: https://github.com/postfiatorg/postfiatl1v2/blob/830dc9c731698e0c5e212cd04de3e88a0a378f6f/benchmarks/cobalt-activation-live/packet/activation-status.json
[h924]: https://github.com/postfiatorg/postfiatl1v2/blob/830dc9c731698e0c5e212cd04de3e88a0a378f6f/benchmarks/cobalt-adversarial-verification/e5/h924-registry-update.json
[ecs211]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/node/src/ethereum_checkpoint_signing.rs#L211-L231
[ecs223]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/node/src/ethereum_checkpoint_signing.rs#L223-L231
[puev357]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/pftl_uniswap_ethereum_verification.rs#L357
[puev380]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/pftl_uniswap_ethereum_verification.rs#L380-L400
[phc185]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/ethereum-contracts/src/PFTLUniswapHandoffController.sol#L185-L189
[phc1454]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/ethereum-contracts/src/PFTLUniswapHandoffController.sol#L1454
[deploy144]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/ethereum-contracts/script/DeployA666PrimaryMarket.s.sol#L144
[prfv110]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/ethereum-contracts/src/PFTLReceiptFinalityVerifierV1.sol#L110-L129
[prfv115]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/ethereum-contracts/src/PFTLReceiptFinalityVerifierV1.sol#L115
[prfv303]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/ethereum-contracts/src/PFTLReceiptFinalityVerifierV1.sol#L303-L304
[nvae4292]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/nav_vault_asset_execution.rs#L4292
[tmr3037]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/types/src/transactions_mempool_receipts.rs#L3037
[fsc167]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/fastswap_control.rs#L167-L171
[fsc386]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/fastswap_control.rs#L386-L410
[otr875]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/owned_transfer_recovery.rs#L875-L889
