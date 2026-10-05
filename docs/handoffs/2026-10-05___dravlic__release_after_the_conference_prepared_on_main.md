# Release after the conference prepared on main

- **Operator:** Domagoj Ravlić (`dravlic`)
- **Date:** 2026-10-05 UTC
- **Responding to:** no handoff from the other lane since
  [its 2026-10-01 handoff][nazgul]. The other lane merged PR #55 (`b1d1928c`)
  on 2026-10-04 and presents the product on stage on 2026-10-06. My previous
  handoff: [2026-10-02][previous].

## BLUF

Because of the conference day, I changed nothing today on the six validator
hosts, on the chain, or in the StakeHub repository the demo installs from, and
I will change nothing there before 2026-10-07; every fleet action was a read.
The day went to the release that follows the conference, all on `main` and
undeployed:

1. the [release plan][plan] (`ab4ec9ee`);
2. the issuer-signed operation `pftl_uniswap_route_bridge_policy_update`, which
   updates a route's Ethereum bridge committee (`9e4d80be`, CI repair
   `8d1c9c20`);
3. the RPC accept budget raised, with no port closure while the service
   reports (`e3bb0dbf`);
4. a read-only command that prepares the six-member FastPay committee record
   and its unsigned governance batch (`a683475a`). Two facts matter for the
   fleet: all six validators sign that batch, and the new committee must start
   at exactly height 10001. If nothing is installed before then, fast payments
   take no new orders after height 10000;
5. a local dry run of both rotations on the six-validator test fixtures: both
   halves work with 5 of 6 signers, and the live procedure is written
   (`78c7b2e9`). The one gap it found was closed the same day with three
   per-validator commands that prepare, sign and assemble FastSwap control
   certificates (`672b707c`);
6. the weekend fleet state recorded (`df347288`). Blocks 1104–1115 are the
   other lane's BMNRC export of the full minted amount to Ethereum, A666 NAV
   epoch 9 and route epoch 11, a pfUSDC deposit and a BMNRC return import;
7. PR #54 reviewed with a comment and held until 2026-10-07; PR #55 read after
   its merge: correct, with two small follow-ups noted.

Validator-5 goes back into both signer groups with that release unless the
other lane objects by 2026-10-07 evening UTC. The bridge half ends with one
issuer-signed transaction, which I prepare.

## Current state

- **Fleet this morning** (07:21:55Z, [demo preflight][preflight]; recorded in
  [Current State, 2026-10-05][weekend], `df347288`). All six at height 1115,
  tip `28e1175b…`, root `a5287eaf…`. **READY WITH ATTENTION**: 55 PASS,
  5 ATTENTION (the hand-started relays), 0 FAIL. Validators up 6 d 23 h with
  0 restarts. RPC accept-budget restarts: validator-0 four, validator-5 two,
  the others one each. Free disk 16.8–28.6 GB. The other lane's
  `navcoin-proof-watchdog@` user units on the validator-3 host: 14.
  - Blocks 1104–1115 (read on validator-1, all accepted at view 0):
    - 1104: `pftl_uniswap_export_debit` of 640,585,238 BMNRC atoms (the full
      minted amount) on `pftl-bmnrc-ethereum-wBMNRC-usdc-v1`, signed by
      `pf4b26fe…`;
    - 1105: `destination_consume`, signed by `pf9bd795…`;
    - 1106: a PFT transfer;
    - 1107 and 1111: A666 route pause and unpause, signed by `pfd0c86d…`;
    - 1108–1109: A666 `nav_reserve_submit` and `nav_epoch_finalize` for
      epoch 9;
    - 1110: `pftl_uniswap_route_epoch_advance` from 10 to 11 on the A666 route,
      signed by `pffcb93d…`;
    - 1112–1114: a pfUSDC deposit propose, finalize and claim, signed by
      `pf23d883…`, claiming 75,000,000 atoms to `pff5e290…`;
    - 1115: `pftl_uniswap_return_import` of 75,000,000 BMNRC atoms to
      `pff5e290…`.
  - The same commit records the STO-05 closure next to the export-receipt
    sentence in [Current State][state]. It also records the SH-08 decision in
    the [StakeHub safety review][shr].
