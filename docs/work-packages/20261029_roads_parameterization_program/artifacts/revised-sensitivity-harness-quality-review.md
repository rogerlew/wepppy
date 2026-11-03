# Independent sensitivity harness correctness and QA review

Reviewer: `/root/harness_quality`, 2026-11-03. Scope: additive
`tests/roads/roads_matrix.py` arguments, `tests/roads/roads_sensitivity.py`,
its deterministic tests and `artifacts/revised_sensitivity.py`. The separate
scientific review owns study selection and outcome interpretation. This review
changes no implementation, historical publication, parameter or default.

Authority: Roads adjudication and validation-suite contracts; generated-artifact
validation and artifact-observability standards; `tests/AGENTS.md`.

## Initial findings

| ID | Severity / disposition | Required disposition |
| --- | --- | --- |
| HQ-01 | Medium, resolved | Generated lane replaces prepared template inputs but retains some template metadata in its final record. Recompute or explicitly separate management/template provenance, physical dimensions and aspect bridge metadata so final readback describes consumed inputs. |
| HQ-02 | Medium, resolved | Execution-start receipt binds preliminary `prepared.json` for generated inputs. Bind the exact final prepared receipt and verify its object matches the record submitted to execution. |
| HQ-03 | Medium, resolved | The generated exact-input control needs explicit seven-output parity against retained r7 evidence; process success is insufficient. |
| HQ-04 | Medium, resolved | Failure receipt boundary currently surrounds native execution only. Retain explicit status/diagnostics for subsequent auditor/interchange/summary failures as well, without converting them into successful results. |
| HQ-05 | Medium, resolved | Verifying only listed prepared files permits an added runtime sidecar before execution. Require exact input membership at the fresh pre-execution boundary, then preserve declared inputs and retain generated output inventory. |
| HQ-06 | Low, resolved | Deterministic coverage should exercise actual failure receipt filesystem retention, nonfinite serialization and default builder compatibility in addition to helper arithmetic. |

## Source compatibility assessment

The `roads_matrix.prepare` and `execute` changes add keyword-only optional
arguments. Omitted arguments preserve the committed fixture binary, existing
control matrix, builder order and formulas. Geometry overrides are restricted to
core cases and width/fill-length/fill-slope fields; they cannot silently compound
an existing one-factor fixture. New studies explicitly select r7. Historical
`site.json`, original results, publication and provenance must remain unchanged.

An explicit reviewed source-delta entry in `analysis_staleness_current.json`
can acknowledge this test-tooling change after final review. It must not certify
historical reports as current or replace their execution hashes. Default source
compatibility is distinct from new-panel scientific acceptance.

## Disposition and validation

HQ-01 through HQ-05 are resolved in the inspected source. The generated lane
removes temporary template claims, binds its exact source and final prepared
receipt, checks record/receipt equality, and explicitly compares the exact
control's seven outputs with retained r7 output hashes. Pre-execution inventory
membership is exact. Native and subsequent audit/parser failures retain explicit
receipts and partial files; neither receipt changes a failure into a pass.
Analysis rechecks declared sources, native input/output bindings, per-case result
records and derived table hashes before producing paired comparisons. It records
actual signatures, aliases/no-ops, annual/event differences, role-boundary effects
and extensive/intensive interactions.

HQ-06 is resolved by focused deterministic tests and independent default parity.
The native failure test mocks only the process result; it exercises the real
prepared capsule, failure receipt and retained input bytes. It is failure-path
coverage, not evidence of native model success. Post-native parser failure
retention was source-reviewed; no independently injected parser failure is claimed.

Independent command `wctl run-pytest tests/roads/test_roads_contracts.py
tests/roads/test_roads_sensitivity.py -q --maxfail=1` passed 19 tests before the
last failure/event additions (log `/tmp/roads-harness-quality-tests.log`). Final focused command `wctl run-pytest tests/roads/test_roads_sensitivity.py -q
--maxfail=1` passed all 9 tests in 10.47 seconds, including native failure retention,
zero-day/event comparison and rejection of missing or duplicate calendar dates.
Log: `/tmp/roads-harness-quality-final-tests.log`.

