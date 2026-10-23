//! Shared-fixture tests for the strict entry profile module (Z2 step 3).
//!
//! The fixtures under
//! `benchmarks/ai-governance/validator-entry-profile-20261023/fixtures/` hold
//! each case's inputs and expected output. This module must produce the same
//! canonical bytes as that expected output, and the Python mirror
//! (`python/tests/test_validator_entry_profile.py`) checks the same bytes and
//! their SHA-256. Agreement on every case is the convergence proof.

use super::validator_entry_profile::*;
use serde_json::Value;
use std::collections::BTreeMap;
use std::path::PathBuf;

fn fixtures() -> Value {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join(
        "../../benchmarks/ai-governance/validator-entry-profile-20261023/fixtures/cases.json",
    );
    serde_json::from_slice(&std::fs::read(&path).expect("fixtures readable"))
        .expect("fixtures parse")
}

fn cases() -> Vec<Value> {
    fixtures()["cases"].as_array().expect("cases array").clone()
}

fn case(name: &str) -> Value {
    cases()
        .into_iter()
        .find(|case| case["name"] == name)
        .unwrap_or_else(|| panic!("fixture case {name} missing"))
}

/// Sorted-key compact JSON with ASCII escapes: the canonical form of the
/// fixtures' expected outputs, written independently of the module's writer.
fn canonical(value: &Value) -> String {
    match value {
        Value::Null => "null".to_owned(),
        Value::Bool(flag) => flag.to_string(),
        Value::Number(number) => number.to_string(),
        Value::String(text) => {
            let mut out = String::new();
            push_canonical_json_string(&mut out, text);
            out
        }
        Value::Array(items) => format!(
            "[{}]",
            items.iter().map(canonical).collect::<Vec<_>>().join(",")
        ),
        Value::Object(map) => {
            let sorted: BTreeMap<&String, &Value> = map.iter().collect();
            let fields = sorted
                .into_iter()
                .map(|(key, value)| {
                    format!(
                        "{}:{}",
                        canonical(&Value::String(key.clone())),
                        canonical(value)
                    )
                })
                .collect::<Vec<_>>();
            format!("{{{}}}", fields.join(","))
        }
    }
}

fn error_json(error: &EntryProfileError) -> String {
    format!("{{\"error\":\"{}\"}}", error.0)
}

/// Runs one fixture case through the module and returns its canonical bytes.
fn run_case(case: &Value) -> String {
    match case["kind"].as_str() {
        Some("evaluate") => match parse_parameters(&case["parameters"]).and_then(|parameters| {
            parse_operator(&case["operator"]).map(|operator| (parameters, operator))
        }) {
            Ok((parameters, operator)) => evaluate(&parameters, &operator).canonical_json(),
            Err(error) => error_json(&error),
        },
        Some("identity_flag") => {
            let parsed = parse_parameters(&case["parameters"]).and_then(|parameters| {
                parse_strict_input(&case["operator"]).map(|input| (parameters, input))
            });
            match parsed.and_then(|(parameters, input)| {
                parse_model_classification(&case["model_classification"])
                    .map(|model| (parameters, input, model))
            }) {
                Ok((parameters, input, model)) => {
                    let met = meets_strict_profile(&parameters, &input);
                    let flag = identity_flag(model, met);
                    let mut out = String::from("{\"identity_flag\":");
                    push_canonical_json_string(&mut out, flag.as_str());
                    out.push_str(&format!(
                        ",\"meets_strict_profile\":{met},\"validator_id\":"
                    ));
                    push_canonical_json_string(
                        &mut out,
                        case["operator"]["validator_id"].as_str().unwrap_or(""),
                    );
                    out.push('}');
                    out
                }
                Err(error) => error_json(&error),
            }
        }
        Some("resolve_flag_input") => {
            let artifact = match &case["artifact"] {
                Value::Null => None,
                value => Some(value),
            };
            let flag = resolve_flag_input(
                artifact,
                &case["expected_pins"],
                case["validator_id"].as_str().expect("validator id"),
            );
            format!("{{\"flag\":\"{}\"}}", flag.as_str())
        }
        other => panic!("unsupported case kind {other:?}"),
    }
}

