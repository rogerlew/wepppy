# PCV-01 independent implementation security review

## Findings and disposition

| ID | Severity | Concrete evidence and exploit/failure path | Required remediation and current disposition |
| --- | --- | --- | --- |
| PCV-SEC-01 | High | Initial bounds route retained `data_uri`/client `cfg`; alternate data bypassed inspected `ws`, and popup HTML concatenation executed an injected image handler on polygon click. Actual served template/Leaflet reproduction succeeded; geometry transport was a fixture. | **Resolved:** author changed bounds to shared server-authorized metadata, rejects `data_uri`, and constructs popup/title DOM text and encoded links. Actual Flask route returns 400 for the bypass. Fixed-template browser recheck creates a valid popup, no injected image/script, and an encoded link. |
| PCV-SEC-02 | Medium | Initial `rollback()` trusted any manifest `outputs` path/hash. Actual rollback deleted an original source named in both `sources` and `outputs` in an isolated temporary run. | **Resolved:** fixed output allowlist and source-overlap rejection run before reuse/deletion. Direct reproduction now raises `Manifest contains unowned output paths` and preserves the original. Real-writer forged READONLY regression passes. |
| PCV-SEC-03 | Medium | Initial publication copied into final files. Injecting interruption after 12 bytes left a failed manifest and partial final Parquet; actual rollback refused its mismatched hash. | **Resolved:** complete staged files are published using exclusive atomic `os.link` after journaling. Actual native-writer tests pass for interruption both before and after publication, followed by safe rollback. |
| PCV-SEC-04 | Low | Initial run manifests and aggregate evidence omitted exact writer identity. | **Resolved:** all 63 runs were actually regenerated with the final writer identity. Independent final readback matched 63 retained/current manifests, 919 original files and 567 outputs. Final browser downloads and canonical archive/restore match the current manifest/Parquet hashes; see final evidence review below. |

The bounds defect was retained legacy behavior within this package's changed admission surface. No general ownerless-run restriction is proposed as remediation.

## Metadata and verdict

- Original code reviewer: independent `contract_security` agent, dedicated security reviewer role; no runtime edits by reviewer.
- Final evidence reviewer: independent `final_security_evidence` agent, dedicated security reviewer role, 2026-10-12; read-only evidence/source/filesystem inspection, no network requests, probes, role changes or runtime edits.
- Review: 2026-10-12, initial inspection/reproductions 16:43–16:49 UTC; remediation recheck completed 16:52:37 UTC.
- Scope: combined/bounds routes, Portland collection catalog, generator/templates, combined-viewer JS, offline preparation, related tests and retained evidence. Unrelated `docs/projects/i-crews/st_joe/` changes excluded.
- Starting implementation: `dc6f3879e3372fa35062708b2c2f0caeb7eba18e`.
- Contract ancestor: `d75460acc4d73d0d890019f332b8c1965bf6362a`, committed 2026-10-12 16:33:30 UTC, includes two independent contract reviews before implementation.
- Final candidate: `9c8293008377b1c4279e22f0e65fd76f88697caf`, including core implementation `c1e91921090b115d6f5ddc45f3e86639c772b27f`. All 13 committed runtime files and current files match [the retained identity](evidence/runtime-source-identity.json). The final commit adds only static OpenStreetMap attribution after browser acceptance; it was separately inspected and does not change access, data or interaction logic.
- Security impact: high; collection authorization, arbitrary run-list input, rendered content and maintenance writes require dedicated review.
- Gate: **pass for forest development security readiness**. Unresolved findings: high **0**, medium **0**, low **0**. This follows the independent correctness/QA review and completed final receipts. Production deployment, production data preparation and incident closure remain outside this approval.

## Direct reproductions and rechecks

All filesystem reproductions used isolated temporary directories through `wctl exec weppcloud python`; no production or copied Portland source was changed. The native publication failure test used `tests/wepp/interchange/test_project/output/loss_pw0.txt`; only the publication call was injected, not the converter.

Initial actual rollback result:

```json
{"forged_output_deleted_original":true}
```

After remediation:

```json
{"forged_output_denied":"Manifest contains unowned output paths","original_preserved":true}
{"bounds_data_uri_status":400}
```

Initial publication failure result:

```json
{"status":"failed","partial_paths":["wepp/output/interchange/loss_pw0.hill.parquet"],"rollback_error":"Changed or missing manifest file: wepp/output/interchange/loss_pw0.hill.parquet","source_preserved":true}
```

Initial headless Chromium bounds reproduction requested a `data:application/json` alternate payload with one Portland run and an injected `cfg`. The real served template executed only an inert `window.pcvSecurityProof` flag after polygon selection. A fixture supplied geometry because the copied run's bound endpoint was unavailable; authentication/template/DOM were not mocked. No credential was accessed or sent:

