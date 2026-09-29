# NEAR Intents: what it is, how it works, and what it means for NAV swaps

Research note, 2026-09-29. Operator: Domagoj Ravlić (`dravlic`). Sources: the NEAR Intents documentation, the `near/intents` contract repository, NEAR's own posts, three independent write-ups, and DefiLlama, all read on 2026-09-29 and listed at the end. Numbers are the sources' numbers as of the dates given; nothing here was measured by this lane.

## Part 1. The short version, in plain words

**What it is.** NEAR Intents is a way to swap money between blockchains without using those blockchains to carry out the swap. You put your coins into a shared vault, sign a sentence like "I give 100 of A and I want at least 200 of B", and professional traders compete to give you the best price. The swap then settles inside one ledger on the NEAR chain. Only the deposit at the start and the withdrawal at the end are visible on the other chains. The team calls the signed sentence an *intent*, the traders *solvers*, and the ledger the *Verifier*.

**How one swap goes, step by step.**

1. You send coins to a deposit address. A bridge brings them into the Verifier and credits your account there.
2. Your app asks a message service for prices. The service asks every connected solver at once and waits up to three seconds.
3. Each solver answers with a signed offer that is valid for about a minute.
4. You pick an offer and sign your intent. The service bundles your intent with the solver's and hands both to the Verifier.
5. The Verifier checks that every kind of coin balances between the people in the swap, so nobody can receive more of a coin than someone else gave. It then moves the balances in one atomic step. If anything is off, nothing moves.
6. You withdraw to any supported chain, or leave the balance inside for the next swap.

**Why it is fast and cheap.** The swap is one bookkeeping entry in the ledger on the NEAR chain, rather than separate swap transactions on the other chains. The protocol's own fee is one hundredth of a percent. Solvers earn by beating the quote, not by charging you. Public sources report about 4.5 billion dollars of swaps in the thirty days to 26 September 2026 and more than 10 billion in total, at an average all-in cost of about 0.15 percent.

**Where the trust sits.** This is the part to look at closely. The swap inside the Verifier is checked by code, but the coins themselves sit in bridges run by people. One bridge is a "proof of authority" system: named validators confirm what arrived on Bitcoin, Zcash, Tron and a dozen other chains. Other bridges use small groups that must act together to control the keys; one has four named operators, and NEAR's own bridge uses a similar group. The message service that collects prices is one company's service, though the protocol can run without it. The team also screens addresses against sanctions lists and has a law-enforcement contact channel, so the flows are watched.

**How it compares with our NAV swaps.** We are building a different trust model on purpose. In our intended system, when USDC comes from Ethereum, the validators accept it only with a cryptographic proof that Ethereum finalized the deposit. When a NAVCoin is issued or redeemed, the price comes from a finalized NAV with a reserve proof behind it. When funds leave, a burn is proven before the payout. The aim is not to trust a bridge operator's signature alone for custody. The route still depends on the agreed vault path, validators agreeing, the service carrying the proof, the service paying out, the agreed spread and the reserve proof details. NEAR Intents instead trusts named bridge operators for custody and gets speed, many chains and low fees in return. They win on convenience and reach; our design aims to give a regulator or fund auditor more that can be checked without relying on those bridge operators.

**What is worth borrowing.**

- *The intent itself.* Letting a user sign "what I want" and letting competing solvers find the price is a better user experience than our fixed route with a governed quote. It also fits a wallet demo well.
- *Solver competition for the NAV spread.* Our NAVCoin subscribe and redeem run at a governed spread. A small solver market on top of our proof-based route could tighten it without changing custody.
- *One ledger for many assets.* Their Verifier holds every asset as one multi-token balance sheet, so a wallet reads one balance list. Our wallet already went this way with the portfolio document.
- *The deposit-address flow and the one-call API.* A quote-specific deposit address and a single REST call are why so many wallets integrated them in months.

**What not to copy.** Custody by named validators or key committees, and a swap trail that cannot be reconstructed from the public records of the source and destination chains alone. Balances are public on NEAR, but withdrawal and re-entry can break the trail across chains. The independent write-ups are blunt that the design makes tracing hard and that illicit actors have noticed; a fund that wants to prove its reserves cannot sit on that kind of rail.

