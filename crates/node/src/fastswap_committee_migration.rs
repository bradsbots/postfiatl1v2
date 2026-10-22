//! Offline `postfiat-node fastswap-committee-migrate`: move a stopped
//! validator's FastSwap store from the drained committee epoch to the next
//! canonically activated epoch. Read-only toward consensus: it changes only
//! files under `fastswap-v1/`. Runbook: docs/runbooks/fastpay-committee-recovery.md.

use super::*;
use postfiat_crypto_provider::bytes_to_hex;
use postfiat_storage::fastswap_store::{
    backup_fastswap_store, encode_fastlane_state_file, fastswap_file_sha3_384,
    load_fastswap_store_read_only, lock_fastswap_store_offline, remove_fastswap_wal_and_snapshot,
    restore_fastswap_store_backup, write_fastswap_file_owner_only, FastSwapBackupFileV1,
};
use postfiat_types::{
    FastLaneCheckpointCertificateV1, FastLaneCheckpointV1, FastLanePrepareFenceV1,
};
use serde::Serialize;
use std::path::PathBuf;

const STORE_FILES: [&str; 4] = [
    FASTSWAP_COMMITTEE,
    FASTSWAP_BASE_STATE,
    "fastswap-v1.snapshot.json",
    "fastswap-v1.wal",
];

pub(crate) struct FastSwapCommitteeMigrationOptions {
    pub(crate) data_dir: PathBuf,
    pub(crate) committee_file: PathBuf,
    pub(crate) anchor_file: PathBuf,
    pub(crate) backup_directory: Option<PathBuf>,
    pub(crate) validator_id: Option<String>,
    pub(crate) dry_run: bool,
}

#[derive(Debug, Serialize)]
pub(crate) struct FastSwapCommitteeSideV1 {
    pub(crate) committee_epoch: u64,
    pub(crate) committee_root: String,
    pub(crate) domain: postfiat_types::FastSwapCommitteeDomainV1,
    pub(crate) prepare_fences: Vec<FastLanePrepareFenceV1>,
    pub(crate) anchored_checkpoints: Vec<String>,
    pub(crate) objects: usize,
    pub(crate) file_sha3_384: std::collections::BTreeMap<String, Option<String>>,
}

#[derive(Debug, Serialize)]
pub(crate) struct FastSwapCommitteeMigrationReport {
    pub(crate) schema: &'static str,
    pub(crate) store_directory: String,
    pub(crate) validator_id: String,
    pub(crate) dry_run: bool,
    /// `would-migrate` or `migrated`.
    pub(crate) outcome: String,
    /// `snapshot` or `base+wal`.
    pub(crate) load_path: &'static str,
    pub(crate) wal_records: usize,
    pub(crate) replayed_wal_records: usize,
    pub(crate) anchor_checkpoint_id: String,
    pub(crate) notes: Vec<String>,
    pub(crate) before: FastSwapCommitteeSideV1,
    pub(crate) after: FastSwapCommitteeSideV1,
    pub(crate) backup_directory: Option<String>,
    pub(crate) backup_manifest: Vec<FastSwapBackupFileV1>,
    pub(crate) moved_aside: Vec<String>,
    pub(crate) verification: String,
}

#[cfg(test)]
thread_local! {
    pub(super) static FAIL_AFTER_WRITE: std::cell::Cell<bool> = const { std::cell::Cell::new(false) };
}

/// The drained → next-epoch transform shared with the service's own
/// migration check: same objects, the new committee domain, no fence of the
/// drained epoch, and the anchored drain checkpoint recorded (its pending fee
/// burns are empty by the drain check).
pub(super) fn migrate_drained_fastlane_state(
    drained: &FastLaneStateV1,
    next: &postfiat_types::FastSwapCommitteeDomainV1,
    anchored_checkpoint: Option<FastLaneCheckpointIdV1>,
) -> FastLaneStateV1 {
    let mut migrated = drained.clone();
    migrated.committee = next.clone();
    migrated
        .prepare_fences
        .retain(|_, fence| fence.committee_epoch == next.committee_epoch);
    migrated.anchored_checkpoints.extend(anchored_checkpoint);
    migrated
}

