//! The help text and the three "unsupported ..." errors must agree with the
//! methods the binary actually builds and validates.
//!
//! The `request` builder accepts every method in "Supported request methods"
//! and "FastSwap methods". `validate-request --expect-kind` and
//! `validate-response --expect-kind` accept the methods in "Supported request
//! kinds" and "Supported response kinds": the builder list minus the
//! builder-only methods, which have no request or response kind.

use std::collections::BTreeSet;
use std::process::{Command, Output};

/// Methods the request builder accepts but neither kind parser maps.
const BUILDER_ONLY: &[&str] = &["mempool_submit_fastlane_primary_finality"];

fn run(args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_postfiat-rpc-sdk"))
        .args(args)
        .output()
        .expect("run postfiat-rpc-sdk")
}

fn stderr(output: &Output) -> String {
    String::from_utf8_lossy(&output.stderr).into_owned()
}

fn help() -> String {
    stderr(&run(&["help"]))
}

/// The comma-separated names on the help line that starts with `prefix`.
fn help_list(help: &str, prefix: &str) -> Vec<String> {
    let line = help
        .lines()
        .find(|line| line.starts_with(prefix))
        .unwrap_or_else(|| panic!("help text lacks `{prefix}`"));
    line[prefix.len()..]
        .trim_end_matches('.')
        .split(", ")
        .map(str::to_string)
        .collect()
}

/// Every method the help advertises for the request builder.
fn advertised_builder_methods(help: &str) -> Vec<String> {
    let mut methods = help_list(help, "Supported request methods: ");
    methods.extend(help_list(help, "FastSwap methods: "));
    methods
}

/// The names after `; supported: ` in the error line that starts with `prefix`.
fn error_list(text: &str, prefix: &str) -> Vec<String> {
    let line = text
        .lines()
        .find(|line| line.starts_with(prefix))
        .unwrap_or_else(|| panic!("expected an error starting `{prefix}`: {text}"));
    line.split_once("; supported: ")
        .unwrap_or_else(|| panic!("error has no supported list: {line}"))
        .1
        .split(", ")
        .map(str::to_string)
        .collect()
}

/// The set of `names`, asserting the list has no duplicates.
fn unique(names: &[String]) -> BTreeSet<&str> {
    let set = names.iter().map(String::as_str).collect::<BTreeSet<_>>();
    assert_eq!(set.len(), names.len(), "duplicate names in {names:?}");
    set
}

/// The `supported:` list of the unknown-kind error of `subcommand`.
fn unknown_kind_error_list(subcommand: &str) -> Vec<String> {
    let output = run(&[
        subcommand,
        "--input",
        "unused-input.json",
        "--expect-kind",
        "definitely_not_a_kind",
    ]);
    assert!(
        !output.status.success(),
        "{subcommand} accepted a bogus kind"
    );
    let prefix = match subcommand {
        "validate-request" => "error: unsupported request kind `definitely_not_a_kind`",
        _ => "error: unsupported response kind `definitely_not_a_kind`",
    };
    error_list(&stderr(&output), prefix)
}

#[test]
fn every_advertised_method_has_a_request_builder() {
    let help = help();
    let methods = advertised_builder_methods(&help);
    unique(&methods);
    for method in &methods {
        let output = run(&[
            "request", "--method", method, "--id", "t-1", "--output", "-",
        ]);
        let text = stderr(&output);
        assert!(
            !text.contains("unsupported request builder method"),
            "`{method}` is advertised in help but the builder rejects it: {text}"
        );
    }
}

#[test]
fn unknown_method_error_lists_exactly_the_advertised_builder_methods() {
    let output = run(&[
        "request",
        "--method",
        "definitely_not_a_method",
        "--id",
        "t-1",
        "--output",
        "-",
    ]);
    assert!(!output.status.success());
    let listed = error_list(
        &stderr(&output),
        "error: unsupported request builder method `definitely_not_a_method`",
    );
    let help = help();
    let advertised = advertised_builder_methods(&help);
    assert_eq!(unique(&listed), unique(&advertised));
}

