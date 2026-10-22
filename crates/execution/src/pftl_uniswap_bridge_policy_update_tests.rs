// PFTL-Uniswap route Ethereum bridge committee rotation
// (`pftl_uniswap_route_bridge_policy_update`).

struct BridgePolicyFixture {
    genesis: Genesis,
    ledger: LedgerState,
    issuer_key: MlDsa65KeyPair,
    issuer: String,
    reserve_key: MlDsa65KeyPair,
    reserve: String,
    route_id: String,
    epoch1: FastSwapCommitteeV1,
    epoch2: FastSwapCommitteeV1,
    policy: EthereumRouteVerificationPolicyV1,
}

fn bridge_policy_committee(genesis: &Genesis, epoch: u64, seeds: &[u8]) -> FastSwapCommitteeV1 {
    let mut committee = FastSwapCommitteeV1 {
        domain: FastSwapCommitteeDomainV1 {
            chain: FastSwapChainDomainV1 {
                chain_id: genesis.chain_id.clone(),
                genesis_hash: FastSwapOpaqueHashV1(
                    hex_to_bytes(&crate::genesis_hash(genesis))
                        .expect("genesis hash hex")
                        .try_into()
                        .expect("48-byte genesis hash"),
                ),
                protocol_version: genesis.protocol_version,
            },
            fastswap_schema_version: postfiat_types::FASTSWAP_SCHEMA_VERSION_V1,
            committee_epoch: epoch,
            committee_root: FastSwapCommitteeRootV1::ZERO,
            validator_count: u16::try_from(seeds.len()).expect("committee size"),
            quorum: u16::try_from((2 * seeds.len()) / 3 + 1).expect("quorum"),
        },
        validators: seeds
            .iter()
            .enumerate()
            .map(|(index, seed)| FastSwapValidatorV1 {
                validator_id: format!("validator-{index}"),
                public_key: ml_dsa_65_keygen_from_seed(&[*seed; 32]).public_key,
            })
            .collect(),
    };
    committee.domain.committee_root = committee.computed_root().expect("committee root");
    committee
}