- **Release plan** ([plan][plan], `ab4ec9ee`).
  - Done on `main`: `1bb15a78` (manifest-verified record), `b1d1928c` (PR #55),
    `0609cb01` (PR #48) and `dc7d9bb6` (PR #51).
  - Built today: items 1 and 3 are ticked. Item 2's tool exists; the record
    itself is installed on release day.
  - Waiting on the other lane: the delayed-precommit fix, once pushed and
    reviewed.
  - Timing: qualification takes 90–115 min after the full workspace suite,
    rollout 61–73 min, hands-on about 2.5–3 h. Nothing is deployed before
    2026-10-07. The plan informs the other lane rather than asking, and the
    other lane may object until 2026-10-07 evening UTC.
- **Bridge committee operation** (`9e4d80be`, 21 files).
  - Fields: `issuer`, `route_id`, `authority_epoch` (current + 1),
    `committee_root`, and three echoed fields (`minimum_confirmations`,
    `handoff_controller_code_hash`, `wrapped_navcoin_code_hash`) that must
    equal the current values.
  - Consensus rules: issuer only, and no open handoff (no outstanding export
    or return claims, no StopPrepare fence on the target committee). The
    epoch and root must resolve through
    [`committee_for_policy`][puev380] to the newest governed committee (roster
    root [`fastswap_types.rs:177`][ft177], [`:197`][ft197]).
  - Activation has two steps. First, the validators admit epoch N+1 with
    `ActivateCommittee` after epoch N's final drained checkpoint
    ([`fastswap_control.rs:167`][fsc167], [`:386-410`][fsc386]). Then the
    issuer sends the update. The old committee keeps signing until both are
    done.
  - The receipt transition is `route_bridge_policy_updated`. Nothing changes
    on the Ethereum side.
  - Code: [`transactions_mempool_receipts.rs:3104-3187`][tmr3104] (dispatch
    [`:3630`][tmr3630], [`:3800`][tmr3800], [`:3883`][tmr3883],
    [`:3942`][tmr3942], [`:4021`][tmr4021], [`:4159`][tmr4159]),
    [`core_chain.rs:71-72`][cc71], [`market_nav_asset_types.rs:3376`][mnat],
    [`nav_vault_asset_execution.rs:5640-5742`][nv5640],
    [`nft_escrow_asset_execution.rs:3006-3016`][ne3006],
    [`block_finality.rs:1464-1472`][bf1464],
    [`certified_asset_ops.rs:378`][cao378],
    [`response_validation.rs:3088-3096`][rv3088],
    [`protocol_requests.rs:48`][pr48]. The builder mode `bridge-policy-update`
    is in [`a666-build-route-epoch-advance.py:87-171`][builder]; the spec
    section is [Rotating the route's Ethereum bridge committee][spec].
  - Tests: (a)–(g) fail with a stubbed dispatch and pass with the code.
    Regressions 14 + 6 + 4 passed, builder tests 14/14, and clippy
    `-D warnings` is clean on four crates.
  - Not covered:
    - execution has no validator-registry check; that is enforced through the
      validator-quorum `ActivateCommittee` path;
    - the replay test compares the ledger, not the storage root;
    - "open handoff" is interpreted as outstanding claims plus a StopPrepare
      fence;
    - A666 is not moved.
  - CI repair `8d1c9c20`: rustfmt on `ethereum_checkpoint_signing.rs` and one
    source hash in
    `docs/status/OPEN-SOURCE-PROOF-PUBLIC-INPUT-INVENTORY-20260716.json`; no
    proof-input entry changed.
- **RPC accept budget** (`e3bb0dbf`).
  - The generated RPC unit passes `--max-requests 100000` (was 10000) with
    `RestartSec=1` (was 5) ([`batch_snapshot.rs:2403`][bs2403]).
  - [`rpc_serve_with_report`][rsr17] finishes in-flight connections and
    writes the end-of-run report before closing the port
    ([`group_03.rs:424-457`][g03]).
  - I rejected a gapless handover: the service is a single process without a
    socket unit, and `SO_REUSEPORT` is unsafe because the mempool and finality
    locks are in-process.
  - Tests:
    - both failed first: `deployment_validator_unit_stage_is_canonical_and_non_overwriting`
      and `rpc_serve_budget_drains_in_flight_request_and_reports_before_closing_listener`;
    - `rpc_serve`: 35 passed; `snapshot_deployment`: 18 passed;
    - clippy clean.
  - What remains:
    - about 1 s of closed port per 100,000 connections;
    - an idle keep-alive can hold the drain up to `--timeout-ms` (30 s);
    - the [public RPC operator policy][rpcpol] still lists 10000 as the
      controlled-testnet default, attributed to
      `scripts/testnet-provision-bundle`, which is not in the repository.
  - The deployed `c93b2137` keeps the old behaviour until the release.
- **FastPay committee tool** (`a683475a`).
  - Usage: `postfiat-node fastpay-committee-prepare [--data-dir PATH]
    [--registry-file PATH] [--valid-from H] [--new-orders-through H]`.
  - What it does: it reads the node's data directory and builds the
    `FastPayRecoveryCommitteeV1` record for epoch N+1 over the six current
    registry keys with quorum 5. It test-applies the record against the next
    block, then prints the record, its payload and the unsigned governance
    batch. It never signs and never reads a key.
  - It refuses:
    - stale or unregistered keys;
    - any quorum other than 5 of 6;
    - a start height other than the previous end + 1;
    - a start height at or below the installing block, i.e. a passed deadline.
  - From the code:
    - the record is installed by a governance batch (policy, record and the
      amendment `fastpay_recovery_bootstrap_v1:<payload hash>`). All six
      active validators sign it with their current registry keys
      ([`governance.rs:521`][gov521];
      [`consensus_artifacts.rs:2842-2926`][ca2842], [`:2928-2990`][ca2928]).
      The signers are neither the issuer nor a single governance key, which
      corrects the 2026-10-01 proposal;
    - nodes replicate the record through a governance block, and the state
      root includes the committee list;
    - the new epoch must start at exactly the previous
      `new_orders_through_height` + 1, which is 10001, and the installing
      block must be below 10001 ([`owned_transfer_recovery.rs:875-899`][otr875]);
    - so epoch 2, if installed now, takes effect at 10001 and ends by default
      at 19990;
    - if no committee is installed before 10001, epoch 1 takes no new orders
      after height 10000, and a later rotation needs a code change. This is a
      deadline for the fleet regardless of the validator-5 decision;
    - validator-5's current key must be in the record
      ([`fastpay_recovery_node.rs:356-395`][frn356]).
  - Tests: five `fastpay_committee_prepare` tests, the CLI handler test and
    the 21 existing bootstrap tests pass; clippy is clean.
  - Docs: the [runbook section "Preparing the next committee"][runbook] and
    the proposal's "Update 2026-10-05" ([proposal][v5]).
  - Not yet run against a real devnet data directory, because that needs host
    access.
- **Dry run of both rotations** ([dry run][dryrun], `78c7b2e9`, plus two test
  files that reproduce it).
  - Setup: it ran on the repository's six-validator fixtures with the
    consensus code called directly, not on six running processes. The local
    harness was not suitable for three reasons:
    - it defaults to RPC port 27650, which is the live tunnel port;
    - it cannot create a route with an Ethereum bridge policy;
    - checkpoints need an Ethereum RPC.
  - Bridge half, in order:
    - the live defect reproduced: a checkpoint signed with the rotated fifth
      key fails `InvalidVoteSignature`, four signers fail `BelowQuorum`, and
      all five of validators 0–4 are needed;
    - an issuer update before activation is rejected
      (`committee_not_governed`);
    - after the final drained epoch-1 checkpoint, validators 0–4 activate
      epoch 2. A validator-5 signature is rejected
      (`InvalidControlCertificate`), and the route stays at epoch 1;
    - the issuer update is rejected while a handoff is open and accepted
      without one;
    - an epoch-2 checkpoint then assembles with validator-4 absent and the
      rotated validator-5 signing, 5 of 6.
  - FastPay half:
    - epoch 1 over six keys, validator-5 rotated;
    - `fastpay-committee-prepare` builds epoch 2 starting exactly at the
      previous end + 1. The rule is that end height + 1, not a constant;
    - the install needs all six signatures with current keys: five
      signatures are refused, and so is the stale key;
    - a payment under epoch 2 with validator-4 absent is certified.
  - Not exercised:
    - a real export producing the open handoff;
    - StopPrepare fences: the fixture has no FastSwap policy, while the live
      chain needs one fence per policy epoch.
  - The missing signing tool was added the same day (`672b707c`,
    [`fastswap_control_signing.rs`][fcs]; [commands][fsccmd]):
    - `fastswap-control-prepare` (`--kind activate-committee --epoch N
      --committee-root HEX` or `--kind stop-prepare --policy-epoch N`). It
      builds the committee from the active registry keys and refuses a wrong
      root, an epoch other than current + 1, or a missing drained final
      checkpoint. Then it runs the admission check;
    - `fastswap-control-vote-sign` signs only with a key that matches the
      active committee. It keeps anti-equivocation records under
      `fastswap-control-signing/` and refuses a second, different vote for
      the same key;
    - `fastswap-control-assemble` checks duplicates, signatures and the
      5-of-6 quorum, then dry-applies the certificate to a ledger copy.
  - The signers are the active FastSwap committee with their validator keys,
    5 of 6 ([`fastswap_control.rs:97-135`][fsc97];
    [`fastswap_types.rs:802-910`][ft802]), so validators 0–4 under epoch 1.
    A vote binds the committee identity, the action digest and the validator
    id, but no route or policy id.
  - Tests:
    - four in `fastswap_control_signing.rs`: an assembled activation is
      admitted by the six-validator fixture; validator-5's current-key vote
      and a set of four votes are refused; a second different vote is
      refused; prepare refuses without a drained final checkpoint;
    - the CLI handler test;
    - clippy, fmt and the inventory check are clean.
  - Still open:
    - the final drained FastLane checkpoint comes from the normal checkpoint
      flow (`fastswap_checkpoint_status`), not from a manual command;
    - StopPrepare has no end-to-end admission test.
  - Live procedure: steps 0–7 in the [dry run][dryrun], in five stages:
    1. read-only checks;
    2. validators 0–4 sign the StopPrepare fences, the final drained
       checkpoint and `ActivateCommittee`. This has no undo, but nothing
       changes until the next stage;
    3. the other lane's issuer sends the bridge update with the epoch-2 root.
       This has no undo; a mistake is fixed with epoch 3;
    4. a checkpoint is assembled with 5 of 6;
    5. `fastpay-committee-prepare` runs, then all six validators sign the
       record below height 10001.
  - The procedure has no live payment check after the install. The dry run
    covered payments only on the fixture.
- **Pull requests.**
  - [#54][pr54] (`white-guy-01`, dead swap-pricing test wrapper) is correct:
    the wrapper only mapped the production call, the four assertions keep
    their error codes, and there is no other caller. The real test behind it,
    [`wan_devnet_invalid_asset_orchard_swap_proof_is_rejected_and_valid_swap_still_applies`][orchardtest],
    is a slow Orchard proving test to run before merging on 2026-10-07.
    Status: [review comment][pr54c], not merged.
  - #55, merged by the other lane, is correct for what it claims: the disk
    index uses `>`, and the archive scan sets the flag only when a further
    matching row exists. No caller depended on the old meaning;
    `account_tx_truncation`: 1 passed. Two follow-ups are recorded in the
    plan:
    - the Python fallback scan keeps the old meaning
      ([`client.py:1609`][py1609], [`:1637-1639`][py1637]);
    - the archive scan still reports truncated when the range has more blocks
      than the limit, and returns oldest-first without a start height
      ([`block_finality.rs:577`][bf577]).
- **CI on `main`** (`gh run list` at 11:06Z).
  - `docs-build`, `rust-ci` and `product-security-ci` succeeded on
    `b1d1928c` and `ab4ec9ee`. `docs-build` succeeded on every commit today.
  - `9e4d80be` failed `product-security-ci` in two places:
    `public-tree-hygiene` (proof-inventory source drift) and the open proof
    kit's format check. It also failed the `rust-ci` `check` job at
    `cargo fmt`; its `test` job passed. `e3bb0dbf`, which predates the repair,
    failed both `product-security-ci` and the `rust-ci` `check` job at
    `cargo fmt`.
  - After the repair `8d1c9c20`, `product-security-ci` succeeded on
    `8d1c9c20`, `a683475a` and `78c7b2e9`.
  - Still running: `rust-ci` on `8d1c9c20` and every later commit, and
    `product-security-ci` on `df347288` and `672b707c`.
- **Read-only checks for pending items and release day** (validator-1,
  10:55Z; not yet in [Current State][state]).
  - Arc custody row: route `pftl-a666-ethereum-wA666-usdc-v1` is at epoch 11
    (policy `32c970e9…`, valid from height 1110 to 10000, not paused). It has
    one custody row, the Ethereum pfUSDC source `2bae082a…` (source epoch 10,
    issuer `pf23d883…`, the same figures as on 2026-09-28). No Arc source,
    chain id or the server wallet `0xC75Bf05C…` appears. The 2026-09-28
    request is therefore only partly met (the epoch, not the row) and stays
    open.
  - FastSwap committee: `fastswap_capabilities` and `fastswap_checkpoint_status`
    answer `fastswap_unavailable` on validator-1, so the FastSwap committees,
    policies, fences and the final checkpoint id could not be read over RPC.
    Block 1110's consensus committee epoch 3 (root `ca8da61a…`) is the
    block-finality committee, not the FastSwap one.
  - Release-day consequence: before activation, a read-only check of a
    validator host's local ledger must confirm the FastSwap control path is
    live on `c93b2137` and read its committee epoch and final checkpoint id.
- **Documents.** The [proposal][v5]'s opening summary still describes the
  FastPay committee as validators 0–4, and the dry run's "Live membership
  differs" note follows it. The proposal's 2026-10-02 section says six members
  with a stale validator-5 key. This is a dry-run follow-up.
- **Repository and deployment boundary.**
  - Live probe: yes, read-only. Preflight at 07:21:55Z and validator-1 reads
    at 10:55Z; no transaction, restart or configuration change.
  - Deployed: release `combined-fastpay-20260928`, executable `1f8b332d…`,
    source `c93b2137`, unchanged since 2026-09-28.
  - Repository: `main` at `672b707c` before this handoff.
  - Merged but undeployed: everything in the plan's scope plus today's node
    commits.
- **Work server.**
  - Disk: 75 GB free at 11:00Z with the suite running (94 GB this morning).
  - Suite: the full workspace suite for the candidate (`cargo test --workspace
    --locked --no-fail-fast`) has run since 10:47Z in the worktree
    `postfiatl1v2-dravlic` at `672b707c`; output goes to
    `~/.cache/suite-20261005/cargo-test.log`.
  - Corbanu: my Corbanu session was restarted once after an SSH drop froze its input.
    I skipped an update offer (0.1.44 → 0.1.48) so the shared binary stays as
    it is through the conference day.
- **Task Node.**
  - Release plan: `task_99181a776019491f8070ce6c0698d42d`, Rewarded.
  - Bridge operation: `task_2e3a14fe2f0ad6b89bfb9649e19503db`, Rewarded 3 PFT.
  - RPC budget: `task_85ea4a840c4a89bf11d65c570b6a1a1d`, Rewarded 3.2 PFT.
  - Committee tool: `task_6a3c5d67403aa4a873317a574f618db4`, Rewarded 2.5 PFT.
  - Dry run: `task_be9b64294772de67f21d787cbfe6cfa8`, Rewarded (amount not
    shown).
  - Control-certificate commands: `task_b961ceeeecdbf7dc7bff8e5ea16f21df`,
    Rewarded 3 PFT.
  - This handoff has no Task Node task.

## Next decision or action

### My next steps, in order

1. **2026-10-06, the conference day; nothing live.**
   - Read the result of the full workspace suite.
   - Confirm the FastSwap control path on the live release from a validator
     host's local ledger (read-only) and read the final checkpoint id.
   - Wallet improvements on a StakeHub side branch (the stale readiness flow
     table, a read-only live-mode route check command), to merge on
     2026-10-07.
   - The release candidate list, with the suite in the background on the work
     server.
   - The dry-run follow-ups, including the membership note above, and my
     tooling.
2. **2026-10-07 and after.**
   - Merge PR #54 after its Orchard test.
   - Cut the release branch from `main` and qualify it: two identical clean
     builds, history checks, a rotation and rollback rehearsal, a signed
     manifest and a packet.
   - Roll out one validator at a time with the safe-rollout tool.
   - Then the signer-group activation per the dry-run procedure: I run the
     validator signatures (`ActivateCommittee` by validators 0–4, the FastPay
     record by all six) and prepare the bridge update for the other lane's
     issuer key.
   - The relay units go in a window of their own; the plan keeps them out of
     the release.
3. **After the release:** the SCT-06 traffic campaign on the devnet (about
   3 h, test PFT).

### Only the other lane can provide

Each item shows the date first asked.

- **(a)** The two NEAR Intents design questions ([note][near]). 2026-09-29.
- **(b)** NAVCoin signer keys and custody rows ([inputs][z3]). 2026-09-22.
- **(c)** The Arc route step. Epoch 11 is done, but the Arc custody row is
  still missing (see above). 2026-09-28.
- **(d)** A compatible governed NAV profile with fresh proofs for A666.
  2026-09-22.
- **(e)** StakeHub custody Q1. 2026-09-07.
- **(f)** Reserve-proof successor adoption ([PR #49][pr49]). 2026-09-24.
- **(g)/(n)** Validator-5: now an objection window until 2026-10-07 evening
  UTC instead of a letter, plus one issuer signature for the bridge update
  once the release is live. 2026-09-25 / 2026-10-01.
- **(h)** The height-915 archive and the height-924 custodian. 2026-08-30.
- **(i)** The AI-governance decision for Gate Zero Z2. 2026-09-03.
- **(j)** The six inventory rows needing an operator decision
  ([inventory][inventory]). 2026-09-10.
- **(k)** Disk items on the validators. 2026-09-28.
- **(l)** The `ETHEREUM_MAINNET_RPC_URL` repository secret. 2026-09-28.
- **(m)** The cap values. 2026-09-29.
- **(o)** Permission to delete the other lane's old caches on the work server
  (~200 GB). 2026-10-01.
- **(p)** A window for the relay units, outside the release. 2026-10-01.
- **(q)** FW-13 and FW-14. 2026-09-30.

## References

- [The other lane's 2026-10-01 handoff][nazgul]; my [2026-10-02
  handoff][previous].
- Commits on `main`: `ab4ec9ee`, `9e4d80be`, `8d1c9c20`, `e3bb0dbf`,
  `a683475a`, `78c7b2e9`, `df347288`, `672b707c`.
- [`docs/plans/active/next-validator-release-plan-20261005.md`][plan].
- [`docs/review/signer-committee-rotation-dry-run-20261005.md`][dryrun].
- [`docs/runbooks/fastpay-committee-recovery.md`][runbook].
- [`docs/review/validator-5-signer-committees-decision-proposal-20261001.md`][v5].
- [`docs/status/chain-state-current.md`][state].
- [PR #54 review comment][pr54c].

[nazgul]: 2026-10-01___nazgul__navcoin_create_and_swap_build_phase0_and_bmnrc_opening.md
[previous]: 2026-10-02___dravlic__bmnrc_protocol_check_inventory_rows_closed_and_decisions_taken.md
[plan]: ../plans/active/next-validator-release-plan-20261005.md
[state]: ../status/chain-state-current.md
[weekend]: ../status/chain-state-current.md#2026-10-05-weekend-state-before-the-other-lanes-conference-day
[runbook]: ../runbooks/fastpay-committee-recovery.md#preparing-the-next-committee
[spec]: ../navcoins/navcoin-create-and-swap-spec.md#rotating-the-routes-ethereum-bridge-committee
[fsccmd]: ../navcoins/pftl-tools.md#fastswap-control-certificates
[rpcpol]: ../runbooks/public-rpc-operator-policy.md
[dryrun]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/review/signer-committee-rotation-dry-run-20261005.md
[v5]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/review/validator-5-signer-committees-decision-proposal-20261001.md
[shr]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/review/stakehub-safety-repairs-review-20260922.md
[inventory]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/review/defect-inventory-20260910.md
[z3]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/status/z3-cycle1-inputs-20260922.md
[near]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/specs/near-intents-architecture-research-20260929.md
[preflight]: https://github.com/postfiatorg/postfiatl1v2/blob/main/deployments/combined-fastpay-20260928/demo-preflight.py
[pr49]: https://github.com/postfiatorg/postfiatl1v2/pull/49
[pr54]: https://github.com/postfiatorg/postfiatl1v2/pull/54
[pr54c]: https://github.com/postfiatorg/postfiatl1v2/pull/54#pullrequestreview-5412107296
[tmr3104]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/types/src/transactions_mempool_receipts.rs#L3104-L3187
[tmr3630]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/types/src/transactions_mempool_receipts.rs#L3630
[tmr3800]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/types/src/transactions_mempool_receipts.rs#L3800
[tmr3883]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/types/src/transactions_mempool_receipts.rs#L3883
[tmr3942]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/types/src/transactions_mempool_receipts.rs#L3942
[tmr4021]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/types/src/transactions_mempool_receipts.rs#L4021
[tmr4159]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/types/src/transactions_mempool_receipts.rs#L4159
[cc71]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/types/src/core_chain.rs#L71-L72
[mnat]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/types/src/market_nav_asset_types.rs#L3376
[nv5640]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/execution/src/nav_vault_asset_execution.rs#L5640-L5742
[ne3006]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/execution/src/nft_escrow_asset_execution.rs#L3006-L3016
[bf1464]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/node/src/block_finality.rs#L1464-L1472
[cao378]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/node/src/main_parts/certified_asset_ops.rs#L378
[rv3088]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/rpc_sdk/src/response_validation.rs#L3088-L3096
[pr48]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/rpc_sdk/src/protocol_requests.rs#L48
[builder]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/scripts/a666-build-route-epoch-advance.py#L87-L171
[puev380]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/execution/src/pftl_uniswap_ethereum_verification.rs#L380
[ft177]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/types/src/fastswap_types.rs#L177
[ft197]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/types/src/fastswap_types.rs#L197
[ft802]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/types/src/fastswap_types.rs#L802-L910
[fsc97]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/execution/src/fastswap_control.rs#L97-L135
[fsc167]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/execution/src/fastswap_control.rs#L167
[fsc386]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/execution/src/fastswap_control.rs#L386-L410
[fcs]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/node/src/fastswap_control_signing.rs
[bs2403]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/node/src/batch_snapshot.rs#L2403
[rsr17]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/node/src/rpc_serve_runtime.rs#L17
[g03]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/node/src/main_parts/cli_dispatch_parts/group_03.rs#L424-L457
[gov521]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/node/src/governance.rs#L521
[ca2842]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/node/src/consensus_artifacts.rs#L2842-L2926
[ca2928]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/node/src/consensus_artifacts.rs#L2928-L2990
[otr875]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/execution/src/owned_transfer_recovery.rs#L875-L899
[frn356]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/node/src/fastpay_recovery_node.rs#L356-L395
[orchardtest]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/node/src/tests/asset_orchard_issued_tests.rs#L720
[py1609]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/python/postfiat_rpc/client.py#L1609
[py1637]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/python/postfiat_rpc/client.py#L1637-L1639
[bf577]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/node/src/block_finality.rs#L577

## End of session (11:49 UTC)

Three of the 2026-10-06 items in "My next steps" above are done: the StakeHub
side branch, the FastSwap control path read and the suite result. For
2026-10-06, the release candidate list, the remaining dry-run follow-ups and my
tooling are left.

- **StakeHub wallet branch, merging on 2026-10-07.** Branch
  `wallet/readiness-and-route-check-20261005`, commit `9abec352`,
  [PR #21][sh21]. The PR is open against `master` and not merged. `master` is
  unchanged at `52eb686`, so the demo installs what it did before.
  - `pft bridge route-check [--json]` does the same proxy route fetch and relay
    readiness call as bridge-in. It then runs the same `parse_route` and
    `check_relay_readiness`. It prints a table and a verdict, and it exits 1 on
    a refusal. It sends, signs and reserves nothing, and it scrubs the
    configured proxy and relay tokens from its output.
  - The [live-funds readiness review][shready] now marks three sets of
    findings repaired: PT-04–07 (`eb7388d`), PT-08 (`52eb686`) and WB-11
    (`34aa078`). The open P3 list goes from 24 to 19. Item 3 names the command.
    Live mode still needs the $5 live qualification and Q1.
  - The demo runbook's live-mode section gains one sentence that names the
    command.
  - Tests: `tests/test_pft_mainnet_bridge.py` 49 passed (4 new); wallet suite
    215 passed.
  - The command has not been run against the real proxy. It covers the deposit
    relay readiness only.
  - Task Node `task_a8d6ae883ef748ec100718c4faf0d59d`: Rewarded 2.4 PFT.
- **Live FastSwap control path** (`770d5ca6`). The details are in the
  [dry-run note's section][fsread] and in [release plan][plan] item 5. The same
  commit corrects the [proposal][v5]'s opening: both committees have six members,
  and validator-5's entry holds its stale key.
  - On validator-1 the FastSwap service does not open. Its local store
    `fastswap-v1.wal` has 26 records and was last written on 2026-07-23. The
    store uses the unkeyed checksum that the deployed release has refused since
    keyed integrity landed (`4dbd80c2`). Only `open_for_legacy_migration`
    ([`fastswap_store.rs:475`][fss475]) accepts that checksum, and no command
    calls it.
  - A `fastswap_*` RPC call tries to open the service. If the open fails, the
    call returns `fastswap_unavailable` ([`rpc_cli.rs:686-706`][rpc686],
    [`:1314`][rpc1314]).
  - Control admission for `StopPrepare` and `ActivateCommittee` runs on ledger
    state, without the service ([`mempool_proposals.rs:736-835`][mp736],
    [`fastlane_primary.rs:205-215`][flp205]). Only the final-checkpoint votes
    need the service.
  - Committee epoch 1 lists validators 0–5 with quorum 5 and root
    `a2eebcba…`, which is the A666 policy root. The WAL holds no anchored
    checkpoint.
  - Release day therefore needs an offline conversion command for that store.
    It runs on each validator while that validator's units are stopped.
    Release day also needs a new gate before step 1:
    `fastswap_capabilities` and `fastswap_checkpoint_status` must answer on
    validators 0–4.
  - Disclosure: the two `fastswap_*` RPC reads at 10:53:21Z, before the
    handoff above, made the service write `fastswap-v1.lock` and
    `.integrity.key` into validator-1's `fastswap-v1/` directory. The host read
    at 11:30–11:33Z wrote nothing. It used only `systemctl`, `ls`, `stat`,
    `cat`, `jq` and `grep`.
- **Full workspace suite on the candidate.** It ran in worktree
  `postfiatl1v2-dravlic` at `672b707c`, from 10:47Z to 11:38Z, and exited 101.
  - It ran 84 test groups with one failure:
    `transport_batch_payload_tests::long_running_validator_service_requires_explicit_json_storage_acknowledgement`.
  - The test panicked at [`crates/storage/src/lib.rs:155`][lib155] because the
    integrity key `.postfiat/node0/.integrity.key` had mode 664.
  - The cause is a stale test artifact in that worktree,
    `crates/node/.postfiat/node0/.integrity.key`, dated 2026-08-31. Git ignores
    the file and does not track it. After I removed it, the test passed and
    recreated the key with mode 600 (rerun at 11:41Z: 1 passed).
  - So the candidate's suite is green apart from that environment artifact. As
    usual, qualification repeats the full run on the cut release branch. Log:
    `~/.cache/suite-20261005/cargo-test.log`.
- **CI on `main`** (`gh run list`, 11:48Z).
  - `ab4ec9ee`, `a683475a`, `78c7b2e9` and `df347288`: `docs-build`,
    `rust-ci` and `product-security-ci` all succeeded.
  - `9e4d80be` and `e3bb0dbf`: `product-security-ci` failed, and the `rust-ci`
    `check` job failed, as described above. Their `rust-ci` `test` jobs passed.
  - `8d1c9c20`: `rust-ci` failed in its `test` job at 11:06Z. The failing test
    was `cobalt_shadow::tests::catch_up_rejects_malformed_batches_without_durable_mutation`.
    The same test passed in `rust-ci` on `a683475a`, `78c7b2e9` and
    `df347288`. It also passed in the local suite on `672b707c`. I have not
    investigated it yet. The plan requires CI to be green at the cut commit.
  - `672b707c` and `67d823e2`: `rust-ci` is still running.
  - `39180c08` and `770d5ca6`: `rust-ci` and `product-security-ci` are still
    running.
  - `docs-build` succeeded on every commit.
- **Nothing else changed after the handoff above.** Nothing changed on any
  host or on the chain. The only host access was the FastSwap read above.

[sh21]: https://github.com/postfiatorg/StakeHub/pull/21
[shready]: https://github.com/postfiatorg/StakeHub/blob/9abec3524244cd4921934c62990c452f39f10c09/docs/review/live-funds-readiness-20260929.md
[fsread]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/review/signer-committee-rotation-dry-run-20261005.md#live-fastswap-control-path-2026-10-05-read
[fss475]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/storage/src/fastswap_store.rs#L475
[rpc686]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/node/src/rpc_cli.rs#L686-L706
[rpc1314]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/node/src/rpc_cli.rs#L1314
[mp736]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/node/src/mempool_proposals.rs#L736-L835
[flp205]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/execution/src/fastlane_primary.rs#L205-L215
[lib155]: https://github.com/postfiatorg/postfiatl1v2/blob/672b707c2816ffa41d3340199a550b505f68b6dd/crates/storage/src/lib.rs#L155
