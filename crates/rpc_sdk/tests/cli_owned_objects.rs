//! Built-binary coverage for the `owned_objects` CLI wiring.
use std::fs;
use std::path::PathBuf;
use std::process::Command;

fn bin() -> Command {
    Command::new(env!("CARGO_BIN_EXE_postfiat-rpc-sdk"))
}

fn temp_path(name: &str) -> PathBuf {
    let mut path = std::env::temp_dir();
    path.push(format!(
        "postfiat-rpc-sdk-owned-objects-{}-{name}",
        std::process::id()
    ));
    path
}

fn read_request(path: &PathBuf) -> serde_json::Value {
    serde_json::from_str(&fs::read_to_string(path).expect("read request")).expect("parse request")
}

#[test]
fn request_subcommand_builds_owned_objects_request_without_optional_flags() {
    let output_path = temp_path("plain.json");
    let owner = "ab".repeat(1952);
    let output = bin()
        .args([
            "request",
            "--method",
            "owned_objects",
            "--id",
            "owned-objects-cli-1",
            "--owner-public-key-hex",
            owner.as_str(),
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
    assert_eq!(written["method"], "owned_objects");
    assert_eq!(written["id"], "owned-objects-cli-1");
    assert_eq!(written["params"]["owner_public_key_hex"], owner);
    assert!(written["params"].get("asset").is_none());
    assert!(written["params"].get("limit").is_none());
    let _ = fs::remove_file(&output_path);
}

#[test]
fn request_subcommand_builds_owned_objects_request_with_optional_flags() {
    let output_path = temp_path("filtered.json");
    let owner = "ab".repeat(1952);
    let output = bin()
        .args([
            "request",
            "--method",
            "owned_objects",
            "--id",
            "owned-objects-cli-2",
            "--owner-public-key-hex",
            owner.as_str(),
            "--asset",
            "USDX",
            "--limit",
            "25",
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
    assert_eq!(written["params"]["asset"], "USDX");
    assert_eq!(written["params"]["limit"], 25);
    let _ = fs::remove_file(&output_path);
}

#[test]
fn request_subcommand_requires_owner_public_key_hex() {
    let output_path = temp_path("missing.json");
    let output = bin()
        .args([
            "request",
            "--method",
            "owned_objects",
            "--id",
            "owned-objects-cli-3",
            "--output",
        ])
        .arg(&output_path)
        .output()
        .expect("run request");
    assert!(!output.status.success());
    assert!(
        String::from_utf8_lossy(&output.stderr).contains("missing --owner-public-key-hex"),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(!output_path.exists());
}

#[test]
fn help_lists_owned_objects() {
    let output = bin().arg("help").output().expect("run help");
    let text = format!(
        "{}{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(text.contains("owned_objects"), "help text: {text}");
    assert!(text.contains("Owned_objects request supports --owner-public-key-hex"));
}

/// A complete, internally consistent `owned_objects` response for owner
/// `owner`, no asset filter, node default limit 2048.
fn owned_objects_response(id: &str, owner: &str) -> serde_json::Value {
    serde_json::json!({
        "version": "postfiat-local-rpc-v1",
        "id": id,
        "ok": true,
        "result": {
            "schema": "postfiat-owned-objects-v1",
            "chain_id": "postfiat-testnet",
            "genesis_hash": "cd".repeat(48),
            "protocol_version": 3,
            "owner_public_key_hex": owner,
            "asset": null,
            "limit": 2048,
            "truncated": false,
            "object_count": 1,
            "total_value": 100,
            "objects": [{
                "id": "01".repeat(32),
                "version": 1,
                "owner_pubkey_hex": owner,
                "value": 100,
                "asset": "PFT"
            }]
        },
        "error": null,
        "events": []
    })
}

fn write_json(path: &PathBuf, value: &serde_json::Value) {
    fs::write(path, serde_json::to_vec(value).expect("encode")).expect("write json");
}

fn owned_objects_request_file(name: &str, params: serde_json::Value) -> PathBuf {
    let path = temp_path(name);
    write_json(
        &path,
        &serde_json::json!({
            "version": "postfiat-local-rpc-v1",
            "id": "owned-objects-bind",
            "method": "owned_objects",
            "params": params
        }),
    );
    path
}

fn validate_response_with(response: &PathBuf, request: Option<&PathBuf>) -> std::process::Output {
    let mut command = bin();
    command
        .args(["validate-response", "--input"])
        .arg(response)
        .args(["--expect-kind", "owned_objects"]);
    if let Some(request) = request {
        command.arg("--request-file").arg(request);
    }
    command.output().expect("run validate-response")
}

#[test]
fn validate_response_binds_owned_objects_to_request_file() {
    let owner_a = "ab".repeat(1952);
    let owner_b = "cd".repeat(1952);
    let response = temp_path("bind-response.json");
    write_json(
        &response,
        &owned_objects_response("owned-objects-bind", &owner_a),
    );

    let request_a = owned_objects_request_file(
        "bind-request-a.json",
        serde_json::json!({"owner_public_key_hex": owner_a}),
    );
    let output = validate_response_with(&response, Some(&request_a));
    assert!(
        output.status.success(),
        "matching request must pass: {}",
        String::from_utf8_lossy(&output.stderr)
    );

    let mismatches = [
        (
            "bind-request-owner.json",
            serde_json::json!({"owner_public_key_hex": owner_b}),
            "owner_public_key_hex",
        ),
        (
            "bind-request-asset.json",
            serde_json::json!({"owner_public_key_hex": owner_a, "asset": "PFT"}),
            "asset",
        ),
        (
            "bind-request-limit.json",
            serde_json::json!({"owner_public_key_hex": owner_a, "limit": 25}),
            "limit",
        ),
    ];
    for (name, params, field) in mismatches {
        let request = owned_objects_request_file(name, params);
        let output = validate_response_with(&response, Some(&request));
        let stderr = String::from_utf8_lossy(&output.stderr);
        assert!(!output.status.success(), "{name} must fail");
        assert!(stderr.contains(field), "{name}: stderr {stderr}");
        let _ = fs::remove_file(&request);
    }
    let _ = fs::remove_file(&request_a);
    let _ = fs::remove_file(&response);
}

#[test]
fn validate_response_requires_request_file_for_owned_objects() {
    let response = temp_path("unbound-response.json");
    write_json(
        &response,
        &owned_objects_response("owned-objects-bind", &"ab".repeat(1952)),
    );
    let output = validate_response_with(&response, None);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(!output.status.success());
    assert!(
        stderr.contains("owned_objects response validation requires --request-file"),
        "stderr: {stderr}"
    );
    let _ = fs::remove_file(&response);
}