fn bridge_policy_fixture() -> BridgePolicyFixture {
    let genesis = Genesis::new("postfiat-local");
    let issuer_key = ml_dsa_65_keygen_from_seed(&[0x61; 32]);
    let reserve_key = ml_dsa_65_keygen_from_seed(&[0x62; 32]);
    let issuer = address_from_public_key(&issuer_key.public_key);
    let reserve = address_from_public_key(&reserve_key.public_key);
    let mut ledger = LedgerState::new(vec![
        Account::new(
            issuer.clone(),
            100_000,
            Some(bytes_to_hex(&issuer_key.public_key)),
        ),
        Account::new(
            reserve.clone(),
            100_000,
            Some(bytes_to_hex(&reserve_key.public_key)),
        ),
    ]);
    let receipt = bridge_policy_execute(
        &genesis,
        &mut ledger,
        &issuer_key,
        &issuer,
        ASSET_CREATE_TRANSACTION_KIND,
        AssetTransactionOperation::AssetCreate(AssetCreateOperation {
            issuer: issuer.clone(),
            code: "A6R".to_string(),
            version: 1,
            precision: 6,
            display_name: "Bridge policy rotation NAVCoin".to_string(),
            max_supply: None,
            requires_authorization: false,
            freeze_enabled: true,
            clawback_enabled: false,
        }),
        1,
    );
    assert!(receipt.accepted, "{receipt:?}");
    let native_asset_id = ledger.asset_definitions[0].asset_id.clone();
    let receipt = bridge_policy_execute(
        &genesis,
        &mut ledger,
        &issuer_key,
        &issuer,
        ASSET_CREATE_TRANSACTION_KIND,
        AssetTransactionOperation::AssetCreate(AssetCreateOperation {
            issuer: issuer.clone(),
            code: "USDR".to_string(),
            version: 1,
            precision: 6,
            display_name: "Bridge policy settlement asset".to_string(),
            max_supply: Some(1_000_000),
            requires_authorization: false,
            freeze_enabled: true,
            clawback_enabled: false,
        }),
        1,
    );
    assert!(receipt.accepted, "{receipt:?}");
    let settlement_asset_id = ledger.asset_definitions[1].asset_id.clone();
    let receipt = bridge_policy_execute(
        &genesis,
        &mut ledger,
        &issuer_key,
        &issuer,
        NAV_ASSET_REGISTER_TRANSACTION_KIND,
        AssetTransactionOperation::NavAssetRegister(NavAssetRegisterOperation {
            issuer: issuer.clone(),
            asset_id: native_asset_id.clone(),
            reserve_operator: reserve.clone(),
            proof_profile: "bridge-policy-ledger-transparent".to_string(),
            valuation_unit: "USDC".to_string(),
            redemption_account: issuer.clone(),
        }),
        2,
    );
    assert!(receipt.accepted, "{receipt:?}");

    // Epoch 1 still lists validator-5's genesis key (seed 6); epoch 2 is the
    // validator-activated successor with its rotated key (seed 16).
    let epoch1 = bridge_policy_committee(&genesis, 1, &[1, 2, 3, 4, 5, 6]);
    let epoch2 = bridge_policy_committee(&genesis, 2, &[1, 2, 3, 4, 5, 16]);
    let policy = EthereumRouteVerificationPolicyV1 {
        authority_epoch: 1,
        committee_root: epoch1.domain.committee_root,
        minimum_confirmations: 12,
        handoff_controller_code_hash: [0x71; 32],
        wrapped_navcoin_code_hash: [0x72; 32],
    };
    let route_id = "pftl-bridge-policy-route".to_string();
    let route = PftlUniswapConsensusRouteState {
        route_id: route_id.clone(),
        route_family: PFTL_UNISWAP_ROUTE_FAMILY_PRIMARY_MINT.to_string(),
        route_config_digest: "a1".repeat(48),
        route_trust_class: PFTL_UNISWAP_TRUST_CLASS_BFT_CHECKPOINT.to_string(),
        native_nav_asset_id: native_asset_id,
        settlement_asset_id,
        handoff_controller: "0x1111111111111111111111111111111111111111".to_string(),
        settlement_adapter: "0x2222222222222222222222222222222222222222".to_string(),
        wrapped_navcoin_token: "0x3333333333333333333333333333333333333333".to_string(),
        ethereum_chain_id: 1,
        route_supply_cap_atoms: 1_000,
        packet_notional_cap_atoms: 100,
        latest_finalized_nav_epoch: 1,
        return_finality_blocks: 12,
        live_value_enabled: true,
        ethereum_verification_policy: Some(policy.clone()),
        authorized_valid_supply_atoms: 0,
        pftl_spendable_supply_atoms: 0,
        native_spendable_balances_atoms: std::collections::BTreeMap::new(),
        ethereum_spendable_supply_atoms: 0,
        other_registered_venue_supply_atoms: 0,
        outstanding_bridge_claims_atoms: 0,
        pending_return_import_claims_atoms: 0,
        settlement_reserve_atoms: 0,
        primary_subscription_nonces: std::collections::BTreeMap::new(),
        export_packets: std::collections::BTreeMap::new(),
        export_nonces: std::collections::BTreeMap::new(),
        return_imports: std::collections::BTreeMap::new(),
        paused: false,
        v2: None,
    };
    route.validate().expect("valid bridge policy route fixture");
    ledger.pftl_uniswap_routes.push(route);
    crate::fastswap_control::register_fastswap_committee(&mut ledger, epoch1.clone(), None)
        .expect("genesis bridge committee");
    BridgePolicyFixture {
        genesis,
        ledger,
        issuer_key,
        issuer,
        reserve_key,
        reserve,
        route_id,
        epoch1,
        epoch2,
        policy,
    }
}

fn bridge_policy_signed(
    genesis: &Genesis,
    ledger: &LedgerState,
    key: &MlDsa65KeyPair,
    signer: &str,
    kind: &str,
    operation: AssetTransactionOperation,
) -> SignedAssetTransaction {
    signed_asset_transaction_with_minimum_fee(
        genesis,
        ledger,
        key,
        kind,
        ledger
            .account(signer)
            .expect("bridge policy signer")
            .sequence
            + 1,
        operation,
    )
}

fn bridge_policy_execute(
    genesis: &Genesis,
    ledger: &mut LedgerState,
    key: &MlDsa65KeyPair,
    signer: &str,
    kind: &str,
    operation: AssetTransactionOperation,
    height: u64,
) -> Receipt {
    let transaction = bridge_policy_signed(genesis, ledger, key, signer, kind, operation);
    execute_asset_transaction(genesis, ledger, &transaction, height)
}

fn bridge_policy_update(
    fixture: &BridgePolicyFixture,
    signer: &str,
    committee: &FastSwapCommitteeV1,
) -> PftlUniswapRouteBridgePolicyUpdateOperation {
    PftlUniswapRouteBridgePolicyUpdateOperation {
        issuer: signer.to_string(),
        route_id: fixture.route_id.clone(),
        authority_epoch: committee.domain.committee_epoch,
        committee_root: bytes_to_hex(&committee.domain.committee_root.0),
        minimum_confirmations: fixture.policy.minimum_confirmations,
        handoff_controller_code_hash: bytes_to_hex(&fixture.policy.handoff_controller_code_hash),
        wrapped_navcoin_code_hash: bytes_to_hex(&fixture.policy.wrapped_navcoin_code_hash),
    }
}

