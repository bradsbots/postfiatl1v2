# Signer groups half switched and size cap fixed

- **Operator:** Domagoj Ravlić (`dravlic`)
- **Date:** 2026-10-12 UTC
- **Responding to:** no handoff from the other lane since
  [its 2026-10-01 handoff][nazgul]. My previous handoff: [2026-10-09][previous].

## BLUF

The follow-ups of release `signer-rotation-20261007` ran today. The FastSwap
store is converted on all six validators ([sheet §7][sheet7]). The signer-group
activation ([sheet §8][sheet8]) is half done: the FastPay epoch-2 committee with
validator-5's current key is installed at height 1123. The bridge half stopped
at §8.2, after the `StopPrepare` at height 1122: the RPC refused the
70,944-byte `AnchorCheckpoint` (64 KiB cap). Nothing was admitted at §8.2, so no
issuer update exists yet. The fix is on `main` for the next release
(`7f9d0d98`). I also recorded the technical decisions that had waited on the
other lane (`69d7a108`) and triaged the 49 bradsbots pull requests
(`80df43cf`); nothing merged. Fleet record: [Current State][state].

## Current state

- **Fleet.** `observe-fleet.py`, read-only, at 10:11Z, 11:14Z and 12:06Z.
  Last read 12:06Z: all six on `signer-rotation-20261007` (`decaa411…`,
  manifest `fa4649aa…`, source `0fa55d0b`), height 1123, tip `bafcc6ef4acc…`,
  root `942d1fc2b663…`, mempools empty, 12 units active, 16–27 GB free per
  host. Records: [store-conversion/][conv] and [signer-activation/][act] on the
  release branch; [Current State][state] (2026-10-12 section). No live probe
  while writing this handoff.
- **FastSwap store conversion** ([sheet §7][sheet7]; release `aa75b099`, `main`
  `3fea3fc7`). One host at a time, validator-5 first, 10:57–11:13Z. Every host
  converted 26 of 26 records; backups kept at
  `/var/lib/postfiat/fastswap-v1-backup-validator-N`; six-way agreement before
  and after each host. The sheet's backup command needed a pre-created backup
  directory (the parent is root-owned); the sheet is corrected, and this commit
  adds the same note to step 3 of the [runbook][runbook-conv]. Validator-5
  still answers `fastswap_unavailable` until the bridge committee changes.
- **Signer-group activation** ([sheet §8][sheet8], [record][record]; release
  `6675d1d6`, `main` `51856c5f`).
  - FastPay half complete: the epoch-2 committee (six members with validator-5's
    current key, quorum 5, valid 10001–19990, registry root `86125482…`) was
    signed by all six at slot 1123 and installed at height 1123 (block
    `bafcc6ef…`, certificate `b2f5c70c…`, `fastpay_recovery_committee_rotated`
    on all six). Payments are unchanged until 10001.
  - §8.0, read-only, passed: 0 outstanding claims and returns on the A666 and
    BMNRC routes; one FastSwap policy `356e5cca…` at policy epoch 1; committee
    epoch 1, root `a2eebcba…`; the epoch-2 committee root
    `72836827f9f3ecd3042261a77abff72235f0238b6a81f673630a62199415021a1be0cbd5451878edca0e110434c1da37`
    computed identically on all six ([committee][committee]).
  - §8.1 `StopPrepare` admitted at height 1122 (tx `fbafffe4…`,
    `fastlane_control_applied` on all six).
  - §8.2 `AnchorCheckpoint` refused by the RPC parameter check:
    `fastlane_primary_json` is capped at 65,536 bytes and the five-vote
    checkpoint is 70,944 bytes, five ML-DSA-65 signatures as JSON number arrays
    ([transaction][anchor]). Nothing admitted; §8.3 and §8.4 did not run; no
    issuer update exists.
  - The fence until the next release ([sheet §8 notes][sheet8-after]): new
    FastSwap prepares under policy epoch 1 and bridge policy updates aimed at
    committee epoch 1 are stopped. Ethereum route checkpoints, A666/pfUSDC
    deposits and returns, the NAVCoin proof watchdogs and the faucet are
    unaffected; the epoch-1 bridge committee keeps signing. The last FastSwap
    use was in July.
  - Why I did not force the live path: the local CLI path
    (`mempool_submit_fastlane_primary` plus
    `transport-peer-certified-mempool-round`) is unreviewed and races
    `rpc-serve`'s in-process lock, and the `ActivateCommittee` certificate
    (~176 KB) would exceed the argv limit anyway (my journal;
    [sheet §8 note][sheet8-resume]).
