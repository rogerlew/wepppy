# SUDI-02 correctness and QA review

Reviewer: `/root/soil_format_contract_correctness`. Date: 2026-09-26 UTC.
Reviewed baseline: `64dc33a0d`; required contract ancestor: `313951562`;
reviewed runtime commit: `f6ee5b527`. The ancestor precedes implementation. Authority is
`docs/schemas/single-user-defined-inputs-contract.md`, Upload interface and
validation, Source state, publication and recovery, and Generated inputs and
modifiers sections; ADR-0075 records
the scoped preservation decision. Related security evidence is the separate
contract and final security review in this artifact directory.

## Findings and disposition

| ID | Severity | Finding and evidence | Disposition |
| --- | --- | --- | --- |
| SF-C01 | Medium | Binary64-only checks admitted 9002 `npar=1.000000001`, which becomes native REAL 1.0, and distinct water fractions that become equal. Direct `wctl run-python` reproduction confirmed admission. | Resolved: strict hydraulic and cumulative-depth inequalities are also checked after native single-precision conversion; source values remain unchanged. |
| SF-C02 | Medium | The first precision fix replaced original-domain checks. It admitted sand 60.00000001/clay 40, then WSU silently repaired sand to 60.0. It also rejected valid sand 30.1/clay 69.9 because rounded operands were added as Python doubles. Both reproduced directly. | Resolved: original parameter/texture checks remain; native precision adds only necessary strict-order checks. Rejected-repair and valid-texture regressions pass. |
| SF-C03 | Low | `prep_soil` still annotated a fixed ten-item tuple after adding an optional eleventh flag. | Resolved: annotation now matches the optional worker arguments using `Tuple[Any, ...]`. |

No unresolved high, medium or low findings in the changed workflow. The prior
contract findings are implemented: developed labels no longer suppress explicit
upload-mode kslast overrides; exact-horizon clipping does not duplicate depths;
CEC bounds apply to each version.

## User outcome and state review

Users can independently upload supported one-OFE soil files, see their selected
filename, and apply the profile to every hillslope/OFE. New version metadata is
canonical and immutable source bytes survive preparation. Rejected replacement
preserves the selected generation. Existing error codes, run authorization,
module/run locking and policy gates are unchanged.

| State | Required outcome | Evidence reviewed |
| --- | --- | --- |
| Absent or never-used source | Existing source-required guidance; a valid upload creates the managed directory and source. | Source publication tests use fresh directories; live authenticated uploads use the real NoDb/RQ boundary. |
| Empty chooser or present-empty source state | Reuse a valid source; otherwise preserve existing required-upload/repair guidance. | Existing source lifecycle is unchanged; malformed metadata repair and reuse tests remain. |
| Populated new format | Persist exact bytes/version, prepare the same profile at every OFE, execute native WEPP. | New publication tests, native matrix and retained live inputs. |
| Supported legacy 7778 or ordinary dataset | Preserve established behavior and independent landuse/soil choices. | Existing native/independent-source cases; preservation is opt-in, with default WSU branches unchanged. |
| Malformed replacement or unavailable populated source | Existing explicit error, no silent fallback and no replacement mutation. | Shape/numeric/text differential tests; source rejection, stale-write, containment and publication-failure tests. |
| Working, failed, completed jobs | Established job state and visible project artifacts remain available. | Live RQ job IDs, recorded fresh-process retry and final native artifacts/downloads. |

Malformed input is an expected `invalid_single_input` validation failure under
the Upload interface contract. Missing accepted bytes or malformed persisted
metadata remain exceptional `single_input_unavailable` repair conditions under
Source state/publication. No new user-facing error envelope is introduced.

## Generated artifact evidence

| Stage | Evidence | Result |
| --- | --- | --- |
| Request intent | `validate_live_soil_formats.py` sends authenticated mode-5 uploads for 2006, 2006.2 and 9002. | Each upload returns 200. |
| Reloaded source state | Real NoDb reload, `read_source`, canonical version and source hash checks. | All three sources match fixture bytes. |
| Intermediate and prepared files | Native regression matrix covers all four versions at 1/2/12/32 OFEs; live controller/service wiring covers 2/12 OFEs and single-OFE preparation. | Version, avke, ksflag, restrictive and appended hydraulic values preserved. |
| Exact consumed input | Reviewer independently reparsed six retained live files and compared every OFE to source with only the selected saturation override; SHA256s match retained evidence. | All six match. |
| Native output | Vendored `wepp_260803`; live records retain success and nonempty output sizes. Modifier regression also rejects NaN/Inf output text. | All three new versions execute at both live topologies. |
| User inspection | Existing authenticated browse/download endpoint returns each accepted source byte-for-byte. | All three return 200. |

