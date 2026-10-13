//! Built-binary coverage for the `owned_recovery_status` CLI wiring.
use std::fs;
use std::path::PathBuf;
use std::process::Command;

fn bin() -> Command {
    Command::new(env!("CARGO_BIN_EXE_postfiat-rpc-sdk"))
}

fn temp_path(name: &str) -> PathBuf {
    let mut path = std::env::temp_dir();
    path.push(format!(
        "postfiat-rpc-sdk-owned-recovery-status-{}-{name}",
        std::process::id()
    ));
    path
}

#[test]
fn request_subcommand_builds_owned_recovery_status_request() {
    let output_path = temp_path("request.json");
    let lock_id = "ab".repeat(48);
    let output = bin()
        .args([
            "request",
            "--method",
            "owned_recovery_status",
            "--id",
            "owned-recovery-status-cli-1",
            "--lock-id",
            lock_id.as_str(),
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
    let written: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(&output_path).expect("read request"))
            .expect("parse request");
    assert_eq!(written["method"], "owned_recovery_status");
    assert_eq!(written["id"], "owned-recovery-status-cli-1");
    assert_eq!(written["params"]["lock_id"], lock_id);
    let _ = fs::remove_file(&output_path);
}

#[test]
fn request_subcommand_requires_lock_id() {
    let output_path = temp_path("missing.json");
    let output = bin()
        .args([
            "request",
            "--method",
            "owned_recovery_status",
            "--id",
            "owned-recovery-status-cli-2",
            "--output",
        ])
        .arg(&output_path)
        .output()
        .expect("run request");
    assert!(!output.status.success());
    assert!(
        String::from_utf8_lossy(&output.stderr).contains("missing --lock-id"),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(!output_path.exists());
}

#[test]
fn help_lists_owned_recovery_status() {
    let output = bin().arg("help").output().expect("run help");
    let text = format!(
        "{}{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(text.contains("owned_recovery_status"), "help text: {text}");
    assert!(text.contains("Owned_recovery_status request supports --lock-id"));
}

fn write_json(path: &PathBuf, value: &serde_json::Value) {
    fs::write(path, serde_json::to_vec(value).expect("encode")).expect("write json");
}

fn status_request_file(name: &str, method: &str, lock_id: &str) -> PathBuf {
    let path = temp_path(name);
    write_json(
        &path,
        &serde_json::json!({
            "version": "postfiat-local-rpc-v1",
            "id": "owned-recovery-status-bind",
            "method": method,
            "params": {"lock_id": lock_id}
        }),
    );
    path
}

fn validate_status_response(response: &PathBuf, request: Option<&PathBuf>) -> std::process::Output {
    let mut command = bin();
    command
        .args(["validate-response", "--input"])
        .arg(response)
        .args(["--expect-kind", "owned_recovery_status"]);
    if let Some(request) = request {
        command.arg("--request-file").arg(request);
    }
    command.output().expect("run validate-response")
}

#[test]
fn validate_response_binds_owned_recovery_status_to_requested_lock() {
    let lock_a = "aa".repeat(48);
    let lock_b = "bb".repeat(48);
    let response = temp_path("bind-response.json");
    write_json(
        &response,
        &serde_json::json!({
            "version": "postfiat-local-rpc-v1",
            "id": "owned-recovery-status-bind",
            "ok": true,
            "result": {
                "schema": "postfiat-fastpay-recovery-status-v1",
                "lock_id": lock_a,
                "status": "open_or_unknown",
                "reveal_count": 0,
                "fence": null
            },
            "error": null,
            "events": []
        }),
    );
    let request_a = status_request_file("bind-request-a.json", "owned_recovery_status", &lock_a);
    let request_b = status_request_file("bind-request-b.json", "owned_recovery_status", &lock_b);

    let output = validate_status_response(&response, Some(&request_a));
    assert!(
        output.status.success(),
        "lock A request must pass: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let output = validate_status_response(&response, Some(&request_b));
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(!output.status.success(), "lock B request must fail");
    assert!(stderr.contains("lock_id"), "stderr: {stderr}");

    let output = validate_status_response(&response, None);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(!output.status.success(), "unbound validation must fail");
    assert!(
        stderr.contains("owned_recovery_status response validation requires --request-file"),
        "stderr: {stderr}"
    );
    for path in [&response, &request_a, &request_b] {
        let _ = fs::remove_file(path);
    }
}
