# Signer rotation release deployed

- **Operator:** Domagoj Ravlić (`dravlic`)
- **Date:** 2026-10-09 UTC
- **Responding to:** no handoff from the other lane since
  [its 2026-10-01 handoff][nazgul]. The conference is over. The objection
  window on the [validator-5 reinstatement][v5] closed on 2026-10-08 evening
  UTC without an objection. My previous handoff: [2026-10-08][previous].

## BLUF

Release `signer-rotation-20261007` (executable `decaa411…`, manifest
`fa4649aa…`, source `0fa55d0b`) runs on all six validators since 12:28Z. I
rolled it out one validator at a time (validator-1, 0, 2, 3, 4, 5) with one
devnet grant after each: heights 1116–1121, all at view 0, identical blocks on
all six, certified 5 of 6. No divergence and no rollback (release branch
`a4fb8bca`, `main` `63c2e696`). Before it, I recorded the before state
(`1e710d74`) and a fresh signed canary backup of validator-1 (manifest
`49b2b6cd…`, re-imported and fully replayed at height 1115, `d94e9837`). After
state at 12:32Z: all twelve validator and RPC processes on `decaa411…`,
`deployment_manifest_verified` true on all six, the RPC units on
`--max-requests 100000` with a one-second restart delay. The release's
preflight at 12:43Z: READY WITH ATTENTION (the five hand-started relays), six
at height 1121, tip `329bc2f1…`, root `aa462feb…`. Not done today, planned for
2026-10-12: the FastSwap store conversion per host, the signer-group
activation (both halves), the relay units, and the review of the twelve pull
requests #56–#67 that the bradsbots account opened overnight. StakeHub
[PR #21][sh21] (the read-only live-mode route check and the refreshed
readiness table) is merged into `master` (merge commit `73f9107a`; `master`
head `48e5565` records the 84 environment-bound test files).

## Current state

- **Go/no-go reads, 10:51–10:53Z** ([before.json][before], [sheet §0–§3][sheet0]).
  No objection anywhere: `origin/main`, handoffs, PR comments; the operator
  confirmed that no Telegram message arrived. No other session or rollout was
  active on the fleet. The other lane's `navcoin-proof-watchdog@` user units
  are unchanged since 2026-09-30/10-01 (3 on validator-0, 14 on validator-3).
  Before state (10:51:42Z): six on `combined-fastpay-20260928` (`1f8b332d…`,
  `c93b2137`, manifest `d2fdb687…`) at height 1115, tip `28e1175b63a9…`, root
  `a5287eaff909…`, mempools empty. Stage recheck: `decaa411…` / `fa4649aa…`,
  publisher `pfc531e0…`, validity window 2026-10-06 to 2027-10-06
  ([RELEASE-ID.txt][rid]). Local preflight `PASS_SIGNED_LOCAL_INPUTS_ONLY`
  (33 files, 4 artifacts, signed gate 6/6). Fleet preflight: six-way
  agreement, six rosters valid (root `08a451e0…`), 11 files per host,
  0 deletions, order validator-1, 0, 2, 3, 4, 5.
- **Canary backup** (`d94e9837`, 11:52Z, [sheet §4][sheet4]). Manifest
  `49b2b6cdcce9277a811b079bdf9a95d2c740c48f22c06130a80989ff8d61304b`. After
  re-import, `verify-finalized-checkpoint` verified true (quorum 5 of 6) and
  `verify-state` verified true at 1115 / `28e1175b63a9…` / `a5287eaff909…`.
  Validator-1 had 18.71 GB free after the export. As with every previous
  release, the backup command also leaves a copy of the new executable next to
  the export on validator-1.
