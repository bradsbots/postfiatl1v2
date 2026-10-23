# Chain PR integration and developer handoff

- **Operator:** Codex (`codex`)
- **Date:** 2026-10-23 UTC
- **For:** The chain developer and release owner

## BLUF

PRs **#138–#144 and #49 are merged** into public `main` through
[#145](https://github.com/postfiatorg/postfiatl1v2/pull/145). The combined
review found and fixed interactions between recipient validation, rejected
transaction fees, memo history and reserve identity consumers. All nine final
PR checks passed. **Nothing was deployed or activated in this session.** The
next work is protocol-owner review and exact devnet archive replay of the
merged release binary, followed by the existing release process. This handoff
supersedes the merge queue and pending-CI status in the
[October 22 chain handoff](2026-10-22___nazgul__chain_p0_fixes_for_the_coinbase_review.md).

## Current state

### Source and network status

- Public `main` was verified at
  `124a187b19dc178ef92b5c3cfcfb08100eb69277`, the normal merge of #145 at
  **2026-10-22 23:59:15 UTC**.
- The tested integration head was
  `7e7169b65a70234faaac4b6ff252a6684aa81b75`. The merged tree is identical to
  that tested tree. The merge parents are the previous main
  `13c408c8c40f8e00f956b40b68770c5fa62a637b` and the tested integration head.
- All eight original PRs are marked merged. Their original heads and the
  reserve guest's pinned source remain ancestors of `main`; no squash or
  force-push was used. #139 was retargeted from the #138 branch to `main`.
- The last **documented**, rather than freshly probed, fleet observation is
  **2026-10-21 12:30:55 UTC**: six validators on release
  `store-handle-20261021`, source `86706699`, binary SHA-256
  `eea96ba6761ed223047d7781663100d34efe5641d36031bd50874bd9c8b41f36`,
  height 1137 with six-way agreement. See
  [Current State](../status/chain-state-current.md) and
  [Network Status](../status/network-status.md) for subsequent observations.
- This session performed no live fleet probe, validator restart, deployment,
  governance activation, live transaction signing or submission, A666
  migration, or website publication. The changes below are merged source;
  their deployed status was not refreshed.

### What was merged

| PR | Original reviewed head | Result in the combined source |
| --- | --- | --- |
| [#138](https://github.com/postfiatorg/postfiatl1v2/pull/138) | `25ffe212a` | Integrator documentation front door and smaller navigation. |
| [#139](https://github.com/postfiatorg/postfiatl1v2/pull/139) | `aeb7e9816` | Coinbase integration plan, comparisons and reviewer guide. |
| [#140](https://github.com/postfiatorg/postfiatl1v2/pull/140) | `e6c0f7d1c` | Documentation contradictions repaired; the production-genesis supply question remains open. |
| [#141](https://github.com/postfiatorg/postfiatl1v2/pull/141) | `285941764` | Asset-Orchard verifying-key fingerprints and their regeneration check. |
| [#142](https://github.com/postfiatorg/postfiatl1v2/pull/142) | `920f7cc47` | Memo contents in history, shielded-withdrawal account rows, and correct receipt positions for mixed transaction blocks. Index schema v2 requires backfill after deployment. |
| [#143](https://github.com/postfiatorg/postfiatl1v2/pull/143) | `593430854` | Malformed-recipient rejection and an optional mixed-case address checksum that preserves legacy addresses. Admission changes with the binary; execution enforcement has a governance activation height. |
| [#144](https://github.com/postfiatorg/postfiatl1v2/pull/144) | `92866ba34` | Fee claims for authenticated effect failures, a require-memo account flag, and `issued_payment_v2`. Execution changes have governance activation heights. |
| [#49](https://github.com/postfiatorg/postfiatl1v2/pull/49) | `d01cb1214` | NEAR receipt freshness, Aave debt completeness, duplicate committee-key rejection, duplicate manifest-entry rejection, and a reproducible successor candidate identity. Registration remains separate. |

The integration merged those heads in the order shown. The original #49 work
already contained regenerated manifests and two identical guest builds from
the previous lane. This session preserved that provenance and corrected its
consumers; it did not register the candidate on-chain.

### Integration repairs beyond the individual PRs

1. **Recipient checks and fee claims now compose.** `IssuedPaymentV2` initially
   fell through the recipient validator's wildcard after combining #143 and
   #144. It now receives the same validation. Transfer/payment execution
   wrappers, escrow/NFT handling, governance kinds and live/archive replay
   paths were reconciled so recipient rejection and fee claiming both apply
   at their independently governed heights. Start with
   [recipient validation][recipient], [execution entrypoints][entrypoints]
   and [node execution actions][actions].
2. **Issued-payment memos reach exchange clients.** The shared history helper
   returns memo contents, hashes, counts and byte totals for native and
   issued payments. Rust SDK response validation and Python archive fallback
   accept those issued-payment memo rows. See [history construction][history],
   [SDK validation][sdk] and [Python client][python-client].
3. **Regressions cover the combined behavior.**
   `recipient_failures_claim_fees_with_both_gates_and_replay_identically`
   covers all three recipient rejection classes, fee burning, sequence
   advancement, no amount transfer and identical replay results.
   `issued_payment_v2_uses_recipient_validation_and_exposes_memos` covers the
   new transaction variant. Both are in the [node tests][node-tests]. The
   [Rust SDK tests][sdk-tests] and [Python history tests][python-tests] cover
   signed memo contents and deposit-tag decoding. Existing exchange-history
   fixtures were changed to canonical recipients so they remain valid under
   the stricter admission rules.
4. **Reserve consumers use the reproduced candidate.** The profile-rotation
   builder, route-epoch builder and six-node atomic-swap test were repointed,
   along with their fixtures. The deployed legacy identity and the earlier
   successor's historical qualification evidence remain separate.
5. **Documentation describes the integrated result.** Navigation and README
   conflicts were resolved, strict-build source links and a stale address
   anchor were fixed, and RPC docs now explain issued-payment memo contents
   and fee-charging `tec_*` rows. The Coinbase plan, comparisons and reviewer
   guide distinguish included source from the October 21 deployed baseline.
   The locked research specification was not rescored.

The additional commits are
[`1ebc0faf8`](https://github.com/postfiatorg/postfiatl1v2/commit/1ebc0faf8a7ff9d46688251a291e15ee5ad33ef4)
(integration fixes),
[`fa3d9b9b4`](https://github.com/postfiatorg/postfiatl1v2/commit/fa3d9b9b49086184eca01388c59f0922a9cc7e94)
(reserve fixtures and RPC documentation), and
[`7e7169b65`](https://github.com/postfiatorg/postfiatl1v2/commit/7e7169b65a70234faaac4b6ff252a6684aa81b75)
(source status in the listing package). Some wrapper reconciliation is in the
normal merge commits preceding them.

A suspected governance replay-order problem was investigated: archive replay
reconstructs governance sequentially before executing subsequent blocks. No
bug was demonstrated there, so no speculative change was made. Tests also
cover inactive rules and legacy account serialization: zero account flags
remain omitted from legacy bytes and state commitments.

### Reserve candidate provenance

The [candidate identity][candidate] remains `candidate_not_registered`. Its
source is `16d41b5ddd9a3a19921c8304dd1e658ba1f0a721`; its ELF SHA-256 is
`b64b7666eabf1b251029877a842b5722f041f6a296a1156c715548a05d28dcd5`.
The identity file contains the verifying key, profile ID, policy hashes and
reproduction commands. Preserve this source commit in Git history: the build
uses `git archive` at that exact revision.

The final proof CI rebuilt and checked the immutable legacy guest, the older
public successor with its historical qualification data, and the new
freshness/debt candidate. Do not overwrite `program-identity.json`,
`a666-successor-program-identity.json` or `elf/` with the candidate build.

### Validation and review limits

All **nine final PR checks** passed on `7e7169b65`, verified at
**2026-10-22 23:58:38 UTC**:

| Evidence | Passing checks |
| --- | --- |
| [Rust CI](https://github.com/postfiatorg/postfiatl1v2/actions/runs/39864672912) | `check` and full `test` (1h 34m 14s). |
| [Product security CI](https://github.com/postfiatorg/postfiatl1v2/actions/runs/39864672901) | `public-tree-hygiene`, `rust-supply-chain`, `python-sdk`, `wallet-and-proxy`, `evm-contracts`, `open-reserve-proof-kit` (46m 45s). |
| [Docs CI](https://github.com/postfiatorg/postfiatl1v2/actions/runs/39864672913) | Strict documentation build. |

The release-only `official-mainnet-fork` job was **skipped**, as designed for
this PR; it is still required on the exact release revision before tagging.
These links describe the final combined PR run, not a claim about later push
runs. Earlier combined runs exposed a stale docs anchor and old reserve test
pins; both were fixed before the passing run above.

Local validation also passed: locked workspace/all-target check; 733 core Rust
tests; 76 focused node/RPC tests; 986 Python tests with 3 skipped and 412
passing subtests; 22 reserve-builder tests using temporary fixture keys;
JavaScript address tests; workspace Clippy with warnings denied; strict docs,
link and handoff-index checks; and 12 publication/hygiene checks. Those counts
describe separate local runs and are not additive to the full CI suite.

This was agent source review plus automated validation. It is not an external
cryptographic audit or two independent human approvals. At handoff time #145
has no formal approving reviews, and GitHub reports `main` unprotected with
no applicable branch rules. The user authorized the merges, but that does not
establish the reviewer and protection requirements documented in the
[release process](../release-process.md). Protocol-owner/security review and
repository-admin reconciliation of that policy gap remain outstanding.

## Next decision or action

1. **Review the integrated source.** Use #145 and the regressions above,
   especially the #143/#144 interaction and reserve identity consumers.
   Review the final merged revision rather than treating the original PR
   branches as the release candidate.
2. **Qualify the release before deployment.** Build from the merged release
   revision and run the exact height-924 and current-head devnet archive
   replays. Compare state roots, receipts, fees and sequences; stop on any
   mismatch. Those archives were unavailable in this review worktree, and
   synthetic tests do not replace this gate. Follow the
   [release process](../release-process.md) for second-builder reproduction,
   signed artifacts, rollback and canary qualification, and release checks.
3. **Roll out before governance activation.** Use the existing
   `scripts/postfiat-safe-rollout` process after release approval. All six
   validators must run the new binary before activating
   `recipient_format_activation_height`, `rejected_tx_fee_activation_height`
   or `require_memo_activation_height`. Malformed-recipient admission becomes
   stricter as soon as the binary is deployed; that part does not wait for
   execution activation.
4. **Backfill account history after installing the binary.** On every node
   serving `account_tx`, follow the [index runbook](../runbooks/account-tx-index.md):

   ```bash
   postfiat-node account-tx-index-build --data-dir <validator-data>
   postfiat-node account-tx-index-status --data-dir <validator-data>
   ```

   Confirm usable v2 indexes and the expected retained-history range. The
   rebuild cannot recover blocks or history already pruned.
5. **Keep A666 migration as its own operation.** G1 remains open for the live
   legacy verifier. The
   [StakeHub deprecation gates](../plans/STAKEHUB-DECOUPLING-AND-OPEN-RESERVE-PROOF-INFRASTRUCTURE-PLAN-20260801.md)
   require G3 public-adapter qualification and G5 controlled migration
   rehearsal. Use fresh qualification/proofs, issuer and reserve-owner
   signatures, and fresh 5-of-6 checkpoint votes. These are the StakeHub
   gates, not the similarly numbered storage milestones. Source merge and
   candidate reproduction do not register a profile or authorize migration.
6. **Resolve the remaining product decisions separately.** Production genesis
   must settle the 100 billion target versus the devnet's 1,000 PFT supply.
   Website go-live still needs its publication decision. Neither was completed
   by this integration.

## References

- [Integration PR and discussion](https://github.com/postfiatorg/postfiatl1v2/pull/145)
- [Merged source](https://github.com/postfiatorg/postfiatl1v2/tree/124a187b19dc178ef92b5c3cfcfb08100eb69277)
- [Previous chain handoff](2026-10-22___nazgul__chain_p0_fixes_for_the_coinbase_review.md)
  and [developer lane handoff](2026-10-22___dravlic__reserve_proof_conditions_done_and_both_replays_in.md)
- [Coinbase integration plan](../listings/coinbase/integration-plan.md),
  [comparisons](../listings/coinbase/comparisons.md) and
  [reviewer guide](../listings/coinbase/reviewer-agent-guide.md)
- [Reserve successor proposal](../review/nav-reserve-proof-successor-proposal-20260924.md)
  and [candidate identity][candidate]
- [Current chain state](../status/chain-state-current.md),
  [release process](../release-process.md) and
  [account history index runbook](../runbooks/account-tx-index.md)

[recipient]: https://github.com/postfiatorg/postfiatl1v2/blob/124a187b19dc178ef92b5c3cfcfb08100eb69277/crates/execution/src/recipient_format.rs
[entrypoints]: https://github.com/postfiatorg/postfiatl1v2/blob/124a187b19dc178ef92b5c3cfcfb08100eb69277/crates/execution/src/entrypoints.rs
[actions]: https://github.com/postfiatorg/postfiatl1v2/blob/124a187b19dc178ef92b5c3cfcfb08100eb69277/crates/node/src/execution_actions.rs
[history]: https://github.com/postfiatorg/postfiatl1v2/blob/124a187b19dc178ef92b5c3cfcfb08100eb69277/crates/node/src/block_finality.rs
[sdk]: https://github.com/postfiatorg/postfiatl1v2/blob/124a187b19dc178ef92b5c3cfcfb08100eb69277/crates/rpc_sdk/src/response_validation.rs
[python-client]: https://github.com/postfiatorg/postfiatl1v2/blob/124a187b19dc178ef92b5c3cfcfb08100eb69277/python/postfiat_rpc/client.py
[node-tests]: https://github.com/postfiatorg/postfiatl1v2/blob/124a187b19dc178ef92b5c3cfcfb08100eb69277/crates/node/src/tests/rejected_fee_require_memo.rs
[sdk-tests]: https://github.com/postfiatorg/postfiatl1v2/blob/124a187b19dc178ef92b5c3cfcfb08100eb69277/crates/rpc_sdk/src/response_validation_tests.rs
[python-tests]: https://github.com/postfiatorg/postfiatl1v2/blob/124a187b19dc178ef92b5c3cfcfb08100eb69277/python/tests/test_account_tx_exchange_rows.py
[candidate]: https://github.com/postfiatorg/postfiatl1v2/blob/124a187b19dc178ef92b5c3cfcfb08100eb69277/tools/nav-reserve-proof/qualifications/freshness-and-debt-20260924/candidate-identity.json