fn bridge_policy_apply(
    fixture: &mut BridgePolicyFixture,
    by_reserve: bool,
    operation: PftlUniswapRouteBridgePolicyUpdateOperation,
) -> Receipt {
    let (key, signer) = if by_reserve {
        (&fixture.reserve_key, fixture.reserve.clone())
    } else {
        (&fixture.issuer_key, fixture.issuer.clone())
    };
    bridge_policy_execute(
        &fixture.genesis,
        &mut fixture.ledger,
        key,
        &signer,
        PFTL_UNISWAP_ROUTE_BRIDGE_POLICY_UPDATE_TRANSACTION_KIND,
        AssetTransactionOperation::PftlUniswapRouteBridgePolicyUpdate(operation),
        10,
    )
}

fn bridge_policy_assert_rejected(
    fixture: &mut BridgePolicyFixture,
    by_reserve: bool,
    operation: PftlUniswapRouteBridgePolicyUpdateOperation,
    code: &str,
) {
    let route_before = fixture
        .ledger
        .pftl_uniswap_route(&fixture.route_id)
        .cloned();
    let receipts_before = fixture.ledger.pftl_uniswap_receipts.len();
    let receipt = bridge_policy_apply(fixture, by_reserve, operation);
    assert!(!receipt.accepted, "{receipt:?}");
    assert_eq!(receipt.code, code, "{receipt:?}");
    assert_eq!(
        fixture
            .ledger
            .pftl_uniswap_route(&fixture.route_id)
            .cloned(),
        route_before
    );
    assert_eq!(fixture.ledger.pftl_uniswap_receipts.len(), receipts_before);
}

#[test]
fn bridge_policy_update_issuer_advances_committee_and_keeps_echoed_fields() {
    let mut fixture = bridge_policy_fixture();
    let epoch2 = fixture.epoch2.clone();
    // Before validators activate epoch 2, the route stays on epoch 1.
    let operation = bridge_policy_update(&fixture, &fixture.issuer, &epoch2);
    bridge_policy_assert_rejected(
        &mut fixture,
        false,
        operation.clone(),
        "pftl_uniswap_bridge_policy_committee_not_governed",
    );
    fixture.ledger.fastswap_committees.push(epoch2.clone());

    let before = fixture
        .ledger
        .pftl_uniswap_route(&fixture.route_id)
        .cloned()
        .unwrap();
    let receipt = bridge_policy_apply(&mut fixture, false, operation);
    assert!(receipt.accepted, "{receipt:?}");
    let after = fixture
        .ledger
        .pftl_uniswap_route(&fixture.route_id)
        .cloned()
        .unwrap();
    let policy = after.ethereum_verification_policy.clone().unwrap();
    assert_eq!(policy.authority_epoch, 2);
    assert_eq!(policy.committee_root, epoch2.domain.committee_root);
    assert_eq!(
        policy.minimum_confirmations,
        fixture.policy.minimum_confirmations
    );
    assert_eq!(
        policy.handoff_controller_code_hash,
        fixture.policy.handoff_controller_code_hash
    );
    assert_eq!(
        policy.wrapped_navcoin_code_hash,
        fixture.policy.wrapped_navcoin_code_hash
    );
    let mut unchanged = after.clone();
    unchanged.ethereum_verification_policy = before.ethereum_verification_policy.clone();
    assert_eq!(unchanged, before, "only the Ethereum policy may change");
    let route_receipt = fixture.ledger.pftl_uniswap_receipts.last().unwrap();
    assert_eq!(route_receipt.transition, "route_bridge_policy_updated");
    assert_eq!(
        route_receipt.state_before_hash,
        pftl_uniswap_route_state_hash(&before)
    );
    assert_eq!(
        route_receipt.state_after_hash,
        pftl_uniswap_route_state_hash(&after)
    );
    // The canonical route string carries the new authority.
    assert_ne!(
        route_receipt.state_before_hash,
        route_receipt.state_after_hash
    );
}

