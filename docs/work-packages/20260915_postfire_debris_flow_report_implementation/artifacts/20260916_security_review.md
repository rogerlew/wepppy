# Security Review — Saved post-fire likelihood report

## Metadata

- Package: [report implementation](../package.md).
- Reviewer: independent security agent `/root/report_security_review`.
- Date: 2026-09-16 UTC; branch master; contract ancestor `ac4deb681`.
- Scope: additive ResultCatalog projection, report reader, Flask blueprint and
  registration, report template/controller/CSV, control link, passive Unitizer
  bootstrap hook, paired tests, and retained validation scripts/records.
- Related correctness/UX decisions: [runtime disposition](runtime_review_disposition.md).
  Contract reviews: [checkpoint reviews](contract_reviews.md). Quality telemetry:
  [code-quality observation](code_quality.md). This security gate does not replace
  those reviews or the package's broad validation gate.

## Security Triage Decision

- Security impact: **high**; dedicated security review **required**.
- New session-authorized report/query/detail/attachment endpoints expose accepted
  run data. Existing public/private/owner rules remain authoritative; a run ID,
  enabled mod, or accepted attempt ID does not grant access.
- Threat assumptions: request parameters and browser-rendered strings are
  untrusted; filesystem corruption/replacement/symlinks are tested. Existing NoDb
  ownership and cache contracts remain trusted boundaries, not new upload APIs.
- Preserve absent/empty, populated M1/M3, legacy v1, v2 partial support, unavailable
  rows, stale/unknown currentness, and prior acceptance with a newer failed/running
  attempt. Reject malformed/corrupt/replaced inputs without inventing zero values.

## Findings

| ID | Severity | Surface / failure path | Evidence and required remediation | Status |
| --- | --- | --- | --- | --- |
| SEC-R01 | Medium | A Unitizer rerender recreated enabled event buttons during a pending page query; a detail request could supersede that query and leave controls/results inconsistent. | Persistent loadingQuery across renderEvents and guarded loadDetail; controller regression invokes a unit change while the page request is pending. | Resolved; independently confirmed |
| SEC-R02 | Low | is_file followed a symlinked redisprep.dump into optional shared currentness reading. No new symlink-creation surface or demonstrated remote exploit was found. | Skip symlink/nonregular dumps, preserving accepted values/current:null. Real-file test verifies no get_state call and unchanged target bytes. | Resolved; independently confirmed |
| LIVE-02 | Medium | Inherited shell startup invoked Project.unitChangeEvent, passively posting set_unit_preferences despite the report's no-project-write contract. | Override only the initial bootstrap call for this report; hydrate Unitizer locally. Existing reports/modal handlers remain unchanged. Final M1/M3 browser records show no project mutations and unchanged protected bytes. | Resolved; independently confirmed |

Also reviewed COR-R01: accepted size/hash, not historical inode timestamps, now
governs restored attachments. Before/after descriptor metadata still detects
in-read mutation. COR-R02 preserves partial-M3 terrain explanations independently
of common input coverage. Neither correction weakens validation or authorization.
COR-R03 retains filter-eligible off-page selection using already validated detail
or one bounded attempt-pinned detail request. It preserves generation rejection
and changes neither authorization nor the displayed-page CSV scope.

No risk acceptance is needed for these resolved findings. No previous package's
credential decision is reopened or expanded by this review.

## Verdict

- Security gate: **pass** for the reviewed implementation and retained development
  evidence; unresolved high/medium/low security findings: **0 / 0 / 0**.
- Release recommendation: eligible for the authorized local implementation commit
  after remaining package gates; no push, production deployment, model rerun or
  source acquisition is authorized by this sign-off.

## Surface Checks

### 0) Valid-State Non-Interference and User Experience

- Checked real absent-state and saved-bundle fixtures, partial M3, legacy support,
  replacement races and byte-identical restore behavior. Security controls do not
  require creating optional state or discarding valid results when currentness
  dependencies fail. Real filesystem failures supplement injected boundary errors.
