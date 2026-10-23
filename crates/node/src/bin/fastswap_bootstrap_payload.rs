use postfiat_crypto_provider::{hash_bytes, hex_to_bytes};
use postfiat_execution::fastswap_bridge::asset_definition_hash;
use postfiat_types::{
    FastAssetIdV1, FastAssetRuleHashV1, FastAssetRuleV1, FastSwapChainDomainV1,
    FastSwapCommitteeDomainV1, FastSwapCommitteeRootV1, FastSwapCommitteeV1,
    FastSwapGovernanceBootstrapPayloadV1, FastSwapMarketEnvelopeHashV1, FastSwapOpaqueHashV1,
    FastSwapPolicyHashV1, FastSwapPolicySnapshotV1, FastSwapQuoteRoundingV1, FastSwapValidatorV1,
    LedgerState, FASTSWAP_SCHEMA_VERSION_V1,
};
use serde::Deserialize;
use std::env;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};

#[derive(Deserialize)]
struct ChainTip {
    chain_id: String,
    genesis_hash: String,
    protocol_version: u32,
    height: u64,
}

#[derive(Deserialize)]
struct ValidatorRegistry {
    validators: Vec<ValidatorRecord>,
}

#[derive(Deserialize)]
struct ValidatorRecord {
    node_id: String,
    algorithm_id: String,
    public_key_hex: String,
}

struct Options {
    ledger: PathBuf,
    registry: Option<PathBuf>,
    committee_file: Option<PathBuf>,
    tip: PathBuf,
    activation_height: u64,
    valid_through_height: u64,
    asset_0_id: String,
    asset_1_id: String,
    price_numerator: u128,
    price_denominator: u128,
    nav_epoch: u64,
    market_envelope_hash: String,
    output: PathBuf,
}

fn required_flag(args: &[String], flag: &str) -> Result<String, String> {
    let index = args
        .iter()
        .position(|value| value == flag)
        .ok_or_else(|| format!("missing {flag}"))?;
    args.get(index + 1)
        .cloned()
        .ok_or_else(|| format!("missing value for {flag}"))
}

fn optional_flag(args: &[String], flag: &str) -> Result<Option<String>, String> {
    if !args.iter().any(|value| value == flag) {
        return Ok(None);
    }
    required_flag(args, flag).map(Some)
}

fn parse_options(args: &[String]) -> Result<Options, String> {
    let registry = optional_flag(args, "--registry")?.map(PathBuf::from);
    let committee_file = optional_flag(args, "--committee-file")?.map(PathBuf::from);
    if registry.is_some() == committee_file.is_some() {
        return Err("exactly one of --registry or --committee-file is required".into());
    }
    Ok(Options {
        ledger: PathBuf::from(required_flag(args, "--ledger")?),
        registry,
        committee_file,
        tip: PathBuf::from(required_flag(args, "--tip")?),
        activation_height: required_flag(args, "--activation-height")?
            .parse()
            .map_err(|_| "--activation-height must be a u64".to_owned())?,
        valid_through_height: required_flag(args, "--valid-through-height")?
            .parse()
            .map_err(|_| "--valid-through-height must be a u64".to_owned())?,
        asset_0_id: required_flag(args, "--asset-0-id")?,
        asset_1_id: required_flag(args, "--asset-1-id")?,
        price_numerator: required_flag(args, "--price-numerator")?
            .parse()
            .map_err(|_| "--price-numerator must be a u128".to_owned())?,
        price_denominator: required_flag(args, "--price-denominator")?
            .parse()
            .map_err(|_| "--price-denominator must be a u128".to_owned())?,
        nav_epoch: required_flag(args, "--nav-epoch")?
            .parse()
            .map_err(|_| "--nav-epoch must be a u64".to_owned())?,
        market_envelope_hash: required_flag(args, "--market-envelope-hash")?,
        output: PathBuf::from(required_flag(args, "--output")?),
    })
}

fn read_json<T: for<'de> Deserialize<'de>>(path: &Path) -> Result<T, String> {
    let bytes = fs::read(path).map_err(|error| format!("{}: {error}", path.display()))?;
    serde_json::from_slice(state_file_body(&bytes))
        .map_err(|error| format!("{}: {error}", path.display()))
}

