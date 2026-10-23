//! The account history index follows block commits: a block committed after
//! `account-tx-index-build` is served from the index without a rebuild, a
//! crash between the durable commit and the index append leaves a state the
//! build repairs, repeated governance receipt ids keep the index following,
//! and the append changes no consensus output.

use super::*;

const RECIPIENT_A: &str = "pf00000000000000000000000000000000000000a1";
const RECIPIENT_B: &str = "pf00000000000000000000000000000000000000b2";
const RECIPIENT_C: &str = "pf00000000000000000000000000000000000000c3";
const RECIPIENT_D: &str = "pf00000000000000000000000000000000000000d4";

#[derive(Clone, Copy, Debug)]
enum Backend {
    Legacy,
    Transactional,
}

fn chain(label: &str, backend: Backend) -> PathBuf {
    let data_dir = unique_test_dir(label);
    match backend {
        Backend::Legacy => {
            init(InitOptions {
                data_dir: data_dir.clone(),
                chain_id: "postfiat-local".to_string(),
                node_id: "validator-0".to_string(),
                validator_count: 1,
            })
            .expect("init");
        }
        Backend::Transactional => {
            init_consensus_v2(InitConsensusV2Options {
                data_dir: data_dir.clone(),
                chain_id: "account-tx-commit-index".to_string(),
                node_id: "validator-0".to_string(),
                validator_count: 1,
                activation_height: 1000,
                storage_activation_height: Some(1),
            })
            .expect("init transactional");
        }
    }
    data_dir
}

fn transfer_batch(data_dir: &Path, to: &str) -> PathBuf {
    let batch_file = data_dir.join(format!("transfer-{to}.batch.json"));
    create_transfer_batch(BatchTransferOptions {
        data_dir: data_dir.to_path_buf(),
        key_file: None,
        to: to.to_string(),
        amount: ACCOUNT_RESERVE,
        batch_file: batch_file.clone(),
    })
    .expect("build transfer batch");
    batch_file
}

fn apply(data_dir: &Path, batch_file: &Path) {
    let receipts = apply_batch(ApplyBatchOptions {
        data_dir: data_dir.to_path_buf(),
        batch_file: batch_file.to_path_buf(),
        certificate_file: None,
    })
    .expect("commit batch");
    assert!(receipts.iter().all(|receipt| receipt.accepted), "{receipts:?}");
}

fn commit_transfer(data_dir: &Path, to: &str) {
    let batch_file = transfer_batch(data_dir, to);
    apply(data_dir, &batch_file);
}

fn history(data_dir: &Path, address: &str) -> AccountTxReport {
    account_tx(AccountTxQueryOptions {
        data_dir: data_dir.to_path_buf(),
        address: address.to_string(),
        from_height: None,
        to_height: None,
        limit: Some(100),
    })
    .expect("account tx")
}

/// The rows the bounded archive scan returns, whatever the index state.
fn scanned(data_dir: &Path, address: &str) -> Vec<AccountTxRow> {
    let store = NodeStore::new(data_dir);
    let genesis = store.read_genesis().expect("genesis");
    let block_log = store.read_blocks().expect("blocks");
    let options = AccountTxQueryOptions {
        data_dir: data_dir.to_path_buf(),
        address: address.to_string(),
        from_height: None,
        to_height: None,
        limit: Some(100),
    };
    account_tx_scan(options, 100, &store, &genesis, &block_log)
        .expect("archive scan")
        .rows
}

fn build(data_dir: &Path) -> AccountTxIndexBuildReport {
    rebuild_account_tx_index(AccountTxIndexOptions {
        data_dir: data_dir.to_path_buf(),
    })
    .expect("account tx index build")
}

fn index_status(data_dir: &Path) -> AccountTxIndexStatusReport {
    account_tx_index_status(AccountTxIndexOptions {
        data_dir: data_dir.to_path_buf(),
    })
    .expect("account tx index status")
}

