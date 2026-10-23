use postfiat_crypto_provider::{hash_bytes, hex_to_bytes};
use postfiat_types::{
    FastAssetIdV1, FastLaneDepositV1, FastLanePrimaryOperationV1, FastLanePrimaryTransactionV1,
    FastObjectIdV1, FastObjectKeyV1, FastSwapCommitteeV1, FastSwapGovernanceBootstrapPayloadV1,
    FastSwapIntentV1, FastSwapPartyV1, FastSwapRfqHashV1, SignedFastLaneDepositV1,
};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

fn flag(args: &[String], name: &str) -> Result<String, String> {
    let index = args
        .iter()
        .position(|value| value == name)
        .ok_or_else(|| format!("missing {name}"))?;
    args.get(index + 1)
        .cloned()
        .ok_or_else(|| format!("missing value for {name}"))
}

fn optional_flag(args: &[String], name: &str) -> Result<Option<String>, String> {
    if !args.iter().any(|value| value == name) {
        return Ok(None);
    }
    flag(args, name).map(Some)
}

/// The wallet's activation payload, under the committee epoch it declares.
///
/// An epoch-1 payload is the governance bootstrap and must pass every
/// bootstrap rule. A payload for a later epoch (written by
/// `fastswap_bootstrap_payload --committee-file` after an `ActivateCommittee`)
/// keeps every rule except the bootstrap's own epoch-1 bound. With
/// `--committee-file`, the payload's committee must equal the committee that
/// record installed, read as `fastswap-committee-migrate` reads it.
fn read_payload(
    path: &Path,
    committee_file: Option<&Path>,
) -> Result<FastSwapGovernanceBootstrapPayloadV1, String> {
    let bytes = fs::read(path).map_err(|error| format!("{}: {error}", path.display()))?;
    let payload: FastSwapGovernanceBootstrapPayloadV1 =
        serde_json::from_slice(&bytes).map_err(|error| format!("{}: {error}", path.display()))?;
    match payload.committee.domain.committee_epoch {
        0 => return Err("invalid bootstrap payload: committee epoch 0".to_owned()),
        1 => payload
            .validate_payload()
            .map_err(|error| format!("invalid bootstrap payload: {error:?}"))?,
        _ => {
            payload
                .committee
                .validate()
                .map_err(|error| format!("invalid bootstrap payload: committee: {error:?}"))?;
            let mut bootstrap_bounds = payload.clone();
            bootstrap_bounds.committee.domain.committee_epoch = 1;
            bootstrap_bounds
                .validate_payload()
                .map_err(|error| format!("invalid bootstrap payload: {error:?}"))?;
        }
    }
    if let Some(committee_file) = committee_file {
        if read_committee_file(committee_file)? != payload.committee {
            return Err("activation payload committee differs from the committee file".to_owned());
        }
    }
    Ok(payload)
}

