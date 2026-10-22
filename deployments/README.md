# Deployments

> **Internal engineering record.** Each directory is the record of one release
> or deployment: inputs, deploy sheets, signed manifests, receipts and observed
> rollout data, written at the time. A directory here does not mean the release
> is running now. For what runs on the network, read
> [Network Status](../docs/status/network-status.md) and the full log in
> [Current State](../docs/status/chain-state-current.md).

Directory names are `<release-or-route>-<YYYYMMDD>`, for example
`storage-lease-20260831` or `combined-fastpay-20260928`. Releases deployed
after 2026-09-28 (`signer-rotation-20261007`, `fastlane-cap-20261014`,
`store-handle-20261021`) keep their records on their `release/*` branches; the
Current State log links to them.

Scripts and receipts refer to these paths, so do not move or rename them.
