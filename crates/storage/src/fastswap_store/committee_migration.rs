//! Store-level helpers for the offline FastSwap committee-epoch migration
//! (`postfiat-node fastswap-committee-migrate`). The node crate owns the
//! drained-state checks; this module owns the lock, the read-only replay, the
//! verified backup and its restore. Runbook:
//! docs/runbooks/fastpay-committee-recovery.md.

use super::legacy_migration::{probe_store_lock, write_atomically, write_verified_backup_manifest};
use super::{
    apply_record, lock_store_directory, read_records, read_snapshot, validate_record_sequences,
    FastSwapStoreError, FastSwapWalRecordV1, ProcessLock, FASTSWAP_LOCK_FILE,
    FASTSWAP_SNAPSHOT_FILE, FASTSWAP_WAL_FILE,
};
use crate::integrity::IntegrityKey;
use postfiat_types::FastLaneStateV1;
use serde::Serialize;
use std::fs::{self, File};
use std::io;
use std::path::Path;

/// Exclusive FastSwap store lock held for the whole offline migration.
#[derive(Debug)]
pub struct FastSwapStoreLock {
    _lock: Option<ProcessLock>,
}

/// Take the store lock; refuses when a running service (or another
/// migration) holds it. A dry run probes through a read-only descriptor and
/// never creates the lock file.
pub fn lock_fastswap_store_offline(
    directory: &Path,
    dry_run: bool,
) -> Result<FastSwapStoreLock, FastSwapStoreError> {
    if dry_run {
        return Ok(FastSwapStoreLock {
            _lock: probe_store_lock(directory)?,
        });
    }
    Ok(FastSwapStoreLock {
        _lock: Some(ProcessLock {
            _file: lock_store_directory(directory)?,
        }),
    })
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct FastSwapBackupFileV1 {
    pub path: String,
    pub bytes: u64,
    pub sha3_384: String,
}

/// A store replayed without writing: snapshot when present, else base + WAL.
#[derive(Debug, Clone)]
pub struct FastSwapStoreReadOnlyLoadV1 {
    pub state: FastLaneStateV1,
    pub snapshot_present: bool,
    pub snapshot_next_sequence: Option<u64>,
    pub wal_records: usize,
    pub replayed_wal_records: usize,
    pub fence_records: usize,
    pub anchor_records: usize,
}

/// Replay exactly as `FastSwapStore::open` + `replay` do, but with the existing
/// integrity key only and no lock-file, key or directory writes.
pub fn load_fastswap_store_read_only(
    directory: &Path,
    base: &FastLaneStateV1,
) -> Result<FastSwapStoreReadOnlyLoadV1, FastSwapStoreError> {
    let snapshot_path = directory.join(FASTSWAP_SNAPSHOT_FILE);
    let wal_path = directory.join(FASTSWAP_WAL_FILE);
    let key = match IntegrityKey::load_existing(directory) {
        Ok(key) => key,
        Err(error) if error.kind() == io::ErrorKind::NotFound => {
            if snapshot_path.exists() || wal_path.exists() {
                return Err(FastSwapStoreError::Conflict(
                    "store has a WAL or snapshot but no integrity key; run fastswap-store-migrate first",
                ));
            }
            return Ok(FastSwapStoreReadOnlyLoadV1 {
                state: base.clone(),
                snapshot_present: false,
                snapshot_next_sequence: None,
                wal_records: 0,
                replayed_wal_records: 0,
                fence_records: 0,
                anchor_records: 0,
            });
        }
        Err(error) => return Err(error.into()),
    };
    let snapshot = read_snapshot(&snapshot_path, &key, false)?;
    let records = read_records(&wal_path, &key, false)?;
    let snapshot_next = snapshot.as_ref().map(|value| value.next_sequence);
    let mut expected = snapshot_next.unwrap_or(0);
    validate_record_sequences(&records, expected)?;
    let mut state = match snapshot {
        Some(snapshot) => snapshot.state.into_state()?,
        None => base.clone(),
    };
    let (mut replayed, mut fences, mut anchors) = (0, 0, 0);
    for record in &records {
        if record.sequence() < expected {
            continue;
        }
        if record.sequence() != expected {
            return Err(FastSwapStoreError::SequenceMismatch {
                expected,
                actual: record.sequence(),
            });
        }
        apply_record(&mut state, record)?;
        expected = expected.saturating_add(1);
        replayed += 1;
        match record {
            FastSwapWalRecordV1::Fence { .. } => fences += 1,
            FastSwapWalRecordV1::AnchorCheckpoint { .. } => anchors += 1,
            _ => {}
        }
    }
    Ok(FastSwapStoreReadOnlyLoadV1 {
        state,
        snapshot_present: snapshot_next.is_some(),
        snapshot_next_sequence: snapshot_next,
        wal_records: records.len(),
        replayed_wal_records: replayed,
        fence_records: fences,
        anchor_records: anchors,
    })
}

/// Full verified backup of the store (every regular file except the lock),
/// fsynced, with a SHA3-384 manifest.
pub fn backup_fastswap_store(
    store: &Path,
    backup: &Path,
) -> Result<Vec<FastSwapBackupFileV1>, FastSwapStoreError> {
    write_verified_backup_manifest(store, backup)
}

/// Atomic owner-only (0600) write: temp file, fsync, rename, fsync directory.
pub fn write_fastswap_file_owner_only(path: &Path, bytes: &[u8]) -> Result<(), FastSwapStoreError> {
    write_atomically(path, bytes)?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(path, fs::Permissions::from_mode(0o600))?;
    }
    Ok(())
}

