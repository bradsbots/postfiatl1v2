# PFT ERC-20 on Base path set and next release candidates landed

- **Operator:** Domagoj Ravlić (`dravlic`)
- **Date:** 2026-10-26 UTC

## BLUF

The Coinbase listing path is decided and built as far as our side can take it today. PFT gets a plain fixed-supply ERC-20 on Base now and a one-for-one bridge into native PFT at mainnet genesis that never closes. The [options paper][paper] settles it (`c85ed0e0` through `aeaa12f6`, harness 85.67), and the [milestone][milestone] is the first active plan (`6fc56c17`, `a10aefcc`, `95e630d4`). The token contract with 8 tests and a Base deploy script is on main (`ad5ba32f`) and now lives in its own Foundry project, `crates/pft-token-contracts`, with the OpenZeppelin submodule at the same pin, so that the A666 reader build stays reproducible (`62db8c0e`): [`src/PFTToken.sol`][token], [`test/PFTToken.t.sol`][tokentest] and [`script/DeployPFTToken.s.sol`][tokendeploy]. `crates/ethereum-contracts` compiles as before `ad5ba32f`. The [one-page note][onepager] for the Coinbase document and the [dry-run record][dryrun] are in `docs/listings/coinbase/` (`66326c6d`). The [Phase 2 design note][phase2] (`e48c99f4`, `13240104`, `d968472e`) records the proof style, the dormant release path, the release cap and the committee lifecycle; it scored 84.73 and is not locked. The [next release][next] gained three candidates:

1. the round command no longer sends the certified block to its own validator while holding the store lease (`d9463929`);
2. per-height vote outcome records for the SCT-08 reliability input (`1432b8e0`), with the window command that derives the fact (`a711925c`); their export to the signed snapshot is open, because it needs a new snapshot version;
3. account history index schema v3, which writes only the commit's rows (`8f2217d7`); the rollout must run `account-tx-index-build` on every validator.

## Current state

The nine bot pull requests of the weekend, #149, #151, #153, #155, #158, #159, #161, #163 and #165, are reviewed in full and merged, as is #147 (`12df2b21`, then `3e26f4fe`). Both smoke checks and the full node suite pass.

In `product-security-ci`, the reworded provider-name comment (`1b5daa6e`) made wallet-and-proxy green. RUSTSEC-2026-0387 (crypto-bigint 0.5.5, with no fixed 0.5 release, held by k256 0.13 under the pinned Alloy 1.5.7) is accepted with a dated `deny.toml` entry, and the upgrade is a next-release candidate (`202e5605`). The open-reserve-proof-kit job has been red since `ad5ba32f`: the OpenZeppelin library changed the A666 reader's compiler input hash from `c252f32a…` to `3ad5112a…`. `3f355e58` made the error visible. The fix is the token move (`62db8c0e`); its CI result was still pending at the time of writing.

For Z2, the flag variant of the host runner has offline tests (`495d4a71`), and the run files now get owner, host and same-host checks (`6050215a`, `b08da983`). The first counted weekly round is on 2026-10-27 ([plan][z2]).

The devnet was not touched today: no host contact, no RPC calls and no live change. The last observed fleet state is the one in [Current State][state], captured 2026-10-23 10:40Z: all six validators on `exchange-readiness-20261023` (source `6b1a0585`), at height 1153. Main through `62db8c0e` carries everything listed above; none of it is deployed.

Task Node tasks rewarded today, 24.7 PFT in total:

| Task | Work | PFT |
|---|---|---|
| `task_47c67dbc…` | host runner flag variant | 2 |
| `task_b9c8fede…` | red CI check, #147, five bot PRs | 3.2 of 4 |
| `task_42e61a72…` | run-file checks, second bot PR batch | 2.45 of 3.5 |
| `task_2d1ec27c…` | options paper | 1.6 of 2 |
| `task_5111d278…` | crypto-bigint advisory | 1 of 1.75 |
| `task_f9cd04fb…` | certified-round self-delivery fix | 2 of 2.5 |
| `task_7017067d…` | per-height vote records | 3.2 |
| `task_9cb9117a…` | token contract | 2.5 |
| `task_77c5dfec…` | Phase 2 design note | 2.25 of 3 |
| `task_eb84cfbc…` | account history index v3 | 3 of 3.5 |
| `task_f1528ebc…` | Phase 2 note decisions | 1.5 of 2 |

