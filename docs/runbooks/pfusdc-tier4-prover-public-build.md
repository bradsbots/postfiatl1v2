# Public default pfUSDC prover build

The default `tools/pfusdc-tier4-prover` build enables SP1 6.3.1 native Gnark.
Its Go build requires the original ignition-verifier module at commit
`10693546ab33a54bff6d02cebb46fba538559748`. The original repository and public
Go proxy currently return 404. This is the dependency failure reported in
[upstream SP1 issue 3004](https://github.com/succinctlabs/sp1/issues/3004),
not a reason to disable default features or replace cryptographic code.

With the repository's Rust toolchain, Go >=1.24, Python >=3.11, a C compiler
and libclang available:

```sh
python3 scripts/pfusdc-tier4-prover-build
python3 scripts/pfusdc-tier4-prover-build --test
python3 scripts/test_pfusdc_public_build.py
```

The wrapper downloads only three fixed files from the recovery proxy's
immutable commit `9580323dfab6a759db4eea04fac40c3c31612da8`, verifies their
SHA-256 values, and stages a local module proxy in the user cache. Use
`--cache-dir /chosen/cache` to select another location. It then invokes the
ordinary locked default Cargo build or host unit tests. Other modules use
the canonical Go proxy; there is no `direct` fallback to private Git access.

The module archive retains the original Go checksum
`h1:z42ewLaLxoTYeQ17arcF4WExZc/eSaN3YVlF7eEaPt4=` and go.mod checksum
`h1:JdKor28c/KR4BbznP88bz8AAvnCgovzrB3KWsiR7lwk=`. Go's authenticated
checksum database remains enabled, private-module exemptions are cleared
for the child build, inherited Go config/workspace files are disabled, and
`-mod=readonly` forbids changes to Go dependencies.
Corrupt cached files fail before Cargo; inspect/remove the corrupt recovery
cache before retrying. No dependency/source replacement is applied.

This repairs public build availability. It does not change SP1/circuit
versions, Cargo or Go locks, guests, ELFs, vkeys, trusted setup, qualification
inventories, verifier contracts or deployed routes. Compilation and host unit
tests do not establish proof, qualification, production or deployment parity.
The wrapper never invokes the prover CLI. Existing audited proving and route
qualification gates remain necessary before operating a route.

Retire the recovery only after upstream publishes and this repository adopts
a supported publicly buildable dependency, with the relevant identity gates.
The wrapper stops if the SDK version or default feature contract changes.