/// Checkpoint fields that differ between `state` and the anchored checkpoint.
pub(super) fn drain_checkpoint_mismatches(
    state: &FastLaneStateV1,
    ledger: &LedgerState,
    anchored_id: FastLaneCheckpointIdV1,
    anchored: &FastLaneCheckpointV1,
) -> Result<Vec<&'static str>, String> {
    let candidate = build_fastlane_checkpoint(state, ledger, Some(anchored_id), 0)
        .map_err(|error| format!("checkpoint of the loaded state failed: {error:?}"))?;
    let fields = [
        (
            "live_object_root",
            candidate.live_object_root == anchored.live_object_root,
        ),
        (
            "live_object_totals",
            candidate.live_object_totals == anchored.live_object_totals,
        ),
        (
            "exit_claim_root",
            candidate.exit_claim_root == anchored.exit_claim_root,
        ),
        (
            "exit_claim_totals",
            candidate.exit_claim_totals == anchored.exit_claim_totals,
        ),
        (
            "terminal_root",
            candidate.terminal_root == anchored.terminal_root,
        ),
        (
            "active_policy_hashes",
            candidate.active_policy_hashes == anchored.active_policy_hashes,
        ),
        (
            "imported_deposit_root",
            candidate.imported_deposit_root == anchored.imported_deposit_root,
        ),
        (
            "redeemed_exit_claim_root",
            candidate.redeemed_exit_claim_root == anchored.redeemed_exit_claim_root,
        ),
    ];
    Ok(fields
        .into_iter()
        .filter_map(|(name, equal)| (!equal).then_some(name))
        .collect())
}

