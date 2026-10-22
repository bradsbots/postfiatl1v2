mod owned_recovery_status {
    use super::*;
    use postfiat_types::{
        FastPayCertificateV1, FastPayFenceOriginV1, FastPayOperationKindV1,
        FastPayOrderRecoveryV1, FastPayRecoveryDecisionV1, FastPayVersionFenceV1,
        OwnedCertificateDomain, OwnedObjectRef, OwnedOutputSpec, OwnedTransferCertificateV3,
        OwnedTransferOrderV3, OwnedTransferVote, FASTPAY_ORDER_RECOVERY_SCHEMA_V1,
        FASTPAY_VERSION_FENCE_SCHEMA_V1, OWNED_CERTIFICATE_DOMAIN_SCHEMA_V3,
    };
    use serde_json::{Value, json};

    fn with(mut value: Value, pointer: &str, replacement: Value) -> Value {
        *value.pointer_mut(pointer).expect("fixture pointer") = replacement;
        value
    }

    /// A transfer order whose recovery lock id is the real
    /// `fastpay_transfer_lock_id_v1` digest, so a confirmed fence built from
    /// it passes `FastPayVersionFenceV1::validate_shape`.
    fn transfer_order() -> OwnedTransferOrderV3 {
        let mut order = OwnedTransferOrderV3 {
            domain: OwnedCertificateDomain {
                schema: OWNED_CERTIFICATE_DOMAIN_SCHEMA_V3.to_string(),
                chain_id: "rpc-sdk-tests".to_string(),
                genesis_hash: "11".repeat(48),
                protocol_version: 3,
                registry_id: "22".repeat(48),
            },
            recovery: FastPayOrderRecoveryV1 {
                schema: FASTPAY_ORDER_RECOVERY_SCHEMA_V1.to_string(),
                committee_epoch: 7,
                lock_id: "00".repeat(48),
                valid_from_height: 100,
                expires_at_height: 110,
                recovery_closes_at_height: 120,
            },
            inputs: vec![OwnedObjectRef {
                id: "33".repeat(32),
                version: 9,
            }],
            outputs: vec![OwnedOutputSpec {
                owner_pubkey_hex: "44".repeat(32),
                value: 9,
                asset: "PFT".to_string(),
            }],
            fee: 1,
            nonce: 8,
            memos: Vec::new(),
        };
        order.recovery.lock_id = postfiat_types::fastpay_transfer_lock_id_v1(&order);
        order
    }

    fn certificate() -> FastPayCertificateV1 {
        FastPayCertificateV1::Transfer(OwnedTransferCertificateV3 {
            order: transfer_order(),
            owner_pubkey_hex: "aa".repeat(32),
            owner_signature_hex: "bb".repeat(32),
            votes: vec![OwnedTransferVote {
                validator_id: "validator-0".to_string(),
                signature_hex: "cc".repeat(32),
            }],
        })
    }

    fn fence(decision: FastPayRecoveryDecisionV1) -> FastPayVersionFenceV1 {
        let certificate = certificate();
        let input = certificate.inputs()[0].clone();
        let retained = matches!(decision, FastPayRecoveryDecisionV1::Confirmed { .. });
        FastPayVersionFenceV1 {
            schema: FASTPAY_VERSION_FENCE_SCHEMA_V1.to_string(),
            operation: FastPayOperationKindV1::Transfer,
            origin: FastPayFenceOriginV1::OrderedRecovery,
            committee_epoch: 7,
            registry_root: "22".repeat(48),
            lock_id: certificate.recovery().lock_id.clone(),
            inputs: vec![input.clone()],
            decision,
            certificate: retained.then_some(certificate),
            decided_at_height: 120,
            next_versions: vec![OwnedObjectRef {
                id: input.id,
                version: input.version + 1,
            }],
        }
    }

    fn confirmed_fence() -> FastPayVersionFenceV1 {
        fence(FastPayRecoveryDecisionV1::Confirmed {
            order_digest: "44".repeat(48),
            certificate_digest: "55".repeat(48),
        })
    }

    fn cancelled_fence() -> FastPayVersionFenceV1 {
        fence(FastPayRecoveryDecisionV1::Cancelled)
    }

    fn lock_id() -> String {
        confirmed_fence().lock_id
    }

    fn report(status: &str, reveal_count: u64, fence: Option<&FastPayVersionFenceV1>) -> Value {
        json!({
            "schema": "postfiat-fastpay-recovery-status-v1",
            "lock_id": lock_id(),
            "status": status,
            "reveal_count": reveal_count,
            "fence": fence
                .map(|fence| serde_json::to_value(fence).expect("fence json"))
                .unwrap_or(Value::Null)
        })
    }

    fn validate(report: &Value) -> Result<(), RpcResponseValidationError> {
        validate_response_kind(
            &success_response("owned-recovery-status-1", report, vec![])
                .expect("owned recovery status response"),
            RpcResponseKind::OwnedRecoveryStatus,
        )
    }

    fn rejected_field(report: Value) -> String {
        match validate(&report) {
            Err(RpcResponseValidationError::InvalidResult { field, .. }) => field,
            other => panic!("expected an InvalidResult rejection, got {other:?}"),
        }
    }

    #[test]
    fn builds_and_validates_owned_recovery_status_request() {
        let request = owned_recovery_status_request(
            "owned-recovery-status-1",
            OwnedRecoveryStatusParams { lock_id: lock_id() },
        );
        assert_eq!(request.method, METHOD_OWNED_RECOVERY_STATUS);
        assert_eq!(request.params["lock_id"], json!(lock_id()));
        validate_request(
            &request,
            Some("owned-recovery-status-1"),
            Some(RpcRequestKind::OwnedRecoveryStatus),
        )
        .expect("owned recovery status request");
    }

    #[test]
    fn rejects_owned_recovery_status_request_params() {
        let rejects = |request: RpcRequest| {
            assert!(
                validate_request(&request, None, Some(RpcRequestKind::OwnedRecoveryStatus))
                    .is_err(),
                "expected rejection for {:?}",
                request.params
            );
        };
        rejects(RpcRequest::empty("owned-recovery-status-2", METHOD_OWNED_RECOVERY_STATUS));
        rejects(
            RpcRequest::empty("owned-recovery-status-3", METHOD_OWNED_RECOVERY_STATUS)
                .with_param_value("lock_id", string_value("AB".repeat(48))),
        );
        rejects(
            RpcRequest::empty("owned-recovery-status-4", METHOD_OWNED_RECOVERY_STATUS)
                .with_param_value("lock_id", string_value("ab".repeat(47))),
        );
        rejects(
            owned_recovery_status_request(
                "owned-recovery-status-5",
                OwnedRecoveryStatusParams { lock_id: lock_id() },
            )
            .with_param_value("certificate_digest", string_value("ab".repeat(48))),
        );
    }

    #[test]
    fn accepts_every_status_value() {
        validate(&report("confirmed", 2, Some(&confirmed_fence()))).expect("confirmed");
        validate(&report("cancelled", 0, Some(&cancelled_fence()))).expect("cancelled");
        validate(&report("certificate_revealed", 1, None)).expect("certificate_revealed");
        validate(&report("open_or_unknown", 0, None)).expect("open_or_unknown");
    }

    #[test]
    fn rejects_wrong_schema() {
        let value = with(
            report("open_or_unknown", 0, None),
            "/schema",
            json!("postfiat-fastpay-recovery-status-v2"),
        );
        assert_eq!(rejected_field(value), "schema");
    }

    #[test]
    fn rejects_malformed_lock_id() {
        let value = with(report("open_or_unknown", 0, None), "/lock_id", json!("AB".repeat(48)));
        assert_eq!(rejected_field(value), "lock_id");
        let value = with(report("open_or_unknown", 0, None), "/lock_id", json!("ab".repeat(47)));
        assert_eq!(rejected_field(value), "lock_id");
    }

    #[test]
    fn rejects_unknown_status_value() {
        let value = with(report("open_or_unknown", 0, None), "/status", json!("pending"));
        assert_eq!(rejected_field(value), "status");
        let value = with(report("open_or_unknown", 0, None), "/status", json!(""));
        assert_eq!(rejected_field(value), "status");
    }

    #[test]
    fn rejects_non_integer_reveal_count() {
        let value = with(report("open_or_unknown", 0, None), "/reveal_count", json!(-1));
        assert_eq!(rejected_field(value), "reveal_count");
        let value = with(report("open_or_unknown", 0, None), "/reveal_count", json!("0"));
        assert_eq!(rejected_field(value), "reveal_count");
    }

    #[test]
    fn rejects_missing_fence_key() {
        let mut value = report("open_or_unknown", 0, None);
        value.as_object_mut().expect("object").remove("fence");
        assert_eq!(rejected_field(value), "fence");
    }

    #[test]
    fn rejects_status_that_disagrees_with_fence_and_reveal_count() {
        assert_eq!(
            rejected_field(report("cancelled", 0, Some(&confirmed_fence()))),
            "status"
        );
        assert_eq!(
            rejected_field(report("open_or_unknown", 0, Some(&cancelled_fence()))),
            "status"
        );
        assert_eq!(
            rejected_field(report("certificate_revealed", 3, Some(&confirmed_fence()))),
            "status"
        );
        assert_eq!(rejected_field(report("open_or_unknown", 1, None)), "status");
        assert_eq!(rejected_field(report("certificate_revealed", 0, None)), "status");
        assert_eq!(rejected_field(report("confirmed", 5, None)), "status");
    }

    #[test]
    fn rejects_fence_for_another_lock() {
        let value = with(
            report("confirmed", 0, Some(&confirmed_fence())),
            "/lock_id",
            json!("ab".repeat(48)),
        );
        assert_eq!(rejected_field(value), "fence.lock_id");
    }

    #[test]
    fn rejects_fence_records_that_fail_the_type_shape_rules() {
        // Unknown field: FastPayVersionFenceV1 is deny_unknown_fields.
        let mut value = report("confirmed", 0, Some(&confirmed_fence()));
        value["fence"]
            .as_object_mut()
            .expect("fence object")
            .insert("unexpected".to_string(), json!(true));
        assert_eq!(rejected_field(value), "fence");
        // A cancelled fence must not retain a certificate.
        let mut retained = cancelled_fence();
        retained.certificate = Some(certificate());
        assert_eq!(rejected_field(report("cancelled", 0, Some(&retained))), "fence");
        // A confirmed fence must retain its certificate.
        let mut bare = confirmed_fence();
        bare.certificate = None;
        assert_eq!(rejected_field(report("confirmed", 0, Some(&bare))), "fence");
        // Each input must advance by exactly one version.
        let mut stale = confirmed_fence();
        stale.next_versions[0].version = stale.inputs[0].version;
        assert_eq!(rejected_field(report("confirmed", 0, Some(&stale))), "fence");
        // The fence schema is pinned by the type itself.
        let value = with(
            report("confirmed", 0, Some(&confirmed_fence())),
            "/fence/schema",
            json!("postfiat-fastpay-version-fence-v2"),
        );
        assert_eq!(rejected_field(value), "fence");
    }

    // --- request binding (validate_owned_recovery_status_response) ---

    fn status_request(id: &str, lock_id: String) -> RpcRequest {
        owned_recovery_status_request(id, OwnedRecoveryStatusParams { lock_id })
    }

    fn bind(report: &Value, request: &RpcRequest) -> Result<(), RpcResponseValidationError> {
        validate_owned_recovery_status_response(
            &success_response("owned-recovery-status-1", report, vec![])
                .expect("owned recovery status response"),
            request,
        )
    }

    fn bind_rejected_field(report: &Value, request: &RpcRequest) -> String {
        match bind(report, request) {
            Err(RpcResponseValidationError::InvalidResult { field, .. }) => field,
            other => panic!("expected an InvalidResult rejection, got {other:?}"),
        }
    }

    #[test]
    fn binds_same_id_response_to_the_requested_lock() {
        // Two requests with the same id: A selects the reported lock, B another.
        let lock_a = lock_id();
        let lock_b = "ab".repeat(48);
        assert_ne!(lock_a, lock_b);
        let request_a = status_request("owned-recovery-status-1", lock_a);
        let request_b = status_request("owned-recovery-status-1", lock_b);
        let confirmed = confirmed_fence();
        let cancelled = cancelled_fence();
        for response in [
            report("open_or_unknown", 0, None),
            report("certificate_revealed", 2, None),
            report("confirmed", 1, Some(&confirmed)),
            report("cancelled", 0, Some(&cancelled)),
        ] {
            assert!(validate(&response).is_ok(), "report is valid on its own");
            bind(&response, &request_a).expect("lock A request binds the lock A report");
            assert_eq!(bind_rejected_field(&response, &request_b), "lock_id");
        }
    }

    #[test]
    fn rejects_unbound_id_foreign_method_and_malformed_request() {
        let response = report("open_or_unknown", 0, None);
        let other_id = status_request("owned-recovery-status-2", lock_id());
        assert!(matches!(
            bind(&response, &other_id),
            Err(RpcResponseValidationError::UnexpectedId { .. })
        ));
        // Foreign method carrying the same lock_id param.
        let foreign = RpcRequest::empty("owned-recovery-status-1", METHOD_ACCOUNT)
            .with_param_value("lock_id", string_value(lock_id()));
        assert_eq!(bind_rejected_field(&response, &foreign), "request");
        // Malformed owned_recovery_status requests.
        for malformed in [
            RpcRequest::empty("owned-recovery-status-1", METHOD_OWNED_RECOVERY_STATUS),
            status_request("owned-recovery-status-1", lock_id().to_uppercase()),
            status_request("owned-recovery-status-1", lock_id()[..94].to_string()),
            status_request("owned-recovery-status-1", lock_id())
                .with_param_value("status", string_value("confirmed")),
        ] {
            assert_eq!(bind_rejected_field(&response, &malformed), "request");
        }
    }

    #[test]
    fn request_binding_still_applies_the_shape_checks() {
        let request = status_request("owned-recovery-status-1", lock_id());
        let wrong_status = report("confirmed", 0, None);
        assert_eq!(bind_rejected_field(&wrong_status, &request), "status");
        let confirmed = confirmed_fence();
        let foreign_fence = with(
            report("confirmed", 1, Some(&confirmed)),
            "/fence/lock_id",
            json!("ab".repeat(48)),
        );
        assert!(bind(&foreign_fence, &request).is_err());
    }
}
