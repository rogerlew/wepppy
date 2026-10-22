# Security and integration review: Roads modeled-area accounting

## Metadata and verdict

- Reviewer: Codex integration_contract_review; 2026-10-22 21:28 UTC.
- Package: `20261022_roads_accounting_repair`.
- Contract ancestor: `83f7410e852575483418590919a3bde2dbf19f4a`.
- Scope: current working-tree accounting orchestration, controller integration,
  aggregate report admission, and native water/publication boundaries.
- Security impact: **high**, because source selection and file publication change.
- Gate status: **pass for reviewed implementation and local security checks**.
- Unresolved findings: high 0, medium 0, low 0.
- Release recommendation: hold until the package's remaining correctness,
  broad-validation and artifact-observability evidence is complete. This review
  is not deployment approval or a production-equivalence claim.

This supersedes the open dispositions in the
[interim security review](20261022_security_review_interim.md).
The reviewer changed only review artifacts, not runtime code or tests.
Numerical accounting has a separate independent native review.

Reviewed primary source hashes:

| Source | SHA-256 |
| --- | --- |
| wepppy/wepp/interchange/roads_accounting.py | `1a4b311872dd9d73e4465af8f3183c19ae0758ee057a577a542667813f398ca8` |
| wepppy/nodb/mods/roads/roads.py | `0cd8cc1954ff2e5092ea935ae41f1786fb3c242ff57a45af555c7859cb62d084` |
| wepppy/wepp/reports/hillslope_watbal.py | `b7c4e03cbe3375475b0cbc6d545c1bfd3dd01643323a09fcae790115a050e88d` |
| wepppy/wepp/reports/output_scope.py | `67f0e22820827a34bfb5d71b6d9496bf5df1840d023174e071eaee59e2b78810` |
| native wepp_interchange/src/totalwatsed/roads.rs | `756c3e72764df8196b895ca8b524fc145ad9aa6ae59757f9d3b53b8e11b8ddc2` |

## Trust model and valid states

The [canonical contract](../../../schemas/roads-water-accounting-contract.md)
governs baseline immutability, model-space allocation, corrected readiness and
historical access. Existing Roads RQ single-flight locking remains in place;
auth, CSRF, queue topology, subprocess mechanisms and network access are unchanged.
Source and allocation digests detect changed/restored artifacts; they are not
signatures against a privileged actor able to forge all local artifacts.

| State | Required outcome | Evidence |
| --- | --- | --- |
| First run without optional state | Create ordinary accessible ledger and outputs | Native compose tests and umask test pass. |
| Empty contributor manifest | Preserve baseline PASS bytes and baseline water representation | Unchanged-source and continuous native-boundary tests pass. |
| Additive/replacement/expansion | Retain contracted allocation and original baseline bytes | Parametrized native composition and replacement tests pass. |
| Historical unmarked reports | Preserve existing historical selection | Shared validator performs no accounting admission when markers are absent; inspected. |
| Corrected products with missing/changed ledger | Fail explicitly, without raw fallback | Missing-ledger tests plus direct yearly-report check pass. |
| Optional sources absent/empty/partial | Retain contracted native support semantics | No new Python requirement rejects optional absence; numerical review owns full matrix. |
| Aliased destination or changed source | Reject before baseline corruption or ready publication | Direct controller and input-drift experiments pass. |

## Findings and disposition