`task_12d7bf61…` (vote reliability window command) and `task_47bbfbbc…` (release cap and committee lifecycle) are awaiting review.

## Next decision or action

My next steps, in order:

1. the token project move (`62db8c0e`), green in CI;
2. the first counted weekly scorer round (Z2 step 6, from 2026-10-27);
3. the release cut from main once CI is green at the cut, with the candidates above, then the rollout with `account-tx-index-build` on every validator;
4. one more pass on the Phase 2 note for the lock;
5. the Base Sepolia test deployment once a deployer key holds Base Sepolia ETH; the server's test wallet `0xC75Bf05Ce82d6f4b6139dd9446D6De5F5994a4CB` can serve.

Only your lane can provide these; each shows the date it was first asked:

- the token document with the total supply, the split at launch, the treatment of PFT already paid on the PFT Ledger, and the treasury Safe's signers and threshold; the audit budget and vendor; then the Base mainnet deployment with your keys (2026-10-26; all listed on the [decision sheet][decisions]);
- the two issuer signatures per the [issuer signing sheet][issuer], A666 first, then BMNRC (2026-09-25 and 2026-10-01); they block the validator-5 checkpoint;
- the on-chain registration of the reserve-proof successor after the StakeHub gates (2026-09-24);
- the `ETHEREUM_MAINNET_RPC_URL` secret (2026-09-28);
- the StakeHub acceptance file and the installed binaries for the first rehearsal (2026-10-21);
- SCT-08 items 1–3 ([campaign][sct08], 2026-10-23);
- the genesis supply and the website go-live, your own items (2026-10-23).

## References

- [Options paper][paper], [milestone][milestone], [Phase 2 design note][phase2], [one-page note][onepager], [dry-run record][dryrun]
- [Decision sheet][decisions], [next release plan][next], [SCT-08 campaign][sct08], [Z2 plan][z2]
- [Current State][state], [issuer signing sheet][issuer], the other lane's [2026-10-23 handoff][lane1023], my [previous handoff][previous]
- Commits `c85ed0e0`, `aeaa12f6`, `6fc56c17`, `a10aefcc`, `95e630d4`, `ad5ba32f`, `66326c6d`, `e48c99f4`, `13240104`, `d968472e`, `d9463929`, `1432b8e0`, `a711925c`, `8f2217d7`, `12df2b21`, `3e26f4fe`, `1b5daa6e`, `202e5605`, `3f355e58`, `62db8c0e`, `495d4a71`, `6050215a`, `b08da983`

[lane1023]: 2026-10-23___codex__chain_pr_merge_handoff.md
[previous]: 2026-10-23___dravlic__exchange_readiness_release_live_and_storage_offline_qualified.md
[paper]: ../listings/coinbase/pft-erc20-representation-options-20261026.md
[milestone]: ../plans/active/pft-erc20-base-listing-milestone.md
[onepager]: ../listings/coinbase/pft-erc20-one-pager.md
[dryrun]: ../listings/coinbase/pft-token-dry-run-20261026.md
[phase2]: ../specs/pft-erc20-base-bridge-phase2-design-20261026.md
[token]: https://github.com/postfiatorg/postfiatl1v2/blob/62db8c0e41dc4beecf979c3e5f29265b1bd8d22c/crates/pft-token-contracts/src/PFTToken.sol
[tokentest]: https://github.com/postfiatorg/postfiatl1v2/blob/62db8c0e41dc4beecf979c3e5f29265b1bd8d22c/crates/pft-token-contracts/test/PFTToken.t.sol
[tokendeploy]: https://github.com/postfiatorg/postfiatl1v2/blob/62db8c0e41dc4beecf979c3e5f29265b1bd8d22c/crates/pft-token-contracts/script/DeployPFTToken.s.sol
[next]: ../plans/active/next-validator-release-plan-20261108.md
[decisions]: ../governance/pending-operator-decisions.md
[sct08]: ../review/sct08-evidence-campaign-20261023.md
[z2]: ../plans/active/z2-advisory-flag-execution-plan-20261022.md
[state]: ../status/chain-state-current.md
[issuer]: https://github.com/postfiatorg/postfiatl1v2/blob/61e9b00c8399907f45dff2be1ee44b8f1da431af/deployments/fastlane-cap-20261014/ISSUER-SIGNING-SHEET-20261020.md
