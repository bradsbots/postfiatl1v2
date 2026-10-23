# Storage verifier and packager acceptance changes: review, 2026-10-23

**Verdict: ACCEPT WITH CHANGES.** All three changes are faithful ports of rules
the milestone already accepts. None is a weakening introduced on 2026-10-23,
and the 1.10 ratio limit is untouched. Skipping the four binaries in the
redaction scan is safe. The verifier still refuses tampering, mixed builds and
missing inputs. Two changes are needed before the packet is used for
`OFFLINE QUALIFIED`: the original hash of each rewritten window report must be
kept (finding 4), and the ported gates need refusal tests (finding 5). Finding
6 is recommended.

**Scope.** `main` `aa1ebd05` and `6e0e3df0`:
`python/postfiat_rpc/storage_scaling.py`,
`benchmarks/storage-scaling/package_packet.py`,
`python/tests/test_storage_scaling.py` and
`python/tests/test_storage_scaling_packager.py`. The measures used are:

- the [storage milestone](../plans/completed/storage-scaling-milestone.md): the
  G4 ratio limit of 1.10, the height-cost model and G5;
- the [stall-tolerant plan](../plans/active/stall-tolerant-g4-campaign-plan.md)
  and the [model-floor plan](../plans/active/model-floor-g4-campaign-plan.md);
- the runner branch `g4-runner-bounds-20261019` (`51a19272`), files
  `run_campaign.py` and `run_paired_campaign.py`.

Line numbers are at `main` `2cd26f4f`. The tests were read, and the two
storage test files were run: 72 passed. Nothing was run against a packet.

## Per change

| Change | Verifier / packager | Rule it ports | Judgment |
| --- | --- | --- | --- |
| Certified-send and vote-lock work gates | `storage_scaling.py:1257` (`_verify_vote_lock_work`) and `:1436` (`_verify_certified_send_work`). Each recomputes from the raw report and requires gate pass, empty reason codes, and equality with the window and its bound receipt. Summary booleans are at `:3471-3482` | Runner `9ec853e0` (vote-lock) and `15d059d1` (certified-send), the gates attempt 4 ran under | Faithful port; no refusal test (finding 5) |
| Prepared-input build provenance (`prepared_by`) | `storage_scaling.py:2649-2800`. The measured candidate must still be the packet's node binary and source (`:2684-2697`). `prepared_by` admits only an older builder that prepared the fleets, with full-form identities. The fleet digests stay bound to the frozen material | Runner `2c562eeb` (2026-08-28): "derive a new manifest instead of rewriting the old build identity" (runner `README.md:171-175`). Attempt 4 used exactly this, deriving its manifest from `ec5a4715…` | Faithful port. The measured binary is not relaxed |
| Stall tolerance | `storage_scaling.py:125-129` and `_recompute_round_coverage` (`:1462`, rule at `:1496-1518`). A round passes if its unattributed residual is in [−1, 100] ms. One round per window may fall in (100, 250] ms. A second such round, or any residual above 250 ms, fails. The tolerated round is listed and must equal the receipt (`:1549`) | Runner `2e49abb2`, reviewed and approved by the operator (stall-tolerant plan, item 2); `run_campaign.py:758-765`, `:1424-1460`. The boundaries and the one-per-window count are identical | Faithful port. Note: it bounds the residual (round time not covered by named stages), not round latency. The stalled round's full latency still feeds the 1.10 p95 ratios |
| 5 ms materiality floor | `storage_scaling.py:46-51`, `:1034-1041`: the threshold is max(10 % of baseline, 2σ residual, same-height range, 5 ms). A positive slope with predicted growth above it still fails (`:1086-1087`). Recorded thresholds must equal the recomputation (`:1081-1085`) | Runner `ae6ec9cb` (model-floor plan, "Change since the predecessor"); `run_campaign.py:75-83`, `:560-565`. The formula is identical | Faithful port. It only raises the floor of an existing max(); the ratio gate (`:3468-3469`, `expected > 1.10`) is unchanged |
| Topology path in run reports | `package_packet.py:95-110`: `config.topology_file` becomes `$TOPOLOGY_FILE`. The topology stays bound by `topology_sha256`. Used for windows at `:498` and advances at `:339` | Milestone G3 redaction rule: reports carry no host-local paths (the harness fix `325afbdb` did the same for `verify-only.json`) | Correct redaction, but the original hash of each window report is lost (finding 4) |
| Binaries skipped in the redaction scan | `package_packet.py:648-668`, call at `:895`; verifier `storage_scaling.py:4239`, call at `:4320` | Hash-pinned binaries; see the redaction section | Safe. Recommend recording it (finding 6) |

## Redaction of the binaries

The exemption cannot widen beyond the binaries:

- The set is the packet's `source.binaries`. The verifier requires exactly
  four roles: `bin/postfiat-node`, `bin/postfiat-storage-corpus-batches`,
  `bin/postfiat-node-rollback` and `bin/postfiat-node-incompatible`
  (`storage_scaling.py:522-540`).
- Each binary's SHA-256 must match its file, and the four digests must differ.
- The node digest is cross-bound to the G4 report and the replay receipts. The
  batch-builder digest is cross-bound to the prepared-input manifest and its
  receipts (`:2709`, `:3159`).
- A text file therefore cannot take a binary role to escape the scan.

Before 2026-10-23 the scan already skipped files over 16 MiB (both functions),
so the three node binaries (52–63 MB) were never scanned. The change affects
only the 1.8 MB batch builder.

What the four packet binaries contain (`~/.cache/storage-packet-20261023/packet/bin/`,
work server):

| Binary | `SENSITIVE` pattern hits | Host-local paths | Non-loopback IPv4 |
| --- | --- | --- | --- |
| batch builder (1.8 MB) | none | cargo registry (31), rustup toolchain (1), its build checkout under `~/.cache/storage-g4-20261019` (2) | none |
| node, rollback, incompatible | code strings only (error texts and identifiers such as "private key", `spending_key`, `rseed`) | cargo registry, rustup, one build checkout | none |

These are compile-time panic locations and code strings. They hold no key, seed
or credential, no validator material and no address. They reveal only the build
account's user name and directory names. The milestone's rule is about evidence
files: no private validator material, and no host-local paths in reports. The
binaries are not reports. They must stay byte-identical to the hash-pinned
release build, so they cannot be redacted. They are already public through
their deployment.

## Does the verifier still refuse what it must

- **Tampering:** yes. The checksum manifest, every bound reference and the 69
  tamper cases are checked, with tests for checksum, cost-model,
  resource-variance and raw-resource tampering.
- **A mixed-build packet:** yes. The binary roles must be distinct and bound
  (`:522-540`). The embedded binary revision must match the source (`:543-551`).
  The prepared-input candidate must be the packet's binary (`:2684-2697`). The
  replacement replay must be on the packet's binary.
- **A missing input:** yes. A missing performance lane, a missing original E3
  campaign or an unbound reference fails, and every artifact is resolved
  through the checksums.

## Findings

**4. Keep the original hash of each rewritten window report (required).**

- **Condition:** the packager rewrites a window report's `config.topology_file`.
- **Observed:** `package_packet.py:498-500` overwrites
  `window["normalized_report_sha256"]` with the rewritten file's hash. The
  campaign's recorded hash, from the report bound as `7aa8d72c…`, is not kept
  anywhere in the packet. For advance reports the packager keeps it as
  `source_report_sha256` (`:339-342`).
- **Expected:** a reviewer can trace every packet window report to the campaign
  report it came from, as before 2026-10-23, when the window reports were
  byte-identical copies.
- **Suggested change:** record `source_normalized_report_sha256` beside the
  rewritten hash, as for advances. In the verifier, require it to be a full
  SHA-256, and require that `config.topology_file` is either the original or
  `$TOPOLOGY_FILE`. Test that any other field change is refused.

**5. Refusal tests for the ported gates (required).**

- **Condition:** today's tests cover one tolerated stall, two stalls, a tampered
  floor threshold, hidden round time and the derived build.
- **Observed:** no test makes the verifier refuse a raw report with a repeated
  or late vote-lock migration (`VOTE_LOCK_MIGRATION_REPEATED`,
  `VOTE_LOCK_MIGRATION_AFTER_FIRST_VALIDATOR_RESERVATION`). The same is true
  for the two certified-send index migration codes, a single residual over
  250 ms, a residual below −1 ms, and real growth above the floor ("material
  stage … retains a positive height relationship").
- **Expected:** G5 requires the verifier to "fail on every … inconsistent
  required artifact", and the 114 packager and verifier tests are the
  milestone's evidence of that. A ported gate without a refusal test is not yet
  shown to refuse.
- **Suggested change:** add one negative fixture each. Include the two
  boundaries: residual 250.0 passes as the one stall, and 250.01 fails.

**6. Record the binary exemption (recommended).**

- **Condition:** the redaction scan now skips the four binaries.
- **Observed:** `artifacts/redaction.json` holds only `passed` and
  `allowed_nonlocal_ip_files`. The packet does not say that the binaries, or
  files over 16 MiB, were not scanned.
- **Expected:** the packet states what its redaction scan covered.
- **Suggested change:** add an exempt-path list and its reason to the redaction
  artifact, and have the verifier require it to equal the four roles.
  Optionally, accept the exemption only for files that start with the ELF
  magic number.

**Minor.** The message at `storage_scaling.py:538` says "three-binary set"; the
set has four. The milestone's G5 line "one stall of 100–250 ms per window"
should read "one unattributed residual in (100, 250] ms per window".
