# Coinbase integration plan: Text Improvement Harness scores

Scores for [the integration plan](integration-plan.md). This record is not part of the scored text.

Every gate ran the harness `score` with `--gate full --runs 5 --force --temperature 0 --max-tokens 8000`. The prompt was `Rate this document on a scale of 1-100. Output the score and your reasoning.` Run groups: `coinbase-integration-plan-20261022-r1` to `-r8`.

| Gate | Document SHA-256 | `gpt-6-astra` | `claude-fable-5.1` | `glm-5.3` | Average |
| --- | --- | --- | --- | --- | ---: |
| r1, original | `6ece2956…` | 84, 85, 85, 85, 85 | 85, 85, 86, 84, 84 | 88, 88, 91, 88, 88 | 86.07 |
| r2, memo correction | `700ef0e6…` | 85, 85, 85, 85, 85 | 84, 84, 85, 86, 84 | 86, 86, 88, 84, 88 | 85.33 |
| r3, improvement rewrite | `1713e627…` | 86, 86, 85, 86, 87 | 89, 83, 86, 87, 84 | 89, 92, 89, 90, 88 | 87.13 |
| r4, network wording | `8ee4d7f6…` | 86, 86, 87, 86, 86 | 85, 86, 87, 87, 86 | 88, 88, 88, 88, 88 | 86.80 |
| r5, custody wording | `0c6dc28c…` | 85, 85, 86, 85, 84 | 85, 86, 87, 85, 86 | 88, 88, 88, 88, 88 | 86.27 |
| r6, red-team corrections | `7537578c…` | 87, 87, 86, 86, 86 | 86, 86, 84, 84, 86 | 88, 86, 88, 92, 88 | 86.67 |
| r7, second adversarial review | `14a49cfb…` | 87, 86, 86, 87, 87 | 86, 87, 86, 87, 87 | 92, 88, 88, 88, 88 | 87.33 |
| r8, chain fixes in review | `68c3bd4e…` | 87, 86, 87, 88, 87 | 83, 85, 84, 84, 84 | 88, 88, 88, 88, 88 | **86.33** |

- **r1** passed the 86/100 gate.
- **r2** corrected a factual error: r1 said exchanges could tag deposits with memos today, but `account_tx` returns only a hash of a payment's memos. The correction scored 85.33, below the gate.
- **r3** followed the improvement loop in [AGENTS.md](../../../AGENTS.md). The 15 judge critiques of r2 were given to `openai/gpt-5.6-sol-pro` with these rules:
  - add no new facts, numbers, dates, names or URLs;
  - keep every link;
  - keep every statement about what is missing or unaudited.
- The r3 rewrite was then checked against r2:
  - all 75 links are unchanged;
  - it adds no new numbers;
  - every admission is kept, including the missing audit, the halts, the documentation contradictions and the address checksum.
- The r3 changes:
  - an owner and dependencies for each roadmap phase;
  - a statement that calendar dates are not committed;
  - sharper exit tests for phases 3 and 4;
  - a single post-quantum table instead of two.
- **r4** uses the repository's name for the network, a controlled development network, instead of "public" (see [public-claims-checklist.md](../../status/public-claims-checklist.md)). It also adds that the source code and chain-state records are public. A first run on an intermediate edit was stopped before it finished, and only the final text was scored.
- **r5** states that Fireblocks' NEAR rotation used PKCS#11 with kryoptic, an open-source software HSM, so "HSM-based" is not read as hardware.
- **r6** applies the first adversarial review of the listing package (`openai/gpt-5.6-sol-pro`). Each change was checked against the code or the companion documents:
  - NAVCoins are no longer described as issued only against zero-knowledge proofs, because a profile may also use `ledger-transparent`, `multi-fetch-quorum` or `placeholder` verifiers;
  - the successor reserve-proof guest fixes N1 and A1, while G1 waits for the separate A666 migration;
  - the 100 billion PFT figure is called an unpublished target, and the phase 4 genesis now includes allocations and vesting;
  - one certificate is the protocol's finality rule, and Coinbase sets its own confirmation count;
  - a wrapped PFT is described as reusing existing components, with no contract yet;
  - a fourth compliance point covers deposits that come straight out of the shielded pool.
- **r7** applies the second adversarial review. NAVCoin issuance is "against a finalized reserve record, checked by the verifier the asset's profile sets", not "after an on-chain reserve-proof verification".
- **r8** points each phase 1 gap to its fix in an open pull request (#140 to #144) and to PR #49's status. It states that none is merged or deployed and that the consensus changes ship inactive.

The plan is locked at r8. Any later edit must be re-scored before it replaces this version.

Raw scores and model responses are outside Git in `~/repos/pastedocs/.coinbase-integration-plan-20261022/`.
