# Strict entry profile: shared fixtures (Z2 step 3)

Rule module `postfiat.validator_entry_profile.v1`, version 1:

- Rust: `crates/consensus_cobalt/src/validator_entry_profile.rs`;
- Python mirror, sharing no code with it: `python/postfiat_rpc/validator_entry_profile.py`.

Both follow the locked
[identity flag pipeline specification](../../../docs/specs/identity-flag-pipeline-spec-20261023.md),
sections 3, 4 and 7. Both are `SHADOW_ONLY`, and no consensus path calls them
until step 4 of the
[Z2 plan](../../../docs/plans/active/z2-advisory-flag-execution-plan-20261022.md).

`fixtures/cases.json` holds 263 cases. Each has its inputs, its expected output
and the SHA-256 of that output's canonical JSON (sorted keys, compact,
ASCII-escaped):

| Group | Cases | Source of the expected output |
| --- | ---: | --- |
| `direction` | 31 | Written by hand: the direction's five cases, the boundaries (three clean rounds, a gap, a domain lost in round four, a below-cutoff round, an absent round, a flag that clears, the interim rule), the flag-input resolution and the refused inputs. The build refuses to write if the mirror disagrees with any of them |
| `worked_example_20260903` | 110 | The spec's §4.1, from the committed corpus and replay outputs. It gives 13 flags with the score-0 stand-in and 0 with the "not established" stand-in |
| `round_28` | 122 | The fork's testnet round 28 (61 operators, all hypothetically flagged, under both rules), from the SHA-256-pinned round files. Under `entry_profile_v1`: 25 incumbents keep their seats and 36 entrants are withheld. Under the interim rule: 24 entrants may take a seat and 12 are withheld |

`fixtures/modules.json` pins the SHA-256 of both module files and of
`cases.json`. The Python test checks those pins.

**Convergence.** Both of these must equal the canonical bytes of each case's
`expected`:

- `cargo test -p postfiat-consensus-cobalt --lib validator_entry_profile`;
- `python3 -m pytest python/tests/test_validator_entry_profile.py`.

The Python side also checks `expected_sha256`.

**Rebuild:** `python3 benchmarks/ai-governance/validator-entry-profile-20261023/build_fixtures.py`.
This needs no network. It needs round 28's files under the sub-scorer's
gitignored `rounds/`. Any rule or parameter change changes the expected bytes
and the module hashes.