- **Rollout** (`a4fb8bca`: apply, grant and observed files in
  [observed/][observed], [rollout-record.json][record], [RELEASE-ID.txt][rid]
  `status=DEPLOYED` at height 1121).
  - Applies 12:06:38–12:28:03Z with `scripts/postfiat-safe-rollout
    apply-next`, each exiting 0 with nothing on stderr.
  - Grants (applied validator → height, proposer, block / root):
    validator-1 → 1116, validator-0, `83b7f91f…` / `321f07c6…`;
    validator-0 → 1117, validator-1, `e4e0d71e…` / `a48c585b…`;
    validator-2 → 1118, validator-2, `61307ba4…` / `c6319f18…`;
    validator-3 → 1119, validator-3, `37e3b118…` / `fb08eafb…`;
    validator-4 → 1120, validator-4, `d164872d…` / `4bbfc090…`;
    validator-5 → 1121, validator-5, `329bc2f1…` / `aa462feb…`.
    For every grant, the `blocks` RPC on all six returned the identical block
    certified 5 of 6, the tip on all six, mempools 0, and the receipt verified
    on all six.
  - After each apply, `observe-fleet.py` passed: the applied validator and its
    RPC on `decaa411…`, the manifest check passed on every host, and
    `deployment_manifest_verified` true on the applied hosts.
  - The faucet moved 6 PFT plus 192 atoms of fees (68.99 PFT left).
  - One deviation, recorded in [sheet §5][sheet5]: StakeHub's `runtime_binary`
    and `topology_file` were pointed at the new release only after
    validator-5, because the faucet runs `runtime_binary status` on all six
    hosts, so the new path had to exist everywhere first. `local_node_binary`
    was pointed at it before the first grant. The old config is kept as
    `~/.pft/config.toml.bak-20261009`.
  - Left on hosts: the backup's copy of the new executable on validator-1 and
    each grant's small working directory on its proposer host (normal).
  - The rollback path was not needed: [rollback-one.sh][rollback] to
    `combined-fastpay-20260928` with the data in place, and the signed
    validator-1 backup `49b2b6cd…` as the fallback.