fn tip_height(data_dir: &Path) -> u64 {
    NodeStore::new(data_dir)
        .read_blocks()
        .expect("blocks")
        .blocks
        .last()
        .expect("tip block")
        .header
        .height
}

fn assert_served_from_index(data_dir: &Path, address: &str) -> AccountTxReport {
    let report = history(data_dir, address);
    assert!(
        report.index_used,
        "{address} was not served from the index: {report:?}"
    );
    assert_eq!(report.archive_lookup_count, 0);
    assert_eq!(report.scanned_block_count, 0);
    assert_eq!(report.rows, scanned(data_dir, address));
    report
}

/// Copies the disk index (metadata and account shards) aside.
fn save_disk_index(data_dir: &Path, label: &str) -> PathBuf {
    let saved = data_dir.join(format!("saved-disk-index-{label}"));
    fs::create_dir_all(saved.join(ACCOUNT_TX_ACCOUNT_SHARDS_DIR)).expect("saved dir");
    fs::copy(
        account_tx_disk_index_path(data_dir),
        saved.join(ACCOUNT_TX_DISK_INDEX_FILE),
    )
    .expect("save disk meta");
    for entry in fs::read_dir(account_tx_account_shards_dir(data_dir)).expect("shards") {
        let entry = entry.expect("shard entry");
        fs::copy(
            entry.path(),
            saved
                .join(ACCOUNT_TX_ACCOUNT_SHARDS_DIR)
                .join(entry.file_name()),
        )
        .expect("save shard");
    }
    saved
}

/// Puts a saved disk index back. With `meta_only`, only the metadata file is
/// restored, so the shards written by a later append stay on disk.
fn restore_disk_index(data_dir: &Path, saved: &Path, meta_only: bool) {
    fs::copy(
        saved.join(ACCOUNT_TX_DISK_INDEX_FILE),
        account_tx_disk_index_path(data_dir),
    )
    .expect("restore disk meta");
    if meta_only {
        return;
    }
    let shards = account_tx_account_shards_dir(data_dir);
    fs::remove_dir_all(&shards).expect("remove shards");
    fs::create_dir_all(&shards).expect("shards dir");
    for entry in fs::read_dir(saved.join(ACCOUNT_TX_ACCOUNT_SHARDS_DIR)).expect("saved shards") {
        let entry = entry.expect("saved shard");
        fs::copy(entry.path(), shards.join(entry.file_name())).expect("restore shard");
    }
}

#[test]
fn a_block_committed_after_the_build_is_served_from_the_index_without_a_rebuild() {
    for backend in [Backend::Legacy, Backend::Transactional] {
        let data_dir = chain(&format!("account-tx-commit-follow-{backend:?}"), backend);
        commit_transfer(&data_dir, RECIPIENT_A);
        let built = build(&data_dir);
        assert!(built.disk_index_usable, "{built:?}");
        assert_served_from_index(&data_dir, RECIPIENT_A);

        // No rebuild between these commits and the reads.
        commit_transfer(&data_dir, RECIPIENT_B);
        commit_transfer(&data_dir, RECIPIENT_A);
        let a = assert_served_from_index(&data_dir, RECIPIENT_A);
        assert_eq!(a.rows.len(), 2, "{backend:?}");
        let b = assert_served_from_index(&data_dir, RECIPIENT_B);
        assert_eq!(b.rows.len(), 1, "{backend:?}");
        assert_eq!(b.rows[0].block_height, tip_height(&data_dir) - 1);
        let faucet = a.rows[0].from_address.clone();
        let sender = assert_served_from_index(&data_dir, &faucet);
        assert_eq!(sender.rows.len(), 3, "{backend:?}");
        let status = index_status(&data_dir);
        assert!(status.disk_index_usable, "{status:?}");
        assert_eq!(status.disk_index_lag_blocks, Some(0), "{status:?}");
        assert_eq!(status.current_tip_height, Some(tip_height(&data_dir)));
        assert_eq!(status.disk_indexed_to_height, Some(tip_height(&data_dir)));
        assert_eq!(status.disk_tip_hash, status.current_tip_hash);
        // The aggregate file follows too.
        assert!(status.index_usable, "{status:?}");

        fs::remove_dir_all(data_dir).expect("remove test data dir");
    }
}

