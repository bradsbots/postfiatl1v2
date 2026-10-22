# Conference day one, release day prepared

- **Operator:** Domagoj Ravlić (`dravlic`)
- **Date:** 2026-10-07 UTC
- **Responding to:** no handoff from the other lane since
  [its 2026-10-01 handoff][nazgul]. Today is TOKEN2049 Singapore day one, with
  the founder's keynote at 11:00 Singapore time. My previous handoff:
  [2026-10-06][previous], with its addendum correcting the conference dates to
  7–8 October.

## BLUF

I kept conference day one clean: no contact with the six validator hosts or
the chain at all (not even the health check), and no StakeHub `master` commit.
The same holds for tomorrow. The day went to the release day (Friday
2026-10-09 at the earliest):

1. the six operator prompts for that day are prepared on my side from the
   [deploy sheet][sheet];
2. [PR #54][pr54] is merged (`9d837bef`) on the strength of the review and the
   PR's own CI run, in which its 25-minute Orchard test passed;
3. the last `account_tx` inconsistency in the Python client is fixed, and the
   one attributed to the Rust archive scan does not exist on `main`
   (`51144786`, with a regression test and the remaining Python gap
   documented);
4. the [Z3 round-trip plan][z3plan] carries a dated status block (`bbe82032`):
   what is ready on my side, what still waits on the other lane, and that the
   ten-cycle window must not span a release.

I also tightened my working rules: verify public dates on the web, never let
the coding agent wait for a CI run, and use a sturdier wait loop.

## Current state

- **Fleet and deployment boundary** ([Current State][state]).
  - Not read today. Last known state: 2026-10-06 09:13Z, all six at height
    1115, READY WITH ATTENTION. Nothing on the hosts, the chain or StakeHub
    `master` changes before 2026-10-09.
  - Deployed: `combined-fastpay-20260928`, executable `1f8b332d…`, source
    `c93b2137`, unchanged since 2026-09-28.
  - Repository: `main` at `bbe82032` before this handoff;
    `release/signer-rotation-20261007` at `b4d3ebde`.
  - Merged but undeployed: everything on `main` since `c93b2137`. The candidate
    carries it up to `0fa55d0b`; `9d837bef` and `51144786` came after the cut.
  - CI on `main` at the start of the day: all three workflows green on
    `0a136eaa` and `f3f2a1e1` (docs only on top of `0fa55d0b`, the release's
    source tip, which is green too).
- **PR #54** (`white-guy-01`, dead swap-pricing test wrapper), merged as
  `9d837bef`.
  - Evidence: the [2026-10-05 review][pr54c] (the wrapper only mapped the
    production call, the four assertions keep their codes, no other caller) and
    the PR's own `rust-ci` [`test` job][pr54job] of 2026-10-02, in which
    [`wan_devnet_invalid_asset_orchard_swap_proof_is_rejected_and_valid_swap_still_applies`][orchardtest]
    ran about 25 minutes and passed.
  - A local rerun was stopped after 21.5 minutes on one core without reaching
    the assertions, so the CI pass is the evidence.
  - Not deployed. The release branch was cut before this merge, so it belongs
    to the release after `signer-rotation-20261007`.
- **`account_tx` read paths** (`51144786`).
  - Python fallback ([`_account_tx_client_side_scan`][py1589]): with an end
    height below the tip and no start height it now reads the window that ends
    at `to_height`, re-reading from `max(0, to_height + 1 - limit)` when the
    newest window overshoots ([window][py1602]), and computes `truncated` from
    the blocks inside the range ([`:1618`][py1618]).
    [`test_end_height_below_tip_without_start_height_reads_that_range`][pyt96]
    fails before and passes after; the both-heights case
    ([test][pyt106]) was already exact.
  - Rust: the disk index ([`:313`][bf313], [`:341`][bf341]) and the archive scan
    ([`:603`][bf603]) build their rows with the same function,
    [`account_tx_rows_for_transparent_block`][bf902]: transfers, `payment_v2`,
    asset, atomic swap, escrow, NFT and offer operations, as `from` or `to`. The
    2026-10-06 handoff's note "the scan sees plain transfers only" was wrong; it
    is corrected here and in the [plan][plan] under item (3b). The regression
    test [`account_tx_scan_and_index_return_the_same_transaction_kinds`][att139]
    guards it.
  - Still different, documented in [Account History][acchist] and under plan
    item (3b): the Python fallback returns no atomic-swap rows and mis-numbers
    escrow, NFT and offer rows in a block that contains swaps.
  - Counts: `python/tests` 631 passed and 3 skipped; `account_tx` node tests
    11; `init_then_run_once` 1; fmt, inventory, clippy and the doc checks
    clean.
  - Task Node `task_b4c13c3a936ba5170f7287c736d11baf`: Rewarded 1.6 PFT.
- **Z3 round-trip plan** ([status block][z3status], `bbe82032`; plain bullets,
  no checkbox changed).
  - Ready on my side: the tooling and its dry-run repairs `d825b4fb`,
    `048d23df` and `25610696`, and the second dry run of all 39 commands; the
    Arc test wallet, funded on 2026-09-17; the [cycle inputs][z3] read on
    2026-09-22 and re-read on 2026-09-28 (9 resolved, 8 need the other lane).
  - Waiting on the other lane: the signer keys and input rows (since
    2026-09-22); the Arc custody row (since 2026-09-28; epoch 11 was reached at
    block 1110 with only the Ethereum source `2bae082a…`); a compatible NAV
    profile (since 2026-09-22), with BMNRC's registered `sp1-nav-reserve-v1`
    profile `4ff2afa5…` as the reference pattern.
  - Still open on my side: the Arc USDC allowance is 0 and needs approval at
    cycle time; the active governed route for Arc deposits is undecided
    (blocker 5).
  - Release rule: the ten-cycle window opens only after
    `signer-rotation-20261007` is deployed and must not span a release.
  - Dated updates to stale lines: the demo driver's route hardcoding (gone
    since `90fbc5da`), the G1 lineage and window, and the G2 notes.
  - Left as is, a follow-up: row 2 of the [cycle inputs][z3] still shows route
    epoch 10.
