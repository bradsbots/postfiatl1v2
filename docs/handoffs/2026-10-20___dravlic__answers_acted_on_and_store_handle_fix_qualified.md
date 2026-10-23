# Answers acted on and store handle fix qualified

- **Operator:** Domagoj Ravlić (`dravlic`)
- **Date:** 2026-10-20 UTC
- **Responding to:** the other lane's [2026-10-20 handoff][nazgul] (answers to
  (a)–(m)). My previous handoff: [2026-10-19][previous].

## BLUF

1. **The four asks to me are done.**
   - **(l) Caches:** all six are deleted. The work server went from 20 to 214 GB
     free.
     - `postfiatl1v2-arcusdc-current` had nothing unpushed: all 38 branches were
       on origin. I kept its small ignored records locally.
     - The small records of the August passing run went to the private archive
       branch `backup/20261020/storage-g4-passing-run-records` (70 MB, sha256
       `55a3acf3…`).
   - **(g) BMNRC update file:** [`bmnrc-bridge-policy-update.unsigned.json`][bmnrc]
     (sha256 `5179d6f7…`, operation sha256 `10887bf3…`). It sets
     `authority_epoch` 2 and root `72836827…`. Its policy was read from the
     verified height-1123 backup, and it is unchanged at 1131 (route hash
     `b2817e68…`).
   - **(g) Window and sheet:** both published at 10:13Z in the
     [signing sheet][sheet] (release commit `30c6dcd6`).
     - The window was 2026-10-20 12:00–16:00 UTC: A666 on validator-4's RPC at
       height 1132, then BMNRC on validator-5 at 1133.
     - The path: the founder signs with `wallet-sign-asset-transaction` on the
       founder's host, then the signed file goes through
       `mempool_submit_signed_asset_transaction_finality`.
     - The RPC path accepts only the next proposer's host, which corrects the
       earlier "any validator host". The pre-checks and after-reads are in the
       sheet.
   - **Watchdog units:** the `navcoin-proof-watchdog@` user units on validators 0
     and 3 are stopped and disabled ([record][watchdog]).
     - 3 + 14 units, under root's lingering user session.
     - Configs and state files are kept; validator and RPC PIDs are unchanged.
     - Release commit `819918d2`, main `15cc15b6`.

   **The window was not used.** It assumed a message outside the handoff
   channel, so the window moves to the other lane's next shift.
   - The [sheet][sheet] is self-checking: the founder runs its pre-checks right
     before submitting, A666 first on the host that proposes the next height,
     then BMNRC.
   - Use the latest commit on the release branch. `ad9d706c` corrected the
     committee check: it now reads the activation receipt by RPC, because the
     hosts' `ledger.json` is a legacy file that still shows committee 1.
   - My read-only pre-checks of 11:41Z passed on every precondition
     ([record][prechecks], `a0b859da`).
   - I verify both routes at the start of my next day.
2. **STO-07 is fixed and qualified.** STO-07 is the store-handle regression
   found yesterday.
   - **The fix:** main `8644f0af` keeps the transactional store open for the
     life of a consensus operation ([fix][fix]).
     - Database opens per six-validator round: 126 → 8 per validator, 163 → 5
       on the proposer.
     - The lease is still released between requests, so `rpc-serve` can open
       the database.
     - No on-disk, consensus or execution change. Three tests.
     - The runner now records `database_opens` next to `page_reads`.
   - **The G4 re-run:** attempt 3, 12:22–13:17Z (3,288 s), output
     `~/repos/postfiat-storage-g4-regression-20261020`. **PASS**, evidence
     eligible, no height growth in any stage, every gate green
     ([result][result]).
     - Every per-stage p95 is back at the August level. In ms, against attempt
       2 before the fix: certificate 156 vs 763, certified sends 82 vs 663,
       `local_vote` 39 vs 441, `vote_requests` 69 vs 586, proposal 33 vs 94,
       `post_apply_status` 0.7 vs 27.7.
   - **The closure commit `0293e00d`** records the run in the campaign plan, the
     [milestone][milestone], the [inventory][inventory] (STO-07 Fixed) and
     [Current State][state]:
     - ratios 1.0261 (consensus) and 1.0326 (wallet); against the legacy store
       0.340 / 0.447;
     - disk writes per window 1.03 GB at height 50 and 3.68 GB at 5,000. The
       height-50 figure is 2.2× August's: recorded as an observation, cause not
       known;
     - 22,500 lookups per window; page reads 37/43/42 per round; zero database
       opens inside any stage.

     It also re-derives the harness page bounds down to 96/80/32
     ([bounds][bounds]).
   - The deployed release `fastlane-cap-20261014` does not contain the fix. The
     next release carries it together with `fastswap-committee-migrate`.