#[test]
fn a_crash_between_the_commit_and_the_index_append_leaves_a_rebuildable_state() {
    for backend in [Backend::Legacy, Backend::Transactional] {
        for meta_only in [false, true] {
            let data_dir = chain(
                &format!("account-tx-commit-crash-{backend:?}-{meta_only}"),
                backend,
            );
            commit_transfer(&data_dir, RECIPIENT_A);
            build(&data_dir);
            let saved = save_disk_index(&data_dir, "before-b");
            let saved_aggregate = save_aggregate_index(&data_dir, "before-b");

            // The block and its receipts are durable; the index append is lost
            // (all of it, or everything from the disk metadata write on; the
            // aggregate is written after the disk metadata).
            commit_transfer(&data_dir, RECIPIENT_B);
            restore_disk_index(&data_dir, &saved, meta_only);
            restore_aggregate_index(&data_dir, &saved_aggregate);
            assert_eq!(index_status(&data_dir).disk_index_lag_blocks, Some(1));
            let behind = history(&data_dir, RECIPIENT_B);
            assert!(!behind.index_used, "a stale index answered: {behind:?}");
            assert_eq!(behind.rows, scanned(&data_dir, RECIPIENT_B));
            assert_eq!(behind.rows.len(), 1);

            // The next commit does not paper over the gap.
            commit_transfer(&data_dir, RECIPIENT_C);
            assert_eq!(index_status(&data_dir).disk_index_lag_blocks, Some(2));
            let still_behind = history(&data_dir, RECIPIENT_C);
            assert!(!still_behind.index_used, "{still_behind:?}");
            assert_eq!(still_behind.rows, scanned(&data_dir, RECIPIENT_C));

            // The build repairs it, and later commits follow again.
            let rebuilt = build(&data_dir);
            assert!(rebuilt.disk_index_usable, "{rebuilt:?}");
            for address in [RECIPIENT_A, RECIPIENT_B, RECIPIENT_C] {
                assert_served_from_index(&data_dir, address);
            }
            commit_transfer(&data_dir, RECIPIENT_D);
            assert_eq!(index_status(&data_dir).disk_index_lag_blocks, Some(0));
            assert_served_from_index(&data_dir, RECIPIENT_D);
            assert_served_from_index(&data_dir, RECIPIENT_B);

            fs::remove_dir_all(data_dir).expect("remove test data dir");
        }
    }
}

/// Writes a block that links `receipts` (appended to the receipt log), as a
/// durable commit leaves it, and returns it with an archive entry for it.
fn write_durable_block(
    data_dir: &Path,
    batch_kind: &str,
    receipts: Vec<Receipt>,
    archive_entry: Option<BatchArchiveEntry>,
    label: &str,
) -> (BlockRecord, BatchArchiveEntry) {
    let store = NodeStore::new(data_dir);
    let tip = store
        .read_blocks()
        .expect("blocks")
        .blocks
        .last()
        .cloned()
        .expect("tip");
    let archive_entry = archive_entry.unwrap_or_else(|| BatchArchiveEntry {
        batch_kind: batch_kind.to_string(),
        batch_id: hash_hex("account-tx-commit-index.batch", label.as_bytes()),
        payload_hash: String::new(),
        payload_json: String::new(),
    });
    let mut block = tip.clone();
    block.header.height = tip.header.height + 1;
    block.header.parent_hash = tip.header.block_hash.clone();
    block.header.batch_kind = batch_kind.to_string();
    block.header.batch_id = archive_entry.batch_id.clone();
    block.header.receipt_count = receipts.len() as u64;
    block.header.block_hash = hash_hex("account-tx-commit-index.block", label.as_bytes());
    block.receipt_ids = receipts.iter().map(|receipt| receipt.tx_id.clone()).collect();
    block.fastpay_pre_state_effects = Vec::new();
    for receipt in receipts {
        store.append_receipt(receipt).expect("append receipt");
    }
    store.append_block(block.clone()).expect("append block");
    (block, archive_entry)
}

