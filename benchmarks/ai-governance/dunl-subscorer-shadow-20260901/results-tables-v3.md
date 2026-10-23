# Deterministic sub-scorer v3 shadow evaluation — per-round tables

Rounds evaluated: 9; fetch/evaluation failures: none.

### testnet-r12 (prompt v5, baseline: model overall score, gap 5)

| Metric | Value |
|---|---|
| Validators compared | 45 |
| consensus mean/max abs delta | 3.6 / 70 |
| reliability mean/max abs delta | 16.22 / 50 |
| software mean/max abs delta | 0 / 0 |
| diversity mean/max abs delta | 0 / 0 |
| identity mean/max abs delta | 0.33 / 5 |
| Final score mean/max abs delta | 9.78 / 22 |
| Cutoff flips (out / in) | 1 / 0 |
| Baseline reproduces published UNL | True |
| UNL overlap / seats changed | 20/20 / 0 |
| Diversity source | model |
| Automated acceptance (control, no in-flip, overlap >= 19) | pass |

Cutoff-boundary cases (final within 5 of 40 under either scorer):

| Validator | Baseline final | Deterministic final | Flipped |
|---|---|---|---|
| `nHU5tRRbniyS...` | 45 | 29 | YES |

### testnet-r13 (prompt v5, baseline: model overall score, gap 5)

| Metric | Value |
|---|---|
| Validators compared | 45 |
| consensus mean/max abs delta | 5.07 / 38 |
| reliability mean/max abs delta | 19 / 70 |
| software mean/max abs delta | 0.67 / 10 |
| diversity mean/max abs delta | 0 / 0 |
| identity mean/max abs delta | 1.33 / 25 |
| Final score mean/max abs delta | 8.84 / 26 |
| Cutoff flips (out / in) | 0 / 0 |
| Baseline reproduces published UNL | True |
| UNL overlap / seats changed | 20/20 / 0 |
| Diversity source | model |
| Automated acceptance (control, no in-flip, overlap >= 19) | pass |

No cutoff-boundary cases.

### testnet-r14 (prompt v6, baseline: model overall score, gap 5)

| Metric | Value |
|---|---|
| Validators compared | 42 |
| consensus mean/max abs delta | 5.31 / 38 |
| reliability mean/max abs delta | 14.88 / 50 |
| software mean/max abs delta | 0.71 / 10 |
| diversity mean/max abs delta | 0 / 0 |
| identity mean/max abs delta | 0.6 / 10 |
| Final score mean/max abs delta | 6.17 / 24 |
| Cutoff flips (out / in) | 0 / 0 |
| Baseline reproduces published UNL | True |
| UNL overlap / seats changed | 20/20 / 0 |
| Diversity source | model |
| Automated acceptance (control, no in-flip, overlap >= 19) | pass |

No cutoff-boundary cases.

### testnet-r15 (prompt v6, baseline: model overall score, gap 5)

| Metric | Value |
|---|---|
| Validators compared | 50 |
| consensus mean/max abs delta | 4.38 / 38 |
| reliability mean/max abs delta | 20.4 / 75 |
| software mean/max abs delta | 0 / 0 |
| diversity mean/max abs delta | 0 / 0 |
| identity mean/max abs delta | 0.8 / 20 |
| Final score mean/max abs delta | 7.9 / 22 |
| Cutoff flips (out / in) | 0 / 0 |
| Baseline reproduces published UNL | True |
| UNL overlap / seats changed | 19/20 / 1 |
| Diversity source | model |
| Automated acceptance (control, no in-flip, overlap >= 19) | pass |

No cutoff-boundary cases.

### testnet-r16 (prompt v8, baseline: formula(model sub-scores), gap 5)