/// A validator data directory writes whole-file state as `<json>` plus a
/// `pftmac1:<hex>` line keyed by that node's local secret
/// (`crates/storage/src/integrity.rs`). This offline tool cannot verify a
/// node-local key; it reads the JSON body the tag covers. Files without the
/// tag are read unchanged.
fn state_file_body(bytes: &[u8]) -> &[u8] {
    let mut end = bytes.len();
    while end > 0 && matches!(bytes[end - 1], b'\n' | b'\r') {
        end -= 1;
    }
    match bytes[..end].iter().rposition(|byte| *byte == b'\n') {
        Some(newline) if bytes[newline + 1..end].starts_with(b"pftmac1:") => &bytes[..newline],
        _ => bytes,
    }
}

/// The committee an `ActivateCommittee` record installed, read as
/// `fastswap-committee-migrate --committee-file` reads it: the record's
/// `operation.certificate.action.committee`, or a bare committee document.
fn read_committee_file(path: &Path) -> Result<FastSwapCommitteeV1, String> {
    let value: serde_json::Value = read_json(path)?;
    let object = value
        .pointer("/operation/certificate/action/committee")
        .cloned()
        .unwrap_or(value);
    let committee: FastSwapCommitteeV1 = serde_json::from_value(object)
        .map_err(|error| format!("committee file is not a FastSwap committee: {error}"))?;
    committee.validate().map_err(|error| {
        format!("committee file does not validate against its own root: {error:?}")
    })?;
    Ok(committee)
}

fn fixed48(value: &str, label: &str) -> Result<[u8; 48], String> {
    hex_to_bytes(value)
        .map_err(|error| format!("invalid {label}: {error}"))?
        .try_into()
        .map_err(|_| format!("{label} must be 48 bytes"))
}

fn write_new_payload(path: &Path, encoded: &[u8]) -> Result<(), String> {
    let mut output = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .map_err(|error| format!("{}: {error}", path.display()))?;
    output
        .write_all(encoded)
        .map_err(|error| format!("{}: {error}", path.display()))
}

fn validate_height_window(
    tip_height: u64,
    activation_height: u64,
    valid_through_height: u64,
) -> Result<(), String> {
    let first_valid_activation = tip_height
        .checked_add(1)
        .ok_or_else(|| "chain tip height is exhausted; no activation window remains".to_owned())?;
    if activation_height <= first_valid_activation || valid_through_height <= activation_height {
        return Err("activation must leave one governance-commit height and precede expiry".into());
    }
    Ok(())
}

struct BuiltPayload {
    payload: FastSwapGovernanceBootstrapPayloadV1,
    encoded: Vec<u8>,
    tip_height: u64,
}

fn main() -> Result<(), String> {
    let args = env::args().skip(1).collect::<Vec<_>>();
    let options = parse_options(&args)?;
    let built = build_payload(&options)?;
    write_new_payload(&options.output, &built.encoded)?;
    println!(
        "wrote {}: tip={} activation={} expiry={} committee=6 quorum=5 rules=2 policies=1",
        options.output.display(),
        built.tip_height,
        options.activation_height,
        options.valid_through_height
    );
    if options.committee_file.is_some() {
        let domain = &built.payload.committee.domain;
        println!(
            "committee epoch={} root={}",
            domain.committee_epoch,
            postfiat_crypto_provider::bytes_to_hex(&domain.committee_root.0)
        );
    }
    Ok(())
}

/// Epoch 1, the committee a governance bootstrap installs: the six registry
/// members, for an activation still ahead of the tip.
fn registry_committee(
    registry_path: &Path,
    options: &Options,
) -> Result<(FastSwapCommitteeV1, FastSwapChainDomainV1, u64), String> {
    let mut registry: ValidatorRegistry = read_json(registry_path)?;
    let tip: ChainTip = read_json(&options.tip)?;
    validate_height_window(
        tip.height,
        options.activation_height,
        options.valid_through_height,
    )?;

    registry
        .validators
        .sort_by(|left, right| left.node_id.cmp(&right.node_id));
    if registry.validators.len() != 6
        || registry
            .validators
            .iter()
            .any(|record| record.algorithm_id != "ML-DSA-65")
        || !registry
            .validators
            .windows(2)
            .all(|pair| pair[0].node_id < pair[1].node_id)
    {
        return Err("canonical six-member ML-DSA-65 validator registry required".into());
    }
    let chain = tip_chain(&tip)?;
    let validators = registry
        .validators
        .into_iter()
        .map(|record| {
            Ok(FastSwapValidatorV1 {
                validator_id: record.node_id,
                public_key: hex_to_bytes(&record.public_key_hex)
                    .map_err(|error| format!("invalid validator public key: {error}"))?,
            })
        })
        .collect::<Result<Vec<_>, String>>()?;
    let mut committee = FastSwapCommitteeV1 {
        domain: FastSwapCommitteeDomainV1 {
            chain: chain.clone(),
            fastswap_schema_version: FASTSWAP_SCHEMA_VERSION_V1,
            committee_epoch: 1,
            committee_root: FastSwapCommitteeRootV1::ZERO,
            validator_count: 6,
            quorum: 5,
        },
        validators,
    };
    committee.domain.committee_root = committee
        .computed_root()
        .map_err(|error| format!("committee root: {error:?}"))?;
    committee
        .validate()
        .map_err(|error| format!("committee: {error:?}"))?;
    Ok((committee, chain, tip.height))
}