```json
{"anonymous_status":200,"geometry_transport":"fixture; rendering is real template"}
{"cfg_script_executed":true}
```

Fixed-template recheck rendered the actual current Jinja template through the real Flask app, then loaded that HTML into Chromium with malicious title/config fixture values. The same geometry fixture exercised the real Leaflet popup. The route has separately been proven to reject alternate data; this stronger rendering probe also proves the DOM remains safe if hostile configuration reaches it:

```json
{"fixed_render_has_popup":true,"popup_images":0,"cfg_script_executed":false,"link_is_encoded":true}
```

The revised focused test run passed seven preparation cases, including real native writer, source preservation, unknown output refusal, symlink escape, changed-output refusal, forged manifest, and both interruption cases. It then stopped at an older bounds route test whose mocked PUBLIC run had no metadata after the new server-metadata requirement: `1 failed, 11 passed`. The author updated the fixture and added alternate-payload rejection coverage. Independent rerun of `wctl run-pytest tests/weppcloud/test_combined_viewer_preparation.py tests/weppcloud/routes/test_combined_watershed_viewer_security.py --maxfail=1 -q` passed: **26 passed**, four existing dependency deprecation warnings, 9.56 seconds. The initial failure was fixture drift, not a runtime metadata defect.

## Surface assessment

This table preserves the original code-review assessment. The final evidence review below closes its stated forest acceptance obligations.

| Surface | Assessment and evidence limit |
| --- | --- |
| Resource authority | Parsed server catalog equals the production inventory: nine collections, 63 distinct run IDs. `utils/portland_collections.py` checks PUBLIC independently, then active current-account Admin/Root, exact catalog plus PortlandGroup, or explicit owner. No prefix/config/token-group grant. |
| Membership and disclosure | Main viewer validates every run before metadata and rejects mixed lists generically. No new role mutation or ownerless downstream restriction. Same-session live revocation, independent grants and real hostile resolver evidence remain final acceptance obligations. |
| Rendering | Main template uses `tojson` and autoescaping; JS uses `textContent`, DOM nodes, encoded link components and URLSearchParams. Bounds remediation removes its unsafe popup/title sinks and alternate data loading; Leaflet overlay labels are also escaped through a text node before the control's HTML rendering. |
| CSRF and credentials | Generator includes CSRF; global Flask protection remains configured with no new exemption found. Real missing/invalid-token rejection remains a final evidence obligation. Share state has no credentials; smoke storage is in the gitignored secrets directory. |
| Files and integrity | Staging/source containment, original hashes, marker preservation and visible failure state are implemented. Fixed ownership checks and atomic publication close reproduced filesystem failures. Writer evidence reconciliation and actual browse/archive/restore visibility remain outstanding. |
| Data evidence | `forest-preparation.jsonl` initially contained 63 completed native conversions with exact source-decimal comparisons. This supports conversion/parity, not final browser authorization acceptance. |
| Errors and logging | Offline broad catch is explicitly justified as a failure-recording boundary and re-raises. Main viewer clears result layers and reports required-data failure rather than returning partial success. |
| Services and dependencies | No new queue, service, execution identity, model rerun or dependency. Existing Deck.gl CDN/OSM precedent is reused. General query/browse/session policy implementation is unchanged. |

## Final retained-evidence review

The independent final reviewer inspected the [correctness/QA disposition](2026-10-12_implementation_correctness_review.md), canonical PCV-01 contract, operator guide and rollout handoff, then verified the retained receipts against their test paths and actual forest files. The earlier independent code reproductions and their closed findings above remain the code-security evidence; this continuation did not rerun adversarial probes.

