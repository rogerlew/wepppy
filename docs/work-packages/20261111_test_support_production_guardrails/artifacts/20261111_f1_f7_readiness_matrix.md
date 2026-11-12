# F1-F7 pre-deployment readiness matrix

**Status**: Initial snapshot; not release-ready  
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
| F7 / SEC-07 | this package | Diagnosed/scaffolded only | Complete M0-M5 profile/auth/wctl/smoke work and reviews | prove production route absence on exact deployed candidate |

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

