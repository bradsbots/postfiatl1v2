//! Read-only preparation of the next FastPay recovery committee record and
//! its unsigned governance batch. Nothing here signs, writes or reads a key.

use super::*;

pub const FASTPAY_COMMITTEE_PREPARE_SCHEMA_V1: &str = "postfiat-fastpay-committee-prepare-v1";
const PREPARED_COMMITTEE_SIZE: usize = 6;
const PREPARED_COMMITTEE_QUORUM: usize = 5;

fn refused(message: impl std::fmt::Display) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, message.to_string())
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FastPayCommitteePrepareOptions {
    pub data_dir: PathBuf,
    /// Optional registry snapshot supplying member keys; every key must still
    /// match the node's current `validator_registry.json`.
    pub registry_file: Option<PathBuf>,
    pub valid_from_height: Option<u64>,
    pub new_orders_through_height: Option<u64>,
}

pub struct FastPayCommitteeInputs<'a> {
    pub ledger: &'a LedgerState,
    pub chain_tip_height: u64,
    pub active_validators: &'a [String],
    /// `(validator_id, public_key_hex)` from the node's current registry.
    pub registered_keys: &'a [(String, String)],
    pub member_keys: &'a [(String, String)],
    pub requested_valid_from_height: Option<u64>,
    pub new_orders_through_height: Option<u64>,
}

#[derive(Debug)]
pub struct PreparedFastPayCommittee {
    pub previous: postfiat_types::FastPayRecoveryCommitteeV1,
    pub earliest_valid_from_height: u64,
    pub payload: postfiat_types::FastPayRecoveryGovernancePayloadV1,
}

/// Applies the rotation rules of `execute_fastpay_recovery_governance_update_v1`
/// before anything is built, so a refused record never reaches a signer.
pub fn prepare_next_fastpay_committee(
    inputs: FastPayCommitteeInputs<'_>,
) -> Result<PreparedFastPayCommittee, String> {
    let policy = inputs.ledger.fastpay_recovery_policy.clone().ok_or(
        "no FastPay recovery policy is installed; use fastpay-recovery-governance-bootstrap",
    )?;
    let previous = inputs
        .ledger
        .fastpay_recovery_committees
        .last()
        .cloned()
        .ok_or(
            "no FastPay recovery committee is installed; use fastpay-recovery-governance-bootstrap",
        )?;
    previous.validate()?;

    // A rotation starts exactly one block after the previous epoch stops
    // admitting new orders, and only from a block below that height.
    let earliest = previous
        .new_orders_through_height
        .checked_add(1)
        .ok_or("FastPay committee admission height overflow")?;
    let valid_from = inputs
        .requested_valid_from_height
        .map_or(earliest, |requested| requested.max(earliest));
    if valid_from != earliest {
        return Err(format!(
            "valid_from_height {valid_from} refused: committee epoch {} must start at exactly \
             {earliest} (previous new_orders_through_height + 1)",
            previous.committee_epoch + 1
        ));
    }
    let next_block = inputs.chain_tip_height.saturating_add(1);
    if valid_from <= next_block {
        return Err(format!(
            "rotation window closed: the next block is {next_block} and valid_from_height \
             {valid_from} must be above the installing block"
        ));
    }
    let new_orders_through = match inputs.new_orders_through_height {
        Some(height) => height,
        None => valid_from
            .checked_add(previous.new_orders_through_height - previous.valid_from_height)
            .ok_or("new_orders_through_height overflow")?,
    };

    let mut active = inputs.active_validators.to_vec();
    active.sort();
    let mut members = inputs.member_keys.to_vec();
    members.sort();
    if members.iter().map(|(id, _)| id).ne(active.iter()) {
        return Err("committee members must be exactly the active validators".to_string());
    }
    for member in &members {
        if !inputs.registered_keys.contains(member) {
            return Err(format!(
                "{} key is not its currently registered validator key (stale or unregistered)",
                member.0
            ));
        }
    }

    let committee = postfiat_types::FastPayRecoveryCommitteeV1::from_public_keys(
        previous.chain_id.clone(),
        previous.genesis_hash.clone(),
        previous.protocol_version,
        previous
            .committee_epoch
            .checked_add(1)
            .ok_or("FastPay committee epoch overflow")?,
        valid_from,
        new_orders_through,
        members,
    )?;
    if committee.validators.len() != PREPARED_COMMITTEE_SIZE
        || committee.quorum != PREPARED_COMMITTEE_QUORUM
    {
        return Err(format!(
            "committee quorum is {} of {}; this command prepares only 5 of 6",
            committee.quorum,
            committee.validators.len()
        ));
    }
    if inputs
        .ledger
        .fastpay_recovery_committees
        .iter()
        .any(|existing| existing.registry_root == committee.registry_root)
    {
        return Err("committee registry_root duplicates an installed committee".to_string());
    }
    let payload = postfiat_types::FastPayRecoveryGovernancePayloadV1 { policy, committee };
    payload.payload_bytes()?;
    Ok(PreparedFastPayCommittee {
        previous,
        earliest_valid_from_height: earliest,
        payload,
    })
}