The separate [default parity receipt](revised-harness-default-parity.json) and
[reproducer](review_harness_default_parity.py) compare the original
`e0308765c` matrix helper against the current helper, using the same current
canonical production builders. Bare-direct, rutted and three-OFE unrutted
preparation have identical native `p1.*` bytes and requested/emitted/parity
metadata; no native calls were made. The original fixture binary remains selected
when optional arguments are omitted. This directly supports default compatibility
without rerunning the historical 516-case publication.

The first parity command tried a host `/tmp` script path inside the container and
failed before preparation; `/tmp/roads-default-parity-review.log` retains it. The
piped `wctl exec -T weppcloud python -` retry succeeded and retained its disposable
capsules and receipt. No original evidence was overwritten.

## Verdict

**Accept the bounded harness implementation.** All initial evidence-integrity
findings are resolved, including duplicate-calendar multiplication prevention.
Scientific declaration and outcome acceptance remain with the separate study
review; this review cannot certify the eventual browser/RQ workflow, field
calibration or deployment. No unresolved medium/high correctness or QA finding
remains in this source review. Broad repository sanity remains a separate gate.

## Final source binding

- `tests/roads/roads_matrix.py`: `fc87fba11e1984da44364fe698cd7a87013f43e7ea3977b5781888ee96d1e73e`.
- `tests/roads/roads_sensitivity.py`: `1dc93d62f312601ee54019369603f795684a2b5362d77b23df5129b3874adeaa`.
- `tests/roads/test_roads_sensitivity.py`: `f1447e075a9e3bb4d4b3e3a24f4897f7aa4d92c77f21fe853be54f0f432cafb2`.
- `docs/work-packages/20261029_roads_parameterization_program/artifacts/revised_sensitivity.py`: `73cf22708073fc8075850fd264bdea8fd3c1917ce739ec9f1136dc90171d5fd0`.

Final prepared-declaration readback also passes for `declaration-v2.json`, SHA256
`fd298285d83d558d4e0604365e70ff058e72c5f913bc95752e804751edb44bec`:
all 47 task records equal their final prepared receipts, every declared prepared
input hash matches, and 12 preparation-only alias probes are present. Generated
source metadata explicitly identifies Denver/2711184/rutted; unsupported template
texture/RFG claims are absent (`null`). The exact source aspect is 100 degrees,
while the canonical-writer bridge is explicitly 180 degrees. This check verifies
prepared evidence, not the not-yet-reviewed native outcome.

## Historical publication staleness receipt review

Independently verified the updated `tests/roads/analysis_staleness_current.json`,
SHA256 `13d4a55ab9b3fa3a988e6adeef1cdaf71a486f73d9e3256df09b78b28e827c5f`.
The recorded delta map equals a fresh `roads_analysis.source_hashes()` comparison
with original publication provenance. Exactly four entries changed from
`e0308765c`: Roads resolver, matrix helper, new sensitivity helper and its tests.
Exactly four subsequent review entries were appended; all older reviews remain.
The new matrix/tooling entries match this review's source bindings and independent
default preparation parity. The resolver entry matches its dedicated correctness
review and retained source hash.

Historical status, notice, rationale and report/provenance bindings are unchanged.
Actual report SHA256 remains
`263174f8f56c94a9fb2773572d16f65593453df4816a6d38b7a069e97a924d7a`;
actual execution provenance SHA256 remains
`44e3f899ef18162e046e983cf0b518923e19abb3838dbcd4cb45e196a5d8e3f0`.
The report remains explicitly stale. This receipt acknowledges reviewed source
drift and does not refresh, rerun or certify the historical publication.