| ID | Severity | Surface | Resolution and evidence | Status |
| --- | --- | --- | --- | --- |
| SEC-01 | High | Destination aliases | `_destination` requires the expected Roads parent; `validate_destinations` executes before both controller interchange conversion paths. Real controller calls reject an interchange-to-baseline alias before conversion and preserve baseline bytes. | Resolved |
| SEC-02 | High | Missing-ledger downgrade | `has_accounting` recognizes retained corrected products/markers. Missing ledger therefore reaches explicit load failure. Direct shared-validator and TotalWatbalReport checks confirm no fallback. | Resolved |
| SEC-03 | High | Allocation lineage | Stable allocation digests are recorded for composed PASS, routing and products and checked on load. The previous represented-area edit is rejected by the native-boundary regression test. | Resolved |
| SEC-04 | High | Source observation timing | Source hashes are captured before geometry/header reads, checked before and after composition, and checked again after native water generation before ready state. Current allocation is also rechecked during regeneration. Both precomposition and postproduction mutation experiments reject changed inputs. | Resolved |
| SEC-05 | Medium | Ledger permissions | First creation uses 0666 subject to umask; replacement preserves prior access mode. Test verifies 0660 under umask 0007 and preservation of an existing 0640 mode. Local web and RQ containers both run uid 1000/gid 993. | Resolved |
| INT-01 | Medium | Aggregate reader admission | Shared Roads validation is called by yearly water balance, return-period readers/refresh and streamflow, while average reporting validates its accounting source. Regeneration invalidates prior Roads return-period tables. Direct yearly-report missing-ledger rejection passes; other callsites inspected. | Resolved |

## Independent validation

Executed:

```text
wctl run-pytest tests/wepp/interchange/test_roads_accounting.py --maxfail=1 -q
11 passed, 2 dependency deprecation warnings in 9.08s
```

The suite invokes the installed native composition and continuous water kernels;
it covers area expansion, replacement precedence, unchanged bytes, stale sources,
ID collision, destination aliasing, missing ledger, allocation edits, umask/mode,
and equal-timestamp product changes.

Additional `wctl exec -T weppcloud python` checks used real scratch filesystem
operations and real production methods. For source-drift injection only, a
wrapper changed fixture bytes after the actual native function returned; the
native computation and publication were not mocked:

```text
_regenerate_roads_report_resources rejects alias before other controller reads or conversion
_prepare_modeled_area_accounting rejects alias before other controller reads or conversion
source changed after real native header read: rejected before ledger/composition
shared validator rejects retained corrected artifact with missing ledger
TotalWatbalReport rejects retained corrected artifact with missing ledger
input changed after real native water production: rejected; ledger remains routed, not ready
```

`wctl exec -T weppcloud id` and `wctl exec -T rq-worker id` both returned
`uid=1000 gid=993 groups=993`. This establishes local service identity parity;
it does not certify a production host's mounts, groups, umask or orchestration.
Changed reviewed code passes `git diff --check`.

## Surface checks and limits

Writes remain in the Roads tree and original inputs are hashed. Native water
outputs use existing staged publication with rollback; a post-read drift failure
does not mark the ledger ready. Allocation/input/product mismatches raise explicit
errors. Missing native APIs have no Python fallback. No new secret, external
dependency, network operation, unsafe deserialization or shell construction was
introduced. Existing authorization and queue locks are unchanged.

The native staged pair is not a simultaneous multi-file read transaction, and
digest checks are optimistic drift detection rather than source locking. A
process crash can leave derived candidates or a non-ready ledger; admission must
reject incomplete lineage and reconstruction must use original constituent files.
These are established explicit recovery boundaries, not unreported success.

The ledger and accounting Parquet live under ordinary visible Roads project
directories and are documented in the module README; no hidden storage or new
archive exclusion was identified. Final archive/restore and project-browser
observability evidence remains the package owner's closeout obligation.

## Remaining package evidence and sign-off

The retained [UM1 validation record](20261022_um1_validation.json) reports 5,844
daily rows, 16 years, matching ledger/report area and 44 unchanged original
Parquet files. This reviewer inspected that record but did not independently
repeat the whole 16-year model run. Final correctness review must bind exact
consumed PASS, fresh watershed outputs, original-source hashes and displayed
yearly/daily/average results, together with native build provenance and broad gates.

Full route-level malformed/legacy regression coverage, native publication-failure
evidence, optional numerical cases, canonical archive/restore and live authorized
artifact access remain to be assembled in the final package. Production deployment
requires the separately mandated production-equivalent workflow evidence; no
production rollout or in-place historical repair was performed by this reviewer.

Security reviewer sign-off: Codex integration_contract_review, 2026-10-22 UTC,
for the reviewed source hashes and local evidence above. Package-owner closeout
and the separate correctness gate remain required.
