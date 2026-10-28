# Cordis and Harness update audit — 2026-10-28

## Inspected sources

- Python starting commit: `daf3f35728f15be6c1d207d559c3ed293981f0b5` (clean).
- [Harness HEAD](https://github.com/deepseek-ai/deepseek-harness/tree/f3803c96974ad4a94195fb97e5c637e9c2a3afe3), compared with the previous inspected Harness `86a402200d95fecef4529d969836f1fe13c6cb0d`.
- [Cordis HEAD](https://github.com/cordiverse/cordis/tree/bd427d05490b5d04c9e74926167ab3e2901370b8) (core 4.0.0-rc.12), compared with the previous inspected Cordis `5dac6953d2d993d345d1de9fb0a5926f6d78a7e7`.

Both remote repositories were freshly cloned. The audit covers the runtime/library
relevant to this Python port, not all Harness application changes. The primary
target and the [2026-10-16 audit](upstream-audit-2026-10-16.md) remain unchanged.

## Harness findings

Across vendor/, 20 files changed (297 insertions, 62 deletions); vendored Cordis
moved from 4.0.5-alpha.2 to 4.0.6-alpha.1. The only core source change is
`vendor/cordis/src/fiber.ts` (f2f563c, e199aa1):

| Harness change | Python outcome |
|---|---|
| Public `rawConfig` getter/setter retaining raw input without validating or restarting | Deferred. Python exposes read-only `Fiber.raw_config`; there is no `update()` to consume a retained value. |
| `effectiveConfig` returning the lifecycle-published object | Already covered by `Fiber.config`, which returns the last resolved object by identity. |
| `resolveConfig(candidate)` validating through `internal/config` hooks without publishing | Deferred. Python has no `internal/config` waterfall; validation happens only during activation. |
| `restart()`/`update()` routed through the canonical `ctx.fiber` for registry wrappers | Not applicable. Python registrations return the owning Fiber directly; there are no wrapper fibers and no `update()`. |

Other vendor changes (loader project-relative bare-specifier resolution, entry and
tree config tweaks, timer and HMR updates, the rc.11 upgrade plan and package
versions) are outside the explicit Python loader and kernel APIs.

## Cordis changes and Python decisions

| Upstream change | Python outcome |
|---|---|
| [bd427d0](https://github.com/cordiverse/cordis/commit/bd427d0): close an async-generator effect when its epoch changes | Already satisfied. `Effect._setup_async` stops at the next checkpoint and calls `aclose()` in `finally`. Reproduced both new upstream sequences before adding tests: `[0, 2, 1]` for mid-way disposal, and `TypeError` with `[0, 1]` for an invalid yield. |
| [67538f6](https://github.com/cordiverse/cordis/commit/67538f6) (core part): public `ValidationError.issues`, `is`, `normalizePath`, `formatPath`; empty paths omitted from the message | Already satisfied. `ValidationError.issues` is public, paths are restricted to field names and indices, and empty paths produce no `(at ...)` suffix. `isinstance` replaces the Symbol brand. The loader source-location tracing is outside the Python loader. |
| [1ce0e49](https://github.com/cordiverse/cordis/commit/1ce0e49): log an aggregate error with no members as itself | Not applicable. Python logs through stdlib `logging` with `exc_info`; there is no Cordis logger flattening. |
| Loader entry-option validation/evaluation scopes (1a6df96, b9e00c0, 3e159c0), `cordis:` specifier removal (34c8ac5), drive-letter paths (e76a291, df4431e) | Outside the explicit Python loader. |
| Include alias/anchor, patch provenance and group id fixes (35fdc96, 6434188, 0e0cc2c); HMR core/watcher split and defaults (5b8ad37, 31bb050); fs/HMR test fixes; CI and version bumps | JS package concerns; not represented as ported Python features. |

## Supplemental source-indexed regression catalog

| Source | Python regression | Boundary |
|---|---|---|
| Cordis bd427d0, packages/core/tests/dispose.spec.ts "async yield (aborted, finally)" | tests/test_effects.py::test_async_generator_finally_runs_before_cleanup_when_disposed_midway | Events replace fake timers; the in-flight yield is still collected and cleaned up after `finally`. |
| Cordis bd427d0, packages/core/tests/dispose.spec.ts "async yield invalid effect" | tests/test_effects.py::test_async_generator_closed_on_invalid_yield | Generator `finally` runs before rollback of collected cleanups; the invalid yield surfaces as `TypeError`. |

## Compatibility assessment

There is no runtime code change. Public signatures, imports, dependency versions and
the runtime dependency count are unchanged. The Harness config-access API is not
adopted; code written against `rawConfig` assignment or `resolveConfig(candidate)`
has no Python equivalent yet.

## Validation

- Before changes: 404 Python tests passed.
- After changes: 406 tests passed with warnings treated as errors; Ruff lint and
  format checks and strict mypy passed.
- No upstream JavaScript test run, full Harness boot or GitHub-hosted CI was part
  of this audit.