**Decision for you.** Nothing here changes this week's plan. Two things are worth a yes or no when you have a minute: (1) should the wallet's swap screen move to an intent-style flow, "what I want" plus competing quotes, on top of our existing proof-based route; (2) should we study NEAR Intents as a *distribution channel* for NAVCoins later, meaning a NAVCoin listed there so their users can buy it, while custody and proofs stay ours. Both are design questions, not urgent, and neither needs money.

## Part 2. The architecture, for the engineers and the agents

### 2.1 Components

| Component | What it is | Who runs it | Source |
| --- | --- | --- | --- |
| Verifier (`intents.near`, internal name Defuse) | The on-chain settlement contract on NEAR mainnet: an internal ledger of deposited assets (NEP-245 multi-token balances per account) plus the intent execution engine. "Intents Technology does not custody these balances — control stays with the keys that can sign for each account." | Deployed and upgradable by the protocol team (a controller interface handles upgrades and state migrations) | [Verifier intro], [repo] |
| Message Bus (solver relay) | An off-chain service: takes quote requests, broadcasts them to all connected solvers over WebSocket, collects signed quotes, bundles the user's intent with the chosen solver intent and submits the bundle to the Verifier. "The protocol can operate without the Message Bus." | The protocol team; a single service today | [Bus], [RPC] |
| Solvers (market makers) | Independent parties that hold inventory inside the Verifier and answer quotes with signed `token_diff` intents. They do not charge fees; they earn the difference when a fill beats the quote. On cross-asset swaps whose quote is still fresh (within about 30 minutes), that improvement is split 50/50 with the protocol. | Third parties | [Fees], [Bus] |
| 1Click API | A REST layer for integrators: quote, quote-specific deposit address, execution, status. "1Click does not take custody." Adds 20–25 bps unless an integrator agreement applies. | The protocol team | [1Click], [Fees] |
| Bridges | Omni Bridge (Ethereum, Base, Arbitrum, BNB, Solana, Bitcoin) with a Bridge Token Factory on NEAR that "manages both native tokens from the source chain and bridged tokens" and requests outbound signatures from an MPC network (chain signatures); PoA Bridge (a proof-of-authority validator set; Bitcoin, BCH, Litecoin, Dogecoin, Zcash, Tron, XRP, Sui, Aptos, Cardano, Starknet, Gnosis, Berachain, and the EVM chains again) with `PoA Token` and `PoA Factory` contracts in the repository; HOT Bridge (a separate MPC validator network with nodes from EverStake, NEAR Protocol, Aurora and HAPI; BNB, Polygon, Optimism, Avalanche, Scroll, Monad, TON, Stellar and others). The route is "selected automatically". | Omni: NEAR's bridge team plus the MPC network; PoA: the PoA validators (operator not named in the docs); HOT: the HOT MPC network | [Bridges], [OmniBridge], [repo], [Indago] |

### 2.2 The intent model

- An **intent payload** carries `signer_id`, `verifying_contract`, a `deadline` (ISO 8601), a 256-bit `nonce` and a list of intents. The nonce is `[4-byte salt][28-byte unique data]`; the salt must match the contract's current salt, which is how old signatures are invalidated wholesale. Nonces can also be invalidated explicitly.
- **Intent types**: `token_diff` (the swap: signed deltas per token, "a trade of 100 token A for 200 token B can be represented as `{"A": -100, "B": 200}`"; in a batch "the total diffs across all tokens must sum to zero" or the whole batch fails). In practice, each token must balance separately across all participants; amounts of unlike tokens are not added together. Other types are `transfer` (inside the ledger), `ft_withdraw` / `nft_withdraw` / `mt_withdraw` / `native_withdraw` (out of the ledger), `storage_deposit`, and `add_public_key` / `remove_public_key` (account abstraction: any registered key may sign for the account).
- **Execution**: `execute_intents` runs a list in order; `simulate_intents` dry-runs it. Caveat from the docs: NEAR is asynchronous and sharded, so "intents submitted in sequence do not guarantee they will *complete* in that sequence" — settlement inside one `execute_intents` call is atomic, cross-call ordering is not.
- **Signing standards**: NEP-413 (NEAR wallets), ERC-191 (Ethereum wallets), raw Ed25519 (the docs); the repository's payload traits also cover BIP-322 (Bitcoin) and TIP-191, so one engine hashes and verifies messages from different standards uniformly. This is how a Bitcoin or Ethereum key can act inside the NEAR ledger without a NEAR account.

