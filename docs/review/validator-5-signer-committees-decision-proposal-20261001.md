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
| **A. Both committees to six members, quorum stays 5** | FastPay: a new committee record (`committee_epoch` + 1, `valid_from_height`, six validators, quorum 5) under the recovery policy. Bridge: a new Ethereum policy with `authority_epoch 2` and a committee root that includes validator-5's checkpoint key, on the A666 asset. | The FastPay committee record (governance key); the A666 policy update (A666 issuer key); very likely one Ethereum transaction so the contracts that check certificates learn the new committee (inferred, see below). | The unsigned transactions, a six-validator fork dry run of both rotations, the before and after read-backs, a rollback note (the previous committee stays valid until its `new_orders_through_height`). | This lane 1–2 h; the other lane two or three signatures and possibly one Ethereum transaction with gas. | Low on PFTL (a committee record is additive and bounded by heights). Medium on the Ethereum side if a contract update is needed. Not during the conference week unless a quiet window exists. |
| **B. Bridge committee only** | The bridge half of A. FastPay stays 5 of 5. | The A666 policy update and the possible Ethereum transaction. | The bridge half of A. | This lane ~1 h; one or two signatures. | As A for the bridge; payments keep the single point of failure. |
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
- **Inferred, to be confirmed in the dry run:** that the Ethereum contracts
  which verify the certificates need their own update when the committee
  changes; which governance key signs the FastPay committee record; the effort
  ranges.

## The question

Answer with one letter: **A**, **B** or **C**. If A or B, name a day for the
signatures, and this lane has the unsigned transactions and the dry-run record
ready before it.

## References

- [The other lane's 2026-10-01 handoff][nazgul]
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