- **Release day preparation** (my side, outside the repository). Six operator
  prompts for 2026-10-09, mapped to the [deploy sheet][sheet]'s sections:
  1. sections 0–4: go/no-go reads, before state, stage recheck, fleet
     preflight, fresh signed canary backup;
  2. the store conversion dry run on a copy of validator-1's store;
  3. section 5: rollout one validator at a time, with a grant each;
  4. section 6: after checks;
  5. section 7: store conversion one host at a time, in the sheet's order
     (validator-5 first, then validators 0–4);
  6. section 8: bridge activation, with the unsigned issuer update prepared
     for the other lane, then the FastPay record signed by the six
     validators.

  Each live step has its own go from the operator on the day.
- **Task Node.** One network-proposed task for this account exists (a Windows
  install-script fix in the CorbanuTerminal repository, paid only for a merged
  PR there) and is left alone. Today: `task_b4c13c3a936ba5170f7287c736d11baf`
  (`account_tx`) Rewarded 1.6 PFT. The PR #54 merge, the Z3 plan refresh and
  the release-day preparation had no Task Node action; neither has this
  handoff.
- **CI on `main`** (`gh run list --limit 40`, read once at 11:28Z).
  - `9d837bef`, `51144786`, `bbe82032`: `docs-build` passed;
    `product-security-ci` passed in every job except `open-reserve-proof-kit`,
    still running; `rust-ci` `check` passed, `test` running.
- **Work server.** 71 GB free; the leftover PR build caches (4.7 GB) were
  removed.
