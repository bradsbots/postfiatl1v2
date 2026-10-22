# Quantum Authorization

PostFiat starts the base transparent account and validator authorization paths
with ML-DSA-style signatures.

## Why

A new settlement chain does not need to begin with long-lived classical account
and validator keys and hope to migrate later. If quantum migration risk matters
on an institutional horizon, the chain should price larger signatures and
certificates from genesis.

## What Exists

- post-quantum account signing flows;
- wallet vectors;
- post-quantum validator transport envelopes;
- certificate handling for larger signature material;
- ML-DSA performance and size evidence;
- SDK wallet finality using signed transparent transfers.

## ML-DSA Certificate Structure

```mermaid
flowchart TD
  Header[Block header<br/>height, parent, state root,<br/>payload hash, certificate digest]
  Cert[Detached ML-DSA certificate<br/>registryRoot<br/>certificate domain<br/>validator signatures]
  Pair1[validatorID + ML-DSA signature]
  Pair2[validatorID + ML-DSA signature]
  PairN[validatorID + ML-DSA signature]
  Registry[Active registry root<br/>validator identities and public keys]
  Quorum[Quorum check<br/>q = floor(2n/3) + 1]

  Header --> Cert
  Cert --> Pair1
  Cert --> Pair2
  Cert --> PairN
  Cert --> Registry
  Pair1 --> Quorum
  Pair2 --> Quorum
  PairN --> Quorum
  Registry --> Quorum
```

## Post-Quantum Authorization Flow

```mermaid
flowchart LR
  Wallet[Wallet signs transaction<br/>ML-DSA account key]
  Submit[Submit signed transfer<br/>bounded write path]
  Validators[Validators verify<br/>signature, sequence, fee, balance]
  Order[Order and certify block<br/>validator ML-DSA votes]
  Header[Block header commits<br/>detached certificate digest]
  Audit[Audit nodes fetch certificate<br/>and re-verify signatures<br/>against registryRoot]

  Wallet --> Submit --> Validators --> Order --> Header --> Audit
```

## Recovery Path

What exists today (updated 2026-10-22):

- **Validator keys.** A compromised or lost validator key is replaced through a
  governed validator-registry update. The replacement is another ML-DSA-65 key;
  after activation, the old key's staging and votes are rejected
  ([validator emergency key rotation](../runbooks/validator-emergency-key-rotation.md)).
  On the devnet, Cobalt ratified such a rotation for validator 5 at height 924
  ([Cobalt adversarial results](../governance/cobalt-adversarial-verification-results.md)).
- **Account keys.** No account key-rotation transaction exists. An address binds
  its ML-DSA public key on first spend, and later spends must use that key. If a
  key may be compromised but still works, sweep the funds to a fresh address. The
  protocol cannot recover a lost key
  ([account key rotation boundary](../specs/account-key-rotation-boundary.md)).
- **SLH-DSA.** No SLH-DSA (FIPS 205) key, genesis commitment, verifier or
  activation path exists in the code.

```mermaid
flowchart TD
  subgraph Today[Implemented today]
    Lost[Validator key compromised or lost]
    Update[Governed validator-registry update<br/>current-registry ML-DSA authorizations]
    NewKey[Replacement ML-DSA-65 key active<br/>old-key votes rejected]
    Lost --> Update --> NewKey
  end

  subgraph Proposed[Proposed, not implemented]
    Monitor[ML-DSA break or credible emergency]
    Emergency[Governed emergency path<br/>freeze affected authorization class]
    SLH[Activate SLH-DSA recovery keys<br/>committed at genesis]
    Rotate[Rotate validator and account authority<br/>old ML-DSA path rejected or constrained]
    Monitor -.-> Emergency -.-> SLH -.-> Rotate
  end
```

The proposed SLH-DSA fallback needs a complete FIPS 205 key commitment,
verification, governance activation, migration and recovery ceremony, with its
own tests, before it can be described as available
([cryptography inventory](../status/OPEN-SOURCE-CRYPTOGRAPHY-INVENTORY-20260716.md)).

## Sources

- `crates/crypto_provider/src/lib.rs`
- `crates/types/src/lib.rs`
- `crates/node/src/transport_cli.rs`
- `crates/rpc_sdk/src/lib.rs`
- `scripts/testnet-ml-dsa-performance-smoke` *(archived outside this repository; see `scripts/README.md`)*
- `scripts/testnet-wallet-test-vectors-smoke` *(archived outside this repository; see `scripts/README.md`)*
