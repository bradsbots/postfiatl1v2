//! Strict entry profile rule module (Z2 step 3), `postfiat.validator_entry_profile.v1`.
//!
//! A pure, deterministic, integer-only rule module. It decides which entry
//! profile applies to one operator in one round, and whether the operator may
//! take a new seat. It follows the locked identity flag pipeline specification
//! (`docs/specs/identity-flag-pipeline-spec-20261023.md`, sections 3, 4 and 7):
//!
//! - `meets_strict_profile` never reads a flag. Under `entry_profile_v1` it
//!   needs a verified domain and at least `required_clean_rounds` consecutive
//!   clean rounds ending at the round before the current one. Under
//!   `interim_domain_only` it needs a verified domain.
//! - A round is clean for an operator when it is present in that round's frozen
//!   final scores, its domain was verified, and its final score is at or above
//!   the round's cutoff. This is the proposed default, pending its decision line.
//! - `identity_flag` is `flag` only when an admissible model classification is
//!   `flag` and the strict profile is not met; otherwise `clear`.
//! - `resolve_flag_input` gives `none` for a missing artifact, a wrong schema, a
//!   non-shadow artifact, a pin mismatch, an absent or duplicated operator, or
//!   an unknown flag value.
//! - A flag input of `none` or `clear` selects the standard profile, and `flag`
//!   selects the strict one. A flag never removes an incumbent and only
//!   withholds a new seat.
//!
//! The module is `SHADOW_ONLY`. No consensus path calls it, and the existing
//! admission policy (`validator_admission_policy.rs`) is unchanged. Step 4 of
//! the Z2 plan wires it in. The Python mirror is
//! `python/postfiat_rpc/validator_entry_profile.py`. It shares no code with this
//! module and must produce byte-identical canonical JSON on every shared
//! fixture.

use serde_json::Value;

pub const VALIDATOR_ENTRY_PROFILE_SCHEMA: &str = "postfiat.validator_entry_profile.v1";
pub const VALIDATOR_ENTRY_PROFILE_VERSION: u32 = 1;
pub const VALIDATOR_ENTRY_PROFILE_DECISION_SCHEMA: &str =
    "postfiat.validator_entry_profile.decision.v1";
pub const VALIDATOR_ENTRY_PROFILE_PARAMETERS_SCHEMA: &str =
    "postfiat.validator_entry_profile.parameters.v1";
pub const IDENTITY_FLAG_ARTIFACT_SCHEMA: &str = "postfiat.identity_flag.v1";

/// A refused input; the payload is a stable error code shared with the mirror.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EntryProfileError(pub &'static str);

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StrictProfileRule {
    EntryProfileV1,
    InterimDomainOnly,
}