pub(crate) fn fastswap_committee_migrate(
    options: &FastSwapCommitteeMigrationOptions,
) -> Result<FastSwapCommitteeMigrationReport, String> {
    let directory = options.data_dir.join(FASTSWAP_DIRECTORY);
    if !directory.is_dir() {
        return Err(format!(
            "FastSwap store `{}` does not exist",
            directory.display()
        ));
    }
    let lock = lock_fastswap_store_offline(&directory, options.dry_run)
        .map_err(|error| format!("store lock: {error}; stop both validator units first"))?;
    let next = read_committee_file(&options.committee_file)?;
    let (anchor_id, anchor_certificate) = read_anchor_file(&options.anchor_file)?;
    let ledger = NodeStore::new(&options.data_dir)
        .read_ledger()
        .map_err(|error| format!("canonical ledger read failed: {error}"))?;
    let current: FastSwapCommitteeV1 = read_bounded_json(&directory.join(FASTSWAP_COMMITTEE))
        .map_err(|error| format!("{FASTSWAP_COMMITTEE}: {error}"))?;
    let mut base = read_fastlane_base_state(&directory.join(FASTSWAP_BASE_STATE))
        .map_err(|error| format!("{FASTSWAP_BASE_STATE}: {error}"))?;
    if current.validate().is_err() || current.domain != base.committee {
        return Err("store committee.json and base-state.json domains differ".to_owned());
    }
    let old_epoch = current.domain.committee_epoch;
    if next.domain.committee_epoch != old_epoch + 1 || next.domain.chain != current.domain.chain {
        return Err(format!(
            "committee file is epoch {} on another chain or not the epoch after the store's epoch {old_epoch}",
            next.domain.committee_epoch
        ));
    }
    if ledger.fastswap_committees.last() != Some(&next) {
        return Err(format!(
            "committee file (epoch {}, root {}) is not the latest canonically registered committee",
            next.domain.committee_epoch,
            bytes_to_hex(&next.domain.committee_root.0)
        ));
    }
    if !ledger.fastswap_committees.contains(&current) {
        return Err("store committee is not registered in canonical ledger state".to_owned());
    }
    let anchored = verify_fastlane_checkpoint_certificate(&current, &anchor_certificate)
        .map_err(|error| format!("anchor file is not a valid checkpoint certificate of the store committee: {error:?}"))?;
    if !ledger.fast_lane_checkpoint_anchors.iter().any(|anchor| {
        anchor
            .votes
            .first()
            .and_then(|vote| vote.checkpoint.checkpoint_id().ok())
            == Some(anchor_id)
    }) {
        return Err(format!(
            "anchor checkpoint {} is not anchored in canonical ledger state",
            bytes_to_hex(&anchor_id.0)
        ));
    }
    if !anchored.drain_ready
        || !anchored.exit_claim_totals.is_empty()
        || !anchored.pending_fee_burn_totals.is_empty()
    {
        return Err("anchor checkpoint is not a drained final checkpoint".to_owned());
    }
    let validator_id = resolve_validator_id(options, &next)?;

    // Load exactly as the service does: canonical controls override the base.
    base.asset_rules = ledger
        .fast_lane_asset_rules
        .iter()
        .map(|rule| rule.rule_hash().map(|hash| (hash, rule.clone())))
        .collect::<Result<_, _>>()
        .map_err(|error| format!("asset rule hash failed: {error:?}"))?;
    base.holder_permits = ledger
        .fast_lane_holder_permits
        .iter()
        .map(|permit| (permit.permit_id, permit.clone()))
        .collect();
    base.policy_snapshots = ledger
        .fastswap_policy_snapshots
        .iter()
        .map(|policy| (policy.policy_hash, policy.clone()))
        .collect();
    let loaded = load_fastswap_store_read_only(&directory, &base)
        .map_err(|error| format!("store replay failed: {error}"))?;
    let state = &loaded.state;
    let notes = check_drained(state, &ledger, old_epoch, anchor_id, &anchored, &loaded)?;
    let migrated = migrate_drained_fastlane_state(state, &next.domain, Some(anchor_id));
    verify_migrated_committee_base(&migrated, &ledger, &next)
        .map_err(|error| format!("migrated base refused by the service check: {error}"))?;
    let base_bytes = encode_fastlane_state_file(&migrated).map_err(|error| format!("{error}"))?;
    let committee_bytes = serde_json::to_vec(&next).map_err(|error| error.to_string())?;

    let mut report = FastSwapCommitteeMigrationReport {
        schema: "postfiat-fastswap-committee-migration-v1",
        store_directory: directory.display().to_string(),
        validator_id: validator_id.clone(),
        dry_run: options.dry_run,
        outcome: "would-migrate".to_owned(),
        load_path: if loaded.snapshot_present {
            "snapshot"
        } else {
            "base+wal"
        },
        wal_records: loaded.wal_records,
        replayed_wal_records: loaded.replayed_wal_records,
        anchor_checkpoint_id: bytes_to_hex(&anchor_id.0),
        notes,
        before: side(&current.domain, state, file_hashes(&directory)?),
        after: side(
            &next.domain,
            &migrated,
            predicted_hashes(&base_bytes, &committee_bytes),
        ),
        backup_directory: None,
        backup_manifest: Vec::new(),
        moved_aside: Vec::new(),
        verification: "not run (dry run)".to_owned(),
    };
    if options.dry_run {
        drop(lock);
        return Ok(report);
    }

    let backup = options.backup_directory.clone().unwrap_or_else(|| {
        let seconds = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_or(0, |elapsed| elapsed.as_secs());
        directory.with_file_name(format!(
            "{FASTSWAP_DIRECTORY}.pre-committee-epoch-{}-{seconds}",
            next.domain.committee_epoch
        ))
    });
    report.backup_manifest = backup_fastswap_store(&directory, &backup)
        .map_err(|error| format!("backup refused: {error}"))?;
    report.backup_directory = Some(backup.display().to_string());
    let written = (|| -> Result<Vec<String>, String> {
        write_fastswap_file_owner_only(&directory.join(FASTSWAP_BASE_STATE), &base_bytes)
            .map_err(|error| format!("{error}"))?;
        write_fastswap_file_owner_only(&directory.join(FASTSWAP_COMMITTEE), &committee_bytes)
            .map_err(|error| format!("{error}"))?;
        remove_fastswap_wal_and_snapshot(&directory).map_err(|error| format!("{error}"))
    })();
    // The service open takes the store lock itself.
    drop(lock);
    let verified = written.and_then(|moved| {
        report.moved_aside = moved;
        #[cfg(test)]
        if FAIL_AFTER_WRITE.with(|flag| flag.replace(false)) {
            return Err("injected post-write verification failure".to_owned());
        }
        verify_open(&options.data_dir, &validator_id, &next)
    });
    match verified {
        Ok(verification) => {
            report.outcome = "migrated".to_owned();
            report.after.file_sha3_384 = file_hashes(&directory)?;
            report.verification = verification;
            Ok(report)
        }
        Err(error) => {
            let _relock = lock_fastswap_store_offline(&directory, false).map_err(|lock_error| {
                format!("{error}; restore could not lock the store: {lock_error}")
            })?;
            restore_fastswap_store_backup(&directory, &backup).map_err(|restore_error| {
                format!(
                    "{error}; RESTORE FAILED ({restore_error}); restore from {} by hand",
                    backup.display()
                )
            })?;
            Err(format!("{error}; store restored from {}", backup.display()))
        }
    }
}

