//! Built-binary coverage for the `market_ops_status` CLI wiring.
use std::fs;
use std::path::PathBuf;
use std::process::Command;

fn bin() -> Command {
    Command::new(env!("CARGO_BIN_EXE_postfiat-rpc-sdk"))
}

fn temp_path(name: &str) -> PathBuf {
    let mut path = std::env::temp_dir();
    path.push(format!(
        "postfiat-rpc-sdk-market-ops-status-{}-{name}",
        std::process::id()
    ));
    path
}

fn read_request(path: &PathBuf) -> serde_json::Value {
    serde_json::from_str(&fs::read_to_string(path).expect("read request")).expect("parse request")
}

#[test]
fn request_subcommand_builds_market_ops_status_request_without_epoch() {
    let output_path = temp_path("latest.json");
    let asset_id = "ab".repeat(48);
    let output = bin()
        .args([
            "request",
            "--method",
            "market_ops_status",
            "--id",
            "market-ops-status-cli-1",
            "--asset-id",
            asset_id.as_str(),
            "--output",
        ])
        .arg(&output_path)
        .output()
        .expect("run request");
    assert!(
        output.status.success(),
        "request failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let written = read_request(&output_path);
    assert_eq!(written["method"], "market_ops_status");
    assert_eq!(written["id"], "market-ops-status-cli-1");
    assert_eq!(written["params"]["asset_id"], asset_id);
    assert!(written["params"].get("epoch").is_none());
    let _ = fs::remove_file(&output_path);
}

#[test]
fn request_subcommand_builds_market_ops_status_request_with_epoch() {
    let output_path = temp_path("epoch.json");
    let asset_id = "ab".repeat(48);
    let output = bin()
        .args([
            "request",
            "--method",
            "market_ops_status",
            "--id",
            "market-ops-status-cli-2",
            "--asset-id",
            asset_id.as_str(),
            "--epoch",
            "7",
            "--output",
        ])
        .arg(&output_path)
        .output()
        .expect("run request");
    assert!(
        output.status.success(),
        "request failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let written = read_request(&output_path);
    assert_eq!(written["params"]["epoch"], 7);
    let _ = fs::remove_file(&output_path);
}

#[test]
fn request_subcommand_requires_asset_id() {
    let output_path = temp_path("missing.json");
    let output = bin()
        .args([
            "request",
            "--method",
            "market_ops_status",
            "--id",
            "market-ops-status-cli-3",
            "--output",
        ])
        .arg(&output_path)
        .output()
        .expect("run request");
    assert!(!output.status.success());
    assert!(
        String::from_utf8_lossy(&output.stderr).contains("missing --asset-id"),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(!output_path.exists());
}

#[test]
fn help_lists_market_ops_status() {
    let output = bin().arg("help").output().expect("run help");
    let text = format!(
        "{}{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(text.contains("market_ops_status"), "help text: {text}");
    assert!(text.contains("Market_ops_status request supports --asset-id"));
}

fn report(asset_id: &str, epoch: u64) -> serde_json::Value {
    serde_json::json!({
        "schema": "postfiat-market-ops-public-status-v1",
        "asset_id": asset_id,
        "nav_floor_usd_e8": 100_000_000_u64,
        "verified_net_assets_usd_e8": 5_000_000_000_000_u64,
        "valid_global_supply_atoms": 50_000_000_000_u64,
        "reserve_packet_fresh": true,
        "supply_packet_fresh": true,
        "reserve_packet_age_blocks": 12,
        "supply_packet_age_blocks": 4,
        "funded_alignment_reserve_usd_e8": 250_000_000_000_u64,
        "required_alignment_reserve_usd_e8": 200_000_000_000_u64,
        "current_reserve_deploy_cap_usd_e8": 10_000_000_000_u64,
        "current_mint_cap_atoms": 1_000_000_000_u64,
        "market_operations_status": "active",
        "accepted_policy_hash": "cd".repeat(32),
        "envelope_hash": "ef".repeat(48),
        "envelope_epoch": epoch,
        "packet_expires_at": 1_800_000_000_u64,
        "disclosure": "The protocol proves NAV and may execute bounded market operations under public caps. Holders do not have a standing right to redeem at NAV, and market operations can pause."
    })
}

/// Builds the request with the CLI itself, writes `result` as the response
/// under the same id, and runs `validate-response` with `--request-file`.
fn validate_bound(
    tag: &str,
    request_asset_id: &str,
    request_epoch: Option<&str>,
    result: &serde_json::Value,
) -> std::process::Output {
    let request_path = temp_path(&format!("{tag}-request.json"));
    let response_path = temp_path(&format!("{tag}-response.json"));
    let mut request = bin();
    request.args([
        "request",
        "--method",
        "market_ops_status",
        "--id",
        "market-review-1",
        "--asset-id",
        request_asset_id,
    ]);
    if let Some(epoch) = request_epoch {
        request.args(["--epoch", epoch]);
    }
    let built = request
        .arg("--output")
        .arg(&request_path)
        .output()
        .expect("run request");
    assert!(built.status.success(), "request failed: {built:?}");
    let response = postfiat_rpc_sdk::success_response("market-review-1", result, vec![])
        .expect("build response");
    postfiat_rpc_sdk::write_response_file(&response_path, &response).expect("write response");
    let output = bin()
        .args(["validate-response", "--input"])
        .arg(&response_path)
        .args([
            "--expect-kind",
            "market_ops_status",
            "--expect-id",
            "market-review-1",
            "--require-ok",
            "--request-file",
        ])
        .arg(&request_path)
        .output()
        .expect("run validate-response");
    let _ = fs::remove_file(&request_path);
    let _ = fs::remove_file(&response_path);
    output
}

fn validate_unbound(tag: &str, result: &serde_json::Value) -> std::process::Output {
    let response_path = temp_path(&format!("{tag}-response.json"));
    let response = postfiat_rpc_sdk::success_response("market-review-1", result, vec![])
        .expect("build response");
    postfiat_rpc_sdk::write_response_file(&response_path, &response).expect("write response");
    let output = bin()
        .args(["validate-response", "--input"])
        .arg(&response_path)
        .args(["--expect-kind", "market_ops_status", "--require-ok"])
        .output()
        .expect("run validate-response");
    let _ = fs::remove_file(&response_path);
    output
}

fn assert_rejected(output: &std::process::Output, field: &str) {
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        !output.status.success(),
        "expected rejection, stdout: {}",
        String::from_utf8_lossy(&output.stdout)
    );
    assert!(stderr.contains(&format!("`{field}`")), "stderr: {stderr}");
}

#[test]
fn validate_response_binds_market_ops_status_to_request_asset_and_epoch() {
    let requested = "aa".repeat(48);
    let other = "ab".repeat(48);
    // Reviewer repro: request aa*48 / epoch 8, response ab*48 / envelope_epoch 7.
    let output = validate_bound("review", &requested, Some("8"), &report(&other, 7));
    assert_rejected(&output, "asset_id");
    let output = validate_bound("asset", &requested, Some("7"), &report(&other, 7));
    assert_rejected(&output, "asset_id");
    let output = validate_bound("asset-latest", &requested, None, &report(&other, 7));
    assert_rejected(&output, "asset_id");
    let output = validate_bound("epoch", &other, Some("8"), &report(&other, 7));
    assert_rejected(&output, "envelope_epoch");
}

#[test]
fn validate_response_accepts_market_ops_status_bound_to_its_request() {
    let asset_id = "ab".repeat(48);
    let output = validate_bound("match", &asset_id, Some("7"), &report(&asset_id, 7));
    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    // Omitted epoch selects the latest finalized envelope, whatever its epoch.
    let output = validate_bound("latest", &asset_id, None, &report(&asset_id, 9));
    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
}

#[test]
fn validate_response_rejects_contradictory_active_market_ops_status() {
    let asset_id = "ab".repeat(48);
    let control = validate_unbound("control", &report(&asset_id, 7));
    assert!(
        control.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&control.stderr)
    );
    for (field, value) in [
        ("reserve_packet_fresh", serde_json::json!(false)),
        ("supply_packet_fresh", serde_json::json!(false)),
        ("funded_alignment_reserve_usd_e8", serde_json::json!(0)),
    ] {
        let mut result = report(&asset_id, 7);
        result[field] = value;
        let output = validate_unbound(field, &result);
        assert_rejected(&output, field);
        let output = validate_bound(&format!("{field}-bound"), &asset_id, Some("7"), &result);
        assert_rejected(&output, field);
    }
}