### 2.3 The quote flow (Message Bus JSON-RPC)

1. `quote`: input and output asset ids (for example `nep141:ft1.near`), either `exact_amount_in` or `exact_amount_out`, `min_deadline_ms` (default 60 s). The bus "forwards the request to all solvers, waits up to 3000ms, and returns all available options"; each option has a `quote_hash`, amounts and an `expiration_time`. Shorter validity can yield better prices.
2. `publish_intent` / `publish_intents`: the user's signed payload plus the chosen `quote_hashes`; batching can requote and retry.
3. `get_status`: `TX_BROADCASTED` → `SETTLED` (with the NEAR transaction hash and actual filled amounts) or `NOT_FOUND_OR_NOT_VALID` (expired or failed, with a reason).

### 2.4 Custody and trust, stated plainly

- Inside the Verifier, correctness is enforced by the contract: each token balances across participants, and signatures, nonces and deadlines are checked. Audits exist ("audited by independent security firms"; reports behind a Drive link; firms and dates not named on the page), plus a HackenProof bounty. The contract is upgradable by its controller.
- Outside the Verifier, the real assets sit with the bridges. The PoA bridge is by construction a trusted validator set; the Omni and HOT bridges are MPC committees (no single key, but a small named group). A user holding "BTC" inside the Verifier holds a claim on whichever bridge brought it in.
- The Message Bus and the 1Click API are operated services; the protocol works without the bus, but in practice the bus is the market.
- Compliance: automated screening of quote flows against several AML providers (TRM Labs, Binance AML, AMLBot and PureFi), an internal portal, and a dedicated law-enforcement request channel. "coverage can vary by flow and integration path". An independent investigation (Indago Labs) documents the protocol's use in laundering chains: "a swap between two chains involves no transaction on either of them", "withdrawal and re-entry under a different account identifier" breaks the trail, and the mainstream volume means "funds arriving from it are not automatically flagged". That is the reputational and regulatory exposure of the design.

### 2.5 Fees and numbers (sources' figures)

- Protocol fee 1 bp on every transfer and swap, collected on-chain; since February 2026 the protocol's fee income is converted into NEAR purchases. The near-intents.org site adds 0.2 %; the 1Click API adds 25 bps unauthenticated, 20 bps authenticated (1 bp on stablecoin pairs), with a 50/50 split when an integrator sets its own fee; some withdrawals carry 0.1 %.
- Solvers earn only "quote improvement", split 50/50.
- Volume: about 4.49 billion USD in the thirty days to 26 September 2026 with 6.7 million USD gross fees (14.93 bps average); more than 10 billion USD and 15.7 million swaps cumulative, 1.6 million users; TVL reported at 169 million USD after a 77 % monthly rise (dates per the cited pages). The gross-fee-to-volume ratio does not by itself establish every user's all-in cost.

### 2.6 Side by side with the PostFiat NAV swap architecture

