# Storage regression campaign on the running code

- **Operator:** Domagoj Ravlić (`dravlic`)
- **Date:** 2026-10-19 UTC
- **Responding to:** no handoff from the other lane since
  [its 2026-10-01 handoff][nazgul]. My previous handoff: [2026-10-16][previous].

## BLUF

1. **G4 regression: PUBLIC TESTNET BLOCKED.**
   - The [storage milestone][milestone]'s status text was stale. It still said
     "no deployment-eligible candidate" and pointed at `ff2b3532`/`48a94425`.
     In fact the seventh one-shot G4 run on `d0ae79f3` passed on 2026-08-30, the
     storage-lease line has run on all six validators since 2026-08-31, and the
     deployed release `fastlane-cap-20261014` (`8bed9b90`) descends from it. I
     corrected the milestone (`82e19626`).
   - I then ran a [G4 regression campaign][g4plan] on the current code, to check
     it still meets the G4 criteria. Candidate `29824ed7` is the deployed source
     plus the commits merged since (`2737f080`, the offline
     `fastswap-committee-migrate` command, and the test-only #131 change). The
     runner is the `ae6ec9cb` line at `51a19272` (branch
     `g4-runner-bounds-20261019`). One run, no retry: 10:52:46–12:03:29Z (3,975 s).
   - Four gates fail ([result][result]):
     - height-cost model: `certified_sends_ms` grows with height (per-window p95
       median 663 ms at height 50 → 842 ms at 5,000; fitted +170 ms against a
       150 ms threshold);
     - wallet-to-final, height 5,000 vs 50: 1.1046 against the 1.10 limit;
     - the new store vs the legacy JSON store at height 50: 1.531 (consensus
       round) and 1.600 (wallet-to-final), where August measured 0.345 and
       0.356. The new engine is now slower than the store it replaced.

     The consensus-round ratio 5,000 vs 50 passes at 1.0994.
   - Against the August pass, every consensus-path stage is 3–30× slower at both
     heights (certificate 167 → 763 ms, certified sends 80 → 663, local vote
     40 → 441, vote requests 65 → 586, proposal 32 → 94, post-apply status
     0.9 → 27.7). `local_apply`, `write_commit` and the legacy lane are
     unchanged, so the environment is ruled out.
   - Cause (file:line evidence in the [result][result]): a real regression since
     `f0013c29` (2026-08-31, the bounded writer lease). The node no longer keeps
     its redb database open; most store lookups reopen and close it. On every
     close redb 4.2 writes the free-space map and trims the file, at a cost that
     grows with the database size (14.7 MB at height 50, 1.81 GB at 5,000).
     - Disk writes per window: 0.47 → 10.9 GB at height 50 and 37 GB at height
       5,000, for identical logical writes.
     - Lookups per window: 17,700 → 44,700 (`f0013c29` plus
       `d8f65885`/`943c4ca7`).
     - The runner misses redb's close-time writes: it counts only the
       application's fsyncs.
   - This is a blocking finding for the public-testnet path ([STO-07][inventory],
     P1). The devnet runs this store code, idle at height 1131; nothing changed
     on the validators.
2. **Page bound (finding on the way).** The first attempt (on `8bed9b90`) stopped
   at G2: the harness's per-round page bound (64 lookups per proposal) no longer
   fits the current code.
   - The proposal round does 74 lookups and the validator rebuild 80 (29 and 35
     on `d0ae79f3`). Two shipped changes cause it: `f0013c29` re-validates the
     generation pointer on every store-handle lookup (one more metadata read per
     state read), and `d8f65885`/`943c4ca7` make `read_fastpay_ledger` do about
     11 lookups where it did 2.
   - The node enforces no such limit. Writes and full-history reads are unchanged
     (0), and the cost is fixed per round, not growing with height, so it is not
     a scaling regression under the milestone's criterion.
   - I re-derived the bounds with the old headroom (proposal reads 176, apply
     reads 160, writes 32; `29824ed7`, runner `51a19272`) and recorded the reason
     in the [plan][bounds]. The cheap fix (cache the pointer validation per node
     store) is part of the store-handle candidate in the
     [next release plan][next].
3. **Pull requests.** I did not review the five bot pull requests of the weekend
   ([#133][pr133]–[#137][pr137]; [#134][pr134] reports a wrong result in
   Friday's `fastswap-committee-migrate`). The server had to stay quiet during
   the measurement. They are tomorrow's second item.
4. **Work server.** I removed 33 GB of my own build and repair caches; every kept
   archive has another verified copy. The harness binaries cannot be rebuilt to
   the same hash (the random linker temp path, inventory row SQ-01).

Records: the [G4 regression plan][g4plan], [Current State][state] (2026-10-19
section), [STO-07][inventory].

## Current state

- **Fleet.** Last observation: my read-only `observe-fleet` run at 07:47:40Z
  (verified). Six on `fastlane-cap-20261014` at height 1131, tip `9b054f09…`,
  root `a12e7c5f…`, unchanged since 2026-10-15. That run was the only live probe
  of this session; I did not touch the validators.
- **Deployment boundary** ([Current State][state]).
  - Deployed: source `8bed9b90`, executable `b1b3dbb1…`
    ([RELEASE-ID.txt][releaseid]).
  - Release branch `release/fastlane-cap-20261014` is at `6b4fa4b0`, unchanged
    today. `main` was at `93b73181` before this handoff.
  - Merged but undeployed: `2737f080` and #129–#132 (as on 2026-10-16), plus
    today's `29824ed7` (campaign page bounds in `run_campaign.py`, harness only).
- **Storage gates on the current code.** G1 PASS, G2 PASS (with the re-derived
  page bounds), G4 BLOCKED (the height-cost model on certified sends plus three
  ratio gates). G3/G5 (`OFFLINE QUALIFIED`) still need the other lane's
  height-915 archive and the height-924 custodian, (h) below. G6 needs fresh
  copies and a separate decision.
- **Campaign records** (work server, not in Git):
  - `~/.cache/storage-g4-20261019/` (`status.json`, the gate reports);
  - G4 output `~/repos/postfiat-storage-g4-regression-20261019` (campaign report
    `94188f3c…`, checkpoint `d1bb6e97…`).

  Committed in `93b73181`: the campaign result, the milestone status, the
  inventory row STO-07, the release-plan item and the Current State paragraph.
- **A666 issuer update.** Prepared, not yet signed:
  [`observed/a666-bridge-policy-update.unsigned.json`][update], sha256
  `24aa2e28…`.
- **CI on `main`.** I read `gh run list --branch main --limit 20` once at 12:49Z:
  18 runs passed, none failed, and the `rust-ci` and `product-security-ci` runs of
  `93b73181` were still in progress.
- **Devnet.** Not touched: no validator or RPC restart, no transaction.
- **Task Node.** The campaign task `task_58ffc05cea0a90f85b7218e86c80230c` is
  Rewarded (4.5 PFT), with the BLOCKED verdict stated plainly in its evidence. No
  other task today. This handoff has no Task Node action.

## Next decision or action

### My next steps, in order

1. Fix the store handle lifetime (`f0013c29` follow-up;
   [`transactional.rs:2664`][lease]):
   - open the store once per consensus operation or round in
     `transport-validator-serve` and pass the handle down, closing it between
     rounds so `rpc-serve` can open it;
   - reuse the validated pointer for the handle's life;
   - add an open/close counter to the runner.

   About 0.5–1 day with focused storage and node tests, then one G4 re-run
   (~66 min). If it passes, the next release carries the fix together with
   `fastswap-committee-migrate`. The review of #133–#137 the same day.
2. New bot pull requests, and [#95][pr95]/[#103][pr103] as their authors answer.
3. The next release, when its change set is ready; it carries
   `fastswap-committee-migrate`. On its release day:
   - the migration on the six validators, validator-5 first;
   - once the issuer update is signed, the next Ethereum checkpoint with
     validator-5.

### Only the other lane can provide

I ask the other lane for the following; each shows the date first asked.

- **(a)** NEAR Intents question 2 ([note][near]). 2026-09-29.
- **(b)** The NAVCoin signer keys and the cycle inputs ([inputs][z3]).
  2026-09-22.
- **(c)** The Arc source row on the A666 route. 2026-09-28.
- **(d)** A compatible governed NAV profile with fresh proofs. 2026-09-22.
- **(e)** StakeHub custody Q1. 2026-09-07.
- **(f)** The reserve-proof successor adoption and registration
  ([PR #49][pr49] at `f12b8d57`). 2026-09-24.
- **(g)** Validator-5: one issuer-key signature and the submission of the
  prepared A666 bridge policy update ([file][update]), and the same update for
  the BMNRC route. 2026-09-25 / 2026-10-01.
- **(h)** The height-915 archive and the height-924 custodian. These now block
  the only remaining storage gates, G3/G5. 2026-08-30.
- **(i)** The AI-governance decision for Gate Zero Z2. 2026-09-03.
- **(j)** The inventory rows SCT-10 and PI-16 ([inventory][inventory]).
  2026-09-10.
- **(k)** The `ETHEREUM_MAINNET_RPC_URL` repository secret. 2026-09-28.
- **(l)** Permission to delete the other lane's old caches on the work server
  (~200 GB; 105 GB of them are old storage-campaign folders). 2026-10-01.
- **(m)** FW-13. 2026-09-30.

## References

- My [2026-10-16 handoff][previous]; the other lane's
  [2026-10-01 handoff][nazgul].
- Commits: `main` `82e19626`, `29824ed7`, `93b73181`; runner `51a19272` (branch
  `g4-runner-bounds-20261019`); release branch: none today.
- [Storage scaling milestone][milestone]; [G4 regression plan][g4plan]
  ([result][result], [bound re-derivation][bounds]);
  [next release plan][next]; [defect inventory][inventory].
- Runner: [`benchmarks/storage-scaling/run_campaign.py`][runner] (at `51a19272`).
- [Current State][state].

[nazgul]: 2026-10-01___nazgul__navcoin_create_and_swap_build_phase0_and_bmnrc_opening.md
[previous]: 2026-10-16___dravlic__committee_migration_command_and_relays_persistent.md
[state]: ../status/chain-state-current.md
[milestone]: ../plans/completed/storage-scaling-milestone.md
[g4plan]: ../plans/active/g4-regression-deployed-release-20261019.md
[result]: ../plans/active/g4-regression-deployed-release-20261019.md#result-2026-10-19
[bounds]: ../plans/active/g4-regression-deployed-release-20261019.md#bound-re-derivation-2026-10-19
[next]: ../plans/active/next-validator-release-plan-20261101.md#candidates
[inventory]: ../review/defect-inventory-20260910.md
[near]: ../specs/near-intents-architecture-research-20260929.md
[z3]: ../status/z3-cycle1-inputs-20260922.md
[runner]: https://github.com/postfiatorg/postfiatl1v2/blob/51a1927220637158f26a3b1383be1065e7f1ada4/benchmarks/storage-scaling/run_campaign.py
[lease]: https://github.com/postfiatorg/postfiatl1v2/blob/93b7318120095fb595e2359cf3f1e3dc2e8eef6f/crates/storage/src/transactional.rs#L2664
[releaseid]: https://github.com/postfiatorg/postfiatl1v2/blob/6b4fa4b0596fecbdad663d9cddf902ae7b56d8b7/deployments/fastlane-cap-20261014/RELEASE-ID.txt
[update]: https://github.com/postfiatorg/postfiatl1v2/blob/6b4fa4b0596fecbdad663d9cddf902ae7b56d8b7/deployments/fastlane-cap-20261014/observed/a666-bridge-policy-update.unsigned.json
[pr49]: https://github.com/postfiatorg/postfiatl1v2/pull/49
[pr95]: https://github.com/postfiatorg/postfiatl1v2/pull/95
[pr103]: https://github.com/postfiatorg/postfiatl1v2/pull/103
[pr133]: https://github.com/postfiatorg/postfiatl1v2/pull/133
[pr134]: https://github.com/postfiatorg/postfiatl1v2/pull/134
[pr137]: https://github.com/postfiatorg/postfiatl1v2/pull/137
