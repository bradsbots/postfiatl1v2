//! Exchange integration over the real `rpc-serve` process: `tx` and
//! `account_tx` return `payment_v2` memo contents, and `account_tx` lists a
//! shielded withdrawal as a credit of the recipient account. Every response
//! is checked with the Rust SDK response validator.

use std::fs;
use std::io::{BufRead, BufReader, Write};
use std::net::{TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use postfiat_crypto_provider::{
    bytes_to_hex, hash_hex, hex_to_bytes, ml_dsa_65_sign, ML_DSA_65_ALGORITHM,
};
use postfiat_node::{
    apply_batch, create_mempool_batch, faucet_key, init, rebuild_account_tx_index,
    submit_signed_payment_v2_json_to_mempool, AccountTxIndexOptions, ApplyBatchOptions,
    InitOptions, MempoolBatchOptions, NodeOptions, SignedPaymentV2JsonSubmitOptions,
};
use postfiat_rpc_sdk::{
    account_tx_request, tx_request, validate_response_kind, RpcRequest, RpcResponse,
    RpcResponseKind,
};
use postfiat_storage::NodeStore;
use postfiat_types::{
    BatchArchiveEntry, OrchardWithdrawActionPayload, PaymentMemo, Receipt, ShieldedAction,
    ShieldedActionBatch, SignedPaymentV2, UnsignedPaymentV2, PAYMENT_V2_TRANSACTION_KIND,
};

const PAYMENT_RECIPIENT: &str = "pf0000000000000000000000000000000000000001";
const WITHDRAW_RECIPIENT: &str = "pf0000000000000000000000000000000000000002";
const DEPOSIT_TAG: &str = "customer-7781";
const WITHDRAW_AMOUNT: u64 = 3_000_000;

fn node_bin() -> &'static str {
    env!("CARGO_BIN_EXE_postfiat-node")
}

fn unique_root() -> PathBuf {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("system clock before epoch")
        .as_nanos();
    std::env::temp_dir().join(format!(
        "postfiat-exchange-rpc-history-{}-{nanos}",
        std::process::id()
    ))
}

fn free_port() -> u16 {
    TcpListener::bind(("127.0.0.1", 0))
        .expect("bind ephemeral port")
        .local_addr()
        .expect("ephemeral local address")
        .port()
}

fn wait_for_file(path: &Path) {
    let deadline = Instant::now() + Duration::from_secs(20);
    while Instant::now() < deadline {
        if path.metadata().is_ok_and(|metadata| metadata.len() > 0) {
            return;
        }
        thread::sleep(Duration::from_millis(20));
    }
    panic!("timed out waiting for {}", path.display());
}

fn rpc_call(port: u16, request: &RpcRequest) -> RpcResponse {
    let mut stream = TcpStream::connect(("127.0.0.1", port)).expect("connect RPC server");
    stream
        .set_read_timeout(Some(Duration::from_secs(30)))
        .expect("set RPC timeout");
    serde_json::to_writer(&mut stream, request).expect("write RPC request");
    stream.write_all(b"\n").expect("terminate RPC request");
    stream.flush().expect("flush RPC request");
    let mut response = String::new();
    BufReader::new(stream)
        .read_line(&mut response)
        .expect("read RPC response");
    serde_json::from_str(&response).expect("decode RPC response")
}

fn text_hex(text: &str) -> String {
    bytes_to_hex(text.as_bytes())
}

