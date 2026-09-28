# Why main's CI was red (28 September 2026)

Status: **finding**. Two separate causes kept `main` red. Both were in
`main`'s own code, not in secrets, accounts or runners. The merge of the
installed release line on 28 September removes both. No workflow was
changed and no check was weakened.

## Summary

| Workflow / job | Failing step | Error | Red since |
| --- | --- | --- | --- |
| `rust-ci` / `check` | `cargo clippy --workspace --all-targets --locked -- -D warnings` | `clippy::err_expect` at `crates/node/src/cobalt_handoff.rs:1466` | `21cf30f8`, 16 September 12:09Z |
| `rust-ci` / `check` | `cargo fmt --all -- --check` (earlier step, which then hid the Clippy error) | unformatted code in `crates/node/src/fastpay_recovery_node.rs` and `crates/rpc_sdk/src/main.rs` | first run on `a3b95b23`, 25 September 03:52Z |
| `product-security-ci` / `open-reserve-proof-kit` | `cargo fmt --all -- --check` in `tools/nav-reserve-proof` | the same unformatted code; `--all` also checks the kit's local path dependencies | first run on `a3b95b23`, 25 September 03:52Z |

`docs-build` passed throughout. The `rust-ci` `test` job passed on every
failing run that was sampled (16, 21, 23 and 25 September). The other six
`product-security-ci` jobs passed on `c4cbf759`.

## Cause 1: Clippy `err_expect` (16 September)

- `21cf30f8` ("Repair burn 5 Cobalt handoff findings") added a test in
  `crates/node/src/cobalt_handoff.rs` that calls `result.err().expect(...)`.
  With `-D warnings`, Clippy 1.95.0 rejects this in favour of `expect_err`.
- Run history: the last green `rust-ci` on main was `34611d66`, run
  `35093573106` (16 September 12:02Z). The next run, on `21cf30f8`
  (`35094235056`), failed in `cargo clippy`. Every later run failed the
  same way until 25 September, for example `35598049554` (21 September) and
  `35840795297` (23 September).
- The release line already has the fix:
  `result.expect_err("expanded data must be bounded before checkpoint cloning")`.

## Cause 2: unformatted FastPay cherry-picks (25 September)

- `28ab6931` left one unformatted hunk in
  `crates/node/src/fastpay_recovery_node.rs`, and `d8f65885` left five in
  `crates/rpc_sdk/src/main.rs`. These were cherry-picks of the FastPay
  committee repair from the r4 line. The parent commit `1fe136a4` passes
  `cargo fmt --check`.
- The two commits were pushed together with `a3b95b23`. From then on,
  `rust-ci` `check` failed at `cargo fmt`, before Clippy runs. The last green
  `product-security-ci` was run `36079257288` on `1fe136a4` (25 September
  00:48Z). The first red one was on `a3b95b23` (`36092148453`).
- The release line has these same files formatted, as `2a5ba80f` and
  `943c4ca7`.

## Local reproduction

| Tree | `cargo fmt --all -- --check` (root and kit) | Clippy |
| --- | --- | --- |
| `main` at `e7c85996` | fail: 1 hunk in `fastpay_recovery_node.rs`, 5 in `rpc_sdk/src/main.rs` | `cargo clippy -p postfiat-node --lib --tests --locked -- -D warnings`: fail, `err_expect` at `cobalt_handoff.rs:1466` |
| merge of `release/combined-fastpay-20260928` (code identical to `c93b2137`) | pass | `cargo clippy --workspace --all-targets --locked -- -D warnings`: pass |

All commands used the pinned toolchain 1.95.0 with `-j 2`, one cargo
invocation at a time.

## Repair

This needs no separate repair commit. The merge replaces every code path
on `main` with the release line's version, which is formatted and
Clippy-clean. The only differences from the release branch are in `docs/` and
`mkdocs.yml`.

## After the push

The merge (`6b8f6ea8`) and this document (`63a0550a`) were pushed together
at 09:00Z. The verdict for each workflow on `main` is recorded below once
the runs finish.

- `docs-build` on `63a0550a`: **fail**. The failing step was
  `scripts/public-doc-links`, because this document linked to an anchor
  that did not exist. The next commit fixed the link.
