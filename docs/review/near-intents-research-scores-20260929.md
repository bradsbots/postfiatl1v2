# NEAR Intents research note: Text Improvement Harness scores

Scores for [the research note](../specs/near-intents-architecture-research-20260929.md). This record is not part of the scored text.

Each gate ran the harness `score` with `--gate full --runs 5 --force --temperature 0 --max-tokens 8000`. The prompt was `Rate this document on a scale of 1-100. Output the score and your reasoning.` The credential came from vault label `openroutertih`. Improvement rounds were direct OpenRouter calls to `openai/gpt-5.6-sol-pro`.

| Gate | Document SHA-256 | `gpt-6-astra-pro` | `claude-fable-5.1` | `glm-5.3` | Average |
| --- | --- | --- | --- | --- | ---: |
| r1, original | `22a3404e…` | 78, 78, 76, 79, 78 | 84, 85, 80, 84, 86 | 90, 88, 90, 92, 88 | 83.73 |
| r2, first rewrite (`6a0084db`) | `7fde1d9d…` | 82, 81, 82, 82, 82 | 84, 84, 84, 84, 82 | 90, 90, 90, 90, 88 | 85.00 |
| r3, quotations corrected, astra-pro rewrite | `90929d16…` | 84, 84, 84, 83, 84 | 84, 84, 82, 84, 86 | 91, 90, 91, 88, 90 | **85.93** |

Run groups: `near-intents-research-20260929-r1`, `-r2`, `-r3`. The r3 version scored highest and is kept. It remains below the 86/100 gate, so the note is not locked.

Before r3, every Part 2 quotation was checked verbatim against its cited page. The `token_diff` quote now uses the docs' wording. The unconfirmed "selected automatically" and Omni Bridge quotations are now plain paraphrases.

Raw scores and responses are outside Git in `~/pastedocs/.near-intents-research-20260929/`.
