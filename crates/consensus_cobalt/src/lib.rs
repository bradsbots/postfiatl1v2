#![allow(clippy::too_many_arguments)]

include!("core_types.rs");
include!("validator_admission_policy.rs");
include!("cobalt_cover_extractor.rs");
include!("trust_graph_governance.rs");
include!("rbc_abba_mvba.rs");
include!("dabc_registry.rs");
include!("internal_validation.rs");

/// Z2 step 3 strict entry profile (`SHADOW_ONLY`, not called by consensus).
pub mod validator_entry_profile;

#[cfg(test)]
#[path = "validator_entry_profile_tests.rs"]
mod validator_entry_profile_tests;

#[cfg(test)]
mod tests {
    include!("tests.rs");
}