#[test]
fn bridge_policy_update_rejects_non_issuer_signer() {
    let mut fixture = bridge_policy_fixture();
    fixture
        .ledger
        .fastswap_committees
        .push(fixture.epoch2.clone());
    let epoch2 = fixture.epoch2.clone();
    // The reserve operator may run the route but may not move its committee.
    let operation = bridge_policy_update(&fixture, &fixture.reserve, &epoch2);
    bridge_policy_assert_rejected(
        &mut fixture,
        true,
        operation,
        "unauthorized_pftl_uniswap_bridge_policy_issuer",
    );
}

#[test]
fn bridge_policy_update_rejects_epoch_other_than_current_plus_one() {
    let mut fixture = bridge_policy_fixture();
    let epoch2 = fixture.epoch2.clone();
    fixture.ledger.fastswap_committees.push(epoch2.clone());
    let epoch3 = bridge_policy_committee(&fixture.genesis, 3, &[1, 2, 3, 4, 5, 26]);
    fixture.ledger.fastswap_committees.push(epoch3.clone());
    let skip = bridge_policy_update(&fixture, &fixture.issuer, &epoch3);
    bridge_policy_assert_rejected(
        &mut fixture,
        false,
        skip,
        "pftl_uniswap_bridge_policy_epoch_mismatch",
    );
    let mut same = bridge_policy_update(&fixture, &fixture.issuer, &epoch2);
    same.authority_epoch = 1;
    // Epoch 1 is the route-creation epoch; the envelope rejects it statelessly.
    bridge_policy_assert_rejected(&mut fixture, false, same, "bad_asset_transaction_envelope");
}

#[test]
fn bridge_policy_update_rejects_root_not_over_current_governed_keys() {
    let mut fixture = bridge_policy_fixture();
    // A well-formed epoch-2 roster that validators never activated.
    let unregistered = bridge_policy_committee(&fixture.genesis, 2, &[1, 2, 3, 4, 5, 99]);
    let operation = bridge_policy_update(&fixture, &fixture.issuer, &unregistered);
    bridge_policy_assert_rejected(
        &mut fixture,
        false,
        operation,
        "pftl_uniswap_bridge_policy_committee_not_governed",
    );
    // Re-labelling the stale epoch-1 roster as epoch 2 is not governed either.
    let mut stale = bridge_policy_update(&fixture, &fixture.issuer, &fixture.epoch1.clone());
    stale.authority_epoch = 2;
    bridge_policy_assert_rejected(
        &mut fixture,
        false,
        stale,
        "pftl_uniswap_bridge_policy_committee_not_governed",
    );
    // A governed epoch-2 committee that has already been superseded is stale.
    let epoch2 = fixture.epoch2.clone();
    fixture.ledger.fastswap_committees.push(epoch2.clone());
    fixture
        .ledger
        .fastswap_committees
        .push(bridge_policy_committee(
            &fixture.genesis,
            3,
            &[1, 2, 3, 4, 5, 26],
        ));
    let superseded = bridge_policy_update(&fixture, &fixture.issuer, &epoch2);
    bridge_policy_assert_rejected(
        &mut fixture,
        false,
        superseded,
        "pftl_uniswap_bridge_policy_committee_not_current",
    );
}

#[test]
fn bridge_policy_update_rejects_changed_echo_fields_and_active_handoff() {
    let mut fixture = bridge_policy_fixture();
    let epoch2 = fixture.epoch2.clone();
    fixture.ledger.fastswap_committees.push(epoch2.clone());
    let mut confirmations = bridge_policy_update(&fixture, &fixture.issuer, &epoch2);
    confirmations.minimum_confirmations += 1;
    let mut controller = bridge_policy_update(&fixture, &fixture.issuer, &epoch2);
    controller.handoff_controller_code_hash = "73".repeat(32);
    let mut wrapped = bridge_policy_update(&fixture, &fixture.issuer, &epoch2);
    wrapped.wrapped_navcoin_code_hash = "74".repeat(32);
    for operation in [confirmations, controller, wrapped] {
        bridge_policy_assert_rejected(
            &mut fixture,
            false,
            operation,
            "pftl_uniswap_bridge_policy_echo_mismatch",
        );
    }
    fixture.ledger.pftl_uniswap_routes[0].outstanding_bridge_claims_atoms = 1;
    fixture.ledger.pftl_uniswap_routes[0].authorized_valid_supply_atoms = 1;
    let operation = bridge_policy_update(&fixture, &fixture.issuer, &epoch2);
    bridge_policy_assert_rejected(
        &mut fixture,
        false,
        operation,
        "pftl_uniswap_bridge_policy_handoff_active",
    );
}