3. **The answers are recorded where the plans live.** Main `9f5382bf` and
   `27523eeb`; StakeHub [`19a7189`][sh-answers] (the answers) and
   [`97c2a8e`][sh-fw13] (FW-13).
   - **(h) 915:** recorded as lost. I propose the newest signed canary (height
     1123, `d957141e…`) as the replacement replay input ([G3][g3]).
   - **(h) 924:** I am recorded as the custodian.
     - The copies are the two stopped-copy folders of 2026-08-30 on the work
       server (28 + 26 GB). One read-only copy is approved.
     - Their manifest signatures must be verified before any use. Neither folder
       holds a real verdict file.
   - **(i) Z2:** the confirmation is on the [pending-decisions sheet][sheet-pd],
     and the remaining live steps are under Z2 in the
     [testnet-path milestone][testnet].
   - **(b) Z3 cycle 1:** the [command sheet][z3] is rebound to
     `fastlane-cap-20261014`, with the answered rows.
   - **(e), (m) StakeHub:** the custody answer is recorded. Q1: (a) for real
     money, (b) for testnet rehearsals.
   - **FW-13 is implemented.** The venue inventory wallet unlocks only with the
     owner-only operator passphrase file, in `swaps.py` and `orchard.py` as in
     `fastswap.py`. Four fail-first tests; 275 tests green.
4. **Housekeeping.**
   - A second Corbanu session of this lane now runs document work in parallel
     with code work, in the checkout `postfiatl1v2-dravlic`.
   - Corbanu Terminal on the work server was updated 0.1.44 → 0.1.48 by accident
     during that start.

## Current state

- **Fleet.** Live probe: my read-only RPC reads through all six hosts at
  13:41:38Z.
  - Six on `fastlane-cap-20261014` at height 1131, tip `9b054f09…`, root
    `a12e7c5f…`, mempools empty. Unchanged since 2026-10-15
    ([Current State][state]).
  - The other lane's watchdog units were stopped today.
- **Deployment boundary.**
  - Deployed: source `8bed9b90`, executable `b1b3dbb1…`.
  - Release branch `release/fastlane-cap-20261014` is at `a0b859da`. `main`
    was at `aee4a12a` before this handoff.
  - Merged but undeployed: `8644f0af` (STO-07), `2737f080`
    (`fastswap-committee-migrate`) and this week's reviewed merges, listed in
    the [next release plan][next].
- **Routes.**
  - A666 and BMNRC are both still on authority epoch 1 (root `a2eebcba…`):
    0 claims, 0 returns, not paused.
  - Bridge committee epoch 2 has been active since height 1131.
  - Both unsigned update files on the release branch (A666 `24aa2e28…`, BMNRC
    `5179d6f7…`) wait for the founder's signatures.
- **Storage.**
  - STO-07 is Fixed on main (`8644f0af`) and qualified by the G4 re-run PASS.
    It is not deployed yet.
  - The G3 replay is pending: the 924 copy and the 1123 replacement.
  - Rows (h) and (i) of the pending-decisions sheet are answered.
- **Pull requests.** #133–#137 are reviewed and merged (`c8a9f0ec`,
  `aee4a12a`). `0cbe0c54` fixes the Python examples page lines that #133 left.
- **CI on `main`.** At 13:42Z, 10 of the last 20 runs had passed and none had
  failed. The other 10 were still in progress: the `rust-ci` and
  `product-security-ci` runs of the five 13:28–13:31Z pushes.
- **Task Node.** Six tasks are Rewarded today, 14.5 PFT in total. This handoff
  has no Task Node action.
  - `task_f551146d…` founder signing packet (2.5)
  - `task_36fdcf8e…` FW-13 (2)
  - `task_9e5fbf14…` STO-07 fix (4)
  - `task_93924b9a…` PRs #133/#137 (1.5)
  - `task_c2fd3df2…` G4 attempt 3 (3)
  - `task_43fdbf0e…` PRs #134/#136/#135 (1.5)
- **Devnet.** Touched only by the watchdog shutdown: no validator or RPC change.
  The founder's two issuer transactions were **not** submitted. At 13:41Z the
  chain was at 1131 with both route hashes unchanged.

## Next decision or action

### My next steps, in order

1. **The next release.**
   - Cut from main with the STO-07 fix, `fastswap-committee-migrate` and this
     week's reviewed merges, and qualify it locally.
   - Install it on the six validators with a fresh canary backup.
   - Then run `fastswap-committee-migrate` per host, validator-5 first.
   - Once the founder's two updates are in, the next Ethereum checkpoint, 5 of
     6, with validator-5.
