# Security review — production M3 integration

## Metadata

- Package: `docs/work-packages/20260914_staley_m3_integration/`.
- Reviewer: independent `source_boundary_review` security agent, 2026-09-14.
- Reviewed production checkpoint: `b998d44e2126889e8014cc83230d51f6b89e9c82`;
  current additive `live_browser.cjs` reviewed separately before commit.
- Scope: module `io`, soil snapshot/input/policy readers, source preparation,
  transport/acquisition/replay, production soil authority, production M3,
  fixed-path predictor/result replay, publication and accepted download route;
  canonical archive/browse inclusion and the development acceptance runner.
- Related evidence: [implementation reviews](20260914_implementation_reviews.md),
  [local preparation review](20260914_generic_implementation_review.md),
  [network/result review](20260914_network_reader_review.md), and
  [runtime validation](20260914_runtime_completion_validation.md).
- Authority: scientific checkpoint `89d673c38`, generic preparation `7328a0004`,
  replay refinement `0792c7e59`, bounded acquisition authorization `2de5ca737`.

## Security triage decision

Security impact is **high**; dedicated review is required. This increment adds
bounded external acquisition, native decoding, retained source records,
run-scoped filesystem reads, worker publication and a downloadable exact mask.

The threat model includes malformed or changing local inputs, symlink swaps,
inconsistent SQLite/WAL state, corrupt retained transcripts, native callbacks
that cannot return to Python, stale project authority and partial publication.
The operator controls the explicit development command and its evidence path;
credentials stay outside project records. Remote source responses remain
untrusted despite fixed official endpoints. Existing run access rules apply,
including existing public-run visibility; this change does not privatize runs.

Valid states include absent/empty optional sources, verified primary/fallback
inputs, zero common support, terrain unavailability, supported legacy results
without a mask, interrupted attempts and previously accepted results. Scientific
unavailability is not a security error or proof of positive M3 acceptance.

## Findings

| ID | Severity | Surface | Finding and evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| SEC-01 | High | Source isolation | Original SQLite and symlink races could create sidecars, accept rollback-spill data or retain outside bytes. `soil_snapshot.py`, `soil_inputs.py`, `io.py`; independently reproduced rollback and symlink cases. | Retained no-follow copies, reject journals, bracket identities, stream limits and recheck missing dependencies. | Resolved; see implementation review. |
| SEC-02 | Medium | Preparation/integrity | Receipt parse/hash races, directory replacement and post-rename cleanup errors could invalidate provenance or misreport a committed promotion. `source_preparation.py`; real NoDb/filesystem regressions. | Same-byte parsing, descriptor-relative rename, original text limits, locked authoritative project recheck and explicit committed warnings. | Resolved; production binding reviewed at `b998d44e2`. |
| SEC-03 | High | Network/native execution | Python signal deadlines did not bound blocked native C work; independent reproduction exceeded its request budget. `source_transport.py`, `source_acquisition.py`. | Parent supervision of overall and active request deadlines; shared budgets and latched admission failures. | Resolved; controlled C-blocking request killed within the parent bound. |
| SEC-04 | Medium | Replay/provenance | Derived collection labels and retained range bytes could be altered before replay; offline replay could appear freshly retrieved. `source_replay.py`, acquisition/parser tests. | Regenerate lineage/query, verify acquisition-time body hashes, pin original native TIFF for legacy transcripts, record zero network requests and unknown original retrieval time. | Resolved; independent tamper rejections and final attribution readback. |
| SEC-05 | Medium | Browser credentials | Playwright `fill(password)` failure messages include the password; the initial runner persisted raw exceptions/page errors to browsable evidence and stdout. | Persist only fixed failure/stage signals; restrict the privileged login to the authorized HTTPS origin and form action; scan retained evidence without printing values. | Resolved; independent synthetic reproduction and corrected-runner replay below. |
| SEC-06 | Medium | Credential incident | The earlier unrestricted process diagnostic exposed a Redis credential in tool output, as recorded in the implementation review. The owner said "redis credential is known" and then "continue"; this acknowledges the notice and continued work, not confirmed rotation or explicit acceptance of the residual exposure. | Owner confirms credential response/rotation, or explicitly accepts the recorded exposure without rotation for development-package closeout; never repeat the value in evidence. | Open external response condition; reviewer recommends bounded development-only risk acceptance if explicitly acknowledged, not production-deployment approval. |

No unresolved medium/high implementation finding remains in production
checkpoint `b998d44e2`. SEC-06 is not silently accepted or considered repaired
by subsequent code changes.

## Verdict

- Production code boundary gate: **pass**, bounded to the reviewed checkpoint.
- Artifact observability gate: **pass**, with final live/archive evidence below.
- Package security gate: **fail / hold** pending SEC-06 response or explicit
  owner acceptance of the recommended bounded development-only residual risk.
- Unresolved findings: high 0, medium 1, low 0.
- Release recommendation: hold package closeout; this is not production
  deployment approval. No production deployment occurred in this review.

## Surface checks

### 0) Valid-state noninterference and user experience