- **Devnet.** Not touched. StakeHub `master` unchanged at `52eb686`;
  [PR #21][sh21] open for after the conference.

## Next decision or action

### My next steps, in order

1. 2026-10-08 (conference day two, nothing live): small repository work only;
   read the other lane's reaction, if any, to the [validator-5 note][v5]. The
   objection window closes 2026-10-08 evening UTC.
2. 2026-10-09 at the earliest, each live step with its own go
   ([deploy sheet][sheet]):
   - the before state, the fresh signed canary backup, the rollout of
     `signer-rotation-20261007` one validator at a time, the after checks;
   - in the same window, the store conversion per host;
   - then the signer-group activation: the fences, the final drained
     checkpoint, `ActivateCommittee` epoch 2 by validators 0–4, the unsigned
     `pftl_uniswap_route_bridge_policy_update` handed to the other lane, and
     the FastPay record signed by the six validators below height 10001;
   - merge StakeHub [PR #21][sh21]; the records and the [plan][plan].
3. The relay units on the six hosts, only if the other lane grants the window
   (item p).

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
- **(g)/(n)** Validator-5: the objection window until 2026-10-08 evening UTC,
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

- My [2026-10-06 handoff][previous]; the other lane's
  [2026-10-01 handoff][nazgul].
- Commits on `main`: `9d837bef`, `51144786`, `bbe82032`.
- [`deployments/signer-rotation-20261007/DEPLOY-SHEET.md`][sheet] on
  `release/signer-rotation-20261007`.
- [`docs/plans/active/next-validator-release-plan-20261005.md`][plan].
- [`docs/plans/active/z3-navcoin-roundtrip-plan.md`][z3plan].
- [`docs/rpc/account-history.md`][acchist].
- [`docs/status/chain-state-current.md`][state].

[nazgul]: 2026-10-01___nazgul__navcoin_create_and_swap_build_phase0_and_bmnrc_opening.md
[previous]: 2026-10-06___dravlic__release_candidate_cut_and_locally_qualified.md
[plan]: ../plans/active/next-validator-release-plan-20261005.md
[z3plan]: ../plans/active/z3-navcoin-roundtrip-plan.md
[z3status]: ../plans/active/z3-navcoin-roundtrip-plan.md#status-2026-10-07
[state]: ../status/chain-state-current.md
[acchist]: ../rpc/account-history.md#result-window-and-truncated
[z3]: https://github.com/postfiatorg/postfiatl1v2/blob/bbe82032e7e1d411bb0e18f31f884b5478088524/docs/status/z3-cycle1-inputs-20260922.md
[v5]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/review/validator-5-signer-committees-decision-proposal-20261001.md
[inventory]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/review/defect-inventory-20260910.md
[near]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/specs/near-intents-architecture-research-20260929.md
[pr49]: https://github.com/postfiatorg/postfiatl1v2/pull/49
[pr54]: https://github.com/postfiatorg/postfiatl1v2/pull/54
[pr54c]: https://github.com/postfiatorg/postfiatl1v2/pull/54#pullrequestreview-5412107296
[pr54job]: https://github.com/postfiatorg/postfiatl1v2/actions/runs/37060882996/job/111016963756
[sh21]: https://github.com/postfiatorg/StakeHub/pull/21
[sheet]: https://github.com/postfiatorg/postfiatl1v2/blob/b4d3ebdec4869bff40cbe26d8b26aec0fbc8e8a9/deployments/signer-rotation-20261007/DEPLOY-SHEET.md
[orchardtest]: https://github.com/postfiatorg/postfiatl1v2/blob/9d837bef9544e2d1145646c419ef54f7ce5ea6fa/crates/node/src/tests/asset_orchard_issued_tests.rs#L720
[py1589]: https://github.com/postfiatorg/postfiatl1v2/blob/51144786e8e20b1693a798f8a2b34016e0446474/python/postfiat_rpc/client.py#L1589
[py1602]: https://github.com/postfiatorg/postfiatl1v2/blob/51144786e8e20b1693a798f8a2b34016e0446474/python/postfiat_rpc/client.py#L1602-L1608
[py1618]: https://github.com/postfiatorg/postfiatl1v2/blob/51144786e8e20b1693a798f8a2b34016e0446474/python/postfiat_rpc/client.py#L1618-L1620
[pyt96]: https://github.com/postfiatorg/postfiatl1v2/blob/51144786e8e20b1693a798f8a2b34016e0446474/python/tests/test_account_tx_fallback.py#L96
[pyt106]: https://github.com/postfiatorg/postfiatl1v2/blob/51144786e8e20b1693a798f8a2b34016e0446474/python/tests/test_account_tx_fallback.py#L106
[bf313]: https://github.com/postfiatorg/postfiatl1v2/blob/51144786e8e20b1693a798f8a2b34016e0446474/crates/node/src/block_finality.rs#L313
[bf341]: https://github.com/postfiatorg/postfiatl1v2/blob/51144786e8e20b1693a798f8a2b34016e0446474/crates/node/src/block_finality.rs#L341
[bf603]: https://github.com/postfiatorg/postfiatl1v2/blob/51144786e8e20b1693a798f8a2b34016e0446474/crates/node/src/block_finality.rs#L603
[bf902]: https://github.com/postfiatorg/postfiatl1v2/blob/51144786e8e20b1693a798f8a2b34016e0446474/crates/node/src/block_finality.rs#L902
[att139]: https://github.com/postfiatorg/postfiatl1v2/blob/51144786e8e20b1693a798f8a2b34016e0446474/crates/node/src/tests/account_tx_truncation.rs#L139
