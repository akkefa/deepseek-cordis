# Cordis and Harness update audit — 2026-10-16

## Inspected sources

- Python starting commit: `5c9badb71f26332caab702834fe496b0a7cf868d` (clean).
- [Harness HEAD](https://github.com/deepseek-ai/deepseek-harness/tree/86a402200d95fecef4529d969836f1fe13c6cb0d), compared with the Python target `639ed015397290b3745d163aafe02ffee4aa3f84`.
- [Cordis HEAD](https://github.com/cordiverse/cordis/tree/5dac6953d2d993d345d1de9fb0a5926f6d78a7e7), compared with the previous inspected upstream `f8ea3cd50f1a5724e8e715995bcde131c9c12b2c`.

Both remote repositories were freshly cloned. The supplied second URL is Cordis,
not OpenAI Codex. The audit covers the runtime/library relevant to this Python
port, not all Harness application changes.

## Harness findings

`vendor/cordis/src` is unchanged from the pinned target. Its manifest version
changed from 4.0.4 to 4.0.5-alpha.2. Across vendor/, 14 files changed, with 36
insertions and 15 deletions. The substantive additions are loader `moduleNamespace`
retention for HMR and timer English/Chinese display metadata; other changes include
package versions and metadata. Python's explicit loader has no HMR or module
namespace identity contract and there is no timer plugin. No direct core port is
needed from this Harness update.

## Cordis changes and Python decisions

| Upstream change | Python outcome |
|---|---|
| [9cad5e8](https://github.com/cordiverse/cordis/commit/9cad5e8): providers outlive dependent cleanup | Adapted. Reproduced old ordering `provider closed, consumer read: closed`; corrected ordering is `consumer read: open, provider closed`. Track committed dependents even after registry removal. |
| [c261dd2](https://github.com/cordiverse/cordis/commit/c261dd2): restart revisions and stale load failures | Adapted revision checks for Python restart and setup. Successful or failing superseded work cannot settle the newer restart. JS update/persistence remains unimplemented. |
| [9f5e690](https://github.com/cordiverse/cordis/commit/9f5e690): parallel telemetry mode | Adopted: `parallel` replaces historical `emit`. |
| [1a87f46](https://github.com/cordiverse/cordis/commit/1a87f46): event name in grouped errors | Adopted with Python BaseExceptionGroup; original exception members retained. |
| [5dac695](https://github.com/cordiverse/cordis/commit/5dac695): pending/failed disposal state | Python already drives terminal disposal to DISPOSED; existing lifecycle tests pass. JS internal/status hooks remain outside parity. |
| [1431598](https://github.com/cordiverse/cordis/commit/1431598): resolve config on each reload | Python already validates raw config during activation; config tests pass. JS internal/config, internal/commit and update hooks are not implemented. |
| [bc9a344](https://github.com/cordiverse/cordis/commit/bc9a344): isolation boundary lookup | Preserve Python's explicit ScopeLabel identity contract. Different labels already prevent snapshot leakage; upstream now also blocks inheritance across a newly derived isolation using the same realm. That is not silently adopted. |
| [7e9eb09](https://github.com/cordiverse/cordis/commit/7e9eb09): injected metadata before context intercepts | Deferred API change. Python currently layers injection mappings onto the mount's intercepts and exposes explicit resolve_config; precedence changes can affect existing users. |
| [9aa1415](https://github.com/cordiverse/cordis/commit/9aa1415): symbolic root property | JS-specific API change; Python retains ctx.root. |
| 147e4f2: removal after isolate moves | JS mutable isolate/HMR behavior is outside the Python loader; Python registrations capture stable name/label keys. |
| 7d0a90d: dispose internal/update hooks | Python listeners are already effect-owned; kernel update hooks are unimplemented. |
| Import suffixes, utility removal, package/version/lint changes | JS build/package concerns; no Python runtime dependency changes. |
| Loader resolve/disabled/id/init changes; HMR Windows paths and unload races; include paths/errors; timer cancellation; scaffolder failures and registry URLs | Outside the explicit Python loader/kernel APIs. Not represented as ported or tested Python features. |

## Supplemental source-indexed regression catalog

The original 72-case pinned catalog remains unchanged. These are newer-source
adaptations, separate from that inventory:

| Source | Python regression | Boundary |
|---|---|---|
| Cordis 9cad5e8, packages/core/tests/service-dispose.spec.ts | tests/test_services.py::test_provider_resources_outlive_dependent_cleanup (6 cases) | Disposal, restart, root teardown, successful/failing consumer cleanup; explicit require rather than proxy reads. |
| Same source, disposing consumer removed from registry | tests/test_services.py::test_withdrawal_waits_for_consumer_already_removed_from_registry | Committed-binding ownership, not registry membership, controls release. |
| Cordis c261dd2, packages/core/tests/update.spec.ts | tests/test_fiber.py::test_restart_during_setup_runs_new_revision (2 cases) | Restart success/failure overlap only; no claim of update API parity. |
| Cordis 9f5e690, packages/core/tests/events.spec.ts | tests/test_events.py::test_parallel_telemetry_reports_parallel_mode | Existing regression updated for the intentional diagnostic change. |
| Cordis 1a87f46, packages/core/tests/events.spec.ts | tests/test_events.py::test_parallel_failure_identifies_event_and_preserves_original_errors | Python grouped-error message, identity/order and all-settled behavior. |

## Compatibility assessment

Public function signatures, imports, package version, dependency versions and
runtime dependency count are unchanged. Existing tests pass with the historical
parallel telemetry expectation intentionally updated. This is not an unconditional
promise that all downstream code is unaffected:

1. Internal/dispatch observers must recognize `parallel` instead of `emit`.
2. Exact grouped-error string matches must account for the event name.
3. Providers now wait for dependent cleanup. Cleanup that waits for a provider to
   close first must be redesigned; hung dependent cleanup can delay shutdown.
4. Restarting during setup now runs the requested new activation, instead of
   allowing old work to satisfy it. Code relying on that race can behave differently.

Reentrant structural cleanup exclusions remain Python-specific. Undeclared reads
through get(), retained methods, transparent tracing, dynamic isolation moves and
full Harness execution are not covered by this dependency guarantee.

## Validation

- Before changes: 388 Python tests passed on Python 3.11.15.
- After changes: 398 tests passed on Python 3.11.15, 3.12.13 and 3.13.13, warnings
  treated as errors. The latter runs reused the installed pure-Python pytest tooling
  via PYTHONPATH; they were not independent uv dependency resolutions.
- Ruff lint, whole-project formatting, and strict mypy passed on the updated code.
  Removed one pre-existing trailing space in a config docstring to pass formatting.
- Cordis core: 152 tests across 14 spec files passed using Vitest 4.1.5 and
  Cosmokit 1.8.1 in an isolated runner. The initial run failed to parse the decorator
  suite; that suite was explicitly excluded from the successful run. No full
  upstream monorepo/compile-time test claim is made.
- No full Harness boot, live model/service integration or GitHub-hosted Linux CI
  was run. No commit, push, tag or publication is part of this update.

The design decision is recorded in [ADR 0020](adr/0020-upstream-fixes.md).