#[test]
fn validator_entry_profile_reproduces_every_shared_fixture_byte_for_byte() {
    let all = cases();
    assert_eq!(all.len(), 263);
    let mut mismatches = Vec::new();
    for case in &all {
        let actual = run_case(case);
        let expected = canonical(&case["expected"]);
        if actual != expected {
            mismatches.push(format!("{}: {actual} != {expected}", case["name"]));
        }
    }
    assert!(
        mismatches.is_empty(),
        "{} mismatches, first: {:?}",
        mismatches.len(),
        mismatches.first()
    );
}

#[test]
fn validator_entry_profile_flagged_real_operator_is_eligible_after_four_clean_rounds() {
    let out: Value = serde_json::from_str(&run_case(&case(
        "flagged_real_operator_eligible_after_four_clean_rounds",
    )))
    .unwrap();
    assert_eq!(out["profile"], "strict");
    assert_eq!(out["seat"], "may_take_new_seat");
    assert_eq!(out["clean_rounds"], 4);
}

#[test]
fn validator_entry_profile_flag_only_withholds_a_new_seat() {
    let out: Value = serde_json::from_str(&run_case(&case(
        "flagged_entrant_withheld_before_the_strict_profile",
    )))
    .unwrap();
    assert_eq!(out["seat"], "new_seat_withheld");
    let out: Value =
        serde_json::from_str(&run_case(&case("flagged_incumbent_keeps_its_seat"))).unwrap();
    assert_eq!(out["seat"], "keeps_seat");
}

#[test]
fn validator_entry_profile_missing_or_invalid_flag_input_is_no_flag() {
    for name in [
        "model_outage_no_artifact_resolves_to_no_flag",
        "resolve_pin_mismatch_gives_none",
        "resolve_wrong_schema_gives_none",
        "resolve_non_shadow_artifact_gives_none",
        "resolve_absent_operator_gives_none",
        "resolve_duplicate_operator_gives_none",
        "resolve_unknown_flag_value_gives_none",
    ] {
        assert_eq!(run_case(&case(name)), "{\"flag\":\"none\"}", "{name}");
    }
    let out: Value = serde_json::from_str(&run_case(&case(
        "no_flag_input_selects_the_standard_profile",
    )))
    .unwrap();
    assert_eq!(out["profile"], "standard");
    assert_eq!(out["seat"], "may_take_new_seat");
}

#[test]
fn validator_entry_profile_worked_example_and_round_28_counts() {
    let all = cases();
    let mut flags = BTreeMap::new();
    let mut seats = BTreeMap::new();
    for case in &all {
        let out: Value = serde_json::from_str(&run_case(case)).unwrap();
        match case["group"].as_str() {
            Some("worked_example_20260903") => {
                let stand_in = case["name"]
                    .as_str()
                    .unwrap()
                    .split(':')
                    .next()
                    .unwrap()
                    .to_owned();
                *flags.entry(stand_in).or_insert(0) += usize::from(out["identity_flag"] == "flag");
            }
            Some("round_28") => {
                let rule = case["name"]
                    .as_str()
                    .unwrap()
                    .split(':')
                    .next()
                    .unwrap()
                    .to_owned();
                *seats
                    .entry((rule, out["seat"].as_str().unwrap().to_owned()))
                    .or_insert(0) += 1;
            }
            _ => {}
        }
    }
    assert_eq!(flags["legitimacy_score_zero"], 13);
    assert_eq!(flags["packet_not_established"], 0);
    let seat = |rule: &str, value: &str| {
        seats
            .get(&(rule.to_owned(), value.to_owned()))
            .copied()
            .unwrap_or(0)
    };
    assert_eq!(seat("entry_profile_v1", "keeps_seat"), 25);
    assert_eq!(seat("entry_profile_v1", "new_seat_withheld"), 36);
    assert_eq!(seat("interim_domain_only", "keeps_seat"), 25);
    assert_eq!(seat("interim_domain_only", "may_take_new_seat"), 24);
    assert_eq!(seat("interim_domain_only", "new_seat_withheld"), 12);
}

#[test]
fn validator_entry_profile_decision_is_marked_shadow_only() {
    for case in cases().iter().filter(|case| case["kind"] == "evaluate") {
        let out: Value = serde_json::from_str(&run_case(case)).unwrap();
        if out.get("error").is_none() {
            assert_eq!(out["shadow_only"], true, "{}", case["name"]);
        }
    }
}
