# Fleet recorded, relay default, WB-11 repaired and demo readiness

- **Operator:** Domagoj Ravlić (`dravlic`)
- **Date:** 2026-10-01 UTC
- **Responding to:** [the other lane's handoff][nazgul], 2026-09-30 17:00 to
  2026-10-01 03:35 UTC.

## BLUF

Today I worked on the platform your demos run on, while your lane kept working
on the validator hosts. Six watchdog user units on the validator-3 host started
as late as 09:53–09:55Z. By 10:32Z the chain was at 1085, seven blocks past your
handoff's 1078: two more A666 route Trades and one redemption, all signed by
`pfab9b92…`. I changed nothing on any host; every fleet action was a read.
Delivered:

1. The fleet state, verified and recorded (`dc734563`).
2. The checkpoint scripts default to the working Ethereum relay (`08de8187`).
3. WB-11: the burn id is confirmed against the live burn in block 1071, and a
   real bug in its file shape is repaired (StakeHub `306e791`, `34aa078`).
4. The status field `deployment_manifest_verified`, repaired for the next
   release (`1bb15a78`).
5. Two contributor pull requests merged (#51 `dc7d9bb6`, #48 `0609cb01`), and
   #52 reviewed with a comment: draft #47 is the correct fix.
6. A one-page [decision proposal][v5] on validator-5 and the two signer
   committees (`aa237a08`).
7. A demo-day preflight command and a [readiness note][ready] for the
   conference week (`56561e47`, `2e142ae7`). The preflight ran READY WITH
   ATTENTION: 55 PASS, 5 ATTENTION (all for the hand-started relays), 0 FAIL.
8. The work server's disk was 100 % full this morning (4.2 GB free of 601 GB).
   It has 94 GB free after I removed my own superseded qualification caches.

## Current state

### Fleet

- **Read-only observation at 10:32:42Z.** All six at height 1085, tip
  `b2c7f04e…`, root `b60665e9…`, source `c93b2137`. Validator PIDs are
  unchanged since 2026-09-28. Record: [Current State, 2026-10-01][fleet]
  (`dc734563`).
- **Three RPC accept-budget restarts.** Validator-0 at 07:40:35Z, validator-5
  at 08:28:25Z, then validator-2 at 11:40:39Z. Each was a clean exit, restarted
  5 s later by `Restart=always` on the same executable.
  - The path: the unit passes `--max-requests 10000`
    ([`batch_snapshot.rs:2403`][bs2403]); the accept loop stops at that count
    ([`rpc_serve_runtime.rs:105`][rs105], [`rpc_cli.rs:608`][rc608]); the
    command prints its report and returns 0 ([`group_03.rs:457`][g457]).
  - Confirmed from validator-0's `rpc-stdout.log` end-of-run report:
    `max_requests` 10000, `request_count` 129838. The budget counts
    connections, and one connection carries several requests. Recorded in the
    [readiness note][fragile]; the Current State section, written before that
    read, still calls the cause unverified.
- **Validator-2's transport event log** last wrote at 04:31:38Z. The 09:25:33Z
  write on the other five was a transport `health_request` probe, not a block.
  Validator-2 agrees at 1085.
- **Blocks 1079–1085**, route `pftl-a666-ethereum-wA666-usdc-v1`, account
  `pfab9b92…` sequences 230–236: `pftl_uniswap_order_reserve`,
  `primary_subscribe_v2` and `order_release` at 1079–1081 and 1083–1085, and
  `pftl_uniswap_primary_redeem` at 1082. That is your continued work.
- **Your ce22 h1033 replay** is recorded under the [block-1011 note][m1011].

### Ethereum relays on the validator hosts

- **28703** (`navcoin-ethereum-archive-rpc-20260907.service`, dRPC) is the
  only relay that answers archive `eth_getCode` (HTTP 200 at block 26094220).
- **28701** (PublicNode) returns HTTP 403, "Archive requests require a personal
  token".
- **28701 and 28702** are hand-started python processes from
  `/tmp/a666-https-jsonrpc-loopback-proxy.py`, a file that no longer exists on
  any host. On validator-1, 28701 is a unit and 28702 is absent. They vanish on
  a reboot.
- **`08de8187`:** `scripts/a666-mainnet-return-import.sh` and
  `scripts/a666-mainnet-record-destination-consume.sh` default
  `A666_VALIDATOR_ETHEREUM_RPC` to `http://127.0.0.1:28703`. Documented in
  [PFTL tools][relays].
- **Not done:** the host change (systemd units for 28701 and 28702, no
  validator restart, about 20 minutes). Your lane was active on those hosts all
  day, and I do not work on the same machines at the same time. It is proposed
  below.

### Checkpoint signing and watchdogs

- Validators 0–4 each have two new records today under
  `/var/lib/postfiat/validator-N/ethereum-checkpoint-signing/` (your export
  and return). Validator-5 has none.
- Your watchdog user units are untouched:
  - validator-0 host: `navcoin-proof-watchdog@normal`, since 2026-09-30
    22:21Z;
  - validator-3 host: ten `navcoin-proof-watchdog@` units, six of them started
    09:53–09:55Z today.

### WB-11 (StakeHub)

- **The live burn** in block 1071: `vault_bridge_burn_to_redeem`, 1,000,000
  atoms, epoch 53, by `pfab9b92…`, settled at 1072 as redemption `aa4168d6…`.
  Node id, redemption `burn_tx_id` and wallet-derived id are the same:
  `deb4dab7dd95b560422a587984955f8cfbcb8fe8ddbbed8be0d5269551ac8c2b7d9143bb4f520000287be678f0dfd1af`.
- **The bug.** `signed_burn_tx_id()` ([`mainnet_bridge.py:776`][sh776] at
  `306e791`) expected a nested `unsigned.operation` object. The real signer,
  `postfiat-rpc-sdk-a3b95b23`, and the node write the flat form.
  - A resume after a crash between signing and recording the burn stopped with
    `AttributeError`. There was no double-burn risk, but the withdrawal could
    not finish on its own.
  - The tests passed because the fake signer wrote the nested form.
- **Repaired in `34aa078`:** both shapes give the same id.
  - The id is SHA3-384 over a typed preimage ([`tx_hashing.rs:20-24`][th];
    [`transactions_mempool_receipts.rs:4177-4186`][t4177], [`:4123-4139`][t4123],
    [`:3929-3930`][t3929], [`:2077-2090`][t2077]).
  - The JSON shape comes only from serde `tag` and `flatten`
    ([`:3441`][t3441], [`:4079-4080`][t4079]).
- **Tests:** fixture [`tests/fixtures/pfusdc_burn_block_1071.signed.json`][fix].
  Five of the new tests fail on `306e791` and pass on `34aa078`.
  `tests/test_pft_mainnet_bridge.py`: 45 passed. Wallet suite: 210 passed.
- **Records:** [`wallet-bridge-review-20260924.md`][wbr] (WB-11 repaired
  2026-10-01) and [`live-funds-readiness-20260929.md`][lfr]: item 1 is
  confirmed; item 2, the unattended hold, stays until one live withdrawal goes
  through this wallet.

### `deployment_manifest_verified` (`1bb15a78` on `main`, not deployed)

- **What changed.** `postfiat-node deployment-manifest-verify` deletes any old
  record first. After a successful check, it writes a verification record
  (manifest SHA-256, deployment id, publisher, verified-at, validity window) to
  `POSTFIAT_DEPLOYMENT_VERIFIED_RECORD`.
- **What `status` reports.** `true` only when the record matches the current
  manifest's hash, deployment id, publisher and window, and the time is inside
  the window. A missing, stale, wrong-schema or unreadable record keeps
  `false` and never fails `status`. The record itself is not signed.
- **Env files.** The release generator writes the variable into new env files:
  `<data-dir>/readiness/rpc.deployment-verified.json` and
  `transport.deployment-verified.json`.
- **Why not in-process.** A signature check inside `status` was impossible:
  the env has no publisher key, and the manifest's own key would vouch for
  itself.
- **Files**, at `1bb15a78`:
  - `crates/node/src/lifecycle_queries.rs` [192-194][lq192], [880-893][lq880],
    [1039-1091][lq1039];
  - `batch_snapshot.rs` [2553-2564][bs2553], [2974-3014][bs2974];
  - `main_parts/cli_dispatch_parts/group_05.rs` [3075-3091][g5];
  - `main_parts/cli_dispatch.rs` [141][cd141];
  - `node_types_snapshot_deployment.rs` [122-134][nt122];
  - `tests/snapshot_deployment.rs` [33-215][sd33];
  - [Current State][state45] lines 45-73;
    [signed-deployment-manifest runbook][runbook] lines 147-150 and 173-178.
- **Tests:** `deployment_status_reports_signature_verified_manifest` fails
  before and passes after; `deployment_status_rejects_stale_or_missing_verification_record`
  (four cases); `snapshot_deployment` 18/18; clippy `-D warnings` clean.
- **Fleet:** on `c93b2137` it reports `false` until the next release.

### Contributor pull requests

- **[#51][pr51]** (0xzoz, devnet node helper run path), merged as `dc7d9bb6`.
  Scripts only. `bash -n` on 9 scripts; `scripts/node-helper-smoke` exit 0;
  guard cases exit 2.
- **[#48][pr48]** (white-guy-01, fresh-host monitor snapshot smoke), merged as
  `0609cb01`. Operator tooling plus one Apple-only line in
  `crates/node/src/storage_migration.rs`. Python tests 5/5; clippy clean; the
  smoke exits 0 on ports moved off the 27650 tunnels. Not covered: the other
  smokes that use the harness #48 changed, and the macOS line.
- **[#52][pr52]** (JJ2203-theRealOne, relative data directories), left open
  with a [review comment][pr52r]. It fixes the default case only; an explicit
  relative `--spool-dir` still fails. Draft [#47][pr47] (citadelculture) is the
  correct fix: both probes return `ok=true` when it is built. #52's end-to-end
  test could be added on top of it.

### Validator-5 decision proposal (`aa237a08`)

- [`docs/review/validator-5-signer-committees-decision-proposal-20261001.md`][v5].
- Both signer groups are 5-of-5 over validators 0–4: FastPay quorum 5 per the
  [r4 handoff][r4], and bridge `certificate_quorum` 5 per
  [`rollout-record.json`][rollout]. One of validators 0–4 down stops payments
  and Ethereum transfers.
- Options: **A**, both committees to six members with quorum 5 (my lean, after
  the conference); **B**, bridge only; **C**, leave as is.
- Marked as inferred: an Ethereum-side contract update, which key signs the
  FastPay committee record, and the effort ranges.

### Demo-day readiness (`56561e47`, `2e142ae7`)

- **The command:**
  [`deployments/combined-fastpay-20260928/demo-preflight.py`][preflight],
  documented in that folder's [README][readme].
  - Read-only, standard library only.
  - Checks ledger agreement, release and manifest, mempool, unit state with
    uptime and restart counts, the relay 28703 archive read, how 28701 and
    28702 were started, checkpoint key presence and record counts, RPC
    readiness flags, disk (10 GB threshold), the two logrotate rules and
    `apt-daily-upgrade`.
  - `--json`, and an optional `--wallet-url` that I did not point at your
    wallet.
- **The note:** [`docs/status/demo-readiness-20261001.md`][ready], with Solid,
  Fragile and Before the event sections and the table from the 12:05:53Z run.
  - READY WITH ATTENTION: 55 PASS, 0 FAIL, and 5 ATTENTION, one for the
    hand-started relays on each of validators 0 and 2–5. A rerun at 12:10:56Z
    gave the same result.
  - It proposes the one hardening step that needs your window: relay units on
    validators 0 and 2–5, plus 28702 on validator-1, with no validator
    restart.
  - The rule: run the preflight before each demo. Go on READY, or on
    ATTENTION caused only by the relays. Stop on FAIL.

### Work server disk

- **At 10:30Z:** 4.2 GB free of 601 GB. The large users were `~/repos` (297
  GB), `~/.cache` (178 GB) and `~/.postfiat/deployments` (63 GB).
- **Removed by me after inspection** (nothing running there, no backup or
  canary files):
  - `~/.cache/release-repair-20260918` (45 GB) and `release-repair-20260922`
    (24 GB);
  - `~/.cache/qualify-fix-20260918` and `qualify-fix-20260922` (2.4 GB each);
  - the `target/` folders of the worktrees `postfiatl1v2-dravlic` (16 GB) and
    `postfiatl1v2-e1` (2.6 GB), then `git worktree prune`.
- **Now:** 94 GB free (`df -h`, 12:22Z).
- **Kept:** `release-repair-20260925` and `release-repair-20260928` (canary
  backups of the deployed releases), `release-repair-20260916` and `deploy-*`.
- **Not touched, yours:**
  - `~/.cache/combined-release-20260915` (42 GB) and
    `signing-fix-qualification-20260909` (18 GB);
  - `~/repos/postfiatl1v2-arcusdc-current` (64 GB, idle since 09-01);
  - `~/repos/postfiat-storage-g4-measurement-ae6ec9cb-d0ae79f3-v1` (39 GB),
    `postfiat-batched-index-candidate-48a94425` (17 GB) and
    `postfiat-storage-g4-4f976290-ae658441` (17 GB).

### On your handoff

- **The ~$10k `xyz:GOOGL` long / `xyz:AAPL` short pair** opened at 20:45Z on
  2026-09-30 was not placed by me. My day ended at 12:58Z, and no process on
  the work server trades.
- **FW-04 and FW-09 notes:** read.
- **The three P3 items** (FW-13, FW-14, PT-08) stay yours.
- **The watchdog units** were left running.
- **Validator-5's bridge committee question** is answered by the
  [proposal][v5].
- **GitHub Dependabot alert #2** (medium, `postcss` in
  `wallet-web/package-lock.json`, fixed in 8.5.23) was not touched, because
  `wallet-web` is your active B0.1 area.

### Fleet and repository boundary

- **Last observed fleet state:** 10:32:42Z, recorded in [Current State][fleet].
  The 12:05:53Z preflight saw the same height, tip and root.
- **Deployed:** release `combined-fastpay-20260928`, executable `1f8b332d…`,
  source `c93b2137` on `release/combined-fastpay-20260928` (branch at
  `7869a707`, unchanged today).
- **Repository:** `main` at `2e142ae7` before this handoff. StakeHub `master`
  at `34aa078`.
- **Merged but undeployed node code:** `1bb15a78`, and #48's Apple-only line.
- **Live actions:** reads only. Status, journal, log, relay and block reads on
  the six hosts, and the preflight runs. While writing this handoff, I re-read
  the redemption with one `vault_bridge_status` call on validator-0's RPC and
  read the tails of the transport event logs on validators 0 and 2 (about
  12:20Z). No transaction, restart or configuration change. Otherwise the
  devnet was not touched.
- **CI on `main`, read at 12:24Z:** no failed run. `docs-build` is green on
  every commit today. `rust-ci` and `product-security-ci` are green on
  `08de8187` and still running on most later commits.

### Task Node

Four tasks today, all Rewarded, 6.8 PFT in total:

| Task | Scope | Reward |
| --- | --- | ---: |
| `task_3b681e43b39b55ebf350cc6f4a495299` | WB-11 | 2 PFT |
| `task_78a4bbf0ff094e2769abede544ea60e9` | `deployment_manifest_verified` | 1.7 PFT |
| `task_b74ed6d4909827bb477332f1c616ba69` | Contributor pull requests | 1.5 PFT |
| `task_f528cc9567504aaa2a871f4d96bdd8af` | Demo-day readiness | 1.6 PFT |

This handoff has no Task Node task.

## Next decision or action

### My next steps, in order

1. **Relay units.** Turn the hand-started relays 28701 and 28702 on the six
   validator hosts into systemd units (same upstreams, `--attempts 3`). About
   20 minutes, no validator restart, with before and after reads and a
   rollback note. Only in a window when your agents are not on those hosts;
   you name the moment.
2. **Specification review.** Check the platform statements of the NAVCoin
   specification (§3, §8.1–8.5 and §9.1 of
   [`docs/navcoins/navcoin-create-and-swap-spec.md`][spec]) against
   `c93b2137`, as a condition / observed / expected table. Not started today.
3. **If you answer A or B on validator-5:** prepare the unsigned committee
   transactions and a six-validator fork dry run.
4. **After your next live runs:** re-read the event logs; check the first live
   shield step against the batch-bound check; run the demo preflight before
   each demo day.
5. **Waiting:** the `deployment_manifest_verified` change ships with the next
   release (regenerated env files). PR #52 waits for #47.

### Only you can provide

Each item is listed with the date it was first asked. I asked for each again
today.

- **(a)** The two NEAR Intents design questions ([note][near]). 2026-09-29.
- **(b)** NAVCoin signer keys and custody, rows 4, 8, 11, 12, 13, 16 and 17
  ([`z3-cycle1-inputs-20260922.md`][z3]). 2026-09-22.
- **(c)** The Arc route step: route epoch 11 or more, a custody row for the
  Arc source, and the A666 issuer key. 2026-09-28.
- **(d)** A compatible governed NAV profile with fresh proofs. 2026-09-22.
- **(e)** StakeHub custody Q1 and archive Q2 ([proposal][custody]).
  2026-09-07.
- **(f)** Reserve-proof successor adoption, yes or no ([PR #49][pr49]).
  2026-09-24.
- **(g)** FastPay committee rotation for validator-5, now part of (n).
  2026-09-25.
- **(h)** The height-915 archive and the height-924 custodian. 2026-08-30.
- **(i)** The AI-governance decision for Gate Zero Z2. 2026-09-03.
- **(j)** Twelve inventory rows ([`defect-inventory-20260910.md`][inventory]).
  2026-09-10.
- **(k)** Disk items on the validators: the September 5–7 dumps, `gate931`,
  `gate926`, the three unknown-origin snapshot entries and the five `.zst`
  archives ([inventory][disk]). 2026-09-28.
- **(l)** The `ETHEREUM_MAINNET_RPC_URL` repository secret ([note][ci]).
  2026-09-28.
- **(m)** The cap values. 2026-09-29.
- **(n) New:** one letter, A, B or C, on the [validator-5 proposal][v5].
  2026-10-01.
- **(o) New:** permission to delete your old caches on the work server listed
  above (~200 GB). 2026-10-01.
- **(p) New:** a 20-minute window for the relay units on the six hosts.
  2026-10-01.
- **(q)** The three skipped P3 items FW-13, FW-14 and PT-08. 2026-09-30.

## References

- [The other lane's handoff][nazgul].
- My previous handoff: [2026-09-30][previous].
- Commits on `main`: `dc734563`, `08de8187`, `1bb15a78`, `dc7d9bb6`,
  `0609cb01`, `aa237a08`, `56561e47`, `2e142ae7`.
- [`deployments/combined-fastpay-20260928/demo-preflight.py`][preflight] and
  [`docs/status/demo-readiness-20261001.md`][ready].
- StakeHub `306e791` and `34aa078` on `master`;
  [`docs/review/wallet-bridge-review-20260924.md`][wbr] and
  [`docs/review/live-funds-readiness-20260929.md`][lfr].
- [`docs/status/chain-state-current.md`][fleet].
- [`docs/navcoins/pftl-tools.md`][relays].
- [`docs/review/validator-5-signer-committees-decision-proposal-20261001.md`][v5].
- [PR #52 review comment][pr52r].

[nazgul]: 2026-10-01___nazgul__navcoin_create_and_swap_build_phase0_and_bmnrc_opening.md
[previous]: 2026-09-30___dravlic__fastpay_resume_repaired_wallet_caps_and_log_checks.md
[r4]: 2026-09-25___postfiatchad__r4_view_recovery_chain_unstuck.md
[fleet]: ../status/chain-state-current.md#2026-10-01-fleet-after-the-other-lanes-navcoin-operator-tests
[state45]: ../status/chain-state-current.md#why-status-reports-deployment_manifest_verifiedfalse
[m1011]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/status/combined-fastpay-merge-20260925.md#why-the-lines-diverged
[ready]: ../status/demo-readiness-20261001.md
[fragile]: ../status/demo-readiness-20261001.md#fragile
[relays]: ../navcoins/pftl-tools.md#ethereum-relays-on-the-validator-hosts
[v5]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/review/validator-5-signer-committees-decision-proposal-20261001.md
[runbook]: ../runbooks/signed-deployment-manifest.md
[spec]: ../navcoins/navcoin-create-and-swap-spec.md
[preflight]: https://github.com/postfiatorg/postfiatl1v2/blob/56561e47b29364ed89e1a319f90cb5386c1fc8a9/deployments/combined-fastpay-20260928/demo-preflight.py
[readme]: https://github.com/postfiatorg/postfiatl1v2/blob/56561e47b29364ed89e1a319f90cb5386c1fc8a9/deployments/combined-fastpay-20260928/README.md#demo-preflight
[rollout]: https://github.com/postfiatorg/postfiatl1v2/blob/release/combined-fastpay-20260928/deployments/combined-fastpay-20260928/observed/rollout-record.json
[bs2403]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/node/src/batch_snapshot.rs#L2403
[rs105]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/node/src/rpc_serve_runtime.rs#L105
[rc608]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/node/src/rpc_cli.rs#L608
[g457]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/node/src/main_parts/cli_dispatch_parts/group_03.rs#L457
[th]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/tx_hashing.rs#L20-L24
[t4177]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/types/src/transactions_mempool_receipts.rs#L4177-L4186
[t4123]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/types/src/transactions_mempool_receipts.rs#L4123-L4139
[t3929]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/types/src/transactions_mempool_receipts.rs#L3929-L3930
[t2077]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/types/src/transactions_mempool_receipts.rs#L2077-L2090
[t3441]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/types/src/transactions_mempool_receipts.rs#L3441
[t4079]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/types/src/transactions_mempool_receipts.rs#L4079-L4080
[lq192]: https://github.com/postfiatorg/postfiatl1v2/blob/1bb15a78b50f296443f0c97e50c836dce977565e/crates/node/src/lifecycle_queries.rs#L192-L194
[lq880]: https://github.com/postfiatorg/postfiatl1v2/blob/1bb15a78b50f296443f0c97e50c836dce977565e/crates/node/src/lifecycle_queries.rs#L880-L893
[lq1039]: https://github.com/postfiatorg/postfiatl1v2/blob/1bb15a78b50f296443f0c97e50c836dce977565e/crates/node/src/lifecycle_queries.rs#L1039-L1091
[bs2553]: https://github.com/postfiatorg/postfiatl1v2/blob/1bb15a78b50f296443f0c97e50c836dce977565e/crates/node/src/batch_snapshot.rs#L2553-L2564
[bs2974]: https://github.com/postfiatorg/postfiatl1v2/blob/1bb15a78b50f296443f0c97e50c836dce977565e/crates/node/src/batch_snapshot.rs#L2974-L3014
[g5]: https://github.com/postfiatorg/postfiatl1v2/blob/1bb15a78b50f296443f0c97e50c836dce977565e/crates/node/src/main_parts/cli_dispatch_parts/group_05.rs#L3075-L3091
[cd141]: https://github.com/postfiatorg/postfiatl1v2/blob/1bb15a78b50f296443f0c97e50c836dce977565e/crates/node/src/main_parts/cli_dispatch.rs#L141
[nt122]: https://github.com/postfiatorg/postfiatl1v2/blob/1bb15a78b50f296443f0c97e50c836dce977565e/crates/node/src/node_types_snapshot_deployment.rs#L122-L134
[sd33]: https://github.com/postfiatorg/postfiatl1v2/blob/1bb15a78b50f296443f0c97e50c836dce977565e/crates/node/src/tests/snapshot_deployment.rs#L33-L215
[sh776]: https://github.com/postfiatorg/StakeHub/blob/306e791a3afde290860eea60ca74cec7faa9ba62/pft_wallet/mainnet_bridge.py#L776
[fix]: https://github.com/postfiatorg/StakeHub/blob/34aa078ac8caa37f03a325c87e1784265cdde9e0/tests/fixtures/pfusdc_burn_block_1071.signed.json
[wbr]: https://github.com/postfiatorg/StakeHub/blob/master/docs/review/wallet-bridge-review-20260924.md
[lfr]: https://github.com/postfiatorg/StakeHub/blob/master/docs/review/live-funds-readiness-20260929.md
[custody]: https://github.com/postfiatorg/StakeHub/blob/master/docs/review/custody-and-archive-decision-proposal-20260923.md
[pr47]: https://github.com/postfiatorg/postfiatl1v2/pull/47
[pr48]: https://github.com/postfiatorg/postfiatl1v2/pull/48
[pr49]: https://github.com/postfiatorg/postfiatl1v2/pull/49
[pr51]: https://github.com/postfiatorg/postfiatl1v2/pull/51
[pr52]: https://github.com/postfiatorg/postfiatl1v2/pull/52
[pr52r]: https://github.com/postfiatorg/postfiatl1v2/pull/52#pullrequestreview-5378762269
[near]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/specs/near-intents-architecture-research-20260929.md
[z3]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/status/z3-cycle1-inputs-20260922.md
[inventory]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/review/defect-inventory-20260910.md
[ci]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/status/main-ci-red-20260928.md
[disk]: https://github.com/postfiatorg/postfiatl1v2/blob/release/combined-fastpay-20260925/deployments/combined-fastpay-20260925/observed/disk-inventory-20260928.json
