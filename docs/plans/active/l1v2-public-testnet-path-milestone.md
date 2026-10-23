# L1v2 Public Testnet Path

**Status:** Active — sequencing document; authorizes no deployment, devnet mutation, or launch
**Date:** 2026-08-30
**Task:** Task Node `task_510e7605cb2dff0dfd672b397d26f2a6`
**Basis:** [Storage scaling milestone](../completed/storage-scaling-milestone.md), [G4 first-pass handoff](../../handoffs/2026-08-30___postfiatchad__g4_first_pass.md), [Cobalt further evaluation](https://postfiat.org/posts/cobalt-further-evaluation/), Dynamic UNL roadmap (`dynamic-unl-scoring/docs/CurrentRoadmap.md`)

Each lettered gate that changes chain, fleet, or authority state requires its
own operator decision; this plan orders the work and names the decision
points, nothing more.

## Gate Zero — operator preconditions (recorded 2026-08-30)

**No community-facing step — genesis outreach (C3 execution), ratification
clients on operator machines (C4 deployment), any Phase D gate, or launch —
may start until all three are true.** Internal work (A, B, C1, C2, E, and
design-only portions of C3/C4) proceeds normally. Bars below are proposed
operationalizations; the operator may tighten or restate them.

- [ ] Z1 **Cobalt is live**: Cobalt-ratified transitions are the sole
      registry-change path on the running devnet with the qualified storage
      lineage (post-B3), and have processed real transitions — including at
      least one validator change — over a sustained window with zero
      overrides
- [ ] Z2 **AI-governance decision made and live**: the C2 shadow evaluation
      is complete, the model-authority decision (keep or demote) is recorded,
      and the decided configuration is what actually runs the fork's weekly
      production rounds. **Decision made 2026-10-20:** demote, per the
      [2026-09-03 direction](../../governance/ai-governance-direction-20260903.md),
      confirmed by the other lane ([answer (i)](../../handoffs/2026-10-20___nazgul__founder_lane_resync_and_answers_to_open_asks.md)).
      Live still needs ([execution plan](z2-advisory-flag-execution-plan-20261022.md)):
      - [ ] Pin the v2 sub-scorer in the round manifest (content hash and manifest section)
      - [ ] Specify the flag pipeline: typed `identity_flag` (`clear`/`flag`), pinned execution profile, two-owner byte-convergent replay
      - [ ] Build the strict entry profile as a versioned deterministic rule module with a Python mirror and fixtures
      - [ ] Wire the advisory flag: it only switches entry to the strict profile; divergent or missing output yields no flag
      - [ ] Keep flags and legitimacy scores `SHADOW_ONLY` until the recorded promotion gates pass
      - [ ] Run v2 beside the model for four weekly shadow rounds on the fork, then switch the production rounds to it
- [ ] Z3 **NAVCoin swaps work end to end** ([Z3 NAVCoin round-trip plan](z3-navcoin-roundtrip-plan.md); Z3 remains OPEN): full round trips
      (deposit → mint → swap → redemption) succeed repeatedly on the
      qualified lineage over a sustained window **without requiring any
      consensus upgrade during that window** — consensus-surface churn on
      NAVCoin paths must have stopped before strangers run the binary

## A — Finish offline storage qualification (G3 → G5): complete (2026-10-23)

- [x] G4 scaling PASS at candidate `d0ae79f3`, binary `9e82d928…8c80c`, report `e2cff9cd…999f` ([handoff](../../handoffs/2026-08-30___postfiatchad__g4_first_pass.md))
- [x] A1 *(operator, external)* Height-915 quarantine archive: **lost** (other lane, 2026-10-20, [answer (h)](../../handoffs/2026-10-20___nazgul__founder_lane_resync_and_answers_to_open_asks.md)). I propose the signed validator-1 canary archive at height 1123 (manifest `d957141e68a2…`, fully replayed 2026-10-15) as the replacement; reasons in [storage G3](../completed/storage-scaling-milestone.md#g3-exact-replay). Source-tree SHA-256 `724389ad583b36aa979b1497a8377babd724fa389686a2ee41765441f0934ee0`, signature PASS (2026-10-21, [storage G3](../completed/storage-scaling-milestone.md#g3-exact-replay)) Resolved 2026-10-22: the packager and verifier accept the 1123 canary as the replacement (`5c331e60`).
- [x] A2 *(operator, external)* Height-924 custodian named and one read-only copy approved (2026-10-20): I am the custodian; the six stopped copies of 2026-08-30 are on the work server (`~/.postfiat/deployments/storage-rollout-d0ae79f3`, `storage-rollout-10dd9f20`). Verifying both copies' manifest signatures is open in [storage G3](../completed/storage-scaling-milestone.md#g3-exact-replay); the replay waits for STO-07
- [x] A3 Run both exact replays against the frozen binary with `benchmarks/storage-scaling/run_replay_evidence.py`; bind receipts. 1123 half: done with the harness (2026-10-21): `--signed-archive-dir` mode (`2ebc7b13`), binary `eea96ba6…` (`store-handle-20261021`, source `86706699`), PASS at 1123, tip `bafcc6ef…`, root `942d1fc2…`; archive tree hash `724389ad…` before and after. Receipt `~/.cache/g3-1123-replay-20261021/receipts/height-1123-harness/receipts/height-1123.json`, SHA-256 `c172d31e…` ([storage G3](../completed/storage-scaling-milestone.md#g3-exact-replay)). 924 half: done with the harness (2026-10-22): `--legacy-source-dir` mode (`e8a962cd`), same binary, copy `storage-rollout-10dd9f20` validator-0, PASS at 924, tip `ebeb0e1e…`, root `0854bc47…`; counts, roots and ordered history equal the recorded 2026-08-30 manifest; independent `--verify-only` PASS with clone and target hashes unchanged; source tree hash `13ffe388…` before and after. Report `~/.cache/g3-924-replay-20261022/receipts/height-924-harness-redacted/replay-report.json`, SHA-256 `fa071f84…`, from the redacted re-run (harness `325afbdb`, no host paths; receipt `fa643375…`, `verify-only.json` `10dc5398…`). The first run's report `9e5e8f0f…` is superseded. Packet binding stays with A4
- [x] A4 Assemble the redaction-safe packet with `benchmarks/storage-scaling/package_packet.py`; run the offline verifier; milestone state becomes **OFFLINE QUALIFIED**. 2026-10-22: **not assembled**. No single source and binary covers G2–G4 and the replays (`8644f0af` against `86706699`), the verifier still requires the lost height-915 archive, and there is no six-clone migration report for the candidate. The state stays SELECTED. The gap list and owners are in [storage G5](../completed/storage-scaling-milestone.md#g5-offline-qualification-packet); the first item needs a decision from Post Fiat. Decided 2026-10-22: one build for everything — G1, G2 and G4 are re-run on the deployed binary `eea96ba6…` (source `86706699`, attempt 4, started today), where the replays already stand, followed by the 1123 verifier change, the six-clone rehearsal, the `verify-only.json` redaction and the packet, all ours. Gap 2 closed 2026-10-22: the packager and verifier accept the signed height-1123 canary in place of the lost 915 archive, with the 915+924 pair path unchanged; the rehearsal and the redaction remain before the packet. 2026-10-23: the
  six-clone rehearsal PASSES on `eea96ba6…`, from 924 through 934 (report
  `b2d78622…`). The packet is assembled and `storage_scaling verify` passes
  offline: `~/.cache/storage-packet-20261023/packet/`, checksum manifest
  `c99cf314…`, verifier output `892843a5…`. The state still does not become
  OFFLINE QUALIFIED. Five boxes stay open: G2's last, G3's last, G4D's three,
  G5's documentation box and the label itself
  ([storage G5](../completed/storage-scaling-milestone.md#g5-offline-qualification-packet)).
  A5 waits for them. 2026-10-23, later: all five boxes except the label are
  closed (`b055543c`, `475436b4`). Packet-r2 is
  `~/.cache/storage-packet-20261023/packet-r2/`, checksum manifest
  `8bc64e1d…`, verifier output `e396222b…`. OFFLINE QUALIFIED pending the independent review of the verifier acceptance changes of 2026-10-23.
  **Done 2026-10-23:** the review's changes are in `4d8d2a72` and the
  milestone is **OFFLINE QUALIFIED**. Packet-r3 is
  `~/.cache/storage-packet-20261023/packet-r3/`, checksum manifest
  `357f06ee…`, verifier output `e4fba47e…`.
- [x] A5 Retire [storage-scaling-milestone.md](../completed/storage-scaling-milestone.md) into `docs/plans/completed/` and refresh `docs/architecture/state-and-storage.md` concisely. Done 2026-10-23 in the same commit as this line

## B — Pre-deployment rehearsal and deployment decision (G6)

- [x] B1 *(operator)* Authorized and captured six distinct stopped validator-directory copies from the controlled devnet fleet (2026-08-30)
- [ ] B2 Run the six-clone migration rehearsal (`benchmarks/storage-scaling/run_migration_rehearsal.py`): **FAIL 2026-08-30** after all six exact height-924 rebuild/verify passes; the first height-925 round rejected superseded validator-registry history reapplication. 2026-10-23: the same script PASSES on the deployed `eea96ba6…` from 924 through 934, as the storage packet's rehearsal. G6's deployment-exact gate (signed units, RPC co-start, rollback to the old binary) is still open
- [ ] B3 *(operator decision)* Deploy a qualified lineage to the controlled devnet with pinned source/binary/data/activation/rollback identities; **blocked — do not deploy `d0ae79f3`**; verify any successor with a fleet receipt (`docs/status/chain-state-current.md` update)

## C — Validator story: fork community feeds the l1v2 registry

The PFT Ledger fork (51+ community validators, Dynamic UNL live) supplies the
operator population; l1v2 supplies the registry-as-protocol-state destination.

- [ ] C1 Complete Dynamic UNL governance verification G.6/G.7 and Evidence Transparency E.1 on the fork (`dynamic-unl-scoring/docs/CurrentRoadmap.md`)
- [x] C2 Run the deterministic sub-scorer shadow evaluation against frozen rounds 12–19 (per `dynamic-unl-scoring/docs/DeterministicFinalScore.md` method): complete 2026-09-01, all eight rounds — 2 cutoff flips (both stricter), UNL overlap 19–20/20 ([results note](../../governance/dunl-subscorer-shadow-eval-20260901.md), `benchmarks/ai-governance/dunl-subscorer-shadow-20260901/`); the *(operator decision)* keep or demote model authority was made 2026-10-20 (demote; tracked by Z2)
- [x] C3 Design the l1v2 genesis-registry proposal path: scored fork operators → proposed registry + template trust graph → Cobalt-checked ratification (Dynamic UNL Phase 3A/3B; `crates/consensus_cobalt/`, `docs/architecture/overview.md`): designed in [genesis-registry-proposal-path.md](../../architecture/genesis-registry-proposal-path.md) (2026-09-01, harness 88.93) — source artifacts, ML-DSA identity binding, proposed-registry schema and content hash, Cobalt-checked path with DGA bounds, verification story, `SHADOW_ONLY` boundaries, and work sequence; design only, execution stays Gate Zero-blocked
- [ ] C4 Extend the validator sidecar into the l1v2 ratification client (commit-reveal signature after deterministic round replay; `validator-scoring-sidecar`)

## D — Public-testnet eligibility gates

- [x] D1 Inventory the non-storage release gates: `SECURITY.md`, `docs/release-process.md`, open security items (`docs/security/`): inventoried in [`docs/status/release-gate-inventory.md`](../../status/release-gate-inventory.md) (21 gates: 4 DONE, 16 OPEN, 1 UNKNOWN)
- [x] D2 Public operator runbook: join, key custody (ML-DSA), sidecar, monitoring (`docs/runbooks/`, fork operator docs as template): published [`docs/runbooks/public-operator-runbook.md`](../../runbooks/public-operator-runbook.md) (2026-09-01) — seven operator journeys, commands verified against the current tree; steps an outsider cannot yet perform carry boxed gap notes naming the blocking inventory rows (3 custody, 6–8/10 per-release, 17 launch authority, 18 ops readiness) and milestone items (C3/C4, Gate Zero)
- [x] D3 Topology/independence thresholds for launch, reusing the fork's strict-gate machinery (placement preflight, concentration caps): proposed in [launch-topology-thresholds.md](../../architecture/launch-topology-thresholds.md) (2026-09-01) — concrete numbers for all five dimensions with cited fork rules, existing vs `new:` preflights named (placement preflight and L3 independence verifier are `new:`); every threshold awaits the operator's confirmation
- [ ] D4 *(operator decision)* Public-testnet launch — explicitly outside this plan's authority

## E — Mandate deliverables

- [x] E1 Python CLI: `testnet-path` status tool reading gate states from this document and the milestone registry; human-runnable (`python/postfiat_rpc/testnet_path.py`, tests `python/tests/test_testnet_path_status.py`; run `PYTHONPATH=python python3 -m postfiat_rpc.testnet_path`, with `--json` and `--markdown`)
- [x] E2 User-facing interface consuming the CLI output (docs/status page): generated [`docs/status/testnet-path.md`](../../status/testnet-path.md) via `--markdown`, listed in the mkdocs nav next to the current-state page
- [ ] E3 On completion, retire this document into `docs/plans/completed/` and refresh documentation

## Order and dependencies

A1/A2 are independent external inputs; A3–A5 follow either. B needs A
complete. C1/C2 and design work run in parallel with A and B. **Everything
that touches community operators is blocked by Gate Zero (Z1–Z3).** D needs
B, C, and Gate Zero. E1/E2 can start immediately.
