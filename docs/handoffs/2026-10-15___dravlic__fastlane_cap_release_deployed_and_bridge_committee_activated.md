# Fastlane cap release deployed and bridge committee activated

- **Operator:** Domagoj Ravlić (`dravlic`)
- **Date:** 2026-10-15 UTC
- **Responding to:** no handoff from the other lane since
  [its 2026-10-01 handoff][nazgul]. My previous handoff: [2026-10-14][previous].

## BLUF

Release `fastlane-cap-20261014` has run on all six validators since 11:03Z. With it,
I finished the bridge half of the signer-group switch on the chain: the drained
epoch-1 FastSwap checkpoint was anchored at height 1130, and bridge committee epoch 2
(validator-5 included) was activated at 1131. The A666 issuer update is prepared
unsigned for the other lane. The release carries the RPC size cap and receipt fix
(`7f9d0d98`), the rustls 0.23.46 advisory fix (#123) and the reviewed contributor
merges of 2026-10-13/14/15 (the plan's [already-on-main list][already]). Records:
the [release packet][packet], [sheet §7][sheet7] and [Current State][state]
(2026-10-15 section).

## Current state

- **Fleet.** Last observation: my read-only state read at 11:45:37Z
  ([after 7.3][after73]). All six run `fastlane-cap-20261014` at height 1131, tip
  `9b054f09…`, root `a12e7c5f…`, with empty mempools. Each host has 16–28 GB free
  ([after checks][afterchecks]). The 2026-10-13 relay units are active
  ([demo preflight][demo]). There was no live probe while writing this handoff.
- **Deployment boundary.**
  - Deployed: source `8bed9b90`, executable
    `b1b3dbb150d3596577df3bb3fe145103d90988cf71558c4d34a035fe4bb44405`, signed
    manifest `4f379c57b42c…`, publisher `pfc531e0…`. The manifest is verified on
    every host ([RELEASE-ID.txt][releaseid]).
  - Release branch `release/fastlane-cap-20261014` is at `78257b7a`. `main` was at
    `05736347` before this handoff.
  - Merged but undeployed: none. Since `8bed9b90`, `main` has only the record
    commits `58229844`, `932e148d` and `05736347`.
- **Cut and local qualification** (release `5163642c`, `main` `58229844`;
  [packet][qual]).
  - Two identical clean builds.
  - History replays of the 1115 and 1050 canaries and of the six original copies,
    each to its recorded root.
  - Rotation and rollback rehearsals on copies.
  - Size checks: the new RPC check accepted the real 70,944-byte anchor and a
    176 KB `ActivateCommittee`-sized input, and refused 262,145 bytes.
- **Rollout** ([rollout record][rollout]; release `0aa292a9`, `ddd5e120`; `main`
  `932e148d`).
  - Before state (`2970a301`): all six on `decaa411…` at 1123, tip `bafcc6ef…`,
    root `942d1fc2…`.
  - Signed canary backup (`de6eec20`, manifest `d957141e68a2…`): re-imported,
    then checkpoint and full replay verified at 1123.
  - Applies ran 10:38:19–11:03:35Z in the order validator-1, 0, 2, 3, 4, 5. After
    each, one 1-PFT grant (heights 1124–1129) was certified identically on all six.
    There was no divergence and no rollback.
  - `demo-preflight.py` at 11:07Z: READY, 60 PASS / 0 ATTENTION / 0 FAIL.
- **Bridge half of the switch** ([activation record][activation]; release
  `78257b7a`, `main` `05736347`).
  - Height 1130: the drained epoch-1 checkpoint (five fresh votes from validators
    0–4, 70,944 bytes) was anchored, tx `f34dd1f5…`, with
    `fastlane_checkpoint_anchored` on all six.
  - Height 1131: bridge committee epoch 2 was activated (the six current registry
    keys including validator-5, quorum 5, root `72836827f9f3…1da37`), tx
    `2b2efa37…`, with `fastlane_control_applied` on all six. A re-prepare now
    refuses because epoch 2 is active.
  - The unsigned `pftl_uniswap_route_bridge_policy_update` for the A666 route is
    at [`observed/a666-bridge-policy-update.unsigned.json`][update], sha256
    `24aa2e28ff942d0be9557416d2b796d6b9a8131abf7704c6ad1348539f51c03f`. It sets
    `authority_epoch` 2 and the epoch-2 root, and echoes the three policy fields
    read from the verified 1123 backup. Its `key_file` is a placeholder for the
    issuer to replace.
- **Signer groups.**
  - FastPay: committee epoch 2 (validator-5 included) has been installed since
    2026-10-12 at height 1123, valid from 10001.
  - Bridge: epoch 2 has been active on the chain since height 1131, root
    `72836827…`.
  - The A666 and BMNRC routes stay on authority epoch 1 until their issuer updates
    are signed. Until then, the epoch-1 committee (validators 0–4) keeps signing
    Ethereum checkpoints.
  - Two things remain on our side:
    - The FastSwap service's local committee file on validators 0–4 still holds
      epoch 1: `fastswap_capabilities` reports epoch 1, `enabled` false.
      Validator-5 answers `fastswap_unavailable`. Moving that file is a separate
      local step.
    - The BMNRC route needs the same issuer update.
- **Rollback.** For the executable, [`rollback-one.sh`][rollback] returns a
  validator to `signer-rotation-20261007` (`decaa411…`) with its data in place.
  The signed canary backup `d957141e…` is the fallback. The chain records at 1130
  and 1131 stay; the only correction is forward ([sheet §7][sheet7]).
- **Before the cut: supply-chain gate.**
  - Four rustls advisories published overnight (RUSTSEC-2026-0346…0349) made
    cargo-deny fail on `main`.
  - I reviewed and merged #123 (`Cargo.lock` → 0.23.46), #124, #125 and #126 (the
    tool lock pins and the pfUSDC prover public build recovery): `97bb4d35`,
    `cc297fa3`, `620c2bd2`, `ec0d898b`. Record: `09c4a630`.
  - The gate passed again on `ec0d898b`.
- **Contributor pull requests** ([triage table][triage]).
  - I reviewed and merged the bots' answers and the two new pull requests: #80
    `417d32b2`, #120 `bd434dd4`, #121 `4005a132`, #122 `a9bbf7c9`. Record:
    `8bed9b90`.
  - [#115][pr115] is merged into [PR #49][pr49]'s own branch (`f12b8d57`). #49's
    head moved, so a successor build from it has a different ELF and vkey than one
    from `670fa615`. The adoption of #49 stays with the other lane.
  - Every bot pull request is now merged or back with its author ([#95][pr95],
    [#103][pr103]).
  - citadelculture opened two drafts today: [#127][pr127] on #49's branch and
    [#128][pr128] on the release plan. Neither is marked ready.
- **CI on `main`.** I read `gh run list --branch main --limit 30` once at 12:00Z
  (ten commits, `ec0d898b` to `05736347`): 27 runs passed, none failed, and three
  were still in progress (`rust-ci` on `932e148d`, plus `rust-ci` and
  `product-security-ci` on `05736347`).
- **Devnet touched today.** Four actions, with no undo; the chain only moves
  forward:
  - the canary export on validator-1;
  - the rollout on all six, with six 1-PFT grants;
  - the anchor at 1130;
  - the `ActivateCommittee` at 1131.
- **Task Node.** Five tasks were Rewarded today (13.4 PFT):
  - `task_4bb2ccc6…`: the gate review;
  - `task_141e881b…`: the review of the answered and new pull requests;
  - `task_ec08d09a…`: the cut;
  - `task_e3c93955…`: the rollout;
  - `task_4053e393…`: the bridge activation.

  This handoff has no Task Node action.

## Next decision or action

### My next steps, in order

1. Move the FastSwap service's local committee file on validators 0–4 to epoch 2
   in a window of mine.
   - First I read the service code for the right procedure. It is a
     stopped-units step, like the 2026-10-12 store conversion.
   - Once the issuer update is applied, sign the next Ethereum checkpoint 5 of 6,
     with validator-5's current key.
2. Re-check #95 and #103 as their authors answer. New bot pull requests get the
   same full-read standard.
3. Make the transient 28703 relay units and validator-1's 28701 unit proper units.
4. Close the open review findings:
   - the `pft_to_atoms` rounding gap;
   - the `cobalt_handoff` fixture temp-directory name;
   - the reuse-of-request-id check missing on the WebSocket path.

### Only the other lane can provide

I ask the other lane for the following; each shows the date first asked.

- **(a)** NEAR Intents question 2 ([note][near]). 2026-09-29.
- **(b)** The NAVCoin signer keys and the cycle inputs ([inputs][z3]).
  2026-09-22.
- **(c)** The Arc source row on the A666 route. 2026-09-28.
- **(d)** A compatible governed NAV profile with fresh proofs. 2026-09-22.
- **(e)** StakeHub custody Q1. 2026-09-07.
- **(f)** The reserve-proof successor adoption and registration
  ([PR #49][pr49], now at `f12b8d57` with #115). 2026-09-24.
- **(g)** Validator-5. These two updates finish the switch:
  - One issuer-key signature and the submission of the prepared A666 bridge
    policy update ([file][update], sha256 above). The expected receipt is
    `route_bridge_policy_updated`.
  - The same update for the BMNRC route, from its issuer.

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

- My [2026-10-14 handoff][previous]; the other lane's
  [2026-10-01 handoff][nazgul].
- Release packet on `release/fastlane-cap-20261014`: [README][packet],
  [DEPLOY-SHEET][sheet], [RELEASE-ID.txt][releaseid], [qualification/][qual],
  [observed/][observed].
- Commits: release `5163642c`, `2970a301`, `de6eec20`, `0aa292a9`, `ddd5e120`,
  `78257b7a`; `main` `09c4a630`, `8bed9b90`, `58229844`, `932e148d`,
  `05736347`; the size-cap fix `7f9d0d98`.
- [Next release plan][next]; [validator-5 signer committees decision][v5];
  [signer committee rotation dry run][dryrun].
- [Current State][state].

[nazgul]: 2026-10-01___nazgul__navcoin_create_and_swap_build_phase0_and_bmnrc_opening.md
[previous]: 2026-10-14___dravlic__contributor_pull_requests_cleared_release_tomorrow.md
[state]: ../status/chain-state-current.md
[next]: ../plans/active/next-validator-release-plan-20261101.md
[triage]: ../plans/active/next-validator-release-plan-20261101.md#contributor-pull-requests-triaged-2026-10-12
[already]: ../plans/active/next-validator-release-plan-20261101.md#already-on-main-past-the-cut
[v5]: ../review/validator-5-signer-committees-decision-proposal-20261001.md
[dryrun]: ../review/signer-committee-rotation-dry-run-20261005.md
[inventory]: ../review/defect-inventory-20260910.md
[near]: ../specs/near-intents-architecture-research-20260929.md
[z3]: ../status/z3-cycle1-inputs-20260922.md
[packet]: https://github.com/postfiatorg/postfiatl1v2/blob/78257b7a7160fd69ae661ad2d9d85f6f44ba591d/deployments/fastlane-cap-20261014/README.md
[sheet]: https://github.com/postfiatorg/postfiatl1v2/blob/78257b7a7160fd69ae661ad2d9d85f6f44ba591d/deployments/fastlane-cap-20261014/DEPLOY-SHEET.md
[sheet7]: https://github.com/postfiatorg/postfiatl1v2/blob/78257b7a7160fd69ae661ad2d9d85f6f44ba591d/deployments/fastlane-cap-20261014/DEPLOY-SHEET.md#7-signer-group-activation-bridge-half
[releaseid]: https://github.com/postfiatorg/postfiatl1v2/blob/78257b7a7160fd69ae661ad2d9d85f6f44ba591d/deployments/fastlane-cap-20261014/RELEASE-ID.txt
[qual]: https://github.com/postfiatorg/postfiatl1v2/blob/78257b7a7160fd69ae661ad2d9d85f6f44ba591d/deployments/fastlane-cap-20261014/qualification/README.md
[observed]: https://github.com/postfiatorg/postfiatl1v2/tree/78257b7a7160fd69ae661ad2d9d85f6f44ba591d/deployments/fastlane-cap-20261014/observed
[rollout]: https://github.com/postfiatorg/postfiatl1v2/blob/78257b7a7160fd69ae661ad2d9d85f6f44ba591d/deployments/fastlane-cap-20261014/observed/rollout-record.json
[afterchecks]: https://github.com/postfiatorg/postfiatl1v2/blob/78257b7a7160fd69ae661ad2d9d85f6f44ba591d/deployments/fastlane-cap-20261014/observed/after-checks.json
[demo]: https://github.com/postfiatorg/postfiatl1v2/blob/78257b7a7160fd69ae661ad2d9d85f6f44ba591d/deployments/fastlane-cap-20261014/observed/demo-preflight-after.json
[activation]: https://github.com/postfiatorg/postfiatl1v2/blob/78257b7a7160fd69ae661ad2d9d85f6f44ba591d/deployments/fastlane-cap-20261014/observed/bridge-activation/bridge-activation-record.json
[after73]: https://github.com/postfiatorg/postfiatl1v2/blob/78257b7a7160fd69ae661ad2d9d85f6f44ba591d/deployments/fastlane-cap-20261014/observed/bridge-activation/state-7.3-after.json
[update]: https://github.com/postfiatorg/postfiatl1v2/blob/78257b7a7160fd69ae661ad2d9d85f6f44ba591d/deployments/fastlane-cap-20261014/observed/a666-bridge-policy-update.unsigned.json
[rollback]: https://github.com/postfiatorg/postfiatl1v2/blob/78257b7a7160fd69ae661ad2d9d85f6f44ba591d/deployments/fastlane-cap-20261014/rollback-one.sh
[pr49]: https://github.com/postfiatorg/postfiatl1v2/pull/49
[pr95]: https://github.com/postfiatorg/postfiatl1v2/pull/95#issuecomment-6167713335
[pr103]: https://github.com/postfiatorg/postfiatl1v2/pull/103#issuecomment-6167713654
[pr115]: https://github.com/postfiatorg/postfiatl1v2/pull/115
[pr127]: https://github.com/postfiatorg/postfiatl1v2/pull/127
[pr128]: https://github.com/postfiatorg/postfiatl1v2/pull/128
