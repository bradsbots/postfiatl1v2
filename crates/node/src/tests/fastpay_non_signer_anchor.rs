use super::fastpay_payment_safety::{
    commit_fastlane_primary_for_test, copy_fastpay_node_dir, rewrite_fastpay_node_id,
    signed_owned_deposit_for_test,
};
use super::*;

/// Validator-5's key is rotated after the FastPay committee was recorded, so it
/// is a registered validator that cannot sign. A FastPay payment is certified by
/// validators 0-4 and the next height is validator-5's view-0 turn.
#[test]
fn fastpay_non_signer_view_zero_proposer_anchors_held_effect() {
    let root = unique_test_dir("postfiat-fastpay-non-signer-anchor");
    let source_dir = root.join("validator-0");
    init(InitOptions {
        data_dir: source_dir.clone(),
        chain_id: "postfiat-fastpay-non-signer-anchor".to_string(),
        node_id: "validator-0".to_string(),
        validator_count: 6,
    })
    .expect("init");
    let source_store = NodeStore::new(&source_dir);
    let genesis = source_store.read_genesis().expect("genesis");
    let validators = local_validator_ids(6).expect("validator IDs");
    let validator_keys =
        read_validator_key_file(&source_dir.join(VALIDATOR_KEYS_FILE)).expect("keys");
    let committee = postfiat_types::FastPayRecoveryCommitteeV1::from_public_keys(
        genesis.chain_id.clone(),
        genesis_hash(&genesis),
        genesis.protocol_version,
        1,
        2,
        100,
        validator_keys
            .validators
            .iter()
            .map(|record| (record.node_id.clone(), record.public_key_hex.clone()))
            .collect(),
    )
    .expect("committee");
    let payload = postfiat_types::FastPayRecoveryGovernancePayloadV1 {
        policy: postfiat_types::FastPayRecoveryPolicyV1 {
            schema: postfiat_types::FASTPAY_RECOVERY_POLICY_SCHEMA_V1.to_string(),
            activation_height: 2,
            max_validity_blocks: 4,
            max_recovery_blocks: 4,
        },
        committee: committee.clone(),
    };
    let payload_file = root.join("fastpay-policy.json");
    let bootstrap_file = root.join("fastpay-bootstrap.json");
    atomic_write(&payload_file, serde_json::to_vec(&payload).unwrap()).unwrap();
    create_fastpay_recovery_governance_bootstrap(FastPayRecoveryGovernanceBootstrapOptions {
        data_dir: source_dir.clone(),
        validators: validators.clone(),
        support: validators.clone(),
        veto_until_height: 0,
        payload_file,
        amendment_file: root.join("fastpay-amendment.json"),
        batch_file: bootstrap_file.clone(),
    })
    .expect("bootstrap");
    let receipts = apply_unsigned_governance_fixture_for_test(ApplyBatchOptions {
        data_dir: source_dir.clone(),
        batch_file: bootstrap_file,
        certificate_file: None,
    })
    .expect("apply bootstrap");
    assert!(receipts[0].accepted, "{receipts:?}");

    // Governed rotation of validator-5's key; the FastPay committee keeps the old key.
    let registry_path = source_dir.join(VALIDATOR_REGISTRY_FILE);
    let registry = read_validator_registry_file(&registry_path).unwrap();
    let mut rotated = registry.clone();
    let replacement = ml_dsa_65_keygen_from_seed(&[94; 32]);
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
        activation_height: 2,
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
    let mut keys = validator_keys.clone();
    let member = keys
        .validators
        .iter_mut()
        .find(|v| v.node_id == "validator-5")
        .unwrap();
    member.public_key_hex = bytes_to_hex(&replacement.public_key);
    member.private_key_hex = bytes_to_hex(&replacement.private_key);
    write_validator_key_file(&source_dir.join(VALIDATOR_KEYS_FILE), &keys).unwrap();

    // Fund the payer, then fill until the next height is validator-5's view-0 turn.
    let owner = postfiat_crypto_provider::ml_dsa_65_keygen().expect("owner");
    let owner_pubkey_hex = bytes_to_hex(&owner.public_key);
    let source = read_transfer_key_file(&source_dir, None).expect("faucet key");
    let mut sequence = 1;
    let deposit = commit_fastlane_primary_for_test(
        &source_dir,
        "payer-deposit",
        signed_owned_deposit_for_test(
            &genesis,
            &source,
            owner.public_key.clone(),
            sequence,
            100,
            [95; 32],
        ),
    );
    assert!(deposit.accepted, "{deposit:?}");
    let leader = |height: u64| {
        postfiat_ordering_fast::leader_for_view(&validators, height, 0).expect("leader")
    };
    while leader(source_store.read_chain_tip().unwrap().height + 1) != "validator-5" {
        sequence += 1;
        let filler = commit_fastlane_primary_for_test(
            &source_dir,
            &format!("filler-{sequence}"),
            signed_owned_deposit_for_test(
                &genesis,
                &source,
                owner.public_key.clone(),
                sequence,
                1,
                [sequence as u8; 32],
            ),
        );
        assert!(filler.accepted, "{filler:?}");
    }
    let tip_height = source_store.read_chain_tip().unwrap().height;
    let input = source_store
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

    // The FastPay payment, certified and applied by validators 0-4.
    let mut order = postfiat_types::OwnedTransferOrderV3 {
        domain: committee.certificate_domain(),
        recovery: postfiat_types::FastPayOrderRecoveryV1 {
            schema: postfiat_types::FASTPAY_ORDER_RECOVERY_SCHEMA_V1.to_string(),
            committee_epoch: committee.committee_epoch,
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
            owner_pubkey_hex: "non-signer-anchor-recipient".to_string(),
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
    let votes = (0..committee.quorum)
        .map(|index| {
            serde_json::from_str::<postfiat_types::OwnedTransferVote>(
                &owned_sign_v3(options(index), &signed_json, &validators[index]).expect("vote"),
            )
            .unwrap()
        })
        .collect::<Vec<_>>();
    assert_eq!(votes.len(), 5);
    assert!(owned_sign_v3(options(5), &signed_json, "validator-5").is_err());
    let certificate = serde_json::to_value(postfiat_types::OwnedTransferCertificateV3 {
        order,
        owner_pubkey_hex: owner_pubkey_hex.clone(),
        owner_signature_hex: signed.owner_signature_hex,
        votes,
    })
    .unwrap();
    let certificate_json = certificate.to_string();
    for (index, validator) in validators.iter().enumerate().take(committee.quorum) {
        let ack: postfiat_types::FastPayApplyAckV1 = serde_json::from_str(
            &owned_apply_v3(options(index), &certificate_json, validator).expect("apply"),
        )
        .expect("signed ack");
        assert!(postfiat_execution::verify_fastpay_apply_ack_v1(
            &ack,
            &validator_keys.validators[index].public_key_hex
        ));
    }

    // Negative: validator-5 never holds an effect from an invalid certificate.
    let sixth_store = NodeStore::new(&data_dirs[5]);
    let sixth_before = sixth_store.read_ledger().unwrap();
    for attack in ["four-votes", "duplicate", "forged", "cross-domain", "owner"] {
        let mut invalid = certificate.clone();
        match attack {
            "four-votes" => {
                invalid["votes"].as_array_mut().unwrap().pop();
            }
            "duplicate" => invalid["votes"][4] = invalid["votes"][0].clone(),
            "forged" => invalid["votes"][4]["signature_hex"] = "00".into(),
            "cross-domain" => invalid["order"]["domain"]["chain_id"] = "other-chain".into(),
            _ => invalid["owner_signature_hex"] = "00".into(),
        }
        assert!(
            owned_apply_v3(options(5), &invalid.to_string(), "validator-5").is_err(),
            "{attack}"
        );
        assert_eq!(sixth_store.read_ledger().unwrap(), sixth_before, "{attack}");
        assert!(
            !data_dirs[5].join(FASTPAY_SPECULATIVE_JOURNAL_FILE).exists(),
            "{attack}"
        );
    }
    assert!(owned_apply_v3(options(5), &certificate_json, "absent-validator").is_err());
    assert!(!data_dirs[5].join(FASTPAY_SPECULATIVE_JOURNAL_FILE).exists());

    // Validator-5 holds the verified effect without signing anything. Keep the
    // failure (old behaviour) so the proposal and votes below show the stall.
    let held = owned_apply_v3(options(5), &certificate_json, "validator-5");
    let expected_effects = fastpay_pre_state_effects_for_next_block(
        &NodeStore::new(&data_dirs[0]),
        &read_fastpay_ledger(&NodeStore::new(&data_dirs[0])).unwrap(),
    )
    .unwrap();
    assert_eq!(expected_effects.len(), 1);
    if let Ok(held) = &held {
        let receipt: serde_json::Value = serde_json::from_str(held).unwrap();
        assert_eq!(receipt["schema"], FASTPAY_HELD_EFFECT_SCHEMA_V1);
        assert_eq!(receipt["signed"], false);
        assert_eq!(receipt["lock_id"], expected_effects[0].lock_id.as_str());
        assert!(receipt.get("signature_hex").is_none());
        assert!(serde_json::from_str::<postfiat_types::FastPayApplyAckV1>(held).is_err());
        let journal = std::fs::read(data_dirs[5].join(FASTPAY_SPECULATIVE_JOURNAL_FILE)).unwrap();
        assert_eq!(
            &owned_apply_v3(options(5), &certificate_json, "validator-5").expect("idempotent"),
            held
        );
        assert_eq!(
            std::fs::read(data_dirs[5].join(FASTPAY_SPECULATIVE_JOURNAL_FILE)).unwrap(),
            journal
        );
        // Restart safety: a fresh store re-reads the held effect from disk.
        status(options(5)).expect("restarted status");
        let restarted = NodeStore::new(&data_dirs[5]);
        assert_eq!(
            fastpay_pre_state_effects_for_next_block(
                &restarted,
                &read_fastpay_ledger(&restarted).unwrap()
            )
            .unwrap(),
            expected_effects
        );
    }

    // Validator-5 proposes the next height at view 0.
    let anchor = signed_owned_deposit_for_test(
        &genesis,
        &source,
        owner.public_key.clone(),
        sequence + 1,
        10,
        [96; 32],
    );
    admit_fastlane_primary_to_mempool(&data_dirs[5], anchor).expect("admit anchor");
    let batch_file = root.join("anchor-batch.json");
    create_mempool_batch(MempoolBatchOptions {
        data_dir: data_dirs[5].clone(),
        batch_file: batch_file.clone(),
        max_transactions: 1,
    })
    .expect("anchor batch");
    let proposal_file = root.join("anchor-proposal.json");
    let proposal = propose_batch(BatchProposalOptions {
        data_dir: data_dirs[5].clone(),
        verify_block_log: true,
        batch_kind: Some(BATCH_KIND_TRANSPARENT.to_string()),
        batch_file: batch_file.clone(),
        proposal_file: proposal_file.clone(),
        view: Some(0),
        timeout_certificate_file: None,
        key_file: None,
        validator_id: None,
    })
    .expect("validator-5 proposal");
    assert_eq!(proposal.proposer, "validator-5");
    assert_eq!(proposal.view, 0);

    let mut vote_files = Vec::new();
    let mut refusals = Vec::new();
    for (index, validator) in validators.iter().enumerate() {
        let vote_file = root.join(format!("{validator}.vote.json"));
        match create_block_vote(BlockVoteOptions {
            data_dir: data_dirs[index].clone(),
            verify_block_log: true,
            key_file: data_dirs[index].join(VALIDATOR_KEYS_FILE),
            validator_id: Some(validator.clone()),
            batch_file: Some(batch_file.clone()),
            proposal_file: Some(proposal_file.clone()),
            timeout_certificate_file: None,
            block_height: Some(proposal.block_height),
            vote_file: vote_file.clone(),
        }) {
            Ok(_) => vote_files.push(vote_file),
            Err(error) => refusals.push(format!("{validator}: {error}")),
        }
    }
    assert!(
        refusals.is_empty(),
        "view-0 proposal by validator-5 refused (held={}): {refusals:?}",
        held.as_ref()
            .map_or_else(|error| error.to_string(), |_| "ok".into())
    );
    assert_eq!(proposal.fastpay_pre_state_effects, expected_effects);

    let certificate_file = root.join("anchor-certificate.json");
    let block_certificate = aggregate_verified_block_certificate(BlockCertificateOptions {
        data_dir: data_dirs[5].clone(),
        verify_block_log: true,
        batch_file: Some(batch_file.clone()),
        proposal_file: Some(proposal_file),
        timeout_certificate_file: None,
        block_height: Some(proposal.block_height),
        vote_files,
        certificate_file: certificate_file.clone(),
    })
    .expect("view-0 block certificate");
    assert_eq!(
        block_certificate
            .as_block_certificate_file()
            .fastpay_pre_state_effects,
        expected_effects
    );
    for data_dir in &data_dirs {
        let receipts = apply_batch(ApplyBatchOptions {
            data_dir: data_dir.clone(),
            batch_file: batch_file.clone(),
            certificate_file: Some(certificate_file.clone()),
        })
        .expect("apply anchor block");
        assert!(receipts[0].accepted, "{receipts:?}");
        verify_blocks(NodeOptions {
            data_dir: data_dir.clone(),
        })
        .expect("replay anchored history");
        let store = NodeStore::new(data_dir);
        assert!(
            fastpay_pre_state_effects_for_next_block(&store, &read_fastpay_ledger(&store).unwrap())
                .unwrap()
                .is_empty(),
            "effect anchored exactly once"
        );
    }
    let statuses = (0..6)
        .map(|index| status(options(index)).expect("status"))
        .collect::<Vec<_>>();
    assert!(statuses.windows(2).all(|pair| {
        pair[0].block_height == pair[1].block_height
            && pair[0].block_tip_hash == pair[1].block_tip_hash
            && pair[0].state_root == pair[1].state_root
    }));
    assert_eq!(statuses[5].block_height, proposal.block_height);
    let ledgers = (0..6)
        .map(|index| NodeStore::new(&data_dirs[index]).read_ledger().unwrap())
        .collect::<Vec<_>>();
    assert!(ledgers.windows(2).all(|pair| pair[0] == pair[1]));
    assert!(ledgers[5]
        .owned_objects
        .iter()
        .any(
            |object| object.owner_pubkey_hex == "non-signer-anchor-recipient" && object.value == 99
        ));

    // A late replay after anchoring stays idempotent and cannot re-anchor.
    owned_apply_v3(options(5), &certificate_json, "validator-5").expect("post-anchor replay");
    let store = NodeStore::new(&data_dirs[5]);
    assert!(fastpay_pre_state_effects_for_next_block(
        &store,
        &read_fastpay_ledger(&store).unwrap()
    )
    .unwrap()
    .is_empty());
    std::fs::remove_dir_all(root).unwrap();
}