/// Reads a node data directory and prints-ready JSON: the record, its payload
/// and the unsigned governance batch, dry-run against the next block.
pub fn fastpay_committee_prepare(
    options: FastPayCommitteePrepareOptions,
) -> io::Result<serde_json::Value> {
    let store = NodeStore::new(&options.data_dir);
    let genesis = store.read_genesis()?;
    let governance = store.read_governance()?;
    let ledger = store.read_ledger()?;
    let tip = read_chain_tip_or_reconstruct_for_genesis_read_only(&store, &genesis)?;
    let active = active_validator_ids(&governance)?;
    let registered = load_validator_pubkeys(&options.data_dir)?;
    let members = match &options.registry_file {
        Some(path) => read_validator_registry_file(path)?
            .validators
            .into_iter()
            .filter(|record| active.contains(&record.node_id))
            .map(|record| {
                if record.algorithm_id != ML_DSA_65_ALGORITHM {
                    return Err(refused(format!(
                        "{} registry key is not ML-DSA-65",
                        record.node_id
                    )));
                }
                Ok((record.node_id, record.public_key_hex))
            })
            .collect::<io::Result<Vec<_>>>()?,
        None => registered
            .iter()
            .filter(|(id, _)| active.contains(id))
            .cloned()
            .collect(),
    };
    let prepared = prepare_next_fastpay_committee(FastPayCommitteeInputs {
        ledger: &ledger,
        chain_tip_height: tip.height,
        active_validators: &active,
        registered_keys: &registered,
        member_keys: &members,
        requested_valid_from_height: options.valid_from_height,
        new_orders_through_height: options.new_orders_through_height,
    })
    .map_err(refused)?;
    let record = &prepared.payload.committee;
    if record.chain_id != genesis.chain_id
        || record.genesis_hash != genesis_hash(&genesis)
        || record.protocol_version != genesis.protocol_version
    {
        return Err(refused(
            "installed FastPay committee domain does not match genesis",
        ));
    }
    let batch = unsigned_fastpay_recovery_governance_batch(
        &genesis,
        prepared.payload.clone(),
        active.clone(),
        active,
        0,
    )?;
    let bootstrap = &batch.fastpay_recovery_bootstraps[0];
    let mut dry_run = ledger.clone();
    match postfiat_execution::execute_fastpay_recovery_governance_update_v1(
        &mut dry_run,
        bootstrap,
        tip.height.saturating_add(1),
    )
    .map_err(refused)?
    {
        postfiat_execution::FastPayRecoveryGovernanceOutcomeV1::CommitteeRotated => {}
        other => return Err(refused(format!("unexpected dry-run outcome {other:?}"))),
    }
    let replaced: Vec<&str> = record
        .validators
        .iter()
        .filter(|member| !prepared.previous.validators.contains(member))
        .map(|member| member.validator_id.as_str())
        .collect();
    Ok(serde_json::json!({
        "schema": FASTPAY_COMMITTEE_PREPARE_SCHEMA_V1,
        "signed": false,
        "chain_tip_height": tip.height,
        "previous_committee": {
            "committee_epoch": prepared.previous.committee_epoch,
            "valid_from_height": prepared.previous.valid_from_height,
            "new_orders_through_height": prepared.previous.new_orders_through_height,
            "registry_root": prepared.previous.registry_root,
        },
        "earliest_valid_from_height": prepared.earliest_valid_from_height,
        "replaced_member_keys": replaced,
        "governance_signers_required": bootstrap.amendment.quorum,
        "record": record,
        "payload": prepared.payload,
        "unsigned_transaction": batch,
    }))
}

