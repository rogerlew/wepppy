# SUDI-02 final security review

## Findings and closure

| ID | Severity | Exploit or failure path | Concrete evidence and required remediation | Status |
| --- | --- | --- | --- | --- |
| CS-01 | Medium | A soil text field containing native list-directed controls could pass Python tokenization while native READ leaves later parameters unassigned; Python-only quoting could change labels. | `_soil_tokens` in `wepppy/wepp/single_input.py` requires native-compatible syntax before parsing. `test_native_label_differentials_rejected` covers slash, comma, comment punctuation, doubled quotes and escape syntax for each new format. Numeric fields cannot be quoted. | Closed in `f6ee5b527`. |
| CS-02 | Medium | Comments between a 9002 adjustment/header pair or before a restrictive record could pass validation but disrupt native reads. | `_canonical_text` removes standalone comments from derived soil records; `_serialize_preserved_input` places provenance before the free-text comment. Fixtures contain comments at both native no-skip boundaries; publication, preparation and native execution succeed while accepted bytes stay unchanged. | Closed in `f6ee5b527`. |
| SF-C01 | Medium | Binary64-valid strict inequalities could collapse when read as native REAL, including `n > 1`, residual/saturated water and wilting-point/field-capacity pairs. | `_native_real` adds float32 strict-order checks for hydraulic values and cumulative depth. Direct reviewer probes rejected `1.00000001`, `0.3/0.300000001` and `0.45/0.450000001`; dedicated regressions retain these boundaries. | Closed in `f6ee5b527`; also reviewed by correctness. |
| SF-C02 | Medium | Replacing original-domain checks with rounded checks could admit a texture sum that the permissive WSU reader silently repairs, or reject a valid original sum. | Original texture/parameter checks remain; float32 checks supplement only required strict inequalities. Correctness review documents reproductions and regression closure. | Closed in `f6ee5b527`. |

No unresolved high, medium or low security findings. No explicit risk acceptance
was needed. This review makes no claim that every scientifically inappropriate
parameter choice can be rejected at admission.

## Metadata

- Package: `docs/work-packages/20260926_single_input_soil_formats/`.
- Reviewer: `/root/soil_format_contract_security`, dedicated independent security reviewer.
- Final review time: 2026-09-26 02:40 UTC.
- Baseline: `64dc33a0d`; approved contract ancestor: `313951562`; runtime: `f6ee5b527`.
- `git merge-base --is-ancestor 313951562 f6ee5b527` passed. Contract commit time is 02:21 UTC; runtime commit time is 02:37 UTC.
- Scope: strict admission, upload-only WSU preservation, source normalization/version metadata, preparation flags, soil guidance and retained acceptance harness/artifacts.
- Prior contract review: [contract security review](20260926_contract_security.md).
- Correctness and QA: [independent review](20260926_correctness_review.md), read before final security sign-off; no unresolved findings.
- Validation: [summary](20260926_validation_summary.md), [live acceptance](20260926_live_acceptance.json), [archive acceptance](20260926_archive_acceptance.json).

## Security triage and assumptions

Impact is **high**: additional untrusted uploaded records reach native WEPP.
A dedicated review is required and completed here. The threat model includes an
authenticated project user supplying malformed text, native parser controls,
invalid counts/numbers or replacement content designed to corrupt source state.
Project authorization, immutable opt-in configuration, bounded multipart parsing,
NoDb/run coordination and native subprocess isolation remain the existing trust
boundaries. The amendment grants no new authority or external integration.

The separate correctness review covers absent, empty, populated, supported legacy
and hostile states. This security gate verifies containment and noninterference;
it does not replace that correctness approval.

## Surface checks