- Live M1/NOAA and M3/CLI reports show the accepted model/identity, not current form
  preferences. Agent review is not a human usability study or exhaustive state proof.

### 1) Auth, Session, and Authorization

- Every implemented endpoint calls existing authorize before loading report data.
  Route tests exercise the real owner/public policy with fixture ownership data,
  including repeated private denials; authorization itself is not stubbed there.
- GET readers add no CSRF exemption or token-minting path. Explicit inherited unit
  preference actions retain existing authorization/CSRF handling. No-store and
  sanitized errors cover matched endpoint authorization and unexpected failures.

### 2) Secrets and Credential Handling

- No new secrets, mounts or credential defaults. The browser evidence helper reads
  the existing ignored development-account file, verifies login/form origin, and
  retains no credentials, cookies, CAP tokens or authentication response bodies.
  Screenshots occur after login. No secret-store/rotation change is in scope.

### 3) Input Validation and Output Safety

- Typed duration/filter/sort/page inputs, duplicate/unknown-key rejection, finite
  numeric checks, exact attempt/event syntax and fixed artifact names are enforced.
- Jinja tojson protects the seed; rendered values use textContent. Browser payloads
  omit raw provenance contexts/paths. Errors use bounded messages, not tracebacks.
- CSV text neutralizes formula prefixes after whitespace/control characters;
  quoting is additional, not the sole defense. Numeric scientific values retain
  precision and explicit fraction labels. Query URLs remain same-origin paths.

### 4) File System and Run-Tree Boundaries

- Reuse rainfall_io.open_local: component-wise no-follow opening, regular-file
  checks and existing byte limits. Attachments pin accepted size/SHA-256 and
  recheck live descriptor metadata plus accepted state before transfer.
- Failure, mutation and early-disconnect tests verify descriptor closure. No
  arbitrary file/attempt reader, archive exclusion, hidden result copy or changed
  file-permission policy is introduced.

### 5) Queue, Worker, and Subprocess Surfaces

- No enqueue site, dependency edge, worker/subprocess or cancellation path changes;
  the RQ graph gate is not applicable to this report increment.
- Currentness uses reconcile=False. Passive reads do not build models, sources,
  climate/soils or publish results. Existing read-through caches remain unchanged.

### 6) Agentic Tooling and MCP Surfaces

- No new tool/MCP permissions. The requested reusable UX role was reviewed in the
  preceding documentation checkpoint and adds no tool or sandbox authority.
- Evidence scripts are operator-invoked, development-origin bounded, and retain
  local records. They do not authorize deployment or expose a general browser API.

### 7) Network and External Integrations

- Runtime report operations read local accepted files; no source egress. Browser
  requests are bounded user-driven reads through existing HTTP timeout behavior;
  there is no automatic polling/retry loop or new network dependency.
- Existing table/decoded-byte/page caps bound individual requests. Measured full
  M1 page loading and paging are retained, not extrapolated into a load-test SLA.

### 8) CI/CD and Supply Chain

- No dependency, image, workflow token, runner permission or deployment change.
  Rebuilt controller assets use the existing repository pipeline.

### 9) Data Integrity, Locking, and Concurrency

- All three tables come from the same validated read; manifest/model/assessment
  association and accepted-record rechecks prevent mixed-attempt responses.
- UI generation and loading state reject superseded responses. Replacement
  disables exports/detail/attachment links; transient errors label prior values.
- Passive Unitizer startup is local only. Existing reports retain their default
  call, and explicit modal actions retain their existing workflow.

### 10) Logging, Monitoring, and Incident Readiness

- Unexpected server errors are logged at the deliberate boundary but sanitized
  for clients. Optional currentness failure is logged and visibly unknown.
- Browser evidence separates the exact existing recorder/events endpoint from
  prohibited project mutations; it does not claim zero session/observability
  effects. Failed/intermediate acceptance records remain inspectable.
- Rollback is removal of additive report wiring/UI; accepted artifacts and run
  preferences must not be deleted or reset.

