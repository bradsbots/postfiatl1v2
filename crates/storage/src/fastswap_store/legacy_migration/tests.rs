use super::super::tests::{state, test_dir};
use super::*;
use crate::integrity::to_hex;
use postfiat_types::{FastLaneStateV1, FastSwapEffectsDigestV1, FastSwapIdV1, FastSwapIntentIdV1};
use std::collections::BTreeMap;

/// A store written by the current code, then re-tagged with the legacy
/// unkeyed checksum, as on the live validators before keyed integrity.
fn legacy_fixture(label: &str) -> (PathBuf, FastLaneStateV1, FastLaneStateV1) {
    let directory = test_dir(label);
    let base = state();
    let mut live = base.clone();
    let object = *live.objects.keys().next().expect("object");
    {
        let mut store = FastSwapStore::open(&directory).expect("open");
        store
            .reserve_all(
                &mut live,
                FastSwapIdV1([8; 48]),
                FastSwapIntentIdV1([9; 48]),
                FastSwapEffectsDigestV1([10; 48]),
                100,
                &[object],
            )
            .expect("reserve");
    }
    let wal = directory.join(FASTSWAP_WAL_FILE);
    let mut bytes = fs::read(&wal).expect("read wal");
    let mut offset = 0;
    while let Some((payload, _, end)) = frame(&bytes, offset) {
        let legacy = legacy_checksum(FASTSWAP_WAL_MAC_DOMAIN, payload);
        bytes[end - FASTSWAP_WAL_CHECKSUM_BYTES..end].copy_from_slice(&legacy);
        offset = end;
    }
    fs::write(&wal, &bytes).expect("write legacy wal");
    (directory, base, live)
}

fn backup_for(directory: &Path, suffix: &str) -> PathBuf {
    let name = directory.file_name().and_then(|name| name.to_str());
    directory.with_file_name(format!("{}-{suffix}", name.expect("name")))
}

fn convert(backup: &Path) -> FastSwapStoreMigrationOptions {
    FastSwapStoreMigrationOptions {
        dry_run: false,
        backup_directory: Some(backup.to_path_buf()),
    }
}

fn contents(directory: &Path) -> BTreeMap<String, Vec<u8>> {
    fs::read_dir(directory)
        .expect("read dir")
        .map(|entry| entry.expect("entry").path())
        .filter(|path| path.is_file())
        .map(|path| {
            let name = path
                .file_name()
                .expect("name")
                .to_string_lossy()
                .into_owned();
            (name, fs::read(&path).expect("read"))
        })
        .collect()
}

fn assert_still_legacy(directory: &Path) {
    assert!(matches!(
        FastSwapStore::open(directory),
        Err(FastSwapStoreError::CorruptWal { .. })
    ));
}

fn cleanup(paths: &[&Path]) {
    for path in paths {
        if path.is_dir() {
            fs::remove_dir_all(path).ok();
        } else {
            fs::remove_file(path).ok();
        }
    }
}

#[test]
fn migration_converts_legacy_store_so_normal_open_verifies_every_record() {
    let (directory, base, live) = legacy_fixture("migrate-convert");
    let wal = directory.join(FASTSWAP_WAL_FILE);
    let original = fs::read(&wal).expect("read");
    assert_still_legacy(&directory);

    let backup = backup_for(&directory, "backup");
    let report = migrate_legacy_fastswap_store(&directory, &convert(&backup)).expect("migrate");
    assert_eq!(report.outcome, "converted");
    assert_eq!(
        (
            report.wal_records,
            report.legacy_wal_records,
            report.converted_wal_records
        ),
        (1, 1, 1)
    );
    assert_eq!(report.wal_bytes, original.len() as u64);
    assert!(!report.integrity_key_created);
    assert_eq!(
        report.verification,
        "normal open verified 1 record(s) with the keyed MAC"
    );
    let key = IntegrityKey::load_existing(&directory).expect("key");
    assert_eq!(report.integrity_key_fingerprint, Some(key.fingerprint()));
    let key_bytes = fs::read(directory.join(INTEGRITY_KEY_FILE)).expect("key bytes");
    let rendered = serde_json::to_string(&report).expect("json");
    assert!(
        !rendered.contains(&to_hex(&key_bytes)),
        "report must not leak the key"
    );

    // The backup is the exact pre-migration store, key included.
    assert_eq!(report.backup_directory, Some(backup.display().to_string()));
    assert_eq!(report.backup_files_verified, 2);
    assert_eq!(
        fs::read(backup.join(FASTSWAP_WAL_FILE)).expect("backup wal"),
        original
    );
    assert_eq!(
        fs::read(backup.join(INTEGRITY_KEY_FILE)).expect("backup key"),
        key_bytes
    );
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mode = fs::metadata(backup.join(INTEGRITY_KEY_FILE))
            .expect("meta")
            .permissions();
        assert_eq!(mode.mode() & 0o777, 0o600);
    }

    let converted = fs::read(&wal).expect("read converted");
    assert_eq!(converted.len(), original.len());
    assert_ne!(converted, original);
    let store = FastSwapStore::open(&directory).expect("normal open after migration");
    assert_eq!(store.replay(&base).expect("replay"), live);
    drop(store);

    // Idempotent: a second run finds nothing, writes no backup, changes nothing.
    let second_backup = backup_for(&directory, "backup-2");
    let again =
        migrate_legacy_fastswap_store(&directory, &convert(&second_backup)).expect("second run");
    assert_eq!(again.outcome, "nothing-to-convert");
    assert_eq!(
        (again.legacy_wal_records, again.converted_wal_records),
        (0, 0)
    );
    assert_eq!(again.backup_directory, None);
    assert!(!second_backup.exists());
    assert_eq!(fs::read(&wal).expect("read"), converted);
    assert_eq!(again.verification, report.verification);
    cleanup(&[&directory, &backup]);
}

