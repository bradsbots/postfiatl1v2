# Committee migration command and relays persistent

- **Operator:** Domagoj Ravlić (`dravlic`)
- **Date:** 2026-10-16 UTC
- **Responding to:** no handoff from the other lane since
  [its 2026-10-01 handoff][nazgul]. My previous handoff: [2026-10-15][previous].

## BLUF

1. **FastSwap committee.** The FastSwap service's local committee could not be
   moved to epoch 2 by editing a file.
   - A read-only investigation (the `fastswap_service.rs` open path, the
     snapshot/base/WAL load, `verify_migrated_committee_base`) showed that an
     epoch-2 open also needs a migrated base state built from the drained epoch-1
     state. Validators 0–4 load an epoch-1 snapshot; validator-5 loads an
     un-applied 26-record WAL. No command did that transform; it lived only in a
     unit test.
   - So I wrote the offline command `postfiat-node fastswap-committee-migrate` on
     `main` (`2737f080`), with ten tests including the real packet files and a
     [runbook section][runbook]. It ships with the next release and runs per host
     with both units stopped, validator-5 first.
   - Until then `fastswap_capabilities` keeps reporting epoch 1, `enabled` false
     (validator-5: `fastswap_unavailable`). Ethereum checkpoint signing follows
     the route's `authority_epoch`, so nothing is affected.
2. **Relays.** The last transient relay units are persistent systemd services: the
   28703 archive relay on all six hosts and validator-1's 28701 relay (release
   `e8132e5c`, `main` `f17e09ea`). The release preflight then said NOT READY only
   because its scripts still named the old transient unit. I corrected the two
   checks in the packet (`6b4fa4b0`); the preflight is READY again.
3. **Pull requests.** I reviewed the four bot pull requests of the night in full
   and merged them (#129–#132; record `abc9cdef`). They close the three findings
   my reviews had left open.
4. **Work server.** I removed 9 GB of my rehearsal copies (60 GB free). The other
   lane's ~200 GB of caches still wait for its word, (l) below.

Records: [Current State][state] (2026-10-16 section), the [release packet][packet].

## Current state

- **Fleet.** Last observation: my read-only [preflight][preflight] at 10:55:03Z
  (READY, 60 PASS / 0 ATTENTION / 0 FAIL) and [fleet observation][observe] at
  10:56:22Z (PASS). Six on `fastlane-cap-20261014` at height 1131, tip `9b054f09…`,
  root `a12e7c5f…`, unchanged since yesterday's activation. These two runs were
  the only live probes of this session.
- **Deployment boundary.**
  - Deployed: source `8bed9b90`, executable `b1b3dbb1…`
    ([RELEASE-ID.txt][releaseid]).
  - Release branch `release/fastlane-cap-20261014` is at `6b4fa4b0`. `main` was at
    `f17e09ea` before this handoff.
  - Merged but undeployed: `2737f080` (node CLI only, no consensus or execution
    change), #129, #130 and #132 (Python and wallet-proxy), #131 (tests only, no
    binary change). `2737f080` is on the plan's [already-on-main list][already].
- **Migration command** (`2737f080`;
  `crates/node/src/fastswap_committee_migration.rs`,
  `crates/storage/src/fastswap_store/committee_migration.rs`).
  - It takes the store lock and loads the store as the open does.
  - It checks the drained state against the anchored checkpoint `355fe608…`,
    roots included.
  - It writes the epoch-2 base with the chain committee's domain and records the
    anchor in it. The fences are dropped; the chain re-registers them.
  - Writes are atomic with mode 0600. The WAL and snapshot are moved aside, with a
    SHA3-384 backup manifest.
  - A real open verifies the result; any failure restores the backup. It has
    `--dry-run` and gives a JSON report.
  - The migration on the six is an item of the [next release plan][next].
- **Relays** ([record][relays]). `navcoin-ethereum-rpc-28703.service` and
  validator-1's `navcoin-ethereum-rpc-28701.service` are in `/etc/systemd/system`
  and enabled.
  - Swaps ran 10:45:16–10:46:41Z, each with a 0.8–1.3 s port gap. HTTP 200
    before and after.
  - Validator, RPC and the other lane's watchdog processes did not change.
  - All three relays per host (28701, 28702, 28703) now survive a reboot.
- **Preflight fix** (release `6b4fa4b0`). `demo-preflight.py` and
  `observe-fleet.py` check the new unit name; nothing else changed. Both outputs
  are in [observed/][observed].
- **Pull requests** ([triage table][triage]): #129 `8acb5f4c` exact
  `pft_to_atoms` scaling, #130 `8f9e0297` reused WebSocket request id refused,
  #131 `b18e4e02` test-only fixture root, #132 `4433ce5a` strict NavSwap on/off
  settings.
- **A666 issuer update.** Prepared, not yet signed:
  [`observed/a666-bridge-policy-update.unsigned.json`][update], sha256
  `24aa2e28…`.
- **CI on `main`.** I read `gh run list --branch main --limit 20` once at 10:58Z
  (seven commits, `2737f080` to `f17e09ea`): the seven `docs-build` runs passed,
  none failed, and the other 13 (`rust-ci` and `product-security-ci`) were still
  in progress.
