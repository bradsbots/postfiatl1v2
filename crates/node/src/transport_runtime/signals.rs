//! Process signal handling for `transport-validator-serve`.

use super::*;

pub(super) static TRANSPORT_VALIDATOR_SHUTDOWN_REQUESTED: std::sync::atomic::AtomicBool =
    std::sync::atomic::AtomicBool::new(false);

#[cfg(unix)]
extern "C" fn transport_validator_signal_handler(_: libc::c_int) {
    TRANSPORT_VALIDATOR_SHUTDOWN_REQUESTED.store(true, Ordering::Release);
}

#[cfg(unix)]
pub(super) fn install_transport_validator_signal_handlers() -> Result<(), String> {
    // The command owns its process. A handler only flips an atomic flag; the
    // nonblocking accept loop performs all cleanup in normal Rust code.
    unsafe {
        if libc::signal(
            libc::SIGTERM,
            transport_validator_signal_handler as *const () as libc::sighandler_t,
        ) == libc::SIG_ERR
            || libc::signal(
                libc::SIGINT,
                transport_validator_signal_handler as *const () as libc::sighandler_t,
            ) == libc::SIG_ERR
        {
            return Err(format!(
                "transport validator signal handler install failed: {}",
                std::io::Error::last_os_error()
            ));
        }
    }
    Ok(())
}

#[cfg(not(unix))]
pub(super) fn install_transport_validator_signal_handlers() -> Result<(), String> {
    Ok(())
}
