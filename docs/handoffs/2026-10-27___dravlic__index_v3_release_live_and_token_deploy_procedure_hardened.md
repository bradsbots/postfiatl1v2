# Index v3 release live and token deploy procedure hardened

- **Operator:** Domagoj Ravlić (`dravlic`)
- **Date:** 2026-10-27 UTC

## BLUF

The `index-v3-20261027` release runs on all six validators, applied one at a time at 1154–1159 (11:05–11:35Z). The after checks were clean, and the account history index was rebuilt to schema v3 on every host and has followed the chain since 1160 ([Current State][state], [release README][relreadme], [deploy sheet][sheet]). The first live reading of the vote records found defect VR-01 ([review][vr01]). Its fix is on main as a next-release candidate (`5fc43961`). Three rounds of correctness review hardened the token's deploy procedure and tests without changing the contract. The Coinbase texts now say only what the code and the plan support, and the [one-pager][onepager] is the version to use. The first counted weekly scorer round could not run yet, because round 29 was not published (`877c614e`).

## Current state

The release was cut at `b950ed82` on `release/index-v3-20261027`. The release branch also carries the before state (`03ce4dbc`), the signed canary backup with its exact replay (`6101c9fe`), the rollout (`cbbd5131`) and the index rebuild with the vote-record check and the after state (`c2f80cb9`). Main records the cut (`77725bef`) and the deployment (`4fc0a521`).

The applies ran in the order validator-1, 0, 2, 3, 4, 5, with one 1-PFT faucet grant after each at 1154–1159. Every grant was certified at view 0 and applied identically on all six. The after checks at 1159 / `ae91ad6d…` / `60ddbee3…` passed. The v3 index was then built on each host with only that host's RPC unit stopped, in 7.1–9.8 s per host, with lag 0, and the grant at 1160 extended it on all six. The release carries the round command fix, the per-height vote records, index schema v3, the verify_bridge read fix and the merged bot fixes. It has no governance step.

The last observed fleet state is the after state of 2026-10-27 12:14Z ([after state][after]). All six validators run `index-v3-20261027` (executable `b5cf3ce4…`, signed manifest `a61e290a…`, source `d728f895`) at 1160 / `f65e6fac…` / `f06608d4…` with empty mempools. The three activation heights stay at 1153, both routes are at authority epoch 1, the swap service is at epoch 2, and StakeHub's config points at the release. No live read was made after 12:14Z. The rollback target is `exchange-readiness-20261023` (`4085ac70…`). After a rollback on a host that has a v3 index, run the old binary's `account-tx-index-build` on that host, as the sheet's [Rollback section][rollback] says.

The vote records showed VR-01. validator-2's record for 1160 lists validator-0 as `no_answer`, although validator-0 accepted both vote requests, its first answer arriving 2.3 s after the proposal, just after the quorum. The cause is the late-vote writer: past the deadline it stopped before draining the answers already received (`crates/node/src/transport_runtime.rs:2933` at `d728f895`). The missing records at 1158 and 1159 have a different cause. The grant rounds through 1159 ran the previous executable, because StakeHub's `runtime_binary` stays on the previous release until the last apply. The fix (`5fc43961`) drains every received answer before classifying. It records an answer after the quorum as accepted, and an answer still seen after the deadline as `late_after_deadline`. Two fail-first tests in `transport_batch_payload_tests.rs` cover it. The 40-second wait before the record is the deadline wait by design. validator-2's absence from the 1155–1159 certificates is the reliability signal the records exist to capture.

Main through `877c614e` carries work past the deployed `d728f895` that is not deployed. The next-release candidates are the VR-01 fix (`5fc43961`), the k256 0.14 family upgrade for RUSTSEC-2026-0387, and the vote-record export to the signed snapshot, which needs a new snapshot version ([next release plan][next]).

The token contract is unchanged. A correctness review in three rounds led to `5d6e6709`, `cd33f6ca`, `0f4fec6e`, `27e8d0f7` and `07cb2586`. The deploy script now asserts the chain id. It authenticates the treasury as a real Safe: the proxy and singleton code hashes, `masterCopy`, a threshold of at least 2, and at least as many distinct owners. It also cross-checks the supply in whole PFT and in base units, and it refuses a used deployer key. It writes a deployment record with build provenance only for a real run. The suite adds boundary, fuzz and invariant tests, an exact 13-function ABI check, and script tests for every refusal and the accepted path. The procedure, with its pre- and post-deployment checklists, is in the [token README][tokenreadme]. In the [milestone][milestone], P1.1 and P1.2 are done. P1.3, the Base Sepolia test deployment, waits for a deployer key funded with Base Sepolia test ETH and for the token document figures. The anvil run is in the [dry-run record][dryrun].

The Coinbase texts were tightened in `1fe5f9cd`, `7a6d789f` and `1b3f0742`: the [one-pager][onepager] and the [options paper][paper]'s paste text.

The weekly scorer round is a shadow evaluation and publishes nothing. At 12:57Z the public testnet scoring service had round 28 (completed 2026-10-20) as its newest round. Round 29 was not found, so nothing was evaluated. The [Z2 plan][z2] records the check and the next ones: after 19:30Z today, then 2026-11-03, 11-10 and 11-17.

