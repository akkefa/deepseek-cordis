# Cordis and Harness update audit — 2026-10-31

## Inspected sources

- Python starting commit: `46762564f1aa81d2590d996f1f1697ecd4036a2d` (branch
  `new_version_release`, clean).
- [Harness HEAD](https://github.com/deepseek-ai/deepseek-harness/tree/ce7073d51254c26cd63b22a60835b8f948deb447),
  compared with the previous inspected Harness `f3803c96974ad4a94195fb97e5c637e9c2a3afe3`.
  Vendored `@deepseek-ai/cordis` is 4.0.6-alpha.1 with the Core 4.0.0-rc.11 merge.
- [Cordis HEAD](https://github.com/cordiverse/cordis/tree/d8b7ea1dac73f441aa2f02414d1cf90c9c31274e)
  (core 4.0.0-rc.12), compared with the previous inspected Cordis
  `bd427d05490b5d04c9e74926167ab3e2901370b8`.

Both repositories were freshly cloned. The primary target and the
[2026-10-16](upstream-audit-2026-10-16.md) and
[2026-10-28](upstream-audit-2026-10-28.md) audits remain unchanged.
`packages/extensions/tool-cordis/tests/cordis-lifecycle.spec.ts` at Harness HEAD
still matches the catalog fingerprint
`c98e874987a5d2219fc0f6ce3709d9a514739a0f738a66692f12b4d2875033df`.

## Harness findings

Since `f3803c9`, `vendor/cordis/src` changed in `context.ts`, `events.ts`,
`fiber.ts`, `logger.ts`, `reflect.ts` and `utils.ts` (Core rc.11 merge `a91a827`).

| Harness behavior | Python outcome |
|---|---|
| `internal/plugin` published while PENDING, after the parent owns the disposer and before dependency refresh; synchronous failure disposes and rethrows; parent UNLOADING skips refresh | Adopted in `Registry.mount`. |
| Disposal clears uid, publishes `internal/plugin` with per-listener containment, then unregisters | Adopted in `Fiber._emit_plugin_disposed`. |
| `internal/status(fiber, oldState)` on every state change | Adopted in `Fiber._change_state`. |
| Mutable `inject`; observers may add dependencies before activation | Adopted. `Fiber.inject` is now an ordered dict (breaking change). |
| `rawConfig` setter without an active check, `effectiveConfig`, non-publishing `resolveConfig(candidate)` through the `internal/config` waterfall | Adopted as `raw_config`, `effective_config`, `resolve_config`. |
| `assertActive()` and callback-enumerating `dispatch()` | Adopted as `assert_active()` and `Events.dispatch()`. |
| Waterfall `next()` is single-use per listener | Adopted. A second call raises `RuntimeError`. |
| Failure latch: `_setEpoch` ignores restart and dependency changes while an error is retained; only `update()` clears it | Not adopted. Python has no `update()`, so restart and dependency restoration still retry a FAILED Fiber. Documented in lifecycle.md. |
| Intercepts built from the constructor-time `inject` only | Deviation. Python builds intercepts after publication, so observer-added entries also carry intercept configuration. Documented and tested. |
| `update()`, `internal/commit`, `internal/update(config, next)` without `noSave` | Future work, together with persistence hooks. |
| Hook storage cleanup, symbol event names, logger and reflect refactors | JS representation concerns; no Python change. |

## Cordis changes and Python decisions

| Upstream change | Python outcome |
|---|---|
| [74b7905](https://github.com/cordiverse/cordis/commit/74b7905): `registry.replace()` and `internal/replace` | Not adopted. Not present in Harness's vendored Cordis. |
| [e708b90](https://github.com/cordiverse/cordis/commit/e708b90): notify only services a fiber provides | Already satisfied by `owner_changed` operating on owned bindings. |
| [92ebba5](https://github.com/cordiverse/cordis/commit/92ebba5): defer access error stacks | Not applicable; no property-access tracker in Python. |
| Loader isolate label and cross-tree entry fixes (b109a1a, bb3bf8a); HMR module graph and root reconciliation (5fc4328, d8b7ea1) | Outside the explicit Python loader. |

## Compatibility assessment

Public API changes: `Fiber.inject` changes from a tuple of names to a mutable
dict, and a repeated waterfall continuation now raises. Both are recorded as
breaking in the 0.2.0 changelog. No runtime dependency was added.

## Validation

- Before changes: 417 Python tests passed.
- After changes: 420 tests passed with warnings treated as errors; Ruff lint and
  format checks and strict mypy passed.
- No upstream JavaScript test run, full Harness boot or GitHub-hosted CI was part
  of this audit.
