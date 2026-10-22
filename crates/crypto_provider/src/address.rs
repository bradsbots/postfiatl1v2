//! PFTL account address parsing, validation and checksummed display.
//!
//! The canonical on-chain address is `pf` followed by the 40 lowercase hex
//! characters of the first 20 bytes of
//! SHA3-384(`postfiat.address.v1` || 0x00 || ML-DSA-65 public key).
//!
//! The optional checksum is a mixed-case encoding of the same 40 hex
//! characters, in the style of EIP-55 but domain-separated with this chain's
//! SHA3 family:
//!
//! ```text
//! h = SHA3-256("postfiat.address.checksum.v1" || 0x00 || lowercase_hex40)
//! for i in 0..40:
//!     if hex40[i] is a letter a-f and nibble i of h >= 8: uppercase it
//! ```
//!
//! Nibble `i` is the high nibble of `h[i / 2]` when `i` is even and the low
//! nibble when `i` is odd. The `pf` prefix is never uppercased and is not
//! part of the hashed input.
//!
//! Parsers accept the all-lowercase (legacy) form and the exact checksummed
//! form. Any other use of uppercase hex is a checksum failure. Signed
//! transactions must always carry the canonical lowercase form.

use sha3::{Digest, Sha3_256};

/// Prefix of every PFTL account address.
pub const ADDRESS_PREFIX: &str = "pf";
/// Number of hex characters after the prefix.
pub const ADDRESS_HEX_LEN: usize = 40;
/// Total address length in characters.
pub const ADDRESS_LEN: usize = 42;
/// Domain tag of the address derivation hash.
pub const ADDRESS_DERIVATION_DOMAIN: &str = "postfiat.address.v1";
/// Domain tag of the mixed-case checksum hash.
pub const ADDRESS_CHECKSUM_DOMAIN: &str = "postfiat.address.checksum.v1";

/// Receipt and RPC error code for a destination field that is not
/// `pf` + 40 hex characters.
pub const INVALID_RECIPIENT_ADDRESS_CODE: &str = "invalid_recipient_address";
/// Receipt and RPC error code for a mixed-case destination whose checksum
/// does not verify.
pub const INVALID_RECIPIENT_CHECKSUM_CODE: &str = "invalid_recipient_checksum";
/// Receipt and RPC error code for a correctly checksummed destination in a
/// signed transaction. Signed transactions must carry the lowercase form.
pub const NONCANONICAL_RECIPIENT_ADDRESS_CODE: &str = "noncanonical_recipient_address";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AddressError {
    /// The input does not start with `pf` in any letter case.
    MissingPrefix,
    /// The input starts with `PF`, `Pf` or `pF`. The prefix is always lowercase.
    UppercasePrefix,
    /// The input is not exactly 42 characters long.
    WrongLength,
    /// The 40 characters after the prefix are not all hex digits.
    NonHex,
    /// The hex part uses uppercase letters but is not the checksummed form.
    BadChecksum,
    /// The address is a valid checksummed form, but the context requires the
    /// canonical lowercase form (for example a signed transaction field).
    NotCanonical,
}

impl AddressError {
    /// Stable machine-readable reason, also used by the published vectors.
    pub const fn reason(self) -> &'static str {
        match self {
            Self::MissingPrefix => "missing_prefix",
            Self::UppercasePrefix => "uppercase_prefix",
            Self::WrongLength => "wrong_length",
            Self::NonHex => "non_hex",
            Self::BadChecksum => "bad_checksum",
            Self::NotCanonical => "not_canonical",
        }
    }

    /// `true` for structural failures, `false` for checksum and case failures.
    pub const fn is_malformed(self) -> bool {
        matches!(
            self,
            Self::MissingPrefix | Self::UppercasePrefix | Self::WrongLength | Self::NonHex
        )
    }

    /// Receipt and RPC error code for a destination field with this error.
    pub const fn recipient_error_code(self) -> &'static str {
        match self {
            Self::BadChecksum => INVALID_RECIPIENT_CHECKSUM_CODE,
            Self::NotCanonical => NONCANONICAL_RECIPIENT_ADDRESS_CODE,
            Self::MissingPrefix | Self::UppercasePrefix | Self::WrongLength | Self::NonHex => {
                INVALID_RECIPIENT_ADDRESS_CODE
            }
        }
    }
}