| Dimension | NEAR Intents | PostFiat NAV swaps and the pfUSDC route |
| --- | --- | --- |
| Where the swap settles | Inside one NEAR contract's internal ledger | On the PostFiat L1 as certified blocks (validator consensus) |
| How external value enters | Bridges: PoA validators or MPC committees credit the ledger | A governed vault route on Ethereum mainnet; validators accept a deposit only with a finality proof (`sp1-ethereum-finality-v1`) relayed by the proof relay |
| How value leaves | Withdrawal intent; the bridge's validators or MPC sign the outbound transfer | Burn-to-redeem certified on L1, proven, then paid out by the payout service against the vault |
| Price discovery | Competing solvers, signed quotes valid about a minute, best fill wins, solver earns the improvement | Governed NAV: primary subscribe and redeem at the finalized NAV with a governed spread; reserves proven by a reserve proof profile |
| Who is trusted for custody | Bridge validators (PoA) or MPC committees; the contract for ledger correctness | The intended model does not rely on a bridge signature alone: it uses finality proofs, reserve proofs and certified receipts, alongside validator consensus, the governed vault route, proof relay and payout service |
| Privacy | Ledger balances are public on NEAR; a confidential-execution variant has been announced by NEAR | Shielded (Orchard-style) private swaps in the design; public and private lanes side by side |
| Chains | About 26 chains including Bitcoin, Zcash, Tron | Ethereum mainnet today (Arc testnet in the Z3 plan); others by adding governed routes with proofs |
| Fees | 1 bp protocol, plus 20–25 bps at the API layer, plus bridge fees | Governed spread and network fees; no market-maker layer yet |
| Failure behaviour | Atomic inside one call; expired quotes fail cleanly; cross-call ordering not guaranteed | Certified or not; resume and reconciliation rules in the wallet and operator tooling (this lane's September repairs) |
| Compliance posture | Address screening, LE channel; documented use by illicit actors | No public exposure yet; a fund-grade audit trail is the design goal |

### 2.7 What this suggests for us

1. **Keep custody as it is.** Proof-based ingress and egress is the property NEAR Intents does not have and cannot bolt on without changing its bridges. It is our differentiator with funds and auditors.
2. **Add intents on top, not instead.** A user-signed "what I want" plus a small set of solvers competing to fill it against our governed NAV route would give the wallet the NEAR Intents feel without moving custody. The solver's fill is still a certified L1 transaction and the NAV is still proven. This is a design study, not a sprint item.
3. **Consider NEAR Intents as a shelf, later.** Listing a NAVCoin as an asset inside their Verifier would expose it to 1.6 million users through one bridge integration; the bridge would then be the trusted party for the bridged NAVCoin, exactly the trade-off this note describes. Only after the NAVCoin is live and its reserve proof has moved to the successor profile.
4. **Reuse the small things now.** Quote expiry and requote-on-failure semantics for the wallet's swap screen; a quote-specific deposit address for the bridge flow; one multi-asset balance list, which the wallet already has.

## Sources

- Verifier contract introduction: https://docs.near-intents.org/near-intents/market-makers/verifier/introduction
- Intent types and execution: https://docs.near-intents.org/integration/verifier-contract/intent-types-and-execution.md
- Deposits: https://docs.near-intents.org/near-intents/market-makers/verifier/deposits-and-withdrawals
- Withdrawals: https://docs.near-intents.org/integration/verifier-contract/deposits-and-withdrawals/withdrawals.md
- Message Bus: https://docs.near-intents.org/near-intents/market-makers/bus
- JSON-RPC: https://docs.near-intents.org/integration/market-makers/message-bus/rpc.md
- 1Click API: https://docs.near-intents.org/integration/distribution-channels/1click-api/about-1click-api.md
- Token bridges: https://docs.near-intents.org/integration/bridging/overview
- Fees: https://docs.near-intents.org/resources/fees.md
- Security: https://docs.near-intents.org/security-compliance/security.md
- Risk and compliance: https://docs.near-intents.org/security-compliance/risk-and-compliance.md
- Contracts repository: https://github.com/near/intents
- NEAR on Omni Bridge: https://www.near.org/blog/omnibridge-nears-universal-solution-for-cross-chain-liquidity
- Confidential Intents announcement: https://www.near.org/blog/confidential-intents
- Fees and volume figures: https://phemex.com/academy/near-intents-explained-swap-fees
- TVL: https://cryptobriefing.com/near-intents-tvl-169-million/
- DefiLlama: https://defillama.com/protocol/near-intents
- Independent risk view: https://indagolabs.eu/how-near-intents-works-and-why-illicit-actors-are-choosing-it/