#[test]
fn bridge_policy_update_keeps_old_committee_until_final_checkpoint() {
    let mut fixture = bridge_policy_fixture();
    // Validators cannot activate epoch 2 without epoch 1's final checkpoint.
    let mut no_checkpoint = fixture.ledger.clone();
    assert_eq!(
        crate::fastswap_control::register_fastswap_committee(
            &mut no_checkpoint,
            fixture.epoch2.clone(),
            None
        ),
        Err(crate::fastswap_control::FastSwapControlError::MissingFinalCheckpoint)
    );
    // Until then the route's verification authority is still epoch 1.
    let route = fixture
        .ledger
        .pftl_uniswap_route(&fixture.route_id)
        .unwrap();
    let committee = crate::pftl_uniswap_ethereum_verification::committee_for_policy(
        &fixture.genesis,
        &fixture.ledger,
        route.ethereum_verification_policy.as_ref().unwrap(),
    )
    .expect("epoch 1 remains the route committee");
    assert_eq!(committee, &fixture.epoch1);
    // An epoch-2 committee with a pending StopPrepare fence is mid-handoff.
    fixture
        .ledger
        .fastswap_committees
        .push(fixture.epoch2.clone());
    fixture
        .ledger
        .fast_lane_prepare_fences
        .push(postfiat_types::FastLanePrepareFenceV1 {
            committee_epoch: 2,
            policy_epoch: 1,
            finalized_primary_height: 9,
        });
    let operation = bridge_policy_update(&fixture, &fixture.issuer, &fixture.epoch2.clone());
    bridge_policy_assert_rejected(
        &mut fixture,
        false,
        operation.clone(),
        "pftl_uniswap_bridge_policy_committee_not_current",
    );
    fixture.ledger.fast_lane_prepare_fences.clear();
    assert!(bridge_policy_apply(&mut fixture, false, operation).accepted);
    let route = fixture
        .ledger
        .pftl_uniswap_route(&fixture.route_id)
        .unwrap();
    let committee = crate::pftl_uniswap_ethereum_verification::committee_for_policy(
        &fixture.genesis,
        &fixture.ledger,
        route.ethereum_verification_policy.as_ref().unwrap(),
    )
    .expect("epoch 2 is the route committee after the update");
    assert_eq!(committee, &fixture.epoch2);
}

#[test]
fn bridge_policy_update_full_history_replay_reproduces_root() {
    let mut fixture = bridge_policy_fixture();
    fixture
        .ledger
        .fastswap_committees
        .push(fixture.epoch2.clone());
    let base = fixture.ledger.clone();
    let mut history = Vec::new();
    let mut rejected = bridge_policy_update(&fixture, &fixture.reserve, &fixture.epoch2.clone());
    rejected.minimum_confirmations += 1;
    for (by_reserve, operation) in [
        (true, rejected),
        (
            false,
            bridge_policy_update(&fixture, &fixture.issuer, &fixture.epoch2.clone()),
        ),
    ] {
        let (key, signer) = if by_reserve {
            (&fixture.reserve_key, fixture.reserve.clone())
        } else {
            (&fixture.issuer_key, fixture.issuer.clone())
        };
        let transaction = bridge_policy_signed(
            &fixture.genesis,
            &fixture.ledger,
            key,
            &signer,
            PFTL_UNISWAP_ROUTE_BRIDGE_POLICY_UPDATE_TRANSACTION_KIND,
            AssetTransactionOperation::PftlUniswapRouteBridgePolicyUpdate(operation),
        );
        // Round-trip through the wire form so replay uses decoded bytes.
        let transaction: SignedAssetTransaction =
            serde_json::from_slice(&serde_json::to_vec(&transaction).unwrap()).unwrap();
        let receipt =
            execute_asset_transaction(&fixture.genesis, &mut fixture.ledger, &transaction, 10);
        history.push((transaction, receipt));
    }
    assert!(!history[0].1.accepted && history[1].1.accepted);
    let mut replayed = base;
    for (transaction, receipt) in &history {
        assert_eq!(
            &execute_asset_transaction(&fixture.genesis, &mut replayed, transaction, 10),
            receipt
        );
    }
    let root = |ledger: &LedgerState| {
        postfiat_crypto_provider::hash_hex(
            "postfiat.test.bridge-policy-replay-root",
            &serde_json::to_vec(ledger).unwrap(),
        )
    };
    assert_eq!(replayed, fixture.ledger);
    assert_eq!(root(&replayed), root(&fixture.ledger));
    assert_eq!(
        pftl_uniswap_route_state_hash(replayed.pftl_uniswap_route(&fixture.route_id).unwrap()),
        fixture
            .ledger
            .pftl_uniswap_receipts
            .last()
            .unwrap()
            .state_after_hash
    );
}