#[cfg(test)]
mod tests {
    use super::*;

    const CHAIN: &str = "fastpay-prepare-fixture";

    fn key(seed: u8) -> String {
        bytes_to_hex(&ml_dsa_65_keygen_from_seed(&[seed; 32]).public_key)
    }

    /// Validators 0-5 with current keys; validator-5 was rotated after epoch 1.
    fn fixture() -> (LedgerState, Vec<String>, Vec<(String, String)>, String) {
        let ids: Vec<String> = (0..6).map(|index| format!("validator-{index}")).collect();
        let registered: Vec<(String, String)> = ids
            .iter()
            .enumerate()
            .map(|(index, id)| (id.clone(), key(80 + index as u8)))
            .collect();
        let stale_key = key(99);
        let mut genesis_keys = registered.clone();
        genesis_keys[5].1 = stale_key.clone();
        let mut ledger = LedgerState::empty();
        ledger.fastpay_recovery_policy = Some(postfiat_types::FastPayRecoveryPolicyV1 {
            schema: postfiat_types::FASTPAY_RECOVERY_POLICY_SCHEMA_V1.to_string(),
            activation_height: 11,
            max_validity_blocks: 100,
            max_recovery_blocks: 100,
        });
        ledger.fastpay_recovery_committees.push(
            postfiat_types::FastPayRecoveryCommitteeV1::from_public_keys(
                CHAIN.to_string(),
                "11".repeat(48),
                1,
                1,
                11,
                10_000,
                genesis_keys,
            )
            .unwrap(),
        );
        (ledger, ids, registered, stale_key)
    }