- **Size-cap fix on `main`, undeployed** (`7f9d0d98`).
  - A separate 256 KiB cap for `fastlane_primary_json`
    (`MAX_RPC_FASTLANE_PRIMARY_JSON_BYTES`,
    `crates/rpc_sdk/src/protocol_requests.rs`). Measured JSON/binary ratio
    3.60×, so the transactions stay under the untouched 128 KiB mempool limit.
  - The finality handler reports the receipt code of the operation submitted:
    `fastlane_checkpoint_anchored`, `fastlane_control_applied`,
    `owned_deposit_applied` (`crates/execution/src/fastlane_primary.rs`,
    `crates/node/src/rpc_dispatch.rs`).
  - `--fastlane-primary-file` (`crates/node/src/rpc_cli.rs`).
  - Three reproduce-first tests:
    `fastlane_primary_json_cap_admits_signer_rotation_control_transactions`
    (`crates/rpc_sdk/src/protocol_request_tests.rs`),
    `rpc_finality_reports_stop_prepare_as_success` and
    `rpc_finality_reports_five_vote_anchor_then_activate_committee_as_success`
    (`crates/node/src/fastswap_control_signing.rs`).
  - [Runbook section][runbook-submit]; §8.2–8.4 is an item of the
    [next release plan][next-rollout].
- **Decisions taken** (`69d7a108`).
  - [Inventory][inventory]: SQ-02 Closed (deployed `0fa55d0b` is in main's
    ancestry; `pftl_source_settlement.rs` is tracked). SQ-01 Decided (the
    two-clean-build identity gate of the release qualification is the
    toolchain contract; both builds of the last release produced
    `decaa411…`). SQ-06 Decided (the release process of 2026-09-25 and
    2026-10-09). SCT-08 Decided (the evidence campaign is authorized and listed
    in the [20261101 plan][next]). SCT-10 and PI-16 stay with the other lane.
    "Needs operator decision": 6 → 2.
  - NEAR Intents question 1 ([note][near], §2.7): the swap screen keeps the
    proof-based route; no intent-style flow before the first live cycle.
  - FW-14 ([plan][next]): the pool keeps its a651 shielded after each run, as
    the deployed release does.
  - Wallet cap values: the defaults installed on 2026-09-30 stand
    (`pft_run_atoms` 100 PFT; `run_usd` 5 / `campaign_usd` 50) until the other
    lane changes them in `~/.pft/config.toml` `[limits]`. Recorded here because
    the cap documents live in StakeHub.
  - The relay-units window is a technical host step that I run myself.