fn read_committee_file(path: &Path) -> Result<FastSwapCommitteeV1, String> {
    let bytes = fs::read(path).map_err(|error| format!("{}: {error}", path.display()))?;
    let value: serde_json::Value =
        serde_json::from_slice(&bytes).map_err(|error| format!("{}: {error}", path.display()))?;
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

fn activation_payload(args: &[String]) -> Result<FastSwapGovernanceBootstrapPayloadV1, String> {
    let committee_file = optional_flag(args, "--committee-file")?.map(PathBuf::from);
    read_payload(
        &PathBuf::from(flag(args, "--payload")?),
        committee_file.as_deref(),
    )
}

fn bytes<const N: usize>(value: &str, label: &str) -> Result<[u8; N], String> {
    hex_to_bytes(value.trim_start_matches("0x"))
        .map_err(|error| format!("invalid {label}: {error}"))?
        .try_into()
        .map_err(|_| format!("{label} must be {N} bytes"))
}

fn write_private(path: &Path, value: &impl serde::Serialize) -> Result<(), String> {
    if path.exists() {
        return Err(format!("{} already exists", path.display()));
    }
    let encoded = serde_json::to_vec_pretty(value).map_err(|error| error.to_string())?;
    fs::write(path, encoded).map_err(|error| format!("{}: {error}", path.display()))
}

fn deposit(args: &[String]) -> Result<(), String> {
    let payload = activation_payload(args)?;
    let asset_id = FastAssetIdV1(bytes(&flag(args, "--asset-id")?, "asset id")?);
    let rule = payload
        .asset_rules
        .iter()
        .find(|rule| rule.asset_id == asset_id)
        .ok_or_else(|| "asset is absent from the activated bootstrap payload".to_owned())?;
    let source_address = flag(args, "--source-address")?;
    let source_pubkey = hex_to_bytes(&flag(args, "--source-pubkey")?)
        .map_err(|error| format!("invalid source public key: {error}"))?;
    let sequence = flag(args, "--sequence")?
        .parse::<u64>()
        .map_err(|_| "--sequence must be a u64".to_owned())?;
    let amount_atoms = flag(args, "--amount-atoms")?
        .parse::<u64>()
        .map_err(|_| "--amount-atoms must be a u64".to_owned())?;
    if amount_atoms == 0 {
        return Err("deposit amount must be positive".to_owned());
    }
    let value = FastLaneDepositV1 {
        domain: payload.committee.domain.chain,
        source_address,
        source_pubkey: source_pubkey.clone(),
        sequence,
        fee_pft: 1,
        destination_owner_pubkey: source_pubkey,
        destination_holder_permit_id: None,
        asset_id,
        asset_rule_hash: rule
            .rule_hash()
            .map_err(|error| format!("asset rule hash: {error:?}"))?,
        amount_atoms,
        nonce: bytes(&flag(args, "--nonce")?, "deposit nonce")?,
    };
    value
        .signing_bytes()
        .map_err(|error| format!("deposit validation: {error:?}"))?;
    write_private(&PathBuf::from(flag(args, "--output")?), &value)
}

fn primary(args: &[String]) -> Result<(), String> {
    let input = PathBuf::from(flag(args, "--signed-deposit")?);
    let signed: SignedFastLaneDepositV1 = serde_json::from_slice(
        &fs::read(&input).map_err(|error| format!("{}: {error}", input.display()))?,
    )
    .map_err(|error| format!("{}: {error}", input.display()))?;
    let value = FastLanePrimaryTransactionV1 {
        operation: FastLanePrimaryOperationV1::Deposit { signed },
    };
    let tx_id = value
        .tx_id()
        .map_err(|error| format!("primary transaction validation: {error:?}"))?;
    write_private(&PathBuf::from(flag(args, "--output")?), &value)?;
    println!(
        "{}",
        tx_id
            .0
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    );
    Ok(())
}

struct PartyArgs {
    address: String,
    pubkey: Vec<u8>,
    object_id: [u8; 32],
    object_version: u64,
    amount: u64,
}

fn quote_asset_1(amount_0: u64, numerator: u128, denominator: u128) -> Result<u64, String> {
    if denominator == 0 {
        return Err("price denominator is zero".to_owned());
    }
    let quoted = u128::from(amount_0)
        .checked_mul(numerator)
        .ok_or_else(|| "quote multiplication overflow".to_owned())?
        / denominator;
    quoted
        .try_into()
        .map_err(|_| "governed quote exceeds u64 asset atoms".to_owned())
}

fn party_args(args: &[String], suffix: &str) -> Result<PartyArgs, String> {
    let amount = flag(args, &format!("--amount-{suffix}"))?
        .parse::<u64>()
        .map_err(|_| format!("--amount-{suffix} must be a u64"))?;
    if amount == 0 {
        return Err(format!("--amount-{suffix} must be positive"));
    }
    Ok(PartyArgs {
        address: flag(args, &format!("--owner-{suffix}-address"))?,
        pubkey: hex_to_bytes(&flag(args, &format!("--owner-{suffix}-pubkey"))?)
            .map_err(|error| format!("invalid owner {suffix} public key: {error}"))?,
        object_id: bytes(&flag(args, &format!("--object-{suffix}-id"))?, "object id")?,
        object_version: flag(args, &format!("--object-{suffix}-version"))?
            .parse::<u64>()
            .map_err(|_| format!("--object-{suffix}-version must be a u64"))?,
        amount,
    })
}

fn intent(args: &[String]) -> Result<(), String> {
    let payload = activation_payload(args)?;
    if payload.policies.len() != 1 {
        return Err("wallet helper requires one unambiguous active policy".to_owned());
    }
    let policy = &payload.policies[0];
    if policy.paused {
        return Err("FastSwap policy is paused".to_owned());
    }
    let first = party_args(args, "0")?;
    let second = party_args(args, "1")?;
    let expected_asset_1 = quote_asset_1(
        first.amount,
        policy.price_numerator,
        policy.price_denominator,
    )?;
    if expected_asset_1 != second.amount {
        return Err(format!(
            "amount-1 does not match the governed quote: expected {expected_asset_1}"
        ));
    }
    let amount_0 = first.amount;
    let amount_1 = second.amount;
    let make_party = |owner: PartyArgs,
                      offered_asset_id: FastAssetIdV1,
                      offered_rule_hash,
                      received_asset_id: FastAssetIdV1,
                      received_rule_hash,
                      received_amount: u64| FastSwapPartyV1 {
        owner_address: owner.address,
        owner_pubkey: owner.pubkey,
        offered_asset_id,
        offered_asset_rule_hash: offered_rule_hash,
        offered_amount: owner.amount,
        receives_asset_id: received_asset_id,
        receives_asset_rule_hash: received_rule_hash,
        receives_holder_permit_id: None,
        receives_amount: received_amount,
        asset_inputs: vec![FastObjectKeyV1 {
            object_id: FastObjectIdV1(owner.object_id),
            version: owner.object_version,
        }],
        fee_inputs: Vec::new(),
        asset_change: 0,
        fee_change: 0,
        fee_burn_pft: 0,
    };
    let expires_at_height = flag(args, "--expires-at-height")?
        .parse::<u64>()
        .map_err(|_| "--expires-at-height must be a u64".to_owned())?;
    if expires_at_height < policy.valid_from_height
        || expires_at_height > policy.valid_through_height
    {
        return Err("intent expiry is outside the governed policy window".to_owned());
    }
    let rfq: [u8; 48] = hash_bytes(
        "postfiat.fastswap.wallet_rfq.v1",
        flag(args, "--rfq")?.as_bytes(),
    )
    .try_into()
    .map_err(|_| "RFQ hash must be 48 bytes".to_owned())?;
    let value = FastSwapIntentV1 {
        domain: payload.committee.domain,
        policy_hash: policy.policy_hash,
        rfq_hash: FastSwapRfqHashV1(rfq),
        market_envelope_hash: policy.market_envelope_hash,
        nav_epoch: policy.nav_epoch,
        expires_at_height,
        nonce: bytes(&flag(args, "--nonce")?, "intent nonce")?,
        party_0: make_party(
            first,
            policy.pair_asset_0,
            policy.asset_rule_hash_0,
            policy.pair_asset_1,
            policy.asset_rule_hash_1,
            amount_1,
        ),
        party_1: make_party(
            second,
            policy.pair_asset_1,
            policy.asset_rule_hash_1,
            policy.pair_asset_0,
            policy.asset_rule_hash_0,
            amount_0,
        ),
    };
    value
        .canonical_bytes()
        .map_err(|error| format!("intent validation: {error:?}"))?;
    write_private(&PathBuf::from(flag(args, "--output")?), &value)
}

fn main() -> Result<(), String> {
    let args = env::args().skip(1).collect::<Vec<_>>();
    match args.first().map(String::as_str) {
        Some("deposit") => deposit(&args[1..]),
        Some("primary") => primary(&args[1..]),
        Some("intent") => intent(&args[1..]),
        _ => Err("usage: fastswap_wallet_payload <deposit|primary|intent> [flags]".to_owned()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const PFUSDC: &str = "02c46a36eb0da3516b4d8affea8f4028ad3f36825a3e8f0e009ea9dbbbcfb3c233f6830bd5221fe2717fb6a1a7005d7b";
    const OWNER_0: &str = "pf23d8831301aa1cce6fdd7bf4a2db2aead1619ba8";
    const OWNER_1: &str = "pffcb93d9f87a843a8aa34e1adf241f5d58143e81b";
    const EPOCH_2_PAYLOAD_SHA256: &str =
        "718fce157096c58133ca08c19e9bdd577c22b023c35556f78e9c083c1f4c39b7";
    const EPOCH_2_ROOT: &str = "72836827f9f3ecd3042261a77abff72235f0238b6a81f673630a62199415021a1be0cbd5451878edca0e110434c1da37";
    const EPOCH_2_DOMAIN_SHA256: &str =
        "b1c5261b5559f2266a4e7620f5945fa250dcea8ad7dd7d2e763a5e7c756b577b";
    /// Outputs of this helper at `ef7b406b` (before epoch awareness) for the
    /// epoch-1 form of the fixture payload and the arguments below.
    const EPOCH_1_DEPOSIT_SHA256: &str =
        "76ee046e1170420d1e8c076cca495ae1f7d0408f1fa9dec2c6582c3ea9ca1ac3";
    const EPOCH_1_INTENT_SHA256: &str =
        "eba7a5fbd8cbdd268292d391789e6f1d07d88a43c0e3765fc9b65bfc989f3fa9";

    fn fixture(name: &str) -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("testdata/fastswap-bootstrap-current-epoch")
            .join(name)
    }

    fn sha256_hex(bytes: &[u8]) -> String {
        use sha2::Digest;
        postfiat_crypto_provider::bytes_to_hex(&sha2::Sha256::digest(bytes))
    }

    fn scratch(name: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "postfiat-wallet-payload-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir_all(&dir).unwrap();
        dir.join(name)
    }

    /// The real epoch-2 activation payload with its committee epoch changed.
    fn payload_with_epoch(epoch: u64) -> PathBuf {
        let mut value: serde_json::Value =
            serde_json::from_slice(&fs::read(fixture("payload-epoch2.json")).unwrap()).unwrap();
        value["committee"]["domain"]["committee_epoch"] = epoch.into();
        let path = scratch("payload.json");
        fs::write(&path, serde_json::to_vec_pretty(&value).unwrap()).unwrap();
        path
    }

    fn validator_key(index: usize) -> String {
        let payload: FastSwapGovernanceBootstrapPayloadV1 =
            serde_json::from_slice(&fs::read(fixture("payload-epoch2.json")).unwrap()).unwrap();
        postfiat_crypto_provider::bytes_to_hex(&payload.committee.validators[index].public_key)
    }

    fn args(values: &[String]) -> Vec<String> {
        values.to_vec()
    }

    fn deposit_args(payload: &Path, output: &Path, extra: &[&str]) -> Vec<String> {
        let mut values = [
            "--payload",
            &payload.display().to_string(),
            "--asset-id",
            PFUSDC,
            "--source-address",
            OWNER_0,
            "--source-pubkey",
            &validator_key(0),
            "--sequence",
            "7",
            "--amount-atoms",
            "100000",
            "--nonce",
            &"11".repeat(32),
            "--output",
            &output.display().to_string(),
        ]
        .map(String::from)
        .to_vec();
        values.extend(extra.iter().map(|value| value.to_string()));
        args(&values)
    }

    fn intent_args(payload: &Path, output: &Path, extra: &[&str]) -> Vec<String> {
        let mut values = [
            "--payload",
            &payload.display().to_string(),
            "--owner-0-address",
            OWNER_0,
            "--owner-0-pubkey",
            &validator_key(0),
            "--object-0-id",
            &"22".repeat(32),
            "--object-0-version",
            "1",
            "--amount-0",
            "100000",
            "--owner-1-address",
            OWNER_1,
            "--owner-1-pubkey",
            &validator_key(1),
            "--object-1-id",
            &"33".repeat(32),
            "--object-1-version",
            "1",
            "--amount-1",
            "100000",
            "--expires-at-height",
            "200",
            "--rfq",
            "rh-20261021-fs",
            "--nonce",
            &"44".repeat(32),
            "--output",
            &output.display().to_string(),
        ]
        .map(String::from)
        .to_vec();
        values.extend(extra.iter().map(|value| value.to_string()));
        args(&values)
    }

    fn committee_file() -> String {
        fixture("activate-committee.json").display().to_string()
    }

    #[test]
    fn epoch_two_fixture_is_the_recorded_activation_payload() {
        assert_eq!(
            sha256_hex(&fs::read(fixture("payload-epoch2.json")).unwrap()),
            EPOCH_2_PAYLOAD_SHA256
        );
    }

    #[test]
    fn epoch_one_activation_keeps_the_deposit_and_intent_bytes() {
        let payload = payload_with_epoch(1);
        let deposit_out = scratch("deposit.json");
        deposit(&deposit_args(&payload, &deposit_out, &[])).expect("epoch-1 deposit");
        assert_eq!(
            sha256_hex(&fs::read(&deposit_out).unwrap()),
            EPOCH_1_DEPOSIT_SHA256
        );
        let intent_out = scratch("intent.json");
        intent(&intent_args(&payload, &intent_out, &[])).expect("epoch-1 intent");
        assert_eq!(
            sha256_hex(&fs::read(&intent_out).unwrap()),
            EPOCH_1_INTENT_SHA256
        );
    }

    #[test]
    fn epoch_two_activation_builds_deposit_and_intent_under_epoch_two() {
        let payload = fixture("payload-epoch2.json");
        let deposit_out = scratch("deposit.json");
        deposit(&deposit_args(&payload, &deposit_out, &[])).expect("epoch-2 deposit");
        let built: FastLaneDepositV1 =
            serde_json::from_slice(&fs::read(&deposit_out).unwrap()).unwrap();
        let activation = read_payload(&payload, None).expect("epoch-2 activation");
        assert_eq!(built.domain, activation.committee.domain.chain);
        let intent_out = scratch("intent.json");
        intent(&intent_args(&payload, &intent_out, &[])).expect("epoch-2 intent");
        let built: FastSwapIntentV1 =
            serde_json::from_slice(&fs::read(&intent_out).unwrap()).unwrap();
        assert_eq!(built.domain.committee_epoch, 2);
        assert_eq!(
            postfiat_crypto_provider::bytes_to_hex(&built.domain.committee_root.0),
            EPOCH_2_ROOT
        );
        let canonical =
            serde_json::to_string(&serde_json::to_value(&built.domain).unwrap()).unwrap();
        assert_eq!(sha256_hex(canonical.as_bytes()), EPOCH_2_DOMAIN_SHA256);
    }

    #[test]
    fn committee_file_equal_to_the_activation_committee_is_accepted() {
        let payload = fixture("payload-epoch2.json");
        let committee = committee_file();
        deposit(&deposit_args(
            &payload,
            &scratch("d.json"),
            &["--committee-file", &committee],
        ))
        .expect("deposit with the recorded committee");
        intent(&intent_args(
            &payload,
            &scratch("i.json"),
            &["--committee-file", &committee],
        ))
        .expect("intent with the recorded committee");
    }

    #[test]
    fn activation_whose_committee_differs_from_the_committee_file_is_refused() {
        // An epoch-1 activation against the recorded epoch-2 committee.
        let payload = payload_with_epoch(1);
        let committee = committee_file();
        for error in [
            deposit(&deposit_args(
                &payload,
                &scratch("d.json"),
                &["--committee-file", &committee],
            )),
            intent(&intent_args(
                &payload,
                &scratch("i.json"),
                &["--committee-file", &committee],
            )),
        ] {
            let error = error.expect_err("refused");
            assert!(error.contains("differs from the committee file"), "{error}");
        }
    }

    #[test]
    fn committee_file_that_does_not_validate_is_refused() {
        let tampered = scratch("committee.json");
        let text = fs::read_to_string(fixture("activate-committee.json")).unwrap();
        fs::write(
            &tampered,
            text.replacen("\"committee_root\":[114,", "\"committee_root\":[115,", 1),
        )
        .unwrap();
        let tampered = tampered.display().to_string();
        let error = deposit(&deposit_args(
            &fixture("payload-epoch2.json"),
            &scratch("d.json"),
            &["--committee-file", &tampered],
        ))
        .expect_err("refused");
        assert!(error.contains("root"), "{error}");
    }

    #[test]
    fn committee_epoch_zero_is_refused() {
        let error = deposit(&deposit_args(
            &payload_with_epoch(0),
            &scratch("d.json"),
            &[],
        ))
        .expect_err("refused");
        assert!(error.contains("invalid bootstrap payload"), "{error}");
    }

    #[test]
    fn quote_uses_governed_down_rounding_without_narrowing_prices() {
        assert_eq!(quote_asset_1(9, 100_000_000, 820_102_177).unwrap(), 1);
        assert_eq!(quote_asset_1(10, 1, 1).unwrap(), 10);
        assert!(quote_asset_1(1, 1, 0).is_err());
        assert!(quote_asset_1(u64::MAX, u128::MAX, 1).is_err());
    }
}
