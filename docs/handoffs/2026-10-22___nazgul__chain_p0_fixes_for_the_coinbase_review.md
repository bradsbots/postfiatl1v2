# Chain P0 fixes for the Coinbase review

- **Operator:** Claude ("Nazgûl") for the founder's lane (`nazgul`)
- **Date:** 2026-10-22 UTC
- **Responding to:** [dravlic, 2026-10-22](2026-10-22___dravlic__reserve_proof_conditions_done_and_both_replays_in.md)

> **Update, 2026-10-23:** All eight PRs in this merge queue are now merged
> through #145. See the [integration and developer handoff](2026-10-23___codex__chain_pr_merge_handoff.md)
> for the combined fixes, passing checks and remaining release gates. This
> update does not record a deployment or governance activation.

## BLUF

Coinbase's listing team is reviewing PFTL. This lane fixed the chain and
documentation gaps that review would hit first. All of it is in open PRs, with
tests; nothing is merged, deployed, signed or activated.

| PR | What it fixes | Consensus? |
| --- | --- | --- |
| [#140](https://github.com/postfiatorg/postfiatl1v2/pull/140) | Ten documentation contradictions: the whitepaper signing fence, the SLH-DSA recovery diagram, the custody model, the turnstile, envelope line references, the vendored `fips204` disclosure, defect-inventory deployment notes, `deny.toml` dates, a `verify-vendored-halo2` locale bug, `SECURITY.md` storage, the chain-state summary | No |
| [#141](https://github.com/postfiatorg/postfiatl1v2/pull/141) | Publishes the Orchard verifying-key fingerprints, with `scripts/verify-orchard-vks` | No |
| [#142](https://github.com/postfiatorg/postfiatl1v2/pull/142) | Memo contents in `tx`/`account_tx`; shielded withdrawals in `account_tx`; a receipt-position bug that broke history for blocks mixing FastLane with escrow, NFT or offer transactions | No (index schema v2) |
| [#143](https://github.com/postfiatorg/postfiatl1v2/pull/143) | Rejects malformed recipients at RPC and mempool now, and in execution after `recipient_format_activation_height`; adds an optional mixed-case address checksum with published vectors | Yes, gated |
| [#144](https://github.com/postfiatorg/postfiatl1v2/pull/144) | Fee claim on validly signed transactions that fail on their effect (`tec_*`), after `rejected_tx_fee_activation_height`; a require-memo account flag and `issued_payment_v2`, after `require_memo_activation_height` | Yes, gated |

**PR #49:** your blocker is cleared. This lane pushed three commits to your
branch (`066323b4..d01cb121`). Together they add:

- the regenerated successor policy manifests, which needed no keys;
- the candidate guest identity, built twice and byte-identical;
- a merge of `main`;
- a replay of the old successor's epochs 7 and 8 on a host pinned at
  `a2516a1b`, because the stricter new types reject those old inputs.

All nine checks pass. There is a summary comment on the PR.

## Current state

- **CI at the time of writing:**
  - #140, #141 and #49 are fully green.
  - #142 and #143 pass everything except `open-reserve-proof-kit`. That
    failed upstream: the SP1 installer found no release
    `succinct-1.94.0-64bit`. A re-run is requested.
  - #144's workspace `test` job was still running.
- **Pre-activation behaviour.** #143 and #144 keep every pre-activation
  receipt and ledger byte-identical in their tests. The full node library
  suites pass: 434 on #144; on #143, 426 plus the 7 fixed fixtures.
- **Consensus code is unreplayed.** Neither PR was replayed against the real
  devnet archive; this host has no archive.
- The listing package
  ([PR #139](https://github.com/postfiatorg/postfiatl1v2/pull/139)) now points
  each gap to these PRs and says plainly that they are not merged or deployed.

## Next decision or action

(a) **Review #143 and #144.** They are consensus changes in your area.

(b) **Release gate before any deployment.** Build the release from merged
`main`.
- Run your exact replays (height 924 and the current head) with it, and
  confirm identical state roots.
- Only then roll it out with `scripts/postfiat-safe-rollout`.
- Activate the new heights by governance only after all six validators run
  it. Older binaries reject the new amendment kinds and the new
  `account_set` and `issued_payment_v2` transactions.

(c) **Merge order and conflicts:**
1. #138, then #139.
2. #140: take #138's README and add the `redb` fact.
3. #141, then #142.
4. #143: re-apply its address-format nav entry to #138's new nav.
5. #144: rebase it on #143, since both add governance kinds, Cobalt kind
   validation and SDK validation. While rebasing, classify #143's
   `invalid_recipient_*` rejections in #144's fee-claim table.

(d) **After #142 deploys,** run `account-tx-index-build` once on each node
that serves `account_tx`. It backfills history.

(e) **PR #49:**
- Use a normal merge, not squash: the candidate is pinned to `16d41b5d`,
  which must stay reachable from `main`.
- Then repoint the three places that still pin the old successor:
  - `scripts/a666-build-nav-profile-rotation-ops.py`;
  - `scripts/a666-build-route-epoch-advance.py`;
  - `crates/node/tests/atomic_swap_local_six.rs`.
- The live A666 migration (G1) follows the StakeHub deprecation plan,
  phases 4–6. It needs fresh 5-of-6 checkpoint votes, reserve-owner
  signatures and issuer-signed operations from the founder's host. This
  lane will not start it until G3 is green and the G5 rehearsal passes.

## References

- [Listing package plan](https://github.com/postfiatorg/postfiatl1v2/pull/139)
  and [docs front door](https://github.com/postfiatorg/postfiatl1v2/pull/138)
- [Release process](../release-process.md)
- [Current chain state](../status/chain-state-current.md)
