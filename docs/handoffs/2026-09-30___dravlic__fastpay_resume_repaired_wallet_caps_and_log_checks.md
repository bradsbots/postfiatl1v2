# FastPay resume repaired, wallet caps and log checks

- **Operator:** Domagoj Ravlić (`dravlic`)
- **Date:** 2026-09-30 UTC

## BLUF

The other lane is travelling and left the evening to this lane's discretion. He
picks up in the morning. No commit, handoff or live funds from him have arrived
since 2026-09-29. I used the time to make his live end-to-end runs safer, in
four parts:

1. **FW-04 is repaired in the Python SDK.** `send_fastpay` now saves the signed
   order before it asks for votes, and saves the exact certificate before
   `owned_apply_v3`. A repeat call with the same `work_dir` re-applies that
   certificate, or records the input as spent, or refuses without signing
   again. Commit `0310e8b4`; [PR #53][pr53] merged as `efc58090`. The wallet on
   this server now loads a pinned copy of this SDK.
2. **FW-08 and the FW-09 spending caps** are merged in StakeHub as `23a45d9`
   ([PR #19][sh19], squash). The shield step now checks the receipts of its own
   batch. FastPay payments and PFT transfers have a new atom cap. The swap flows
   now reserve against the existing USD caps.
3. **The event logs are checked.** Two devnet faucet grants (heights 1063 and
   1064) confirmed that each validator's fresh transport event log receives
   events. A second logrotate rule, for `rpc-events.ndjson`, is installed on
   all six validators. Nothing was restarted.
4. **28 of the 31 recorded P3 findings are repaired** on StakeHub
   [PR #20][sh20]. The other 3 are the other lane's custody or release
   decisions, and I skipped them. PR #20 is not merged at the time of writing:
   its full-suite run started at 11:56Z.

The last observed chain state is 2026-09-30T11:09Z: height 1064, identical on
all six validators, all on `combined-fastpay-20260928`
([Current State][state]).

## Current state

### FW-04: the FastPay send can now be resumed (postfiatl1v2)

- **Commit:** `0310e8b4` on `fix/fastpay-certificate-persist-20260930`.
  [PR #53][pr53] was merged to `main` as `efc58090`.
- **Files:**
  - [`python/postfiat_rpc/wallet.py`][w1063]
  - `python/tests/test_wallet.py`
  - `docs/python/client-api.md`
  - `docs/python/wallet-functions.md`
- **What changed in `send_fastpay`** ([`wallet.py:1063`][w1063]):
  - **Journal.** With a caller-owned `work_dir`, it writes a journal named
    `fastpay-send-*.json` (schema `postfiat-fastpay-send-journal-v1`). The name
    is set by `_fastpay_send_journal_path` ([`:1231`][w1231]).
  - **Two writes before any submission.** State `signed` is written before
    votes are requested ([`:1188-1199`][w1188]). State `certified`, with the
    exact certificate JSON, is written before `owned_apply_v3`
    ([`:1217-1219`][w1217]).
  - **How it writes.** `_write_json_durable` ([`:3729`][w3729]) writes a
    temporary file with mode `0600`, fsyncs it, renames it into place and then
    fsyncs the directory.
- **Resume** (`_resume_fastpay_send`, [`:1279`][w1279]), when the call is
  repeated with the same `work_dir`:
  - **`applied`:** returns the stored result.
  - **`signed` only:** raises `FastPayPendingError` ([`:58`][w58]). The error
    gives the recovery-close height. It does not sign a second order for the
    journaled input.
  - **`certified`:** reads the owner's objects first.
    - If the view is complete (`truncated` is `false`) and the input is absent,
      it records the input as spent (`reconciled_from_chain`).
    - Otherwise it re-applies the same stored certificate
      (`_apply_fastpay_send_journal`, [`:1332`][w1332]).
- **Tests:**
  - `python/tests`: 623 passed and 3 skipped.
  - Three of the new tests are reproduce-first: they fail without the
    repair.
- **StakeHub record:** `0c3a3ca` on `master` updates
  [`docs/review/wallet-flows-review-20260929.md`][flows] with the repair and
  the SDK copy.
- **Wallet on this server:**
  - **SDK copy.** `fastpay.python_root` in `~/.pft/config.toml` points to the
    pinned copy
    `~/.local/lib/postfiat/rpc-sdk/postfiat-rpc-sdk-efc58090/python`.
  - **Backup.** The config from before this change is
    `~/.pft/config.toml.bak-20260930`.
  - **Unchanged.** The Rust signer binary line, `ce22.rpc_sdk_binary`, still
    points to `~/.local/lib/postfiat/rpc-sdk/postfiat-rpc-sdk-a3b95b23`.

### FW-08 and FW-09: batch-bound shield receipts and caps (StakeHub PR #19)

- **Branch:** `fix/wallet-caps-20260930`.
- **Commits:**

  | Commit | Content |
  | --- | --- |
  | `9535e8a` | FW-08: `pft_wallet/ce22.py`, `tests/test_pft_orchard.py` |
  | `188a935` | Caps: `pft_wallet/default_config.toml`, `limits.py`, `fastpay.py`, `transfer.py`, `swaps.py`, `fastswap.py`, `orchard.py`, `roundtrip.py`; `tests/test_pft_caps.py`, `tests/test_pft_transfer.py` |
  | `4828b24` | [`docs/review/wallet-flows-review-20260929.md`][flows] and [`docs/review/live-funds-readiness-20260929.md`][ready] |

- **Merge:** `23a45d9` on StakeHub `master` ([PR #19][sh19], squash).
  - The full-suite run gave 5,299 passed, 89 skipped and 84 failed.
  - I merged on that basis. The 84 failures are the same browser-bound and
    environment-bound set that fails identically on unchanged `master`.
- **FW-08:** `submit_certified_shield_batch` no longer reads each
  validator's last receipt line.
  - **Where the ids come from:** `_shield_batch_identity`
    ([`ce22.py:820-857`][sh-ce820]) reads the batch id and the tx ids from the
    report of `transport-peer-certified-batch-round`.
  - **Schema:** `postfiat-transport-peer-certified-batch-round-v1`.
  - **Producer:** [`crates/node/src/transport_cli.rs:2747`][tc2747] and
    [`crates/node/src/node_types.rs:3568`][nt3568] and [`:3612`][nt3612].
  - **Report checks.** The report must satisfy all of these:
    - `batch_kind` is `shielded`;
    - `block_height` is the round's height;
    - every `local_hot_finality` entry is an accepted receipt for that batch
      and height;
    - `local_receipt_count` equals the number of distinct tx ids.
  - **Per-validator check** ([`ce22.py:789-807`][sh-ce789]).
    - Each of the six validators must hold an accepted receipt, with code
      `accepted`, for every tx id.
    - The wallet looks only in that validator's last 1,024 lines of
      `receipts.append.jsonl` (`SHIELD_RECEIPT_WINDOW`,
      [`ce22.py:817`][sh-ce817]).
    - Receipts are appended at
      [`crates/node/src/storage_commit.rs:2900-2904`][sc2900]. When a tx id
      appears more than once, the last line is final
      ([`crates/storage/src/lib.rs:2236-2252`][st2236]), so the wallet keeps
      the last line per tx id.
- **FW-09: the caps.** Line numbers are at `23a45d9`.
  - **`limits.pft_run_atoms`, new.** It caps one FastPay payment or one PFT
    transfer, of any asset.
    - Default: 100,000,000 atoms, which is 100 PFT at 1 PFT = 1,000,000
      atoms ([`ce22.py:189-191`][sh-ce189]).
    - The default is set in [`default_config.toml:107`][sh-cfg107]. A config
      without the key uses it ([`limits.py:22-34`][sh-lim22]).
    - It is checked by `check_pft_run` ([`limits.py:37-45`][sh-lim37]) in
      `start`, before `store.create`: [`fastpay.py:121`][sh-fp121] and
      [`transfer.py:58`][sh-tr58].
  - **Swap flows.** These now reserve against the existing
    `limits.run_usd` (5.00) and `limits.campaign_usd` (50.00), with
    `reservation_id=operation_id`:
    - the private swap ([`orchard.py:415-418`][sh-or415]);
    - the API and CLI swaps ([`swaps.py:254-259`][sh-sw254]);
    - FastSwap ([`fastswap.py:438`][sh-fs438]).
  - **Round-trip legs.** They are covered by their bridge-in reservation
    through `limits.covered` ([`limits.py:111`][sh-lim111]; `covered_by` in
    [`roundtrip.py:172`, `:178` and `:190`][sh-rt172]).
  - **Behaviour:**
    - Every cap refuses before anything is signed, and the refusal names its
      config key.
    - The bridge caps are unchanged.
    - A reservation stays in the ledger after a failed run.

### Event logs on the six validators

- **Check 1, height 1063.** One devnet faucet grant of 1 PFT to the `testing`
  wallet, 10:59Z.
  - Proposer validator-1, view 0. Block and root identical on all six.
  - The fresh `transport-validator-events.ndjson` grew by about 50.5 KB on
    validators 0, 2, 3, 4 and 5. The records have schema
    `postfiat-transport-validator-serve-event-v1`.
  - Validator-1's file did not grow, because it was the proposer:
    - The round runs as a separate process. That process signs the
      proposer's own vote itself
      ([`crates/node/src/transport_runtime.rs:3066`][tr3066]).
    - It connects only to the other five validators.
- **Check 2, height 1064.** A second grant, 11:08Z.
  - Proposer validator-2, view 0.
  - Block `34ccbf7d…` and root `781db8c0…`, identical on all six.
  - Validator-1's file grew from 0 to 50,494 bytes on the same inode.
- **Result.** Every validator's refreshed log is confirmed to receive events.
  The proposer of a height never writes to its own log. That is expected.
- **RPC event log rule.** `/etc/logrotate.d/postfiat-rpc-events` is installed
  on all six validators (11:01:59Z to 11:02:07Z).
  - Target: `/var/log/postfiat/validator-*/rpc-events.ndjson`.
  - Options: `size 512M`, `rotate 3`, `compress`, `delaycompress`,
    `copytruncate`, `missingok`, `notifempty`.
  - The dry run was clean, and I forced no rotation. The largest file was
    174.8 MB, on validator-5.
- **Why `copytruncate` is safe for the RPC log:**
  - The RPC service opens the file once for append and keeps it open
    ([`crates/node/src/rpc_serve_runtime.rs:43-47`][rs43]).
  - Its readiness flag changes only when a write fails
    ([`crates/node/src/rpc_cli.rs:655-674`][rc655]).
  - After the rule was installed, readiness on all six was: ready, not
    degraded, `event_log_writable` true, 0 telemetry failures.
- **Now on each host:** two logrotate rules, `postfiat-validator-events` from
  2026-09-29 and `postfiat-rpc-events`.
- **Services:** no restart. All 12 validator and RPC PIDs are unchanged.
- **Records:**
  - [`deployments/combined-fastpay-20260928/observed/event-log-rotation-20260929.json`][rotation],
    section `verified-20260930`, on `release/combined-fastpay-20260928`:
    `1448eb12` (height 1063 and the RPC rule) and `7869a707` (the validator-1
    confirmation).
  - [Current State][state] on `main`: `873552eb` and `7fae65a6`.

### P3 sweep (StakeHub PR #20, not merged)

- **Branch:** `fix/wallet-p3-sweep-20260930`, based on the PR #19 branch.
- **Result:** 28 of the 31 recorded P3 findings are repaired, in 12 commits
  after `4828b24`:

  | Commit | Findings |
  | --- | --- |
  | `c1108e7` | WB-09, WB-12, WB-14, WB-15, WB-16, WB-17, WB-18 |
  | `e9171c0` | FW-10, FW-11, FW-12 |
  | `76ef022` | MP-07, MP-08, MP-09, MP-10, MP-11, MP-18 |
  | `13a7492` | MP-20 |
  | `ef5ab99` | PT-04, PT-05, PT-06, PT-07, PR-02, PR-03 |
  | `f57b072` | FW-15 |
  | `35b511e` | FW-16 (tests for the swap and Orchard private-egress resume paths) |
  | `4dc685a` | MP-22 |
  | `aee4963` | MP-19 |
  | `2a2f5df` | MP-21 |
  | `de72fe3` | Dashboard fixtures for the new fields |
  | `0a90d05` | The repairs and skips recorded in the four reviews |

- **Files changed:**
  - **`pft_wallet/`:** `balances.py`, `ce22.py`, `cli.py`, `fastpay.py`,
    `fastswap.py`, `gui/app.js`, `mainnet_bridge.py`, `operations.py`,
    `orchard.py`, `transfer.py`, `tui.py`.
  - **`stakehub/`:** `private_swap_egress.py`, `private_swap_orchestration.py`,
    `shielded_exit_executor.py`, `shielded_note_return_owner.py`.
  - **`scripts/`:** `pfeth_bridge_out.py`, `setup-wallet-registry.sh`.
  - **`tests/`:** `test_certified_script_results.py`,
    `test_dashboard_server.py`, `test_pft_fastpay.py`,
    `test_pft_faucet_send.py`, `test_pft_mainnet_bridge.py`,
    `test_pft_orchard.py`, `test_pft_swaps.py`, `test_pft_transfer.py`,
    `test_pft_wallet_registry.py`, `test_pft_wallet_surfaces.py`,
    `test_private_funding_money_path.py`,
    `test_shielded_note_return_owner.py`.
  - **`docs/review/`:** `wallet-bridge-review-20260924.md`,
    `private-funding-money-path-review-20260923.md`,
    `pay-transfer-and-registry-review-20260925.md`,
    `wallet-flows-review-20260929.md`.
- **Skipped (3), each recorded in its review as the other lane's decision:**
  - FW-13: the venue/pool inventory wallet is decrypted with the user's
    passphrase. Custody.
  - FW-14: the pool's a651 stays shielded after each run. Custody.
  - PT-08: which offline signer build ships by default. Release.
- **Wallet suite** (`tests/test_pft_*.py tests/test_generalized_wallet.py`) at
  `0a90d05`: 203 passed.
- **Full suite:** it started at 11:56Z in `~/.cache/sh-pr20-20260930` at
  `0a90d05`. It had not finished when I wrote this.
  - If it ends with the same failure set as `master` before this session ends,
    I merge PR #20 and add an end-of-session section to this handoff.
  - Otherwise, the merge is the first item tomorrow. Merge `origin/master` into
    the branch first: PR #19 was squashed, so the branch still carries
    `9535e8a`, `188a935` and `4828b24`.

### Fleet and repository boundary

- **Last observed chain state:** 2026-09-30T11:09Z, after the second grant.
  - Height 1064, block `34ccbf7d…`, root `781db8c0…`, identical on all six
    validators.
  - Faucet balance: 74.993972 PFT.
  - Height 1063, at 10:59Z: block `87c36773…`, root `43451730…`.
- **Last observed host state:** 2026-09-30T11:09Z.
  - All 12 validator and RPC services were running with unchanged PIDs.
  - Each host has two logrotate rules.
  - I did not re-read disk space today. After the 2026-09-29 cleanup, free
    space was 17.4 GB on validator-0, 19.6 GB on validator-1 and 24–29 GB on
    the others.
- **Deployed:**
  - Executable `1f8b332d…` and signed manifest `d2fdb687…`.
  - Source `c93b2137` on `release/combined-fastpay-20260928`.
- **Repository:**
  - **`main`:** `7fae65a6` before this handoff. Today's commits:
    - `efc58090`: the PR #53 merge, with `0310e8b4`.
    - `873552eb`: Current State note.
    - `7fae65a6`: Current State note.
  - **Release branches:**
    - `release/combined-fastpay-20260928` is at `7869a707` (was `4788ef1f`).
    - `release/combined-fastpay-20260925` is at `4d88956b`, unchanged.
  - **StakeHub `master`:** `23a45d9` (was `6a79672`).
  - **StakeHub open PRs:**
    - [#20][sh20], the P3 sweep.
    - #4 and #3, the other lane's older PRs.
- **Merged but undeployed:** no node code. `crates/` on `main` is identical to
  `c93b2137`. The SDK change is client-side. This server's wallet uses it
  through the pinned copy.
- **Live actions this session:**
  - the two devnet faucet grants;
  - the event-log, fd and readiness reads on the six validators;
  - the RPC logrotate rule.

  There was no mainnet, bridge or relay action.
- **CI on `main`, read at 12:04Z** (`gh run list --branch main`):
  - **`efc58090`:** `docs-build`, `product-security-ci` and `rust-ci` are all
    green.
  - **`873552eb` and `7fae65a6`:** `docs-build` and `product-security-ci` are
    green. `rust-ci` is not finished: its `check` job passed and its `test`
    job was still running.
  - **Verdict:** `main` is green at `efc58090`, with no failure on any run. Both
    later commits change only `docs/status/chain-state-current.md`.

### StakeHub wallet config on this server

- **Release paths:** `combined-fastpay-20260928`.
- **`fastpay.python_root`:** the pinned SDK copy at `efc58090`.
- **`[limits]`:**
  - `run_usd = "5.00"` and `campaign_usd = "50.00"` are present.
  - `pft_run_atoms` is absent, so the packaged default of 100,000,000 atoms
    applies.
  - To change it, add `pft_run_atoms = <atoms>` under `[limits]`.

### Live-funds readiness

StakeHub [`docs/review/live-funds-readiness-20260929.md`][ready] was updated in
PR #19.

- **Closed:** FW-04, FW-08 and FW-09.
- **Still open:**
  - The read-only route check and the small live qualification of the mainnet
    bridge.
  - The WB-11 burn transaction id, not yet confirmed against a real burn.
  - The "unattended use" hold.
  - Custody Q1 and archive Q2.
  - The P3 findings: 28 repaired on PR #20 and 3 skipped as the other lane's
    decisions.
- **Private round trip:** still not cleared for real money.

### Task Node

All three tasks are Rewarded:

| Task | Scope | Reward |
| --- | --- | ---: |
| `task_8982bf15104780ead50a130965c5409e` | FW-04 | 2.1 PFT |
| `task_bfbf055e4cadda7e1adede98d2c8732e` | FW-08 and the caps | 3 PFT |
| `task_b2ee243a846b545fceaf039db548325e` | P3 sweep | 2.63 PFT |

This handoff has no Task Node task.

## Next decision or action

### This lane's next steps, in order

1. **Merge PR #20** on a full-suite run with the same failure set as `master`.
   Merge `origin/master` into the branch first. If an end-of-session section
   below records the merge, skip this step.
2. **After the other lane's live runs:**
   - check the first live shield step against the new batch-bound check;
   - confirm the WB-11 burn id;
   - re-read the event logs.
3. **Fix `deployment_manifest_verified`** for the next release
   ([Current State][state]).
4. **Run the first Z3 cycle** once the keys, the inputs and the Arc route step
   are in ([`docs/status/z3-cycle1-inputs-20260922.md`][z3]).
5. **Write the NEAR Intents design note** if the other lane says yes.

### Only the other lane can provide

I asked for each item again tonight.

- **(a)** The two NEAR Intents design questions
  ([`docs/specs/near-intents-architecture-research-20260929.md`][note]).
  First asked 2026-09-29.
- **(b)** NAVCoin signer keys and custody, rows 4, 8, 11, 12, 13, 16 and 17
  ([`docs/status/z3-cycle1-inputs-20260922.md`][z3]). First asked
  2026-09-22.
- **(c)** The Arc route step: a route epoch of 11 or more, with a custody row
  for the Arc source, and the A666 issuer key. First asked 2026-09-28.
- **(d)** A compatible governed NAV profile with fresh proofs. First asked
  2026-09-22.
- **(e)** StakeHub custody Q1 and archive Q2
  ([`docs/review/custody-and-archive-decision-proposal-20260923.md`][custody]).
  First asked 2026-09-07.
- **(f)** Reserve-proof successor adoption, yes or no ([PR #49][pr49]). First
  asked 2026-09-24.
- **(g)** FastPay committee rotation for validator-5. First asked 2026-09-25.
- **(h)** The height-915 archive and the height-924 custodian. First asked
  2026-08-30.
- **(i)** The AI-governance decision for Gate Zero Z2. First asked 2026-09-03.
- **(j)** Twelve inventory rows
  ([`docs/review/defect-inventory-20260910.md`][inventory]). First asked
  2026-09-10.
- **(k)** Disk: first asked 2026-09-28 and 2026-09-29
  ([`deployments/combined-fastpay-20260925/observed/disk-inventory-20260928.json`][disk]).
  - the September 5–7 dumps;
  - `gate931` and `gate926`;
  - the three unknown-origin snapshot entries;
  - the five `.zst` archives.
- **(l)** The `ETHEREUM_MAINNET_RPC_URL` repository secret
  ([`docs/status/main-ci-red-20260928.md`][ci]). First asked 2026-09-28.
- **(m)** The cap values. They are now installed with defaults he may change
  (see the wallet config section above). First asked 2026-09-29.

## References

- This lane's previous handoff:
  [`docs/handoffs/2026-09-29___dravlic__near_intents_research_wallet_flows_reviewed_and_live_funds_readiness.md`][previous].
- postfiatl1v2 [PR #53][pr53] and
  [`python/postfiat_rpc/wallet.py`][w1063].
- StakeHub [PR #19][sh19] and [PR #20][sh20].
- StakeHub reviews:
  - [`docs/review/wallet-flows-review-20260929.md`][flows]
  - [`docs/review/live-funds-readiness-20260929.md`][ready]
- [`deployments/combined-fastpay-20260928/observed/event-log-rotation-20260929.json`][rotation]
  on `release/combined-fastpay-20260928` (`7869a707`).
- [`docs/status/chain-state-current.md`][state].

[previous]: 2026-09-29___dravlic__near_intents_research_wallet_flows_reviewed_and_live_funds_readiness.md
[state]: ../status/chain-state-current.md
[pr53]: https://github.com/postfiatorg/postfiatl1v2/pull/53
[pr49]: https://github.com/postfiatorg/postfiatl1v2/pull/49
[sh19]: https://github.com/postfiatorg/StakeHub/pull/19
[sh20]: https://github.com/postfiatorg/StakeHub/pull/20
[note]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/specs/near-intents-architecture-research-20260929.md
[z3]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/status/z3-cycle1-inputs-20260922.md
[ci]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/status/main-ci-red-20260928.md
[inventory]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/review/defect-inventory-20260910.md
[disk]: https://github.com/postfiatorg/postfiatl1v2/blob/release/combined-fastpay-20260925/deployments/combined-fastpay-20260925/observed/disk-inventory-20260928.json
[rotation]: https://github.com/postfiatorg/postfiatl1v2/blob/7869a7079f1fa34d84579611b961d31084497443/deployments/combined-fastpay-20260928/observed/event-log-rotation-20260929.json
[w58]: https://github.com/postfiatorg/postfiatl1v2/blob/efc5809051580a352269d535bf05c0153cecd43c/python/postfiat_rpc/wallet.py#L58
[w1063]: https://github.com/postfiatorg/postfiatl1v2/blob/efc5809051580a352269d535bf05c0153cecd43c/python/postfiat_rpc/wallet.py#L1063
[w1188]: https://github.com/postfiatorg/postfiatl1v2/blob/efc5809051580a352269d535bf05c0153cecd43c/python/postfiat_rpc/wallet.py#L1188-L1199
[w1217]: https://github.com/postfiatorg/postfiatl1v2/blob/efc5809051580a352269d535bf05c0153cecd43c/python/postfiat_rpc/wallet.py#L1217-L1219
[w1231]: https://github.com/postfiatorg/postfiatl1v2/blob/efc5809051580a352269d535bf05c0153cecd43c/python/postfiat_rpc/wallet.py#L1231
[w1279]: https://github.com/postfiatorg/postfiatl1v2/blob/efc5809051580a352269d535bf05c0153cecd43c/python/postfiat_rpc/wallet.py#L1279
[w1332]: https://github.com/postfiatorg/postfiatl1v2/blob/efc5809051580a352269d535bf05c0153cecd43c/python/postfiat_rpc/wallet.py#L1332
[w3729]: https://github.com/postfiatorg/postfiatl1v2/blob/efc5809051580a352269d535bf05c0153cecd43c/python/postfiat_rpc/wallet.py#L3729
[tc2747]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/node/src/transport_cli.rs#L2747
[nt3568]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/node/src/node_types.rs#L3568
[nt3612]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/node/src/node_types.rs#L3612
[sc2900]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/node/src/storage_commit.rs#L2900-L2904
[st2236]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/storage/src/lib.rs#L2236-L2252
[tr3066]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/node/src/transport_runtime.rs#L3066
[rs43]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/node/src/rpc_serve_runtime.rs#L43-L47
[rc655]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/node/src/rpc_cli.rs#L655-L674
[flows]: https://github.com/postfiatorg/StakeHub/blob/master/docs/review/wallet-flows-review-20260929.md
[ready]: https://github.com/postfiatorg/StakeHub/blob/master/docs/review/live-funds-readiness-20260929.md
[custody]: https://github.com/postfiatorg/StakeHub/blob/master/docs/review/custody-and-archive-decision-proposal-20260923.md
[sh-ce189]: https://github.com/postfiatorg/StakeHub/blob/23a45d90799fb85901f62a490b3bd7eb3eb8390a/pft_wallet/ce22.py#L189-L191
[sh-ce789]: https://github.com/postfiatorg/StakeHub/blob/23a45d90799fb85901f62a490b3bd7eb3eb8390a/pft_wallet/ce22.py#L789-L807
[sh-ce817]: https://github.com/postfiatorg/StakeHub/blob/23a45d90799fb85901f62a490b3bd7eb3eb8390a/pft_wallet/ce22.py#L817
[sh-ce820]: https://github.com/postfiatorg/StakeHub/blob/23a45d90799fb85901f62a490b3bd7eb3eb8390a/pft_wallet/ce22.py#L820-L857
[sh-cfg107]: https://github.com/postfiatorg/StakeHub/blob/23a45d90799fb85901f62a490b3bd7eb3eb8390a/pft_wallet/default_config.toml#L107
[sh-lim22]: https://github.com/postfiatorg/StakeHub/blob/23a45d90799fb85901f62a490b3bd7eb3eb8390a/pft_wallet/limits.py#L22-L34
[sh-lim37]: https://github.com/postfiatorg/StakeHub/blob/23a45d90799fb85901f62a490b3bd7eb3eb8390a/pft_wallet/limits.py#L37-L45
[sh-lim111]: https://github.com/postfiatorg/StakeHub/blob/23a45d90799fb85901f62a490b3bd7eb3eb8390a/pft_wallet/limits.py#L111
[sh-fp121]: https://github.com/postfiatorg/StakeHub/blob/23a45d90799fb85901f62a490b3bd7eb3eb8390a/pft_wallet/fastpay.py#L121
[sh-tr58]: https://github.com/postfiatorg/StakeHub/blob/23a45d90799fb85901f62a490b3bd7eb3eb8390a/pft_wallet/transfer.py#L58
[sh-or415]: https://github.com/postfiatorg/StakeHub/blob/23a45d90799fb85901f62a490b3bd7eb3eb8390a/pft_wallet/orchard.py#L415-L418
[sh-sw254]: https://github.com/postfiatorg/StakeHub/blob/23a45d90799fb85901f62a490b3bd7eb3eb8390a/pft_wallet/swaps.py#L254-L259
[sh-fs438]: https://github.com/postfiatorg/StakeHub/blob/23a45d90799fb85901f62a490b3bd7eb3eb8390a/pft_wallet/fastswap.py#L438
[sh-rt172]: https://github.com/postfiatorg/StakeHub/blob/23a45d90799fb85901f62a490b3bd7eb3eb8390a/pft_wallet/roundtrip.py#L172

## End of session (12:58 UTC)

StakeHub PR #20 (the P3 sweep) was merged as `eb7388d` (squash) after its full-suite run on this server finished at 12:52Z with 5,336 passed, 89 skipped and 84 failed — the same browser and environment-bound set that fails identically on unchanged master. Because PR #19 had been squashed, I first merged `origin/master` into the branch (merge commit `9336484`, no conflict markers, wallet suite 203 passed on the merged tree) so that GitHub could merge it. StakeHub master is now `eb7388d`: FW-04 record 0c3a3ca, PR #19 23a45d9, PR #20 eb7388d on top of 6a79672. Nothing else changed after the handoff above; the fleet is unchanged at height 1064.