// These messages and the recipient error codes appear in rejected receipts
// once the recipient-format rule is active. Treat them as stable: changing
// them changes receipts for the same input.
impl std::fmt::Display for AddressError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(match self {
            Self::MissingPrefix => "address must start with `pf`",
            Self::UppercasePrefix => "address prefix must be lowercase `pf`",
            Self::WrongLength => "address must be `pf` followed by exactly 40 hex characters",
            Self::NonHex => "address must be `pf` followed by 40 hex characters (0-9, a-f)",
            Self::BadChecksum => {
                "address checksum does not match; use the all-lowercase form or the exact checksummed form"
            }
            Self::NotCanonical => {
                "address must use the canonical lowercase form in a signed transaction"
            }
        })
    }
}

impl std::error::Error for AddressError {}

/// Checks the prefix, length and hex alphabet and returns the 40-character
/// hex part in its original letter case.
fn address_hex_part(input: &str) -> Result<&str, AddressError> {
    let bytes = input.as_bytes();
    match bytes {
        [b'p', b'f', ..] => {}
        [first, second, ..]
            if first.eq_ignore_ascii_case(&b'p') && second.eq_ignore_ascii_case(&b'f') =>
        {
            return Err(AddressError::UppercasePrefix)
        }
        _ => return Err(AddressError::MissingPrefix),
    }
    // Non-ASCII input is rejected before the length check so the reason does
    // not depend on how an implementation counts string length.
    if !input.is_ascii() {
        return Err(AddressError::NonHex);
    }
    if bytes.len() != ADDRESS_LEN {
        return Err(AddressError::WrongLength);
    }
    let hex = &input[ADDRESS_PREFIX.len()..];
    if !hex.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return Err(AddressError::NonHex);
    }
    Ok(hex)
}

/// Mixed-case checksum encoding of 40 lowercase hex characters.
fn checksum_hex(lowercase_hex: &str) -> String {
    let mut hasher = Sha3_256::new();
    hasher.update(ADDRESS_CHECKSUM_DOMAIN.as_bytes());
    hasher.update([0u8]);
    hasher.update(lowercase_hex.as_bytes());
    let digest = hasher.finalize();
    lowercase_hex
        .bytes()
        .enumerate()
        .map(|(index, byte)| {
            let hash_byte = digest[index / 2];
            let nibble = if index % 2 == 0 {
                hash_byte >> 4
            } else {
                hash_byte & 0x0f
            };
            if byte.is_ascii_alphabetic() && nibble >= 8 {
                byte.to_ascii_uppercase() as char
            } else {
                byte as char
            }
        })
        .collect()
}

/// Parses a human-entered address and returns its canonical lowercase form.
///
/// Accepts the all-lowercase form and the exact checksummed form. Rejects
/// malformed input and any other use of uppercase hex. Does not trim
/// whitespace; callers that accept pasted text should trim first.
pub fn parse_address(input: &str) -> Result<String, AddressError> {
    let hex = address_hex_part(input)?;
    let lowercase = hex.to_ascii_lowercase();
    if hex == lowercase {
        return Ok(format!("{ADDRESS_PREFIX}{lowercase}"));
    }
    if checksum_hex(&lowercase) != hex {
        return Err(AddressError::BadChecksum);
    }
    Ok(format!("{ADDRESS_PREFIX}{lowercase}"))
}

/// `true` when the value is exactly `pf` + 40 lowercase hex characters.
pub fn is_canonical_address(value: &str) -> bool {
    address_hex_part(value).is_ok_and(|hex| !hex.bytes().any(|byte| byte.is_ascii_uppercase()))
}

/// Validates a destination field of a signed transaction. Only the canonical
/// lowercase form is accepted; a correctly checksummed value is reported as
/// [`AddressError::NotCanonical`] so callers can tell the user to normalize.
pub fn validate_canonical_address(value: &str) -> Result<(), AddressError> {
    parse_address(value)?;
    if is_canonical_address(value) {
        Ok(())
    } else {
        Err(AddressError::NotCanonical)
    }
}

/// Returns the checksummed display form of any accepted address.
pub fn checksum_address(address: &str) -> Result<String, AddressError> {
    let canonical = parse_address(address)?;
    Ok(format!(
        "{ADDRESS_PREFIX}{}",
        checksum_hex(&canonical[ADDRESS_PREFIX.len()..])
    ))
}