fn append_after_commit(
    data_dir: &Path,
    block: &BlockRecord,
    archive_entry: &BatchArchiveEntry,
    receipts: &[Receipt],
) -> io::Result<AccountTxIndexAppend> {
    let store = NodeStore::new(data_dir);
    let genesis = store.read_genesis().expect("genesis");
    append_account_tx_index_after_commit(&store, &genesis, block, archive_entry, receipts)
}

#[test]
fn repeated_governance_receipt_ids_keep_the_index_following() {
    let data_dir = chain("account-tx-commit-governance", Backend::Legacy);
    commit_transfer(&data_dir, RECIPIENT_A);
    build(&data_dir);
    let amendment_id = hash_hex("account-tx-commit-index.amendment", b"repeat");
    let rejected = Receipt::rejected(
        amendment_id.clone(),
        "vault_bridge_route_profile_rejected",
        "vault bridge route does not exactly match the active NAV proof profile",
    );
    let accepted = Receipt::accepted(amendment_id.clone(), "vault bridge route profile activated");
    let store = NodeStore::new(&data_dir);
    let mut receipt_log = store.read_receipts().expect("receipts");

    // Two governance blocks repeat the amendment id; each is appended after
    // its durable write, and a replay of the same append changes nothing.
    for (receipt, label) in [(rejected, "governance-1"), (accepted, "governance-2")] {
        let (block, archive_entry) = write_durable_block(
            &data_dir,
            BATCH_KIND_GOVERNANCE,
            vec![receipt.clone()],
            None,
            label,
        );
        receipt_log.push(receipt.clone());
        store
            .write_receipts(&receipt_log)
            .expect("write block-ordered receipt log");
        let receipts = [receipt];
        assert_eq!(
            append_after_commit(&data_dir, &block, &archive_entry, &receipts).expect("append"),
            AccountTxIndexAppend::Appended
        );
        let meta = fs::read(account_tx_disk_index_path(&data_dir)).expect("meta");
        assert_eq!(
            append_after_commit(&data_dir, &block, &archive_entry, &receipts).expect("replay"),
            AccountTxIndexAppend::AlreadyCurrent
        );
        assert_eq!(fs::read(account_tx_disk_index_path(&data_dir)).expect("meta"), meta);
    }
    assert_eq!(
        store
            .read_receipts()
            .expect("receipts")
            .iter()
            .filter(|receipt| receipt.tx_id == amendment_id)
            .count(),
        2
    );
    let status = index_status(&data_dir);
    assert_eq!(status.disk_index_lag_blocks, Some(0), "{status:?}");
    assert_served_from_index(&data_dir, RECIPIENT_A);

    // A rebuild over the same history agrees with the followed index.
    let followed = fs::read(account_tx_disk_index_path(&data_dir)).expect("meta");
    let followed_rows = history(&data_dir, RECIPIENT_A).rows;
    build(&data_dir);
    let rebuilt: AccountTxDiskIndex =
        read_account_tx_disk_index_file(&account_tx_disk_index_path(&data_dir)).expect("meta");
    let followed: AccountTxDiskIndex = serde_json::from_slice(&followed).expect("followed meta");
    assert_eq!(
        (
            followed.indexed_from_height,
            followed.indexed_to_height,
            followed.indexed_block_count,
            followed.indexed_row_count,
            followed.account_count,
            &followed.tip_hash,
        ),
        (
            rebuilt.indexed_from_height,
            rebuilt.indexed_to_height,
            rebuilt.indexed_block_count,
            rebuilt.indexed_row_count,
            rebuilt.account_count,
            &rebuilt.tip_hash,
        )
    );
    assert_eq!(history(&data_dir, RECIPIENT_A).rows, followed_rows);

    // An ordinary id repeated inside one block is still refused, and the
    // index stays where it was.
    let payment = receipt_log[0].clone();
    let (block, archive_entry) = write_durable_block(
        &data_dir,
        BATCH_KIND_TRANSPARENT,
        vec![payment.clone(), payment.clone()],
        None,
        "repeated-ordinary",
    );
    let error = append_after_commit(&data_dir, &block, &archive_entry, &[payment.clone(), payment])
        .expect_err("a repeated ordinary id is refused");
    assert!(
        error.to_string().contains("receipt log contains duplicate tx_id"),
        "{error}"
    );
    assert_eq!(index_status(&data_dir).disk_index_lag_blocks, Some(1));

    fs::remove_dir_all(data_dir).expect("remove test data dir");
}