/// Maintainer regression for #79: every method an unknown-kind error lists as
/// supported must be accepted by that same subcommand's `--expect-kind`.
/// The input file does not exist, so an accepted kind fails later, at the
/// file read, and never with "unsupported ... kind".
#[test]
fn every_kind_listed_as_supported_is_accepted_by_expect_kind() {
    let missing = std::env::temp_dir()
        .join(format!("postfiat-rpc-sdk-kinds-{}", std::process::id()))
        .join("missing.json");
    assert!(!missing.exists());
    let input = missing.to_string_lossy().into_owned();
    for (subcommand, rejection) in [
        ("validate-request", "unsupported request kind"),
        ("validate-response", "unsupported response kind"),
    ] {
        let listed = unknown_kind_error_list(subcommand);
        unique(&listed);
        let rejected = listed
            .iter()
            .filter(|kind| {
                let output = run(&[subcommand, "--input", &input, "--expect-kind", kind]);
                assert!(!output.status.success(), "{subcommand} {kind}");
                stderr(&output).contains(rejection)
            })
            .collect::<Vec<_>>();
        assert!(
            rejected.is_empty(),
            "{subcommand}: listed as supported but rejected by --expect-kind: {rejected:?}"
        );
    }
}

#[test]
fn kind_lists_in_help_and_errors_are_the_builder_list_minus_builder_only() {
    let help = help();
    let builder = advertised_builder_methods(&help);
    let expected = unique(&builder)
        .into_iter()
        .filter(|method| !BUILDER_ONLY.contains(method))
        .collect::<BTreeSet<_>>();
    for (subcommand, help_prefix) in [
        ("validate-request", "Supported request kinds: "),
        ("validate-response", "Supported response kinds: "),
    ] {
        let advertised = help_list(&help, help_prefix);
        assert_eq!(unique(&advertised), expected, "help `{help_prefix}`");
        let listed = unknown_kind_error_list(subcommand);
        assert_eq!(unique(&listed), expected, "{subcommand} error list");
    }
}

#[test]
fn builder_only_methods_build_but_are_not_kinds() {
    for method in BUILDER_ONLY {
        let output = run(&[
            "request",
            "--method",
            method,
            "--id",
            "builder-only-1",
            "--fastlane-primary-json",
            "{}",
            "--output",
            "-",
        ]);
        assert!(output.status.success(), "{method}: {}", stderr(&output));
        let request: serde_json::Value =
            serde_json::from_slice(&output.stdout).expect("request JSON on stdout");
        assert_eq!(request["method"], *method);
        for (subcommand, rejection) in [
            ("validate-request", "error: unsupported request kind"),
            ("validate-response", "error: unsupported response kind"),
        ] {
            let output = run(&[
                subcommand,
                "--input",
                "unused-input.json",
                "--expect-kind",
                method,
            ]);
            let text = stderr(&output);
            assert!(!output.status.success(), "{subcommand} {method}");
            let listed = error_list(&text, rejection);
            assert!(
                !listed.iter().any(|name| name == method),
                "{subcommand}: `{method}` is rejected yet listed as supported: {text}"
            );
        }
    }
}

#[test]
fn methods_and_help_lines_from_later_prs_are_kept() {
    let help = help();
    let builder = advertised_builder_methods(&help);
    let builder = unique(&builder);
    for method in [
        "verify_blocks",
        "verify_bridge",
        "verify_mempool",
        "verify_shielded",
        "account_tx_index_status",
    ] {
        assert!(builder.contains(method), "help omits `{method}`");
    }
    for sentence in [
        "The request subcommand validates the built request (id, method, params) with the same rules as validate-request --expect-kind before writing it",
        "validate-request checks the params rules for the file's own method; --expect-kind additionally asserts the method",
    ] {
        assert!(help.contains(sentence), "help omits: {sentence}");
    }
}
