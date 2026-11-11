# Restrict project pickle artifacts at every interactive boundary

This ExecPlan is a living document governed by
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current, and update
this plan and `tracker.md` at every stopping point.

## Purpose / Big Picture

After this work, a Bootstrap user cannot add a `.pkl` or `.pickle` artifact, and
an existing pickle file cannot be previewed or opened in D-Tale. Authorized users
can still see the file and download its original bytes. CSV, TSV, Feather, Arrow,
and Parquet behavior remains unchanged. This removes the server-side code
execution path without introducing conversion, scanning, or replacement formats.

The proof is deliberately focused: a real temporary Git push is rejected, every
interactive pickle route returns 415 without invoking a reader/loader, a legacy
pickle download is byte-identical, and supported-format controls pass. Per the
operator's decision, do not run the full Python or frontend suites.

## Progress

- [x] (2026-11-11 03:50 UTC) Confirm F2 source paths and operator scope.
- [x] (2026-11-11 03:50 UTC) Scaffold package and review artifacts.
- [x] (2026-11-11 04:08 UTC) M0: amend canonical contracts, obtain two reviews, and commit the ancestor
      checkpoint.
- [x] (2026-11-11 04:11 UTC) M1: add focused failing tests for Bootstrap, browse, and D-Tale.
- [x] (2026-11-11 04:18 UTC) M2: remove pickle admission/readers/capability advertisements and update
      docs/stubs.
- [x] (2026-11-11 04:18 UTC) M3: run the approved focused gates and close correctness, QA/code, and
      security reviews.
- [ ] M4: perform an explicitly authorized scoped rollout and closeout.

Checkpoint ancestor: `aeab3c3e1` (base `991fc5e2c3`); archive clarification
`e2b9f6b35`. Two independent reviews approved both before production edits.

## Surprises & Discoveries

- Runtime inspection and red tests found archive-backed NoDir traversal is retired
  (`runtime_paths/fs.py:resolve`, HTTP 409 `NODIR_ARCHIVE_RETIRED`). Preserve
  retirement errors and whole-archive download; test physical files under NoDir
  roots and assert retired virtual requests never materialize or forward. No
  archive support is restored by this package.

- Observation: Bootstrap rejects blobs containing NUL bytes, but protocol-0
  pickle can be NUL-free; binary detection is not a deserialization safety gate.
  Evidence: `_validate_blob` checks `b"\x00"` and otherwise admits non-parser
  extensions.
- Observation: browse preview calls `pd.read_pickle` only for `.pkl`, while
  D-Tale accepts both `.pkl` and `.pickle`. The restriction must normalize both
  suffixes consistently rather than edit one call site.
- Observation: pickle support is also advertised in preview metadata, directory
  D-Tale links, service documentation, D-Tale `AGENTS.md`, README, and `.pyi`.
- Observation: the canonical browse contract requires raw legacy files to remain
  accessible when an optional representation cannot parse them. Restrict parsing,
  not listing or authorized download.

## Decision Log

- Decision: compare only added/modified/type-changed pickle paths against each
  ref update baseline, for its final tip and every introduced commit, with rename
  detection disabled. Keep general merge/blob/parser validation unchanged.
  Rationale: real-push regressions reproduced merge admission bypass when a
  legacy branch already exists remotely; reverse parent order and already-reachable
  tips also evade introduced-commit-only checks. This is a bounded extension of
  the same suffix admission boundary, without changing allowed-file behavior.
  Date/Author: 2026-11-11, Codex and independent security/correctness reviewers.

- Decision: deny `.pkl` and `.pickle` case-insensitively at Bootstrap and every
  interactive parser boundary.
  Rationale: the suffix selects the unsafe parser; removing that capability is
  the smallest direct fix selected by the operator.
  Date/Author: 2026-11-11, operator and Codex.
- Decision: preserve list and raw download for existing pickle artifacts.
  Rationale: compatibility and the browse filesystem contract do not require
  executing serialized Python objects.
  Date/Author: 2026-11-11, operator direction interpreted with canonical browse
  guidance.
- Decision: use focused validation only and skip the full suite.
  Rationale: the operator explicitly bounded validation to the small changed
  suffix-dispatch surfaces.
  Date/Author: 2026-11-11, operator.

## Outcomes & Retrospective

Implemented Bootstrap suffix admission, including merges and already-reachable
ref adoption, and removed both interactive pickle readers/capability advertisements.
Physical legacy files remain listable and downloadable byte-for-byte, including
raw query/header modes and files under NoDir directory roots. Retired archive
traversal remains retired; whole-archive delivery is unchanged. Focused tests,
stub checks, and independent reviews are retained in `artifacts/`. Production
rollout is not authorized or performed; M4 remains open. Full suites are waived.

## Context and Orientation

Work from `/home/workdir/wepppy`. Read the root and nearest `AGENTS.md` before
editing. Preserve unrelated working-tree changes and do not create or switch
branches unless requested.

