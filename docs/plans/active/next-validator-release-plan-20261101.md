# Next validator release plan (after signer-rotation-20261007)

Skeleton written 2026-10-08. The date suffix is a name, not a date. No date is promised: this
release starts after `signer-rotation-20261007` is deployed and its activation is done
([current plan](next-validator-release-plan-20261005.md)).

## Summary

1. `signer-rotation-20261007` is cut from main at `0fa55d0b` (`release/signer-rotation-20261007`, tip `b4d3ebde`); rollout 2026-10-09 at the earliest.
2. This release carries main past that cut plus the candidates below that are ready and reviewed.
3. Main past the cut changes node behaviour only in rpc-serve input checks (#87, #89, #91, #92: malformed requests now rejected); the rest is test-only Rust, the Python fallback and docs.
4. Rule kept from the current plan: changes that alter a consensus or state result get their own qualification; read-path and tooling changes ride along.
5. Qualification and rollout follow the current plan; nothing starts before the "Not before" rules hold.

## Already on main past the cut

`git log --oneline 0fa55d0b..origin/main`; `git diff --stat 0fa55d0b origin/main -- crates/` touches only test code.

- [x] `9d837bef` (PR #54, contains `c2a03a3b`, `b817b5a1`): removes the dead `#[cfg(test)]` swap-pricing wrapper (`crates/node/src/execution_actions.rs`, `crates/node/src/lib.rs`, `crates/node/src/tests/asset_orchard_issued_tests.rs`). Test-only.
- [x] `51144786`: Python fallback reads the newest blocks at or below the end height (`_account_tx_client_side_scan`, `python/postfiat_rpc/client.py`; `python/tests/test_account_tx_fallback.py`); archive-scan regression test `account_tx_scan_and_index_return_the_same_transaction_kinds` (`crates/node/src/tests/account_tx_truncation.rs`). Read-path tooling.
- [x] `bbe82032`, `54515003`: docs (Z3 plan status; 2026-10-07 handoff).
- [x] Also docs only: `e92b8157`, `0a136eaa`, `f3f2a1e1`, `774a6025`.
- [x] `9e9d45d2`, `af346e00`, `38a10d54`, `5270b8c1` (PRs #87, #89, #91, #92): rpc-serve rejects ambiguous or wrong-typed params of `owned_certificate`, `fastswap_objects`, `transfer_fee_quote` and the proxy parent-wait pins (`crates/node/src/rpc_cli.rs`). RPC serving; no in-repo caller is rejected (review below).

## Candidates

Included only when ready and reviewed by the cut; none is promised.

- [ ] Draft PR #47 (citadelculture): relative RPC child request spool path, issue #27 (`crates/node/src/rpc_cli.rs`). Blocker: draft; owner must finish it. Read-path (RPC serving).
- [ ] PR #52 (JJ2203-theRealOne): RPC worker requests with relative data directories (`crates/node/src/main_parts/cli_dispatch_parts/group_03.rs`). Blocker: waits for #47, the correct fix. Read-path (RPC serving).
- [ ] Draft PRs #43–#46 (citadelculture), if their owner finishes them. Tooling:
    - [ ] #43 rejects uncorrelated raw finality RPC responses (`scripts/native_rpc_finality_submit.py`).
    - [ ] #44 documented node wrapper invocations (`scripts/node-*`).
    - [ ] #45 Python RPC probe false negative across resolved addresses (`python/postfiat_rpc/rpc_probe.py`).
    - [ ] #46 transparent-only monitor smoke with the sole proof warning (`scripts/testnet-monitor-snapshot-smoke`).
- [ ] Python fallback gaps: no atomic-swap rows; escrow, NFT and offer row indexes shift in blocks with a swap (`_account_tx_client_side_scan`; [account history](../../rpc/account-history.md#result-window-and-truncated)). Owner: this lane. Read-path tooling.
- [ ] Archive scan `truncated` means "possibly incomplete" (`account_tx_scan`, `crates/node/src/block_finality.rs`). Changed only if an exact flag is wanted; it needs an unbounded scan of a public read. Owner: this lane, on request. Read-path.
- [ ] The other lane's delayed-precommit fix for its unreleased candidate. Blocker: pushed to main and reviewed. **Consensus change: its own qualification.**
- [x] Testnet provisioning default of the RPC accept budget. Done: [public RPC operator policy](../../runbooks/public-rpc-operator-policy.md) and `systemd/postfiat-rpc.service.example` carry `--max-requests 100000` and `RestartSec=1` like the release generator (`crates/node/src/batch_snapshot.rs:2403`); `example_rpc_unit_matches_generator_accept_budget` (`crates/node/src/tests/snapshot_deployment.rs`) fails if either drifts again. The two `scripts/a666-r4-*` rehearsal scripts still pass `10000`; they are frozen records pinned to candidate `39f7fae3` and were left as is. Tooling/docs.
- [ ] SCT-08: bounded read-only evidence campaign (complete signed bindings, publisher-attested work digests, exclusions, admission facts, native registry-root binding), authorized 2026-10-12 ([inventory](../../review/defect-inventory-20260910.md)). Owner: this lane.
- Not in this repository: FW-13 and FW-14 (P3, StakeHub), owned by the other lane. Tracked here only.
  Decision (2026-10-12), FW-14: I decided that the pool keeps its a651 in the shielded balance after each run, as the deployed release does.

## Contributor pull requests triaged 2026-10-12

bradsbots (fork, read permission) opened #56–#108 between 2026-10-08 and 2026-10-12; none is merged, so
`signer-rotation-20261007` is unaffected. Older PRs (#39, #40, #43–#47, #49, #52) are unchanged above.

- A: CI green, mergeable, not stacked, and only `rpc_sdk`, Python client, scripts, docs, tests, or input/strict-param/env validation in rpc-serve or wallet-proxy.
- B: changes accepted behaviour (node, bridge workers, wallet-proxy runtime) or diff > ~400 lines.
- C: CI red or running, conflicts, or stacked on an unmerged PR.
- No PR had a CI result: every run was held as `action_required`. The 75 held runs (rust-ci, product-security-ci, docs-build) at the head SHA of the 25 A candidates were approved at 12:47Z; the 150 runs of B and C stay held. Checked once at 12:50Z: no job failed, rust-ci `check`/`test` still running or queued on all 25, so nothing was merged today.
- Merge (next session): all three runs green, then `gh pr merge <n> --merge --match-head-commit <head>` (merge commits, as #51 and #54), stacked PRs after their base.
- 2026-10-13: the 15 held runs of #56 and #60–#63 approved at 11:49Z; rust-ci `test` and `open-reserve-proof-kit` still running at 12:23Z, so none merged. Merge them in number order; #60–#62 conflict on the inventory summary only, and after #60–#63 it reads Fixed 107 / Recorded, not fixed 1 (STO-04).
- 2026-10-13 12:38–12:58Z: #60, #62, #61 merged locally at their reviewed heads (inventory counts reconciled), #56 by GitHub; #63's `test` still running at 12:57Z, so it stays open. Inventory now Fixed 106 / Recorded, not fixed 2 (STO-04, CHO-05).
- Related older items: #57 would close the Python fallback atomic-swap gap above; #58 targets the RPC accept-budget default above; #64 duplicates draft #43, #59 draft #45, #56 overlaps #47/#52.

| PR | Title | Area | Size | Head | Class | Action or reason |
|---|---|---|---|---|---|---|
| #56 | Fix rpc-serve relative --data-dir child dispatch and response id echo (issue #27) | `crates/node` | +165/−11 | `2ba57c6a` | B | [x] Reviewed 2026-10-13: MERGE — relative `--data-dir`/`--spool-dir` made absolute at startup and child launch, a worker reply under another id (`local-1`) gets the request id and an `rpc_child_id_mismatch` event, as #27 and the #52 review asked; the rpc unit passes absolute paths, so validators see no change; covers #47/#52; merged `d51f6ae7` |
| #57 | Emit atomic swap rows from the account_tx Python fallback and fix later row indexes | `docs`, `python/postfiat_rpc`, `python/tests` | +247/−4 | `995dbc62` | A | [x] Reviewed 2026-10-13: FIX-AND-MERGE — swap rows/indexes match `account_tx_rows_for_transparent_block`; new tests sat below `unittest.main()` (moved, `5b02fa8f`); merged `1736aebb` |
| #58 | Align operator RPC accept-budget defaults with the release generator and guard against drift | `crates/node` (test), `docs`, `systemd` | +41/−7 | `f1cf1fdb` | A | [x] Reviewed 2026-10-13: MERGE — head moved from `64865358` (main merged in); docs, example unit and a test only, so A: the generator already renders `--max-requests 100000`/`RestartSec=1` and the new test pins the example to it; merged `2209cb49` |
| #59 | Try every resolved address in the Python RPC status probe | `python/postfiat_rpc`, `python/tests` | +204/−17 | `90d5cb27` | A | [x] Reviewed 2026-10-13: FIX-AND-MERGE — tries each address; a socket constructor `OSError` (no IPv6) still escaped, now a failed candidate (`92e6abd6`); merged `772e4d57` |
| #60 | Repair P3 findings CHO-06 and SWP-05: strict digest and timestamp validation | `crates/node`, `docs` | +139/−28 | `9302257a` | B | [x] Reviewed 2026-10-13: MERGE — rehearsal digests must be 96 chars of `0-9a-f` and attestation `observed_at` a real date and time (second 60 refused), the CHO-06/SWP-05 repairs the reviews name; real digests and timestamps pass; inventory counts conflicted with main (94/14), reconciled to 96/12 in the local merge `a243aaf2` |
| #61 | Repair P3 findings SWP-04 and MPL-02: timing capacity and latest-id order | `crates/node`, `docs` | +203/−49 | `c440d7dd` | B | [x] Reviewed 2026-10-13: MERGE — an identical timing replay at the 64-stage cap is a no-op instead of `StorageFull` (SWP-04); `latest_tx_id` reports the FastLane tail before the atomic-swap tail, the selection order (`mempool_proposals.rs:1264`/`1283`), as MPL-02 asked; `testnet-wallet-minimum-smoke` (one pending tx) unaffected; inventory reconciled to 106/2 in the local merge `14850a7e` |
| #62 | Repair P3 findings SMG-05 and SMG-06: bounded artifact reads and relative output preflight | `crates/node`, `docs` | +279/−40 | `478d6cbe` | B | [x] Reviewed 2026-10-13: MERGE — manifest (1 MiB), checksum (4 KiB) and index reads capped on the opened handle; a bare relative output passes the disk preflight and an existing output is measured itself, as SMG-05/06 asked; six stale rows (`0b9c6715`) checked; the index cap test also passes without the fix (race not exercised); inventory reconciled to 104/4 in the local merge `16c3c0ef` |
| #63 | Repair P3 finding CHO-05: negative rehearsal probes keep the approvals they test | `benchmarks`, `crates/node`, `docs` | +288/−89 | `d784294d` | B | [ ] Reviewed 2026-10-13: MERGE, merge when green — the negative rehearsal keeps the signed approvals, needs the positive fixture to verify and fails a probe rejected for another reason, as CHO-05 asked; the runner already passes the activation's signed transition; live five-signer rehearsal not run; still running: rust-ci `test` at 12:57Z; now conflicts with main on the inventory (CHO-05/06 rows, summary) and the review's repair result: at merge keep CHO-06 fixed, Fixed 107, Recorded, not fixed 1 (STO-04), and name both repairs |
| #64 | Reject uncorrelated raw finality RPC responses in the submit helper | `scripts` | +83/−2 | `751cbccc` | A | [x] Reviewed 2026-10-13: MERGE — status/finality ids must equal the request id before routing or persistence; script has no other callers; merged `989c73ab` |
| #65 | Repair P3 finding UNL-04: bind the shadow-round report to its root, window and registry state | `docs`, `python/postfiat_rpc`, `python/tests` | +133/−6 | `39e93b51` | A | [x] Reviewed 2026-10-13: FIX-AND-MERGE — root/window/state binding; a re-hashed swap still seated the held candidate, now the decision is re-derived (`ff56226d`); merged `42b1be74` |
| #66 | Add Python client wrappers for archive_window and the public-read verifiers | `docs`, `python/postfiat_rpc`, `python/tests` | +152/−0 | `38c2fa5c` | A | [x] Reviewed 2026-10-13: MERGE — names, 512-block inclusive bound and `--from-height` mapping match `rpc_dispatch.rs`; new methods only; merged `03a0c735` |
| #67 | Add Python client wrappers for the remaining parameterized public reads (stacked on #66) | `docs`, `python/postfiat_rpc`, `python/tests` | +278/−0 | `5d0e44fa` | A | [x] Reviewed 2026-10-13: MERGE — five wrappers send the `rpc_dispatch.rs` flag names (`--note-id`, `--nullifier-1/2`, `--epoch` u64); new methods only; merged `4473bba5` |
| #68 | Complete Python client coverage of the documented public reads (stacked on #67) | `docs`, `python/postfiat_rpc`, `python/tests` | +504/−0 | `8902392d` | A | [x] Reviewed 2026-10-13: MERGE — nine wrappers; `active_only` sent only when true, as the presence flag in `append_rpc_param_flags`; own commit 226 lines; merged `bbf6ddb0` |
| #69 | Expose every documented public read through the Python RPC CLI (stacked on #68) | `docs`, `python/postfiat_rpc`, `python/tests` | +810/−40 | `aacc8cf9` | A | [x] Reviewed 2026-10-13: MERGE — `--method` choices unchanged for the 33 existing methods, 21 reads added with required-flag checks; own commit 346 lines; merged `79f148e0` |
| #70 | Bound the Solana observer's RPC response reads | `python/postfiat_rpc`, `python/tests` | +89/−1 | `4c7ccfb0` | A | [x] Reviewed 2026-10-13: MERGE — Solana `_rpc` reads at most 1 MiB + 1 and needs a JSON object, as `hyperliquid.py`; observer-only; merged `7348c421` |
| #71 | Bound and validate the Vultr inventory read in the safe-rollout preflight | `python/postfiat_ops`, `python/tests` | +46/−1 | `5bcd67e8` | A | [x] Reviewed 2026-10-13: MERGE — release-day preflight: a valid instance reply is unchanged; oversize, bad JSON or no instance object is now `SafetyError`; merged `bd0bfcc8` |
| #72 | Regenerate the RPC method inventory (144 -> 155 methods) and guard it against lagging the method surface (stacked on #73) | `docs`, `python/tests`, `scripts` | +632/−43 | `f3254e70` | A | [ ] Reviewed 2026-10-13: COMMENT — guard right, committed inventory stale: 9 freshness failures on main, 23 after #67–#69; regeneration on main asked ([comment](https://github.com/postfiatorg/postfiatl1v2/pull/72#issuecomment-6144433008)) |
| #73 | Inventory generator: detect Python wrappers that forward through helpers or wrap the method literal | `python/tests`, `scripts` | +271/−5 | `894e1295` | A | [x] Reviewed 2026-10-13: MERGE — AST-proven forwarding helpers; on main only 20 `python_client` false→true, no row changes; committed inventory left to #72; merged `2cf73e9e` |
| #74 | rpc_sdk: support the verify_blocks, verify_bridge, verify_mempool and verify_shielded reads | `crates/rpc_sdk` | +309/−46 | `a1df96f9` | A | [x] Reviewed 2026-10-13: MERGE — four parameterless reads; standalone validators reuse the `verify_state` section checks; new methods only; merged `b39589b3` |
| #75 | rpc_sdk: support the account_tx_index_status read | `crates/rpc_sdk` | +302/−37 | `8c51ba6e` | A | [x] Reviewed 2026-10-13: MERGE — validator matches `account_tx_index_status` in `block_finality.rs` (both branches); new method only; list conflicts with #74 resolved locally, both sides kept; merged `692779e7` |
| #76 | rpc_sdk: support the nav_reserve_proof_status read | `crates/rpc_sdk` | +370/−36 | `60dc6efd` | B | [ ] review: 406 lines (> ~400) |
| #77 | rpc_sdk: support the vault_bridge_route read | `crates/rpc_sdk` | +424/−18 | `c19decf3` | B | [ ] review: 442 lines |
| #78 | rpc_sdk CLI: validate requests before writing them, and validate params in validate-request without --expect-kind | `crates/rpc_sdk` | +324/−3 | `98ac2857` | A | [x] Reviewed 2026-10-13: FIX-AND-MERGE — refused shapes (limit 0/>512, bad hashes) are ones the node also rejects; doctor defaults pass; either-outcome unmapped test tightened (`ed42d646`); merged `12b83c86` |
| #79 | rpc_sdk CLI: one source of truth for the supported-method lists | `crates/rpc_sdk` | +251/−22 | `6ff430f7` | A | [ ] Reviewed 2026-10-13: COMMENT — conflicts with #74/#75/#78 and its lists would drop their 5 methods; kind errors list `mempool_submit_fastlane_primary_finality`, which no kind path accepts; rebase asked |
| #80 | rpc_sdk: add vault_bridge_status request, validator, and CLI wiring | `crates/rpc_sdk` | +955/−22 | `d76f4c94` | B | [ ] review: 977 lines |
| #81 | rpc_sdk: add market_ops_status request, validator, and CLI wiring | `crates/rpc_sdk` | +553/−26 | `9efc59c2` | B | [ ] review: 579 lines |
| #82 | rpc_sdk: add owned_objects request, validator, and CLI wiring | `crates/rpc_sdk` | +660/−37 | `cea09350` | B | [ ] review: 697 lines |
| #83 | rpc_sdk: add owned_recovery_status request, validator, and CLI wiring | `crates/rpc_sdk` | +518/−37 | `dd67c29e` | B | [ ] review: 555 lines |
| #84 | rpc_sdk: add owned_recovery_capabilities request, validator, and CLI wiring | `crates/rpc_sdk` | +494/−33 | `f95dfad8` | B | [ ] review: 527 lines |
| #85 | rpc_sdk: add owned_certificate request, validator, selector binding, and CLI wiring | `crates/rpc_sdk` | +1007/−25 | `3189bba6` | B | [ ] review: 1032 lines |
| #86 | rpc_sdk CLI: bind every validate-response kind to --request-file | `crates/rpc_sdk` | +223/−2 | `7328b250` | A | [x] Reviewed 2026-10-13: FIX-AND-MERGE — binding correct; no SDK `--request-file` caller; atomic-swap branches re-read the file (citadelculture), now reuse the parsed request (`47874faf`); merged `0b3ec7bf` |
| #87 | node rpc-serve: reject owned_certificate requests carrying both selectors | `crates/node` | +74/−6 | `418cd804` | A | [x] Reviewed 2026-10-13: MERGE — both keys (also `lock_id` + null digest) now `rpc_protocol_error`; wallet-web and #88 send one key; merged `9e9d45d2` |
| #88 | python client: add owned_recovery_status and owned_certificate wrappers | `python/postfiat_rpc`, `python/tests` | +66/−0 | `d5fee302` | A | [x] Reviewed 2026-10-13: MERGE — params and exactly-one-selector rule match `rpc_cli.rs`; new methods only; merged `e9eb7b6c` |
| #89 | node rpc-serve: reject wrong-typed fastswap_objects params instead of ignoring them | `crates/node` | +130/−6 | `d6599054` | A | [x] Reviewed 2026-10-13: MERGE — present non-string/non-u64 (incl. null) params now `fastswap_failed`; only caller (rpc_sdk) well-typed; tests cover helpers, not the arm; merged `af346e00` |
| #90 | node rpc-serve: strict optional params for fastswap_policy and fastswap_checkpoint_status (stacked on #89) | `crates/node` | +214/−16 | `85d40b00` | A | [x] Reviewed 2026-10-13: MERGE — `fastswap_policy`/`fastswap_checkpoint_status` optional params strict, explicit null refused; only caller (rpc_sdk) omits absent keys; merged `b993c0ed` |
| #91 | node rpc-serve: reject wrong-typed transfer_fee_quote optional params instead of dropping them | `crates/node` | +184/−11 | `9438a231` | A | [x] Reviewed 2026-10-13: MERGE — wrong-typed or null `sequence`/`memo_*` now `rpc_protocol_error`; wallet-web, Python, rpc_sdk, wallet-proxy send strings/ints or omit; merged `38a10d54` |
| #92 | node rpc-serve: reject wrong-typed proxy parent-wait requirements instead of waiving them | `crates/node` | +161/−9 | `f77fa0b5` | A | [x] Reviewed 2026-10-13: MERGE — non-string root/parent pins now `rpc_protocol_error`; null stays "no pin" as wallet-proxy sends; merged `5270b8c1` |
| #93 | node rpc-serve: reject proxy root/parent-hash pins sent without the height instead of ignoring them (stacked on #92) | `crates/node` | +305/−10 | `e1c2c72e` | A | [x] Reviewed 2026-10-13: MERGE — root/hash pin without height now `rpc_protocol_error`, as #94's docstring assumes; wallet-proxy always sends the height, rpc_sdk all-or-none; merged `926d8a46` |
| #94 | python client: refuse shield_batch_finality parent pins sent without the height | `python/postfiat_rpc`, `python/tests` | +92/−1 | `c5ea3668` | A | [x] Reviewed 2026-10-13: MERGE — hash/root pin without height refused before `_call`; no Python caller sends that shape; main's node ignores it until #93; merged `13700160` |
| #95 | wallet-proxy: pin the finalized block hash as the parent of a primed proposer route | `wallet-proxy` | +89/−0 | `051fa5d1` | B | [ ] review: wallet-proxy routing semantics (parent-hash pin of a primed proposer route) |
| #96 | wallet-proxy: validate the proposer and fastpay route timing env at startup | `wallet-proxy` | +75/−10 | `3bc1f6f5` | A | [x] Reviewed 2026-10-13: MERGE — six route timing vars via `parseBoundedIntegerEnv` (whole-token check); defaults and in-range values unchanged, malformed/out-of-range now stop startup; no tracked config sets them; merged `75c55fba` |
| #97 | wallet-proxy: validate the wallet feed cadence, read timeout and per-connection TCP cap env | `wallet-proxy` | +68/−5 | `9a4352af` | A | [x] Reviewed 2026-10-13: MERGE — feed interval/floor/read timeout and `MAX_TCP_PER_WS` bounded (0 now refused); helper conflict with #96 resolved locally keeping main's identical check; merged `7b0bae8d` |
| #98 | wallet-proxy: validate the remaining integer env settings at startup (stacked on #96) | `wallet-proxy` | +152/−26 | `4175cf2d` | A | [x] Reviewed 2026-10-13: MERGE — #96 merged; nine settings strict, defaults unchanged; out-of-range now stops startup (e.g. quote TTL > 1 day, certificate retry < 250 was silently replaced); tracked scripts set in-range ports only; merged `d1e7a7d4` |
| #99 | wallet-proxy: validate the boolean env flags at startup | `wallet-proxy` | +122/−11 | `a0fe3f5c` | B | [ ] review: changes accepted values of routing flags (`0`/`1`/`TRUE` now flip features) |
| #100 | Reject non-finite PFTL amounts in pft_to_atoms with ValueError | `python/postfiat_rpc`, `python/tests` | +73/−3 | `02b5514b` | A | [x] Reviewed 2026-10-13: MERGE — NaN/Inf/overflow exponents now `ValueError: amount …`; finite amounts unchanged; only caller is the CLI; pre-existing: >28 significant digits round past the 6-decimal check; merged `e9d4bcd3` |
| #101 | wallet-proxy: require canonical decimal pfUSDC withdrawal amount_atoms | `wallet-proxy` | +79/−2 | `ab6c29dc` | A | [x] Reviewed 2026-10-13: MERGE — canonical decimal string or safe-integer number; wallet-web sends canonical strings; stored jobs are re-normalized on read, so a non-canonical one already on disk would read as absent; merged `c2fe6ae5` |
| #102 | wallet-proxy: require canonical decimal NAVCoin return amount_atoms | `wallet-proxy` | +47/−3 | `cb6bf41f` | A | [x] Reviewed 2026-10-13: FIX-AND-MERGE — canonical amount stops the tx-hash wedge; a JSON number > 2^53−1 was still rounded into the bound job (latent: deployed max 2.5e11), now refused as in #101 (`40ce4f52`); merged `45b50745` |
| #103 | Cap trustless bridge worker and readiness timeouts | `wallet-proxy` | +40/−3 | `150cc731` | B | [ ] review: bridge worker and readiness timeouts |
| #104 | wallet-proxy: require canonical decimal NAVCoin export amount_atoms | `wallet-proxy` | +52/−3 | `abb3a28d` | A | [x] Reviewed 2026-10-13: FIX-AND-MERGE — canonical amount stops the packet wedge; same rounded JSON number gap as #102, now refused (`834a21fd`); merged `4e44d07e` |
| #105 | wallet-proxy: cap eth fast-lane driver timeout_ms at 2147483647 | `wallet-proxy` | +30/−3 | `2b71c5c2` | A | [x] Reviewed 2026-10-13: MERGE — above 2^31−1 Node arms the kill timer at 1 ms, now `driver_config_invalid`; no working value refused (deployed max `10800000`), unlike #103; merged `0bcc2bd3` |
| #106 | Bound the FastSwap TCP connect with the transport timeout | `crates/rpc_sdk` | +57/−2 | `18270ff5` | B | [x] Reviewed 2026-10-13: MERGE (operator decision: a hang becomes a bounded error, no default changed) — `connect_timeout` per resolved address, error prefix kept; FastSwap connect now bounded by the transport timeout (live driver: 30 s); merged `8bed8159` |
| #107 | wallet-proxy: settle A666 round-trip when upstream closes mid-body | `wallet-proxy` | +87/−3 | `ee832ae4` | B | [x] Reviewed 2026-10-13: MERGE (operator decision: a hang becomes a bounded error, no default changed) — mid-body close now 502 `a666_roundtrip_unavailable` instead of a hang; complete, oversize, stall and refused keep their results; merged `610636db` |
| #108 | Validate import_timeout_ms in the NAVCoin return relay driver | `wallet-proxy` | +86/−1 | `4b3ab205` | A | [x] Reviewed 2026-10-13: MERGE — 1 s..24 h, the parent worker's cap; deployed `3600000` passes; `0`/`""` (silently 1 h) now refused, `"3600000"` (crashed `execFile`) now works; merged `0ba3eda8` |

## Not before

- [ ] `signer-rotation-20261007` deployed on all six validators and its activation finished (both signer groups; [activation](next-validator-release-plan-20261005.md#activation-after-rollout)).
- [ ] CI green on main at the cut commit.
- [ ] Full workspace suite at the cut commit (the release gate for the full suite).

## Qualification and rollout

As in the current plan: [Qualification](next-validator-release-plan-20261005.md#qualification) (~90 min after the suite) and [Rollout](next-validator-release-plan-20261005.md#rollout) (~60 min, one validator at a time, `rollback-one.sh` back to `signer-rotation-20261007`). A consensus candidate adds its own qualification before the cut.

- [ ] AnchorCheckpoint + ActivateCommittee of the signer rotation (§8.2–8.4) on the release day of this release