/// Consensus-visible outputs of a data directory.
fn consensus_view(data_dir: &Path) -> (StatusReport, Vec<BlockRecord>, Vec<Receipt>, String) {
    let store = NodeStore::new(data_dir);
    let status = status(NodeOptions {
        data_dir: data_dir.to_path_buf(),
    })
    .expect("status");
    let ledger = serde_json::to_string(&store.read_ledger().expect("ledger")).expect("ledger json");
    (
        status,
        store.read_blocks().expect("blocks").blocks,
        store.read_receipts().expect("receipts"),
        ledger,
    )
}

fn copy_dir(source: &Path, target: &Path) {
    fs::create_dir_all(target).expect("target dir");
    for entry in fs::read_dir(source).expect("source dir") {
        let entry = entry.expect("entry");
        let path = entry.path();
        let destination = target.join(entry.file_name());
        if entry.file_type().expect("file type").is_dir() {
            copy_dir(&path, &destination);
        } else {
            fs::copy(&path, &destination).expect("copy file");
        }
    }
}

#[test]
fn the_index_append_changes_no_consensus_output() {
    for backend in [Backend::Legacy, Backend::Transactional] {
        let with_index = chain(&format!("account-tx-commit-bytes-indexed-{backend:?}"), backend);
        commit_transfer(&with_index, RECIPIENT_A);
        build(&with_index);
        let without_index = unique_test_dir(&format!("account-tx-commit-bytes-plain-{backend:?}"));
        copy_dir(&with_index, &without_index);
        fs::remove_file(account_tx_index_path(&without_index)).expect("remove aggregate");
        fs::remove_file(account_tx_disk_index_path(&without_index)).expect("remove disk meta");
        fs::remove_dir_all(account_tx_account_shards_dir(&without_index)).expect("remove shards");

        // The same signed batches commit in both directories.
        for to in [RECIPIENT_B, RECIPIENT_C] {
            let batch_file = transfer_batch(&with_index, to);
            apply(&with_index, &batch_file);
            apply(&without_index, &batch_file);
        }
        let (status_indexed, blocks_indexed, receipts_indexed, ledger_indexed) =
            consensus_view(&with_index);
        let (status_plain, blocks_plain, receipts_plain, ledger_plain) =
            consensus_view(&without_index);
        assert_eq!(status_indexed.block_height, status_plain.block_height);
        assert_eq!(status_indexed.block_tip_hash, status_plain.block_tip_hash);
        assert_eq!(status_indexed.state_root, status_plain.state_root);
        assert_eq!(blocks_indexed, blocks_plain);
        assert_eq!(receipts_indexed, receipts_plain);
        assert_eq!(ledger_indexed, ledger_plain);
        assert!(!account_tx_disk_index_path(&without_index).exists());
        assert!(!account_tx_index_path(&without_index).exists());

        fs::remove_dir_all(with_index).expect("remove indexed dir");
        fs::remove_dir_all(without_index).expect("remove plain dir");
    }
}

