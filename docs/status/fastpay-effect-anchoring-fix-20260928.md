# FastPay effect anchoring for a non-signer proposer

**Date:** 2026-09-28 UTC · **Branch:** `release/combined-fastpay-20260928` from
`release/combined-fastpay-20260925` (`1775ae33`, code tip `f60e9639`)

## Problem

After a FastPay payment, validators 0–4 hold a pending effect that the next
certified block must anchor. Validator-5 is not an eligible signer: its key was
rotated at block 924, and the replicated FastPay committee still lists the old
key. When validator-5 is the view-0 proposer, its proposal omits the effect,
the others refuse it and the height needs a view change. See the r4 handoff on
`main`, `docs/handoffs/2026-09-25___postfiatchad__r4_view_recovery_chain_unstuck.md`.

## How the effect flows today

- **Produce.** `owned_apply_v3` and `owned_unwrap_apply_v3`
  (`crates/node/src/fastpay_recovery_node.rs`) verify the certificate against
  the replicated committee (`apply_owned_*_certificate_v3`: owner signature,
  quorum of committee signatures, domain, epoch, policy, live inputs), sign a
  `FastPayApplyAckV1` and apply the effect.
- **Journal and restore.** `retain_fastpay_speculative_effect` writes the fence
  plus inverse data to `fastpay_speculative_effects_v1.json`, bound to the
  finalized tip. `read_fastpay_ledger` overlays the journal on the finalized
  ledger, so the effect survives a restart.
- **Anchor.** `fastpay_pre_state_effects_for_next_block`
  (`crates/node/src/block_replay_wallet.rs`) lists every confirmed,
  consensusless, unanchored fence. The proposal builders in
  `crates/node/src/mempool_proposals.rs` put that list in
  `fastpay_pre_state_effects`.
- **Vote check.** A voter rebuilds the proposal
  (`block_finality.rs`, `build_ordered_batch_proposal_with_timings`) and
  `reconcile_fastpay_pre_state_effects` rejects it with *"block proposal
  omitted a locally durable unanchored FastPay effect"*. Supplied effects the
  voter lacks are replayed from their certificates.

## Why validator-5 lacks the effect

The wallet proxy replicates the certificate to all six validators. On
validator-5, `owned_apply_v3` stops at `local_fastpay_signer_public_key`
("local signer key does not match the replicated FastPay committee") before
it verifies or journals anything. The eligibility check is correct for
**signing**; it was also, needlessly, a gate for **holding** the effect.

## Decision: fix (a), a non-signer holds the verified effect

When the requested validator is in the local validator registry but is not an
eligible signer for the certificate's committee, `owned_apply_v3` and
`owned_unwrap_apply_v3` run the same certificate verification and the same
durable journal write, sign nothing, and return a
`postfiat-fastpay-held-effect-v1` receipt instead of an acknowledgement. Its
next proposal then anchors the effect through the unchanged builder.

Fix (b), where a proposer includes effects it can verify, needs the proposer
to obtain certificates it was never sent: a new peer fetch in the proposal path
plus a new trust decision. Fix (a) reuses the delivery that already happens
and the verification signers already run, so it is smaller and safer.

No change to the committee, signer eligibility, quorum, signing, block format
or vote rules. The held receipt is not an acknowledgement. The proxy counts
only signed `postfiat-fastpay-apply-ack-v1` results toward quorum, and the
wallet verifies each acknowledgement signature, so it cannot inflate finality.
This needs no approval from the other lane.

## Invariants and tests

| Invariant | Test |
|---|---|
| No effect held or anchored without a verifiable certificate | Non-signer apply with four votes, a duplicate vote, a forged vote or a wrong domain fails and leaves ledger and journal unchanged |
| A non-signer never signs | Non-signer sign still fails; the held receipt carries no signature and is not a valid acknowledgement |
| No double anchoring | Re-applying on the non-signer is idempotent; after anchoring, `fastpay_pre_state_effects_for_next_block` is empty on all six |
| Restart safety | The held effect is re-read from the journal by a fresh store, re-proposed identically, and a repeated apply is idempotent |
| Identical state on all six | Six-node test: validator-5 proposes at view 0 right after a FastPay payment; all six vote, the block certifies at view 0 and all six have the same tip hash, state root and ledger |

Reproduce first: `fastpay_non_signer_view_zero_proposer_anchors_held_effect`
(`crates/node/src/tests/fastpay_non_signer_anchor.rs`) fails on the old code
exactly as on the fleet: validator-5's apply is refused, its view-0 proposal
omits the effect and validators 0–4 refuse to vote. On the new code it
certifies at view 0.

Existing suites that must stay green: the FastPay committee, recovery, restore
and anchoring tests and the n4/n6 view-recovery and timeout-certificate tests.

## Follow-up outside this change

The wallet proxy counts only signed acknowledgements, so it still reports
validator-5 as not applied and retries it from its outbox. That was already the
case and is harmless: each retry returns the same held receipt.
