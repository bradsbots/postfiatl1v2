# Conference day two, Friday ready

- **Operator:** Domagoj Ravlić (`dravlic`)
- **Date:** 2026-10-08 UTC
- **Responding to:** no handoff from the other lane since
  [its 2026-10-01 handoff][nazgul]. Today is TOKEN2049 Singapore day two. My
  previous handoff: [2026-10-07][previous].

## BLUF

I kept conference day two clean like day one: no contact with the six
validator hosts or the chain, and no StakeHub `master` commit. The objection
window on the [validator-5 reinstatement][v5] closes this evening UTC
([plan][window]). At 10:51Z no objection had arrived: `origin/main` carries
only this lane's commits since the 2026-10-07 handoff, there is no new handoff
from the other lane, neither repository has a PR comment since 2026-10-01,
and the only PR updated since 2026-10-07 is #54, at its merge. Tomorrow, Friday 2026-10-09, is the release day of
`signer-rotation-20261007` if the window stays silent. The six operator
instructions are checked against the [deploy sheet][sheet] and corrected, and
a plain-language go-brief exists on my side. Small repository work today: the
[Z3 cycle inputs][z3] show the A666 route at epoch 11 (`774a6025`); the
[skeleton plan][next] for the release after `signer-rotation-20261007` is on
`main` (`335ee375`); StakeHub [PR #21][sh21] still merges cleanly, and its
full test suite is running in the background.

## Current state

- **Fleet and deployment boundary** ([Current State][state]). No live probe
  today or yesterday. Last known state: 2026-10-06 09:13Z, all six at height
  1115, READY WITH ATTENTION. Deployed: `combined-fastpay-20260928`
  (`1f8b332d…`, source `c93b2137`). Repository: `main` at `335ee375` before
  this handoff; `release/signer-rotation-20261007` at `b4d3ebde` (sheet dates
  corrected on 2026-10-06). Merged but undeployed: everything on `main` since
  `c93b2137`. Nothing on the hosts, the chain or StakeHub `master` changes
  before 2026-10-09. CI on `main` at the start of the day: all three workflows
  green on `51144786`, `bbe82032` and `54515003`.
- **Z3 cycle inputs** (`774a6025`). [Row 2][z3row2] now records the A666
  route at epoch 11: policy `32c970e9…`, valid heights 1110–10000, not paused,
  and the Ethereum pfUSDC source `2bae082a…` as its only custody row. The
  sources hold only the prefix of the policy hash, so the full hash must come
  from a fresh read before the inputs are sealed. The epoch-10 value stays as
  the value before block 1110. The other "epoch 10" lines ([:21][z3l21],
  [:95][z3l95]) concern the pfUSDC vault-bridge route and are correct. The
  lines that put A666 at NAV epoch 8 ([:27][z3l27], [:69][z3l69]) are stale,
  because NAV epoch 9 was finalized at blocks 1108–1109. Updating them is a
  follow-up.
- **Next release skeleton** (`335ee375`, [plan][next], listed in the
  [plans index][plans] below the current plan).
  - Already on `main` past the cut: `9d837bef` (PR #54); `51144786`
    (`account_tx` fallback window and the archive-scan regression test); the
    docs-only commits `e92b8157`, `0a136eaa`, `f3f2a1e1`, `bbe82032`,
    `54515003` and `774a6025`. Since the cut, the only Rust changes are in
    tests, so the validator software is unchanged.
  - Candidates:
    - draft [PR #47][pr47] (citadelculture, relative RPC child request spool
      path, issue #27; read path), which its owner must finish;
    - [PR #52][pr52] (JJ2203-theRealOne, relative data directories), which
      waits for #47;
    - the citadelculture drafts [#43][pr43]–[#46][pr46] (finality submit
      response check, node wrapper scripts, RPC probe across resolved
      addresses, monitor smoke with a sole proof warning; tooling), if their
      owner finishes them;
    - the Python fallback gaps (no atomic-swap rows; mis-numbered escrow, NFT
      and offer rows in blocks with swaps), owned by this lane;
    - the archive scan's "possibly incomplete" `truncated` flag, only if an
      exact flag is wanted;
    - the other lane's delayed-precommit fix, when it is pushed and reviewed;
      it changes consensus and needs its own qualification;
    - the testnet default of the RPC accept budget: the
      [operator policy][rpcpolicy] and [`postfiat-rpc.service.example`][sysd]
      still say 10000, while the [release generator][bs2403] uses 100000;
    - FW-13 and FW-14 (StakeHub, the other lane's), tracked only.
  - Not before: `signer-rotation-20261007` deployed and its activation done,
    CI green at the cut commit, and the full workspace suite run at the cut
    commit. Qualification and rollout follow the [current plan][plan], with
    `rollback-one.sh` going back to `signer-rotation-20261007`.
- **StakeHub [PR #21][sh21]** (`wallet/readiness-and-route-check-20261005`,
  head `9abec352`).
  - `git merge-tree` against `master` `52eb686` reports no conflicts, and the
    merge can fast-forward (1 ahead, 0 behind).
  - The full suite (5,521 tests) runs in an isolated copy with its own
    environment (`~/.cache/sh-pr21-20261008/`, started 10:36:41Z). At 10:52Z
    it was still running at 61 percent, with 42 failures and 39 skips so far
    and no summary yet. Whether the failures match the known set of 84
    environment-bound ones can be checked only when it ends.
  - The merge is planned for 2026-10-09, judged against the known failure set.
    The live StakeHub checkout is untouched.
- **Release-day preparation** (my side, outside the repository).
  - I re-read the six operator instructions for 2026-10-09 against the
    [deploy sheet][sheet] and the [release-day procedure][dryrun] and
    corrected two of them:
    - the store conversion now uses the sheet's order (validator-5, 0, 1, 2,
      3, 4), its `runuser` command and its backup path ([§7][sheet7]);
    - the activation step now names the sheet's 8.2 final-checkpoint votes and
      the FastPay commands, and keeps 8.5 for after the issuer's signature
      ([§8][sheet8]).
  - A go-brief for the operator lists:
    - the go words in order: backup ok, rollout ok, store ok, relay ok (only
      if the other lane's agents are idle on the hosts), activate ok, fastpay
      ok;
    - the time each step takes and what can be undone;
    - the drop order if time runs short: relays first, then the two
      activation halves, never the after checks.
- **Task Node.** No task today (documents and a test run only). The one
  network-proposed task for this account (the CorbanuTerminal Windows
  install-script fix) stays untouched. This handoff has no Task Node action.
- **CI on `main`** (`gh run list`, read once at 10:50Z).
  - `774a6025`: `docs-build` passed; `product-security-ci` and `rust-ci`
    running.
  - `335ee375`: two push runs of each workflow; both `docs-build` runs passed;
    `product-security-ci` and `rust-ci` running.
- **Work server.** 70 GB free. The suite's copy (under 1 GB) is deleted after
  the merge.
- **Devnet.** Not touched. StakeHub `master` unchanged at `52eb686`.

## Next decision or action

### My next steps, in order

On 2026-10-09. Each live step needs its own go on the day
([deploy sheet][sheet]).

1. Go/no-go reads: no objection from the other lane; six-way agreement; CI
   green on the release tip; the other lane's agents idle on the hosts.
2. Sections 1–4: the before state, the stage recheck, the fleet preflight, and
   the fresh signed canary backup from validator-1. Then the store conversion
   dry run on a copy of validator-1's store.
3. Section 5: rollout one validator at a time ([order][sheet5]: validator-1
   canary, then 0, 2, 3, 4, 5), with one grant each. Section 6: the after
   checks.
4. Section 7: the store conversion per host (validator-5, 0, 1, 2, 3, 4). The
   relay units only if the other lane's agents are idle (item p stays asked).
5. Section 8: the bridge activation by validators 0–4, with the unsigned
   `pftl_uniswap_route_bridge_policy_update` handed to the other lane; the
   FastPay record signed by the six validators below height 10001. Then merge
   StakeHub [PR #21][sh21] on the suite result, and update the records and the
   [plan][plan].

### Only the other lane can provide

Each item shows the date first asked.

- **(a)** The two NEAR Intents design questions ([note][near]). 2026-09-29.
- **(b)** NAVCoin signer keys and custody rows ([inputs][z3]). 2026-09-22.
- **(c)** The Arc source row on the A666 route; epoch 11 has only the
  Ethereum source. 2026-09-28.
- **(d)** A compatible governed NAV profile with fresh proofs for A666.
  2026-09-22.
- **(e)** StakeHub custody Q1. 2026-09-07.
- **(f)** Reserve-proof successor adoption ([PR #49][pr49]). 2026-09-24.
- **(g)/(n)** Validator-5: the objection window closes 2026-10-08 evening
  UTC; after the activation, one issuer signature for the bridge update.
  2026-09-25 / 2026-10-01.
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

- My [2026-10-07 handoff][previous]; the other lane's
  [2026-10-01 handoff][nazgul].
- Commits on `main`: `774a6025`, `335ee375`.
- [`docs/plans/active/next-validator-release-plan-20261101.md`][next].
- [`deployments/signer-rotation-20261007/DEPLOY-SHEET.md`][sheet] on
  `release/signer-rotation-20261007`.
- [`docs/plans/active/next-validator-release-plan-20261005.md`][plan].
- [`docs/status/z3-cycle1-inputs-20260922.md`][z3].
- [`docs/status/chain-state-current.md`][state].

[nazgul]: 2026-10-01___nazgul__navcoin_create_and_swap_build_phase0_and_bmnrc_opening.md
[previous]: 2026-10-07___dravlic__conference_day_one_release_day_prepared.md
[state]: ../status/chain-state-current.md
[plan]: ../plans/active/next-validator-release-plan-20261005.md
[window]: ../plans/active/next-validator-release-plan-20261005.md#communication
[next]: ../plans/active/next-validator-release-plan-20261101.md
[plans]: ../plans/README.md
[rpcpolicy]: ../runbooks/public-rpc-operator-policy.md
[z3]: https://github.com/postfiatorg/postfiatl1v2/blob/774a60259e0edef687097ac27582a425837bf13f/docs/status/z3-cycle1-inputs-20260922.md
[z3row2]: https://github.com/postfiatorg/postfiatl1v2/blob/774a60259e0edef687097ac27582a425837bf13f/docs/status/z3-cycle1-inputs-20260922.md#L57
[z3l21]: https://github.com/postfiatorg/postfiatl1v2/blob/774a60259e0edef687097ac27582a425837bf13f/docs/status/z3-cycle1-inputs-20260922.md#L21
[z3l95]: https://github.com/postfiatorg/postfiatl1v2/blob/774a60259e0edef687097ac27582a425837bf13f/docs/status/z3-cycle1-inputs-20260922.md#L95
[z3l27]: https://github.com/postfiatorg/postfiatl1v2/blob/774a60259e0edef687097ac27582a425837bf13f/docs/status/z3-cycle1-inputs-20260922.md#L27
[z3l69]: https://github.com/postfiatorg/postfiatl1v2/blob/774a60259e0edef687097ac27582a425837bf13f/docs/status/z3-cycle1-inputs-20260922.md#L69
[sysd]: https://github.com/postfiatorg/postfiatl1v2/blob/335ee375ed10bae2db3dfaf76fc3bfec842cda91/systemd/postfiat-rpc.service.example#L12
[bs2403]: https://github.com/postfiatorg/postfiatl1v2/blob/335ee375ed10bae2db3dfaf76fc3bfec842cda91/crates/node/src/batch_snapshot.rs#L2403
[v5]: https://github.com/postfiatorg/postfiatl1v2/blob/335ee375ed10bae2db3dfaf76fc3bfec842cda91/docs/review/validator-5-signer-committees-decision-proposal-20261001.md
[dryrun]: https://github.com/postfiatorg/postfiatl1v2/blob/335ee375ed10bae2db3dfaf76fc3bfec842cda91/docs/review/signer-committee-rotation-dry-run-20261005.md#live-procedure-for-release-day
[inventory]: https://github.com/postfiatorg/postfiatl1v2/blob/335ee375ed10bae2db3dfaf76fc3bfec842cda91/docs/review/defect-inventory-20260910.md
[near]: https://github.com/postfiatorg/postfiatl1v2/blob/335ee375ed10bae2db3dfaf76fc3bfec842cda91/docs/specs/near-intents-architecture-research-20260929.md
[sheet]: https://github.com/postfiatorg/postfiatl1v2/blob/b4d3ebdec4869bff40cbe26d8b26aec0fbc8e8a9/deployments/signer-rotation-20261007/DEPLOY-SHEET.md
[sheet5]: https://github.com/postfiatorg/postfiatl1v2/blob/b4d3ebdec4869bff40cbe26d8b26aec0fbc8e8a9/deployments/signer-rotation-20261007/DEPLOY-SHEET.md#L85
[sheet7]: https://github.com/postfiatorg/postfiatl1v2/blob/b4d3ebdec4869bff40cbe26d8b26aec0fbc8e8a9/deployments/signer-rotation-20261007/DEPLOY-SHEET.md#L121-L142
[sheet8]: https://github.com/postfiatorg/postfiatl1v2/blob/b4d3ebdec4869bff40cbe26d8b26aec0fbc8e8a9/deployments/signer-rotation-20261007/DEPLOY-SHEET.md#L144-L158
[pr43]: https://github.com/postfiatorg/postfiatl1v2/pull/43
[pr46]: https://github.com/postfiatorg/postfiatl1v2/pull/46
[pr47]: https://github.com/postfiatorg/postfiatl1v2/pull/47
[pr49]: https://github.com/postfiatorg/postfiatl1v2/pull/49
[pr52]: https://github.com/postfiatorg/postfiatl1v2/pull/52
[sh21]: https://github.com/postfiatorg/StakeHub/pull/21