| Metric | Value |
|---|---|
| Validators compared | 51 |
| consensus mean/max abs delta | 0.69 / 1 |
| reliability mean/max abs delta | 16.08 / 45 |
| software mean/max abs delta | 10 / 10 |
| diversity mean/max abs delta | 0 / 0 |
| identity mean/max abs delta | 0.78 / 20 |
| Final score mean/max abs delta | 3.37 / 10 |
| Cutoff flips (out / in) | 0 / 0 |
| Baseline reproduces published UNL | True |
| UNL overlap / seats changed | 20/20 / 0 |
| Diversity source | model |
| Automated acceptance (control, no in-flip, overlap >= 19) | pass |

Cutoff-boundary cases (final within 5 of 40 under either scorer):

| Validator | Baseline final | Deterministic final | Flipped |
|---|---|---|---|
| `nHBWFVzxVYAV...` | 41 | 41 | no |

### testnet-r17 (prompt v9, baseline: formula(model sub-scores), gap 5)

| Metric | Value |
|---|---|
| Validators compared | 53 |
| consensus mean/max abs delta | 0.43 / 1 |
| reliability mean/max abs delta | 2.45 / 35 |
| software mean/max abs delta | 0 / 0 |
| diversity mean/max abs delta | 0 / 0 |
| identity mean/max abs delta | 1.32 / 5 |
| Final score mean/max abs delta | 0.91 / 7 |
| Cutoff flips (out / in) | 0 / 0 |
| Baseline reproduces published UNL | True |
| UNL overlap / seats changed | 20/20 / 0 |
| Diversity source | model |
| Automated acceptance (control, no in-flip, overlap >= 19) | pass |

No cutoff-boundary cases.

### testnet-r18 (prompt v9, baseline: formula(model sub-scores), gap 5)

| Metric | Value |
|---|---|
| Validators compared | 55 |
| consensus mean/max abs delta | 0.33 / 1 |
| reliability mean/max abs delta | 5.09 / 35 |
| software mean/max abs delta | 0 / 0 |
| diversity mean/max abs delta | 0 / 0 |
| identity mean/max abs delta | 1.36 / 5 |
| Final score mean/max abs delta | 1.31 / 8 |
| Cutoff flips (out / in) | 0 / 0 |
| Baseline reproduces published UNL | True |
| UNL overlap / seats changed | 20/20 / 0 |
| Diversity source | model |
| Automated acceptance (control, no in-flip, overlap >= 19) | pass |

No cutoff-boundary cases.

### testnet-r19 (prompt v10, baseline: formula(model sub-scores), gap 3)

| Metric | Value |
|---|---|
| Validators compared | 54 |
| consensus mean/max abs delta | 0.37 / 1 |
| reliability mean/max abs delta | 3.98 / 35 |
| software mean/max abs delta | 0 / 0 |
| diversity mean/max abs delta | 0 / 0 |
| identity mean/max abs delta | 1.39 / 5 |
| Final score mean/max abs delta | 1.17 / 7 |
| Cutoff flips (out / in) | 0 / 0 |
| Baseline reproduces published UNL | True |
| UNL overlap / seats changed | 19/20 / 1 |
| Diversity source | model |
| Automated acceptance (control, no in-flip, overlap >= 19) | pass |

No cutoff-boundary cases.

### testnet-r28 (prompt v12, baseline: formula(model sub-scores, formula diversity), gap 3)

| Metric | Value |
|---|---|
| Validators compared | 61 |
| consensus mean/max abs delta | 0.49 / 1 |
| reliability mean/max abs delta | 2.46 / 30 |
| software mean/max abs delta | 0 / 0 |
| diversity mean/max abs delta | 9.02 / 33 |
| identity mean/max abs delta | 0.98 / 5 |
| Final score mean/max abs delta | 0.57 / 6 |
| Cutoff flips (out / in) | 0 / 0 |
| Baseline reproduces published UNL | True |
| UNL overlap / seats changed | 24/25 / 1 |
| Diversity source | code.diversity_formula |
| Automated acceptance (control, no in-flip, overlap >= 24) | pass |

No cutoff-boundary cases.