Bootstrap is WEPPcloud's Git-backed project input workflow. Its pre-receive hook
in `wepppy/weppcloud/bootstrap/pre_receive.py` examines every introduced commit,
rejects disallowed paths, symlinks, submodules, large files, NUL-containing blobs,
and invalid WEPP text formats, then writes a push log. A protocol-0 pickle can be
plain ASCII and pass the NUL test. Deny its path suffix in `_validate_path` or at
an equally early shared point so rejection precedes blob loading/parser pooling
and `_append_push_log`.

Browse is the authenticated Starlette filesystem UI under
`wepppy/microservices/browse/`. `flow.py:_tabular_preview` calls
`pandas.read_pickle` for `.pkl`. `browse.py` advertises preview availability,
`listing.py` emits D-Tale links, and `dtale.py` forwards allowed suffixes to the
internal D-Tale loader. Reject pickle before NoDir materialization or outbound
HTTP when practical, while leaving ordinary listing and raw download paths
untouched.

The D-Tale Flask service in `wepppy/webservices/dtale/dtale.py` has `_read_pickle`
and `.pkl`/`.pickle` entries in `READERS`. Remove the function, both registry
entries, and the `.pyi` declaration. Its internal loader must return the same
explicit HTTP 415 used for unsupported extensions if reached directly. Preserve
all lazy Parquet and eager CSV/TSV/Feather/Arrow behavior.

The threat class is project-controlled file content reaching Python pickle
deserialization in a request process. Internal application-owned serialization,
Redis session migration, RQ transport, NoDb JSONPickle, and test-only fixtures do
not depend on these artifact routes and are excluded unless implementation
evidence proves they consume project files.

## Plan of Work

### Milestone 0: Contract checkpoint

Apply the approved decision in
`artifacts/20261110_contract_decision.md` to a canonical
`docs/schemas/bootstrap-git-input-contract.md` and the existing
`docs/schemas/browse-filesystem-contract.md`. Align
`wepppy/microservices/browse/AGENTS.md`, both service READMEs, and
`wepppy/webservices/dtale/AGENTS.md`. State that implementation conformance is
pending.

The durable rule is exact: `.pkl` and `.pickle`, case-insensitive, are forbidden
in Bootstrap commits and unsupported for browse preview/D-Tale; existing files
remain listable and downloadable byte-for-byte. Do not generalize this into a
magic-byte scanner or a ban on internal serialization.

Obtain two independent read-only contract reviews, disposition their findings,
and commit the decision, canonical amendments, and review disposition as a
standalone ancestor. Record the SHA in this plan and tracker before source edits.

Milestone acceptance: exact approved behavior and validation waiver are durable;
two reviews pass; the ancestor precedes implementation.

### Milestone 1: Focused failing regressions

In `tests/weppcloud/bootstrap/test_pre_receive.py`, add a real temporary Git
repository test that commits NUL-free bytes under nested allowed paths for each
lowercase and mixed-case denied suffix. Assert the push rejects with a stable
pickle-not-allowed message and does not append the rejected commit to the push
log. Preserve an allowed `.cli`/`.sol`/`.man`/`.slp` or text control already
covered by the suite. Test the earliest shared boundary rather than only a helper
that the hook might bypass.

In `tests/microservices/test_browse_routes.py` and
`tests/microservices/test_files_routes.py`, construct existing legacy pickle
files without deserializing them. Assert directory/file metadata does not
advertise preview, direct browse preview returns 415, raw authorized download is
byte-identical, and a patched `pd.read_pickle` sentinel is never called. Cover
both suffixes and mixed case.

In `tests/microservices/test_browse_dtale.py`, assert the bridge returns 415
before materialization/outbound HTTP for both suffixes, while an existing CSV or
Parquet control still reaches the loader. In
`tests/microservices/test_dtale_freshness.py` or a focused D-Tale loader test,
assert direct `/internal/load` rejects pickle and `_load_dataframe` has no pickle
dispatch. Do not execute a real pickle payload.

Milestone acceptance: new tests fail on the current code for the intended
capability paths, not because optional D-Tale dependencies are absent.

### Milestone 2: Minimal implementation and documentation

Add a case-insensitive denied-suffix constant to the Bootstrap hook and call it
from the shared path admission before blob loading. Do not alter size, NUL,
parser, ref, deletion, or logging behavior for allowed files.

Remove `.pkl`/`.pickle` from browse preview and D-Tale capability tuples and
directory links. Delete the `pd.read_pickle` branch. Add an explicit early 415
for a direct pickle preview so the file is not accidentally rendered as text or
fed to a future generic table fallback. Leave list and download handlers intact.

Remove both pickle suffixes from `DTALE_SUPPORTED_SUFFIXES`, update its error
message, and reject before materialization/HTTP. Delete `_read_pickle`, remove its
`READERS` entries, update error/documentation wording, and remove the stub
declaration. Do not replace pickle with a permissive fallback.

Update canonical contracts, browse/D-Tale READMEs and AGENTS guidance in the same
change set. Search documentation and user-visible strings so no interactive
pickle capability remains advertised. Technical references to the forbidden
format and internal trusted serialization are allowed when accurate.