fn check_drained(
    state: &FastLaneStateV1,
    ledger: &LedgerState,
    old_epoch: u64,
    anchor_id: FastLaneCheckpointIdV1,
    anchored: &FastLaneCheckpointV1,
    loaded: &postfiat_storage::fastswap_store::FastSwapStoreReadOnlyLoadV1,
) -> Result<Vec<String>, String> {
    let mut problems = Vec::new();
    if let Some((key, _)) = state.reservations.iter().next() {
        problems.push(format!(
            "{} open reservation(s) (first object {}:{})",
            state.reservations.len(),
            bytes_to_hex(&key.object_id.0),
            key.version
        ));
    }
    if !state.pending_fee_burns.is_empty() {
        problems.push(format!(
            "pending fee burns for {} asset(s)",
            state.pending_fee_burns.len()
        ));
    }
    for fence in state.prepare_fences.values() {
        let canonical = ledger.fast_lane_prepare_fences.iter().find(|candidate| {
            candidate.committee_epoch == fence.committee_epoch
                && candidate.policy_epoch == fence.policy_epoch
        });
        if fence.committee_epoch != old_epoch || canonical != Some(fence) {
            problems.push(format!(
                "prepare fence {{committee_epoch {}, policy_epoch {}, height {}}} is not a canonical epoch-{old_epoch} fence",
                fence.committee_epoch, fence.policy_epoch, fence.finalized_primary_height
            ));
        }
    }
    let unfenced = anchored
        .fenced_policy_epochs
        .iter()
        .filter(|policy_epoch| !state.prepare_fences.contains_key(policy_epoch))
        .copied()
        .collect::<Vec<_>>();
    let anchor_missing = !state.anchored_checkpoints.contains(&anchor_id);
    let mismatches = drain_checkpoint_mismatches(state, ledger, anchor_id, anchored)
        .unwrap_or_else(|error| {
            problems.push(error);
            Vec::new()
        });
    let anchor_hex = bytes_to_hex(&anchor_id.0);
    let mut legacy = Vec::new();
    if !unfenced.is_empty() {
        legacy.push(format!(
            "the epoch-{old_epoch} prepare fence for policy epoch(s) {unfenced:?}"
        ));
    }
    if anchor_missing {
        legacy.push(format!("the anchored drain checkpoint {anchor_hex}"));
    }
    if !mismatches.is_empty() {
        problems.push(format!(
            "{} differ from anchored checkpoint {anchor_hex}",
            mismatches.join(", ")
        ));
    }
    let legacy_text =
        (!legacy.is_empty()).then(|| {
            format!(
            "store ({} load, {} WAL record(s), {} fence and {} anchor record(s)) never applied {}",
            if loaded.snapshot_present { "snapshot" } else { "base+WAL" },
            loaded.wal_records,
            loaded.fence_records,
            loaded.anchor_records,
            legacy.join(" or ")
        )
        });
    match (legacy_text, problems.is_empty()) {
        (Some(legacy), false) => Err(format!(
            "{legacy}, and the replayed state does not equal the anchored drained state: {}",
            problems.join("; ")
        )),
        (None, false) => Err(format!("FastSwap store is not drained: {}", problems.join("; "))),
        (Some(legacy), true) => Ok(vec![format!(
            "{legacy}; its replayed state equals the anchored drained state (no reservations, no pending burns, every checkpoint root and total matches), so the migration subsumes them"
        )]),
        (None, true) => Ok(Vec::new()),
    }
}

pub(super) fn read_committee_file(path: &Path) -> Result<FastSwapCommitteeV1, String> {
    let value: serde_json::Value = read_bounded_json(path)
        .map_err(|error| format!("committee file {}: {error}", path.display()))?;
    let object = value
        .pointer("/operation/certificate/action/committee")
        .cloned()
        .unwrap_or(value);
    let committee: FastSwapCommitteeV1 = serde_json::from_value(object)
        .map_err(|error| format!("committee file is not a FastSwap committee: {error}"))?;
    let root = committee
        .computed_root()
        .map_err(codec_error)
        .map_err(|error| error.to_string())?;
    if committee.validate().is_err() || root != committee.domain.committee_root {
        return Err("committee file does not validate against its own root".to_owned());
    }
    Ok(committee)
}

