mod market_ops_status {
    use super::*;
    use serde_json::{Value, json};

    fn asset_id() -> String {
        "ab".repeat(48)
    }

    fn with(mut value: Value, pointer: &str, replacement: Value) -> Value {
        *value.pointer_mut(pointer).expect("fixture pointer") = replacement;
        value
    }

    /// A report shaped like the node's `MarketOpsPublicStatus` for an
    /// active envelope: fresh packets, funded reserve, nonzero caps.
    fn fixture() -> Value {
        json!({
            "schema": "postfiat-market-ops-public-status-v1",
            "asset_id": asset_id(),
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
            "envelope_epoch": 7,
            "packet_expires_at": 1_800_000_000_u64,
            "disclosure": "The protocol proves NAV and may execute bounded market operations under public caps. Holders do not have a standing right to redeem at NAV, and market operations can pause."
        })
    }

    /// The same report after the node has disabled the caps for a
    /// non-active status.
    fn inactive_fixture(status: &str) -> Value {
        let report = with(fixture(), "/market_operations_status", json!(status));
        let report = with(report, "/current_reserve_deploy_cap_usd_e8", json!(0));
        let report = with(report, "/current_mint_cap_atoms", json!(0));
        // Inputs consistent with the node builder reaching `status`.
        match status {
            "stale" | "missing_source_packet" => {
                with(report, "/reserve_packet_fresh", json!(false))
            }
            "underfunded" => with(
                report,
                "/funded_alignment_reserve_usd_e8",
                json!(199_999_999_999_u64),
            ),
            _ => report,
        }
    }

    fn validate(report: &Value) -> Result<(), RpcResponseValidationError> {
        validate_response_kind(
            &success_response("market-ops-status-1", report, vec![])
                .expect("market ops status response"),
            RpcResponseKind::MarketOpsStatus,
        )
    }

    fn rejected_field(report: Value) -> String {
        match validate(&report) {
            Err(RpcResponseValidationError::InvalidResult { field, .. }) => field,
            other => panic!("expected an InvalidResult rejection, got {other:?}"),
        }
    }

    #[test]
    fn builds_and_validates_market_ops_status_request_without_epoch() {
        let request = market_ops_status_request(
            "market-ops-status-1",
            MarketOpsStatusParams {
                asset_id: asset_id(),
                epoch: None,
            },
        );
        assert_eq!(request.method, METHOD_MARKET_OPS_STATUS);
        assert_eq!(request.params["asset_id"], json!(asset_id()));
        assert!(request.params.get("epoch").is_none());
        validate_request(
            &request,
            Some("market-ops-status-1"),
            Some(RpcRequestKind::MarketOpsStatus),
        )
        .expect("market ops status request");
    }

    #[test]
    fn builds_and_validates_market_ops_status_request_with_epoch() {
        let request = market_ops_status_request(
            "market-ops-status-2",
            MarketOpsStatusParams {
                asset_id: asset_id(),
                epoch: Some(7),
            },
        );
        assert_eq!(request.params["epoch"], json!(7));
        validate_request(
            &request,
            Some("market-ops-status-2"),
            Some(RpcRequestKind::MarketOpsStatus),
        )
        .expect("market ops status request with epoch");
    }

    #[test]
    fn rejects_market_ops_status_request_params() {
        let uppercase = RpcRequest::empty("market-ops-status-3", METHOD_MARKET_OPS_STATUS)
            .with_param_value("asset_id", string_value("AB".repeat(48)));
        assert!(validate_request(&uppercase, None, Some(RpcRequestKind::MarketOpsStatus)).is_err());

        let short = RpcRequest::empty("market-ops-status-4", METHOD_MARKET_OPS_STATUS)
            .with_param_value("asset_id", string_value("ab".repeat(47)));
        assert!(validate_request(&short, None, Some(RpcRequestKind::MarketOpsStatus)).is_err());

        let missing = RpcRequest::empty("market-ops-status-5", METHOD_MARKET_OPS_STATUS);
        assert!(validate_request(&missing, None, Some(RpcRequestKind::MarketOpsStatus)).is_err());

        let zero_epoch = market_ops_status_request(
            "market-ops-status-6",
            MarketOpsStatusParams {
                asset_id: asset_id(),
                epoch: Some(0),
            },
        );
        assert!(validate_request(&zero_epoch, None, Some(RpcRequestKind::MarketOpsStatus)).is_err());

        let string_epoch = RpcRequest::empty("market-ops-status-7", METHOD_MARKET_OPS_STATUS)
            .with_param_value("asset_id", string_value(asset_id()))
            .with_param_value("epoch", string_value("7"));
        assert!(validate_request(&string_epoch, None, Some(RpcRequestKind::MarketOpsStatus)).is_err());

        let extra = market_ops_status_request(
            "market-ops-status-8",
            MarketOpsStatusParams {
                asset_id: asset_id(),
                epoch: None,
            },
        )
        .with_param_value("limit", u64_value(5));
        assert!(validate_request(&extra, None, Some(RpcRequestKind::MarketOpsStatus)).is_err());
    }

