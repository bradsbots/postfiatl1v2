# NAVCoin Create and Swap: Phase 0 closing, Phases 3–5 verified, BMNRC opening

- **Lane:** the founder's lane. Claude ("Nazgûl") directs three Codex build agents ("orcs") on this server.
- **Window:** 2026-09-30 ~17:00 UTC to 2026-10-01 03:35 UTC. First pushed at 02:04 UTC; this revision adds the [03:35 UTC update](#update-0335-utc).
- **Responding to:** [dravlic, 2026-09-30](2026-09-30___dravlic__fastpay_resume_repaired_wallet_caps_and_log_checks.md).

## BLUF

The founder asked for a NAVCoin product that an investor can use end to end:

- create a stock-plus-perp NAVCoin;
- prove its reserve;
- buy and sell it at NAV on PFTL;
- bridge it to Ethereum and Uniswap;
- swap it privately.

That product is now specified, and most of it has been built and verified on devnet forks and on Ethereum mainnet with small amounts. The first real NAVCoin, BMNRC (long BMNR stock on Felix, short `xyz:BMNR` on Hyperliquid), is being opened tonight with Post Fiat's own money. State at this handoff:

- **The plan.** [`docs/navcoins/navcoin-create-and-swap-spec.md`](../navcoins/navcoin-create-and-swap-spec.md) is in this push. It has phases B0–B7 with acceptance evidence for every item. Its TIH score is 86.9.
- **Phase 0 (platform).**
  - **Done:**
    - B0.0, closure of the wallet-proxy security incident (redacted note: [`docs/security/SEC-20260930-01-closure.md`](../security/SEC-20260930-01-closure.md));
    - B0.4, a 1 USDC public-wallet deposit into the epoch-10 vault;
    - **B0.5, a full A666 ⇄ wA666 export and return round trip**;
    - B0.7, pfUSDC supply reconciled to the atom.
  - **In progress:** B0.1, the canonical wallet switch. Two attempts each rolled back automatically, so the public wallet is unchanged.
- **Phases 3–4 (executor and Ethereum stack): verified.** This used separate BMNRC perimeter keys: a live $20-capped open and close, plus 18 mainnet-fork tests.
- **Phase 5 (wallet screens): accepted** for the operator demo, on fork evidence.
- **Phase 6 stage A: the BMNRC reserve opening is under way.**
  - The dedicated signer is live under a hash-pinned policy, and the founder's lane is the operator for the live transfers and trades.
  - Done so far: the source allowlist append and the first funding transfer (383.98 USDC to the Felix reserve).
- **One confirmed RED:** in the *unreleased* combined validator candidate, a delayed precommit lets a stale NAV buy commit. **Production `c93b2137` is not affected.** The candidate is not releasable until it is fixed. Details are below.

## What this lane did on the shared fleet (please read)

Everything here was bounded, preflighted and recorded. No validator process was restarted, no release changed, and nothing was reset.

- **Ethereum checkpoint signing, B0.5 export.** Validators 0–4 each ran the existing `c93` CLI `ethereum-checkpoint-vote-sign` once, for one exact Ethereum receipt (block 26094220), and the votes were assembled into a quorum-5 certificate.
  - This writes one new anti-equivocation record per signer under `ethereum-checkpoint-signing/`.
  - Key-free backups were taken before each signature and were never restored.
  - Validator-0 signed first as a canary; after it, height and root were identical on all six and resident PIDs were unchanged.
  - The return leg did the same at Ethereum block 26094365, using `127.0.0.1:28703` on validators 1–4 (see the [update](#update-0335-utc)).
- **Validator-5 is not in the bridge signer set.** Its checkpoint public key does not match the governed bridge `authority_epoch 1` committee: its hash is `aad48519…`, and the committee expects `b8d197ab…`. It took part only in read-only checks. This matches the earlier "validator-5 is not an eligible FastPay signer" finding in [the r4 handoff](2026-09-25___postfiatchad__r4_view_recovery_chain_unstuck.md). It is worth a deliberate decision before the bridge committee is next rotated.
- **Watchdog user services on the validator-0 and validator-3 hosts (B2.4).**
  - These are user-level systemd units with linger enabled. They watch three local quiet-chain forks over private SSH reverse forwards. They are not the production validators, and they do not touch them.
  - Original validator and RPC PIDs and start times were re-checked after every change.
  - The 48-hour runs end on 2026-10-02 at about 22:17 UTC. Please leave them running.
- **Chain height moved.** You last saw 1064; the chain is now at 1078. Every block from 1065 on is an operator test from this lane:
  - Trade, 1065–1067;
  - deposit propose/finalize/claim, 1068–1070;
  - withdrawal burn, 1071, with settlement at 1072;
  - export issue and source;
  - return import at 1077 and redemption at 1078.

  All of them have accepted receipts and the same root on all six validators.
- **Wallet proxy and public wallet.** These were redeployed several times. Each time all jobs were terminal, the operator's edits to the start script were preserved, and an availability check was made from the public URL afterwards. The StakeHub pfUSDC agent (the long-running signer) was **not** restarted or re-keyed. Its only change is one exact destination-allowlist append for the BMNRC Felix reserve at 03:08Z (see the [update](#update-0335-utc)).
- **GPU.** Two proof-only sessions ran on the already-owned Vast instance 53579074, each capped at $1. The instance is confirmed stopped.

## On your 2026-09-30 changes

- **FW-04 (resume a FastPay send without double-signing):** thank you. This lane's NAVCoin flows run through the public wallet proxy and a separate BMNRC executor, not `pft`. The pinned SDK copy does not affect them. The `pft` resume path is now what the founder's own runs should use.
- **FW-09 caps:** these do not collide with this lane's work.
  - The `pft` caps are `limits.pft_run_atoms` at 100 PFT and the $5 per run / $50 per campaign USD caps.
  - This lane's tests use their own caps, $20 per flow and $50 per phase, inside the proxy and executor.
  - The BMNRC launch is sized per the spec's capital plan, about $1,666 of Post Fiat cash in total, and is enforced by the BMNRC signer's own hash-pinned policy.
  - Nothing in this lane goes through `pft` with amounts that would trip your caps.
- **Event-log rotation:** noted. The checkpoint CLI runs above wrote only to `ethereum-checkpoint-signing/` and job directories; no log was touched.
- **P3 sweep:** noted. The three items you left (FW-13 venue wallet passphrase, FW-14 a651 staying shielded, PT-08 default signer build) are still founder decisions, and this lane did not touch them.
- **Full-history replay.** The PROOF agent imported the signed ce22 archive at height 1033 and replayed it through full history. It reproduced the exact root and all active NAV profiles under both deployed `c93` and the candidate. This is new evidence for the "full-history replay fails at block 1011" note, but only for that archive and source pair. It says nothing about a fresh h1075 archive.

## Phase-by-phase state

| Phase | State | Evidence and notes |
|---|---|---|
| **B0.0 incident** | DONE | A 1 USDC public-URL withdrawal paid out, Ethereum `0x0eac6e0c…a21f`, and settled natively at 1072, with replay rejected. Operator gas reconciled 39/39 transactions since Aug 13, with zero unexplained. Logs before the fix cannot show who called, and the closure note says so. |
| B0.1 canonical wallet | Switching | Both switch attempts (02:59Z and 03:15Z) failed their checks and rolled back automatically. The causes were a stale interpreter pin, then a test-harness timeout after three accepted Trade receipts. The public wallet is unchanged. |
| B0.2 fleet provenance | Done (read-only) | The live build is `c93b2137` on `release/combined-fastpay-20260928`. Consensus changes are built on that exact source. |
| B0.3 creator credential | Prepared | It is separate from wallet sessions and is activated with the Phase 5 integration. |
| **B0.4 pfUSDC ingress** | DONE (operator scope) | Ethereum `0x897d34ed…806a`, then PFTL 1068–1070. `live_value_enabled` stays false and unrestricted public deposits stay off. |
| **B0.5 export/return** | DONE | Export: mint `0x3070a3a3…2fab`. Return: burn `0x2368e691…e5bb` (Ethereum 26094365), native import at 1077 and redemption at 1078. Both certificates used validators 0–4. Supply invariant PASS. |
| B0.6 stranded funds | Draft | Epoch-5 holds 195.03 USDC and is impaired; epoch-6 holds 14.08 USDC. Refreshed from two RPCs. |
| **B0.7 supply** | DONE | 303,767,735 = deposits 531,110,901 − burns 227,343,176 + 10. Zero unexplained. |
| B0.8 signer budget | Package ready | Needs one planned StakeHub agent restart with the founder's unlock. It gates outside money only. |
| B0.9 trusted TLS | Prepared | Waits for B0.1. |
| B1.x reserve proof | Built, synthetic PASS | `sp1-nav-reserve-v1` binds profile, epoch, source and mandate with an exact N floor, and **`c93` already enforces this**. A GPU three-source proof gave V = $55 exactly. Live collection waits on the BMNRC opening and a reserve-checkpoint HOLD. |
| B2.1–B2.4 tooling | Built | Wallet builders reproduce the A666 v2 ops byte for byte, and the served WASM signs all 12 cases. The large-proof fee quote needs no validator change. Real 4-hour and 48-hour quiet forks are running. |
| B2.5/B2.6 consensus | **RED** | See below. |
| **B3.x executor** | DONE | Separate BMNRC keys and signer, with no StakeHub agent routing. Live $20-capped open and close: Felix `0x089e8fbf…ceaf` and `0x98bc6079…2604`; Hyperliquid opened 0.56 BMNR and closed it, leaving zero residual. |
| **B4.x Ethereum stack** | DONE (fork) | 18/18 mainnet-fork tests and 148/148 regression tests. Nothing is deployed to mainnet yet. |
| B5.x wallet | Accepted (scoped) | The seven-step Create flow, buy/sell and a browser-signed shielded buy all ran on a six-validator `c93` fork. 87-pair universe. |
| B6 stage A | In progress | 570.39 USDC moves from 0x1455's Ethereum USDC to the BMNRC perimeter. One $400 fee-inclusive Felix ticket is hedged isolated at 2x. Entry gates: basis ≤ 15 bps and liquidation distance ≥ 25%. Steps 1–2 of 17 are done; see the update below. |

## The RED: delayed precommit (combined validator candidate only)

- **Reproduction.** On a six-validator fork with real elapsed time, a buy was proposed while its proven observation was fresh. Its precommit requests were held until after the four-hour expiry. Six new precommit votes then certified it, and it was accepted on all six validators with an observation age of 4 h 0 m 39.7 s.
- **Production is unaffected.** `c93` has no clock gate, and the operator demo relies on calendar pauses plus the watchdog.
- **What it blocks.** The candidate (`7195ab37…`) **must not be released**. B2.6, consensus-enforced freshness, is an outside-money gate.
- **The fix being built.** Bind freshness to a quorum-certified commit time together with the executed root; reject stale NAV orders at execution; and pair a bounded precommit refusal with safe locked-QC / next-view recovery, so a refusal cannot wedge the chain. The same probe becomes the regression test.

## Still with the founder

- **Your list from yesterday is unchanged by this lane:**
  - the NAVCoin keys and the Arc route step for the first cycle;
  - the two StakeHub letters;
  - the reserve-proof answer;
  - the two archive files;
  - the governance decision;
  - the two NEAR Intents design questions.

  On the reserve proof: this lane's B1 work shows that `c93` already binds profile, epoch, source and mandate, and enforces the exact N floor, for `sp1-nav-reserve-v1` profiles. That may answer part of the question. The NAVCoin keys for BMNRC issuance are created during Phase 6 stage B in the founder's browser wallet.
- **From this lane:**
  - B0.8, the one planned StakeHub agent restart, which needs the founder's custody unlock;
  - the reserve-checkpoint and owner-authorization HOLD for live BMNRC collection;
  - a final go/no-go on stage C (pfUSDC route buy, export, Uniswap band, keeper, investor walkthrough) once B0.1, B0.9 and the Phase 5 integration are live.
- **Unattributed book activity.** On StakeHub Hyperliquid 0x1455, a ~$10k `xyz:GOOGL` long / `xyz:AAPL` short pair was opened at 20:45 UTC through the StakeHub agent. It was not placed by this lane or its build agents. If it is yours, please note it.

## Where things live

Private working state stays off this repository:
- directives, decisions, HOLD files and evidence are under `~/repos/orc_directives/` on the founder's server;
- the incident record is private;
- work branches are local and unpushed: `navcoin-p0-*`, `navcoin-proof-*` and `navcoin-exec-*` worktrees.

This push contains this handoff, the spec, and its link from [`docs/navcoins/index.md`](../navcoins/index.md).

## Update (03:35 UTC)

### B0.5 is DONE, and one validator-host finding for you

- **Round trip.** The full A666 ⇄ wA666 round trip passed from the public wallet.
  - **Out:** an export mint of 1,000,000 atoms (`0x3070a3a3…2fab`).
  - **Back:** an Ethereum burn (`0x2368e691…e5bb`), native import at 1077 and public redemption at 1078.
  - **Supply:** the invariant holds at 31,518,438,511, and all six validators converged.
- **The return checkpoint hit a validator-host RPC limit.** Validator-1's `ethereum-checkpoint-vote-sign` failed twice with HTTP 403 through its default `127.0.0.1:28701`.
  - **Cause:** that endpoint fronts PublicNode, which now refuses archive `eth_getCode` at historical blocks without a personal token ("Archive requests require a personal token"). Block reads still succeed, which is why it first looked transient.
  - **Fix used:** the return certificate was signed by validators 1–4 using the existing `127.0.0.1:28703` (dRPC archive) through a CLI argument only. There was no host configuration change and no restart.
  - **Consequence for you:** any future checkpoint signing on the default `28701` will hit the same 403. You may want to repoint `28701` or set `28703` as the default.
- **Signing state.** Each of validators 0–4 now holds one export and one return checkpoint record under `ethereum-checkpoint-signing/`. Validator-5 was read-only throughout.
- **Chain height:** 1078. All six were on the same root at the last read.

### B0.1: two automatic rollbacks, public wallet unchanged

The planned switch (canonical proxy drop-in plus a Caddy reload) ran twice, and both times rolled back cleanly.

- **02:59Z:** the stale `python_sha256` pin in the canonical pNOK deployment config made the canonical proxy refuse to start. Only that private pin was refreshed.
- **03:15Z:**
  - the loopback and public read-only checks passed;
  - one bounded Trade returned three accepted receipts;
  - the harness then timed out waiting for the completion text, so D5 rolled back by design.

The Trade is being reconciled before a third attempt. There is no retry of paid flows.

### Phase 6 stage A: operator log

Steps run so far, by the founder's lane, through the dedicated BMNRC signer and the reviewed helper:

1. **StakeHub agent destination allowlist.** One `set_policy` through the running StakeHub pfUSDC agent appended the BMNRC Felix reserve `0xB4387c67…95B4` to its EVM destination whitelist.
   - All other fields, the $12k per-transaction and $100k daily caps, and the existing entries are unchanged.
   - The agent was not restarted. Check PASS.
2. **Felix funding.** 383.982678 USDC went from `0x1455…d8c0` to the Felix reserve (`0x687ce6bf…1d43`, Ethereum 26094687, status 1). The finalized check is pending.

**Provider change.** `eth.llamarpc.com` returned a persistent HTTP 525 during step 1's preflight, before anything was sent. The BMNRC runtime and helper now use `ethereum-rpc.publicnode.com` plus `eth.drpc.org`, with two-provider agreement still mandatory. The dedicated signer was restarted onto that runtime; the policy hash `c3409016…63eb7` is unchanged.

**Remaining steps:**
- register the Felix funding;
- 186.41 USDC to the cash EOA;
- the CCTP burn and mint to Arbitrum;
- the Hyperliquid bridge deposit and transfer to xyz;
- isolated 2x;
- quote gates;
- the Felix open plus hedge;
- the post-fill evidence for the PROOF reserve collection.

### Consensus candidate: the D12 fix is still in design

The first fix for the delayed-precommit RED added a time-precommit stage, but **ordinary finality precommits still signed after expiry**, as an actual 121-second six-store regression showed. So that design is also RED and must not be released.

- **Next design:** the freshness check goes inside the ordinary consensus-v2 finality-precommit signing path, with safe locked-QC / next-view re-proposal under a fresh clock certificate.
- **Evidence jobs still running:**
  - the original 4-hour delayed-finality probe, which signs late votes after 06:02 UTC;
  - the 48-hour fallback watchdog fork, which runs to Oct 3 02:09 UTC;
  - its read-only pause observer.

  Production `c93` is unchanged at height 1078.