/// Finalizes one faucet `payment_v2` carrying a deposit-tag memo at height 1.
fn finalize_memo_payment(data_dir: &Path) -> String {
    let store = NodeStore::new(data_dir);
    let genesis = store.read_genesis().expect("genesis");
    let ledger = store.read_ledger().expect("ledger");
    let key = faucet_key(NodeOptions {
        data_dir: data_dir.to_path_buf(),
    })
    .expect("faucet key");
    let private_key = hex_to_bytes(&key.private_key_hex).expect("private key bytes");
    let sequence = ledger.account(&key.address).expect("faucet").sequence + 1;
    let memo = PaymentMemo {
        memo_type: text_hex("deposit_tag"),
        memo_format: text_hex("text/plain"),
        memo_data: text_hex(DEPOSIT_TAG),
    };
    let mut fee = 1;
    let signed = loop {
        let unsigned = UnsignedPaymentV2 {
            chain_id: genesis.chain_id.clone(),
            genesis_hash: postfiat_execution::genesis_hash(&genesis),
            protocol_version: genesis.protocol_version,
            address_namespace: postfiat_types::ADDRESS_NAMESPACE.to_string(),
            transaction_kind: PAYMENT_V2_TRANSACTION_KIND.to_string(),
            signature_algorithm_id: ML_DSA_65_ALGORITHM.to_string(),
            from: key.address.clone(),
            to: PAYMENT_RECIPIENT.to_string(),
            amount: postfiat_execution::ACCOUNT_RESERVE,
            fee,
            sequence,
            memos: vec![memo.clone()],
        };
        let signature = ml_dsa_65_sign(&private_key, &unsigned.signing_bytes()).expect("sign");
        let signed = SignedPaymentV2 {
            unsigned,
            algorithm_id: ML_DSA_65_ALGORITHM.to_string(),
            public_key_hex: key.public_key_hex.clone(),
            signature_hex: bytes_to_hex(&signature),
        };
        let minimum = postfiat_execution::minimum_payment_v2_fee_for_ledger(&ledger, &signed);
        if fee >= minimum {
            break signed;
        }
        fee = minimum;
    };
    submit_signed_payment_v2_json_to_mempool(SignedPaymentV2JsonSubmitOptions {
        data_dir: data_dir.to_path_buf(),
        signed_payment_v2_json: serde_json::to_string(&signed).expect("payment json"),
    })
    .expect("admit payment v2");
    let batch_file = data_dir.join("payment-v2-batch.json");
    create_mempool_batch(MempoolBatchOptions {
        data_dir: data_dir.to_path_buf(),
        batch_file: batch_file.clone(),
        max_transactions: 10,
    })
    .expect("create payment v2 batch");
    let receipts = apply_batch(ApplyBatchOptions {
        data_dir: data_dir.to_path_buf(),
        batch_file,
        certificate_file: None,
    })
    .expect("apply payment v2 batch");
    assert_eq!(receipts.len(), 1);
    assert!(receipts[0].accepted, "{receipts:?}");
    receipts[0].tx_id.clone()
}

/// Appends a finalized shielded block holding one accepted
/// `orchard_withdraw_v1` to `WITHDRAW_RECIPIENT`, as an ordered commit stores
/// it (block, archived batch, receipt). `account_tx` and `tx` read only these
/// stored records, so no Orchard proof is generated here.
fn append_shielded_withdrawal(data_dir: &Path) -> String {
    let store = NodeStore::new(data_dir);
    let tip = store
        .read_blocks()
        .expect("blocks")
        .blocks
        .last()
        .cloned()
        .expect("chain has a block");
    let batch_id = hash_hex("postfiat.test.exchange_rpc", b"shielded-batch");
    let batch = ShieldedActionBatch::new(
        batch_id.clone(),
        vec![ShieldedAction::OrchardWithdrawV1(
            OrchardWithdrawActionPayload {
                action_json: serde_json::json!({ "pool_id": "orchard-v1" }).to_string(),
                to: WITHDRAW_RECIPIENT.to_string(),
                amount: WITHDRAW_AMOUNT,
                fee: 5,
                policy_id: "postfiat-orchard-withdraw-public-v1".to_string(),
                disclosure_hash: hash_hex("postfiat.test.exchange_rpc", b"disclosure"),
            },
        )],
    );
    let receipt = Receipt::accepted(
        hash_hex("postfiat.test.exchange_rpc", b"withdraw-receipt"),
        "Orchard withdraw applied",
    );
    let mut block = tip.clone();
    block.header.height = tip.header.height + 1;
    block.header.parent_hash = tip.header.block_hash.clone();
    block.header.batch_kind = "shielded".to_string();
    block.header.batch_id = batch_id.clone();
    block.header.receipt_count = 1;
    block.header.block_hash = hash_hex("postfiat.test.exchange_rpc", b"shielded-block");
    block.receipt_ids = vec![receipt.tx_id.clone()];
    block.fastpay_pre_state_effects = Vec::new();
    store
        .append_batch_archive_entry(BatchArchiveEntry {
            batch_kind: "shielded".to_string(),
            batch_id,
            payload_hash: String::new(),
            payload_json: serde_json::to_string(&batch).expect("shielded batch json"),
        })
        .expect("archive shielded batch");
    store
        .append_receipt(receipt.clone())
        .expect("append withdraw receipt");
    store.append_block(block).expect("append shielded block");
    receipt.tx_id
}