/// The chain's current committee, for a FastSwap activation already on the
/// ledger: the committee comes from its `ActivateCommittee` record, and the
/// activation height must be the one the ledger recorded.
fn recorded_committee(
    committee_file: &Path,
    ledger: &LedgerState,
    options: &Options,
) -> Result<(FastSwapCommitteeV1, FastSwapChainDomainV1, u64), String> {
    let tip: ChainTip = read_json(&options.tip)?;
    let chain = tip_chain(&tip)?;
    let committee = read_committee_file(committee_file)?;
    if committee.domain.chain != chain {
        return Err("committee file chain domain differs from the chain tip".into());
    }
    if committee.domain.validator_count != 6 || committee.domain.quorum != 5 {
        return Err("committee file must name six validators with quorum five".into());
    }
    if ledger.fastswap_activation_height != Some(options.activation_height)
        || tip.height < options.activation_height
        || options.valid_through_height <= options.activation_height
    {
        return Err(
            "activation height must equal the ledger's recorded FastSwap activation height".into(),
        );
    }
    Ok((committee, chain, tip.height))
}

fn tip_chain(tip: &ChainTip) -> Result<FastSwapChainDomainV1, String> {
    Ok(FastSwapChainDomainV1 {
        chain_id: tip.chain_id.clone(),
        genesis_hash: FastSwapOpaqueHashV1(fixed48(&tip.genesis_hash, "genesis hash")?),
        protocol_version: tip.protocol_version,
    })
}

/// Every bootstrap rule. A recorded committee keeps all of them except the
/// bootstrap's own epoch-1 bound, which a later `ActivateCommittee` lifts.
fn validate_activation_payload(
    payload: &FastSwapGovernanceBootstrapPayloadV1,
) -> Result<(), String> {
    payload
        .committee
        .validate()
        .map_err(|error| format!("committee: {error:?}"))?;
    let mut bootstrap_bounds = payload.clone();
    bootstrap_bounds.committee.domain.committee_epoch = 1;
    bootstrap_bounds
        .validate_payload()
        .map_err(|error| format!("bootstrap payload: {error:?}"))
}

