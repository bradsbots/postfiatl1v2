# Custody And Exchange

Custody and exchange support has two tracks:

1. transparent post-quantum account operations;
2. shielded Orchard workflows with scanning, disclosure, and policy review.

## Transparent Track

- account creation;
- fee quote;
- signed transfer;
- receipt/finality verification;
- account history and reconciliation.

## Addresses

- Signed transactions and on-chain state use only the canonical lowercase
  address, `pf` + 40 hex characters.
- Wallets may display and accept an optional mixed-case checksum.
- Nodes reject malformed destination addresses at RPC submission and mempool
  admission, and at execution from a governed activation height.

The format, checksum algorithm, error codes and test vectors are in
[Addresses And Checksums](address-format.md).

## Shielded Track

- receive/view key management;
- deposit address management;
- scan-only monitoring;
- selective disclosure;
- withdrawal review;
- policy and compliance workflows.

## Current Source

- `docs/specs/wallet-exchange-custody-model.md`
- `docs/specs/account-key-rotation-boundary.md`
- `docs/specs/transparent-transaction-envelope.md`