    #[test]
    fn accepts_active_market_ops_status_report() {
        validate(&fixture()).expect("valid active market ops status");
    }

    #[test]
    fn accepts_every_inactive_status_with_zero_caps() {
        for status in [
            "expired",
            "missing_source_packet",
            "paused",
            "stale",
            "underfunded",
        ] {
            validate(&inactive_fixture(status)).unwrap_or_else(|error| {
                panic!("expected `{status}` with zero caps to validate, got {error:?}")
            });
        }
    }

    #[test]
    fn accepts_largest_u64_figures() {
        let report = with(fixture(), "/nav_floor_usd_e8", json!(u64::MAX));
        let report = with(report, "/verified_net_assets_usd_e8", json!(u64::MAX));
        let report = with(report, "/valid_global_supply_atoms", json!(u64::MAX));
        let report = with(report, "/current_mint_cap_atoms", json!(u64::MAX));
        validate(&report).expect("u64::MAX figures");
    }

    #[test]
    fn rejects_figures_beyond_u64_max_instead_of_rounding() {
        // serde_json parses this literal into a lossy f64 (no arbitrary_precision);
        // the node could not have serialized it, so the SDK fails closed.
        let raw = r#"{"nav_floor_usd_e8": 18446744073709551616}"#;
        let oversized: Value = serde_json::from_str(raw).expect("parse oversized literal");
        let report = with(fixture(), "/nav_floor_usd_e8", oversized["nav_floor_usd_e8"].clone());
        assert_eq!(rejected_field(report), "nav_floor_usd_e8");
        assert!(matches!(
            validate(&with(
                fixture(),
                "/current_mint_cap_atoms",
                json!(18_446_744_073_709_551_616_f64)
            )),
            Err(RpcResponseValidationError::InvalidResult { field, message, .. })
                if field == "current_mint_cap_atoms" && message.contains("exceeds u64::MAX")
        ));
    }

    #[test]
    fn rejects_wrong_schema() {
        let report = with(fixture(), "/schema", json!("postfiat-market-ops-public-status-v2"));
        assert_eq!(rejected_field(report), "schema");
    }

    #[test]
    fn rejects_malformed_identifiers() {
        let report = with(fixture(), "/asset_id", json!("AB".repeat(48)));
        assert_eq!(rejected_field(report), "asset_id");
        let report = with(fixture(), "/accepted_policy_hash", json!("cd".repeat(48)));
        assert_eq!(rejected_field(report), "accepted_policy_hash");
        let report = with(fixture(), "/envelope_hash", json!("ef".repeat(32)));
        assert_eq!(rejected_field(report), "envelope_hash");
    }

    #[test]
    fn rejects_zero_figures_the_node_requires_nonzero() {
        for (pointer, field) in [
            ("/nav_floor_usd_e8", "nav_floor_usd_e8"),
            ("/verified_net_assets_usd_e8", "verified_net_assets_usd_e8"),
            ("/valid_global_supply_atoms", "valid_global_supply_atoms"),
            ("/envelope_epoch", "envelope_epoch"),
        ] {
            let report = with(fixture(), pointer, json!(0));
            assert_eq!(rejected_field(report), field);
        }
    }