impl StrictProfileRule {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::EntryProfileV1 => "entry_profile_v1",
            Self::InterimDomainOnly => "interim_domain_only",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EntryProfileParameters {
    pub required_clean_rounds: u64,
    pub strict_profile_rule: StrictProfileRule,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HistoryRound {
    pub round_number: u64,
    pub final_scores_sha256: String,
    pub present: bool,
    pub domain_verified: bool,
    pub final_score: u64,
    pub score_cutoff: u64,
}

impl HistoryRound {
    fn is_clean(&self) -> bool {
        self.present && self.domain_verified && self.final_score >= self.score_cutoff
    }
}

/// The inputs `meets_strict_profile` reads. It takes no flag.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StrictProfileInput {
    pub current_round: u64,
    pub domain_verified: bool,
    pub history: Vec<HistoryRound>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FlagInput {
    None,
    Clear,
    Flag,
}

impl FlagInput {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::None => "none",
            Self::Clear => "clear",
            Self::Flag => "flag",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ModelClassification {
    /// No admissible classification (missing, divergent, truncated, invalid).
    None,
    Clear,
    Flag,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IdentityFlag {
    Clear,
    Flag,
}

impl IdentityFlag {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Clear => "clear",
            Self::Flag => "flag",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OperatorRound {
    pub validator_id: String,
    pub incumbent: bool,
    pub flag: FlagInput,
    pub strict: StrictProfileInput,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Profile {
    Standard,
    Strict,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Seat {
    KeepsSeat,
    MayTakeNewSeat,
    NewSeatWithheld,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EntryProfileDecision {
    pub clean_rounds: u64,
    pub current_round: u64,
    pub meets_strict_profile: bool,
    pub profile: Profile,
    pub reasons: Vec<&'static str>,
    pub seat: Seat,
    pub strict_profile_rule: StrictProfileRule,
    pub validator_id: String,
}

impl EntryProfileDecision {
    /// Sorted-key, compact, ASCII-escaped JSON: the bytes both sides must agree on.
    pub fn canonical_json(&self) -> String {
        let mut out = format!(
            "{{\"clean_rounds\":{},\"current_round\":{},\"meets_strict_profile\":{},\"profile\":",
            self.clean_rounds, self.current_round, self.meets_strict_profile
        );
        push_canonical_json_string(
            &mut out,
            match self.profile {
                Profile::Standard => "standard",
                Profile::Strict => "strict",
            },
        );
        out.push_str(",\"reasons\":[");
        for (index, reason) in self.reasons.iter().enumerate() {
            if index > 0 {
                out.push(',');
            }
            push_canonical_json_string(&mut out, reason);
        }
        out.push_str("],\"schema\":");
        push_canonical_json_string(&mut out, VALIDATOR_ENTRY_PROFILE_DECISION_SCHEMA);
        out.push_str(",\"seat\":");
        push_canonical_json_string(
            &mut out,
            match self.seat {
                Seat::KeepsSeat => "keeps_seat",
                Seat::MayTakeNewSeat => "may_take_new_seat",
                Seat::NewSeatWithheld => "new_seat_withheld",
            },
        );
        out.push_str(",\"shadow_only\":true,\"strict_profile_rule\":");
        push_canonical_json_string(&mut out, self.strict_profile_rule.as_str());
        out.push_str(",\"validator_id\":");
        push_canonical_json_string(&mut out, &self.validator_id);
        out.push('}');
        out
    }
}

/// JSON string escaping identical to Python's `json.dumps(ensure_ascii=True)`.
pub fn push_canonical_json_string(out: &mut String, text: &str) {
    out.push('"');
    for ch in text.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{08}' => out.push_str("\\b"),
            '\u{0c}' => out.push_str("\\f"),
            ch if (ch as u32) < 0x20 || (ch as u32) > 0x7e => {
                let mut units = [0u16; 2];
                for unit in ch.encode_utf16(&mut units) {
                    out.push_str(&format!("\\u{unit:04x}"));
                }
            }
            ch => out.push(ch),
        }
    }
    out.push('"');
}

/// Unbroken clean rounds ending at `current_round - 1`. A gap stops the count.
pub fn consecutive_clean_rounds(history: &[HistoryRound], current_round: u64) -> u64 {
    let mut count = 0;
    let mut expected = current_round.checked_sub(1);
    while let Some(round_number) = expected {
        match history.iter().find(|row| row.round_number == round_number) {
            Some(row) if row.is_clean() => count += 1,
            _ => break,
        }
        expected = round_number.checked_sub(1);
    }
    count
}

/// Whether the operator meets the strict entry profile. It never reads a flag.
pub fn meets_strict_profile(
    parameters: &EntryProfileParameters,
    input: &StrictProfileInput,
) -> bool {
    match parameters.strict_profile_rule {
        StrictProfileRule::InterimDomainOnly => input.domain_verified,
        StrictProfileRule::EntryProfileV1 => {
            input.domain_verified
                && consecutive_clean_rounds(&input.history, input.current_round)
                    >= parameters.required_clean_rounds
        }
    }
}

/// The spec's flag rule: an admissible model `flag` and an unmet strict profile.
pub fn identity_flag(model: ModelClassification, strict_profile_met: bool) -> IdentityFlag {
    if model == ModelClassification::Flag && !strict_profile_met {
        IdentityFlag::Flag
    } else {
        IdentityFlag::Clear
    }
}

/// Step 3's flag input from a flags artifact. Any defect gives `none`.
pub fn resolve_flag_input(
    artifact: Option<&Value>,
    expected_pins: &Value,
    validator_id: &str,
) -> FlagInput {
    let Some(artifact) = artifact.and_then(Value::as_object) else {
        return FlagInput::None;
    };
    if artifact.get("schema").and_then(Value::as_str) != Some(IDENTITY_FLAG_ARTIFACT_SCHEMA)
        || artifact.get("shadow_only") != Some(&Value::Bool(true))
        || artifact.get("pins") != Some(expected_pins)
    {
        return FlagInput::None;
    }
    let Some(operators) = artifact.get("operators").and_then(Value::as_array) else {
        return FlagInput::None;
    };
    let mut matches = operators.iter().filter(|row| {
        row.as_object()
            .and_then(|row| row.get("validator_id"))
            .and_then(Value::as_str)
            == Some(validator_id)
    });
    let (Some(only), None) = (matches.next(), matches.next()) else {
        return FlagInput::None;
    };
    match only.get("identity_flag").and_then(Value::as_str) {
        Some("clear") => FlagInput::Clear,
        Some("flag") => FlagInput::Flag,
        _ => FlagInput::None,
    }
}

/// The entry-profile decision for one operator in one round.
pub fn evaluate(
    parameters: &EntryProfileParameters,
    operator: &OperatorRound,
) -> EntryProfileDecision {
    let clean_rounds =
        consecutive_clean_rounds(&operator.strict.history, operator.strict.current_round);
    let met = meets_strict_profile(parameters, &operator.strict);
    let profile = if operator.flag == FlagInput::Flag {
        Profile::Strict
    } else {
        Profile::Standard
    };
    let mut reasons = vec![match operator.flag {
        FlagInput::None => "no_flag_input_standard_profile",
        FlagInput::Clear => "flag_clear_standard_profile",
        FlagInput::Flag => "flag_selects_strict_profile",
    }];
    let seat = if operator.incumbent {
        reasons.push("incumbent_keeps_seat");
        Seat::KeepsSeat
    } else if profile == Profile::Standard || met {
        Seat::MayTakeNewSeat
    } else {
        Seat::NewSeatWithheld
    };
    if profile == Profile::Strict {
        if met {
            reasons.push("strict_profile_met");
        } else {
            if !operator.strict.domain_verified {
                reasons.push("strict_domain_not_verified");
            }
            if parameters.strict_profile_rule == StrictProfileRule::EntryProfileV1
                && clean_rounds < parameters.required_clean_rounds
            {
                reasons.push("strict_clean_rounds_below_required");
            }
        }
    }
    reasons.sort_unstable();
    EntryProfileDecision {
        clean_rounds,
        current_round: operator.strict.current_round,
        meets_strict_profile: met,
        profile,
        reasons,
        seat,
        strict_profile_rule: parameters.strict_profile_rule,
        validator_id: operator.validator_id.clone(),
    }
}

// --- Input parsing, with the error codes the mirror uses, in the same order ---

fn uint(value: Option<&Value>, code: &'static str) -> Result<u64, EntryProfileError> {
    value.and_then(Value::as_u64).ok_or(EntryProfileError(code))
}

fn boolean(value: Option<&Value>, code: &'static str) -> Result<bool, EntryProfileError> {
    value
        .and_then(Value::as_bool)
        .ok_or(EntryProfileError(code))
}

pub fn parse_parameters(value: &Value) -> Result<EntryProfileParameters, EntryProfileError> {
    if value.get("schema").and_then(Value::as_str)
        != Some(VALIDATOR_ENTRY_PROFILE_PARAMETERS_SCHEMA)
    {
        return Err(EntryProfileError("parameters_schema_unsupported"));
    }
    let required_clean_rounds = uint(
        value.get("required_clean_rounds"),
        "parameters_required_clean_rounds_invalid",
    )?;
    if required_clean_rounds < 1 {
        return Err(EntryProfileError(
            "parameters_required_clean_rounds_invalid",
        ));
    }
    if value.get("require_verified_domain") != Some(&Value::Bool(true)) {
        return Err(EntryProfileError(
            "parameters_require_verified_domain_must_be_true",
        ));
    }
    let strict_profile_rule = match value.get("strict_profile_rule").and_then(Value::as_str) {
        Some("entry_profile_v1") => StrictProfileRule::EntryProfileV1,
        Some("interim_domain_only") => StrictProfileRule::InterimDomainOnly,
        _ => {
            return Err(EntryProfileError(
                "parameters_strict_profile_rule_unsupported",
            ))
        }
    };
    Ok(EntryProfileParameters {
        required_clean_rounds,
        strict_profile_rule,
    })
}

fn is_hex64(text: &str) -> bool {
    text.len() == 64
        && text
            .bytes()
            .all(|byte| matches!(byte, b'0'..=b'9' | b'a'..=b'f'))
}

fn parse_history(
    value: Option<&Value>,
    current_round: u64,
) -> Result<Vec<HistoryRound>, EntryProfileError> {
    let rows = match value {
        None => return Ok(Vec::new()),
        Some(Value::Array(rows)) => rows,
        Some(_) => return Err(EntryProfileError("history_invalid")),
    };
    let mut out: Vec<HistoryRound> = Vec::with_capacity(rows.len());
    for row in rows {
        if !row.is_object() {
            return Err(EntryProfileError("history_round_invalid"));
        }
        let round_number = uint(row.get("round_number"), "history_round_number_invalid")?;
        if round_number >= current_round {
            return Err(EntryProfileError("history_round_not_before_current"));
        }
        if out.iter().any(|seen| seen.round_number == round_number) {
            return Err(EntryProfileError("history_round_duplicated"));
        }
        let final_scores_sha256 = match row.get("final_scores_sha256").and_then(Value::as_str) {
            Some(text) if is_hex64(text) => text.to_owned(),
            _ => return Err(EntryProfileError("history_final_scores_sha256_invalid")),
        };
        out.push(HistoryRound {
            round_number,
            final_scores_sha256,
            present: boolean(row.get("present"), "history_present_invalid")?,
            domain_verified: boolean(
                row.get("domain_verified"),
                "history_domain_verified_invalid",
            )?,
            final_score: uint(row.get("final_score"), "history_final_score_invalid")?,
            score_cutoff: uint(row.get("score_cutoff"), "history_score_cutoff_invalid")?,
        });
    }
    Ok(out)
}

/// The flag-independent inputs of one operator.
pub fn parse_strict_input(value: &Value) -> Result<StrictProfileInput, EntryProfileError> {
    let current_round = uint(value.get("current_round"), "operator_current_round_invalid")?;
    let domain_verified = boolean(
        value.get("domain_verified"),
        "operator_domain_verified_invalid",
    )?;
    let history = parse_history(value.get("history"), current_round)?;
    Ok(StrictProfileInput {
        current_round,
        domain_verified,
        history,
    })
}

pub fn parse_operator(value: &Value) -> Result<OperatorRound, EntryProfileError> {
    let validator_id = match value.get("validator_id").and_then(Value::as_str) {
        Some(text) if !text.is_empty() => text.to_owned(),
        _ => return Err(EntryProfileError("operator_validator_id_invalid")),
    };
    let current_round = uint(value.get("current_round"), "operator_current_round_invalid")?;
    let incumbent = boolean(value.get("incumbent"), "operator_incumbent_invalid")?;
    let domain_verified = boolean(
        value.get("domain_verified"),
        "operator_domain_verified_invalid",
    )?;
    let flag = match value.get("flag").and_then(Value::as_str) {
        Some("none") => FlagInput::None,
        Some("clear") => FlagInput::Clear,
        Some("flag") => FlagInput::Flag,
        _ => return Err(EntryProfileError("operator_flag_unsupported")),
    };
    let history = parse_history(value.get("history"), current_round)?;
    Ok(OperatorRound {
        validator_id,
        incumbent,
        flag,
        strict: StrictProfileInput {
            current_round,
            domain_verified,
            history,
        },
    })
}

pub fn parse_model_classification(value: &Value) -> Result<ModelClassification, EntryProfileError> {
    match value.as_str() {
        Some("none") => Ok(ModelClassification::None),
        Some("clear") => Ok(ModelClassification::Clear),
        Some("flag") => Ok(ModelClassification::Flag),
        _ => Err(EntryProfileError("model_classification_unsupported")),
    }
}
