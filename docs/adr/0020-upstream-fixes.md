# ADR 0020: Selected upstream fixes, 2026-10-16

Status: accepted for this update.

The primary Harness target remains 639ed015397290b3745d163aafe02ffee4aa3f84.
Fresh clones were inspected at Harness 86a402200d95fecef4529d969836f1fe13c6cb0d
and Cordis 5dac6953d2d993d345d1de9fb0a5926f6d78a7e7. Harness core source
has not changed from the primary target. This is a selective upstream adoption,
not a wholesale change to the compatibility target.

## Decisions

- Adopt Cordis 9cad5e8: retain committed consumers on each binding and release them
  only after their cleanup completes. Provider resources wait for these consumers.
  Withdrawal waits for the retired binding, including consumers already removed
  from the registry, rather than waiting for an unrelated subsequent activation.
  Keep the existing Python ancestor/executing-owner exclusions to avoid reentrant
  structural teardown cycles. This is a Python adaptation, not complete JS parity.
- Adopt c261dd2's restart-revision principle: checkpoint and setup validity include
  a monotonic restart revision. A superseded setup must drain, then run the new
  revision; its error is logged but does not fail the new activation. Terminal
  disposal retains Python's existing reentrant-await error reporting.
- Adopt 9f5e690 and 1a87f46: parallel telemetry reports `parallel`, and grouped
  errors identify the event. This supersedes ADR 0008's historical `emit` quirk.
  Exception identities/order and all-settled dispatch behavior remain unchanged.

These changes preserve public Python signatures and zero runtime dependencies.
Cleanup now waits longer where needed; consumer cleanup must not depend on the
provider resource already being closed. Telemetry readers matching `emit` for
parallel work and exact error-message assertions must be updated.

The newer JS symbol-based root access, metadata/intercept precedence and isolation
boundary rules are not adopted: Python has explicit documented root, configuration
and shared-label APIs. No `Fiber.update`, HMR, timer or scaffold API is introduced.
See the source-indexed update audit for remaining boundaries and validation.
