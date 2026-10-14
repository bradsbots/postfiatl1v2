//! Synthetic response-consistency regressions for the public SDK validator.
//! No requests, sockets, signing, wallet or ledger operations are performed.

use postfiat_rpc_sdk::{
    validate_response_kind, RpcResponse, RpcResponseKind, RpcResponseValidationError,
};
use serde_json::{json, Value};
use std::collections::BTreeSet;

fn observed_validation(response: &RpcResponse, kind: RpcResponseKind) -> Value {
    match validate_response_kind(response, kind) {
        Ok(()) => json!({
            "accepted": true, "error_variant": null, "field": null,
            "message": null, "display": null,
        }),
        Err(error) => {
            let display = error.to_string();
            match error {
                RpcResponseValidationError::InvalidResult { field, message } => json!({
                    "accepted": false, "error_variant": "InvalidResult", "field": field,
                    "message": message, "display": display,
                }),
                RpcResponseValidationError::Protocol(_) => json!({
                    "accepted": false, "error_variant": "Protocol", "field": null,
                    "message": null, "display": display,
                }),
                RpcResponseValidationError::UnexpectedId { .. } => json!({
                    "accepted": false, "error_variant": "UnexpectedId", "field": null,
                    "message": null, "display": display,
                }),
                RpcResponseValidationError::ExpectedSuccess { .. } => json!({
                    "accepted": false, "error_variant": "ExpectedSuccess", "field": null,
                    "message": null, "display": display,
                }),
            }
        }
    }
}

#[test]
fn nested_asset_and_escrow_ids_bind_to_outer_result() {
    let fixture: Value = serde_json::from_str(include_str!("fixtures/asset_escrow_inner_id.json"))
        .expect("fixed public synthetic fixtures");
    let cases = fixture["cases"].as_array().expect("literal cases");
    assert_eq!(cases.len(), 28, "complete independent regression matrix");
    let mut names = BTreeSet::new();
    let mut failures = Vec::new();
    let mut accepted = 0;
    for case in cases {
        let name = case["name"].as_str().expect("case name");
        assert!(names.insert(name), "duplicate case {name}");
        let kind = match case["kind"].as_str().expect("response kind") {
            "AssetInfo" => RpcResponseKind::AssetInfo,
            "EscrowInfo" => RpcResponseKind::EscrowInfo,
            "OfferInfo" => RpcResponseKind::OfferInfo,
            "NftInfo" => RpcResponseKind::NftInfo,
            unsupported => panic!("unexpected kind {unsupported}"),
        };
        let response: RpcResponse =
            serde_json::from_value(case["response"].clone()).expect("actual response type");
        let before = serde_json::to_value(&response).expect("typed input JSON");
        assert_eq!(before, case["response"], "input normalization for {name}");
        let observed = observed_validation(&response, kind);
        let after = serde_json::to_value(&response).expect("typed output JSON");
        let unchanged = after == before;
        println!(
            "SDK_INNER_ID_CASE {}",
            json!({
                "name": name, "kind": case["kind"], "observed": observed,
                "response_json_unchanged": unchanged, "response_json": after,
            })
        );
        accepted += usize::from(observed["accepted"] == true);
        if observed != case["expected_corrected"] || !unchanged {
            failures.push(json!({
                "name": name, "expected": case["expected_corrected"],
                "observed": observed, "response_json_unchanged": unchanged,
            }));
        }
    }
    println!(
        "SDK_INNER_ID_SUMMARY {}",
        json!({
            "cases": cases.len(), "accepted": accepted, "rejected": cases.len() - accepted,
            "corrected_contract_mismatches": failures,
        })
    );
    assert!(
        failures.is_empty(),
        "actual SDK validator violates the fixed corrected contract: {}",
        json!(failures)
    );
}
