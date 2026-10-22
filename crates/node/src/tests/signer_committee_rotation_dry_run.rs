use super::fastpay_payment_safety::{
    commit_fastlane_primary_for_test, copy_fastpay_node_dir, rewrite_fastpay_node_id,
    signed_owned_deposit_for_test,
};
use super::*;

/// FastPay half of the local signer committee rotation dry run
/// (docs/review/signer-committee-rotation-dry-run-20261005.md). Six validators,
/// epoch 1 over the genesis keys, validator-5's key rotated, then the epoch-2
/// record prepared by `fastpay-committee-prepare`, signed by all six current
/// registry keys and paid through with validator-5 signing and validator-4 absent.
#[test]
fn fastpay_signer_committee_rotation_dry_run() {
    let timer = std::time::Instant::now();
    let mut lap = std::time::Instant::now();
    let mut step = |name: &str, detail: String| {
        eprintln!(
            "dry-run | {name} | {detail} | {} ms",
            lap.elapsed().as_millis()
        );
        lap = std::time::Instant::now();
    };
    let root = unique_test_dir("postfiat-signer-committee-rotation-dry-run");
    let source_dir = root.join("validator-0");
    init(InitOptions {
        data_dir: source_dir.clone(),
        chain_id: "postfiat-signer-rotation-dry-run".to_string(),
        node_id: "validator-0".to_string(),
        validator_count: 6,
    })
    .expect("init");
    let store = NodeStore::new(&source_dir);
    let genesis = store.read_genesis().expect("genesis");
    let validators = local_validator_ids(6).expect("validator IDs");
    let genesis_keys =
        read_validator_key_file(&source_dir.join(VALIDATOR_KEYS_FILE)).expect("keys");
    let tip = |store: &NodeStore| store.read_chain_tip().unwrap().height;

    // Epoch 1 over the six genesis keys; new orders through height 10 stands
    // in for the live 10000 (test deposits expire after about 16 blocks).
    let epoch1 = postfiat_types::FastPayRecoveryCommitteeV1::from_public_keys(
        genesis.chain_id.clone(),
        genesis_hash(&genesis),
        genesis.protocol_version,
        1,
        2,
        10,
        genesis_keys
            .validators
            .iter()
            .map(|record| (record.node_id.clone(), record.public_key_hex.clone()))
            .collect(),
    )
    .expect("epoch 1");
    let policy = postfiat_types::FastPayRecoveryPolicyV1 {
        schema: postfiat_types::FASTPAY_RECOVERY_POLICY_SCHEMA_V1.to_string(),
        activation_height: 2,
        max_validity_blocks: 4,
        max_recovery_blocks: 4,
    };
    let payload_file = root.join("epoch1-payload.json");
    let bootstrap_file = root.join("epoch1-bootstrap.json");
    atomic_write(
        &payload_file,
        serde_json::to_vec(&postfiat_types::FastPayRecoveryGovernancePayloadV1 {
            policy: policy.clone(),
            committee: epoch1.clone(),
        })
        .unwrap(),
    )
    .unwrap();
    create_fastpay_recovery_governance_bootstrap(FastPayRecoveryGovernanceBootstrapOptions {
        data_dir: source_dir.clone(),
        validators: validators.clone(),
        support: validators.clone(),
        veto_until_height: 0,
        payload_file,
        amendment_file: root.join("epoch1-amendment.json"),
        batch_file: bootstrap_file.clone(),
    })
    .expect("epoch 1 bootstrap");
    let receipts = apply_unsigned_governance_fixture_for_test(ApplyBatchOptions {
        data_dir: source_dir.clone(),
        batch_file: bootstrap_file,
        certificate_file: None,
    })
    .expect("apply epoch 1");
    assert!(receipts[0].accepted, "{receipts:?}");
    step(
        "epoch 1 bootstrap",
        format!(
            "height {}; {} ({}); quorum {}",
            tip(&store),
            receipts[0].code,
            epoch1.registry_root,
            epoch1.quorum
        ),
    );

    // Governed rotation of validator-5's validator key (the live rotation).
    let registry_path = source_dir.join(VALIDATOR_REGISTRY_FILE);
    let registry = read_validator_registry_file(&registry_path).unwrap();
    let mut rotated = registry.clone();
    let replacement = ml_dsa_65_keygen_from_seed(&[95; 32]);
    let previous = rotated
        .validators
        .iter_mut()
        .find(|v| v.node_id == "validator-5")
        .unwrap();
    let old_entry = ValidatorRegistryEntry {
        node_id: previous.node_id.clone(),
        algorithm_id: previous.algorithm_id.clone(),
        public_key_hex: previous.public_key_hex.clone(),
        active: true,
    };
    previous.public_key_hex = bytes_to_hex(&replacement.public_key);
    let new_entry = ValidatorRegistryEntry {
        public_key_hex: previous.public_key_hex.clone(),
        ..old_entry.clone()
    };
    let previous_entry_file = root.join("previous-entry.json");
    let new_entry_file = root.join("replacement-entry.json");
    atomic_write(
        &previous_entry_file,
        serde_json::to_vec(&old_entry).unwrap(),
    )
    .unwrap();
    atomic_write(&new_entry_file, serde_json::to_vec(&new_entry).unwrap()).unwrap();
    let update_file = root.join("rotation-update.json");
    create_validator_registry_update(ValidatorRegistryUpdateOptions {
        data_dir: source_dir.clone(),
        validators: validators.clone(),
        support: validators.clone(),
        activation_height: tip(&store) + 1,
        previous_registry_root: validator_registry_root(&registry, &validators).unwrap(),
        new_registry_root: validator_registry_root(&rotated, &validators).unwrap(),
        previous_validators: validators.clone(),
        new_validators: validators.clone(),
        operation: VALIDATOR_REGISTRY_OP_ROTATE_KEY.to_string(),
        subject_node_id: "validator-5".to_string(),
        previous_record_file: Some(previous_entry_file),
        new_record_file: Some(new_entry_file),
        update_file: update_file.clone(),
    })
    .expect("rotation update");
    let batch_file = root.join("rotation-batch.json");
    create_governance_batch(GovernanceBatchOptions {
        data_dir: source_dir.clone(),
        amendment_file: None,
        registry_update_file: Some(update_file),
        batch_file: batch_file.clone(),
    })
    .unwrap();
    let receipts = apply_unsigned_governance_fixture_for_test(ApplyBatchOptions {
        data_dir: source_dir.clone(),
        batch_file,
        certificate_file: None,
    })
    .expect("commit rotation");
    assert!(
        receipts.iter().any(|receipt| receipt.accepted),
        "{receipts:?}"
    );
    let mut current_keys = genesis_keys.clone();
    let member = current_keys
        .validators
        .iter_mut()
        .find(|v| v.node_id == "validator-5")
        .unwrap();
    member.public_key_hex = bytes_to_hex(&replacement.public_key);
    member.private_key_hex = bytes_to_hex(&replacement.private_key);
    write_validator_key_file(&source_dir.join(VALIDATOR_KEYS_FILE), &current_keys).unwrap();
    step(
        "validator-5 key rotated",
        format!("height {}; epoch 1 keeps the stale key", tip(&store)),
    );

    // Owner funds for the payment.
    let owner = postfiat_crypto_provider::ml_dsa_65_keygen().expect("owner");
    let owner_pubkey_hex = bytes_to_hex(&owner.public_key);
    let faucet = read_transfer_key_file(&source_dir, None).expect("faucet key");
    let mut sequence = 1;
    let deposit = commit_fastlane_primary_for_test(
        &source_dir,
        "payer-deposit",
        signed_owned_deposit_for_test(
            &genesis,
            &faucet,
            owner.public_key.clone(),
            sequence,
            100,
            [95; 32],
        ),
    );
    assert!(deposit.accepted, "{deposit:?}");

    // `fastpay-committee-prepare`: the start height is fixed by epoch 1.
    let refused = fastpay_committee_prepare(FastPayCommitteePrepareOptions {
        data_dir: source_dir.clone(),
        registry_file: None,
        valid_from_height: Some(30),
        new_orders_through_height: None,
    })
    .expect_err("only previous new_orders_through + 1 is accepted");
    let prepared = fastpay_committee_prepare(FastPayCommitteePrepareOptions {
        data_dir: source_dir.clone(),
        registry_file: None,
        valid_from_height: None,
        new_orders_through_height: None,
    })
    .expect("prepare epoch 2");
    let payload: postfiat_types::FastPayRecoveryGovernancePayloadV1 =
        serde_json::from_value(prepared["payload"].clone()).unwrap();
    let epoch2 = payload.committee.clone();
    assert_eq!(
        (
            epoch2.committee_epoch,
            epoch2.valid_from_height,
            epoch2.quorum
        ),
        (2, 11, 5)
    );
    assert_eq!(
        prepared["replaced_member_keys"],
        serde_json::json!(["validator-5"])
    );
    step(
        "fastpay-committee-prepare",
        format!(
            "height {}; valid_from 11, through {}; replaced {}; signers required {}; valid_from 30: {}",
            tip(&store),
            epoch2.new_orders_through_height,
            prepared["replaced_member_keys"],
            prepared["governance_signers_required"],
            refused
        ),
    );

    // Install: all six validators sign with their current registry keys.
    let payload_file = root.join("epoch2-payload.json");
    let amendment_file = root.join("epoch2-amendment.unsigned.json");
    let signed_amendment_file = root.join("epoch2-amendment.signed.json");
    let batch_file = root.join("epoch2-batch.json");
    atomic_write(&payload_file, serde_json::to_vec(&payload).unwrap()).unwrap();
    create_fastpay_recovery_governance_bootstrap(FastPayRecoveryGovernanceBootstrapOptions {
        data_dir: source_dir.clone(),
        validators: validators.clone(),
        support: validators.clone(),
        veto_until_height: 0,
        payload_file: payload_file.clone(),
        amendment_file: amendment_file.clone(),
        batch_file: root.join("epoch2-batch.unsigned.json"),
    })
    .expect("unsigned epoch 2 batch");
    let slot = tip(&store) + 1;
    let key_files = write_split_validator_key_files(&root, &current_keys);
    let authorizations = key_files
        .iter()
        .map(|(validator, key_file)| {
            let authorization_file = root.join(format!("{validator}.epoch2-authorization.json"));
            sign_governance_amendment_authorization(GovernanceAuthorizationSignOptions {
                data_dir: source_dir.clone(),
                amendment_file: amendment_file.clone(),
                validator: validator.clone(),
                validator_key_file: key_file.clone(),
                proposal_slot: slot,
                expires_at_height: slot + 6,
                authorization_file: authorization_file.clone(),
            })
            .expect("sign epoch 2 authorization");
            authorization_file
        })
        .collect::<Vec<_>>();
    let five_of_six = assemble_signed_governance_amendment(GovernanceAmendmentAssembleOptions {
        data_dir: source_dir.clone(),
        amendment_file: amendment_file.clone(),
        authorization_files: authorizations[..5].to_vec(),
        proposal_slot: slot,
        output_file: root.join("epoch2-amendment.five.json"),
    });
    assert!(five_of_six.is_err(), "the record needs all six validators");
    let stale_key_file = root.join("validator-5.stale.json");
    write_validator_key_file(
        &stale_key_file,
        &ValidatorKeyFile {
            validators: vec![genesis_keys.validators[5].clone()],
        },
    )
    .unwrap();
    let stale = sign_governance_amendment_authorization(GovernanceAuthorizationSignOptions {
        data_dir: source_dir.clone(),
        amendment_file: amendment_file.clone(),
        validator: "validator-5".to_string(),
        validator_key_file: stale_key_file,
        proposal_slot: slot,
        expires_at_height: slot + 6,
        authorization_file: root.join("validator-5.stale-authorization.json"),
    });
    assert!(stale.is_err(), "the stale genesis key cannot sign");
    assemble_signed_governance_amendment(GovernanceAmendmentAssembleOptions {
        data_dir: source_dir.clone(),
        amendment_file,
        authorization_files: authorizations,
        proposal_slot: slot,
        output_file: signed_amendment_file.clone(),
    })
    .expect("assemble six authorizations");
    assemble_signed_fastpay_recovery_governance_bootstrap(
        SignedFastPayRecoveryGovernanceBootstrapOptions {
            data_dir: source_dir.clone(),
            payload_file,
            signed_amendment_file,
            proposal_slot: slot,
            batch_file: batch_file.clone(),
        },
    )
    .expect("assemble signed epoch 2 batch");
    let receipts = apply_governance_batch(ApplyBatchOptions {
        data_dir: source_dir.clone(),
        batch_file,
        certificate_file: None,
    })
    .expect("apply signed epoch 2 batch");
    assert!(receipts[0].accepted, "{receipts:?}");
    assert_eq!(receipts[0].code, "fastpay_recovery_committee_rotated");
    let installed_at = tip(&store);
    assert!(installed_at < 11);
    step(
        "epoch 2 installed",
        format!(
            "height {installed_at}; {}; 5 of 6 authorizations: {}; stale v5 key: {}",
            receipts[0].code,
            five_of_six.unwrap_err(),
            stale.unwrap_err()
        ),
    );

    // Advance to the epoch-2 start height.
    while tip(&store) < epoch2.valid_from_height {
        sequence += 1;
        let filler = commit_fastlane_primary_for_test(
            &source_dir,
            &format!("filler-{sequence}"),
            signed_owned_deposit_for_test(
                &genesis,
                &faucet,
                owner.public_key.clone(),
                sequence,
                1,
                [sequence as u8; 32],
            ),
        );
        assert!(filler.accepted, "{filler:?}");
    }
    let tip_height = tip(&store);
    step("advanced to epoch 2", format!("height {tip_height}"));
    let input = store
        .read_ledger()
        .unwrap()
        .owned_objects
        .into_iter()
        .find(|object| object.owner_pubkey_hex == owner_pubkey_hex && object.value == 100)
        .expect("payer object");
    let mut data_dirs = vec![source_dir.clone()];
    for index in 1..6 {
        let data_dir = root.join(format!("validator-{index}"));
        copy_fastpay_node_dir(&source_dir, &data_dir);
        rewrite_fastpay_node_id(&data_dir, &format!("validator-{index}"));
        data_dirs.push(data_dir);
    }
    let options = |index: usize| NodeOptions {
        data_dir: data_dirs[index].clone(),
    };

    // The payment: validators 0-3 and the rotated validator-5; validator-4 absent.
    let mut order = postfiat_types::OwnedTransferOrderV3 {
        domain: epoch2.certificate_domain(),
        recovery: postfiat_types::FastPayOrderRecoveryV1 {
            schema: postfiat_types::FASTPAY_ORDER_RECOVERY_SCHEMA_V1.to_string(),
            committee_epoch: epoch2.committee_epoch,
            lock_id: "00".repeat(48),
            valid_from_height: tip_height,
            expires_at_height: tip_height + 4,
            recovery_closes_at_height: tip_height + 8,
        },
        inputs: vec![postfiat_types::OwnedObjectRef {
            id: input.id.clone(),
            version: input.version,
        }],
        outputs: vec![postfiat_types::OwnedOutputSpec {
            owner_pubkey_hex: "rotation-dry-run-recipient".to_string(),
            value: 99,
            asset: input.asset.clone(),
        }],
        fee: 1,
        nonce: 1,
        memos: Vec::new(),
    };
    order.recovery.lock_id = postfiat_types::fastpay_transfer_lock_id_v1(&order);
    let owner_signature = ml_dsa_65_sign_with_context(
        &owner.private_key,
        &postfiat_execution::owned_transfer_v3_signing_bytes(&order),
        postfiat_execution::OWNED_TRANSFER_CONTEXT_V3,
    )
    .unwrap();
    let signed = postfiat_types::SignedOwnedTransferOrderV3 {
        order: order.clone(),
        owner_pubkey_hex: owner_pubkey_hex.clone(),
        owner_signature_hex: bytes_to_hex(&owner_signature),
    };
    let signed_json = serde_json::to_string(&signed).unwrap();
    let signers = [0usize, 1, 2, 3, 5];
    let votes = signers
        .iter()
        .map(|&index| {
            serde_json::from_str::<postfiat_types::OwnedTransferVote>(
                &owned_sign_v3(options(index), &signed_json, &validators[index]).expect("vote"),
            )
            .unwrap()
        })
        .collect::<Vec<_>>();
    let certificate = serde_json::to_string(&postfiat_types::OwnedTransferCertificateV3 {
        order,
        owner_pubkey_hex,
        owner_signature_hex: signed.owner_signature_hex,
        votes,
    })
    .unwrap();
    for &index in &signers {
        let ack: postfiat_types::FastPayApplyAckV1 = serde_json::from_str(
            &owned_apply_v3(options(index), &certificate, &validators[index]).expect("apply"),
        )
        .expect("signed ack");
        assert!(postfiat_execution::verify_fastpay_apply_ack_v1(
            &ack,
            &current_keys.validators[index].public_key_hex
        ));
    }
    step(
        "FastPay payment under epoch 2",
        format!("height {tip_height}; certified and applied by 0,1,2,3,5 (validator-4 absent)"),
    );
    eprintln!("dry-run | total | {} ms", timer.elapsed().as_millis());
    std::fs::remove_dir_all(root).unwrap();
}
