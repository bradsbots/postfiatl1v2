# Coinbase listing package and docs front door

- **Operator:** Claude ("Nazgûl") for the founder's lane (`nazgul`)
- **Date:** 2026-10-22 UTC
- **Previous handoff from this lane:** [2026-10-20](2026-10-20___nazgul__founder_lane_resync_and_answers_to_open_asks.md)

## BLUF

Coinbase's listing team asked the founder how a Post Fiat integration would
work. This lane answered with two PRs and a page on postfiat.org:

- [PR #138](https://github.com/postfiatorg/postfiatl1v2/pull/138) gives the docs an integrator front door and shrinks the site nav. This handoff ships inside it.
- [PR #139](https://github.com/postfiatorg/postfiatl1v2/pull/139) is the Coinbase listing package: an integration plan, comparisons with XRP and other chains, and a guide for reviewers' AI agents. It is stacked on #138.
- postfiat.org/listings mirrors the package. It is not live until the founder approves the website merge.

**What changes for you:**

- **New handoffs no longer need a `mkdocs.yml` edit.** Run `scripts/docs-handoffs-index` and commit the regenerated `docs/handoffs/index.md` with the handoff.
- **The plan proposes Phase 1 work to Coinbase that would land in your lane.** Ask (a) below.

## Current state

- **Plan status:** locked at 86.27 on the full Text Improvement Harness gate; [score record](https://github.com/postfiatorg/postfiatl1v2/blob/61106cce29cb54551427cb27a46036aaa544c85b/docs/listings/coinbase/integration-plan-scores.md).
- **What the plan says:**
  - PFTL is a controlled devnet on six Foundation-administered validators.
  - It has not been externally audited.
  - Coinbase would integrate through the transparent ledger only.
  - Until Coinbase custody can sign ML-DSA-65, there is an interim ERC-20 path.
- **Network wording.** The plan, the website and the founder's email use the repository's term, "controlled devnet". They add that the source code and chain-state records are public ([public-claims-checklist.md](../status/public-claims-checklist.md)).
- **Contradictions.** The reviewer guide lists 10 contradictions found in the repository ([section 7](https://github.com/postfiatorg/postfiatl1v2/blob/61106cce29cb54551427cb27a46036aaa544c85b/docs/listings/coinbase/reviewer-agent-guide.md#7-contradictions-already-found)). Coinbase's agents will see that list.

## Next decision or action

(a) **Phase 1 of the plan's roadmap** ([§8](https://github.com/postfiatorg/postfiatl1v2/blob/61106cce29cb54551427cb27a46036aaa544c85b/docs/listings/coinbase/integration-plan.md#8-integration-roadmap)) commits Post Fiat to:
   - a checksummed address encoding, with malformed recipients rejected at admission and execution, and published test vectors;
   - memo contents returned by `tx` and `account_tx`, which today return only a memo hash;
   - an account flag that rejects untagged payments, like XRPL's `RequireDest`;
   - indexing of shielded withdrawals that credit a transparent account;
   - regenerated and published Orchard verifying keys.

   Please reply with what you would change in that list, and an order. No calendar dates were promised.

(b) **Four documentation fixes** found while writing the package. All are cited in the reviewer guide.
   - The whitepaper says a consensus safety check (the cross-phase round floor) is missing and untested. The code has had it, with tests, since 2026-09-09; the whitepaper is pinned to an earlier commit.
   - `docs/quantum/authorization.md` shows an SLH-DSA recovery-key path. `SECURITY.md` and the code say none exists.
   - `deny.toml` sets an Orchard 0.15 migration deadline of 2026-08-31, which has passed. The workspace is still on 0.14.0.
   - `scripts/verify-vendored-halo2` fails under `en_US.UTF-8` because `sort` orders lines differently. It passes with `LC_ALL=C`.

(c) The follow-ups listed in the PR #138 description are not done: `testnet-path.md` regeneration, the September summary table in `chain-state-current.md`, the storage line in `SECURITY.md`, and the custody model spec.

## References

- [Integration plan](https://github.com/postfiatorg/postfiatl1v2/blob/61106cce29cb54551427cb27a46036aaa544c85b/docs/listings/coinbase/integration-plan.md), [comparisons](https://github.com/postfiatorg/postfiatl1v2/blob/61106cce29cb54551427cb27a46036aaa544c85b/docs/listings/coinbase/comparisons.md), [reviewer agent guide](https://github.com/postfiatorg/postfiatl1v2/blob/61106cce29cb54551427cb27a46036aaa544c85b/docs/listings/coinbase/reviewer-agent-guide.md).
- [Exchange integration guide](../integrate/exchange-guide.md), [Network Status](../status/network-status.md).
- [Current chain state](../status/chain-state-current.md).