pub(super) fn read_anchor_file(
    path: &Path,
) -> Result<(FastLaneCheckpointIdV1, FastLaneCheckpointCertificateV1), String> {
    let value: serde_json::Value = read_bounded_json(path)
        .map_err(|error| format!("anchor file {}: {error}", path.display()))?;
    let object = value
        .pointer("/operation/certificate")
        .cloned()
        .unwrap_or(value);
    let certificate: FastLaneCheckpointCertificateV1 = serde_json::from_value(object)
        .map_err(|error| format!("anchor file is not a checkpoint certificate: {error}"))?;
    let id = certificate
        .votes
        .first()
        .ok_or("anchor certificate has no votes")?
        .checkpoint
        .checkpoint_id()
        .map_err(|error| format!("anchor checkpoint id failed: {error:?}"))?;
    Ok((id, certificate))
}

fn resolve_validator_id(
    options: &FastSwapCommitteeMigrationOptions,
    next: &FastSwapCommitteeV1,
) -> Result<String, String> {
    if let Some(id) = &options.validator_id {
        return Ok(id.clone());
    }
    let matches = next
        .validators
        .iter()
        .filter(|validator| {
            load_validator_secret_key(&options.data_dir, &validator.validator_id).is_ok_and(|key| {
                ml_dsa_65_sign_with_context(
                    &key,
                    b"fastswap-key-self-check-v1",
                    FASTSWAP_VOTE_CONTEXT_V1,
                )
                .is_ok_and(|signature| {
                    postfiat_crypto_provider::ml_dsa_65_verify_with_context(
                        &validator.public_key,
                        b"fastswap-key-self-check-v1",
                        &signature,
                        FASTSWAP_VOTE_CONTEXT_V1,
                    )
                })
            })
        })
        .map(|validator| validator.validator_id.clone())
        .collect::<Vec<_>>();
    match matches.as_slice() {
        [only] => Ok(only.clone()),
        _ => Err(format!(
            "validator_keys.json matches {} member(s) of the new committee; pass --validator-id",
            matches.len()
        )),
    }
}

fn verify_open(
    data_dir: &Path,
    validator_id: &str,
    next: &FastSwapCommitteeV1,
) -> Result<String, String> {
    let service = FastSwapValidatorServiceV1::open(data_dir, validator_id)
        .map_err(|error| format!("post-migration service open failed: {error}"))?;
    let capabilities = service.capabilities();
    if capabilities.committee != next.domain || !capabilities.enabled {
        return Err(format!(
            "post-migration open reports epoch {} enabled {}",
            capabilities.committee.committee_epoch, capabilities.enabled
        ));
    }
    Ok(format!(
        "service open: committee epoch {}, root {}, enabled true",
        capabilities.committee.committee_epoch,
        bytes_to_hex(&capabilities.committee.committee_root.0)
    ))
}

fn side(
    domain: &postfiat_types::FastSwapCommitteeDomainV1,
    state: &FastLaneStateV1,
    file_sha3_384: std::collections::BTreeMap<String, Option<String>>,
) -> FastSwapCommitteeSideV1 {
    FastSwapCommitteeSideV1 {
        committee_epoch: domain.committee_epoch,
        committee_root: bytes_to_hex(&domain.committee_root.0),
        domain: domain.clone(),
        prepare_fences: state.prepare_fences.values().cloned().collect(),
        anchored_checkpoints: state
            .anchored_checkpoints
            .iter()
            .map(|id| bytes_to_hex(&id.0))
            .collect(),
        objects: state.objects.len(),
        file_sha3_384,
    }
}

fn file_hashes(
    directory: &Path,
) -> Result<std::collections::BTreeMap<String, Option<String>>, String> {
    STORE_FILES
        .iter()
        .map(|name| {
            fastswap_file_sha3_384(&directory.join(name))
                .map(|hash| ((*name).to_owned(), hash))
                .map_err(|error| format!("{name}: {error}"))
        })
        .collect()
}

fn predicted_hashes(
    base: &[u8],
    committee: &[u8],
) -> std::collections::BTreeMap<String, Option<String>> {
    use sha3::{Digest, Sha3_384};
    let hash = |bytes: &[u8]| Some(bytes_to_hex(&Sha3_384::digest(bytes)));
    STORE_FILES
        .iter()
        .map(|name| {
            let value = match *name {
                FASTSWAP_BASE_STATE => hash(base),
                FASTSWAP_COMMITTEE => hash(committee),
                _ => None,
            };
            ((*name).to_owned(), value)
        })
        .collect()
}