Task Node tasks rewarded today, 18.4 PFT in total:

| Task | Work | PFT |
|---|---|---|
| `task_fe9d8cf2…` | release cut and local qualification | 3 of 3.5 |
| `task_bf479e03…` | rollout to six validators | 4 of 5 |
| `task_1b590887…` | VR-01 fix | 2.8 of 3.5 |
| `task_1ca152f2…` | token, first review findings | 1.8 of 3 |
| `task_74d39999…` | token, second review findings | 1.8 of 2 |
| `task_273b9c95…` | token, third review findings | 2 |
| `task_0f16ddb1…` | first counted weekly scorer round | 3 |

## Next decision or action

My next steps, in order:

1. the next release candidates (the VR-01 fix, the k256 0.14 upgrade, the snapshot export), cut when CI is green;
2. the Base Sepolia test deployment of the token, once a deployer key holds test ETH and the token document figures exist;
3. the second counted weekly scorer round next week;
4. the lock of the [Phase 2 design note][phase2].

Only your lane can provide these. Each shows the date it was first asked:

- the token document with the total supply, the split at launch, the treatment of PFT already paid on the PFT Ledger, and the treasury Safe's signers and threshold; the audit budget and vendor; then the Base mainnet deployment with your keys (2026-10-26; all on the [decision sheet][decisions]);
- the two issuer signatures per the [issuer signing sheet][issuer], A666 first, then BMNRC (2026-09-25 and 2026-10-01); they block the validator-5 checkpoint;
- the on-chain registration of the reserve-proof successor after the StakeHub gates (2026-09-24);
- the `ETHEREUM_MAINNET_RPC_URL` secret (2026-09-28);
- the StakeHub acceptance file and the installed binaries (2026-10-21);
- SCT-08 items 1–3 ([campaign][sct08], 2026-10-23);
- the genesis supply and the website go-live (2026-10-23).

## References

- [Release README][relreadme], [deploy sheet][sheet], [after state][after], [Current State][state], [next release plan][next], [VR-01 review][vr01]
- [Token README][tokenreadme], [milestone][milestone], [dry-run record][dryrun], [one-pager][onepager], [options paper][paper], [Phase 2 design note][phase2]
- [Z2 plan][z2], [decision sheet][decisions], [issuer signing sheet][issuer], [SCT-08 campaign][sct08]
- The other lane's [2026-10-23 handoff][lane1023], my [previous handoff][previous]
- Release branch `b950ed82`, `03ce4dbc`, `6101c9fe`, `cbbd5131`, `c2f80cb9`; main `77725bef`, `4fc0a521`, `01f09c52`, `5fc43961`, `5d6e6709`, `cd33f6ca`, `0f4fec6e`, `27e8d0f7`, `07cb2586`, `1fe5f9cd`, `7a6d789f`, `1b3f0742`, `877c614e`

[lane1023]: 2026-10-23___codex__chain_pr_merge_handoff.md
[previous]: 2026-10-26___dravlic__pft_erc20_on_base_path_set_and_next_release_candidates_landed.md
[state]: ../status/chain-state-current.md
[next]: ../plans/active/next-validator-release-plan-20261108.md
[vr01]: ../review/vote-records-vr01-20261027.md
[milestone]: ../plans/active/pft-erc20-base-listing-milestone.md
[dryrun]: ../listings/coinbase/pft-token-dry-run-20261026.md
[onepager]: ../listings/coinbase/pft-erc20-one-pager.md
[paper]: ../listings/coinbase/pft-erc20-representation-options-20261026.md
[phase2]: ../specs/pft-erc20-base-bridge-phase2-design-20261026.md
[z2]: ../plans/active/z2-advisory-flag-execution-plan-20261022.md
[decisions]: ../governance/pending-operator-decisions.md
[sct08]: ../review/sct08-evidence-campaign-20261023.md
[relreadme]: https://github.com/postfiatorg/postfiatl1v2/blob/c2f80cb9630c7d34449410eaddee13a93ed10865/deployments/index-v3-20261027/README.md
[sheet]: https://github.com/postfiatorg/postfiatl1v2/blob/c2f80cb9630c7d34449410eaddee13a93ed10865/deployments/index-v3-20261027/DEPLOY-SHEET.md
[rollback]: https://github.com/postfiatorg/postfiatl1v2/blob/c2f80cb9630c7d34449410eaddee13a93ed10865/deployments/index-v3-20261027/DEPLOY-SHEET.md#rollback-one-validator-emergency-only
[after]: https://github.com/postfiatorg/postfiatl1v2/blob/c2f80cb9630c7d34449410eaddee13a93ed10865/deployments/index-v3-20261027/observed/after.json
[tokenreadme]: https://github.com/postfiatorg/postfiatl1v2/blob/07cb25863bae67aedc8fbfe9274dfd53174a3ac1/crates/pft-token-contracts/README.md
[issuer]: https://github.com/postfiatorg/postfiatl1v2/blob/61e9b00c8399907f45dff2be1ee44b8f1da431af/deployments/fastlane-cap-20261014/ISSUER-SIGNING-SHEET-20261020.md
