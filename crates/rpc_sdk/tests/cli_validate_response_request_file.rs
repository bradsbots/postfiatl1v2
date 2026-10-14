//! Built-binary coverage for `validate-response --request-file` binding on
//! every response kind, not only the request-bound atomic-swap kinds.
use std::fs;
use std::path::PathBuf;
use std::process::{Command, Output};

use postfiat_rpc_sdk::{status_request, success_response, write_request_file, write_response_file};
use serde_json::{json, Value};

fn bin() -> Command {
    Command::new(env!("CARGO_BIN_EXE_postfiat-rpc-sdk"))
}

fn temp_path(name: &str) -> PathBuf {
    let mut path = std::env::temp_dir();
    path.push(format!(
        "postfiat-rpc-sdk-validate-response-request-file-{}-{name}",
        std::process::id()
    ));
    path
}

fn status_result() -> Value {
    json!({
        "chain_id": "rpc-sdk-cli-tests",
        "genesis_hash": "11".repeat(48),
        "protocol_version": 1,
        "validator_count": 6,
        "node_id": "node-0",
        "status": "running",
        "last_run_unix": 1,
        "state_root": "22".repeat(48),
        "block_height": 0,
        "block_tip_hash": "genesis",
        "mempool_pending": 0
    })
}

struct Fixture {
    response_path: PathBuf,
    request_path: PathBuf,
    other_request_path: PathBuf,
}

impl Fixture {
    fn write(tag: &str, result: &Value) -> Self {
        let fixture = Self {
            response_path: temp_path(&format!("{tag}-response.json")),
            request_path: temp_path(&format!("{tag}-request.json")),
            other_request_path: temp_path(&format!("{tag}-other-request.json")),
        };
        let response = success_response("status-1", result, vec![]).expect("build response");
        write_response_file(&fixture.response_path, &response).expect("write response");
        write_request_file(&fixture.request_path, &status_request("status-1"))
            .expect("write request");
        write_request_file(&fixture.other_request_path, &status_request("status-2"))
            .expect("write other request");
        fixture
    }

    fn validate(&self, extra: &[&str]) -> Output {
        bin()
            .args(["validate-response", "--input"])
            .arg(&self.response_path)
            .args(extra)
            .output()
            .expect("run validate-response")
    }
}

impl Drop for Fixture {
    fn drop(&mut self) {
        for path in [
            &self.response_path,
            &self.request_path,
            &self.other_request_path,
        ] {
            let _ = fs::remove_file(path);
        }
    }
}

fn stderr(output: &Output) -> String {
    String::from_utf8_lossy(&output.stderr).into_owned()
}

#[test]
fn request_file_with_matching_id_passes_and_agrees_with_expect_kind() {
    let fixture = Fixture::write("matching", &status_result());
    let request = fixture.request_path.display().to_string();
    let output = fixture.validate(&["--request-file", &request]);
    assert!(output.status.success(), "stderr: {}", stderr(&output));
    assert!(String::from_utf8_lossy(&output.stdout).contains("rpc_response=ok id=status-1"));
    let output = fixture.validate(&["--expect-kind", "status", "--request-file", &request]);
    assert!(output.status.success(), "stderr: {}", stderr(&output));
    let output = fixture.validate(&["--expect-id", "status-1", "--request-file", &request]);
    assert!(output.status.success(), "stderr: {}", stderr(&output));
}

#[test]
fn request_file_rejects_a_response_for_another_request_id() {
    let fixture = Fixture::write("other-id", &status_result());
    let other = fixture.other_request_path.display().to_string();
    let output = fixture.validate(&["--request-file", &other]);
    assert!(!output.status.success());
    assert!(
        stderr(&output).contains("rpc response id `status-1` did not match expected `status-2`"),
        "stderr: {}",
        stderr(&output)
    );
}

#[test]
fn expect_id_conflicting_with_request_file_is_rejected() {
    let fixture = Fixture::write("conflict", &status_result());
    let request = fixture.request_path.display().to_string();
    let output = fixture.validate(&["--expect-id", "status-2", "--request-file", &request]);
    assert!(!output.status.success());
    assert!(
        stderr(&output).contains(
            "--expect-id `status-2` conflicts with request id `status-1` in --request-file"
        ),
        "stderr: {}",
        stderr(&output)
    );
}

