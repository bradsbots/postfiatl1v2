# Network Status

**As of 2026-10-22.** This page is a short summary copied from recorded
observations. It is not a live query. The full, dated operating log is
[Current State](chain-state-current.md); when the two disagree, the log wins.

## In one paragraph

Post Fiat L1 runs one network today: `postfiat-wan-devnet-2`, a controlled
devnet (developer network) run by six Foundation-administered validators. The
source code is public, but outside validators cannot join and no public RPC
endpoint is published. It is not a production mainnet, no public testnet is
open, and the software has not been externally audited. Do not put real value
on it. See [Security](../security/index.md) for the audit and release-gate
position.

## Network facts

| Item | Value | Source |
| --- | --- | --- |
| Chain ID | `postfiat-wan-devnet-2` | [Current State](chain-state-current.md#last-observed-devnet-values) |
| Genesis hash | `ce22ca8c932da0998b484483a09647138a30e0bf44408dd49a8d6d452787ad25521aff3ed334da07e150a7233a3e90a9` | [Current State](chain-state-current.md#last-observed-devnet-values) |
| Validators | 6, all Foundation-administered; the devnet accepts no outside validators | [Cobalt](../governance/cobalt.md), [Public Operator Runbook](../runbooks/public-operator-runbook.md) |
| Block finality | Consensus v2 (prepare/precommit with a commit quorum certificate) | [Finality](../architecture/finality.md) |
| Quorum | 5 of 6 (`q = floor(2n/3) + 1`; tolerates `f = 1` faulty validator) | [Finality](../architecture/finality.md) |
| Validator-trust governance | Cobalt, active since height 916; it ratifies validator-registry and trust-graph changes only and does not order or finalize blocks | [Cobalt](../governance/cobalt.md) |
| Signatures | ML-DSA-65 (FIPS 204) for accounts and validators | [Addresses, Keys And Signatures](../integrate/addresses-keys-signatures.md) |
| Native asset | PFT; 1 PFT = 1,000,000 atoms; fees burn | [Exchange Integration Guide](../integrate/exchange-guide.md#fees) |

## Current release and height

Recorded on 2026-10-21 in [Current State](chain-state-current.md):

| Item | Value |
| --- | --- |
| Release | `store-handle-20261021` (source `86706699`, branch `release/store-handle-20261021`) |
| Node executable SHA-256 | `eea96ba6761ed223047d7781663100d34efe5641d36031bd50874bd9c8b41f36` on all 12 validator and RPC processes |
| Rollout | One validator at a time with `scripts/postfiat-safe-rollout apply-next`, 2026-10-21 11:15–11:38 UTC; no rollback needed |
| Height | 1137 on all six validators (tip `18a4dc86…`, state root `1277c76c…`) |
| Latest fleet observation | 2026-10-21 12:30:55 UTC |

The chain makes blocks only when there are transactions to order, so height
does not advance with wall-clock time. A height that has not moved for days is
normal on this devnet.

## Other running components

- **Storage.** The transactional `redb` storage engine has been active on the
  devnet since height 930 (2026-08-31). The storage-scaling milestone's offline
  qualification packet (gate G5) is not yet assembled as of 2026-10-22; see the
  [storage scaling milestone](../plans/completed/storage-scaling-milestone.md).
- **FastPay and FastSwap.** FastPay's epoch-2 recovery committee was installed
  at height 1123 (2026-10-12). The FastSwap service runs at committee epoch 2
  on all six validators since 2026-10-21. These are certificate lanes beside
  block consensus; see [Settlement Lanes](../architecture/settlement-lanes.md).
- **Validator keys.** Plaintext software key files; HSM or remote signing is not
  implemented. The generated validator units run with
  `--unsafe-devnet-file-signer` and `--unsafe-devnet-json-storage`, and the RPC
  units with `--unsafe-devnet-json-storage`; the services refuse to start
  without these acknowledgements (`crates/node/src/batch_snapshot.rs`,
  [SECURITY.md](https://github.com/postfiatorg/postfiatl1v2/blob/main/SECURITY.md)).

## Access

This repository does not publish a public RPC endpoint for
`postfiat-wan-devnet-2`. Validator RPC listeners bind to loopback and are
reached through an operator-managed authenticated TLS edge
([Public RPC Operator Policy](../runbooks/public-rpc-operator-policy.md)).
To experiment without access, run a local devnet (see
[First Day](../start/first-day.md)).

The `rpc.testnet.postfiat.org` endpoint that appears in governance documents
serves the separate, rippled-derived PFT Ledger, not this chain (see the
[Task Node UNL shadow run](../governance/tasknode-unl-shadow-run-20260904.md)
and the [Glossary](../start/glossary.md#pftl-pft-ledger-and-postfiatd)).

## What is still open

- **Gate Zero** (Z1–Z3) is open: no community-facing step starts until all three
  close. See [Testnet Path](testnet-path.md).
- **Release gates:** 4 done, 16 open, 1 unknown in the
  [Release Gate Inventory](release-gate-inventory.md) (dated 2026-09-01).
- **External audit:** none is recorded in this repository. See
  [Security](../security/index.md).

## How to keep this page current

Update this page when a release is deployed or a fleet observation changes the
facts above. Copy values from [Current State](chain-state-current.md), keep the
"As of" date, and do not add anything that is not recorded there.
