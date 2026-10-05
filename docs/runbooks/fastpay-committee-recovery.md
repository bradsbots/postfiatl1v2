# FastPay recovery after a validator key rotation

The September 2026 failure occurred because every node compared the entire live
validator registry with the pinned FastPay committee. Rotating validator-5 disabled
all six nodes, although validators 0–4 still had valid committee keys.

The repair authorizes each local signer against both its current registry entry
and its pinned committee entry. It verifies the actual signature before reserving
inputs or writing an acknowledgement. The five-signature quorum, committee epoch,
key rotation, balances and ordered-block rules are unchanged.

The active database also needs the retained FastPay journal when answering wallet
queries and preparing blocks. A signed acknowledgement alone was insufficient on
the old release: it wrote legacy JSON while reads used the finalized database.
The repaired node verifies and reconstructs pending certificates in memory, keeps
the finalized root unchanged, and anchors those effects in the next certified
block. Ordered recovery or an intervening certified omission takes precedence.

The Python wallet and Rust RPC SDK must be updated together. The SDK verifies
certificate votes and acknowledgements, then derives exact transfer output IDs
using the execution engine. Python exposes those verified outputs at the top
level for the existing wallet CLI and retains the raw response under `apply`.
From a clean `main` checkout, update and build the SDK:

```bash
git fetch https://github.com/postfiatorg/postfiatl1v2.git main
git merge --ff-only FETCH_HEAD
cargo build --release -p postfiat-rpc-sdk
```

Point `fastpay.python_root` at that checkout's `python` directory,
`fastpay.repo_root` at the checkout, and `ce22.rpc_sdk_binary` at
`target/release/postfiat-rpc-sdk`. Restart the wallet UI after updating so it
loads the matching Python code.

## Operational limit

Epoch 1 still requires five signatures, and only validators 0–4 are eligible.
Any additional signer outage stops new FastPay certificates. Validator-5 receives
accepted FastPay effects through certified ordered blocks; it does not supply an
epoch-1 acknowledgement. The replacement is a governed committee rotation,
described below.

## Preparing the next committee

A committee record (`FastPayRecoveryCommitteeV1`) is installed by a governance
batch that carries one `FastPayRecoveryGovernanceBootstrapV1`: the unchanged
recovery policy, the new record, and a Cobalt amendment of kind
`fastpay_recovery_bootstrap_v1:<payload hash>`. Every active validator signs the
amendment (`governance-authorization-sign`); each signature is checked against
the signer's current registry key. The batch is ordered in a block, and every
node applies it and commits the committee list to the state root.

A rotation is accepted only when the record is the next epoch, keeps the
chain, genesis and protocol of the previous record, has a new `registry_root`,
and starts at exactly the previous `new_orders_through_height` + 1, in a block
below that height. A node signs FastPay only when its committee entry equals its
current `validator_registry.json` key.

The read-only command below reads a data directory, builds epoch N+1 from the
active validators' current registry keys (quorum 5 of 6), dry-runs the rotation
against the next block and prints the record, its payload and the unsigned batch.
It never signs and reads no key file. It refuses a key that is not the
validator's current registered key, any committee other than 5 of 6, and a
`--valid-from` other than the required start height. `--registry-file` takes member
keys from a registry snapshot, and `--new-orders-through` overrides the default
end height, which keeps the previous epoch's length.

```bash
postfiat-node fastpay-committee-prepare --data-dir PATH [--registry-file PATH] [--valid-from H] [--new-orders-through H]
```

Save `payload` as the payload file and the amendment from `unsigned_transaction`.
Each validator signs the amendment with `governance-authorization-sign`.
Combine the signatures with `governance-amendment-assemble`, then build the batch
with `fastpay-recovery-governance-bootstrap-assemble`. On
`postfiat-wan-devnet-2`, epoch 1 admits orders through height 10000, so epoch 2
must start at height 10001 and be installed before then.

## Client recovery

On the original wallet host, use the existing helper:

```bash
pft-fastpay start
pft-fastpay status
pft op list
pft op status EXISTING_OPERATION_ID
```

Inspect the existing operation before retrying. If its wrap succeeded and its
FastPay transfer did not, resume that same operation:

```bash
pft op resume EXISTING_OPERATION_ID
```

This retains the recorded input and reconciles an ambiguous previous application.
Do not create another wrap to hide an unresolved payment. The incident's original
one-PFT coin belongs to that original client; a payment from another test wallet
does not prove that coin was recovered.

For a new payment, amounts are integer atoms (1 PFT = 1,000,000 atoms):

```bash
pft fastpay send SENDER --to RECIPIENT --amount 1000 --operation-id UNIQUE_ID
pft op status UNIQUE_ID
pft gui
```

Completion requires verified quorum acknowledgements, a spent input and the exact
recipient output. Check Activity in the wallet UI. Verify all six nodes after a
subsequent certified ordered block; service health alone is insufficient.

## Converting the FastSwap store before the rotation

Since keyed integrity (`4dbd80c2`), a normal open rejects the legacy unkeyed
record checksums in the July `fastswap-v1` stores, so every `fastswap_*` request
answers `fastswap_unavailable`. The rotation needs `fastswap_checkpoint_status`
on validators 0–4, so each store is converted offline during the rollout:

```bash
postfiat-node fastswap-store-migrate --data-dir PATH [--dry-run] [--backup-dir PATH]
```

The command refuses while the store lock is held, and refuses a torn or tampered
record before writing anything. It copies `fastswap-v1/` (WAL, `committee.json`,
`base-state.json`, `vote-artifacts/`, `.integrity.key`; not the lock) to the
backup directory and compares digests. It then rewrites the WAL tags with the
directory's keyed MAC (temporary file, fsync, rename) and re-opens the store
normally to verify every record. A failed verification restores the original.
The JSON report gives record counts, bytes, the key fingerprint (never the key),
the backup path and the verification result. `--dry-run` writes nothing, and a
second run reports `nothing-to-convert`. A running unit that has not yet opened
the store holds no lock, so stopping both units is the operator's check.

Run it one host at a time, validator-5 first, then validators 0–4. Use the
binary from the release being rolled out.

1. Stop the validator's two units and confirm both are inactive with
   `systemctl is-active`.
2. Dry run: `postfiat-node fastswap-store-migrate --data-dir /var/lib/postfiat/validator-N --dry-run`.
   Expect `would-convert`, with `legacy_wal_records` equal to `wal_records`.
3. Convert: `postfiat-node fastswap-store-migrate --data-dir /var/lib/postfiat/validator-N --backup-dir /var/lib/postfiat/fastswap-v1-backup-validator-N`.
   Expect `converted` and `normal open verified N record(s) with the keyed MAC`.
   Record the key fingerprint and backup path.
4. Start both units.
5. Call `fastswap_checkpoint_status` on that host's RPC; it must answer instead of
   `fastswap_unavailable`. Continue with the next host only then.

Rollback: stop both units, move `fastswap-v1/` aside, copy the backup back to
`<data-dir>/fastswap-v1/` with `cp -a`, and start the units. The restored store
is the legacy store again, so FastSwap stays unavailable on that host.

## Release and backup basis

Use [the safe rollout runbook](safe-validator-rollout.md), preserving the signed
publisher, old binary and unit files. Build from the exact archived deployed
source (`03e1138e`), which captures the deployed `707e006f` working tree, plus the
bounded FastPay and checkpoint-restore repairs.

The mandatory signed backup uses finalized-checkpoint verification. The incident
height-1033 snapshot contains historical block 1011, which fails modern full-history
NAV-supply replay. The repair does not change that invariant or claim full replay
passes. Explicit checkpoint import reconstructs the transactional generation and
then verifies its certified current state, roots, tip, registry and integrity.
Ordinary import and standalone migration still require full historical replay.

The locked specifications are [FastPay authority](../specs/fastpay-committee-local-authority-repair-20260925.md),
[checkpoint restore](../specs/fastpay-checkpoint-restore-prerequisite-20260925.md),
and [transactional reads](../specs/fastpay-transactional-read-view-repair-20260925.md).
See [the deployed repair and payment evidence](../handoffs/2026-09-25_fastpay_restored.md).
