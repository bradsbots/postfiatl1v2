use super::*;

fn account_tx_window(data_dir: &Path, address: &str, limit: usize) -> AccountTxReport {
    account_tx(AccountTxQueryOptions {
        data_dir: data_dir.to_path_buf(),
        address: address.to_string(),
        from_height: Some(1),
        to_height: Some(1),
        limit: Some(limit),
    })
    .expect("account tx window")
}

fn assert_truncation_matches_omitted_rows(data_dir: &Path, sender: &str, recipient: &str) {
    // The recipient has exactly one row: a limit of one returns all of it.
    let exact = account_tx_window(data_dir, recipient, 1);
    assert_eq!(exact.row_count, 1);
    assert!(!exact.truncated, "exact-limit window reported truncated");

    // The sender has two rows: a limit of one omits one, a limit of two none.
    let short = account_tx_window(data_dir, sender, 1);
    assert_eq!(short.row_count, 1);
    assert!(short.truncated, "omitted row was not reported");
    let full = account_tx_window(data_dir, sender, 2);
    assert_eq!(full.row_count, 2);
    assert!(!full.truncated, "exact-limit window reported truncated");
}

/// One transparent block at height 1 with two transfers from the same sender.
fn two_transfer_chain(label: &str) -> (PathBuf, String, String) {
    let data_dir = unique_test_dir(label);
    init(InitOptions {
        data_dir: data_dir.clone(),
        chain_id: "postfiat-local".to_string(),
        node_id: "validator-0".to_string(),
        validator_count: 1,
    })
    .expect("init");
    run_once(NodeOptions {
        data_dir: data_dir.clone(),
    })
    .expect("run once");
    let mut pending = Vec::new();
    for to in [
        "pfrecipient000000000000000000000000000001",
        "pfrecipient000000000000000000000000000002",
    ] {
        pending.push(
            submit_transfer_to_mempool(TransferOptions {
                data_dir: data_dir.clone(),
                key_file: None,
                to: to.to_string(),
                amount: ACCOUNT_RESERVE,
            })
            .expect("submit transfer"),
        );
    }
    let batch_file = data_dir.join("mempool-batch.json");
    create_mempool_batch(MempoolBatchOptions {
        data_dir: data_dir.clone(),
        batch_file: batch_file.clone(),
        max_transactions: 10,
    })
    .expect("create mempool batch");
    let receipts = apply_batch(ApplyBatchOptions {
        data_dir: data_dir.clone(),
        batch_file,
        certificate_file: None,
    })
    .expect("apply batch");
    assert!(receipts.iter().all(|receipt| receipt.accepted), "{receipts:?}");
    let sender = pending[0].transfer.unsigned.from.clone();
    let recipient = pending[1].transfer.unsigned.to.clone();
    (data_dir, sender, recipient)
}

#[test]
fn account_tx_truncated_only_when_rows_are_omitted() {
    let (data_dir, sender, recipient) = two_transfer_chain("postfiat-account-tx-truncation");

    assert!(!account_tx_window(&data_dir, &recipient, 1).index_used);
    assert_truncation_matches_omitted_rows(&data_dir, &sender, &recipient);

    rebuild_account_tx_index(AccountTxIndexOptions {
        data_dir: data_dir.clone(),
    })
    .expect("build account tx index");
    assert!(account_tx_window(&data_dir, &recipient, 1).index_used);
    assert_truncation_matches_omitted_rows(&data_dir, &sender, &recipient);

    fs::remove_dir_all(data_dir).expect("remove test data dir");
}

fn account_tx_rows_without_start(data_dir: &Path, address: &str, limit: usize) -> AccountTxReport {
    account_tx(AccountTxQueryOptions {
        data_dir: data_dir.to_path_buf(),
        address: address.to_string(),
        from_height: None,
        to_height: Some(1),
        limit: Some(limit),
    })
    .expect("account tx without start height")
}