    #[test]
    fn rejects_figures_that_are_not_unsigned_integers() {
        let report = with(fixture(), "/funded_alignment_reserve_usd_e8", json!(-1));
        assert_eq!(rejected_field(report), "funded_alignment_reserve_usd_e8");
        let report = with(fixture(), "/required_alignment_reserve_usd_e8", json!("200"));
        assert_eq!(rejected_field(report), "required_alignment_reserve_usd_e8");
        let report = with(fixture(), "/packet_expires_at", json!(1.5));
        assert_eq!(rejected_field(report), "packet_expires_at");
    }

    #[test]
    fn rejects_unknown_status_value() {
        let report = with(fixture(), "/market_operations_status", json!("halted"));
        assert_eq!(rejected_field(report), "market_operations_status");
        let report = with(fixture(), "/market_operations_status", json!(""));
        assert_eq!(rejected_field(report), "market_operations_status");
    }

    #[test]
    fn rejects_nonzero_caps_unless_active() {
        let report = with(fixture(), "/market_operations_status", json!("paused"));
        assert_eq!(rejected_field(report), "current_reserve_deploy_cap_usd_e8");
        let report = with(inactive_fixture("stale"), "/current_mint_cap_atoms", json!(1));
        assert_eq!(rejected_field(report), "current_mint_cap_atoms");
    }

    #[test]
    fn rejects_missing_freshness_flags() {
        let report = with(fixture(), "/reserve_packet_fresh", json!("true"));
        assert_eq!(rejected_field(report), "reserve_packet_fresh");
        let report = with(fixture(), "/supply_packet_fresh", json!(1));
        assert_eq!(rejected_field(report), "supply_packet_fresh");
    }

    #[test]
    fn rejects_active_status_with_stale_reserve_packet() {
        let report = with(fixture(), "/reserve_packet_fresh", json!(false));
        assert_eq!(rejected_field(report), "reserve_packet_fresh");
    }

    #[test]
    fn rejects_active_status_with_stale_supply_packet() {
        let report = with(fixture(), "/supply_packet_fresh", json!(false));
        assert_eq!(rejected_field(report), "supply_packet_fresh");
    }

    #[test]
    fn rejects_active_status_with_underfunded_alignment_reserve() {
        let report = with(fixture(), "/funded_alignment_reserve_usd_e8", json!(0));
        assert_eq!(rejected_field(report), "funded_alignment_reserve_usd_e8");
        let report = with(
            fixture(),
            "/funded_alignment_reserve_usd_e8",
            json!(199_999_999_999_u64),
        );
        assert_eq!(rejected_field(report), "funded_alignment_reserve_usd_e8");
    }

    #[test]
    fn accepts_active_status_funded_exactly_at_the_requirement() {
        let report = with(
            fixture(),
            "/funded_alignment_reserve_usd_e8",
            json!(200_000_000_000_u64),
        );
        validate(&report).expect("funded == required is active");
    }

    #[test]
    fn rejects_inactive_status_the_report_contradicts() {
        // The node only reports `stale` when a freshness flag is false,
        // `missing_source_packet` with no fresh reserve packet, and
        // `underfunded` / `expired` once both packets are fresh, with
        // `underfunded` additionally requiring funded < required.
        for (status, pointer, value) in [
            ("stale", "/reserve_packet_fresh", json!(true)),
            ("missing_source_packet", "/reserve_packet_fresh", json!(true)),
            ("underfunded", "/funded_alignment_reserve_usd_e8", json!(200_000_000_000_u64)),
            ("underfunded", "/reserve_packet_fresh", json!(false)),
            ("underfunded", "/supply_packet_fresh", json!(false)),
            ("expired", "/reserve_packet_fresh", json!(false)),
            ("expired", "/supply_packet_fresh", json!(false)),
        ] {
            let report = with(inactive_fixture(status), pointer, value);
            assert_eq!(
                rejected_field(report),
                "market_operations_status",
                "{status} with {pointer}"
            );
        }
    }