Absent/empty sources remain unavailable, never an instruction to rebuild shared
Soils. Zero support and unavailable terrain remain explicit. Legacy accepted
files retain access without inventing coverage. Real filesystem/native/NoDb
tests exercise valid inputs and hostile races. This review does not replace
independent scientific, correctness, accessibility or UX acceptance.

### 1) Auth, session and authorization

The accepted download checks `rq:export`, run authorization and config before
resolving files. Existing enqueue/status scopes, session-token transport and
CSRF contracts are unchanged. The runner uses the existing development login;
origin/form validation happens before credentials are filled. Retained actual
browser/session, jobstatus and jobinfo evidence now supplements mocked route
fixtures; no archive API authorization test is claimed.

### 2) Secrets and credential handling

No new production secret dependency or secret argument is introduced. The
runner reads the established gitignored credential file, does not save browser
storage, and no longer retains raw Playwright errors. Its operator-reported
exact-value scan found zero matches in 15 retained JSON/text files; values were
not printed. SEC-06 remains an explicit earlier incident-response condition.

### 3) Input validation and output safety

Strict bounded JSON/table/key/raster admission and fixed source identities are
preserved. Predictor replay pins twelve fixed paths, including basin/domain/SBS
evidence; it never dereferences arbitrary original source paths. Malformed
populated inputs fail explicitly. API downloads reject unrecorded/tampered masks.

### 4) Filesystem and run-tree boundaries

Original soil/cache files are copied through no-follow descriptors and are not
opened as SQLite databases. Failed copies/transcripts remain module-owned and
visible. Promotion pins the source receipt and destination directory; accepted
downloads hash a pinned descriptor before streaming. No new archive exclusion,
hidden-record scheme or alternate download endpoint was introduced.

### 5) Queue, worker and subprocess surfaces

Production execution consumes prepared local inputs and never invokes source
acquisition. Native acquisition is separately authorized and parent-supervised.
Final result acceptance rechecks eligibility and source identities inside the
existing mutation boundary; no new queue/service or shell composition is added.
Actual development RQ job trees are retained and finished; accepted native
output files are uid 1000/gid 993, mode 0644. This is development parity evidence,
not a production-host deployment preflight.

### 6) Agentic tooling surfaces

Review actions were read-only diagnostics, followed by this authorized artifact
write. The synthetic browser checks used no credentials, login or network.
The development runner is restricted to the established authorized HTTPS host;
its operator must use a fresh module-owned evidence directory to preserve
previous attempts. This review grants no additional live-operation authority.

### 7) Network and external integrations

Acquisition is limited to the fixed SDA POST and original THICK object: bounded
requests/bodies, identity-pinned ranges, no redirects/retries, shared FilePath
clone budget, 30-second request/SDA and 120-second native supervision. Start,
terminal and timeout records survive failure. Offline recovery records zero
network requests; it does not reestablish a current remote object identity.

### 8) CI/CD and supply chain

No new external dependency, workflow permission, production image or deployment
topology is introduced. Existing installed native engines remain the execution
baseline. The development evidence script does not authorize production use.

### 9) Data integrity, locking and concurrency

Prepared receipt promotion uses existing NoDb ownership/lock semantics without
an unnecessary save/notify. SQLite main/WAL identities are bracketed; rollback
journals, appearance races and stale final authority are rejected. Publication
installs the exact mask before the manifest and preserves explicit legacy and
interrupted-repair behavior. Failed/stale attempts do not replace acceptance.

### 10) Logging, monitoring and incident readiness

Source requests, failures, replay ancestry, copied inputs, intermediate rasters,
worker diagnostics and publication work are retained visibly. Browser failures
now retain stage/status rather than credential-bearing exception text. Earlier
Redis exposure is recorded without its value. No secret removal or rotation is
claimed; any incident containment requires the owner's separate authority.

## Validation evidence

Independent review read back implementation/tests and reproduced the substantive
isolation, native-timeout and replay failures before closing their corrections.
This final turn added two offline browser diagnostics:

1. Real Playwright with a disabled local password input and synthetic sentinel:
   its timeout message contained the sentinel (`true`); no network or real
   credential was involved.
2. Actual corrected runner source in an isolated VM with synthetic password
   error and page error: no captured write/stdout contained the sentinel;
   terminal evidence was `failure: true`, `stage: login`, exit code 1.

Earlier focused test counts are retained in the linked validation/review
artifacts; parent-reported runs are not represented as a fresh independent
full-suite run. Final runtime test readback covers real owners/native execution,
wrong mask/external receipt, missing dependency appearance, locked authority
change, WAL drift and accepted/unrecorded/tampered download states.

### Live evidence readback

On 2026-09-14, the reviewer independently read retained browser, state, jobstatus,
jobinfo, screenshot and arithmetic-check records under the following project
validation roots. All three job trees finished without an exception; no child
jobs were reported. Browser-downloaded mask SHA-256 values independently match
the corresponding accepted result files, owned by uid 1000/gid 993 (0644).