Milestone acceptance: focused tests pass; source search finds no request-time
`read_pickle`; legacy download hash remains exact; controls pass.

### Milestone 3: Scoped review and validation

Run only the operator-approved checks from `Concrete Steps`. Do not run
`wctl run-pytest tests --maxfail=1`, broad npm tests, or unrelated service suites.
If implementation unexpectedly crosses another boundary, stop and record the
evidence before expanding scope or validation.

Complete independent correctness/UX, QA/code, and security reviews. Correctness
must verify existing-file list/download behavior and supported-format controls.
Security must verify every request-time reader/advertisement disposition and the
ordering of rejection before deserialization/forwarding. Close all medium/high
findings.

Milestone acceptance: every approved focused check passes, reviewers approve,
and the package reports the full-suite waiver rather than implying broad proof.

### Milestone 4: Scoped rollout

When deployment is separately authorized, use the canonical wepp1 deployment
entry point. Exercise controlled files only: one forbidden Bootstrap path, one
existing inert legacy pickle byte file, and one supported CSV/Parquet control.
Confirm rejection/415/no link, exact raw download bytes, supported preview, and
absence of reader/loader errors. Do not run or upload an executable pickle on
production.

Rollback must not restore request-time pickle loading. If the broader application
must roll back, retain an equivalent route/admission restriction until a safe
revision is active.

Milestone acceptance: exact candidate revision and service receipts are retained;
the scoped matrix passes; no broad deployment claim exceeds the evidence.

## Concrete Steps

Run from `/home/workdir/wepppy`.

Focused Bootstrap gate:

    wctl run-pytest tests/weppcloud/bootstrap/test_pre_receive.py --maxfail=1

Focused browse and files gate:

    wctl run-pytest tests/microservices/test_browse_routes.py tests/microservices/test_files_routes.py --maxfail=1

Focused D-Tale bridge/loader gate:

    wctl run-pytest tests/microservices/test_browse_dtale.py tests/microservices/test_dtale_freshness.py --maxfail=1

Stub/API checks after removing `_read_pickle`:

    wctl run-stubtest wepppy.webservices.dtale
    wctl check-test-stubs

Scoped documentation and source checks:

    wctl doc-lint --path docs/work-packages/20261110_pickle_artifact_restriction
    wctl doc-lint --path docs/schemas/browse-filesystem-contract.md
    rg -n "read_pickle|\.pkl|\.pickle|Pickle" wepppy/microservices/browse wepppy/webservices/dtale wepppy/weppcloud/bootstrap

Interpret the final search manually: denied-suffix constants, rejection tests,
and accurate restriction docs should remain; request-time readers and positive
capability advertisements must not.

Do not run the full repository Python or frontend suites. Record the explicit
operator waiver in final review and handoff artifacts.

## Validation and Acceptance

Acceptance is a small behavior matrix. A real Git hook rejects all case variants
of both suffixes and does not log the rejected push. Browse listing shows the
legacy file but no preview/D-Tale affordance. Direct preview and D-Tale requests
return 415 before reader, materializer, or outbound loader calls. Authorized raw
download returns the exact original bytes. Direct D-Tale internal load also
returns 415. CSV/TSV/Feather/Arrow/Parquet and allowed Bootstrap controls retain
their prior behavior.

No test may prove safety by executing a real malicious pickle. Use inert bytes
and call sentinels. A zero-call assertion at each dispatch boundary is stronger
and safer. Documentation-only scaffolding is not implementation evidence;
focused local passes are not deployment evidence.

## Idempotence and Recovery

Tests use temporary Git repositories and run roots and are repeatable. They must
not write to canonical runs or shared Redis. The change does not rewrite existing
artifacts, so retry and rollback have no data migration.

Reverting the restriction reopens the vulnerability. A rollback may restore
other application code only while an equivalent Bootstrap and HTTP restriction
remains. Do not add a feature flag that can silently re-enable pickle readers.

## Artifacts and Notes

Retain the contract checkpoint/reviews, focused red/green transcripts, source
search, exact test list, stub output, controlled download hash, code/QA/security
reviews, and deployment receipt. Do not retain executable pickle payloads,
production run identifiers, tokens, or private artifact content.

## Interfaces and Dependencies

Use existing interfaces only:

- `pre_receive._validate_path` or an immediately adjacent shared path guard for
  Bootstrap suffix denial.
- Browse's existing HTTP 415/PublicHTTPException conventions and download path.
- `DTALE_SUPPORTED_SUFFIXES` and D-Tale `READERS` as capability authorities.
- Existing test clients, temporary Git helper, and monkeypatch call sentinels.

No new runtime dependency, parser, converter, scanner, or service is permitted.

Revision note, 2026-11-11: created for the operator-approved F2 restriction.
The package intentionally preserves raw legacy downloads and uses scoped tests
without a full-suite gate.

Revision note, 2026-11-11: executed M0-M2 and focused validation; discovered retired
archive semantics and legacy-ref merge admission gap, retained red evidence, and
implemented a suffix-only per-ref comparison without changing other merge validators.
