# Release candidate cut and locally qualified

- **Operator:** Domagoj Ravlić (`dravlic`)
- **Date:** 2026-10-06 UTC
- **Responding to:** no handoff from the other lane since
  [its 2026-10-01 handoff][nazgul]. The other lane presented on stage today; its
  last visible action is the [PR #55][pr55] merge on 2026-10-04. My previous
  handoff: [2026-10-05][previous].

## BLUF

I kept the conference day clean. After the 09:13Z health check (all six at
height 1115, READY WITH ATTENTION) I had no contact with the six validator
hosts or the chain, and I made no StakeHub `master` commit. Everything went into
the release that rolls out on 2026-10-07:

1. the release candidate `signer-rotation-20261007` is cut as branch
   `release/signer-rotation-20261007` from `main` at `0fa55d0b` (release commit
   `17bbaf91`, plan ticks `e92b8157`). Every qualification check that runs on
   the work server passed: two identical clean builds (`decaa411…`), all history
   checks against the signed 1050 canary and the 1020/1021 copies matching the
   recorded roots, the rotation and rollback rehearsal on local copies, the
   signed manifest `fa4649aa…` by publisher `pfc531e0…`, and the store
   conversion on a copy of a July store. Only the host-facing part remains for
   tomorrow: fresh canary backup, before-state, rollout, store conversion,
   activation;
2. a 1-in-256 flaky test fixed (`cf65b81e`), and the same flaw fixed in two
   sibling tests (`69c598da`);
3. the two PR #55 follow-ups (`69c598da`);
4. the three rehearsal test gaps closed (`d7212f34`);
5. the browser wallet lock file updated for a new high-severity advisory that
   had turned `product-security-ci` red on every commit since the morning
   (`0fa55d0b`).

The only Task Node proposal from the network for this account, a Windows
install-script fix in the CorbanuTerminal repository paid only for a merged PR
there, was left alone as outside the product.

## Current state

- **Fleet at 09:13Z** (read-only preflight, the day's only contact). All six at
  height 1115, tip `28e1175b…`, root `a5287eaf…`. READY WITH ATTENTION (the
  hand-started relays); no block since the weekend. The other lane's
  `navcoin-proof-watchdog@` user units: 14 on the validator-3 host, 3 on
  validator-0. CI on `main` at the start of the day: all three workflows green
  on `43f8c261`, `d9c42a79` and `1100c6ce`.
- **Flaky test** (`cf65b81e`, test only).
  - [`catch_up_rejects_malformed_batches_without_durable_mutation`][cs1240]
    tampered a random signature by overwriting its first byte with `00`, a no-op
    in about 1 run in 256.
  - Before the fix it reproduced in 1 of 400 parallel runs, like the CI failure
    on `8d1c9c20` ([run 37292381418][run8d1c], same assertion at
    [`cobalt_shadow_tests.rs:1254`][cs1254]); after it, 0 of 520. The fix flips
    every bit of the first byte.
  - `69c598da` fixes the same pattern in
    [`cobalt_shadow_tests.rs:1377`][cs1377] and
    [`atomic_swap_execution_tests.rs:741`][as741], [`:743`][as743]. The two other
    `00` sites ([`pftl_swapd.rs:3026`][sw3026],
    [`consensus_v2_store.rs:720`][cv720]) already check that the signature
    changed.
  - Task Node `task_f193dacfd1f9d8614cb4a40813b2b3fa`: Rewarded 1.75 PFT.
- **PR #55 follow-ups** (`69c598da`).
  - Python fallback scan ([`_account_tx_client_side_scan`][py1589]): truncated
    only when a further matching row exists or the range continues past a full
    block window (one extra block is fetched only when the page is full).
    Without a start height it returns the newest rows. Four tests in
    [`test_account_tx_fallback.py`][pyt] fail first, then pass.
  - Rust archive scan ([`account_tx_scan`][bf545]): newest rows without a start
    height, like the disk index ([test][att106], fails first, then passes).
  - Kept: the scan's `truncated` still means "possibly incomplete" when the
    range has more blocks than the limit, documented in
    [Account History][acchist] and under [plan][plan] item (3b). An exact flag
    needs a whole-range scan that grows with the square of the chain length, and
    the scan is used whenever the index is stale
    ([`storage_commit.rs:2762`][sc2762]).
  - Counts: `account_tx` 10, `cobalt_shadow` 14, `atomic_swap` 14,
    `python/tests` 629 passed and 3 skipped.
  - Still inconsistent and pre-existing: with an end height below the tip, the
    fallback fetches the newest blocks before filtering; the scan sees plain
    transfers only.
  - Task Node `task_0680aa3df68ec01e165950c0b9b115f6`: Rewarded 2.5 PFT.
- **Rehearsal test gaps** (`d7212f34`).
  - StopPrepare end to end on a fixture with one epoch-1 FastSwap policy
    ([test][fcs795]): prepare, five votes, assemble, mempool admission and block
    execution `fastlane_control_applied`, fence present. A missing policy epoch
    is refused with `InvalidFence`.
  - StopPrepare refusals ([test][fcs845]): validator-5's stale key at sign,
    assemble and admission; four votes at assemble and admission; ledger
    unchanged.
  - Store conversion ([tests][lmt327]): a legacy snapshot converts. A forced
    restore after a failed verification ([`cfg(test)` hook][lm135]) brings the
    originals back, removes the new key and leaves no temporary files.
  - FastPay epoch boundary ([test][otr1537]): an epoch-2 record installed at
    height 100 must start exactly at 10001; payments are `NotYetValid` at 10000
    and applied at 10001.
  - Focused suites: storage `fastswap_store` 25, execution
    `owned_transfer_recovery` 12, node `fastswap_control` 6.
  - Not covered: the fixtures write the policy and tip directly; no
    continuation to the final checkpoint and activation; no node-level signing
    at height 10001; no test runs on a real store copy (the qualification below
    did, once).
  - Task Node `task_6ba8fc0b8d34ef11b483c229263adba7`: Rewarded 2.5 PFT.
- **Browser wallet lock file** (`0fa55d0b`, `wallet-web/package-lock.json`
  only, three lines).
  - `source-map-js` 1.2.1 → 1.2.2 for GHSA-68fv-2mgg-jv7q. The advisory made the
    `product-security-ci` job `wallet-and-proxy` fail at
    `npm audit --audit-level=moderate` on `cf65b81e`
    ([run 37445837400][runcf65]), then on `69c598da` and `d7212f34`, and would
    have failed every later commit.
  - `postcss` is already 8.5.26, so [Dependabot alert #2][dep2] is stale.
  - After the fix: the audit reports 0 vulnerabilities, `npm test` 260/260, the
    build passes. The two browser test commands (`test:custody-browser`,
    `test:public-browser`) cannot run on the work server (Chromium lacks
    `libnspr4`); they pass only in CI, where the libraries are installed.
  - `wallet-web` in this repository is not what the other lane serves or demos.
- **Release candidate `signer-rotation-20261007`** ([release inputs][rel],
  [deploy sheet][sheet], [qualification packet][qual]).
  - Branch `release/signer-rotation-20261007`, cut from `main` at `0fa55d0b`,
    the qualified source tip. The branch tip `17bbaf91` adds only
    `deployments/signer-rotation-20261007/`. `e92b8157` on `main` ticks the
    [plan][plan] and records "cut, not deployed" in [Current State][state].
  - Builds ([node-builds.json][builds]): two clean builds from two fresh source
    trees give the identical executable
    `decaa411376a125fb377a29037b6dd470afb2208a268d30a3ce8130f571b370f`
    (rustc 1.95.0, the 2026-09-28 flags and path remaps,
    `SOURCE_DATE_EPOCH` 1789514690).
  - History checks with the new binary, all matching the recorded values:
    - the signed 1050 canary backup of validator-1: import, checkpoint and full
      replay, tip `03a24230…`, root `13d9e652…`; a copy with a changed signature
      is rejected;
    - the six original copies at 1020 (replay through block 1011):
      `9d02b8ee…` / `587c6526…`;
    - the two saved rotated copies at 1021: `5323a2a5…` / `d19264ca…`;
    - six freshly rotated copies at 1021: `11427e60…` / `fda2546f…`.
  - Rehearsal:
    - local signer rotation on six throwaway copies in both start orders, with
      restart;
    - rollback: the deployed 2026-09-28 binary reads data written by the new
      one with matching roots. It passes the checkpoint check on all six
      rotated copies, the full replay of validator-0 at 1021 and the signed 1050
      canary import with checkpoint and full replay;
    - `rollback-one.sh`: the checkpoint and identity checks pass. Its key check
      could not run, because the archived copies carry no faucet key file;
    - the 33 generated files differ from the deployed stage only by
      `--max-requests 100000` and `RestartSec=1` in the six RPC units and the
      `POSTFIAT_DEPLOYMENT_VERIFIED_RECORD` line in the twelve environment
      files; `systemd-analyze verify` is clean on the 12 units;
    - `deployment_manifest_verified` reads `true` with a verification record and
      `false` without one or with a tampered one;
    - `fastswap-store-migrate` on a copy of validator-5's July store converts 26
      of 26 records, a second run finds nothing, and restoring the backup gives
      the legacy store back.
  - Tests: the focused tests for everything after the 2026-10-05 full suite and
    the 2026-09-28 release tests pass (the Python run needs `PYTHONPATH=python`,
    as CI sets it). The full workspace suite of `672b707c` (2026-10-05) is
    cited, not rerun.
  - Manifest signed ([manifest][manifest]):
    `fa4649aa842d0f7aadb4f13aa6dd6eba647f3a0ddc3004562bc3d45d989a203f`,
    publisher `pfc531e00ffefecb8fabe40c6f47c69148df31e49c`. The local preflight
    passes the signed check for all six validators. The signed stage is kept
    under `~/.postfiat/deployments/signer-rotation-20261007/` on the work
    server, not in Git.
  - CI runs on `main` and pull requests only, so the release branch has no runs;
    `0fa55d0b` is in the CI bullet below.
  - Not done today: canary backup, fleet before-state, rollout, store
    conversion, activation.
  - Two points to confirm on the day from the deploy sheet: the store
    conversion order (validator-5 first), and the user the conversion runs as.
    The sheet writes `runuser -u postfiat` so the files stay owned by the
    service user; the [runbook][storerun] does not name the user.
  - Task Node `task_0d3f8a1305cf45f387e22af5c3cfb16e`: Rewarded 3.5 PFT.
- **Task Node proposals.** One network task for this account
  (`req_net_de393e87…`, `task_70dd87a5…`, "Fix install.ps1 Junction Handling
  Defect With Merged PR" in the CorbanuTerminal repository, paid only for a
  merged PR there), left untouched as outside the product. The six other
  outstanding tasks are the other lane's own requests from 2026-08-25 to
  2026-09-10.
- **CI on `main`** (`gh run list --limit 100`, read once at 11:55Z).
  - `cf65b81e`: `docs-build` and `rust-ci` passed; `product-security-ci` failed
    only in `wallet-and-proxy`, on the `source-map-js` advisory (see the lock
    file bullet).
  - `69c598da` and `d7212f34`: `docs-build` passed; `product-security-ci`
    failed the same way; `rust-ci` `check` passed, `test` running.
  - `0fa55d0b`: `docs-build` and `product-security-ci` passed; `rust-ci`
    `check` passed, `test` running.
  - `e92b8157`: `docs-build` passed; `product-security-ci` running
    (`wallet-and-proxy` passed); `rust-ci` `check` passed, `test` running.
- **Work server.** 71 GB free. StakeHub `master` unchanged at `52eb686`;
  [PR #21][sh21] open for 2026-10-07.
- **Devnet and deployment boundary.**
  - Live probe: only the read-only health check at 09:13Z. No transaction, no
    restart, no configuration change.
  - Deployed: `combined-fastpay-20260928`, executable `1f8b332d…`, source
    `c93b2137`, unchanged since 2026-09-28.
  - Repository: `main` at `e92b8157` before this handoff;
    `release/signer-rotation-20261007` at `17bbaf91`.
  - Merged but undeployed: everything on `main` since `c93b2137`, carried by the
    candidate up to `0fa55d0b` ([scope][rel]).
- **Task Node.** Four tasks today, all Rewarded: `task_f193dac…` (flaky test)
  1.75 PFT, `task_0680aa3…` (PR #55 follow-ups) 2.5 PFT, `task_6ba8fc0…` (test
  gaps) 2.5 PFT, `task_0d3f8a1…` (release cut) 3.5 PFT. The lock-file step had
  no Task Node action. This handoff has no Task Node task.

## Next decision or action

### My next steps, in order

On 2026-10-07, each live step with its own go on the day
([deploy sheet][sheet]):

1. Before anything: health check; CI green on `0fa55d0b`, the release's
   source tip; the other lane's reaction to the [validator-5 note][v5]. The
   [plan][plan] and the sheet's GO 0 start the host-facing steps only after the
   objection window closes (2026-10-07 evening UTC).
2. Fresh signed canary backup from validator-1 and the fleet before-state; the
   store conversion dry run on a copy of validator-1's `fastswap-v1` directory.
3. Rollout with `scripts/postfiat-safe-rollout apply-next`, one validator at a
   time (validator-1 canary, then 0, 2, 3, 4, 5), one faucet grant per
   validator, health and agreement after each. Then the post-rollout checks:
   `deployment_manifest_verified` true, the RPC unit arguments, event logs, the
   adapted preflight.
4. In the same window: the store conversion per host with both units stopped
   (validator-5 first), then `fastswap_checkpoint_status` on validators 0–4.
   The relay units on the six hosts are not on the sheet, and the plan keeps
   them out of the release; they join only with (p).
5. Activation: the StopPrepare fences, the final drained checkpoint,
   `ActivateCommittee` epoch 2 (validators 0–4), and the unsigned
   `pftl_uniswap_route_bridge_policy_update` handed to the other lane. Then
   `fastpay-committee-prepare` and the six-validator signed record below height
   10001; live checks with 5 of 6 signers.
6. Merge [PR #54][pr54] after its Orchard test, and StakeHub [PR #21][sh21];
   then the records and the plan.

### Only the other lane can provide

Each item shows the date first asked.

- **(a)** The two NEAR Intents design questions ([note][near]). 2026-09-29.
- **(b)** NAVCoin signer keys and custody rows ([inputs][z3]). 2026-09-22.
- **(c)** The Arc source row on the A666 route; epoch 11 exists since
  2026-10-04 with the Ethereum source only. 2026-09-28.
- **(d)** A compatible governed NAV profile with fresh proofs for A666.
  2026-09-22.
- **(e)** StakeHub custody Q1. 2026-09-07.
- **(f)** Reserve-proof successor adoption ([PR #49][pr49]). 2026-09-24.
- **(g)/(n)** Validator-5: the objection window until 2026-10-07 evening UTC,
  then one issuer signature for the bridge update. 2026-09-25 / 2026-10-01.
- **(h)** The height-915 archive and the height-924 custodian. 2026-08-30.
- **(i)** The AI-governance decision for Gate Zero Z2. 2026-09-03.
- **(j)** The six inventory rows needing an operator decision
  ([inventory][inventory]). 2026-09-10.
- **(k)** Disk items on the validators. 2026-09-28.
- **(l)** The `ETHEREUM_MAINNET_RPC_URL` repository secret. 2026-09-28.
- **(m)** The cap values. 2026-09-29.
- **(o)** Permission to delete the other lane's old caches on the work server
  (~200 GB). 2026-10-01.
- **(p)** A maintenance window for the relay units. 2026-10-01.
- **(q)** FW-13 and FW-14. 2026-09-30.

## References

- My [2026-10-05 handoff][previous]; the other lane's
  [2026-10-01 handoff][nazgul].
- Commits on `main`: `cf65b81e`, `69c598da`, `d7212f34`, `0fa55d0b`,
  `e92b8157`; on `release/signer-rotation-20261007`: `17bbaf91`.
- `deployments/signer-rotation-20261007/`: [README.md][rel],
  [DEPLOY-SHEET.md][sheet], [qualification/README.md][qual].
- [`docs/plans/active/next-validator-release-plan-20261005.md`][plan].
- [`docs/review/signer-committee-rotation-dry-run-20261005.md`][dryrun].
- [`docs/rpc/account-history.md`][acchist].
- [`docs/status/chain-state-current.md`][state].

[nazgul]: 2026-10-01___nazgul__navcoin_create_and_swap_build_phase0_and_bmnrc_opening.md
[previous]: 2026-10-05___dravlic__release_after_the_conference_prepared_on_main.md
[plan]: ../plans/active/next-validator-release-plan-20261005.md
[state]: ../status/chain-state-current.md
[acchist]: ../rpc/account-history.md#result-window-and-truncated
[storerun]: ../runbooks/fastpay-committee-recovery.md#converting-the-fastswap-store-before-the-rotation
[dryrun]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/review/signer-committee-rotation-dry-run-20261005.md
[v5]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/review/validator-5-signer-committees-decision-proposal-20261001.md
[inventory]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/review/defect-inventory-20260910.md
[z3]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/status/z3-cycle1-inputs-20260922.md
[near]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/specs/near-intents-architecture-research-20260929.md
[pr49]: https://github.com/postfiatorg/postfiatl1v2/pull/49
[pr54]: https://github.com/postfiatorg/postfiatl1v2/pull/54
[pr55]: https://github.com/postfiatorg/postfiatl1v2/pull/55
[sh21]: https://github.com/postfiatorg/StakeHub/pull/21
[dep2]: https://github.com/postfiatorg/postfiatl1v2/security/dependabot/2
[run8d1c]: https://github.com/postfiatorg/postfiatl1v2/actions/runs/37292381418
[runcf65]: https://github.com/postfiatorg/postfiatl1v2/actions/runs/37445837400
[rel]: https://github.com/postfiatorg/postfiatl1v2/blob/17bbaf91a9264880b43a208d87c7716d4d4ebe6d/deployments/signer-rotation-20261007/README.md
[sheet]: https://github.com/postfiatorg/postfiatl1v2/blob/17bbaf91a9264880b43a208d87c7716d4d4ebe6d/deployments/signer-rotation-20261007/DEPLOY-SHEET.md
[qual]: https://github.com/postfiatorg/postfiatl1v2/blob/17bbaf91a9264880b43a208d87c7716d4d4ebe6d/deployments/signer-rotation-20261007/qualification/README.md
[builds]: https://github.com/postfiatorg/postfiatl1v2/blob/17bbaf91a9264880b43a208d87c7716d4d4ebe6d/deployments/signer-rotation-20261007/node-builds.json
[manifest]: https://github.com/postfiatorg/postfiatl1v2/blob/17bbaf91a9264880b43a208d87c7716d4d4ebe6d/deployments/signer-rotation-20261007/deployment-manifest.signed.json
[cs1240]: https://github.com/postfiatorg/postfiatl1v2/blob/cf65b81e3c8ce4b0267a2c7b4bbbecb3cd4d0aa6/crates/node/src/cobalt_shadow_tests.rs#L1240-L1244
[cs1254]: https://github.com/postfiatorg/postfiatl1v2/blob/8d1c9c207fea0816b6acdad788271179b0faffda/crates/node/src/cobalt_shadow_tests.rs#L1254
[cs1377]: https://github.com/postfiatorg/postfiatl1v2/blob/69c598da6101ba686a474ad1971d6b62ddb4b8b7/crates/node/src/cobalt_shadow_tests.rs#L1377
[as741]: https://github.com/postfiatorg/postfiatl1v2/blob/69c598da6101ba686a474ad1971d6b62ddb4b8b7/crates/execution/src/atomic_swap_execution_tests.rs#L741
[as743]: https://github.com/postfiatorg/postfiatl1v2/blob/69c598da6101ba686a474ad1971d6b62ddb4b8b7/crates/execution/src/atomic_swap_execution_tests.rs#L743
[sw3026]: https://github.com/postfiatorg/postfiatl1v2/blob/69c598da6101ba686a474ad1971d6b62ddb4b8b7/crates/node/src/bin/pftl_swapd.rs#L3026
[cv720]: https://github.com/postfiatorg/postfiatl1v2/blob/69c598da6101ba686a474ad1971d6b62ddb4b8b7/crates/node/src/consensus_v2_store.rs#L720
[py1589]: https://github.com/postfiatorg/postfiatl1v2/blob/69c598da6101ba686a474ad1971d6b62ddb4b8b7/python/postfiat_rpc/client.py#L1589
[pyt]: https://github.com/postfiatorg/postfiatl1v2/blob/69c598da6101ba686a474ad1971d6b62ddb4b8b7/python/tests/test_account_tx_fallback.py
[bf545]: https://github.com/postfiatorg/postfiatl1v2/blob/69c598da6101ba686a474ad1971d6b62ddb4b8b7/crates/node/src/block_finality.rs#L545
[att106]: https://github.com/postfiatorg/postfiatl1v2/blob/69c598da6101ba686a474ad1971d6b62ddb4b8b7/crates/node/src/tests/account_tx_truncation.rs#L106
[sc2762]: https://github.com/postfiatorg/postfiatl1v2/blob/69c598da6101ba686a474ad1971d6b62ddb4b8b7/crates/node/src/storage_commit.rs#L2762-L2765
[fcs795]: https://github.com/postfiatorg/postfiatl1v2/blob/d7212f34817dd8d9458ef12d0c7c266b81b9662e/crates/node/src/fastswap_control_signing.rs#L795
[fcs845]: https://github.com/postfiatorg/postfiatl1v2/blob/d7212f34817dd8d9458ef12d0c7c266b81b9662e/crates/node/src/fastswap_control_signing.rs#L845
[lmt327]: https://github.com/postfiatorg/postfiatl1v2/blob/d7212f34817dd8d9458ef12d0c7c266b81b9662e/crates/storage/src/fastswap_store/legacy_migration/tests.rs#L327
[lm135]: https://github.com/postfiatorg/postfiatl1v2/blob/d7212f34817dd8d9458ef12d0c7c266b81b9662e/crates/storage/src/fastswap_store/legacy_migration.rs#L135
[otr1537]: https://github.com/postfiatorg/postfiatl1v2/blob/d7212f34817dd8d9458ef12d0c7c266b81b9662e/crates/execution/src/owned_transfer_recovery.rs#L1537