#[test]
fn rpc_tx_and_account_tx_return_memo_contents_and_shielded_withdrawal_credits() {
    let root = unique_root();
    let data_dir = root.join("node");
    init(InitOptions {
        data_dir: data_dir.clone(),
        chain_id: "postfiat-exchange-rpc-history-test".to_string(),
        node_id: "validator-0".to_string(),
        validator_count: 1,
    })
    .expect("initialize RPC test node");
    let payment_tx_id = finalize_memo_payment(&data_dir);
    let withdraw_tx_id = append_shielded_withdrawal(&data_dir);
    rebuild_account_tx_index(AccountTxIndexOptions {
        data_dir: data_dir.clone(),
    })
    .expect("build account tx index");

    let port = free_port();
    let ready = root.join("rpc.ready.json");
    let spool_dir = root.join("rpc-spool");
    let mut child = Command::new(node_bin())
        .args(["rpc-serve", "--unsafe-devnet-json-storage", "--data-dir"])
        .arg(&data_dir)
        .arg("--spool-dir")
        .arg(&spool_dir)
        .arg("--ready-file")
        .arg(&ready)
        .args([
            "--bind-host",
            "127.0.0.1",
            "--port",
            &port.to_string(),
            "--max-requests",
            "4",
            "--timeout-ms",
            "30000",
            "--child-timeout-ms",
            "30000",
        ])
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn RPC server");
    wait_for_file(&ready);

    let tx = rpc_call(port, &tx_request("memo-tx", payment_tx_id.clone()));
    validate_response_kind(&tx, RpcResponseKind::Tx).expect("tx response validates");
    let tx = tx.result.expect("tx result");
    let tx_rows = tx["transaction_rows"]
        .as_array()
        .expect("tx transaction rows");
    assert_eq!(tx_rows.len(), 1);
    assert_eq!(tx_rows[0]["tx_id"], payment_tx_id.as_str());
    assert_eq!(tx_rows[0]["to"], PAYMENT_RECIPIENT);
    assert_eq!(tx_rows[0]["memo_count"], 1);
    assert_eq!(tx_rows[0]["memo_hash"].as_str().map(str::len), Some(96));
    assert_eq!(tx_rows[0]["memos"][0]["memo_data"], text_hex(DEPOSIT_TAG));
    assert_eq!(tx_rows[0]["memos"][0]["memo_data_text"], DEPOSIT_TAG);
    assert_eq!(tx_rows[0]["memos"][0]["memo_type_text"], "deposit_tag");
    assert_eq!(tx_rows[0]["memos"][0]["memo_format_text"], "text/plain");

    let deposits = rpc_call(
        port,
        &account_tx_request("memo-account-tx", PAYMENT_RECIPIENT, None, None, Some(10)),
    );
    validate_response_kind(&deposits, RpcResponseKind::AccountTx)
        .expect("account_tx response validates");
    let deposits = deposits.result.expect("account_tx result");
    assert_eq!(deposits["index_used"], true);
    assert_eq!(deposits["rows"].as_array().map(Vec::len), Some(1));
    assert_eq!(deposits["rows"][0], tx_rows[0]);

    let withdraw_tx = rpc_call(port, &tx_request("withdraw-tx", withdraw_tx_id.clone()));
    validate_response_kind(&withdraw_tx, RpcResponseKind::Tx).expect("withdraw tx validates");
    let withdraw_tx = withdraw_tx.result.expect("withdraw tx result");
    assert_eq!(withdraw_tx["block"]["header"]["batch_kind"], "shielded");

    let credits = rpc_call(
        port,
        &account_tx_request(
            "withdraw-account-tx",
            WITHDRAW_RECIPIENT,
            None,
            None,
            Some(10),
        ),
    );
    validate_response_kind(&credits, RpcResponseKind::AccountTx)
        .expect("withdraw account_tx validates");
    let credits = credits.result.expect("withdraw account_tx result");
    assert_eq!(credits["index_used"], true);
    let credit_rows = credits["rows"].as_array().expect("withdraw rows");
    assert_eq!(credit_rows.len(), 1);
    let credit = &credit_rows[0];
    assert_eq!(credit["tx_id"], withdraw_tx_id.as_str());
    assert_eq!(credit["batch_kind"], "shielded");
    assert_eq!(credit["transaction_kind"], "orchard_withdraw_v1");
    assert_eq!(credit["tx_role"], "shielded_withdrawal");
    assert_eq!(credit["from"], "orchard-v1");
    assert_eq!(credit["to"], WITHDRAW_RECIPIENT);
    assert_eq!(credit["amount"], WITHDRAW_AMOUNT);
    assert_eq!(credit["block_height"], 2);
    assert!(credit.get("asset_id").is_none(), "native PFT credit");
    assert_eq!(credit["accepted"], true);
    assert_eq!(withdraw_tx["transaction_rows"][0], *credit);

    let status = child.wait().expect("wait for RPC server");
    assert!(status.success(), "RPC server failed with {status}");
    fs::remove_dir_all(root).expect("remove RPC test directory");
}
