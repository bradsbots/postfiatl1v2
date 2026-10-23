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

## Submitting FastLane control transactions

`mempool_submit_fastlane_primary_finality` accepts up to 256 KiB of
`fastlane_primary_json` (`MAX_RPC_FASTLANE_PRIMARY_JSON_BYTES`, also for
`--request-file`); other signed-transaction fields keep 64 KiB. The node's
128 KiB canonical-binary mempool limit still binds: the five-vote
`AnchorCheckpoint` is 70,944 JSON bytes (19,705 canonical) and an
`ActivateCommittee` about 176 KB. Linux caps one argument at 128 KiB, so pass
the transaction as a file: `postfiat-node rpc --method
mempool_submit_fastlane_primary --fastlane-primary-file PATH` or `postfiat-rpc-sdk
--fastlane-primary-json-file PATH`. Finality reports success when the receipt
carries the operation's code: `fastlane_checkpoint_anchored` for an anchor,
`fastlane_control_applied` for `StopPrepare` and `ActivateCommittee`,
`owned_deposit_applied` for an owned deposit.

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
   `/var/lib/postfiat` is root-owned, so the `postfiat` user cannot create the
   backup directory: root pre-creates it empty with
   `install -d -o postfiat -g postfiat -m 700 /var/lib/postfiat/fastswap-v1-backup-validator-N`
   (the command refuses a non-empty one).
   Expect `converted` and `normal open verified N record(s) with the keyed MAC`.
   Record the key fingerprint and backup path.
4. Start both units.
5. Call `fastswap_checkpoint_status` on that host's RPC; it must answer instead of
   `fastswap_unavailable`. Continue with the next host only then.

Rollback: stop both units, move `fastswap-v1/` aside, copy the backup back to
`<data-dir>/fastswap-v1/` with `cp -a`, and start the units. The restored store
is the legacy store again, so FastSwap stays unavailable on that host.

## Moving the FastSwap store to the activated committee epoch

The FastSwap service reads its committee only from `fastswap-v1/committee.json` and
`base-state.json`; it never follows the chain, and only epoch 1 is provisioned
automatically (`crates/node/src/fastswap_service.rs`). After `ActivateCommittee`
(epoch 2 at height 1131, root `72836827…`), each validator needs the offline
`fastswap-committee-migrate` from the next release. It ships with that release
and changes only files under `fastswap-v1/`, not consensus or execution.

The command takes the store lock (refuses if held) and replays the store as the
service does: the snapshot if present, else base plus WAL. It checks the drained
state against the anchor file: no reservations, no pending burns, canonical
epoch-1 fences, and every root and total equal to the anchored checkpoint
(`355fe608…`). Otherwise it refuses with the reason. A store that never applied
the fence or the anchor (validator-5) is refused unless its replayed state still
equals the anchored drained state; the report then carries a note. It backs up
`fastswap-v1/` (fsync, SHA3-384 manifest) and writes the epoch-2 `committee.json`
and `base-state.json` (0600, atomic). The epoch-2 base keeps the objects, drops the
epoch-1 fences and records the anchor. It moves the WAL and snapshot aside into the
backup, then verifies with a normal service open: epoch 2, the new root, enabled.
Any failure restores the backup. The JSON report gives the before and after domain,
epoch, root, fences and file hashes, the backup manifest and the verification.

Per host, validator-5 first, then validators 0–4, one at a time:

1. Stop both units; `systemctl is-active` shows both inactive.
2. As root: `install -d -o postfiat -g postfiat -m 700 /var/lib/postfiat/fastswap-v1-epoch2-backup-validator-N`.
3. As `postfiat`, dry run: `postfiat-node fastswap-committee-migrate --data-dir /var/lib/postfiat/validator-N --committee-file 7.2-activate-committee.fastlane-primary.json --anchor-file 7.1-anchor-checkpoint.fastlane-primary.json --dry-run`.
   Expect `would-migrate`; read `notes`. Both files are in the release packet's
   `observed/bridge-activation/`.
