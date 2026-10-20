//! Operation-scoped transactional store leases (STO-07).
//!
//! A consensus operation holds one lease for its whole duration, so every
//! store lookup inside it reuses one open redb handle and its validated
//! generation pointer binding. Dropping the lease closes the database, so the
//! sibling `rpc-serve` or `transport-validator-serve` process can open it
//! between operations.

use std::path::Path;
use std::sync::Arc;

use postfiat_storage::transactional::TransactionalStore;
use postfiat_storage::NodeStore;

/// Open the node's transactional store, if it has one, for one operation.
pub fn hold_transactional_store(
    data_dir: &Path,
) -> Result<Option<Arc<TransactionalStore>>, String> {
    NodeStore::new(data_dir)
        .transactional_store_lease()
        .map_err(|error| format!("transactional store lease failed: {error}"))
}