    #[test]
    fn accepts_inactive_statuses_the_builder_can_emit() {
        // `paused` takes precedence over every other input.
        let report = with(inactive_fixture("paused"), "/reserve_packet_fresh", json!(false));
        let report = with(report, "/supply_packet_fresh", json!(false));
        let report = with(report, "/funded_alignment_reserve_usd_e8", json!(0));
        validate(&report).expect("paused with stale, underfunded inputs");
        // `stale` with only the supply packet stale.
        let report = with(inactive_fixture("stale"), "/reserve_packet_fresh", json!(true));
        let report = with(report, "/supply_packet_fresh", json!(false));
        validate(&report).expect("stale supply packet");
        // `expired` is decided before the funding check.
        let report = with(inactive_fixture("expired"), "/funded_alignment_reserve_usd_e8", json!(0));
        validate(&report).expect("expired and underfunded");
        // `missing_source_packet` with no nav asset: both flags false.
        let report = with(
            inactive_fixture("missing_source_packet"),
            "/supply_packet_fresh",
            json!(false),
        );
        validate(&report).expect("missing source packet without nav asset");
    }

    fn bound_request(asset: String, epoch: Option<u64>) -> RpcRequest {
        market_ops_status_request(
            "market-ops-status-1",
            MarketOpsStatusParams {
                asset_id: asset,
                epoch,
            },
        )
    }

    fn bound(report: &Value, request: &RpcRequest) -> Result<(), RpcResponseValidationError> {
        validate_market_ops_status_response_for_request(
            &success_response("market-ops-status-1", report, vec![])
                .expect("market ops status response"),
            request,
        )
    }

    fn bound_rejected_field(report: &Value, request: &RpcRequest) -> String {
        match bound(report, request) {
            Err(RpcResponseValidationError::InvalidResult { field, .. }) => field,
            other => panic!("expected an InvalidResult rejection, got {other:?}"),
        }
    }

    #[test]
    fn binds_response_to_requested_asset_and_epoch() {
        bound(&fixture(), &bound_request(asset_id(), Some(7))).expect("explicit epoch 7");
        // Omitted epoch = latest finalized envelope: any envelope epoch binds.
        bound(&fixture(), &bound_request(asset_id(), None)).expect("latest envelope");
        let later = with(fixture(), "/envelope_epoch", json!(9));
        bound(&later, &bound_request(asset_id(), None)).expect("latest envelope 9");
    }

    #[test]
    fn bound_validation_rejects_report_for_another_asset() {
        assert_eq!(
            bound_rejected_field(&fixture(), &bound_request("aa".repeat(48), Some(7))),
            "asset_id"
        );
        assert_eq!(
            bound_rejected_field(&fixture(), &bound_request("aa".repeat(48), None)),
            "asset_id"
        );
    }

    #[test]
    fn bound_validation_rejects_report_for_another_explicit_epoch() {
        assert_eq!(
            bound_rejected_field(&fixture(), &bound_request(asset_id(), Some(8))),
            "envelope_epoch"
        );
        assert_eq!(
            bound_rejected_field(&fixture(), &bound_request(asset_id(), Some(6))),
            "envelope_epoch"
        );
    }

    #[test]
    fn bound_validation_rejects_reviewer_wrong_asset_and_epoch() {
        // Request: asset aa*48, epoch 8; response: asset ab*48, envelope_epoch 7.
        assert!(bound(&fixture(), &bound_request("aa".repeat(48), Some(8))).is_err());
    }

    #[test]
    fn bound_validation_rejects_other_response_id() {
        let request = market_ops_status_request(
            "market-ops-status-2",
            MarketOpsStatusParams {
                asset_id: asset_id(),
                epoch: Some(7),
            },
        );
        assert!(matches!(
            bound(&fixture(), &request),
            Err(RpcResponseValidationError::UnexpectedId { .. })
        ));
    }

    #[test]
    fn bound_validation_rejects_request_of_another_method() {
        assert_eq!(
            bound_rejected_field(&fixture(), &status_request("market-ops-status-1")),
            "request"
        );
    }

    #[test]
    fn bound_validation_still_checks_the_report() {
        let report = with(fixture(), "/reserve_packet_fresh", json!(false));
        assert_eq!(
            bound_rejected_field(&report, &bound_request(asset_id(), Some(7))),
            "reserve_packet_fresh"
        );
    }

    #[test]
    fn rejects_altered_disclosure() {
        let report = with(
            fixture(),
            "/disclosure",
            json!("Holders have a standing right to redeem at NAV."),
        );
        assert_eq!(rejected_field(report), "disclosure");
    }
}