#[test]
fn migration_dry_run_reports_without_writing() {
    let (directory, _, _) = legacy_fixture("migrate-dry-run");
    let before = contents(&directory);
    let backup = backup_for(&directory, "backup");
    let options = FastSwapStoreMigrationOptions {
        dry_run: true,
        backup_directory: Some(backup.clone()),
    };
    let report = migrate_legacy_fastswap_store(&directory, &options).expect("dry run");
    assert_eq!(report.outcome, "would-convert");
    assert_eq!(
        (report.legacy_wal_records, report.converted_wal_records),
        (1, 0)
    );
    assert_eq!(report.verification, "not run (dry run)");
    assert_eq!(report.backup_directory, None);
    assert!(!backup.exists());
    assert_eq!(contents(&directory), before);
    assert_still_legacy(&directory);
    cleanup(&[&directory]);
}

#[test]
fn migration_refuses_while_the_store_lock_is_held() {
    let (directory, _, _) = legacy_fixture("migrate-locked");
    let before = contents(&directory);
    let holder = OpenOptions::new()
        .read(true)
        .write(true)
        .open(directory.join(FASTSWAP_LOCK_FILE))
        .expect("lock file");
    acquire_process_lock(&holder).expect("hold lock");
    let backup = backup_for(&directory, "backup");
    for dry_run in [false, true] {
        let options = FastSwapStoreMigrationOptions {
            dry_run,
            backup_directory: Some(backup.clone()),
        };
        assert!(matches!(
            migrate_legacy_fastswap_store(&directory, &options),
            Err(FastSwapStoreError::Conflict(_))
        ));
    }
    assert!(!backup.exists());
    assert_eq!(contents(&directory), before);
    drop(holder);
    cleanup(&[&directory]);
}

#[test]
fn migration_refuses_before_writing_when_the_backup_fails() {
    let (directory, _, _) = legacy_fixture("migrate-backup-fails");
    let before = contents(&directory);
    let occupied = backup_for(&directory, "occupied");
    fs::write(&occupied, b"not a directory").expect("occupy");
    assert!(matches!(
        migrate_legacy_fastswap_store(&directory, &convert(&occupied)),
        Err(FastSwapStoreError::Conflict(_))
    ));
    let inside = directory.join("backup");
    assert!(matches!(
        migrate_legacy_fastswap_store(&directory, &convert(&inside)),
        Err(FastSwapStoreError::Conflict(_))
    ));
    assert!(!inside.exists());
    assert_eq!(contents(&directory), before);
    assert_still_legacy(&directory);
    cleanup(&[&directory, &occupied]);
}

#[test]
fn migration_refuses_truncated_or_corrupt_records_and_leaves_the_original() {
    for (label, damage) in [("migrate-truncated", 0_usize), ("migrate-corrupt", 1_usize)] {
        let (directory, _, _) = legacy_fixture(label);
        let wal = directory.join(FASTSWAP_WAL_FILE);
        let mut bytes = fs::read(&wal).expect("read");
        if damage == 0 {
            bytes.extend_from_slice(&[0, 0, 0, 9, 1, 2]);
        } else {
            bytes[10] ^= 0x01;
        }
        fs::write(&wal, &bytes).expect("damage");
        let before = contents(&directory);
        let backup = backup_for(&directory, "backup");
        assert!(matches!(
            migrate_legacy_fastswap_store(&directory, &convert(&backup)),
            Err(FastSwapStoreError::CorruptWal { .. })
        ));
        assert!(!backup.exists());
        assert_eq!(contents(&directory), before);
        cleanup(&[&directory]);
    }
}

#[test]
fn migration_creates_a_missing_key_with_owner_only_mode() {
    let (directory, base, live) = legacy_fixture("migrate-new-key");
    fs::remove_file(directory.join(INTEGRITY_KEY_FILE)).expect("remove key");
    let backup = backup_for(&directory, "backup");
    let report = migrate_legacy_fastswap_store(&directory, &convert(&backup)).expect("migrate");
    assert!(report.integrity_key_created);
    assert!(!backup.join(INTEGRITY_KEY_FILE).exists());
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mode = fs::metadata(directory.join(INTEGRITY_KEY_FILE))
            .expect("meta")
            .permissions();
        assert_eq!(mode.mode() & 0o777, 0o600);
    }
    let store = FastSwapStore::open(&directory).expect("normal open");
    assert_eq!(store.replay(&base).expect("replay"), live);
    drop(store);
    cleanup(&[&directory, &backup]);
}