/// Display helper: the checksummed form when the value is an accepted
/// address, otherwise the value unchanged.
pub fn display_address(value: &str) -> String {
    checksum_address(value).unwrap_or_else(|_| value.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{address_from_public_key, ml_dsa_65_keygen_from_seed};

    const VECTORS_JSON: &str =
        include_str!("../../../docs/fixtures/addresses/pftl-address-vectors-v1.json");

    #[test]
    fn derived_addresses_are_canonical_and_round_trip_through_the_checksum() {
        for seed_byte in 0u8..32 {
            let key_pair = ml_dsa_65_keygen_from_seed(&[seed_byte; 32]);
            let address = address_from_public_key(&key_pair.public_key);
            assert!(is_canonical_address(&address), "{address}");
            validate_canonical_address(&address).expect("derived address is canonical");
            let checksummed = checksum_address(&address).expect("checksum");
            assert_eq!(checksummed.len(), ADDRESS_LEN);
            assert!(checksummed.starts_with(ADDRESS_PREFIX));
            assert_eq!(checksummed.to_ascii_lowercase(), address);
            assert_eq!(
                parse_address(&checksummed).expect("parse checksummed"),
                address
            );
            assert_eq!(parse_address(&address).expect("parse lowercase"), address);
            assert_eq!(
                checksum_address(&checksummed).expect("idempotent"),
                checksummed
            );
            if checksummed != address {
                assert_eq!(
                    validate_canonical_address(&checksummed),
                    Err(AddressError::NotCanonical)
                );
            }
        }
    }

    #[test]
    fn checksum_uses_the_domain_separated_sha3_256_nibbles() {
        let hex = "0123456789abcdef0123456789abcdef01234567";
        let mut hasher = Sha3_256::new();
        hasher.update(b"postfiat.address.checksum.v1\0");
        hasher.update(hex.as_bytes());
        let digest = hasher.finalize();
        let expected = hex
            .chars()
            .enumerate()
            .map(|(index, character)| {
                let nibble = (digest[index / 2] >> (4 * (1 - index % 2))) & 0x0f;
                if character.is_ascii_alphabetic() && nibble >= 8 {
                    character.to_ascii_uppercase()
                } else {
                    character
                }
            })
            .collect::<String>();
        assert_eq!(
            checksum_address(&format!("pf{hex}")).expect("checksum"),
            format!("pf{expected}")
        );
    }

    #[test]
    fn digit_only_addresses_are_their_own_checksum() {
        let address = format!("pf{}", "1234567890".repeat(4));
        assert_eq!(checksum_address(&address).expect("checksum"), address);
        assert_eq!(validate_canonical_address(&address), Ok(()));
    }

    #[test]
    fn rejects_malformed_input_with_distinct_reasons() {
        let cases = [
            ("", AddressError::MissingPrefix),
            ("p", AddressError::MissingPrefix),
            (
                "0x0123456789abcdef0123456789abcdef01234567",
                AddressError::MissingPrefix,
            ),
            (
                "0123456789abcdef0123456789abcdef0123456789",
                AddressError::MissingPrefix,
            ),
            (
                "PF0123456789abcdef0123456789abcdef01234567",
                AddressError::UppercasePrefix,
            ),
            (
                "Pf0123456789abcdef0123456789abcdef01234567",
                AddressError::UppercasePrefix,
            ),
            (
                "pF0123456789abcdef0123456789abcdef01234567",
                AddressError::UppercasePrefix,
            ),
            ("pf", AddressError::WrongLength),
            (
                "pf0123456789abcdef0123456789abcdef0123456",
                AddressError::WrongLength,
            ),
            (
                "pf0123456789abcdef0123456789abcdef012345678",
                AddressError::WrongLength,
            ),
            ("pfrecipient", AddressError::WrongLength),
            (
                " pf0123456789abcdef0123456789abcdef01234567",
                AddressError::MissingPrefix,
            ),
            (
                "pf0123456789abcdef0123456789abcdef01234567 ",
                AddressError::WrongLength,
            ),
            (
                "pf0123456789abcdef0123456789abcdef0123456g",
                AddressError::NonHex,
            ),
            (
                "pfrecipient000000000000000000000000000001",
                AddressError::WrongLength,
            ),
            (
                "pfrecipient0000000000000000000000000000001",
                AddressError::NonHex,
            ),
            (
                "pf0x23456789abcdef0123456789abcdef01234567",
                AddressError::NonHex,
            ),
        ];
        for (input, expected) in cases {
            assert_eq!(parse_address(input), Err(expected), "{input:?}");
            assert_eq!(
                validate_canonical_address(input),
                Err(expected),
                "{input:?}"
            );
            assert!(!is_canonical_address(input), "{input:?}");
            assert!(expected.is_malformed());
            assert_eq!(
                expected.recipient_error_code(),
                INVALID_RECIPIENT_ADDRESS_CODE
            );
        }
        // A multi-byte character must not panic at the prefix boundary.
        assert_eq!(parse_address("pé"), Err(AddressError::MissingPrefix));
        assert_eq!(
            parse_address("pf\u{00e9}123456789abcdef0123456789abcdef0123456"),
            Err(AddressError::NonHex)
        );
        assert_eq!(parse_address("pf\u{00e9}"), Err(AddressError::NonHex));
    }

    #[test]
    fn rejects_wrong_checksums_and_all_uppercase_hex() {
        let address = address_from_public_key(&ml_dsa_65_keygen_from_seed(&[7u8; 32]).public_key);
        let checksummed = checksum_address(&address).expect("checksum");
        assert_ne!(
            checksummed, address,
            "fixture needs at least one uppercase letter"
        );
        let letter_index = checksummed
            .char_indices()
            .skip(2)
            .find(|(_, character)| character.is_ascii_alphabetic())
            .map(|(index, _)| index)
            .expect("fixture has a hex letter");
        let mut flipped = checksummed.clone().into_bytes();
        flipped[letter_index] ^= 0x20;
        let flipped = String::from_utf8(flipped).expect("ascii");
        if flipped != address {
            assert_eq!(parse_address(&flipped), Err(AddressError::BadChecksum));
            assert_eq!(
                validate_canonical_address(&flipped),
                Err(AddressError::BadChecksum)
            );
        }
        let all_upper = format!("pf{}", address[2..].to_ascii_uppercase());
        if all_upper != checksummed {
            assert_eq!(parse_address(&all_upper), Err(AddressError::BadChecksum));
        }
        assert_eq!(
            AddressError::BadChecksum.recipient_error_code(),
            INVALID_RECIPIENT_CHECKSUM_CODE
        );
        assert_eq!(
            AddressError::NotCanonical.recipient_error_code(),
            NONCANONICAL_RECIPIENT_ADDRESS_CODE
        );
        assert_eq!(display_address("not-an-address"), "not-an-address");
        assert_eq!(display_address(&address), checksummed);
    }

    fn json_string_array<'a>(
        vectors: &'a serde_json::Value,
        key: &str,
    ) -> Vec<&'a serde_json::Value> {
        vectors[key]
            .as_array()
            .unwrap_or_else(|| panic!("vectors field `{key}` must be an array"))
            .iter()
            .collect()
    }

    #[test]
    fn published_vectors_match_the_implementation() {
        let vectors: serde_json::Value =
            serde_json::from_str(VECTORS_JSON).expect("address vectors parse");
        assert_eq!(vectors["schema"], "postfiat.address_vectors.v1");
        assert_eq!(vectors["checksum_domain"], ADDRESS_CHECKSUM_DOMAIN);
        assert_eq!(vectors["derivation_domain"], ADDRESS_DERIVATION_DOMAIN);

        let valid = json_string_array(&vectors, "valid");
        assert!(valid.len() >= 4);
        for case in valid {
            let canonical = case["canonical"].as_str().expect("canonical");
            let checksummed = case["checksummed"].as_str().expect("checksummed");
            if let Some(public_key_seed) = case["ml_dsa_65_seed_hex"].as_str() {
                let seed: [u8; 32] = crate::hex_to_bytes(public_key_seed)
                    .expect("seed hex")
                    .try_into()
                    .expect("32-byte seed");
                let derived =
                    address_from_public_key(&ml_dsa_65_keygen_from_seed(&seed).public_key);
                assert_eq!(derived, canonical, "derivation vector");
            }
            assert!(is_canonical_address(canonical), "{canonical}");
            assert_eq!(validate_canonical_address(canonical), Ok(()));
            assert_eq!(parse_address(canonical).as_deref(), Ok(canonical));
            assert_eq!(parse_address(checksummed).as_deref(), Ok(canonical));
            assert_eq!(checksum_address(canonical).as_deref(), Ok(checksummed));
            assert_eq!(checksum_address(checksummed).as_deref(), Ok(checksummed));
        }

        let invalid_checksum = json_string_array(&vectors, "invalid_checksum");
        assert!(!invalid_checksum.is_empty());
        for case in invalid_checksum {
            let input = case["input"].as_str().expect("input");
            assert_eq!(case["reason"], "bad_checksum");
            assert_eq!(
                parse_address(input),
                Err(AddressError::BadChecksum),
                "{input}"
            );
        }

        let malformed = json_string_array(&vectors, "malformed");
        assert!(malformed.len() >= 4);
        for case in malformed {
            let input = case["input"].as_str().expect("input");
            let error = parse_address(input).expect_err(input);
            assert_eq!(
                error.reason(),
                case["reason"].as_str().expect("reason"),
                "{input:?}"
            );
            assert!(error.is_malformed(), "{input:?}");
        }
    }
}
