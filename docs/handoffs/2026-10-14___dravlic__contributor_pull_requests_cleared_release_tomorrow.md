# Contributor pull requests cleared and release tomorrow

- **Operator:** Domagoj Ravlić (`dravlic`)
- **Date:** 2026-10-14 UTC
- **Responding to:** no handoff from the other lane since
  [its 2026-10-01 handoff][nazgul]. My previous handoff: [2026-10-13][previous].

## BLUF

Today I cleared the contributor pull-request backlog to the same standard as
yesterday. I read every change in full, ran its tests, showed that they fail
without it, and wrote a verdict in the [triage table][triage]. The work covered
the three the bots had answered overnight (#63, #72, #79; the
[defect inventory][inventory] now reads Fixed 107 / Recorded, not fixed 1,
STO-04), the eleven larger ones from the 2026-10-12 triage, and the twelve that
arrived overnight from bradsbots and citadelculture (#109–#120). 21 are merged,
four are back with their authors with a reason, and #80 waits only for its CI
`test` job. No validator or host was touched today. Tomorrow I cut the release
`fastlane-cap-20261014` from `main` with the RPC size-cap fix and these merges,
install it on the six validators, and then run the bridge half of the
signer-group switch ([sheet §8.2–8.4][sheet8]), ending with the unsigned issuer
update for the other lane.

## Current state

- **Fleet.** Last observation: my read-only `observe-fleet.py` run this morning
  (09:50–09:59Z; not recorded in the repository). All six are on
  `signer-rotation-20261007` at height 1123, tip `bafcc6ef…`, root
  `942d1fc2…`; yesterday's 28701/28702 relay units are active. Nothing changed
  on any host today, and there was no live probe while writing this handoff
  ([Current State][state]).
- **Deployment boundary.** Deployed source `0fa55d0b`; release branch
  `69073c33`; `main` was at `fedd78ec` before this handoff. Merged but
  undeployed: everything in the plan's [already-on-main list][already].
  - Node behaviour now also changes in: the RPC size cap and receipt codes
    (`7f9d0d98`); rpc-serve strict params (#87, #89–#93); the child-dispatch id
    check (#56, #109); bounded index reads with `O_NOFOLLOW` (#62, #110); the
    Cobalt handoff rehearsal probes (#60, #63); swap timing and `latest_tx_id`
    order (#61); and the exact-quorum check in `crates/types` (#84).
  - The list named only #84 and #87/#89/#91/#92. This commit adds the rest, one
    line each, with the merge commits.
- **Contributor pull requests** ([triage table][triage]). Record commits:
  `7c48c16a`, `02e20d47`, `1e5a65ce`, `3d8bbb19`, `4c2a63b2`, `775f115c`,
  `fedd78ec`.
  - 21 merged: #63, #72, #76, #77, #79, #81–#85, #99, #109–#114, #116–#119.
  - Eleven small fix commits of mine on top:
    - stale RPC method inventory regenerated: `cf17b649` (#76, #77, #81),
      `e0ed867c` (#82), `43581283` (#83–#85);
    - request-file re-read: `3d8dd100` (#85);
    - a doc line: `4221e47f` (#99);
    - a >4,300-digit integer crash: `1d2eb113` (#113);
    - test scaffolding or debug output left by the author's own review setup:
      `864bfd6c` (#114), `9fe08cec` (#116, also the error wording), `6f74bcb7`
      (#117), `fe8ebe64` (#118);
    - a broken existing test stub: `5aa4de7b` (#119).
  - Back with their authors, each with a reason:
    - [#95][pr95]: a proposer-route parent pin that no document asked for.
    - [#103][pr103]: timeout caps tighter than the Node limit; #117 merged the
      right cap.
    - [#115][pr115]: a correct fix of the NEAR receipt-age authentication, but
      it targets [PR #49][pr49]'s own branch and changes the successor
      program's identity, and it has test debug leftovers to remove. Once it is
      cleaned I will merge it into that branch, since #49 is not built or
      registered yet.
    - [#120][pr120]: a timed-out finality poll must keep exit 0 and the result
      field, per the finality spec; a warning line is wanted instead.
  - [#80][pr80] (`vault_bridge_status` read): reviewed FIX-AND-MERGE. At 13:05Z
    every check except `test` had finished, and `test` was still pending, so it
    stays open. It merges as soon as `test` is green, with the inventory
    regenerated (its only `python-sdk` failure is the stale inventory row).
  - #121 and #122 (bradsbots) arrived while the last batch ran. They are
    unread and tomorrow's first re-check. By its title, #121 addresses the
    #101 stored-job finding.
- **Open findings from the reviews.**
  - The `pft_to_atoms` rounding gap (#100 row).
  - A `cobalt_handoff` test fixture temp-directory name (pid + nanoseconds)
    can collide under parallel runs. I saw it once today; the rerun was green.
  - #112's reuse-of-request-id check is absent from #114's WebSocket path.
  - After a deploy, a host env file with out-of-range `WALLET_PROXY_*` or
    boolean flag values would stop the wallet proxy (#96–#99). I have not
    checked the hosts.
- **CI on `main`.** I read `gh run list --branch main --limit 80` once at
  13:00Z (27 commits, `e0ed867c` to `fedd78ec`). docs-build passed on all 27,
  product-security-ci passed on 12 and failed on 3, rust-ci passed on 4, and
  the other 12 product-security-ci and 22 rust-ci runs were in progress.
  - The three failures (11:32–11:36Z: `3d8c4e9c`, `9157e7cd`, `3d8dd100`) are
    the RPC method inventory freshness test in `python-sdk`, on intermediate
    merge commits of #83–#85. The regeneration commits (`cf17b649`,
    `e0ed867c`, `43581283`) fixed them; `43581283` covers these three.
- **Devnet touched today:** none.
- **Task Node.** Seven tasks Rewarded today, one per batch (11.95 PFT):
  `task_2712658f…`, `task_89aec625…`, `task_38bd26f9…`, `task_3e682626…`,
  `task_735964a9…`, `task_eaefadc9…`, `task_90e0835b…`. This handoff has no
  Task Node action.

## Next decision or action

### My next steps, in order

1. Tomorrow, 2026-10-15: the release `fastlane-cap-20261014`.
   - First: #80 if its `test` job is green (then regenerate the inventory),
     and the re-check of #121 and #122.
   - Cut from `main`, two clean builds, local qualification, deploy sheet.
   - Before state and fleet preflight; a signed canary backup of validator-1
     with a full replay.
   - Safe-rollout one validator at a time (1, 0, 2, 3, 4, 5), with a grant
     each; then the after checks.
   - Then [sheet §8.2][sheet8] `AnchorCheckpoint`, §8.3 `ActivateCommittee`
     epoch 2 (root `72836827…`), and §8.4 the unsigned
     `pftl_uniswap_route_bridge_policy_update` for the issuer.
2. The four pull requests back with their authors, re-checked as they answer.
3. The open review findings above.
4. The transient 28703 relay units.

### Only the other lane can provide

I ask the other lane for the following; each shows the date first asked.

- **(a)** NEAR Intents question 2 ([note][near]). 2026-09-29.
- **(b)** The NAVCoin signer keys and the cycle inputs ([inputs][z3]).
  2026-09-22.
- **(c)** The Arc source row on the A666 route. 2026-09-28.
- **(d)** A compatible governed NAV profile with fresh proofs. 2026-09-22.
- **(e)** StakeHub custody Q1. 2026-09-07.
- **(f)** The reserve-proof successor adoption and registration
  ([PR #49][pr49]; [#115][pr115] improves its branch). 2026-09-24.
- **(g)** Validator-5: the issuer signature on the bridge policy update. It
  becomes possible after tomorrow's release admits the `ActivateCommittee`.
  2026-09-25 / 2026-10-01.
- **(h)** The height-915 archive and the height-924 custodian. 2026-08-30.
- **(i)** The AI-governance decision for Gate Zero Z2. 2026-09-03.
- **(j)** The inventory rows SCT-10 and PI-16 ([inventory][inventory]).
  2026-09-10.
- **(k)** The `ETHEREUM_MAINNET_RPC_URL` repository secret. 2026-09-28.
- **(l)** Permission to delete the other lane's old caches on the work server
  (~200 GB). 2026-10-01.
- **(m)** FW-13. 2026-09-30.

## References

- My [2026-10-13 handoff][previous]; the other lane's
  [2026-10-01 handoff][nazgul].
- [Next release plan][next]: [triage table][triage] with today's rows;
  [already-on-main list][already].
- `main` commits: the record and fix commits above; the size-cap fix
  `7f9d0d98`.
- [Defect inventory][inventory].
- [Deploy sheet §8][sheet8] (release branch, `69073c33`).
- [Current State][state].

[nazgul]: 2026-10-01___nazgul__navcoin_create_and_swap_build_phase0_and_bmnrc_opening.md
[previous]: 2026-10-13___dravlic__contributor_pull_requests_reviewed_and_relays_as_services.md
[state]: ../status/chain-state-current.md
[next]: ../plans/active/next-validator-release-plan-20261101.md
[triage]: ../plans/active/next-validator-release-plan-20261101.md#contributor-pull-requests-triaged-2026-10-12
[already]: ../plans/active/next-validator-release-plan-20261101.md#already-on-main-past-the-cut
[inventory]: ../review/defect-inventory-20260910.md
[near]: ../specs/near-intents-architecture-research-20260929.md
[z3]: ../status/z3-cycle1-inputs-20260922.md
[sheet8]: https://github.com/postfiatorg/postfiatl1v2/blob/69073c334c9a7a97511d2eb96fb9af69a52b8074/deployments/signer-rotation-20261007/DEPLOY-SHEET.md#L190-L244
[pr49]: https://github.com/postfiatorg/postfiatl1v2/pull/49
[pr80]: https://github.com/postfiatorg/postfiatl1v2/pull/80
[pr95]: https://github.com/postfiatorg/postfiatl1v2/pull/95#issuecomment-6167713335
[pr103]: https://github.com/postfiatorg/postfiatl1v2/pull/103#issuecomment-6167713654
[pr115]: https://github.com/postfiatorg/postfiatl1v2/pull/115#issuecomment-6168365415
[pr120]: https://github.com/postfiatorg/postfiatl1v2/pull/120#issuecomment-6168271203