fn build_payload(options: &Options) -> Result<BuiltPayload, String> {
    let ledger: LedgerState = read_json(&options.ledger)?;
    let (committee, chain, tip_height) = match (&options.registry, &options.committee_file) {
        (Some(registry), None) => registry_committee(registry, options)?,
        (None, Some(committee_file)) => recorded_committee(committee_file, &ledger, options)?,
        _ => return Err("exactly one of --registry or --committee-file is required".into()),
    };

    let mut rules =
        [options.asset_0_id.as_str(), options.asset_1_id.as_str()]
            .into_iter()
            .map(|asset_id_hex| {
                let definition = ledger
                    .asset_definitions
                    .iter()
                    .find(|definition| definition.asset_id == asset_id_hex)
                    .ok_or_else(|| format!("missing exact asset definition {asset_id_hex}"))?;
                let issuer = ledger
                    .accounts
                    .iter()
                    .find(|account| account.address == definition.issuer)
                    .ok_or_else(|| format!("missing issuer account {}", definition.issuer))?;
                let issuer_control_pubkey =
                    hex_to_bytes(issuer.public_key_hex.as_deref().ok_or_else(|| {
                        format!("issuer {} has no public key", definition.issuer)
                    })?)
                    .map_err(|error| format!("invalid issuer public key: {error}"))?;
                Ok(FastAssetRuleV1 {
                    asset_id: FastAssetIdV1(fixed48(asset_id_hex, "asset id")?),
                    asset_definition_hash: asset_definition_hash(definition)
                        .map_err(|error| format!("asset definition hash: {error:?}"))?,
                    issuer_address: definition.issuer.clone(),
                    issuer_control_pubkey,
                    requires_authorization: definition.requires_authorization,
                    freeze_enabled: definition.freeze_enabled,
                    clawback_enabled: definition.clawback_enabled,
                    fast_lane_enabled: true,
                    valid_from_height: options.activation_height,
                    valid_through_height: options.valid_through_height,
                })
            })
            .collect::<Result<Vec<_>, String>>()?;
    rules.sort_by_key(|rule| rule.rule_hash().expect("validated asset rule"));

    let asset_0_id = FastAssetIdV1(fixed48(&options.asset_0_id, "asset 0 id")?);
    let asset_1_id = FastAssetIdV1(fixed48(&options.asset_1_id, "asset 1 id")?);
    let rule_hash = |asset_id: FastAssetIdV1| -> Result<FastAssetRuleHashV1, String> {
        rules
            .iter()
            .find(|rule| rule.asset_id == asset_id)
            .ok_or_else(|| "missing rule after canonical sort".to_owned())?
            .rule_hash()
            .map_err(|error| format!("rule hash: {error:?}"))
    };
    let fee_schedule_hash: [u8; 48] = hash_bytes(
        "postfiat.fastswap.fee_schedule.v1",
        b"party_0_fee_pft=1\nparty_1_fee_pft=1\n",
    )
    .try_into()
    .map_err(|_| "fee schedule hash must be 48 bytes".to_owned())?;
    let mut policy = FastSwapPolicySnapshotV1 {
        domain: chain,
        policy_epoch: 1,
        policy_hash: FastSwapPolicyHashV1::ZERO,
        pair_asset_0: asset_0_id,
        pair_asset_1: asset_1_id,
        asset_rule_hash_0: rule_hash(asset_0_id)?,
        asset_rule_hash_1: rule_hash(asset_1_id)?,
        price_numerator: options.price_numerator,
        price_denominator: options.price_denominator,
        rounding: FastSwapQuoteRoundingV1::Down,
        nav_epoch: options.nav_epoch,
        market_envelope_hash: FastSwapMarketEnvelopeHashV1(fixed48(
            &options.market_envelope_hash,
            "market envelope hash",
        )?),
        valid_from_height: options.activation_height,
        valid_through_height: options.valid_through_height,
        fee_schedule_hash: FastSwapOpaqueHashV1(fee_schedule_hash),
        max_inputs_per_party: 16,
        max_outputs: 8,
        paused: false,
    };
    policy.policy_hash = policy
        .computed_hash()
        .map_err(|error| format!("policy hash: {error:?}"))?;
    policy
        .validate()
        .map_err(|error| format!("policy: {error:?}"))?;
    if options.committee_file.is_some() && !ledger.fastswap_policy_snapshots.contains(&policy) {
        return Err("regenerated policy differs from the ledger's governed FastSwap policy".into());
    }

    let payload = FastSwapGovernanceBootstrapPayloadV1 {
        committee,
        asset_rules: rules,
        policies: vec![policy],
        activation_height: options.activation_height,
    };
    if options.committee_file.is_some() {
        validate_activation_payload(&payload)?;
    } else {
        payload
            .validate_payload()
            .map_err(|error| format!("bootstrap payload: {error:?}"))?;
    }
    let encoded = serde_json::to_vec_pretty(&payload)
        .map_err(|error| format!("serialize bootstrap payload: {error}"))?;
    Ok(BuiltPayload {
        payload,
        encoded,
        tip_height,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    const PFUSDC: &str = "02c46a36eb0da3516b4d8affea8f4028ad3f36825a3e8f0e009ea9dbbbcfb3c233f6830bd5221fe2717fb6a1a7005d7b";
    const A651: &str = "de8d3d78aca83f7000632cbd3dd06edd30d105085d16eef1696f9e1707908ec9209239080d21ca1c0cecc36ca6f966b6";
    const ENVELOPE: &str = "f31b5e66ba4d515cb4b29793c5ee41c8c1cd704c36e916c17a2c4d4ec4eaf735cf7881027460f3debe3da4c7e87fa765";
    const EPOCH_2_ROOT: &str = "72836827f9f3ecd3042261a77abff72235f0238b6a81f673630a62199415021a1be0cbd5451878edca0e110434c1da37";
    /// SHA-256 of the epoch-2 committee domain as canonical JSON, the value
    /// StakeHub's activation check 0c' expects.
    const EPOCH_2_DOMAIN_SHA256: &str =
        "b1c5261b5559f2266a4e7620f5945fa250dcea8ad7dd7d2e763a5e7c756b577b";
    /// Bytes of the epoch-1 registry payload written by this tool at `a364eaed`
    /// for the same inputs, before the committee-file mode existed.
    const EPOCH_1_PAYLOAD_SHA256: &str =
        "8671b642883b690ff40854882bf46b8e66d429e6c58a1eac820a460d153bd3f7";
    const GOVERNED_POLICY_HASH: &str = "356e5cca344cde537ccaa2aab7d960f9228182ce22812671e8d053512302a75395e80ade6876670dc2379a9d66e48cc9";

    fn fixture(name: &str) -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("testdata/fastswap-bootstrap-current-epoch")
            .join(name)
    }

    /// Recorded inputs: the height-1123 validator snapshot (ledger reduced to
    /// the fields the tool reads) and the height-1131 `ActivateCommittee`.
    fn options(activation_height: u64, committee: bool) -> Options {
        Options {
            ledger: fixture("ledger.json"),
            registry: (!committee).then(|| fixture("validator_registry.json")),
            committee_file: committee.then(|| fixture("activate-committee.json")),
            tip: fixture("chain_tip.json"),
            activation_height,
            valid_through_height: 10_000,
            asset_0_id: PFUSDC.into(),
            asset_1_id: A651.into(),
            price_numerator: 1_000_000,
            price_denominator: 1_000_000,
            nav_epoch: 3,
            market_envelope_hash: ENVELOPE.into(),
            output: PathBuf::new(),
        }
    }

    fn sha256_hex(bytes: &[u8]) -> String {
        use sha2::Digest;
        postfiat_crypto_provider::bytes_to_hex(&sha2::Sha256::digest(bytes))
    }

    fn temp_copy(name: &str, edit: impl FnOnce(String) -> String) -> PathBuf {
        let path = std::env::temp_dir().join(format!(
            "postfiat-bootstrap-{}-{}-{name}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        let text = fs::read_to_string(fixture(name)).unwrap();
        fs::write(&path, edit(text)).unwrap();
        path
    }

    #[test]
    fn epoch_one_registry_payload_keeps_its_bytes() {
        let built = build_payload(&options(1_125, false)).expect("epoch-1 payload");
        assert_eq!(built.payload.committee.domain.committee_epoch, 1);
        assert_eq!(sha256_hex(&built.encoded), EPOCH_1_PAYLOAD_SHA256);
    }

    #[test]
    fn recorded_activation_gives_the_epoch_two_payload() {
        let built = build_payload(&options(152, true)).expect("current-epoch payload");
        let parsed: FastSwapGovernanceBootstrapPayloadV1 =
            serde_json::from_slice(&built.encoded).expect("payload parses");
        assert_eq!(parsed, built.payload);
        let domain = &parsed.committee.domain;
        assert_eq!(domain.committee_epoch, 2);
        assert_eq!(
            postfiat_crypto_provider::bytes_to_hex(&domain.committee_root.0),
            EPOCH_2_ROOT
        );
        let canonical = serde_json::to_string(&serde_json::to_value(domain).unwrap()).unwrap();
        assert_eq!(sha256_hex(canonical.as_bytes()), EPOCH_2_DOMAIN_SHA256);
        parsed.committee.validate().expect("committee validates");
    }

    #[test]
    fn current_epoch_payload_carries_the_governed_policy() {
        let built = build_payload(&options(152, true)).expect("current-epoch payload");
        let ledger: LedgerState = read_json(&fixture("ledger.json")).unwrap();
        assert_eq!(built.payload.policies, ledger.fastswap_policy_snapshots);
        assert_eq!(
            postfiat_crypto_provider::bytes_to_hex(&built.payload.policies[0].policy_hash.0),
            GOVERNED_POLICY_HASH
        );
    }

    #[test]
    fn current_epoch_refuses_an_unrecorded_activation_height() {
        let error = build_payload(&options(153, true)).err().expect("refused");
        assert!(error.contains("activation height"), "{error}");
    }

    #[test]
    fn current_epoch_refuses_a_policy_the_ledger_did_not_govern() {
        let mut changed = options(152, true);
        changed.nav_epoch = 4;
        let error = build_payload(&changed).err().expect("refused");
        assert!(error.contains("governed FastSwap policy"), "{error}");
    }

    #[test]
    fn current_epoch_refuses_a_committee_of_another_chain() {
        let mut changed = options(152, true);
        changed.tip = temp_copy("chain_tip.json", |text| {
            text.replace("postfiat-wan-devnet-2", "postfiat-other-chain")
        });
        let error = build_payload(&changed).err().expect("refused");
        fs::remove_file(&changed.tip).unwrap();
        assert!(error.contains("chain domain"), "{error}");
    }

    #[test]
    fn current_epoch_refuses_a_committee_whose_root_does_not_match() {
        let mut changed = options(152, true);
        changed.committee_file = Some(temp_copy("activate-committee.json", |text| {
            text.replacen("\"committee_root\":[114,", "\"committee_root\":[115,", 1)
        }));
        let error = build_payload(&changed).err().expect("refused");
        fs::remove_file(changed.committee_file.as_ref().unwrap()).unwrap();
        assert!(error.contains("root"), "{error}");
    }

    #[test]
    fn registry_and_committee_file_are_exclusive() {
        let base = [
            "--ledger",
            "l",
            "--tip",
            "t",
            "--activation-height",
            "152",
            "--valid-through-height",
            "10000",
            "--asset-0-id",
            PFUSDC,
            "--asset-1-id",
            A651,
            "--price-numerator",
            "1",
            "--price-denominator",
            "1",
            "--nav-epoch",
            "3",
            "--market-envelope-hash",
            ENVELOPE,
            "--output",
            "o",
        ]
        .map(String::from)
        .to_vec();
        let with = |extra: &[&str]| {
            let mut args = base.clone();
            args.extend(extra.iter().map(|value| value.to_string()));
            parse_options(&args)
        };
        assert!(with(&[]).is_err());
        assert!(with(&["--registry", "r", "--committee-file", "c"]).is_err());
        assert!(with(&["--registry", "r"]).is_ok_and(|o| o.committee_file.is_none()));
        assert!(with(&["--committee-file", "c"]).is_ok_and(|o| o.registry.is_none()));
    }

    #[test]
    fn data_directory_state_files_are_read_through_their_integrity_tag() {
        let tagged = |text: String| format!("{text}pftmac1:{}\n", "ab".repeat(48));
        let mut changed = options(152, true);
        changed.ledger = temp_copy("ledger.json", tagged);
        changed.tip = temp_copy("chain_tip.json", tagged);
        let built = build_payload(&changed);
        fs::remove_file(&changed.ledger).unwrap();
        fs::remove_file(&changed.tip).unwrap();
        let plain = build_payload(&options(152, true)).expect("plain inputs");
        assert_eq!(built.expect("tagged inputs").encoded, plain.encoded);
    }

    #[test]
    fn bootstrap_payload_existing_file_property_preserves_all_bytes() {
        let root = std::env::temp_dir().join(format!(
            "postfiat-bootstrap-property-{}-{:?}",
            std::process::id(),
            std::thread::current().id()
        ));
        fs::create_dir_all(&root).expect("create test root");
        for length in [0, 1, 2, 16, 256, 1_024] {
            let existing = (0..length).map(|index| index as u8).collect::<Vec<_>>();
            let path = root.join(format!("existing-{length}.json"));
            fs::write(&path, &existing).expect("create existing payload");
            assert!(write_new_payload(&path, b"replacement").is_err());
            assert_eq!(fs::read(&path).expect("existing file"), existing);
        }
        let path = root.join("fresh.json");
        write_new_payload(&path, b"first").expect("fresh output");
        assert!(write_new_payload(&path, b"second").is_err());
        assert_eq!(fs::read(&path).expect("read fresh output"), b"first");
        fs::remove_dir_all(root).expect("cleanup");
    }

    #[test]
    fn exhausted_tip_height_is_rejected_without_panicking() {
        assert!(validate_height_window(u64::MAX, u64::MAX, u64::MAX).is_err());
    }

    #[test]
    fn bootstrap_output_refuses_existing_governance_payload_without_changing_it() {
        let path = std::env::temp_dir().join(format!(
            "postfiat-bootstrap-output-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::write(&path, b"inspected governance payload").unwrap();
        assert!(write_new_payload(&path, b"replacement payload").is_err());
        assert_eq!(fs::read(&path).unwrap(), b"inspected governance payload");
        fs::remove_file(&path).unwrap();
    }
}