- **Contributor pull requests** (`80df43cf`; [triage table][triage]).
  bradsbots is an outside account, so GitHub held all 225 of its CI runs as
  `action_required` and no PR had a CI result.
  - I approved the 75 runs of the 25 class-A PRs (tooling, Python client, input
    validation, strict params: #57, 59, 64, 65, 66, 70, 71, 73, 74, 75, 78, 79,
    86, 87, 88, 89, 91, 92, 94, 96, 97, 100, 101, 102, 104) at their reviewed
    head SHAs. They merge with `gh pr merge --merge --match-head-commit` once
    green.
  - 16 need review (node behaviour, >400-line `rpc_sdk` diffs, wallet-proxy
    routing and env semantics, bridge timeouts: #56, 60, 61, 62, 63, 76, 77,
    80–85, 95, 99, 103).
  - 8 are blocked (#58 conflicts; #67, 68, 69, 72, 90, 93, 98 stacked).
  - Nothing merged today.
- **Deployment boundary.** Deployed source `0fa55d0b`. `main` at `80df43cf`
  before this handoff; release branch at `6675d1d6`. Merged but undeployed:
  `9d837bef` (PR #54), `51144786` (Python `account_tx` fallback), `7f9d0d98`
  (size cap and receipt codes), plus documentation.
- **Devnet touched today:** the store conversion on six hosts (units stopped
  and started, backups kept), the `StopPrepare` at height 1122, the FastPay
  committee record at height 1123. Evidence in the release packet.
- **Not done today:** the relay units on the six hosts; the §8.2–8.4
  submission (release day of the next release); the [plan's][plan-rollout]
  "Live checks" box (no `account_tx` truncation read was recorded on
  2026-10-09). The runbook's backup-directory note is written in this commit.
- **Task Node.** Rewarded: `task_d3b153b3…` (store conversion, 4.5 PFT),
  `task_b4e9493c…` (signer activation, 2.75 PFT), `task_d36054f1…` (size-cap
  fix), `task_53be1fd1…` (pull request triage, 2 PFT). This handoff has no
  Task Node action.
- **CI on `main`** (`gh run list`, read once at 13:00Z). `docs-build` passed on
  `7f9d0d98`, `69d7a108` and `80df43cf`. `7f9d0d98`: `product-security-ci`
  passed, `rust-ci` in progress. `69d7a108`: `rust-ci` and
  `product-security-ci` in progress. `80df43cf`: both queued.

## Next decision or action

### My next steps, in order

1. The relay units on the six hosts.
2. Review and merge of the triaged contributor pull requests as their CI turns
   green.
3. The next release: cut from `main` with `7f9d0d98`, qualify, deploy; then
   §8.2–8.4 on that release day (anchor, `ActivateCommittee`, and the unsigned
   issuer update prepared for the other lane).
4. The plan's "Live checks" box (an `account_tx` truncation read).

### Only the other lane can provide

I ask the other lane for the following; each shows the date first asked.

- **(a)** NEAR Intents question 2 only: listing a NAVCoin inside NEAR Intents
  as a distribution shelf ([note][near]). Question 1 is decided. 2026-09-29.
- **(b)** The NAVCoin signer keys and the cycle inputs ([inputs][z3]).
  2026-09-22.
- **(c)** The Arc source row on the A666 route; epoch 11 has the Ethereum
  source only. 2026-09-28.
- **(d)** A compatible governed NAV profile with fresh proofs. 2026-09-22.
- **(e)** StakeHub custody Q1. 2026-09-07.
- **(f)** The reserve-proof successor adoption and registration
  ([PR #49][pr49]). 2026-09-24.
- **(g)** Validator-5: the FastPay half is done. The issuer signature on the
  bridge policy update becomes possible only after the next release admits the
  `ActivateCommittee`; nothing to sign today. 2026-09-25 / 2026-10-01.
- **(h)** The height-915 archive and the height-924 custodian. 2026-08-30.
- **(i)** The AI-governance decision for Gate Zero Z2. 2026-09-03.
- **(j)** The inventory rows SCT-10 and PI-16 (independent operators; a paid
  independent audit) ([inventory][inventory]). 2026-09-10.
- **(k)** The `ETHEREUM_MAINNET_RPC_URL` repository secret. 2026-09-28.
- **(l)** Permission to delete the other lane's old caches on the work server
  (~200 GB). 2026-10-01.
- **(m)** FW-13: which passphrase unlocks the venue-inventory wallet.
  2026-09-30.

Decided by me today and no longer waiting: the relay-units window, the wallet
cap values (the installed defaults stand), FW-14, NEAR Intents question 1, and
the inventory rows SCT-08, SQ-01, SQ-02 and SQ-06.

## References

- My [2026-10-09 handoff][previous]; the other lane's
  [2026-10-01 handoff][nazgul].
- Release packet `deployments/signer-rotation-20261007/` on
  `release/signer-rotation-20261007` at `6675d1d6`: [DEPLOY-SHEET.md][sheet],
  [observed/store-conversion/][conv], [observed/signer-activation/][act],
  [signer-activation-record.json][record].
- `main` commits: `3fea3fc7`, `51856c5f`, `7f9d0d98`, `69d7a108`, `80df43cf`.
- [Validator-5 signer committees decision proposal][v5];
  [signer committee rotation dry run][dryrun] (six-validator fixtures, not live
  authority).
- [Current release plan][plan] and [next release plan][next].
- [Defect inventory][inventory]; [FastPay committee recovery runbook][runbook].
- [Current State][state].

[nazgul]: 2026-10-01___nazgul__navcoin_create_and_swap_build_phase0_and_bmnrc_opening.md
[previous]: 2026-10-09___dravlic__signer_rotation_release_deployed.md
[state]: ../status/chain-state-current.md
[plan]: ../plans/active/next-validator-release-plan-20261005.md
[plan-rollout]: ../plans/active/next-validator-release-plan-20261005.md#rollout
[next]: ../plans/active/next-validator-release-plan-20261101.md
[next-rollout]: ../plans/active/next-validator-release-plan-20261101.md#qualification-and-rollout
[triage]: ../plans/active/next-validator-release-plan-20261101.md#contributor-pull-requests-triaged-2026-10-12
[runbook]: ../runbooks/fastpay-committee-recovery.md
[runbook-conv]: ../runbooks/fastpay-committee-recovery.md#converting-the-fastswap-store-before-the-rotation
[runbook-submit]: ../runbooks/fastpay-committee-recovery.md#submitting-fastlane-control-transactions
[v5]: ../review/validator-5-signer-committees-decision-proposal-20261001.md
[dryrun]: ../review/signer-committee-rotation-dry-run-20261005.md
[inventory]: ../review/defect-inventory-20260910.md
[near]: ../specs/near-intents-architecture-research-20260929.md
[z3]: ../status/z3-cycle1-inputs-20260922.md
[sheet]: https://github.com/postfiatorg/postfiatl1v2/blob/6675d1d65aae155d86534ea7dcf5a7a086d18d03/deployments/signer-rotation-20261007/DEPLOY-SHEET.md
[sheet7]: https://github.com/postfiatorg/postfiatl1v2/blob/6675d1d65aae155d86534ea7dcf5a7a086d18d03/deployments/signer-rotation-20261007/DEPLOY-SHEET.md#L128-L188
[sheet8]: https://github.com/postfiatorg/postfiatl1v2/blob/6675d1d65aae155d86534ea7dcf5a7a086d18d03/deployments/signer-rotation-20261007/DEPLOY-SHEET.md#L190-L244
[sheet8-after]: https://github.com/postfiatorg/postfiatl1v2/blob/6675d1d65aae155d86534ea7dcf5a7a086d18d03/deployments/signer-rotation-20261007/DEPLOY-SHEET.md#L234-L237
[sheet8-resume]: https://github.com/postfiatorg/postfiatl1v2/blob/6675d1d65aae155d86534ea7dcf5a7a086d18d03/deployments/signer-rotation-20261007/DEPLOY-SHEET.md#L239-L244
[conv]: https://github.com/postfiatorg/postfiatl1v2/tree/6675d1d65aae155d86534ea7dcf5a7a086d18d03/deployments/signer-rotation-20261007/observed/store-conversion
[act]: https://github.com/postfiatorg/postfiatl1v2/tree/6675d1d65aae155d86534ea7dcf5a7a086d18d03/deployments/signer-rotation-20261007/observed/signer-activation
[record]: https://github.com/postfiatorg/postfiatl1v2/blob/6675d1d65aae155d86534ea7dcf5a7a086d18d03/deployments/signer-rotation-20261007/observed/signer-activation/signer-activation-record.json
[committee]: https://github.com/postfiatorg/postfiatl1v2/blob/6675d1d65aae155d86534ea7dcf5a7a086d18d03/deployments/signer-rotation-20261007/observed/signer-activation/epoch2-bridge-committee.json
[anchor]: https://github.com/postfiatorg/postfiatl1v2/blob/6675d1d65aae155d86534ea7dcf5a7a086d18d03/deployments/signer-rotation-20261007/observed/signer-activation/final-checkpoint-epoch1.fastlane-primary.json
[pr49]: https://github.com/postfiatorg/postfiatl1v2/pull/49