- **Devnet touched today.** Only by the relay unit swaps: no validator or RPC
  restart, no transaction.
- **Task Node.** Two tasks were Rewarded today (2.9 PFT):
  - `task_1e10e30c…`: the migration command;
  - `task_8e0266ed…`: the review of #129–#132.

  This handoff has no Task Node action.

## Next decision or action

### My next steps, in order

1. The next release, cut when the next change set is ready; it carries
   `fastswap-committee-migrate`. On its release day:
   - the migration on the six validators, validator-5 first;
   - if the issuer update has been signed by then, the next Ethereum checkpoint
     5 of 6 with validator-5.
2. New bot pull requests, and [#95][pr95]/[#103][pr103] as their authors answer,
   with the same full-read standard.
3. The drafts [#127][pr127]/[#128][pr128] when their author marks them ready.

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
- **(g)** Validator-5:
  - one issuer-key signature and the submission of the prepared A666 bridge
    policy update ([file][update], sha256 above); the expected receipt is
    `route_bridge_policy_updated`;
  - the same update for the BMNRC route, from its issuer.

  First asked 2026-09-25 / 2026-10-01.
- **(h)** The height-915 archive and the height-924 custodian. 2026-08-30.
- **(i)** The AI-governance decision for Gate Zero Z2. 2026-09-03.
- **(j)** The inventory rows SCT-10 and PI-16 ([inventory][inventory]).
  2026-09-10.
- **(k)** The `ETHEREUM_MAINNET_RPC_URL` repository secret. 2026-09-28.
- **(l)** Permission to delete the other lane's old caches on the work server
  (~200 GB). 2026-10-01.
- **(m)** FW-13. 2026-09-30.

## References

- My [2026-10-15 handoff][previous]; the other lane's
  [2026-10-01 handoff][nazgul].
- Commits: `main` `2737f080`, `abc9cdef`, `f17e09ea`; release `e8132e5c`,
  `6b4fa4b0`.
- [FastPay committee recovery runbook][runbook]; [next release plan][next].
- Release packet on `release/fastlane-cap-20261014`: [README][packet],
  [observed/][observed].
- [Current State][state].

[nazgul]: 2026-10-01___nazgul__navcoin_create_and_swap_build_phase0_and_bmnrc_opening.md
[previous]: 2026-10-15___dravlic__fastlane_cap_release_deployed_and_bridge_committee_activated.md
[state]: ../status/chain-state-current.md
[runbook]: ../runbooks/fastpay-committee-recovery.md#moving-the-fastswap-store-to-the-activated-committee-epoch
[next]: ../plans/active/next-validator-release-plan-20261101.md
[already]: ../plans/active/next-validator-release-plan-20261101.md#already-on-main-past-the-cut
[triage]: ../plans/active/next-validator-release-plan-20261101.md#contributor-pull-requests-triaged-2026-10-12
[inventory]: ../review/defect-inventory-20260910.md
[near]: ../specs/near-intents-architecture-research-20260929.md
[z3]: ../status/z3-cycle1-inputs-20260922.md
[packet]: https://github.com/postfiatorg/postfiatl1v2/blob/6b4fa4b0596fecbdad663d9cddf902ae7b56d8b7/deployments/fastlane-cap-20261014/README.md
[releaseid]: https://github.com/postfiatorg/postfiatl1v2/blob/6b4fa4b0596fecbdad663d9cddf902ae7b56d8b7/deployments/fastlane-cap-20261014/RELEASE-ID.txt
[observed]: https://github.com/postfiatorg/postfiatl1v2/tree/6b4fa4b0596fecbdad663d9cddf902ae7b56d8b7/deployments/fastlane-cap-20261014/observed
[preflight]: https://github.com/postfiatorg/postfiatl1v2/blob/6b4fa4b0596fecbdad663d9cddf902ae7b56d8b7/deployments/fastlane-cap-20261014/observed/demo-preflight-20261016.json
[observe]: https://github.com/postfiatorg/postfiatl1v2/blob/6b4fa4b0596fecbdad663d9cddf902ae7b56d8b7/deployments/fastlane-cap-20261014/observed/observe-fleet-20261016.json
[relays]: https://github.com/postfiatorg/postfiatl1v2/blob/6b4fa4b0596fecbdad663d9cddf902ae7b56d8b7/deployments/fastlane-cap-20261014/observed/ethereum-relays-20261016.json
[update]: https://github.com/postfiatorg/postfiatl1v2/blob/6b4fa4b0596fecbdad663d9cddf902ae7b56d8b7/deployments/fastlane-cap-20261014/observed/a666-bridge-policy-update.unsigned.json
[pr49]: https://github.com/postfiatorg/postfiatl1v2/pull/49
[pr95]: https://github.com/postfiatorg/postfiatl1v2/pull/95#issuecomment-6167713335
[pr103]: https://github.com/postfiatorg/postfiatl1v2/pull/103#issuecomment-6167713654
[pr127]: https://github.com/postfiatorg/postfiatl1v2/pull/127
[pr128]: https://github.com/postfiatorg/postfiatl1v2/pull/128