#[test]
fn account_tx_scan_and_index_return_the_newest_rows_without_a_start_height() {
    let (data_dir, sender, _) = two_transfer_chain("postfiat-account-tx-newest");

    let scan = account_tx_rows_without_start(&data_dir, &sender, 1);
    assert!(!scan.index_used);
    rebuild_account_tx_index(AccountTxIndexOptions {
        data_dir: data_dir.clone(),
    })
    .expect("build account tx index");
    let indexed = account_tx_rows_without_start(&data_dir, &sender, 1);
    assert!(indexed.index_used);

    // Without a start height both paths return the newest matching row.
    assert_eq!(indexed.rows.len(), 1);
    assert_eq!(indexed.rows[0].transaction_index, 1);
    assert_eq!(scan.rows, indexed.rows, "scan and index disagree on order");
    assert!(scan.truncated && indexed.truncated);

    fs::remove_dir_all(data_dir).expect("remove test data dir");
}

fn account_tx_all(data_dir: &Path, address: &str) -> AccountTxReport {
    account_tx(AccountTxQueryOptions {
        data_dir: data_dir.to_path_buf(),
        address: address.to_string(),
        from_height: None,
        to_height: None,
        limit: Some(10),
    })
    .expect("account tx")
}

#[test]
fn account_tx_scan_and_index_return_the_same_transaction_kinds() {
    // Height 1: two transfers from the faucet. Height 2: the faucet creates an asset.
    let (data_dir, sender, _) = two_transfer_chain("postfiat-account-tx-kinds");
    let store = NodeStore::new(&data_dir);
    let genesis = store.read_genesis().expect("genesis");
    let faucet_key = read_transfer_key_file(&data_dir, None).expect("faucet key");
    assert_eq!(faucet_key.address, sender);
    let operation = AssetTransactionOperation::AssetCreate(AssetCreateOperation {
        issuer: sender.clone(),
        code: "EUR".to_string(),
        version: 1,
        precision: 2,
        display_name: "Euro".to_string(),
        max_supply: Some(10_000),
        requires_authorization: false,
        freeze_enabled: false,
        clawback_enabled: false,
    });
    let quote = asset_fee_quote(AssetFeeQuoteOptions {
        data_dir: data_dir.clone(),
        source: sender.clone(),
        operation_json: serde_json::to_string(&operation).expect("operation json"),
        sequence: None,
    })
    .expect("asset create fee quote");
    let create = super::signed_asset_transaction_for_test(
        &genesis,
        &store.read_ledger().expect("ledger"),
        &sender,
        &faucet_key.public_key_hex,
        &faucet_key.private_key_hex,
        ASSET_CREATE_TRANSACTION_KIND,
        quote.sequence,
        operation,
    );
    submit_signed_asset_transaction_json_to_mempool(SignedAssetTransactionJsonSubmitOptions {
        data_dir: data_dir.clone(),
        signed_asset_transaction_json: serde_json::to_string(&create).expect("signed json"),
    })
    .expect("submit asset create");
    let batch_file = data_dir.join("asset-batch.json");
    create_mempool_batch(MempoolBatchOptions {
        data_dir: data_dir.clone(),
        batch_file: batch_file.clone(),
        max_transactions: 10,
    })
    .expect("create asset batch");
    let receipts = apply_batch(ApplyBatchOptions {
        data_dir: data_dir.clone(),
        batch_file,
        certificate_file: None,
    })
    .expect("apply asset batch");
    assert!(receipts.iter().all(|receipt| receipt.accepted), "{receipts:?}");

    let scan = account_tx_all(&data_dir, &sender);
    assert!(!scan.index_used);
    rebuild_account_tx_index(AccountTxIndexOptions {
        data_dir: data_dir.clone(),
    })
    .expect("build account tx index");
    let indexed = account_tx_all(&data_dir, &sender);
    assert!(indexed.index_used);

    let kinds = |report: &AccountTxReport| {
        report
            .rows
            .iter()
            .map(|row| row.transaction_kind.clone())
            .collect::<Vec<_>>()
    };
    assert_eq!(
        kinds(&indexed),
        [
            TRANSFER_TRANSACTION_KIND,
            TRANSFER_TRANSACTION_KIND,
            ASSET_CREATE_TRANSACTION_KIND
        ]
    );
    assert_eq!(scan.rows, indexed.rows, "scan and index disagree on rows");
    assert!(!scan.truncated && !indexed.truncated);

    fs::remove_dir_all(data_dir).expect("remove test data dir");
}
