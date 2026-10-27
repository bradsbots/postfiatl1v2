# Signed validator snapshot recovery

Status: controlled-testnet operator procedure

This procedure replaces manual validator-directory copying. It preserves the
chain state and mempool policy while excluding validator keys, faucet private
keys, leases, sockets, logs, RPC spool files, and the certified-send outbox.

## Safety gates

- Stop and fence the validator being replaced before assigning its signer.
- Keep the failed disk or image for forensics; do not repair the only copy.
- Never copy `validator_keys.json`, `faucet_key.json`, deployment private keys,
  or another validator's signing identity into the snapshot.
- Import into a new empty directory. Do not overlay a live data directory.
- The replacement remains RPC/read-only until chain, genesis, protocol,
  height, tip, state root, and signed publisher identity all verify.

## One-time publisher key

Use a dedicated snapshot publisher key. It is not a validator key.

```text
postfiat-node snapshot-publisher-key-export \
  --publisher-key-file /secure/snapshot-publisher.private.json \
  --public-key-file /etc/postfiat/snapshot-publisher.public.json
```

Distribute the public file through the pinned deployment configuration. Keep
the private file outside validator data directories and snapshots.

## Export

Quiesce writes or export from a verified recovery copy, then run:

```text
postfiat-node snapshot-export-signed \
  --data-dir /var/lib/postfiat/validator-healthy \
  --snapshot-dir /srv/postfiat/snapshots/height-N \
  --publisher-key-file /secure/snapshot-publisher.private.json
```

The command verifies governance, bridge, shielded state, mempool, and block
history before export. The signed manifest binds:

- chain ID, genesis hash, protocol version, source node, state root, height,
  tip hash, and last certificate ID;
- the source build revision/profile;
- the explicit `preserve-verified-empty-or-pending` mempool policy;
- every replicated file's byte length and content hash; and
- `signer_material_included=false`.

Archive the complete snapshot directory by content hash. Do not add excluded
runtime or key files afterward.

## Import and replacement

Provision a fresh directory and the replacement validator's own isolated
signer. Then run:

```text
postfiat-node snapshot-import-signed \
  --data-dir /var/lib/postfiat/validator-replacement \
  --snapshot-dir /srv/postfiat/snapshots/height-N \
  --trusted-publisher-key-file /etc/postfiat/snapshot-publisher.public.json \
  --node-id validator-0
```

Import verifies the publisher signature before reading state, verifies every
file hash and byte length, writes into the new directory atomically, replaces
only the public node ID, then re-verifies chain/genesis/protocol/root/height/
tip plus governance, bridge, shielded, mempool, and block history.

Install the replacement validator's signer separately. Confirm the old host is
fenced and that exactly one signer can answer before enabling transport.

## Cold and warm restart drill

Record monotonic time for each drill:

1. `time-to-first-read`: process start until local `status` succeeds.
2. `time-to-ready`: process start until both circuit verifiers are warm, the
   deployment manifest is loaded, RPC health is green, and the transport ready
   marker exists.
3. Run a warm restart of the imported copy without changing files.
4. Run a cold restart after dropping only operating-system page cache on the
   disposable recovery host; do not mutate chain state.
5. Require the identical height, tip, and root after both restarts.

Store timings with the snapshot and deployment-manifest hashes. A test result
without those identities is not comparable evidence.

## Rollback

If signature, content hash, domain identity, state root, or signer uniqueness
fails, keep transport disabled, stop the replacement, preserve its logs and
directory, and return traffic to the still-fenced known-good validator. Never
edit the signed snapshot to make import pass; create a new signed export after
the source problem is understood.

## Vote outcome records (SCT-08 item 4)

For the native reliability input
([decision](../review/sct08-evidence-campaign-20261023.md#decision-the-native-reliability-input-2026-10-23)),
the proposer of each certified batch round keeps one vote record per
finalized height:

```text
<data-dir>/block-vote-records/height-<20-digit height>.json
```

Each record (`postfiat.block_vote_record.v1`) names the height, view, block
hash, certificate ID, proposer, quorum and round deadline (`--timeout-ms`),
and has one entry per validator the round asked, the proposer included:

- `accepted` with its `vote_id`;
- `refused` with a `refusal_class`, the validator's reason without paths or
  quoted values;
- `late_after_deadline` with its `vote_id`: an accepted vote that arrived
  after the round deadline but before the record was written;
- `no_answer`: the writer received no answer from the validator (no
  connection, a failed read, or nothing by the time the record was written).

`answered_after_quorum` marks an answer that arrived after the last vote the
quorum needed. In a quorum-early round (`--allow-peer-failures` or
`--quorum-early-full-propagation`), such a vote is recorded but is not in the
certificate. The record writer waits for missing answers until the round
deadline and then takes every answer already received before it classifies
them, so a vote that arrived after the quorum and inside the deadline is
`accepted` with `answered_after_quorum: true`, also when the round reaches the
writer only at the deadline (a full-propagation send to a slow validator holds
the round up to its timeout). An answer that arrives after the record is
written is not seen: the record is written once and that entry stays
`no_answer`. Records that contain `late_after_deadline` (written by builds with
the VR-01 fix) cannot be read by the `index-v3-20261027` executable or an older
`vote_reliability.py`. Only the
proposer writes the record, after the block and its receipts are durable.
Each validator therefore holds the records of the heights it proposed. A
record is written once: a restart never rewrites it, and a failed write never
fails the round. A height without a record is **not available**; the
reliability window then holds on `missing_reliability`.

Per validator, count accepted votes over a window of records:

```bash
jq -r '.entries[] | select(.outcome == "accepted") | .validator' \
  /var/lib/postfiat/validator-0/block-vote-records/height-*.json | sort | uniq -c
```

That counts one proposer's records. For the reliability window over all six
directories, with the not-available rule, use `python -m
postfiat_rpc.vote_reliability`
([campaign](../review/sct08-evidence-campaign-20261023.md#deriving-the-fact-from-the-vote-records-2026-10-26)).

**Not yet in the signed snapshot.** `snapshot-export-signed` does not carry
these records yet; adding them needs a new snapshot version (follow-up). Until
then, read them from each validator's data directory.
