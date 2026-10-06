//! Offline conversion of a FastSwap store whose WAL records (or snapshot) still
//! carry the legacy unkeyed checksum. Normal opens reject such stores; this
//! path re-tags them with the directory's keyed MAC. Operators run it only with
//! both validator units stopped (see docs/runbooks/fastpay-committee-recovery.md).

use super::{
    acquire_process_lock, lock_error, lock_store_directory, read_bounded_file, read_records,
    snapshot_payload, validate_record_sequences, FastSwapSnapshotV1, FastSwapStore,
    FastSwapStoreError, FastSwapWalRecordV1, ProcessLock, FASTSWAP_LOCK_FILE,
    FASTSWAP_SNAPSHOT_FILE, FASTSWAP_SNAPSHOT_MAC_DOMAIN, FASTSWAP_SNAPSHOT_MAX_BYTES,
    FASTSWAP_SNAPSHOT_SCHEMA, FASTSWAP_WAL_CHECKSUM_BYTES, FASTSWAP_WAL_FILE,
    FASTSWAP_WAL_MAC_DOMAIN, FASTSWAP_WAL_MAX_BYTES, FASTSWAP_WAL_MAX_RECORD_BYTES,
};
use crate::integrity::{from_hex, legacy_checksum, macs_equal, IntegrityKey, INTEGRITY_KEY_FILE};
use serde::Serialize;
use sha3::{Digest, Sha3_384};
use std::fs::{self, File, OpenOptions};
use std::io::{self, Write};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Default)]
pub struct FastSwapStoreMigrationOptions {
    pub dry_run: bool,
    /// Defaults to a sibling `<store>.pre-keyed-migration-<unix-seconds>`.
    pub backup_directory: Option<PathBuf>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct FastSwapStoreMigrationReport {
    pub store_directory: String,
    pub dry_run: bool,
    /// `converted`, `would-convert` or `nothing-to-convert`.
    pub outcome: String,
    pub wal_bytes: u64,
    pub wal_records: usize,
    pub legacy_wal_records: usize,
    pub converted_wal_records: usize,
    pub legacy_snapshot: bool,
    pub converted_snapshot: bool,
    /// Non-secret fingerprint; the key itself is never reported.
    pub integrity_key_fingerprint: Option<String>,
    pub integrity_key_created: bool,
    pub backup_directory: Option<String>,
    pub backup_files_verified: usize,
    pub verification: String,
}

struct WalScan {
    bytes: Vec<u8>,
    records: usize,
    legacy: usize,
}

struct SnapshotScan {
    bytes: Vec<u8>,
    snapshot: FastSwapSnapshotV1,
    legacy: bool,
}

/// Convert a legacy FastSwap store in place. Fails closed: any lock holder,
/// torn or tampered record, or unwritable/unverifiable backup refuses before
/// the store changes; a failed post-write verification restores the original.
pub fn migrate_legacy_fastswap_store(
    directory: &Path,
    options: &FastSwapStoreMigrationOptions,
) -> Result<FastSwapStoreMigrationReport, FastSwapStoreError> {
    if !directory.is_dir() {
        return Err(FastSwapStoreError::Io(io::Error::new(
            io::ErrorKind::NotFound,
            format!("FastSwap store `{}` does not exist", directory.display()),
        )));
    }
    let (lock, probe) = if options.dry_run {
        (None, probe_store_lock(directory)?)
    } else {
        (Some(lock_store_directory(directory)?), None)
    };
    let existing_key = match IntegrityKey::load_existing(directory) {
        Ok(key) => Some(key),
        Err(error) if error.kind() == io::ErrorKind::NotFound => None,
        Err(error) => return Err(error.into()),
    };
    let snapshot_path = directory.join(FASTSWAP_SNAPSHOT_FILE);
    let wal_path = directory.join(FASTSWAP_WAL_FILE);
    let snapshot = scan_snapshot(&snapshot_path, existing_key.as_ref())?;
    let snapshot_next = snapshot
        .as_ref()
        .map_or(0, |scan| scan.snapshot.next_sequence);
    let wal = scan_wal(&wal_path, existing_key.as_ref(), snapshot_next)?;
    let legacy_snapshot = snapshot.as_ref().is_some_and(|scan| scan.legacy);
    let needs_conversion = wal.legacy > 0 || legacy_snapshot;
    let mut report = FastSwapStoreMigrationReport {
        store_directory: directory.display().to_string(),
        dry_run: options.dry_run,
        outcome: "nothing-to-convert".to_owned(),
        wal_bytes: wal.bytes.len() as u64,
        wal_records: wal.records,
        legacy_wal_records: wal.legacy,
        converted_wal_records: 0,
        legacy_snapshot,
        converted_snapshot: false,
        integrity_key_fingerprint: existing_key.as_ref().map(IntegrityKey::fingerprint),
        integrity_key_created: false,
        backup_directory: None,
        backup_files_verified: 0,
        verification: "not run (dry run)".to_owned(),
    };
    if options.dry_run {
        drop(probe);
        if needs_conversion {
            report.outcome = "would-convert".to_owned();
        }
        return Ok(report);
    }
    let lock = lock.ok_or(FastSwapStoreError::Conflict("store lock missing"))?;
    if !needs_conversion {
        drop(lock);
        report.verification = verify_normal_open(directory, wal.records)?;
        return Ok(report);
    }

    let backup = match &options.backup_directory {
        Some(path) => path.clone(),
        None => default_backup_directory(directory)?,
    };
    report.backup_files_verified = write_verified_backup(directory, &backup)?;
    report.backup_directory = Some(backup.display().to_string());

    // The explicit legacy open (as `open_for_legacy_migration`, but under the
    // lock already held) re-tags every record atomically and creates a missing
    // key with mode 0600.
    let key_created = existing_key.is_none();
    let converted = FastSwapStore::open_locked(directory, lock, None, true).map(drop);
    let verified = converted.and_then(|()| verify_normal_open(directory, wal.records));
    #[cfg(test)]
    let verified = verified.and_then(|verification| {
        if tests::FAIL_VERIFICATION_AFTER_WRITE.with(|flag| flag.replace(false)) {
            Err(FastSwapStoreError::StateInvariant(
                "injected post-write verification failure",
            ))
        } else {
            Ok(verification)
        }
    });
    report.integrity_key_created = key_created && directory.join(INTEGRITY_KEY_FILE).exists();
    report.integrity_key_fingerprint = IntegrityKey::load_existing(directory)
        .ok()
        .map(|key| key.fingerprint());
    match verified {
        Ok(verification) => {
            report.outcome = "converted".to_owned();
            report.converted_wal_records = wal.legacy;
            report.converted_snapshot = legacy_snapshot;
            report.verification = verification;
            Ok(report)
        }
        Err(error) => {
            restore_original(
                directory,
                &wal_path,
                &wal,
                &snapshot_path,
                snapshot.as_ref(),
            )?;
            if report.integrity_key_created {
                fs::remove_file(directory.join(INTEGRITY_KEY_FILE))?;
            }
            Err(error)
        }
    }
}

/// Dry run: take the flock through a read-only descriptor when the lock file
/// exists, so a held lock refuses without creating or writing anything.
fn probe_store_lock(directory: &Path) -> Result<Option<ProcessLock>, FastSwapStoreError> {
    let file = match File::open(directory.join(FASTSWAP_LOCK_FILE)) {
        Ok(file) => file,
        Err(error) if error.kind() == io::ErrorKind::NotFound => return Ok(None),
        Err(error) => return Err(error.into()),
    };
    acquire_process_lock(&file).map_err(lock_error)?;
    Ok(Some(ProcessLock { _file: file }))
}

fn scan_snapshot(
    path: &Path,
    key: Option<&IntegrityKey>,
) -> Result<Option<SnapshotScan>, FastSwapStoreError> {
    let bytes = match read_bounded_file(path, FASTSWAP_SNAPSHOT_MAX_BYTES) {
        Ok(bytes) => bytes,
        Err(FastSwapStoreError::Io(error)) if error.kind() == io::ErrorKind::NotFound => {
            return Ok(None)
        }
        Err(error) => return Err(error),
    };
    let snapshot: FastSwapSnapshotV1 = serde_json::from_slice(&bytes)
        .map_err(|_| FastSwapStoreError::CorruptSnapshot("snapshot decode failure"))?;
    if snapshot.schema != FASTSWAP_SNAPSHOT_SCHEMA {
        return Err(FastSwapStoreError::CorruptSnapshot(
            "snapshot schema mismatch",
        ));
    }
    let payload = snapshot_payload(snapshot.next_sequence, &snapshot.state)?;
    let legacy = match snapshot.mac.as_deref() {
        Some(mac_hex) => {
            let tag = from_hex(mac_hex).ok_or(FastSwapStoreError::CorruptSnapshot(
                "snapshot MAC is not hex",
            ))?;
            let key = key.ok_or(FastSwapStoreError::CorruptSnapshot(
                "keyed snapshot present but the integrity key is missing",
            ))?;
            if !macs_equal(&key.mac(FASTSWAP_SNAPSHOT_MAC_DOMAIN, &payload), &tag) {
                return Err(FastSwapStoreError::CorruptSnapshot(
                    "snapshot MAC mismatch (tampered or foreign-key snapshot)",
                ));
            }
            false
        }
        None => {
            if !macs_equal(
                &legacy_checksum(FASTSWAP_SNAPSHOT_MAC_DOMAIN, &payload),
                &snapshot.checksum,
            ) {
                return Err(FastSwapStoreError::CorruptSnapshot(
                    "snapshot checksum mismatch",
                ));
            }
            true
        }
    };
    Ok(Some(SnapshotScan {
        bytes,
        snapshot,
        legacy,
    }))
}

/// Strict WAL scan: unlike a normal open, a torn final record is refused so
/// the operator repairs or restores it explicitly before any rewrite.
fn scan_wal(
    path: &Path,
    key: Option<&IntegrityKey>,
    snapshot_next: u64,
) -> Result<WalScan, FastSwapStoreError> {
    let bytes = match read_bounded_file(path, FASTSWAP_WAL_MAX_BYTES) {
        Ok(bytes) => bytes,
        Err(FastSwapStoreError::Io(error)) if error.kind() == io::ErrorKind::NotFound => Vec::new(),
        Err(error) => return Err(error),
    };
    let mut records: Vec<FastSwapWalRecordV1> = Vec::new();
    let mut legacy = 0_usize;
    let mut offset = 0_usize;
    while offset < bytes.len() {
        let start = offset as u64;
        let corrupt = |reason| FastSwapStoreError::CorruptWal {
            offset: start,
            reason,
        };
        let (payload, tag, end) = frame(&bytes, offset).ok_or(corrupt(
            "truncated or oversized record; migration refuses a torn WAL",
        ))?;
        let keyed =
            key.is_some_and(|key| macs_equal(&key.mac(FASTSWAP_WAL_MAC_DOMAIN, payload), tag));
        if !keyed {
            if !macs_equal(&legacy_checksum(FASTSWAP_WAL_MAC_DOMAIN, payload), tag) {
                return Err(corrupt(
                    "integrity tag matches neither the keyed MAC nor the legacy checksum",
                ));
            }
            legacy += 1;
        }
        records
            .push(serde_json::from_slice(payload).map_err(|_| corrupt("record decode failure"))?);
        offset = end;
    }
    validate_record_sequences(&records, snapshot_next)?;
    Ok(WalScan {
        records: records.len(),
        bytes,
        legacy,
    })
}

/// Returns `(payload, tag, end)` for the record framed at `offset`.
fn frame(bytes: &[u8], offset: usize) -> Option<(&[u8], &[u8], usize)> {
    let length =
        u32::from_be_bytes(bytes.get(offset..offset.checked_add(4)?)?.try_into().ok()?) as usize;
    if length > FASTSWAP_WAL_MAX_RECORD_BYTES {
        return None;
    }
    let payload_start = offset + 4;
    let tag_start = payload_start.checked_add(length)?;
    let end = tag_start.checked_add(FASTSWAP_WAL_CHECKSUM_BYTES)?;
    Some((
        bytes.get(payload_start..tag_start)?,
        bytes.get(tag_start..end)?,
        end,
    ))
}

fn restore_original(
    directory: &Path,
    wal_path: &Path,
    wal: &WalScan,
    snapshot_path: &Path,
    snapshot: Option<&SnapshotScan>,
) -> Result<(), FastSwapStoreError> {
    let _lock = lock_store_directory(directory)?;
    if wal.legacy > 0 {
        write_atomically(wal_path, &wal.bytes)?;
    }
    if let Some(scan) = snapshot.filter(|scan| scan.legacy) {
        write_atomically(snapshot_path, &scan.bytes)?;
    }
    Ok(())
}

/// Temp file in the same directory, fsync, rename, fsync the directory.
pub(super) fn write_atomically(path: &Path, bytes: &[u8]) -> Result<(), FastSwapStoreError> {
    let parent = path
        .parent()
        .ok_or(FastSwapStoreError::Conflict("store path has no parent"))?;
    let name = path
        .file_name()
        .and_then(|name| name.to_str())
        .ok_or(FastSwapStoreError::Conflict("store filename invalid"))?;
    let temporary = parent.join(format!(".{name}.migrate-tmp-{}", std::process::id()));
    let mut file = OpenOptions::new()
        .create(true)
        .truncate(true)
        .write(true)
        .open(&temporary)?;
    if let Ok(metadata) = fs::metadata(path) {
        file.set_permissions(metadata.permissions())?;
    }
    file.write_all(bytes)?;
    file.sync_all()?;
    drop(file);
    fs::rename(&temporary, path)?;
    File::open(parent)?.sync_all()?;
    Ok(())
}

fn verify_normal_open(
    directory: &Path,
    expected_records: usize,
) -> Result<String, FastSwapStoreError> {
    let store = FastSwapStore::open(directory)?;
    let records = read_records(&store.wal_path, &store.integrity_key, false)?;
    if records.len() != expected_records {
        return Err(FastSwapStoreError::StateInvariant(
            "record count changed during FastSwap store migration",
        ));
    }
    Ok(format!(
        "normal open verified {} record(s) with the keyed MAC",
        records.len()
    ))
}

fn default_backup_directory(directory: &Path) -> Result<PathBuf, FastSwapStoreError> {
    let name = directory
        .file_name()
        .and_then(|name| name.to_str())
        .ok_or(FastSwapStoreError::Conflict("store directory name invalid"))?;
    let seconds = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_or(0, |elapsed| elapsed.as_secs());
    Ok(directory.with_file_name(format!("{name}.pre-keyed-migration-{seconds}")))
}

/// Copy every regular file except the lock into `backup`, fsync, and compare
/// SHA3-384 digests. Refuses a non-empty target or a target inside the store.
fn write_verified_backup(store: &Path, backup: &Path) -> Result<usize, FastSwapStoreError> {
    if backup.exists() && (!backup.is_dir() || fs::read_dir(backup)?.next().is_some()) {
        return Err(FastSwapStoreError::Conflict(
            "backup directory exists and is not an empty directory",
        ));
    }
    fs::create_dir_all(backup)?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(backup, fs::Permissions::from_mode(0o700))?;
    }
    if fs::canonicalize(backup)?.starts_with(fs::canonicalize(store)?) {
        fs::remove_dir(backup)?;
        return Err(FastSwapStoreError::Conflict(
            "backup directory must be outside the store",
        ));
    }
    let mut copied = Vec::new();
    copy_tree(store, backup, true, &mut copied)?;
    File::open(backup)?.sync_all()?;
    for (source, target) in &copied {
        if file_digest(source)? != file_digest(target)? {
            return Err(FastSwapStoreError::Conflict(
                "backup verification failed: digest mismatch",
            ));
        }
    }
    Ok(copied.len())
}

fn copy_tree(
    source: &Path,
    target: &Path,
    root: bool,
    copied: &mut Vec<(PathBuf, PathBuf)>,
) -> Result<(), FastSwapStoreError> {
    for entry in fs::read_dir(source)? {
        let entry = entry?;
        let name = entry.file_name();
        if root && name == FASTSWAP_LOCK_FILE {
            continue;
        }
        let (from, to) = (entry.path(), target.join(&name));
        let kind = entry.file_type()?;
        if kind.is_dir() {
            fs::create_dir(&to)?;
            copy_tree(&from, &to, false, copied)?;
            File::open(&to)?.sync_all()?;
        } else if kind.is_file() {
            fs::copy(&from, &to)?;
            File::open(&to)?.sync_all()?;
            copied.push((from, to));
        } else {
            return Err(FastSwapStoreError::Conflict(
                "store contains a non-regular file; refusing to back it up",
            ));
        }
    }
    Ok(())
}

fn file_digest(path: &Path) -> Result<[u8; 48], FastSwapStoreError> {
    Ok(Sha3_384::digest(fs::read(path)?).into())
}

#[cfg(test)]
mod tests;
