# PCV-01 independent implementation security review

## Findings and disposition

| ID | Severity | Concrete evidence and exploit/failure path | Required remediation and current disposition |
| --- | --- | --- | --- |
| PCV-SEC-01 | High | Initial bounds route retained `data_uri`/client `cfg`; alternate data bypassed inspected `ws`, and popup HTML concatenation executed an injected image handler on polygon click. Actual served template/Leaflet reproduction succeeded; geometry transport was a fixture. | **Resolved:** author changed bounds to shared server-authorized metadata, rejects `data_uri`, and constructs popup/title DOM text and encoded links. Actual Flask route returns 400 for the bypass. Fixed-template browser recheck creates a valid popup, no injected image/script, and an encoded link. |
| PCV-SEC-02 | Medium | Initial `rollback()` trusted any manifest `outputs` path/hash. Actual rollback deleted an original source named in both `sources` and `outputs` in an isolated temporary run. | **Resolved:** fixed output allowlist and source-overlap rejection run before reuse/deletion. Direct reproduction now raises `Manifest contains unowned output paths` and preserves the original. Real-writer forged READONLY regression passes. |
| PCV-SEC-03 | Medium | Initial publication copied into final files. Injecting interruption after 12 bytes left a failed manifest and partial final Parquet; actual rollback refused its mismatched hash. | **Resolved:** complete staged files are published using exclusive atomic `os.link` after journaling. Actual native-writer tests pass for interruption both before and after publication, followed by safe rollback. |
| PCV-SEC-04 | Low | Initial run manifests and aggregate evidence omitted exact writer identity. | Code now records preparation/Python-writer/native-binary SHA-256 identities. New preparation evidence must actually carry those identities; earlier outputs must not be relabeled as having used the later writer. Evidence reconciliation pending. |

The bounds defect was retained legacy behavior within this package's changed admission surface. No general ownerless-run restriction is proposed as remediation.

## Metadata and verdict

- Reviewer: independent `contract_security` agent, dedicated security reviewer role; no runtime edits by reviewer.
- Review: 2026-10-12, initial inspection/reproductions 16:43–16:49 UTC; remediation recheck completed 16:52:37 UTC.
- Scope: combined/bounds routes, Portland collection catalog, generator/templates, combined-viewer JS, offline preparation, related tests and retained evidence. Unrelated `docs/projects/i-crews/st_joe/` changes excluded.
- Starting implementation: `dc6f3879e3372fa35062708b2c2f0caeb7eba18e`.
- Contract ancestor: `d75460acc4d73d0d890019f332b8c1965bf6362a`, committed 2026-10-12 16:33:30 UTC, includes two independent contract reviews before implementation.
- Candidate: working tree after the checkpoint; no implementation commit or release approval is claimed.
- Security impact: high; collection authorization, arbitrary run-list input, rendered content and maintenance writes require dedicated review.
- Gate: **pending**, not rollout approval. All high/medium code findings are closed. Provenance evidence and full acceptance/correctness/QA evidence were still in progress.

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

## Residual risk and final gate

Existing ownerless data reads intentionally remain available independently of Portland collection admission. Removing membership removes group-derived collection admission; it does not create a new downstream data embargo. This is PCV-01's approved compatibility boundary.

Final security sign-off follows correctness/QA and requires fixed-template injection rejection, current/revoked/nonmember/anonymous and independent grant evidence, real CSRF rejection, all nine collections, direct writer failure/rollback coverage, reconciled writer provenance, and normal browse/archive visibility with runtime permissions. Source inspection or mocked route tests alone do not close real identity/resolver/filesystem boundaries. No risk acceptance or production deployment approval is recorded here.

Review artifact validation: `wctl doc-lint --path <this artifact>` passed with zero errors/warnings; the `uk2us` preview had no changes.