| Boundary | Final evidence and disposition |
| --- | --- |
| Member and independent grants | [Member browser receipt](evidence/browser-member.log) passes all nine collections, five variables in both units, numeric samples, generator and share/reload. [Final audit](evidence/browser-audit.log) passes the real landing links, all route aliases, mixed-list 403, malformed path input 400, rejected alternate payloads, and missing/invalid CSRF 400. It records anonymous collection 403, a real PUBLIC run 200, and a real owned run 409 after admission; the owner result proves admission, not render readiness. |
| Live account state | [Revoked session](evidence/browser-revoked.log), [restored session](evidence/browser-restored.log) and [account restoration](evidence/account-restoration.json) record the same saved session moving from member 200 to nonmember 403 to independent Admin 200 without relogin. The member roles were Dev/User/PortlandGroup, without Admin/Root. Original forest dev-agent roles were restored. PUBLIC/owner/Admin/Root helper fixtures provide additional branch coverage, not substitutes for these live checks. |
| Writer and original integrity | Catalog, retained production inventory and all preparation records identify exactly the same 63 runs. Final preparation hash `71f9a2e5f922bc7f830670a27bd55bee8057a812e7c3ed1c660df040e8383b2b` matches current source. Independent direct hashing matched all **919 sources**, **567 outputs** and **63 manifests** to [preparation evidence](evidence/forest-preparation.jsonl), with no mismatch. Every run retains READONLY and none has a PUBLIC marker. The retained validation records exact source-decimal equality and complete joins for 24,669 rows, minimum area 0.09 ha. [Source parity](evidence/source-parity.json) separately records fresh production/forest source agreement. |
| Consumed and archived bytes | Final audit downloads the current visible manifest and consumed hill Parquet through normal authorized transport and matches their filesystem hashes; all nine earlier rendered numeric samples match final regenerated query results. [Canonical archive/restore](evidence/archive-restore.json) restores 70 files byte-for-byte on an isolated real-run copy. Its manifest and Parquet hashes equal the final browser receipt and direct current filesystem readback. Queue/status/lock adapters were isolated; actual archive and restore content handling was exercised. |
| Runtime identities | [Runtime identity receipt](evidence/runtime-identity.json) records successful isolated forest preparation under production UID/GID 1002:130 and umask 0022, followed by Parquet readback under forest web UID/GID 1000:993. This validates the bounded forest identity check; it does not prove actual production mounts, image/native versions or deployment orchestration. |
| Rendering and final delta | The original fixed-template injection rejection remains valid. Final normal served-code audit passes real polygon picking, unchanged selection after dragging, pan/zoom and share state. The scoped five-second click setting and optional map-wrapper argument add no authorization, write or untrusted-input surface; [ADR-0087](../../../adrs/ADR-0087-combined-viewer-pointer-duration.md) records its finite performance limitation and correctness approval. The later attribution is a static HTTPS link. |
| Credentials and artifact hygiene | Saved share URLs contain only collection/display fields and no credential components. The reviewer verified the credential/session paths were gitignored and mode 600 while present; temporary browser session storage was subsequently removed. A final retained-log/JSON scan found no credential or cookie transport records. No credentials were read or copied by this reviewer. |

Validation receipts: [focused Python](evidence/python-focused.log) **32 passed**; [WEPPcloud subtree](evidence/python-weppcloud.log) **1,969 passed**; [repository Python](evidence/python-broad.log) **10,620 passed, 126 skipped, 5,494 warnings** in 2,734.17 seconds; [Jest](evidence/frontend-tests.log) **965 tests / 118 suites passed**. Stub checks and focused test-isolation checks pass; the randomization plugin was unavailable. Changed-file broad-exception enforcement passes. The initial broad run stopped on a test-fixture import issue; its stopped receipt is retained and is not counted as a pass.

[Repository frontend lint](evidence/frontend-lint.log) **fails** at `controllers_js/__tests__/climate.test.js:300` (`jest/no-conditional-expect`). Independent diff inspection confirms that file is unchanged from the contract checkpoint. This is a retained preexisting repository-quality limitation, not a new security finding, and this review does not claim all repository checks pass. The author separately reports direct ESLint success for the changed GL modules.

## Residual risk and final gate

**Forest security gate: pass for candidate `9c8293008`; no unresolved security findings or risk acceptance required.** The dedicated review does not replace the independent correctness/QA disposition or the production operational gate.

Existing ownerless data reads intentionally remain available independently of Portland collection admission. Removing membership removes group-derived collection admission; it does not create a downstream data embargo. This is PCV-01's approved compatibility boundary, not an assertion that these historical runs are private.

[Drilldown evidence](evidence/drilldown.json) proves one correctly scoped legacy run shell under an independent Admin grant through the existing Load Without Migrating link, with unchanged sources. Anonymous verification-page HTTP 200 is explicitly not render acceptance. Full legacy report/control readiness and PortlandGroup-only run UI acceptance remain production checks; the forest copies are partial model clones.

The [rollout handoff](rollout-handoff.md) keeps production publication/deployment, data preparation, production identity/mount/native parity, real-account/full-run acceptance and the seven-day observation window open under M5. No production change, migration, deployment authorization or incident-resolution claim follows from this forest review. Retain the manifest-owned rollback and stop on altered originals/outputs or unknown files; no PUBLIC marker or membership change is an authorized production workaround.

Review artifact validation: `wctl doc-lint --path <this artifact>` passed with zero errors/warnings; the `uk2us` spelling preview had no changes.