Live evidence is retained in `20260926_live_acceptance.json`, with input files
under `/wc1/runs/si/single-input-acceptance-20260925/soil-format-acceptance/`.
This is a disposable project with synthetic geometry, development UID 1000/GID
993 and umask 0022. It is environment validation, not production deployment.
All live jobs required a fresh imported worker process after old long-lived
workers failed; web and workers must be updated together. The retained harness
does not claim that unrestarted workers support the new formats.

The reviewer independently ran the twelve precision/texture regressions: all
passed. The retained validation summary records 248 focused parser/WSU/source/artifact
tests and 229 additional preparation/template tests (overlapping), plus 919
frontend tests and successful WSU stubtest, npm lint and shared stub checks.
Final repository-wide gate results belong in the package validation summary;
this review does not substitute for completing those checks.

## QA and maintainability assessment

The change is bounded: one explicit WSU preservation option, version-specific
admission, actual-version metadata and two optional preparation flags. Raw MOFE
stacking remains unchanged. Ordinary catalog/Disturbed parameterization stays on
existing default branches; no new dependency, service, queue edge or file schema
is introduced. The separate preserving writer is justified because sharing the
ordinary writer would recompute or lose supplied values.

Regression tests inspect real serialized values, immutable bytes, consumer
counts and native output. They distinguish original-domain validation from
native precision, and exercise both rejection and valid-state noninterference.
Fixtures deliberately differ from Rosetta predictions and distinguish base
from appended water fractions. The source lifecycle tests use a small controller
double for failure injection, complemented by real NoDb/RQ/live preparation;
they do not mock the changed file writer or parser.

Residual coverage limits: no production rollout occurred; synthetic topologies
do not constitute a scientific parameter calibration. Archive/restore machinery
is unchanged and remains format-opaque under the existing source lifecycle.
`20260926_archive_acceptance.json` records a live 9002 archive/restore preserving
source metadata and hashes; the other new versions have live download coverage.
Legacy summary parsing is unchanged, including its old 2006.2 avke presentation;
the consumed soil files are independently validated through the preserving path.

## Verdict

**Correctness and QA pass for the reviewed amendment.** No unresolved findings
block the separate final security review. Complete and record remaining global
gates before package handoff. Deployment and any production project migration
are outside this approval.

## Broad-suite fixture follow-up

The initial broad run stopped after 4,492 passes and 51 skips in
`tests/nodb/test_kslast_map.py`: its `SimpleNamespace` soil fixture omitted the
`mode` property exposed by real `Soils` instances and now read by preparation.
Reviewed the bounded fixture correction: it supplies mode and covers unchecked
ordinary, checked ordinary, and checked upload combinations for both preparation
paths. Assertions verify the preservation flag at worker arguments 10/15 while
retaining existing grid-mean, provenance, and missing-coverage behavior checks.
No production fallback or change to kslast mapping was introduced. The correction
is approved. The targeted module rerun passed all 32 tests (two warnings,
31.19 seconds). The remaining 398 files resumed with normal directory-selection
semantics; `20260926_regression_coverage.json` records the exact 667-file
collection and 269 prior files. Remaining broad results belong in the validation
summary when complete.

Also reviewed the complete ten-layer acceptance/eleven-layer rejection additions
for each new format and the corrected avke property docstring. These introduce
no new runtime behavior or findings. The remaining broad suite must preserve
the normal `tests` directory selection semantics when excluding completed files;
explicit file selection can enable unrelated optional WBT integration tests.

## Owner validation completion

After this review, the broad continuation completed with 5,366 passes, 49 skips
and 12 passing subtests. Together with the recorded initial prefix and approved
32-test fixture correction, all 667 collected files are covered. Final results
and overlap/collection-skip qualifications are in the validation summary and
coverage JSON. No further runtime behavior changed; owner closes the package
with no unresolved findings.
