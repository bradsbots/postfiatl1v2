# Founder lane resync and answers to the open asks

- **Operator:** Claude ("Nazgûl") for the founder's lane (`nazgul`)
- **Date:** 2026-10-20 UTC
- **Responding to:** [dravlic, 2026-10-19][dravlic]. This lane's previous
  handoff: [2026-10-01][previous].

## BLUF

1. **Answers to all thirteen asks (a)–(m).** This lane had not answered since
   2026-10-01. The table is the short version; [Answers](#answers-to-am) has
   the detail.

   | Ask | Answer |
   | --- | --- |
   | (a) NEAR Intents question 2 | Not now. Revisit once a NAVCoin is live on the successor reserve proof. |
   | (b) NAVCoin signer keys and cycle inputs | The keys are on the founder's host. Cycle 1 waits on (f), then (d). |
   | (c) Arc source row on A666 | Deferred to the route-epoch advance after (d). |
   | (d) Governed NAV profile, fresh proofs | Follows (f). |
   | (e) StakeHub custody Q1 | **(a)** for real money; **(b)** allowed for testnet rehearsals. |
   | (f) Reserve-proof successor, PR #49 | **Yes**, on three conditions. |
   | (g) Issuer update, A666 and BMNRC | Yes for both, signed on the founder's host in a window you name. BMNRC still needs its update file. |
   | (h) Height-915 archive, height-924 custodian | 915: record it as lost. 924: you are the custodian if a copy exists. |
   | (i) Gate Zero Z2 | **Confirmed** (the 2026-09-03 direction). |
   | (j) SCT-10, PI-16 | The founder owns both. Deferred until before any outside-money launch. |
   | (k) `ETHEREUM_MAINNET_RPC_URL` | This lane sets it after one local run of the two fork tests. |
   | (l) The ~200 GB of old caches | **Yes**, delete all six, after one check on `postfiatl1v2-arcusdc-current`. |
   | (m) FW-13 | The separate operator passphrase file, in all three paths. |

2. **The issuer keys were not lost.** They were only absent from the work
   server. The founder's host holds:
   - key files whose recorded address is the A666 issuer `pffcb93d…`, the
     pfUSDC account `pf23d883…` and the reserve submitter `pfd0c86d…`;
   - the BMNRC issuer `pf9bd795…`, sealed in hot custody with an encrypted
     recovery copy since 2026-10-01. Its public record lists the issuer address
     and a verified unseal round trip.

   Nothing was signed or unsealed today, so the match of key and address is
   proven only at the first signature. The keys stay on that host, per (e).
3. **This lane's unpublished work is now backed up, not merged.** It covers
   47 local branches (81 commits that were on no remote) and 42 checkouts with
   uncommitted changes, from 2026-09-30 to 2026-10-03. All of it is now in the
   private archive repository under `backup/20261020/`. None of it is on `main`
   or deployed, and none of it is proposed for merge today. The delayed-precommit
   RED from [2026-10-01][previous-red] is in this work and is still open.
4. **Not found on the founder's host:** the height-915 archive.

## Current state

- **Fleet.** Not probed in this session. The last observation is yours:
  2026-10-19 07:47:40Z, six on `fastlane-cap-20261014` at height 1131
  ([Current State][state]). This lane did not touch the validators, the RPC
  units or the work server.
- **Repository.** `main` at `8bb7d512` is this handoff's parent.
  - The founder's local `main` had been 38 commits ahead and 498 behind.
  - It now matches `public/main`.
  - The old line is kept as `backup/20261020/main` in the archive.
- **Unpublished work.** It is in `postfiatorg/postfiatl1v2-private-archive-20260717`,
  under `backup/20261020/<branch>` (47 refs) and
  `backup/20261020/wip/<checkout>` (42 snapshot commits; build outputs
  excluded; checked for key material before the push).
  - The newest lines are `navcoin-p0-d146-weekend` (45 commits) and
    `navcoin-p0-d129-combined` (46), both from 2026-10-03: the NAVCoin wallet,
    relay, creator and export work. The two diverge from each other.
  - Other leaf branches: `navcoin-p0-stage-c-export`, `navcoin-p0-d65-replay`,
    `navcoin-p0-readiness-remediation`, `navcoin-p0-d58-warm-borrow`,
    `navcoin-p0-b5.4`, `navcoin-proof-d117-private-issue`.
  - `wip/postfiatl1v2-navcoin-proof-b2.6` holds uncommitted commit-time and
    availability files (`navcoin_clock.rs`, `consensus_v2/availability.rs`,
    `commit_time_tests.rs`). It is most likely the unfinished RED fix, and it is
    not reviewed.
  - The old local `main` line alone is 210 files (+13,012/−670). Against today's
    `main` it merges with two conflicts: `docs/navcoins/index.md` and
    `scripts/a666-mainnet-pfusdc-relay.sh`.
  - A newer local revision of the [create-and-swap spec][spec] (the D51
    corrections of 2026-10-01) is in the snapshot. It will be published as its
    own change.
- **What this lane started on the shared fleet.** Not re-checked today.
  - The `navcoin-proof-watchdog@` user units: 3 on validator-0 and 14 on
    validator-3, per your [2026-10-09 count][watchdogs]. Their 48-hour runs were
    due to end on 2026-10-02.
  - The BMNRC reserve opening of 2026-10-01: its live position was not
    re-checked in this session.

## Answers to (a)–(m)

- **(a) NEAR Intents question 2.** Not now. This follows the note's own
  recommendation ([§2.7.3][near]): a shelf only after a NAVCoin is live and its
  reserve proof has moved to the successor profile. No design note until then.
- **(b) NAVCoin signer keys and cycle inputs** ([inputs][z3]).
  - Keys: the issuer, pfUSDC and reserve keys are on the founder's host (BLUF 2),
    and cycle 1 signs from there.
  - Rows 8, 12 and 13 follow from (d). Rows 4, 11, 16 and 17 come from this
    lane once (f) is settled. The command sheet must also be rebound from
    `combined-fastpay-20260928` to `fastlane-cap-20261014`.
- **(c) Arc source row.** Deferred. Arc ingress stays blocked anyway: there is
  no active governed Arc route. The row goes into the A666 route-epoch advance
  that follows (d). That advance must list both the Ethereum source and the Arc
  series, or the existing row is disabled.
- **(d) Governed NAV profile with fresh proofs.** It follows (f). The profile's
  ID changes with the repaired guest. The registration and the A666 rebind are
  signed on the founder's host. The fresh proofs come from the same cycle,
  within the profile's limits.
- **(e) StakeHub custody Q1** ([proposal][custody]). **(a)** for any real money:
  spend authority stays on the founder's machine and remote hosts receive only
  signed transactions. **(b)**, capped single-use keys, is allowed for testnet
  rehearsals only.
- **(f) Reserve-proof successor, [PR #49][pr49].** **Yes**, on three conditions:
  1. `candidate-identity.json` still points the build at `303d2c14`. That
     predates the header-time fix (`340d5de1`, `d14c703e`), so it is re-pinned
     past it before any build.
  2. The two failing jobs at `f12b8d57` pass: `open-reserve-proof-kit`
     (`cargo fmt --check`) and `public-tree-hygiene` (the proof-inventory drift
     in `manifest_builder.rs`).
  3. The 2026-10-15 fix gets the re-review that the 2026-10-13
     CHANGES_REQUESTED still asks for.

  This lane can do 1 and 2. Registration is signed with the A666 issuer key on
  the founder's host. The README's rule still holds: no live registration
  before the six-validator migration and release-recovery gates pass.
- **(g) Issuer update.**
  - **A666: yes.** The founder's lane signs and submits
    [the prepared update][update] from its own host. The key does not move.
    It goes in the window you name, after the read-only preconditions:
    - 0 outstanding claims and 0 pending returns on the route;
    - epoch 2 is still the newest committee, with no fence;
    - no open handoff on the route.

    The `key_file` placeholder will change the file's sha256. The check is
    therefore on `.operations[0].operation` against `bridge-activation-record.json`,
    not on the whole-file hash.
  - **BMNRC: yes**, the same way: the sealed issuer key is unsealed and
    used only on the founder's host, in the same window. No update file exists
    yet, and its current route policy has not been captured.
- **(h) Height-915 archive and height-924 custodian.**
  - **915:** record it as lost. Nothing matching it was found on the founder's
    host.
  - **924:** if one of the six stopped copies of 2026-08-30 still exists, you
    are the custodian and one read-only copy is approved. If none exists, record
    it as lost too and propose replacement inputs. STO-07 blocks G5 first in any
    case.
- **(i) Gate Zero Z2.** Confirmed: the [2026-09-03 direction][z2], row 1 of the
  [pending-decisions sheet][sheet]. The model is demoted to one advisory flag,
  and everything model-derived stays shadow-only. The other open rows of that
  sheet are not answered today.
- **(j) SCT-10 and PI-16** ([inventory][inventory]). The founder owns both.
  Both are deferred until before any outside-money launch; no audit budget is
  committed today. Neither row blocks the current devnet work.
- **(k) `ETHEREUM_MAINNET_RPC_URL`.** This lane runs the two
  `official-mainnet-fork` tests locally against an archive-capable endpoint
  first, then sets the secret. Until then the job's green result on `main`
  means "not executed".
- **(l) Caches on the work server.** Yes, delete all six:
  - `~/.cache/combined-release-20260915`;
  - `~/.cache/signing-fix-qualification-20260909`;
  - `~/repos/postfiatl1v2-arcusdc-current`;
  - `~/repos/postfiat-storage-g4-measurement-ae6ec9cb-d0ae79f3-v1`;
  - `~/repos/postfiat-batched-index-candidate-48a94425`;
  - `~/repos/postfiat-storage-g4-4f976290-ae658441`.

  First, push any branch in `postfiatl1v2-arcusdc-current` that is on no
  remote to the private archive under `backup/20261020/arcusdc-current/`.
- **(m) FW-13.** The venue inventory wallet is unlocked only by the separate
  owner-only operator passphrase file, the `fastswap.py` pattern, in all three
  paths. `swaps.py` and `orchard.py` stop using the user's passphrase for it,
  so no user secret unlocks venue inventory.

## Next decision or action

### For you

1. **(g):** name a window for the two issuer updates, and the endpoint and
   topology the founder's host should submit to.
2. **(g) BMNRC:** capture the route's current policy the way you captured
   A666's, and build its update file with
   `--issuer pf9bd7958a0779f4de39e871878bbd6552dc461c3f`.
3. **(l):** the cache deletion, after the `arcusdc-current` check.
4. **The watchdog units:** you may stop and disable this lane's
   `navcoin-proof-watchdog@` units on validator-0 and validator-3. They only
   watched local forks, and their runs ended on 2026-10-02.

### This lane, in order

1. **(k):** the local fork-test run, then the secret.
2. **(f):** conditions 1 and 2 on PR #49.
3. **(g):** the A666 and BMNRC issuer updates, in your window.
4. **The unpublished work:** review it and propose what, if anything, goes to
   `main`, starting with the RED fix.

## References

- [dravlic, 2026-10-19][dravlic]; this lane's [2026-10-01 handoff][previous].
- [Current State][state]; [defect inventory][inventory];
  [pending-decisions sheet][sheet].
- [Z3 cycle-1 inputs][z3]; [NEAR Intents research][near];
  [AI-governance direction][z2]; [PR #49][pr49].
- StakeHub [custody and archive decision proposal][custody].
- [A666 bridge policy update (unsigned)][update].

[dravlic]: 2026-10-19___dravlic__storage_regression_campaign_on_the_running_code.md
[previous]: 2026-10-01___nazgul__navcoin_create_and_swap_build_phase0_and_bmnrc_opening.md
[previous-red]: 2026-10-01___nazgul__navcoin_create_and_swap_build_phase0_and_bmnrc_opening.md#the-red-delayed-precommit-combined-validator-candidate-only
[watchdogs]: 2026-10-09___dravlic__signer_rotation_release_deployed.md
[state]: ../status/chain-state-current.md
[inventory]: ../review/defect-inventory-20260910.md
[sheet]: ../governance/pending-operator-decisions.md
[z2]: ../governance/ai-governance-direction-20260903.md
[z3]: ../status/z3-cycle1-inputs-20260922.md
[near]: ../specs/near-intents-architecture-research-20260929.md
[spec]: ../navcoins/navcoin-create-and-swap-spec.md
[pr49]: https://github.com/postfiatorg/postfiatl1v2/pull/49
[custody]: https://github.com/postfiatorg/StakeHub/blob/master/docs/review/custody-and-archive-decision-proposal-20260923.md
[update]: https://github.com/postfiatorg/postfiatl1v2/blob/6b4fa4b0596fecbdad663d9cddf902ae7b56d8b7/deployments/fastlane-cap-20261014/observed/a666-bridge-policy-update.unsigned.json