#[test]
fn request_file_derives_the_expected_kind_from_the_request_method() {
    // Not a status result: without a kind nothing inspects it, with the
    // request file the status validator runs and names the missing field.
    let fixture = Fixture::write("derived", &json!({ "schema": "not-a-status-result" }));
    let output = fixture.validate(&[]);
    assert!(output.status.success(), "stderr: {}", stderr(&output));
    let request = fixture.request_path.display().to_string();
    let output = fixture.validate(&["--request-file", &request]);
    assert!(!output.status.success());
    assert!(
        stderr(&output).contains("chain_id"),
        "stderr: {}",
        stderr(&output)
    );
}

#[test]
fn expect_kind_must_match_the_request_method() {
    let fixture = Fixture::write("kind-mismatch", &status_result());
    let request = fixture.request_path.display().to_string();
    let output = fixture.validate(&["--expect-kind", "tx", "--request-file", &request]);
    assert!(!output.status.success());
    assert!(
        stderr(&output)
            .contains("--expect-kind does not match request method `status` in --request-file"),
        "stderr: {}",
        stderr(&output)
    );
}

#[test]
fn help_describes_request_file_binding() {
    let output = bin().arg("help").output().expect("run help");
    let text = format!(
        "{}{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        text.contains("Any validate-response call given --request-file is bound to that request"),
        "help text: {text}"
    );
}

/// The atomic-swap and owned-certificate branches must validate the payload
/// against the same parsed request that bound the id and kind. The request file is a FIFO that yields
/// its content to exactly one reader, so a second read would block forever.
#[cfg(unix)]
#[test]
fn request_bound_kinds_read_the_request_file_once() {
    use std::io::Write;
    use std::time::{Duration, Instant};

    for method in [
        "atomic_swap_fee_quote",
        "mempool_submit_signed_atomic_swap_transaction",
        "mempool_submit_signed_atomic_swap_transaction_finality",
        "owned_certificate",
    ] {
        let fifo = temp_path(&format!("{method}-request.fifo"));
        let response_path = temp_path(&format!("{method}-response.json"));
        let _ = fs::remove_file(&fifo);
        let made = Command::new("mkfifo")
            .arg(&fifo)
            .status()
            .expect("run mkfifo");
        assert!(made.success(), "mkfifo failed");
        let response = success_response("swap-1", &json!({}), vec![]).expect("build response");
        write_response_file(&response_path, &response).expect("write response");

        let request = format!(
            "{{\"version\": \"postfiat-local-rpc-v1\", \"id\": \"swap-1\", \"method\": \"{method}\", \"params\": {{}}}}"
        );
        let writer_path = fifo.clone();
        let writer = std::thread::spawn(move || {
            let mut pipe = fs::OpenOptions::new()
                .write(true)
                .open(&writer_path)
                .expect("open fifo for writing");
            pipe.write_all(request.as_bytes()).expect("write request");
        });

        let mut child = bin()
            .args([
                "validate-response",
                "--input",
                &response_path.to_string_lossy(),
                "--request-file",
                &fifo.to_string_lossy(),
            ])
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::piped())
            .spawn()
            .expect("spawn postfiat-rpc-sdk");
        let started = Instant::now();
        let finished = loop {
            if child.try_wait().expect("poll child").is_some() {
                break true;
            }
            if started.elapsed() > Duration::from_secs(20) {
                child.kill().expect("kill blocked child");
                break false;
            }
            std::thread::sleep(Duration::from_millis(20));
        };
        let output = child.wait_with_output().expect("collect child output");
        writer.join().expect("fifo writer");
        let _ = fs::remove_file(&fifo);
        let _ = fs::remove_file(&response_path);

        assert!(
            finished,
            "{method}: validate-response read --request-file twice"
        );
        // The empty result is rejected by the payload check, which proves the
        // branch ran against the single parsed request.
        let stderr = String::from_utf8_lossy(&output.stderr);
        assert!(
            stderr.contains("response validation failed at"),
            "{method}: {stderr}"
        );
    }
}