/// Remove the WAL and snapshot after they are held by a verified backup.
pub fn remove_fastswap_wal_and_snapshot(store: &Path) -> Result<Vec<String>, FastSwapStoreError> {
    let mut removed = Vec::new();
    for name in [FASTSWAP_WAL_FILE, FASTSWAP_SNAPSHOT_FILE] {
        match fs::remove_file(store.join(name)) {
            Ok(()) => removed.push(name.to_owned()),
            Err(error) if error.kind() == io::ErrorKind::NotFound => {}
            Err(error) => return Err(error.into()),
        }
    }
    File::open(store)?.sync_all()?;
    Ok(removed)
}

/// Put the store back exactly as backed up: rewrite every backed-up file and
/// remove any file the migration or its verification open created.
pub fn restore_fastswap_store_backup(
    store: &Path,
    backup: &Path,
) -> Result<(), FastSwapStoreError> {
    restore_tree(store, backup, true)?;
    File::open(store)?.sync_all()?;
    Ok(())
}

fn restore_tree(store: &Path, backup: &Path, root: bool) -> Result<(), FastSwapStoreError> {
    for entry in fs::read_dir(backup)? {
        let entry = entry?;
        let target = store.join(entry.file_name());
        if entry.file_type()?.is_dir() {
            fs::create_dir_all(&target)?;
            restore_tree(&target, &entry.path(), false)?;
        } else {
            let source = entry.path();
            write_atomically(&target, &fs::read(&source)?)?;
            fs::set_permissions(&target, fs::metadata(&source)?.permissions())?;
        }
    }
    for entry in fs::read_dir(store)? {
        let entry = entry?;
        let name = entry.file_name();
        if (root && name == FASTSWAP_LOCK_FILE) || backup.join(&name).exists() {
            continue;
        }
        if entry.file_type()?.is_dir() {
            fs::remove_dir_all(entry.path())?;
        } else {
            fs::remove_file(entry.path())?;
        }
    }
    Ok(())
}

/// Hex SHA3-384 of a file, or `None` when it is absent.
pub fn fastswap_file_sha3_384(path: &Path) -> Result<Option<String>, FastSwapStoreError> {
    use sha3::{Digest, Sha3_384};
    match fs::read(path) {
        Ok(bytes) => Ok(Some(crate::integrity::to_hex(&Sha3_384::digest(bytes)))),
        Err(error) if error.kind() == io::ErrorKind::NotFound => Ok(None),
        Err(error) => Err(error.into()),
    }
}
