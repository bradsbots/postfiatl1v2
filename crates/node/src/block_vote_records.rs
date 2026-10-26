//! Per-height vote outcome records for the native reliability input
//! (SCT-08 item 4, decision of 2026-10-23 in
//! `docs/review/sct08-evidence-campaign-20261023.md`).
//!
//! A record lists every validator the proposer's round asked for a block vote
//! and the outcome: an accepted vote with its vote id, a refusal with a reason
//! class, or no answer by the round deadline. Votes that arrive after the
//! quorum are included and marked. The record is an observation kept beside
//! the block: it is never read by consensus, voting, certificate or state
//! commitment code, and a failed write never fails the round or the commit.

use std::{
    io,
    path::{Path, PathBuf},
};

use serde::{Deserialize, Serialize};

pub const BLOCK_VOTE_RECORD_DIR: &str = "block-vote-records";
pub const BLOCK_VOTE_RECORD_SCHEMA: &str = "postfiat.block_vote_record.v1";
const MAX_BLOCK_VOTE_RECORD_BYTES: u64 = 256 * 1024;
const MAX_BLOCK_VOTE_RECORD_ENTRIES: usize = 1024;
const MAX_REFUSAL_CLASS_CHARS: usize = 64;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum BlockVoteOutcome {
    Accepted,
    Refused,
    NoAnswer,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct BlockVoteRecordEntry {
    pub validator: String,
    pub outcome: BlockVoteOutcome,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub vote_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub refusal_class: Option<String>,
    /// The answer arrived after the round already held its quorum of votes.
    pub answered_after_quorum: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct BlockVoteRecord {
    pub schema: String,
    pub chain_id: String,
    pub block_height: u64,
    pub view: u64,
    pub block_hash: String,
    pub certificate_id: String,
    pub proposer: String,
    pub quorum: usize,
    /// Answers later than this many milliseconds after the vote requests
    /// started are recorded as `no_answer`.
    pub round_deadline_ms: u64,
    /// One entry per requested validator, sorted by validator id; the
    /// proposer's own vote is included.
    pub entries: Vec<BlockVoteRecordEntry>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BlockVoteRecordWrite {
    Written,
    /// A record for this height and block already exists; it is kept as is.
    AlreadyRecorded,
    /// A record for this height names another block; it is kept and the new
    /// record is not written.
    Conflict {
        existing_block_hash: String,
    },
}

impl BlockVoteRecordWrite {
    pub fn label(&self) -> String {
        match self {
            Self::Written => "written".to_string(),
            Self::AlreadyRecorded => "already_recorded".to_string(),
            Self::Conflict {
                existing_block_hash,
            } => format!("conflict_kept_existing:{existing_block_hash}"),
        }
    }
}

pub fn block_vote_record_dir(data_dir: &Path) -> PathBuf {
    data_dir.join(BLOCK_VOTE_RECORD_DIR)
}

pub fn block_vote_record_path(data_dir: &Path, block_height: u64) -> PathBuf {
    block_vote_record_dir(data_dir).join(format!("height-{block_height:020}.json"))
}

fn invalid(message: impl Into<String>) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, message.into())
}

pub fn validate_block_vote_record(record: &BlockVoteRecord) -> io::Result<()> {
    if record.schema != BLOCK_VOTE_RECORD_SCHEMA {
        return Err(invalid(format!(
            "block vote record schema `{}` is not supported",
            record.schema
        )));
    }
    if record.block_height == 0 || record.block_hash.trim().is_empty() {
        return Err(invalid("block vote record needs a height and a block hash"));
    }
    if record.entries.is_empty() || record.entries.len() > MAX_BLOCK_VOTE_RECORD_ENTRIES {
        return Err(invalid("block vote record entry count is out of range"));
    }
    if !record
        .entries
        .windows(2)
        .all(|pair| pair[0].validator < pair[1].validator)
    {
        return Err(invalid(
            "block vote record entries must be sorted by unique validator id",
        ));
    }
    for entry in &record.entries {
        let consistent = match entry.outcome {
            BlockVoteOutcome::Accepted => {
                entry.vote_id.as_deref().is_some_and(|id| !id.is_empty())
                    && entry.refusal_class.is_none()
            }
            BlockVoteOutcome::Refused => {
                entry.vote_id.is_none()
                    && entry.refusal_class.as_deref().is_some_and(|class| {
                        !class.is_empty() && class.len() <= MAX_REFUSAL_CLASS_CHARS
                    })
            }
            BlockVoteOutcome::NoAnswer => {
                entry.vote_id.is_none()
                    && entry.refusal_class.is_none()
                    && !entry.answered_after_quorum
            }
        };
        if entry.validator.trim().is_empty() || !consistent {
            return Err(invalid(format!(
                "block vote record entry for `{}` is inconsistent",
                entry.validator
            )));
        }
    }
    if !record
        .entries
        .iter()
        .any(|entry| entry.validator == record.proposer)
    {
        return Err(invalid("block vote record omits the proposer"));
    }
    Ok(())
}

pub fn read_block_vote_record(
    data_dir: &Path,
    block_height: u64,
) -> io::Result<Option<BlockVoteRecord>> {
    let path = block_vote_record_path(data_dir, block_height);
    let metadata = match std::fs::symlink_metadata(&path) {
        Ok(metadata) => metadata,
        Err(error) if error.kind() == io::ErrorKind::NotFound => return Ok(None),
        Err(error) => return Err(error),
    };
    if !metadata.is_file() || metadata.len() > MAX_BLOCK_VOTE_RECORD_BYTES {
        return Err(invalid(format!(
            "block vote record `{}` is not a bounded regular file",
            path.display()
        )));
    }
    let record: BlockVoteRecord =
        serde_json::from_slice(&std::fs::read(&path)?).map_err(|error| {
            invalid(format!(
                "block vote record `{}` parse failed: {error}",
                path.display()
            ))
        })?;
    validate_block_vote_record(&record)?;
    if record.block_height != block_height {
        return Err(invalid(format!(
            "block vote record `{}` names height {}",
            path.display(),
            record.block_height
        )));
    }
    Ok(Some(record))
}

/// Writes the record once per height. Callers run this only after the block
/// and its receipts are durable. A rerun after a restart finds the existing
/// record and leaves it; a record for another block at the same height is
/// never overwritten.
pub fn write_block_vote_record(
    data_dir: &Path,
    record: &BlockVoteRecord,
) -> io::Result<BlockVoteRecordWrite> {
    validate_block_vote_record(record)?;
    match read_block_vote_record(data_dir, record.block_height) {
        Ok(Some(existing)) if existing.block_hash == record.block_hash => {
            return Ok(BlockVoteRecordWrite::AlreadyRecorded);
        }
        Ok(Some(existing)) => {
            return Ok(BlockVoteRecordWrite::Conflict {
                existing_block_hash: existing.block_hash,
            });
        }
        Ok(None) => {}
        Err(error) => return Err(error),
    }
    let mut bytes =
        serde_json::to_vec_pretty(record).map_err(|error| invalid(error.to_string()))?;
    bytes.push(b'\n');
    if bytes.len() as u64 > MAX_BLOCK_VOTE_RECORD_BYTES {
        return Err(invalid("block vote record is oversized"));
    }
    postfiat_storage::atomic_write(block_vote_record_path(data_dir, record.block_height), bytes)?;
    Ok(BlockVoteRecordWrite::Written)
}

/// A bounded, path-free class for a validator's refusal text: the innermost
/// clause with quoted values removed, as lowercase words joined by `_`.
pub fn vote_refusal_class(error: &str) -> String {
    let mut unquoted = String::with_capacity(error.len());
    let mut in_quote = false;
    for character in error.chars() {
        if character == '`' {
            in_quote = !in_quote;
            continue;
        }
        if !in_quote {
            unquoted.push(character);
        }
    }
    let clause = unquoted
        .rsplit(": ")
        .find(|clause| clause.chars().any(|c| c.is_ascii_alphabetic()))
        .unwrap_or("");
    let mut class = String::new();
    for character in clause.chars() {
        if character.is_ascii_alphanumeric() {
            class.push(character.to_ascii_lowercase());
        } else if !class.is_empty() && !class.ends_with('_') {
            class.push('_');
        }
        if class.len() >= MAX_REFUSAL_CLASS_CHARS {
            break;
        }
    }
    let class = class.trim_end_matches('_').to_string();
    if class.is_empty() {
        "unspecified".to_string()
    } else {
        class
    }
}

/// What the snapshot export and the reliability window read per height:
/// the record, or `None` when no record exists ("not available").
pub fn block_vote_records_for_heights(
    data_dir: &Path,
    from_height: u64,
    to_height: u64,
) -> io::Result<Vec<(u64, Option<BlockVoteRecord>)>> {
    if from_height == 0 || from_height > to_height {
        return Err(invalid("block vote record height range is invalid"));
    }
    (from_height..=to_height)
        .map(|height| read_block_vote_record(data_dir, height).map(|record| (height, record)))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp_data_dir(label: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "postfiat-block-vote-records-{label}-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .expect("clock")
                .as_nanos()
        ));
        std::fs::create_dir_all(&dir).expect("create temp data dir");
        dir
    }

    fn record(height: u64, block_hash: &str) -> BlockVoteRecord {
        BlockVoteRecord {
            schema: BLOCK_VOTE_RECORD_SCHEMA.to_string(),
            chain_id: "postfiat-test".to_string(),
            block_height: height,
            view: 0,
            block_hash: block_hash.to_string(),
            certificate_id: format!("cert-{height}"),
            proposer: "validator-0".to_string(),
            quorum: 3,
            round_deadline_ms: 5_000,
            entries: vec![
                BlockVoteRecordEntry {
                    validator: "validator-0".to_string(),
                    outcome: BlockVoteOutcome::Accepted,
                    vote_id: Some("vote-0".to_string()),
                    refusal_class: None,
                    answered_after_quorum: false,
                },
                BlockVoteRecordEntry {
                    validator: "validator-1".to_string(),
                    outcome: BlockVoteOutcome::Refused,
                    vote_id: None,
                    refusal_class: Some(
                        "conflicting_block_proposal_vote_already_recorded".to_string(),
                    ),
                    answered_after_quorum: false,
                },
                BlockVoteRecordEntry {
                    validator: "validator-2".to_string(),
                    outcome: BlockVoteOutcome::NoAnswer,
                    vote_id: None,
                    refusal_class: None,
                    answered_after_quorum: false,
                },
                BlockVoteRecordEntry {
                    validator: "validator-3".to_string(),
                    outcome: BlockVoteOutcome::Accepted,
                    vote_id: Some("vote-3".to_string()),
                    refusal_class: None,
                    answered_after_quorum: true,
                },
            ],
        }
    }

    #[test]
    fn block_vote_record_write_is_idempotent_across_restart_and_never_overwrites() {
        let data_dir = temp_data_dir("idempotent");
        let first = record(7, "hash-a");
        assert_eq!(
            write_block_vote_record(&data_dir, &first).expect("first write"),
            BlockVoteRecordWrite::Written
        );
        let path = block_vote_record_path(&data_dir, 7);
        let written = std::fs::read(&path).expect("record bytes");

        // A restarted round or commit retries the same height.
        assert_eq!(
            write_block_vote_record(&data_dir, &first).expect("rerun"),
            BlockVoteRecordWrite::AlreadyRecorded
        );
        let mut later = first.clone();
        later.entries[2].outcome = BlockVoteOutcome::Accepted;
        later.entries[2].vote_id = Some("vote-2".to_string());
        assert_eq!(
            write_block_vote_record(&data_dir, &later).expect("rerun with other outcomes"),
            BlockVoteRecordWrite::AlreadyRecorded
        );
        assert_eq!(
            write_block_vote_record(&data_dir, &record(7, "hash-b")).expect("other block"),
            BlockVoteRecordWrite::Conflict {
                existing_block_hash: "hash-a".to_string()
            }
        );
        assert_eq!(std::fs::read(&path).expect("record bytes"), written);
        assert_eq!(
            read_block_vote_record(&data_dir, 7).expect("read"),
            Some(first)
        );
        std::fs::remove_dir_all(&data_dir).expect("cleanup");
    }

    #[test]
    fn block_vote_records_report_not_available_for_heights_without_a_record() {
        let data_dir = temp_data_dir("not-available");
        write_block_vote_record(&data_dir, &record(2, "hash-2")).expect("write");
        let rows = block_vote_records_for_heights(&data_dir, 1, 3).expect("rows");
        assert_eq!(rows.len(), 3);
        assert_eq!(rows[0], (1, None));
        assert_eq!(rows[1].0, 2);
        assert_eq!(
            rows[1].1.as_ref().map(|r| r.block_hash.as_str()),
            Some("hash-2")
        );
        assert_eq!(rows[2], (3, None));
        std::fs::remove_dir_all(&data_dir).expect("cleanup");
    }

    #[test]
    fn block_vote_record_rejects_inconsistent_or_tampered_records() {
        let data_dir = temp_data_dir("tampered");
        let mut unsorted = record(4, "hash-4");
        unsorted.entries.swap(0, 1);
        assert!(write_block_vote_record(&data_dir, &unsorted).is_err());
        let mut no_answer_with_id = record(4, "hash-4");
        no_answer_with_id.entries[2].vote_id = Some("vote-2".to_string());
        assert!(write_block_vote_record(&data_dir, &no_answer_with_id).is_err());
        write_block_vote_record(&data_dir, &record(4, "hash-4")).expect("write");
        let path = block_vote_record_path(&data_dir, 4);
        let tampered = std::fs::read_to_string(&path)
            .expect("record")
            .replace("\"block_height\": 4", "\"block_height\": 5");
        std::fs::write(&path, tampered).expect("tamper");
        assert!(read_block_vote_record(&data_dir, 4).is_err());
        std::fs::remove_dir_all(&data_dir).expect("cleanup");
    }

    #[test]
    fn vote_refusal_class_is_bounded_and_drops_quoted_values() {
        let error = "transport block vote request to `validator-2` failed after 1 attempts: \
                     attempt 1: transport block vote rejected by `validator-2` for \
                     `block_vote_request`: transport block vote signing failed: \
                     conflicting block proposal vote already recorded";
        assert_eq!(
            vote_refusal_class(error),
            "conflicting_block_proposal_vote_already_recorded"
        );
        assert_eq!(
            vote_refusal_class("rejected: vote file `/var/lib/postfiat/x.json` exists"),
            "vote_file_exists"
        );
        assert_eq!(vote_refusal_class("``"), "unspecified");
        assert!(vote_refusal_class(&"a".repeat(500)).len() <= MAX_REFUSAL_CLASS_CHARS);
    }
}