    fn inputs<'a>(
        ledger: &'a LedgerState,
        ids: &'a [String],
        registered: &'a [(String, String)],
        members: &'a [(String, String)],
        tip: u64,
        requested: Option<u64>,
    ) -> FastPayCommitteeInputs<'a> {
        FastPayCommitteeInputs {
            ledger,
            chain_tip_height: tip,
            active_validators: ids,
            registered_keys: registered,
            member_keys: members,
            requested_valid_from_height: requested,
            new_orders_through_height: None,
        }
    }

    #[test]
    fn fastpay_committee_prepare_reproduces_registry_root_and_quorum_over_fixture_registry() {
        let (ledger, ids, registered, _) = fixture();
        let prepared = prepare_next_fastpay_committee(inputs(
            &ledger,
            &ids,
            &registered,
            &registered,
            1115,
            None,
        ))
        .unwrap();
        let record = &prepared.payload.committee;
        record.validate().unwrap();
        assert_eq!(record.committee_epoch, 2);
        assert_eq!(
            (record.valid_from_height, record.new_orders_through_height),
            (10_001, 19_990)
        );
        assert_eq!(record.quorum, 5);
        assert_eq!(record.validator_public_keys(), registered);
        assert_eq!(record.registry_root, "fa2ee46490c5e0c24b8f174aa64e4ed0d26d094d9bc4d1333f965bff38d3b2520f4c3a292e182f072d53d2b0cc833137");
    }

    #[test]
    fn fastpay_committee_prepare_refuses_stale_member_key() {
        let (ledger, ids, registered, stale_key) = fixture();
        let mut members = registered.clone();
        members[5].1 = stale_key;
        let error = prepare_next_fastpay_committee(inputs(
            &ledger,
            &ids,
            &registered,
            &members,
            1115,
            None,
        ))
        .unwrap_err();
        assert!(
            error.contains("validator-5 key is not its currently registered"),
            "{error}"
        );
    }

    #[test]
    fn fastpay_committee_prepare_applies_earliest_height_rule() {
        let (ledger, ids, registered, _) = fixture();
        let run = |tip, requested| {
            prepare_next_fastpay_committee(inputs(
                &ledger,
                &ids,
                &registered,
                &registered,
                tip,
                requested,
            ))
        };
        for requested in [None, Some(1200), Some(10_001)] {
            let prepared = run(1115, requested).unwrap();
            assert_eq!(prepared.earliest_valid_from_height, 10_001);
            assert_eq!(prepared.payload.committee.valid_from_height, 10_001);
        }
        assert!(run(1115, Some(10_002))
            .unwrap_err()
            .contains("must start at exactly 10001"));
        assert!(run(9_999, None).is_ok());
        assert!(run(10_000, None)
            .unwrap_err()
            .contains("rotation window closed"));
    }

    #[test]
    fn fastpay_committee_prepare_refuses_quorum_other_than_five_of_six() {
        let (mut ledger, _, registered, _) = fixture();
        let four: Vec<(String, String)> = registered[..4].to_vec();
        let ids: Vec<String> = four.iter().map(|(id, _)| id.clone()).collect();
        let previous = ledger.fastpay_recovery_committees.pop().unwrap();
        ledger.fastpay_recovery_committees.push(
            postfiat_types::FastPayRecoveryCommitteeV1::from_public_keys(
                previous.chain_id,
                previous.genesis_hash,
                1,
                1,
                11,
                10_000,
                four.clone(),
            )
            .unwrap(),
        );
        let error = prepare_next_fastpay_committee(inputs(&ledger, &ids, &four, &four, 1115, None))
            .unwrap_err();
        assert!(error.contains("quorum is 3 of 4"), "{error}");
    }

    #[test]
    fn fastpay_committee_prepare_builds_unsigned_batch_from_data_dir() {
        let root = std::env::temp_dir().join(format!(
            "postfiat-fastpay-committee-prepare-{}",
            std::process::id()
        ));
        let _ = std::fs::remove_dir_all(&root);
        init(InitOptions {
            data_dir: root.clone(),
            chain_id: CHAIN.to_string(),
            node_id: "validator-0".to_string(),
            validator_count: 6,
        })
        .unwrap();
        let store = NodeStore::new(&root);
        let genesis = store.read_genesis().unwrap();
        store
            .write_chain_tip(&ChainTipState {
                schema: CHAIN_TIP_SCHEMA.to_string(),
                chain_id: genesis.chain_id.clone(),
                genesis_hash: genesis_hash(&genesis),
                protocol_version: genesis.protocol_version,
                height: 1115,
                block_hash: "aa".repeat(48),
                state_root: "bb".repeat(48),
                ordered_batch_count: 0,
                receipt_count: 0,
                history_base_height: 0,
            })
            .unwrap();
        let registered = load_validator_pubkeys(&root).unwrap();
        let mut epoch_one_keys = registered.clone();
        epoch_one_keys[5].1 = key(99);
        let mut ledger = store.read_ledger().unwrap();
        ledger.fastpay_recovery_policy = fixture().0.fastpay_recovery_policy;
        ledger.fastpay_recovery_committees.push(
            postfiat_types::FastPayRecoveryCommitteeV1::from_public_keys(
                genesis.chain_id.clone(),
                genesis_hash(&genesis),
                genesis.protocol_version,
                1,
                11,
                10_000,
                epoch_one_keys,
            )
            .unwrap(),
        );
        store.write_ledger(&ledger).unwrap();
        let options = |registry_file| FastPayCommitteePrepareOptions {
            data_dir: root.clone(),
            registry_file,
            valid_from_height: None,
            new_orders_through_height: None,
        };

        let output = fastpay_committee_prepare(options(None)).unwrap();
        assert_eq!(output["signed"], false);
        assert_eq!(output["earliest_valid_from_height"], 10_001);
        assert_eq!(
            output["replaced_member_keys"],
            serde_json::json!(["validator-5"])
        );
        assert_eq!(output["record"]["quorum"], 5);
        assert_eq!(output["governance_signers_required"], 6);
        let batch: GovernanceActionBatch =
            serde_json::from_value(output["unsigned_transaction"].clone()).unwrap();
        let bootstrap = &batch.fastpay_recovery_bootstraps[0];
        assert!(bootstrap.amendment.signed_authorizations.is_empty());
        assert_eq!(
            bootstrap.payload.committee.validator_public_keys(),
            registered
        );
        verify_governance_action_batch_id(&genesis, &batch).unwrap();

        let stale_registry = root.join("stale_registry.json");
        let mut snapshot =
            read_validator_registry_file(&root.join("validator_registry.json")).unwrap();
        snapshot.validators[5].public_key_hex = key(99);
        std::fs::write(&stale_registry, serde_json::to_vec(&snapshot).unwrap()).unwrap();
        let error = fastpay_committee_prepare(options(Some(stale_registry))).unwrap_err();
        assert!(error
            .to_string()
            .contains("validator-5 key is not its currently registered"));
        std::fs::remove_dir_all(root).unwrap();
    }
}