| Project / evidence directory | Model / RQ job | Verified outcome |
| --- | --- | --- |
| `addicted-reservist`, `validation/20260914_m3/browser_m1` | M1 / `15e0ebba-789a-497f-b60a-829a28e841f6` | Browser passed; 4,311,306 / 4,311,420 valid cells; 27,669 event, 12 design and 3 inverse rows available. |
| `addicted-reservist`, `validation/20260914_m3/browser_m3_inspect2` | M3 / `8bfbab39-cd3f-495b-b8c4-f5939f6b974e` | Browser passed; 4,311,420 / 4,311,420 common-support cells; T unavailable and all probability rows unavailable. This is not positive M3 arithmetic acceptance. |
| `pfdf-m3-validation-20260914b`, `validation/browser_m3` | M3 / `47bf3c64-3d7f-459a-a4d6-aa3dafffbe5f` | Isolated synthetic basin, actual native/RQ/browser path passed; 3 / 3 valid cells; 90 event, 12 design and 3 inverse rows available. |

Paths above are beneath each project's `postfire_debris_flow/` directory in
`/wc1/runs/ad/` or `/wc1/runs/pf/`. Arithmetic outcomes come from retained
`m1_numbers.json` / `m3_numbers.json` and the reviewed independent Table-4 helper;
this reviewer did not rerun their full numerical checks. The large-basin T
unavailability remains visible in result status, not hidden by full F/S coverage.
Screenshots show the expected model, job ID, coverage/mask link and explicit
unavailability where applicable; this is not a full accessibility certification.

The reviewer compared every entry in retained `protected_before.json` and
`protected_after.json` under `addicted-reservist`'s validation root: 22,357 files
in both, matching project identities and zero changed entries. This compares
the recorded before/after hashes; it is not a new rehash of every live file.

Canonical `project_rq_archive` excludes only `archives/` and two root config
transaction files, not the M3 module. The new `archive_module_evidence.py` uses
the actual archive/restore engine on a fresh module-only copy, with isolated
ownership/lock adapters. It does not restore the original live project or test
archive API authorization. Final `archive_roundtrip.json` beneath the live
validation root records 521 files restored byte-for-byte in
`/wc1/runs/pf/pfdf-archive-validation-20260914/`, from archive
`archives/pfdf-archive-validation-20260914.20260915T012636Z.zip`. Categories include
111 source-preparation records, 13 HTTP bodies, 24 SQLite-related files, 9 valid
masks, 1 failed-acquisition record and 2 decoded native THICK files. The reviewer
independently rehashed 26 representative restored files against this inventory,
including NoDb state, WAL copies, receipts, native rasters, bodies and masks;
all matched. Existing canonical regression coverage also exercises interrupted
publication retention. No original project restore was performed.

The first `browser_browse` attempt retained a `result_validation` failure.
Fresh `browser_browse2/browser.json` completed on 2026-09-15 at 01:31:25 UTC:
ordinary directory listings exposed six selected categories and ordinary file
downloads returned HTTP 200 with matching hashes. These were failed acquisition,
native THICK, raw HTTP body, source receipt, copied SQLite WAL and predictor mask.
The reviewer independently rehashed all six local records against the retained
download hashes; all matched. This uses the established authorized project
browse/download paths, not only the accepted-result download endpoint.

Review artifact validation: scoped `wctl doc-lint` passed (one file, zero errors
or warnings); American English spelling preview applied to prose only.

## Residual risk and completion conditions

No new risk acceptance is recorded. The owner acknowledgment and continued-work
authority for SEC-06 are retained exactly above. They do not establish rotation.
The reviewer can recommend accepting that recorded exposure for development
package closeout, provided the owner explicitly accepts proceeding without
rotation; this does not authorize deployment or further credential disclosure.

The only remaining security closeout condition is SEC-06 owner incident response
or explicit acceptance of the recommended residual risk. Scientific, overall QA
and full-suite completion remain the responsible reviewers' separate gates.

The parent reports activation of recovered receipt
`source_preparation/d0a0f389b467467ab56d69b1b2b14701/receipt.json`, SHA-256
`7a84a1c96e4e684c65d6aea4ffdd8dbf3f0b114cdf4211d09d30873bcab9b134`.
This activation attribution is parent-reported; the resulting live workflows
and their retained masks, source records and archive evidence were read back
independently as described above.

## Sign-off

- Security reviewer: `source_boundary_review`, 2026-09-14; scoped code pass,
  package closeout hold as above.
- Package owner: acknowledges the Redis notice and authorizes continued work;
  explicit SEC-06 risk acceptance or incident-response confirmation is pending.

## Artifact observability gate

The [artifact observability standard](../../../standards/artifact-observability-standard.md)
applies without exception. Existing M1 attempts/publication and the production
M3 runtime inventory are the comparison surface and canonical inventory.

- [x] Visible module-owned writers and failure retention reviewed.
- [x] Canonical archive/browse code does not exclude the new visible paths.
- [x] Actual development M1/M3 RQ/browser/results and protected-hash comparison reviewed.
- [x] M3-specific canonical archive membership and restored-byte evidence complete.
- [x] Live ordinary authorized browse/download of successful and failed records complete.
- [x] Overall observability approval; no exception is granted.