2. New bot pull requests, and [#95][pr95]/[#103][pr103] as their authors answer,
   with the same full-read standard.
3. The manifest-signature verification of the two height-924 copies, then the
   G3 replay after STO-07.
4. StakeHub: the first testnet rehearsal under custody rule (b), with FW-13 in
   place (the separate operator passphrase file in all three paths).
5. The re-review of [PR #49][pr49] once the other lane's conditions 1–2 are
   done.

### Only the other lane can provide

I ask the other lane for the following:

- **(g)** The two issuer signatures and submissions, in its next shift, per the
  [sheet][sheet]. If another window suits it better, I name one on request.
- **(f)** [PR #49][pr49] conditions 1–2, and the registration on its host.
- **(k)** The `ETHEREUM_MAINNET_RPC_URL` secret, after its local fork-test run.
- Its review of its unpublished work, the delayed-precommit RED fix first.

## References

- The other lane's [2026-10-20 handoff][nazgul]; my [2026-10-19 handoff][previous].
- Release branch: [signing sheet][sheet] (`ad9d706c`), [BMNRC update][bmnrc]
  (`30c6dcd6`), [watchdog record][watchdog] (`819918d2`),
  [pre-checks][prechecks] (`a0b859da`).
- Main: `15cc15b6`, `d6e44b06`, `9f5382bf`, `27523eeb`, `0cbe0c54`,
  `8644f0af`, `0293e00d`, `aee4a12a`.
- [Storage scaling milestone][milestone]; [G4 regression plan][g4plan]
  ([fix][fix], [result][result], [bounds][bounds]); [next release plan][next].
- [Defect inventory][inventory] (STO-07); [pending-decisions sheet][sheet-pd];
  [Z3 cycle-1 inputs][z3]; [Current State][state].
- StakeHub [`19a7189`][sh-answers], [`97c2a8e`][sh-fw13].

[nazgul]: 2026-10-20___nazgul__founder_lane_resync_and_answers_to_open_asks.md
[previous]: 2026-10-19___dravlic__storage_regression_campaign_on_the_running_code.md
[state]: ../status/chain-state-current.md
[milestone]: ../plans/completed/storage-scaling-milestone.md
[g3]: ../plans/completed/storage-scaling-milestone.md#g3-exact-replay
[g4plan]: ../plans/active/g4-regression-deployed-release-20261019.md
[fix]: ../plans/active/g4-regression-deployed-release-20261019.md#fix-2026-10-20
[result]: ../plans/active/g4-regression-deployed-release-20261019.md#result-2026-10-20-attempt-3-after-the-fix
[bounds]: ../plans/active/g4-regression-deployed-release-20261019.md#bound-re-derivation-2026-10-19
[next]: ../plans/active/next-validator-release-plan-20261101.md
[testnet]: ../plans/active/l1v2-public-testnet-path-milestone.md
[inventory]: ../review/defect-inventory-20260910.md
[sheet-pd]: ../governance/pending-operator-decisions.md
[z3]: ../status/z3-cycle1-inputs-20260922.md
[sheet]: https://github.com/postfiatorg/postfiatl1v2/blob/ad9d706c0dfad77d203b9444d82c375d781a0ed3/deployments/fastlane-cap-20261014/ISSUER-SIGNING-SHEET-20261020.md
[bmnrc]: https://github.com/postfiatorg/postfiatl1v2/blob/30c6dcd647ae1efe5b52061fa0321e21946e7a0b/deployments/fastlane-cap-20261014/observed/bmnrc-bridge-policy-update.unsigned.json
[watchdog]: https://github.com/postfiatorg/postfiatl1v2/blob/819918d2b0cd5798f365bd1c6341537f11b64ead/deployments/fastlane-cap-20261014/observed/watchdog-units-stopped-20261020.json
[prechecks]: https://github.com/postfiatorg/postfiatl1v2/blob/a0b859da7b11e9eefbeb1c4771143e00e34e9ebf/deployments/fastlane-cap-20261014/observed/issuer-window-prechecks-20261020.json
[sh-answers]: https://github.com/postfiatorg/StakeHub/commit/19a7189b744e132edd86ac01fc3d9e2ebc924ff4
[sh-fw13]: https://github.com/postfiatorg/StakeHub/commit/97c2a8e7856c39e10190480d9b1800fd3762f16f
[pr49]: https://github.com/postfiatorg/postfiatl1v2/pull/49
[pr95]: https://github.com/postfiatorg/postfiatl1v2/pull/95
[pr103]: https://github.com/postfiatorg/postfiatl1v2/pull/103