| Surface | Assessment and evidence |
| --- | --- |
| 0. Valid-state noninterference | Fresh publication, reuse, invalid replacement and malformed populated-state recovery retain existing outcomes. New formats preserve source version and values across every prepared OFE; ordinary catalog/Disturbed behavior remains behind the default WSU path. Direct parser/filesystem tests and real NoDb/RQ preparation complement controller failure doubles. |
| 1. Auth, session, authorization and CSRF | Routes, token/session validation, project scoping and CSRF transport are unchanged. Live acceptance exercised authenticated existing upload/download entry points using a short-lived run-scoped token. No new endpoint or bypass flag was introduced; preservation flags derive from opted-in controller state and soil mode. |
| 2. Secrets and credentials | No committed credential is present in the changed code or evidence. The local harness mints a short-lived scoped token in memory; retained JSON contains hashes, job identifiers and results, not tokens. No new secret mounts or credential transport. |
| 3. Input and output safety | Admission enforces exact version-dependent record widths, ASCII count syntax, bounded counts, original numeric domains, native strict-order bounds and complete consumption. No shell, eval, arbitrary deserialization or referenced-file loading is added. Filename display remains the existing escaped Pure control; only help text changes. |
| 4. Filesystem/run boundaries | Publication still uses bounded decoded bytes, hash-named immutable source generations and existing descriptor-relative/no-follow operations. The only publication deltas are derived comment normalization and actual-version metadata. Failed replacement retains the selected source. Generated copies use existing run/module destinations. |
| 5. Queue, workers and subprocesses | No enqueue site or dependency edge changes. Optional trailing preparation arguments select preservation internally and keep legacy tuples valid. Native binary choice remains `wepp_260803`; no shell command construction or native binary change. The reproduction harness retries only its named disposable run's soil job in a fresh process. |
| 6. Agent/tooling authority | Review was read-only for production files. No role, permission, MCP or deployment tooling changes. Existing user authorization covers local implementation/validation; this artifact does not authorize production operations. |
| 7. Network/integrations | No new external requests, URL-input handling or network dependency. Acceptance uses existing local application and Redis boundaries. |
| 8. CI/CD/supply chain | No new dependency, image, runner permission or workflow change. Preservation bypasses Rosetta recomputation only for admitted uploads; ordinary dependency behavior remains unchanged. |
| 9. Integrity, locking and concurrency | Existing NoDb lock, fresh hydration, immutable publication, generation retention and failure cleanup are unchanged. Source metadata adds supported version values without new keys. Tests exercise actual file publication/reuse with injected persistence failures; live NoDb/RQ evidence covers normal integration. |
| 10. Logging and recovery | Existing bounded validation/error contracts remain; no new uploaded-content logging or broad exception handler. User/operator/developer guidance describes versions, immutable sources and coordinated web/worker refresh. Stale development workers failed explicitly and were retried with fresh imports; no silent format fallback. |

## Validation evidence

Independent reviewer checks:

- `wctl run-pytest tests/wepp/test_single_input_soil_formats.py tests/nodb/test_single_input_sources.py -q`: **119 passed**, two third-party deprecation warnings, during implementation review.
- Direct `wctl run-python` probes confirmed rejection of all three float32 collapse cases listed above.
- Recomputed SHA256 and strictly reparsed all **six** retained live files: 2006, 2006.2 and 9002 at 2 and 12 OFEs. Hashes match retained JSON, versions/counts match, and evidence records native success/nonempty outputs.
- Independently read the retained ZIP member and restored 9002 source. Both match fixture bytes and SHA256 `4581c3555d1a07058deec4666ac24903cbc80ce7748af6a8dc6551f283f3201a`.
- Reviewed native parser source, preservation writer, actual worker wiring, canonical contract ancestry and complete runtime diff. `git diff --check` passed.

Owner/correctness evidence reviewed: 248 focused tests; 229 additional overlapping
preparation/template tests; all four versions executing at 1/2/12/32 OFEs;
separate modifier/native cases for single and three OFEs, including both 9002
adjustment flags; 919 frontend tests, lint, WSU stubtest and shared stub checks.
The owner subsequently reports 115 tests passing in the final format-specific
file, including complete ten-layer acceptance/eleven-layer rejection for all new
formats. Those added cases change tests only; runtime remains `f6ee5b527`.

The repository-wide pytest run remains **pending** at sign-off. Its result is a
separate package handoff gate and must be recorded in the validation summary;
this security verdict does not claim that broad validation passed.

## Artifact observability and residual limits

Accepted sources, generated module files and consumed `wepp/runs/*` remain
visible through normal authorized project tools. Live upload/download checks
returned 200 and preserved bytes for all three new versions. The 9002 archive and
restored source preserve exact bytes; archive machinery is format-opaque and
unchanged. Modifier provenance stays in generated comments; accepted sources
retain original comments and bytes.

Live acceptance used a disposable development project with synthetic geometry,
UID 1000, GID 993 and umask 0022. This is local environment evidence, not
production identity/mount parity or rollout approval. Existing workers held old
imports; web and workers require coordinated updates before production use.
Native calculations inherent to a file version remain unchanged. Preserving
9002 values is not evidence that every supplied value influences every native
model routine, and no scientific calibration is claimed.

## Verdict and sign-off

**Security gate: pass for runtime `f6ee5b527`.** Unresolved findings: high 0,
medium 0, low 0. No security finding blocks package completion after the separate
global validation gates are resolved. No deployment or production migration is
authorized by this review.

Security reviewer: `/root/soil_format_contract_security`, 2026-09-26.
Package owner: `/root`; record final package disposition in the tracker.

## Owner validation completion

After this review, the broad continuation completed with 5,366 passes, 49 skips
and 12 passing subtests. Together with the recorded initial prefix and approved
32-test fixture correction, all 667 collected files are covered. Final results
and overlap/collection-skip qualifications are in the validation summary and
coverage JSON. No further runtime behavior changed; owner closes the package
with no unresolved findings.