4. Real run: the same command with `--backup-dir /var/lib/postfiat/fastswap-v1-epoch2-backup-validator-N`
   instead of `--dry-run`. Expect `migrated` and `service open: committee epoch 2, root 72836827…, enabled true`.
5. Start both units. `fastswap_capabilities` shows epoch 2, root `72836827…` and
   `enabled: true`; `fastswap_checkpoint_status` answers.

Rollback: stop both units, restore `fastswap-v1/` from the backup directory with
`cp -a`, and start the units.

The migration is harmless before the issuer's route update. Epoch-2 FastLane
checkpoint votes stay local until someone submits an `AnchorCheckpoint`.
Ethereum checkpoint signing follows the route's `authority_epoch`, which stays 1
until that update.

### The wallet's activation payload for the current committee

A wallet's FastSwap activation file (`payload.json`, for example StakeHub's
`~/.pft/venue/fastswap-activation/h<height>/payload.json`) carries the committee
domain the swap service checks. A file written before the migration describes
epoch 1. `fastswap_bootstrap_payload --committee-file` writes the payload for the
committee an `ActivateCommittee` installed. It is offline and reads only files.

- **The committee:** taken from the record's `operation.certificate.action.committee`,
  read the same way as `fastswap-committee-migrate --committee-file`, and
  validated against its own root.
- **The rules and policy:** rebuilt exactly as for the bootstrap. They must equal
  a policy the ledger governs (`fastswap_policy_snapshots`).
- **The activation height:** must be the ledger's recorded
  `fastswap_activation_height`.
- **The inputs:** `--committee-file` replaces `--registry`. A validator's
  `ledger.json` and `chain_tip.json` can be used as they are; their trailing
  `pftmac1:` integrity line is node-keyed, so the tool reads the JSON body without
  verifying it.
- **Without `--committee-file`:** the tool writes the epoch-1 bootstrap payload
  byte for byte as before.

For the devnet's epoch 2 (root `72836827…`), with the July bootstrap values that
the ledger records (activation 152, policy epoch 1, NAV epoch 3, valid through
10000):

```bash
fastswap_bootstrap_payload \
  --ledger ledger.json --tip chain_tip.json \
  --committee-file 7.2-activate-committee.fastlane-primary.json \
  --activation-height 152 --valid-through-height 10000 \
  --asset-0-id 02c46a36eb0da3516b4d8affea8f4028ad3f36825a3e8f0e009ea9dbbbcfb3c233f6830bd5221fe2717fb6a1a7005d7b \
  --asset-1-id de8d3d78aca83f7000632cbd3dd06edd30d105085d16eef1696f9e1707908ec9209239080d21ca1c0cecc36ca6f966b6 \
  --price-numerator 1000000 --price-denominator 1000000 --nav-epoch 3 \
  --market-envelope-hash f31b5e66ba4d515cb4b29793c5ee41c8c1cd704c36e916c17a2c4d4ec4eaf735cf7881027460f3debe3da4c7e87fa765 \
  --output payload-epoch2.json
```

Expect `committee epoch=2 root=72836827…`. The committee domain's canonical-JSON
SHA-256 is `b1c5261b…`, the value StakeHub's check 0c′ prints. Run on 2026-10-23
against the height-1123 snapshot of the store-handle release and that release's
`observed/bridge-activation/7.2-activate-committee.fastlane-primary.json`
(SHA-256 `35acb2ff…`), it wrote a payload with SHA-256 `718fce15…`. Its policy
hash is the governed `356e5cca…`, and the 0c′ line is
`True True 2 72836827f9f3ecd3 b1c5261b…`, with an acceptance file that names
that payload.

The payload alone does not finish the switch:

- `fastswap_wallet_payload` builds `deposit` and `intent` under the committee epoch the payload declares, and keeps every other bootstrap rule. With `--committee-file 7.2-activate-committee.fastlane-primary.json`, it refuses a payload whose committee differs from the recorded one.
- The wallet's `ACCEPTANCE.json` names the payload by SHA-256.

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