- **After state** ([after.json][after], 12:32:09Z; [Current State][state]).
  All twelve processes on `decaa411…` with manifest `fa4649aa…`;
  `deployment_manifest_verified` true on all six; RPC units with
  `--max-requests 100000` and `RestartSec=1`; height 1121, tip
  `329bc2f1f31c…`, root `aa462feb712d…` (before: 1115, `28e1175b…`,
  `a5287eaf…`). The other lane's watchdog user units are unchanged (3 on
  validator-0, 14 on validator-3). The release's `demo-preflight.py` at
  12:43:09Z: READY WITH ATTENTION, 55 PASS, 5 ATTENTION (the hand-started
  relays on validators 0 and 2–5), 0 FAIL. Validator-0 reports release
  `signer-rotation-20261007`, `0fa55d0b`, `decaa411` with the manifest
  verified. [Current State][state] (`63c2e696`) records the deployment and
  now says all six report `deployment_manifest_verified` true.
  - Deployment boundary: deployed source `0fa55d0b`; `main` at `63c2e696`
    before this handoff; release branch at `a4fb8bca`. Merged but undeployed:
    `9d837bef` (PR #54, a dead node wrapper removed) and `51144786` (the
    Python `account_tx` fallback window), plus documentation. No live probe
    while writing this handoff.
  - Not updated yet: the sheet's status line still lists `demo-preflight.py`
    as not run, and the [plan's][plan] Rollout checkboxes are unticked.
- **StakeHub [PR #21][sh21] merged** (merge commit `73f9107a`, 2026-10-09
  12:50Z, parents `52eb686` and `9abec352`): `pft bridge route-check
  [--json]`, the readiness table rows (PT-04–08 and WB-11 repaired), and the
  runbook's live-mode sentence.
  - Basis: the branch's full suite (2026-10-08, 57:36) ended with 84 failed,
    5,348 passed, 89 skipped. The 84 are the environment-bound set: 38
    browser, 26 residual-surface, 6 demo-verify, 4 local-EVM failures, and ten
    more (missing `monero` module, `fcntl` `F_ADD_SEALS` and the
    `/usr/bin/true` symlink loop, `orc_directives` paths, the live A666
    signer config, the real wallet manifest root, the W6 checklist). All ten
    reproduced on unchanged `master` `52eb686` in the same environment. The
    PR touches none of those files.
  - `master` head `48e5565` ("Record the environment-bound test files of the
    full-suite baseline") adds the 30 failing files with counts to
    [live-funds-readiness-20260929.md][sh-readiness], so the next comparison
    has them.
  - The live StakeHub checkout stays on the PR branch with its foreign
    uncommitted `AGENTS.md` edit.
- **Pull requests [#56–#67][bradsbots]** (bradsbots, 2026-10-08 14:44Z to
  2026-10-09 02:00Z, all against `main`, none a draft). Repairs of inventory
  P3 findings (CHO-05, CHO-06, SWP-04, SWP-05, SMG-05, SMG-06, MPL-02,
  UNL-04); the relative `--data-dir` child dispatch (#56, issue #27); the
  `account_tx` fallback atomic-swap rows (#57); the RPC accept-budget
  defaults (#58); the resolved-address RPC probe (#59); finality submit id
  correlation (#64); Python client wrappers (#66, #67). Unreviewed and
  unmerged, so the running validators are unaffected; they belong to the
  release after this one ([plan][next]). Review on 2026-10-12.
- **Task Node.** `task_b9827ea96695cfea9fa8c3ad56477e89` ("Roll Out
  signer-rotation-20261007 to Six Validators", 5 PFT): Rewarded 5 PFT. The
  backup, the after checks and the StakeHub merge had no separate task. This
  handoff has no Task Node action.
- **CI on `main`** (`gh run list`, read once at 13:01Z). `63c2e696`:
  `docs-build` passed; `product-security-ci` and `rust-ci` in progress.
  `2dfc7e5e` (last commit of 2026-10-08): all three passed.
- **Work server.** 72 GB free (13:01Z). Of the PR #21 suite copy, only its
  0.5 MB test log remains.
- **StakeHub `master`.** `48e5565` (13:01Z).

## Next decision or action

### My next steps, in order

On 2026-10-12. Each live step needs its own go on the day
([deploy sheet][sheet]).

1. Health check: confirm the fleet stayed on `signer-rotation-20261007` over
   the weekend (heights, agreement, RPC restart counts).
2. [Sheet §7][sheet7]: the FastSwap store conversion per host (validator-5, 0,
   1, 2, 3, 4), after a dry run on a copy of validator-1's store; then
   `fastswap_checkpoint_status` on validators 0–4.
3. [Sheet §8][sheet8]: the bridge activation by validators 0–4, with the
   unsigned `pftl_uniswap_route_bridge_policy_update` handed to the other
   lane; the FastPay record signed by the six validators below height 10001;
   live checks.
4. The relay units on the six hosts in the same window, if the other lane's
   agents are idle.
5. Review of pull requests #56–#67 and the other open contributor pull
   requests; merges into `main` for the next release on the basis of review
   plus CI.

### Only the other lane can provide

Each item shows the date first asked.

- **(a)** The two NEAR Intents design questions ([note][near]). 2026-09-29.
- **(b)** NAVCoin signer keys and custody rows ([inputs][z3]). 2026-09-22.
- **(c)** The Arc source row on the A666 route; epoch 11 has the Ethereum
  source only. 2026-09-28.
- **(d)** A compatible governed NAV profile with fresh proofs for A666.
  2026-09-22.
- **(e)** StakeHub custody Q1. 2026-09-07.
- **(f)** Reserve-proof successor adoption ([PR #49][pr49]). 2026-09-24.
- **(g)/(n)** Validator-5: the window closed in silence and the activation
  is Monday; then one issuer signature for the bridge update. 2026-09-25 /
  2026-10-01.
- **(h)** The height-915 archive and the height-924 custodian. 2026-08-30.
- **(i)** The AI-governance decision for Gate Zero Z2. 2026-09-03.
- **(j)** The six inventory rows needing an operator decision
  ([inventory][inventory]). 2026-09-10.
- **(k)** Disk items on the validators. 2026-09-28.
- **(l)** The `ETHEREUM_MAINNET_RPC_URL` repository secret; the
  `official-mainnet-fork` CI job still warns that it did not run.
  2026-09-28.
- **(m)** The cap values. 2026-09-29.
- **(o)** Permission to delete the other lane's old caches on the work server
  (~200 GB). 2026-10-01.
- **(p)** A maintenance window for the relay units. 2026-10-01.
- **(q)** FW-13 and FW-14. 2026-09-30.

## References

- My [2026-10-08 handoff][previous]; the other lane's
  [2026-10-01 handoff][nazgul].
- Release branch commits: `1e710d74` (before state), `d94e9837` (canary
  backup), `a4fb8bca` (deployment). `main` commit: `63c2e696`.
- `deployments/signer-rotation-20261007/` on
  `release/signer-rotation-20261007`: [README.md][readme],
  [DEPLOY-SHEET.md][sheet], [RELEASE-ID.txt][rid], [observed/][observed],
  [qualification/][qualification].
- [`docs/plans/active/next-validator-release-plan-20261005.md`][plan].
- [`docs/status/chain-state-current.md`][state].

[nazgul]: 2026-10-01___nazgul__navcoin_create_and_swap_build_phase0_and_bmnrc_opening.md
[previous]: 2026-10-08___dravlic__conference_day_two_friday_ready.md
[state]: ../status/chain-state-current.md
[plan]: ../plans/active/next-validator-release-plan-20261005.md
[next]: ../plans/active/next-validator-release-plan-20261101.md
[v5]: ../review/validator-5-signer-committees-decision-proposal-20261001.md
[near]: ../specs/near-intents-architecture-research-20260929.md
[z3]: ../status/z3-cycle1-inputs-20260922.md
[inventory]: ../review/defect-inventory-20260910.md
[readme]: https://github.com/postfiatorg/postfiatl1v2/blob/a4fb8bca523308c98d58f3f9e34ad3b00caeef8b/deployments/signer-rotation-20261007/README.md
[sheet]: https://github.com/postfiatorg/postfiatl1v2/blob/a4fb8bca523308c98d58f3f9e34ad3b00caeef8b/deployments/signer-rotation-20261007/DEPLOY-SHEET.md
[sheet0]: https://github.com/postfiatorg/postfiatl1v2/blob/a4fb8bca523308c98d58f3f9e34ad3b00caeef8b/deployments/signer-rotation-20261007/DEPLOY-SHEET.md#L25-L63
[sheet4]: https://github.com/postfiatorg/postfiatl1v2/blob/a4fb8bca523308c98d58f3f9e34ad3b00caeef8b/deployments/signer-rotation-20261007/DEPLOY-SHEET.md#L64-L81
[sheet5]: https://github.com/postfiatorg/postfiatl1v2/blob/a4fb8bca523308c98d58f3f9e34ad3b00caeef8b/deployments/signer-rotation-20261007/DEPLOY-SHEET.md#L82-L89
[sheet7]: https://github.com/postfiatorg/postfiatl1v2/blob/a4fb8bca523308c98d58f3f9e34ad3b00caeef8b/deployments/signer-rotation-20261007/DEPLOY-SHEET.md#L122-L143
[sheet8]: https://github.com/postfiatorg/postfiatl1v2/blob/a4fb8bca523308c98d58f3f9e34ad3b00caeef8b/deployments/signer-rotation-20261007/DEPLOY-SHEET.md#L145-L159
[rid]: https://github.com/postfiatorg/postfiatl1v2/blob/a4fb8bca523308c98d58f3f9e34ad3b00caeef8b/deployments/signer-rotation-20261007/RELEASE-ID.txt
[observed]: https://github.com/postfiatorg/postfiatl1v2/tree/a4fb8bca523308c98d58f3f9e34ad3b00caeef8b/deployments/signer-rotation-20261007/observed
[before]: https://github.com/postfiatorg/postfiatl1v2/blob/a4fb8bca523308c98d58f3f9e34ad3b00caeef8b/deployments/signer-rotation-20261007/observed/before.json
[after]: https://github.com/postfiatorg/postfiatl1v2/blob/a4fb8bca523308c98d58f3f9e34ad3b00caeef8b/deployments/signer-rotation-20261007/observed/after.json
[record]: https://github.com/postfiatorg/postfiatl1v2/blob/a4fb8bca523308c98d58f3f9e34ad3b00caeef8b/deployments/signer-rotation-20261007/observed/rollout-record.json
[rollback]: https://github.com/postfiatorg/postfiatl1v2/blob/a4fb8bca523308c98d58f3f9e34ad3b00caeef8b/deployments/signer-rotation-20261007/rollback-one.sh
[qualification]: https://github.com/postfiatorg/postfiatl1v2/tree/a4fb8bca523308c98d58f3f9e34ad3b00caeef8b/deployments/signer-rotation-20261007/qualification
[bradsbots]: https://github.com/postfiatorg/postfiatl1v2/pulls?q=is%3Apr+is%3Aopen+author%3Abradsbots
[pr49]: https://github.com/postfiatorg/postfiatl1v2/pull/49
[sh21]: https://github.com/postfiatorg/StakeHub/pull/21
[sh-readiness]: https://github.com/postfiatorg/StakeHub/blob/48e5565269e5e1529089fa6c29394b9bd8465b71/docs/review/live-funds-readiness-20260929.md
