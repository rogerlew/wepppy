# F1-F7 pre-deployment readiness matrix

**Status**: Implementation snapshot; M4/F6 hold; not release-ready
**Snapshot**: 2026-11-12 01:01 UTC
**Candidate revision**: not frozen

This artifact coordinates evidence. It does not replace or amend the owning
packages, and it does not equate local/forest validation with production
deployment.

| Finding | Owning package | Current evidence grade at scaffold | Required before this package closes | Production obligation after close |
| --- | --- | --- | --- | --- |
| F1 / SEC-01 | `20261110_query_engine_access_boundary` | Implemented and forest validated; rollout/observation pending | Confirm accepted reviews, focused gates, forest receipt, candidate ancestry, and no reopened medium/high finding | authorized wepp1 rollout, rollback/containment proof, observation |
| F2 / SEC-02 | `20261110_pickle_artifact_restriction` | M0-M3 locally complete with scoped validation; rollout pending | Confirm exact checkpoint/implementation, focused Git/browse/D-Tale gates, reviews, and candidate ancestry | controlled production denial/allowed-format smoke |
| F3 / SEC-03 | `20261110_browse_listing_output_safety` | M0-M3 locally complete with scoped validation; rollout pending | Confirm focused hostile/valid filename evidence, reviews, and candidate ancestry | production-equivalent inert rendering/navigation check |
| F4 / SEC-04 | `20261111_status_preflight_websocket_authorization` | Closed for forest after full gates and browser E2E; production pending | Confirm forest receipt, service/frontend candidate ancestry, token non-retention, and no reopened finding | authorized production service rollout and both stream checks |
| F5 / SEC-05 | `20261111_safe_traceback_sanitization` | Locally verified with full Python/frontend gates; production pending | Confirm full-gate receipt, sink/source canaries, reviews, candidate ancestry, and compatibility with any later F6 image | production-safe synthetic canary and sink/log observation |
| F6 / SEC-06 | `20261110_wepp1_dependency_security_gate` | M0 complete; M1-M4 still active | Reach M4: exact final image/SBOM/scans/dispositions, compatible upgrades, fail-closed gate, full tests, reviews | separately authorized image activation and post-activation evidence |
| F7 / SEC-07 | this package | M0-M3 implemented; source reviews pass; actual NFS cleanup fails M4 | Complete M0-M5 profile/auth/wctl/smoke work and reviews | prove production route absence on exact deployed candidate |

## Combined Candidate Gates

- [ ] Record one exact Git revision and ancestor proof for all accepted changes.
- [ ] Record exact common/test image IDs and F6 evidence bundle identity.
- [ ] Confirm no unresolved High/Medium correctness, QA, security, or operations
      finding across F1-F7.
- [ ] Run or verify current-candidate focused gates for each owner.
- [ ] Pass one unsegmented `wctl run-pytest tests --maxfail=1`.
- [ ] Pass `wctl run-npm lint` and `wctl run-npm test`.
- [ ] Pass current status2/preflight2 Go gates.
- [ ] Pass F6 exact-image policy/import/pre-activation gates.
- [ ] Complete F7 production route-inventory and authenticated smoke evidence.
- [ ] Review the deployment-validation plan against the exact candidate.

## Evidence-Grade Vocabulary

- **Implemented**: code exists; required validation may remain.
- **Locally validated**: package-defined local tests/reviews pass.
- **Environment validated**: package-defined forest/production-equivalent checks
  pass.
- **Pre-deployment ready**: F1-F7 combined gates and deploy plan pass; no
  production activation is claimed.
- **Deployed**: exact candidate is active on the named host with a receipt.
- **Incident resolved**: deployment, affected-scope validation, recovery, and
  required observation all pass.

At final closeout, replace every summary with exact revision/artifact links and
retain remaining deployment obligations. Never mark a finding VERIFIED solely
because this roll-up package closes.

## Ancestry snapshot (2026-11-12 UTC)

These owner receipts are ancestors of the F7 contract checkpoint, not new
combined-candidate passes. The candidate is not frozen and F6 M4 is absent.

| Finding | Exact retained revision | Ancestor of F7 checkpoint | Owner receipt |
| --- | --- | --- | --- |
| F1 | `d033a33dfb7a3fde21064d233b3127b59fd999a9` | True | [owner evidence](../../20261110_query_engine_access_boundary/tracker.md) |
| F2 | `fe0fcf9168a2ab6f6f79ae78e77a2b3283cd1546` | True | [owner evidence](../../20261110_pickle_artifact_restriction/artifacts/20261110_validation.md) |
| F3 | `73d219877292d573041b039300e0fe44f99bc3c0` | True | [owner evidence](../../20261110_browse_listing_output_safety/tracker.md) |
| F4 | `183c771ea4c6ba4afbdb0999f6521b282b529f8e` | True | [owner evidence](../../20261111_status_preflight_websocket_authorization/artifacts/20261111_validation.md) |
| F5 | `cfa1fc6e79ad1db643bd70c95bc8d44dc7083367` | True | [owner evidence](../../20261111_safe_traceback_sanitization/artifacts/20261111_full_validation.md) |

F7 evidence is [local validation](20261112_validation.md): actual production
route absence and scoped tests pass, but NFS cleanup and automatic browser
workflow/artifact acceptance remain open. F6 owner tracker still reports M1
in progress, CI retrieval prerequisite, and no evaluator/deploy hook/M4.
No F1-F6 focused receipt has been relabeled as a combined-candidate pass.