/// Copies the aggregate index file aside.
fn save_aggregate_index(data_dir: &Path, label: &str) -> PathBuf {
    let saved = data_dir.join(format!("saved-aggregate-{label}.json"));
    fs::copy(account_tx_index_path(data_dir), &saved).expect("save aggregate");
    saved
}

fn restore_aggregate_index(data_dir: &Path, saved: &Path) {
    fs::copy(saved, account_tx_index_path(data_dir)).expect("restore aggregate");
}

#[test]
fn status_reports_both_indexes_usable_while_following_and_the_lag_when_behind() {
    for backend in [Backend::Legacy, Backend::Transactional] {
        let data_dir = chain(&format!("account-tx-commit-status-{backend:?}"), backend);
        commit_transfer(&data_dir, RECIPIENT_A);
        build(&data_dir);

        // A followed commit keeps both indexes current.
        commit_transfer(&data_dir, RECIPIENT_B);
        let status = index_status(&data_dir);
        assert!(status.index_usable, "{backend:?} {status:?}");
        assert!(status.disk_index_usable, "{backend:?} {status:?}");
        assert_eq!(status.tip_hash, status.current_tip_hash);
        assert_eq!(status.indexed_to_height, Some(tip_height(&data_dir)));
        assert_eq!(status.index_lag_blocks, Some(0));
        assert_eq!(status.disk_index_lag_blocks, Some(0));

        // The aggregate holds the new rows too, not only a new tip: with the
        // disk index gone, reads answer from it.
        let disk_meta = account_tx_disk_index_path(&data_dir);
        let saved_meta = fs::read(&disk_meta).expect("disk meta");
        fs::remove_file(&disk_meta).expect("hide disk meta");
        for address in [RECIPIENT_A, RECIPIENT_B] {
            assert_served_from_index(&data_dir, address);
        }
        fs::write(&disk_meta, saved_meta).expect("restore disk meta");

        // Both lost (a crash right after the commit): both report the lag.
        let saved_disk = save_disk_index(&data_dir, "before-c");
        let saved_aggregate = save_aggregate_index(&data_dir, "before-c");
        commit_transfer(&data_dir, RECIPIENT_C);
        restore_disk_index(&data_dir, &saved_disk, false);
        restore_aggregate_index(&data_dir, &saved_aggregate);
        let behind = index_status(&data_dir);
        assert!(!behind.index_usable && !behind.disk_index_usable, "{behind:?}");
        assert_eq!(behind.index_lag_blocks, Some(1));
        assert_eq!(behind.disk_index_lag_blocks, Some(1));
        assert_eq!(
            behind.reason.as_deref(),
            Some("account_tx index tip hash is stale")
        );
        assert!(!history(&data_dir, RECIPIENT_C).index_used);

        // Only the aggregate write lost: the disk index follows, the aggregate
        // stays behind until the build.
        build(&data_dir);
        let saved_aggregate = save_aggregate_index(&data_dir, "before-d");
        commit_transfer(&data_dir, RECIPIENT_D);
        restore_aggregate_index(&data_dir, &saved_aggregate);
        commit_transfer(&data_dir, RECIPIENT_A);
        let split = index_status(&data_dir);
        assert!(!split.index_usable && split.disk_index_usable, "{split:?}");
        assert_eq!(split.index_lag_blocks, Some(2));
        assert_eq!(split.disk_index_lag_blocks, Some(0));
        assert_served_from_index(&data_dir, RECIPIENT_D);
        let rebuilt = build(&data_dir);
        assert!(rebuilt.index_usable && rebuilt.disk_index_usable, "{rebuilt:?}");
        assert_eq!(index_status(&data_dir).index_lag_blocks, Some(0));

        fs::remove_dir_all(data_dir).expect("remove test data dir");
    }
}
