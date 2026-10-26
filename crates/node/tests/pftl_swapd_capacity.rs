use std::fs;
use std::io::{BufRead, BufReader, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use postfiat_node::{init, InitOptions};

/// Kills the daemon and removes the temp root even when an assertion fails.
struct Fixture {
    root: PathBuf,
    daemon: Option<Child>,
}

impl Drop for Fixture {
    fn drop(&mut self) {
        if let Some(mut daemon) = self.daemon.take() {
            let _ = daemon.kill();
            let _ = daemon.wait();
        }
        let _ = fs::remove_dir_all(&self.root);
    }
}

fn free_loopback_port() -> u16 {
    TcpListener::bind("127.0.0.1:0")
        .expect("bind probe listener")
        .local_addr()
        .expect("probe address")
        .port()
}

/// A client that closes before pftl-swapd answers "connection capacity
/// exhausted" must not stop the daemon: the refusal is best effort, as in
/// asset-orchard-local-service.
#[test]
fn swapd_survives_a_client_that_closes_before_the_capacity_refusal() {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock")
        .as_nanos();
    let mut fixture = Fixture {
        root: std::env::temp_dir().join(format!(
            "postfiat-swapd-capacity-{}-{nanos}",
            std::process::id()
        )),
        daemon: None,
    };
    let root = fixture.root.clone();
    let data_dir = root.join("data");
    init(InitOptions {
        data_dir: data_dir.clone(),
        chain_id: "postfiat-local".to_string(),
        node_id: "swapd-capacity-test".to_string(),
        validator_count: 1,
    })
    .expect("init node data dir");
    // Startup only checks the transparent key file's mode; no key is needed.
    let key_file = root.join("transparent-key.json");
    fs::write(&key_file, b"{}\n").expect("write placeholder key file");
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(&key_file, fs::Permissions::from_mode(0o600)).expect("chmod key");
    }
    let bind = format!("127.0.0.1:{}", free_loopback_port());
    let path = |name: &str| root.join(name).to_str().expect("utf-8 path").to_string();
    let daemon = fixture.daemon.insert(
        Command::new(env!("CARGO_BIN_EXE_pftl_swapd"))
            .args(["--data-dir", data_dir.to_str().expect("utf-8 path")])
            .args(["--private-dir", &path("private")])
            .args(["--round-driver-ready-file", &path("ready.json")])
            .args([
                "--transparent-key-file",
                key_file.to_str().expect("utf-8 path"),
            ])
            .args(["--bind", &bind])
            .args(["--asset-service-vault-dir", &path("vault")])
            .args([
                "--issue-ethereum-recipient",
                &format!("0x{}", "11".repeat(20)),
            ])
            .args(["--egress-policy-id", "test-policy"])
            .args(["--route-id", "test-route"])
            .args(["--controlled-wallet-id", "test-wallet"])
            .args(["--max-connections", "1"])
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .expect("spawn pftl_swapd"),
    );
    let mut start = String::new();
    BufReader::new(daemon.stdout.take().expect("stdout"))
        .read_line(&mut start)
        .expect("read start line");
    assert!(
        start.contains("daemon_start"),
        "daemon did not start: {start}"
    );

    // Take the only connection slot and keep it idle.
    let holder = TcpStream::connect(&bind).expect("connect holder");
    thread::sleep(Duration::from_millis(200));
    // Connect and close at once, before the daemon writes its 503.
    drop(TcpStream::connect(&bind).expect("connect closing client"));
    thread::sleep(Duration::from_millis(300));

    let exited = daemon.try_wait().expect("poll daemon");
    let mut stderr = String::new();
    if exited.is_some() {
        daemon
            .stderr
            .take()
            .expect("stderr")
            .read_to_string(&mut stderr)
            .expect("read stderr");
    }
    assert!(
        exited.is_none(),
        "pftl_swapd exited ({exited:?}) after a client closed at capacity: {stderr}"
    );

    // The daemon still serves once the slot is free.
    drop(holder);
    let deadline = Instant::now() + Duration::from_secs(5);
    let status_line = loop {
        let mut client = TcpStream::connect(&bind).expect("connect after capacity");
        client
            .write_all(b"GET /v1/unknown HTTP/1.1\r\nHost: localhost\r\n\r\n")
            .expect("write request");
        let mut response = String::new();
        let _ = client.read_to_string(&mut response);
        if !response.contains("connection_capacity_exhausted") || Instant::now() > deadline {
            break response.lines().next().unwrap_or_default().to_string();
        }
        thread::sleep(Duration::from_millis(50));
    };
    assert_eq!(status_line, "HTTP/1.1 404 Not Found");
}
