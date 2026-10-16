# Contract decision checkpoint

Recorded 2026-10-16 17:57 UTC. Starting implementation revision:
`2bbc60d1ed56c67f1395967e532034a28a27769e`.

Approval: operator's explicit request, "let's fix the blank radio selection for
new projects. the default should be NoScaling". Commit authority is pending.

Classification: intended initialization/presentation change. Amend
`docs/schemas/climate-precipitation-scaling-contract.md` and ADR-0096 before code.
Shared controller and NoDb persistence/concurrency contracts remain unchanged;
the EDDE contract still supports unscaled execution. Existing lock, parser,
configuration ownership, RQ and output contracts are unaffected.

Implementation boundary: `Climate.__init__`, after explicit `precip_scale_mode`
resolution, assign NoScaling only if mode remains None. No getter migration or
template fallback. Preserve prior configuration reference initialization.

Compatibility/regression plan: existing keys and enum serialization; no bulk
NoDb rewrite. New absent configuration selects NoScaling; explicit NoScaling,
Scalar, Monthlies, AnnualMonthlies and Spatial retain their selected mode;
legacy configured factors/maps retain precedence. Malformed configuration
retains existing failures. Existing saved None is excluded from migration.
Test constructor and real persisted reload, default HTML checked radio,
configured modes, and existing unscaled EDDE artifact dates/hash. Verify
numerical no-op behavior rather than adding any parameterization heuristic.

Security impact: none; no authority, path, locking or execution-boundary change.
Two independent contract reviews and disposition precede the checkpoint commit.
No production deployment is authorized by this checkpoint.

## Input and state matrix

| Input/state | Expected outcome |
| --- | --- |
| New project, absent optional scaling settings | Persist NoScaling; default radio checked |
| Reader-admitted empty settings leaving mode unset | Persist NoScaling |
| Configured mode, scalar factor or map | Preserve resolution and precedence |
| Existing saved None or missing legacy field | Unchanged; no migration/getter edit |
| Nonempty unrecognized mode | Preserve KeyError from mode parser |
| Invalid scalar configuration | Preserve ValueError from numeric reader |
| Malformed/hostile factor or map | Preserve reader/selected-mode validation; no fallback or expanded path authority |
| Populated generated climate | Unchanged; no regeneration from constructor-default work |

Failure/no-op policy is the canonical scaling contract's Resolution and
persistence section: default only after successful configuration parsing;
preserve existing configured-input validation and saved-None execution.
Empty, none and null configuration strings are reader-admitted unset values.
For numerical no-op evidence, compare precipitation values from generated CLI
files for None and NoScaling under the same fixed seed and weather fixture;
date and self-hash checks alone prove publication, not numerical equivalence.