## Validation Evidence

Independently rerun after the final security fixes:

    wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_report.py tests/weppcloud/routes/test_postfire_report_bp.py tests/rq/test_project_rq_archive.py::test_postfire_records_survive_canonical_archive_and_restore --maxfail=1 -q

Result: **44 passed**, 9 deprecation warnings, 13.41 seconds. This includes real
authorization, corrupt/symlinked/mutating descriptors, restore/download identity,
optional-state noncreation and canonical archive member/byte preservation.

    wctl run-pytest tests/weppcloud/routes/test_postfire_report_bp.py::test_rendered_report_inheritance_suppresses_only_postfire_passive_unitizer_bootstrap --maxfail=1 -q

Additional final regression: **1 passed**, 4 deprecation warnings, 11.55 seconds.
Real parent/child/include rendering verifies that only postfire suppresses the
initial call, while explicit modal hooks and saved English selection remain.

    wctl run-npm test -- postfire_report

Final result: **21 passed**, 2.763 seconds. Includes real Unitizer public API/local
English-preference initialization, formula-safe CSV, selection/replacement races,
inline failure recovery, and COR-R03 off-page selection/in-flight response cases.
The primary author separately reports full Python: 8,672 passed, 103 skipped,
3,128 warnings; final frontend: 898 passed across 112 suites, with lint passing.
Those broader runs are not represented as independently rerun by this reviewer.

Inspected retained live evidence, generated by the primary author:

- [M1 browser](browser_m1_verified/browser.json): 9,150 storms; detail, paging,
  units, CSV, fixed/ordinary downloads, injected 503 recovery and retained
  off-page selection pass. Final 04:05:29 UTC record: no page errors/project
  mutations; **18 protected files unchanged**.
- [M3 browser](browser_m3_verified/browser.json): 30-storm validation basin,
  correct disturbed9002_wbt config; detail, disabled next-page boundary, units,
  downloads and injected 503 recovery pass. Final 04:05:20 UTC record:
  **23 protected files unchanged**, no page errors/project mutations.
- [M1 saved validation](m1_saved_validation.json) and
  [M3 saved validation](m3_saved_validation.json): exact saved table and attachment
  comparison at all durations; **23 / 28 protected files unchanged**, respectively.
  Both preserve existing code-identity staleness; neither was rerun to hide it.
- [Browser helper](browser_acceptance.cjs) and
  [saved-file helper](validate_saved_runs.py) distinguish real requests from
  browser-injected failures. Earlier browser_m1 and browser_m1_final records are
  failed/intermediate evidence, not acceptance passes.

Documentation validation: this artifact's scoped doc-lint reports zero errors
and warnings; spelling preview and scoped diff check are clean.

## Artifact Observability Gate

- Canonical inventory/layout remains the existing postfire module; report-shell
  precedent is Geneva. No artifact-producing workflow or retention rule changes.
- Real canonical archive/restore test retains failed input/intermediate files,
  diagnostics, acquisition records, masks and interrupted publication work with
  exact member bytes. Reader tests separately prove restored accepted results
  remain readable/downloadable despite changed filesystem timestamps.
- Both live browser records verify ordinary browse/download in addition to the
  new fixed attachment adapter. No hidden-only/download-only project records,
  removed failures or archive exclusions require an exception.

## Residual Risk

- Normal authorized reads retain existing session, logging and Redis read-through
  behavior. Explicit user preference saves are not passive report operations.
- Live evidence covers two saved development basins, not every climate mode,
  concurrency pattern or sustained public workload. Additional cases use targeted
  fixtures; no exhaustive-coverage or production-deployment claim is made.
- No unresolved security risk is accepted by this artifact. Optional UX polish
  and broad-suite outcomes remain the primary author's separate disposition.

## Sign-off

- Security reviewer: `/root/report_security_review`, 2026-09-16 UTC — **pass**.
- Package owner: execution/local commits authorized in the checkpoint; no new
  risk acceptance or production authority is requested or implied.
