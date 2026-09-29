# NEAR Intents research, wallet flows reviewed and live-funds readiness

- **Operator:** Domagoj Ravlić (`dravlic`)
- **Date:** 2026-09-29 UTC

## BLUF

The other lane's homework is done. A research note on NEAR Intents and its
architecture is on `main` at
[`docs/specs/near-intents-architecture-research-20260929.md`][note]
(`6a0084db`, corrections `a8b87d68`, third round recorded `f22e4313`). It
scores 85.93 in the kept version, 0.07 below the 86 lock bar, so it is not
locked ([`docs/review/near-intents-research-scores-20260929.md`][scores]). It
ends with four recommendations and two design questions for the other lane.
For the other lane's live end-to-end runs tonight, StakeHub
[`docs/review/live-funds-readiness-20260929.md`][ready] (`0f139ac` on
`master`) lists per flow what is repaired and merged, what is open, and how to
run within the caps in the code. I then reviewed the four wallet modules no
earlier review covered, in StakeHub
[`docs/review/wallet-flows-review-20260929.md`][flows]: 2 P1, 7 P2 and 7 P3.
Six are repaired and merged as `6a79672` ([PR #18][pr18]). FW-04, FW-08 and
the spending-cap proposal FW-09 are open, and the cap decision is the other
lane's call before tonight's runs. Last, I installed a logrotate rule for
`transport-validator-events.ndjson` on all six validators, with no restart and
no chain action ([record][rotation], `4788ef1f`; [Current State][state],
`0eab3d86`). The last observed chain state is 2026-09-28T08:38Z, with all six
validators on `combined-fastpay-20260928`. The last observed host state is
2026-09-29T12:39Z.

## Current state

### NEAR Intents research note

- **Commits on `main`:**
  - `6a0084db`: the note.
  - `a8b87d68`: two quotation corrections and the score record. All 13 Part 2
    quotations were checked word for word against their cited pages.
  - `f22e4313`: the third improvement round's score. Its text was not kept.
  - The file on `main` is the r3 version, SHA-256 `90929d16…`.
- **Harness scores** ([`docs/review/near-intents-research-scores-20260929.md`][scores]):
  full gate, 5 runs per judge (`gpt-6-astra-pro`, `claude-fable-5.1`,
  `glm-5.3`). Improvement rounds were direct OpenRouter calls to
  `openai/gpt-5.6-sol-pro`.

  | Round | Document SHA-256 | Average | Kept |
  | --- | --- | ---: | --- |
  | r1, as written | `22a3404e…` | 83.73 | no |
  | r2, one improvement round (`6a0084db`) | `7fde1d9d…` | 85.00 | no |
  | r3, quotation corrections and a second round (`a8b87d68`) | `90929d16…` | 85.93 | yes |
  | r4, third round | `f20ed4c3…` | 85.53 | no |

  The note is below the 86 lock bar by 0.07 and is not locked. The per-judge
  scores and hashes are in the score record. Raw responses are outside Git in
  `~/pastedocs/.near-intents-research-20260929/`.
- **Part 1** is a plain-language brief: what NEAR Intents is, one swap step by
  step, why it is fast and cheap, where trust sits, the comparison with NAV
  swaps, what to borrow and what not to copy.
- **Part 2** is the architecture:
  - **§2.1 Components.**
    - The Verifier is `intents.near` (internal name Defuse). It holds a NEP-245
      multi-token internal ledger plus the intent execution engine and can be
      upgraded by its controller.
    - The Message Bus is an off-chain solver relay run by the protocol team as
      a single service. The protocol can operate without it.
    - Solvers are third parties holding inventory inside the Verifier.
    - The 1Click API is a REST layer for quote, quote-specific deposit
      address, execution and status.
    - **Omni Bridge** (Ethereum, Base, Arbitrum, BNB, Solana, Bitcoin): a
      Bridge Token Factory on NEAR, with outbound
      signatures from an MPC network (chain signatures).
    - **Proof-of-authority (PoA) bridge:** a validator set whose operator the
      docs do not name. Its chains include Bitcoin, Zcash, Tron, Sui, Aptos,
      Cardano, Starknet and others.
    - **HOT Bridge:** an MPC network with nodes from EverStake, NEAR Protocol,
      Aurora and HAPI.
  - **§2.2 Intent model.**
    - A payload carries `signer_id`, `verifying_contract`, a `deadline` and a
      256-bit `nonce`. The nonce is a 4-byte salt plus 28 bytes of unique
      data. Changing the contract salt invalidates old signatures wholesale.
    - `token_diff` intents in a batch must sum to zero per token, or the whole
      batch fails.
    - `execute_intents` executes and `simulate_intents` dry-runs. Execution is
      atomic within one call, but ordering across calls is not guaranteed.
    - Signing standards: NEP-413, ERC-191 and raw Ed25519 (docs); BIP-322 and
      TIP-191 (repository payload traits).
  - **§2.3 Message Bus JSON-RPC quote flow.**
    - `quote`: the bus forwards the request to all solvers and waits up to
      3 seconds. Quotes are valid for about 60 seconds (`min_deadline_ms`
      default).
    - `publish_intent` / `publish_intents` takes the signed payload with
      `quote_hashes`.
    - `get_status` reports `TX_BROADCASTED`, then `SETTLED` or
      `NOT_FOUND_OR_NOT_VALID`.
  - **§2.4 Custody and trust.**
    - Inside the Verifier, correctness is enforced by the contract. The assets
      themselves sit with the bridges.
    - Compliance: screening against TRM Labs, Binance AML, AMLBot and PureFi,
      plus a law-enforcement request channel.
    - An independent investigation (Indago Labs) documents use by illicit
      actors.
  - **§2.5 Fees and numbers.** These are the sources' figures; this lane
    measured none of them.
    - Fees: 1 bp protocol fee, plus 20–25 bps at the 1Click layer. Solvers are
      paid only by quote improvement.
    - Volume: about 4.49 billion USD in the 30 days to 2026-09-26, at a
      14.93 bps average (gross fees divided by volume).
    - More than 10 billion USD cumulative, and a TVL of 169 million USD.
  - **§2.6** compares NEAR Intents with the PostFiat NAV swap route and pfUSDC
    route side by side, across ten dimensions.
  - **§2.7 Four recommendations:**
    1. Keep proof-based custody as is.
    2. Study an intent-and-solver layer on top of the governed NAV route, not
       instead of it.
    3. Consider NEAR Intents as a distribution shelf for a NAVCoin only after
       the reserve-proof successor is live.
    4. Reuse quote expiry, requote-on-failure and quote-specific deposit
       addresses in the wallet.
- **Two design questions for the other lane** (end of Part 1; neither is urgent
  and neither needs money):
  1. Should the wallet's swap screen move to an intent-style flow on top of the
     existing proof-based route?
  2. Should NEAR Intents be studied later as a distribution channel for a
     NAVCoin listed there, with custody and proofs staying on PostFiat?

### StakeHub live-funds readiness note

- **Commit:** [`docs/review/live-funds-readiness-20260929.md`][ready] is
  `0f139ac` on StakeHub `master`, on top of `01db0f3`. It adds only that file,
  so its line references to `01db0f3` hold at `0f139ac`. I ran nothing for the
  note, and it approves no run.
- **Merged repairs, 2026-09-22 to 2026-09-28:**
  - R1–R3 (`36edc84`).
  - Twelve money-path findings: MP-01–06, MP-12–17.
  - Wallet bridge: WB-01–08, WB-10, WB-11 and WB-13.
  - Pay transfer and registry: PT-01–03 and PR-01.
  - September 22 review: SH-01, SH-02, SH-04, SH-05, SH-06, SH-09, SH-11 and
    SH-12.
- **Per flow:**

  | Flow | Verdict in the note | Still open |
  | --- | --- | --- |
  | FastPay payments and PFT transfers (devnet) | Can go first | PT-04–08, PR-02, PR-03, WB-16, WB-17; [`pft_wallet/fastpay.py`][fastpay] unreviewed |
  | Mainnet pfUSDC bridge in and out | Repaired, never touched mainnet; read-only route check, then one deposit and one withdrawal of at most 5 USD each, supervised | WB-09, WB-12, WB-14, WB-15, WB-18; WB-11 burn id unconfirmed; route check; live qualification; unattended-use hold |
  | NAVCoin swap | Capped at 5,000,000 atoms (5 USD of pfUSDC); last, with bridged dust, supervised | [`pft_wallet/swaps.py`][swaps] and [`pft_wallet/fastswap.py`][fastswap] unreviewed; live-mode swaps not exercised |
  | Private/shielded route | Not cleared for real money; devnet or `--demo` only | MP-07–11, MP-18–22; Q1, Q2; [`pft_wallet/orchard.py`][orchard] unreviewed; no one-way private A651 buy exists |
  | StakeHub venue and exchange flows | Not cleared for real money | MP-10; not an operational ETH-to-Hyperliquid release; Q1 |

- **Open P3 findings (24):**
  - Wallet bridge (7): WB-09, WB-12, WB-14, WB-15, WB-16, WB-17, WB-18.
  - Money path (10): MP-07–11, MP-18–22.
  - Pay transfer and registry (7): PT-04–08, PR-02, PR-03.
- **Other open prerequisites (12):**
  1. The WB-11 burn `tx_id` match is unconfirmed against a real burn.
  2. The "unattended use" hold stands until a live withdrawal confirms that id.
  3. Read-only route check. It confirms that `parse_route`
     ([`pft_wallet/mainnet_bridge.py:187`][mb187]) and `check_relay_readiness`
     ([`:248`][mb248]) accept the live route and readiness.
  4. Small live qualification: one deposit and one withdrawal within 5 USD.
  5. Custody Q1 (SH-03). With `--live`, the `pfeth_*` scripts still copy keys
     or notes to a validator host.
  6. Archive Q2 (SH-08).
  7. The rest of live mode (balances, FastPay, swaps) with the funded test
     wallet.
  8. Bridge-out (`submit_pftl_bridge_out`) needs a `postfiat-node` built before
     `b19ce4c8`. Current L1 `main` lacks `nav-roundtrip-live-demo`.
  9. Qualification and approval of the exact release and configuration.
  10. The private-funding work left in the sprint handoff.
  11. SH-07's 16 external archive records are not yet verified.
  12. Four never-reviewed modules: [`pft_wallet/fastpay.py`][fastpay],
      [`pft_wallet/swaps.py`][swaps], [`pft_wallet/fastswap.py`][fastswap] and
      [`pft_wallet/orchard.py`][orchard].
- **Caps in the code for tonight:**

  | Cap | Value and where it is set | Where it is enforced |
  | --- | --- | --- |
  | `limits.reserve`, per run | `run_usd = "5.00"`, [`pft_wallet/default_config.toml:102`][cfg102] | [`pft_wallet/limits.py:41-44`][lim41]; called before approval and deposit ([`pft_wallet/mainnet_bridge.py:599`][mb599]) and before the burn signature ([`:902`][mb902]) |
  | `limits.reserve`, campaign | `campaign_usd = "50.00"`, ledger `~/.pft/campaign-spend.jsonl`, [`pft_wallet/default_config.toml:103-104`][cfg103] | [`pft_wallet/limits.py:45-68`][lim45] |
  | `mainnet_bridge.max_fee_atoms` | Default `MAX_FEE_ATOMS = 1_000_000` (1 PFT), [`pft_wallet/mainnet_bridge.py:74`][mb74] | [`pft_wallet/mainnet_bridge.py:884-886`][mb884], before the burn is signed |

  - The per-run cap also bounds the FastPay NAVswap
    ([`pft_wallet/fastswap.py:369-371`][fs369]).
  - The atomic swap has its own 5,000,000-atom limit
    ([`pft_wallet/swaps.py:170`][sw170]). It is checked at
    [`stakehub/atomic_swap_product.py:2549`][asp2549].
  - FastPay refuses a proxy that is not in `proxy_broadcast_devnet` mode or is
    bound to another chain ([`pft_wallet/fastpay.py:59-70`][fp59]).
  - The wallet reads only `~/.pft/config.toml`
    ([`pft_wallet/config.py:56-60`][conf56]).
- **Two warnings:**
  - Reserved cap money is not returned when a run fails
    ([`pft_wallet/limits.py:38-39`][lim38]). A failed run still counts against
    the 50 USD campaign cap.
  - PFT transfers, FastPay payments and the private round trip
    ([`pft_wallet/orchard.py:367`][orch367]) are not covered by
    `limits.reserve` at all.
- **Order for tonight:**
  1. Devnet FastPay payment and PFT transfer.
  2. Read-only route check. Stop if it fails.
  3. `pft bridge-in` of at most 5 USD until `accepted`.
  4. `pft bridge-out` of at most 5 USD until `accepted`.
  5. Optionally, one NAVCoin swap within 5 USD.
  6. Stop.
  - For `needs_reconcile`, run `pft op resume <id>`, never a new deposit or
    burn.
  - Do not run `pfeth_*` with `--live` or any venue flow.
  - The note's "Record for each run" lists what to record and what never to
    record.
- **This server, read at 2026-09-29T11:35Z:**
  - `~/.pft/config.toml` points at `combined-fastpay-20260928` and carries the
    template `[limits]` values (`run_usd = "5.00"`, `campaign_usd = "50.00"`).
  - It has no `mainnet_bridge.max_fee_atoms` override, so the 1 PFT default
    applies.
  - `~/.pft/campaign-spend.jsonl` does not exist yet.
  - The announced live funds had not arrived on this server by 11:00Z.
- **Since the note:** prerequisite 12 and the "unreviewed" entries in the
  per-flow table are covered by the wallet flows review below. StakeHub
  `master` is now `6a79672`.

### StakeHub wallet flows review

- **Document:** StakeHub [`docs/review/wallet-flows-review-20260929.md`][flows].
  - It covers the four modules no earlier review covered:
    [`pft_wallet/fastpay.py`][fastpay], [`pft_wallet/swaps.py`][swaps],
    [`pft_wallet/fastswap.py`][fastswap] and [`pft_wallet/orchard.py`][orchard].
  - It also covers the paths they call: `submit_fastlane_primary` and
    `submit_certified_shield_batch` in `pft_wallet/ce22.py`, `OperationStore`
    in `pft_wallet/operations.py`, `limits.reserve` in `pft_wallet/limits.py`,
    the API and CLI entry points, and `postfiat_rpc.wallet` (`wrap_fastpay`,
    `send_fastpay`, `_collect_fastpay_votes_with`) in `postfiatl1v2` at
    `657c6957`.
  - Its line numbers refer to StakeHub `0f139ac`. Nothing ran against a
    wallet, the fleet, a relay, a prover box or mainnet. Every test uses fakes.
- **Commits on `review/wallet-flows-20260929`:**

  | Commit | Content |
  | --- | --- |
  | `57f6ee8` | The review |
  | `829b52c` | FW-01 |
  | `9d0333a` | FW-03 |
  | `461e330` | FW-02 |
  | `e19c3b4` | FW-07 |
  | `52db8ac` | FW-05 |
  | `ab2f77e` | FW-06 |

- **Merge:** `6a79672` on StakeHub `master`, a squash of [PR #18][pr18].
  - I merged it on the full-suite result: 5,279 passed, 89 skipped and 84
    failed.
  - The 84 failures are the browser-bound and environment-bound set that fails
    identically on unchanged `master`. I checked this by set comparison against
    the 2026-09-23 run.
  - Wallet suite (`tests/test_pft_*.py tests/test_generalized_wallet.py`): 149
    passed before and 160 after. Of the 11 new tests, 8 are reproduce-first
    regression tests that failed on `0f139ac`. The other 3 are positive-path
    tests that pass on both.
- **Task Node:** `task_4be4a1b7abe75fef0d3d9a57c9d1f74a`, Rewarded.
- **P1 and P2 findings:**

  | ID | Sev | Finding | State |
  | --- | --- | --- | --- |
  | FW-01 | P1 | A FastPay payment could be reconciled as accepted from recipient objects when no send was attempted: the wrapped coin was not yet visible and the recipient already held a coin of the same amount | Repaired, `829b52c` |
  | FW-02 | P1 | The private round trip's final unshield broadcast whatever recipient, asset and amount the prover box returned, without binding them to the user | Repaired, `461e330` |
  | FW-03 | P2 | A second FastPay deposit was signed after the first had consumed the account sequence | Repaired, `9d0333a` |
  | FW-04 | P2 | A timed-out FastPay send cannot be re-applied, because the certificate is never saved | Open; the fix belongs in `postfiat_rpc.wallet` in `postfiatl1v2` |
  | FW-05 | P2 | A recorded FastLane deposit was stranded on resume | Repaired, `52db8ac` |
  | FW-06 | P2 | An interrupted FastSwap resumed by re-checking deposits the swap had already consumed | Repaired, `ab2f77e` |
  | FW-07 | P2 | An Orchard shield or swap batch was re-broadcast when the note state was unknown after an attempt | Repaired, `e19c3b4` |
  | FW-08 | P2 | A shield step's success is read from each validator's last receipt line (`pft_wallet/ce22.py:776-798`), not matched to the batch | Open |
  | FW-09 | P2 | The flows have no spending cap | Proposal only |

  - **FW-04 location:** `send_fastpay` in
    [`python/postfiat_rpc/wallet.py:1052`][w1052] builds the certificate at
    [`:1154`][w1154] and applies it at [`:1161`][w1161] without writing it to
    disk. The review's suggested change: write the certificate to `work_dir`
    before `owned_apply_v3`, or accept a prebuilt certificate, and have
    `fastpay.resume` re-apply it.
  - **FW-08:** the receipt must be bound to the batch's transaction id and
    height `h`. The review does not guess the field names until the
    `transport-peer-certified-batch-round` report and receipt schema are
    confirmed in `postfiatl1v2`.
- **P3 findings, recorded and open (7):**
  - FW-10: a raw `pf…` recipient's key comes from the proxy without an address
    check.
  - FW-11: default operation ids are per second, so two identical requests in
    one second become one operation.
  - FW-12: the wallet records the vote count but never compares it with quorum;
    `postfiat_rpc` enforces quorum.
  - FW-13: `swaps.py` and `orchard.py` decrypt the venue/pool inventory wallet
    with the user's passphrase.
  - FW-14: `conserved=True` covers only the user. The pool's a651 stays
    shielded after each run.
  - FW-15: reconciled leg receipts carry a height only, with no transaction id.
  - FW-16: `fastpay.py`, `swaps.resume` and the `orchard.py` resume paths had
    no tests. This is partly addressed, since the new tests cover only the
    repaired paths.
- **`swaps.py`:** nothing above P3.
- **Cap proposal (FW-09)**, for the other lane to decide before tonight's runs.
  Nothing is added yet. Line numbers are at `0f139ac`.

  | Flow | Proposed cap | Insertion point |
  | --- | --- | --- |
  | Private round trip | `limits.reserve(..., operation="shielded-swap", reservation_id=operation_id)` | `orchard.resume`, around the two `_ingress` calls (`pft_wallet/orchard.py:397-398`). Not inside a `roundtrip` child, whose bridge-in leg already reserves |
  | Transparent swap (API/CLI) | `limits.reserve(..., operation="swap", reservation_id=operation_id)` | `swaps.resume`, around `execute_atomic_swap` (`pft_wallet/swaps.py:287`) |
  | FastSwap | `limits.reserve(..., operation="fastpay-navswap", reservation_id=operation_id)` | `fastswap.resume`, before the first `_deposit_object` (`pft_wallet/fastswap.py:409`) |
  | FastPay and PFT transfer | A new atom cap, `limits.pft_run_atoms` | `fastpay.start` before `store.create` (`pft_wallet/fastpay.py:125`); `transfer.start` before its `store.create` (`pft_wallet/transfer.py:62`) |

  - `reservation_id=operation_id` makes a resume reuse its reservation instead
    of counting twice.
  - A failed run still keeps its reservation
    ([`pft_wallet/limits.py:38-39`][lim38]).

### Validator event log rotation

- **Rule:** `/etc/logrotate.d/postfiat-validator-events` on all six
  validators.
  - It applies to
    `/var/log/postfiat/validator-*/transport-validator-events.ndjson`.
  - Options: `size 2G`, `rotate 3`, `compress`, `delaycompress`, `missingok`,
    `notifempty` and `copytruncate`.
  - The daily `logrotate.timer` (00:00 UTC) checks it.
- **Code facts I established first**, at `c93b2137`. Both files are identical
  on `main`.
  - The node opens `transport-validator-events.ndjson` once, with create and
    append ([`crates/node/src/transport_protocol.rs:613`][tp613]). It holds
    that descriptor for the whole process life
    ([`crates/node/src/transport_runtime.rs:933`][tr933]). The observed fd
    flags are `02102001`, which includes `O_APPEND`.
  - There is no size or rotation option, only `--event-log PATH`, and there is
    no reopen. Rename-based rotation would keep writing to the renamed file,
    so the rule uses `copytruncate`.
  - Nothing reads the file back. Indices are in-memory counters, not byte
    offsets. Truncation is therefore safe, and the next append goes to the new
    end of the file.
- **Loss window:** `copytruncate` loses events written during the copy. That is
  about 36 s per 2 GiB copy, or about 6 events at the 2.2 KB/s long-run
  average. No event was lost today, because every file had been idle since
  2026-09-28 08:35–08:37Z.
- **Backlog:** a forced copy of the 13.87 GB file would have filled the disk on
  validator-1 and validator-0.
  - On validators 0, 1, 3, 4 and 5, I compressed the existing log to
    `transport-validator-events.ndjson.pre-rotation-20260929.zst` in the same
    directory. Each archive is about 4.18 GB, with a verified SHA-256 round
    trip. I then emptied the live file in place.
  - Validator-2's file was 40.7 MB, so it got the forced rotation to
    `transport-validator-events.ndjson.1`.
- **Services:** validator and RPC PIDs were identical before and after on all
  six. There was no restart and no new stderr or journal lines. No chain
  action was taken and no file was removed.
- **Free space:**

  | Host | Before | After |
  | --- | ---: | ---: |
  | validator-0 | 7.67 GB | 17.36 GB |
  | validator-1 | 9.88 GB | 19.57 GB |
  | validator-2 | 24.51 GB | 24.51 GB |
  | validator-3 | 19.41 GB | 29.10 GB |
  | validator-4 | 14.50 GB | 24.19 GB |
  | validator-5 | 18.34 GB | 28.03 GB |

- **Records:**
  - [`deployments/combined-fastpay-20260928/observed/event-log-rotation-20260929.json`][rotation]
    on `release/combined-fastpay-20260928`, commit `4788ef1f`.
  - The chain-state note, `0eab3d86` on `main`, in [Current State][state].
- **Not yet confirmed:** that new events arrive in the fresh files. There has
  been no validator traffic since 2026-09-28 08:37Z. Check after the live
  runs.
- **Open:**
  - logrotate never prunes the `.zst` archives.
  - `rpc-events.ndjson` (34–140 MB per host) is not rotated.
- **Rollback:** delete the rule on each host. The rotated files stay.

### Fleet and repository boundary

- **Last observed chain state:** 2026-09-28T08:38Z, at the end of the live
  check ([previous handoff][previous]). All six validators were on
  `combined-fastpay-20260928` at height 1062, tip `9d08fd3e…`, root
  `6324f86e…`. I did not re-read height, tip or root today.
- **Last observed host state:** 2026-09-29, from 12:13Z to the final read at
  12:39Z, during the log rotation. All 12 validator and RPC services were
  active and running with unchanged PIDs. Free space is in the table above.
- **Fleet action today:** the log rotation only. It was a host change, with no
  restart and no chain action.
- **Deployed:**
  - Executable `1f8b332d…` and signed manifest `d2fdb687…`.
  - Source `c93b2137` on `release/combined-fastpay-20260928`.
- **Repository:**
  - `main` was `0eab3d86` before this handoff.
  - Today's `main` commits:
    - the three research-note commits above;
    - `657c6957`, the interim version of this handoff, which this commit
      removes;
    - `0eab3d86`, the chain-state note on the log rotation.
  - `release/combined-fastpay-20260928` is at `4788ef1f` (was `209d1535`). Its
    only change today is the rotation record.
  - `release/combined-fastpay-20260925` is at `4d88956b`, unchanged.
  - StakeHub `master` is at `6a79672` (was `0f139ac`).
- **Merged but undeployed:** no node code. `crates/` on `main` is identical to
  `c93b2137`.
- **Live probe:** no chain or RPC probe. The only live reads were the host reads
  for the log rotation on the six validators.

### Other lane and Task Node

- The other lane has made no commit, handoff or session activity since
  2026-09-28.
- Task Node: one task today, `task_4be4a1b7abe75fef0d3d9a57c9d1f74a`, for the
  wallet flows review. Its outcome is Rewarded. The research note, the
  readiness note and this handoff had no Task Node task.

## Next decision or action

### Operating advice for tonight's runs

- The spending-cap decision (FW-09, item (m) below) is the other lane's call
  before the runs.
- FastPay is devnet only; the proxy must be in `proxy_broadcast_devnet` mode.
  If a FastPay send times out, check `pft op status` and the recipient's
  balance before any retry (FW-04).
- The private round trip is not cleared for real money. Use devnet or `--demo`
  only.
- After the runs, check that new events arrive in each validator's fresh
  `transport-validator-events.ndjson`.

### This lane's next steps, in order

1. After the other lane's live runs, fix FW-04 in `postfiat_rpc.wallet`
   ([`python/postfiat_rpc/wallet.py`][w1052]): save the FastPay certificate
   before submission so that a timed-out send can be re-applied. Then fix
   FW-08, the batch-bound shield receipt.
2. Add the spending caps if the other lane says yes (item (m)).
3. Address the recorded P3s: the 24 from earlier reviews and the 7 from the
   wallet flows review.
4. Fix the `deployment_manifest_verified` field for the next release: rename it
   or pass the `ExecStartPre` result into `status` ([Current State][state]).
5. Run the first Z3 cycle once the other lane's keys, inputs and Arc route step
   are in ([`docs/status/z3-cycle1-inputs-20260922.md`][z3]).
6. If the other lane says yes to the intent-style swap screen, write the NEAR
   Intents design note before any code.

### Only the other lane can provide

Each item was asked again tonight.

- **(a)** The two NEAR Intents design questions
  ([`docs/specs/near-intents-architecture-research-20260929.md`][note], end of
  Part 1). First asked 2026-09-29.
- **(b)** NAVCoin signer keys and custody, and rows 4, 8, 11, 12, 13, 16 and
  17 ([`docs/status/z3-cycle1-inputs-20260922.md`][z3]). First asked
  2026-09-22.
- **(c)** The Arc route step: a route epoch of 11 or more, with a custody row
  for the Arc source, signed by the A666 issuer. First asked 2026-09-28.
- **(d)** A compatible governed NAV profile with fresh proofs. First asked
  2026-09-22.
- **(e)** StakeHub custody Q1 and archive Q2
  ([`docs/review/custody-and-archive-decision-proposal-20260923.md`][custody]).
  First asked 2026-09-07.
- **(f)** Reserve-proof successor adoption, yes or no ([PR #49][pr49],
  [`docs/review/nav-reserve-proof-successor-proposal-20260924.md`][successor]).
  First asked 2026-09-24.
- **(g)** FastPay committee rotation for validator-5. It is needed only for
  validator-5 to sign FastPay payments. First asked 2026-09-25.
- **(h)** The height-915 archive and the height-924 custodian. First asked
  2026-08-30.
- **(i)** The AI-governance decision for Gate Zero Z2. First asked 2026-09-03.
- **(j)** Twelve inventory rows
  ([`docs/review/defect-inventory-20260910.md`][inventory]). First asked
  2026-09-10.
- **(k)** Disk: the September 5–7 dumps, `gate931`, `gate926` and the three
  unknown-origin snapshot entries
  ([`deployments/combined-fastpay-20260925/observed/disk-inventory-20260928.json`][disk]).
  First asked 2026-09-28.
- **(l)** The `ETHEREUM_MAINNET_RPC_URL` repository secret, if the
  `official-mainnet-fork` job should run
  ([`docs/status/main-ci-red-20260928.md`][ci]). First asked 2026-09-28.
- **(m)** The spending-cap decision for FastPay, PFT transfers and the shielded
  swap flows (FW-09, the cap proposal in
  [`docs/review/wallet-flows-review-20260929.md`][flows]). First asked
  2026-09-29.

## References

- [`docs/specs/near-intents-architecture-research-20260929.md`][note] and its
  source list.
- [`docs/review/near-intents-research-scores-20260929.md`][scores].
- StakeHub [`docs/review/live-funds-readiness-20260929.md`][ready].
- StakeHub [`docs/review/wallet-flows-review-20260929.md`][flows] and
  [PR #18][pr18].
- [`deployments/combined-fastpay-20260928/observed/event-log-rotation-20260929.json`][rotation]
  on `release/combined-fastpay-20260928` (`4788ef1f`).
- [`python/postfiat_rpc/wallet.py`][w1052] (FW-04),
  [`crates/node/src/transport_protocol.rs`][tp613] and
  [`crates/node/src/transport_runtime.rs`][tr933] (event log writer).
- StakeHub reviews:
  [`docs/review/wallet-bridge-review-20260924.md`][sh-wb],
  [`docs/review/private-funding-money-path-review-20260923.md`][sh-mp] and
  [`docs/review/pay-transfer-and-registry-review-20260925.md`][sh-pt].
- This lane's previous handoff:
  [`docs/handoffs/2026-09-28___dravlic__fastpay_stall_fixed_live_and_main_line_caught_up.md`][previous].
- [`docs/status/chain-state-current.md`][state].
- [`docs/status/z3-cycle1-inputs-20260922.md`][z3].
- StakeHub
  [`docs/review/custody-and-archive-decision-proposal-20260923.md`][custody].

[note]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/specs/near-intents-architecture-research-20260929.md
[scores]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/review/near-intents-research-scores-20260929.md
[previous]: 2026-09-28___dravlic__fastpay_stall_fixed_live_and_main_line_caught_up.md
[state]: ../status/chain-state-current.md
[z3]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/status/z3-cycle1-inputs-20260922.md
[ci]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/status/main-ci-red-20260928.md
[successor]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/review/nav-reserve-proof-successor-proposal-20260924.md
[inventory]: https://github.com/postfiatorg/postfiatl1v2/blob/main/docs/review/defect-inventory-20260910.md
[disk]: https://github.com/postfiatorg/postfiatl1v2/blob/release/combined-fastpay-20260925/deployments/combined-fastpay-20260925/observed/disk-inventory-20260928.json
[rotation]: https://github.com/postfiatorg/postfiatl1v2/blob/4788ef1fb40ff259e5df2378ddeeb9c2e06b6366/deployments/combined-fastpay-20260928/observed/event-log-rotation-20260929.json
[tp613]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/node/src/transport_protocol.rs#L613
[tr933]: https://github.com/postfiatorg/postfiatl1v2/blob/c93b213755f5889565fd1f77b9e45c149a07193a/crates/node/src/transport_runtime.rs#L933
[w1052]: https://github.com/postfiatorg/postfiatl1v2/blob/0eab3d86b1c075a070771d647a62e15d157ababf/python/postfiat_rpc/wallet.py#L1052
[w1154]: https://github.com/postfiatorg/postfiatl1v2/blob/0eab3d86b1c075a070771d647a62e15d157ababf/python/postfiat_rpc/wallet.py#L1154
[w1161]: https://github.com/postfiatorg/postfiatl1v2/blob/0eab3d86b1c075a070771d647a62e15d157ababf/python/postfiat_rpc/wallet.py#L1161
[flows]: https://github.com/postfiatorg/StakeHub/blob/master/docs/review/wallet-flows-review-20260929.md
[pr18]: https://github.com/postfiatorg/StakeHub/pull/18
[pr49]: https://github.com/postfiatorg/postfiatl1v2/pull/49
[ready]: https://github.com/postfiatorg/StakeHub/blob/master/docs/review/live-funds-readiness-20260929.md
[custody]: https://github.com/postfiatorg/StakeHub/blob/master/docs/review/custody-and-archive-decision-proposal-20260923.md
[sh-wb]: https://github.com/postfiatorg/StakeHub/blob/master/docs/review/wallet-bridge-review-20260924.md
[sh-mp]: https://github.com/postfiatorg/StakeHub/blob/master/docs/review/private-funding-money-path-review-20260923.md
[sh-pt]: https://github.com/postfiatorg/StakeHub/blob/master/docs/review/pay-transfer-and-registry-review-20260925.md
[fastpay]: https://github.com/postfiatorg/StakeHub/blob/0f139ac7e9c1a94e25103777eacc5584e07d0fb8/pft_wallet/fastpay.py
[swaps]: https://github.com/postfiatorg/StakeHub/blob/0f139ac7e9c1a94e25103777eacc5584e07d0fb8/pft_wallet/swaps.py
[fastswap]: https://github.com/postfiatorg/StakeHub/blob/0f139ac7e9c1a94e25103777eacc5584e07d0fb8/pft_wallet/fastswap.py
[orchard]: https://github.com/postfiatorg/StakeHub/blob/0f139ac7e9c1a94e25103777eacc5584e07d0fb8/pft_wallet/orchard.py
[cfg102]: https://github.com/postfiatorg/StakeHub/blob/0f139ac7e9c1a94e25103777eacc5584e07d0fb8/pft_wallet/default_config.toml#L102
[cfg103]: https://github.com/postfiatorg/StakeHub/blob/0f139ac7e9c1a94e25103777eacc5584e07d0fb8/pft_wallet/default_config.toml#L103-L104
[lim38]: https://github.com/postfiatorg/StakeHub/blob/0f139ac7e9c1a94e25103777eacc5584e07d0fb8/pft_wallet/limits.py#L38-L39
[lim41]: https://github.com/postfiatorg/StakeHub/blob/0f139ac7e9c1a94e25103777eacc5584e07d0fb8/pft_wallet/limits.py#L41-L44
[lim45]: https://github.com/postfiatorg/StakeHub/blob/0f139ac7e9c1a94e25103777eacc5584e07d0fb8/pft_wallet/limits.py#L45-L68
[mb74]: https://github.com/postfiatorg/StakeHub/blob/0f139ac7e9c1a94e25103777eacc5584e07d0fb8/pft_wallet/mainnet_bridge.py#L74
[mb187]: https://github.com/postfiatorg/StakeHub/blob/0f139ac7e9c1a94e25103777eacc5584e07d0fb8/pft_wallet/mainnet_bridge.py#L187
[mb248]: https://github.com/postfiatorg/StakeHub/blob/0f139ac7e9c1a94e25103777eacc5584e07d0fb8/pft_wallet/mainnet_bridge.py#L248
[mb599]: https://github.com/postfiatorg/StakeHub/blob/0f139ac7e9c1a94e25103777eacc5584e07d0fb8/pft_wallet/mainnet_bridge.py#L599
[mb884]: https://github.com/postfiatorg/StakeHub/blob/0f139ac7e9c1a94e25103777eacc5584e07d0fb8/pft_wallet/mainnet_bridge.py#L884-L886
[mb902]: https://github.com/postfiatorg/StakeHub/blob/0f139ac7e9c1a94e25103777eacc5584e07d0fb8/pft_wallet/mainnet_bridge.py#L902
[fs369]: https://github.com/postfiatorg/StakeHub/blob/0f139ac7e9c1a94e25103777eacc5584e07d0fb8/pft_wallet/fastswap.py#L369-L371
[sw170]: https://github.com/postfiatorg/StakeHub/blob/0f139ac7e9c1a94e25103777eacc5584e07d0fb8/pft_wallet/swaps.py#L170
[asp2549]: https://github.com/postfiatorg/StakeHub/blob/0f139ac7e9c1a94e25103777eacc5584e07d0fb8/stakehub/atomic_swap_product.py#L2549
[fp59]: https://github.com/postfiatorg/StakeHub/blob/0f139ac7e9c1a94e25103777eacc5584e07d0fb8/pft_wallet/fastpay.py#L59-L70
[conf56]: https://github.com/postfiatorg/StakeHub/blob/0f139ac7e9c1a94e25103777eacc5584e07d0fb8/pft_wallet/config.py#L56-L60
[orch367]: https://github.com/postfiatorg/StakeHub/blob/0f139ac7e9c1a94e25103777eacc5584e07d0fb8/pft_wallet/orchard.py#L367
