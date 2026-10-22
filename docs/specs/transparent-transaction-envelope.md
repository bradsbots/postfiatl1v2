# Transparent Transaction Envelope v1

Status: canonical v1 transparent-transfer envelope
Date: 2026-05-13
Updated: 2026-10-22 (code references and fixture outputs)
Scope: controlled-testnet transparent PQ settlement path

This document freezes the current transparent transfer signing surface. Any
change to these bytes is a protocol change and must use a new version label or
new envelope kind. The purpose is to make wallet, RPC, mempool, execution, and
external review agree on exactly what is signed and replay-protected.

## Implemented Code References

References name the file and symbol, so they survive line moves.

- Unsigned transfer fields and signing bytes: `UnsignedTransfer` and
  `UnsignedTransfer::signing_bytes` in
  [`crates/types/src/transactions_mempool_receipts.rs`](https://github.com/postfiatorg/postfiatl1v2/blob/main/crates/types/src/transactions_mempool_receipts.rs).
- Signed transfer envelope: `SignedTransfer` in the same file.
- Transfer execution and replay/domain rejection: `execute_transfer` in
  [`crates/execution/src/entrypoints.rs`](https://github.com/postfiatorg/postfiatl1v2/blob/main/crates/execution/src/entrypoints.rs).
- Transfer transaction id: `transfer_tx_id` in
  [`crates/execution/src/tx_hashing.rs`](https://github.com/postfiatorg/postfiatl1v2/blob/main/crates/execution/src/tx_hashing.rs).
- Wallet deterministic test vector: `wallet_test_vector` in
  [`crates/node/src/block_replay_wallet.rs`](https://github.com/postfiatorg/postfiatl1v2/blob/main/crates/node/src/block_replay_wallet.rs).
- Test-vector drift lock: the test `wallet_test_vector_is_deterministic_and_redacted` in
  [`crates/node/src/tests/helpers_orchard_transfer_escrow.rs`](https://github.com/postfiatorg/postfiatl1v2/blob/main/crates/node/src/tests/helpers_orchard_transfer_escrow.rs).
- Mempool admission for externally signed transfers:
  `submit_signed_transfer_to_mempool`, `submit_signed_transfer_json_to_mempool`
  and `admit_signed_transfer_to_mempool` in
  [`crates/node/src/mempool_proposals.rs`](https://github.com/postfiatorg/postfiatl1v2/blob/main/crates/node/src/mempool_proposals.rs).

## Unsigned Envelope Fields

`UnsignedTransfer` contains these fields, in the canonical order used for
signing bytes:

1. `chain_id`
2. `genesis_hash`
3. `protocol_version`
4. `address_namespace`
5. `transaction_kind`
6. `signature_algorithm_id`
7. `from`
8. `to`
9. `amount`
10. `fee`
11. `sequence`

Controlled-testnet transparent transfers currently use:

- `address_namespace = postfiat.address.v1`
- `transaction_kind = transparent_transfer`
- `signature_algorithm_id = ML-DSA-65`
- `protocol_version = 1`

## Signing Bytes

The signed message is UTF-8 text with newline-delimited `key=value` fields. It
has a leading version label and a trailing newline after `sequence`.

```text
postfiat.transfer.v1
chain_id={chain_id}
genesis_hash={genesis_hash}
protocol_version={protocol_version}
address_namespace={address_namespace}
transaction_kind={transaction_kind}
signature_algorithm_id={signature_algorithm_id}
from={from}
to={to}
amount={amount}
fee={fee}
sequence={sequence}
```

There is no implicit serialization, field sorting, or optional-field omission
inside the signing bytes. The order above is consensus-critical.

## Signature And Transaction Id

The transparent path signs the exact bytes above with ML-DSA-65 using the
transaction signature context `postfiat-l1-v2/tx/v1`.

`SignedTransfer` then carries:

- `unsigned`
- `algorithm_id`
- `public_key_hex`
- `signature_hex`

The transaction id is:

```text
hash_hex("postfiat.tx_id.v1", bytes)
```

where `bytes` is the unsigned signing bytes followed by:

```text
algorithm={algorithm_id}
public_key={public_key_hex}
signature={signature_hex}
```

with newline separators and a trailing newline.

## Replay And Domain Binding

The envelope is bound to a specific network by `chain_id`, `genesis_hash`, and
`protocol_version`. Execution rejects mismatches before applying balance state.

Replay controls currently implemented:

- wrong chain id is rejected as `wrong_chain`;
- wrong genesis hash is rejected as `wrong_genesis`;
- wrong protocol version is rejected as `wrong_protocol_version`;
- wrong address namespace is rejected as `wrong_address_namespace`;
- wrong transaction kind is rejected as `wrong_transaction_kind`;
- unsupported algorithm ids are rejected;
- bad ML-DSA signatures are rejected;
- duplicate transaction ids are rejected at mempool admission;
- duplicate pending sender sequences are rejected at mempool admission;
- ledger sequence rules reject non-next sender sequences at execution.

None of these rejections is charged. After the governed
`rejected_tx_fee_activation_height`, a transfer that passes every check above
and can pay its fee while keeping the account reserve, but whose effect fails
(for example `insufficient_funds` for the amount), pays its fee (burned),
consumes its sequence, and returns `tec_<reason>`; see
[Custody And Exchange](../wallets/custody-and-exchange.md#rejected-transactions-pay-their-fee).

The v1 transparent envelope does not include an expiry field. Adding expiry,
memo, multi-operation payloads, batching fields, or alternative fee semantics
must create a versioned envelope change instead of silently extending
`postfiat.transfer.v1`.

## Canonical Fixture

The public fixture is intentionally deterministic and must not be funded.

Inputs:

- `chain_id = postfiat-vector-test`
- `validator_count = 5`
- `master_seed_hex = 000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f`
- `account_index = 0`
- `to = pfvectortestrecipient000000000000000001`
- `amount = 17`
- `sequence = 1`
- `signature_seed_hex = 1f1e1d1c1b1a191817161514131211100f0e0d0c0b0a09080706050403020100`

Expected public outputs:

- `genesis_hash = aa450fa2d12a9d10e290266df634b9319d8805450a85bedcbd4d72ec9dbbc7c4d4cca350a3202bf1e58ee01b4dbca732`
- `from = pf857c81edb95af1d64262ed6c0fdcf3ef7aff56fe`
- `fee = 32`
- `transfer_signing_hash = b7ded680cf9ee025253aa8dcedde3b1e090f5853ea681fb240cf8579b5e4de8cf665df97e231d0d565ff91c37dc84189`
- `tx_id = 99991ac80058445af49c45ace67bdc837fcd0dff85f4a15aae3ec05640fc9db1a2ae2270ec4653ec5aa59b262e59c764`

Expected signing bytes:

```text
postfiat.transfer.v1
chain_id=postfiat-vector-test
genesis_hash=aa450fa2d12a9d10e290266df634b9319d8805450a85bedcbd4d72ec9dbbc7c4d4cca350a3202bf1e58ee01b4dbca732
protocol_version=1
address_namespace=postfiat.address.v1
transaction_kind=transparent_transfer
signature_algorithm_id=ML-DSA-65
from=pf857c81edb95af1d64262ed6c0fdcf3ef7aff56fe
to=pfvectortestrecipient000000000000000001
amount=17
fee=32
sequence=1
```

The drift lock in `wallet_test_vector_is_deterministic_and_redacted` asserts
these bytes, the signing hash, and the transaction id. The outputs above were
copied from that test on 2026-10-22, when it passed. Earlier revisions of this
page listed a different fixture genesis hash, signing hash and transaction id;
the test has asserted the values above since the first public commit
(`11839c14f`). The signing-byte format is unchanged.
