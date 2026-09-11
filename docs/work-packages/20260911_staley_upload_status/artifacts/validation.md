# Validation

Checkpoint: `7447e6243`; base: `e534fab6c`.

## Automated checks

- `wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_production.py tests/nodb/mods/test_postfire_debris_flow_dnbr.py tests/nodb/mods/test_postfire_debris_flow_encoding.py tests/nodb/mods/test_postfire_debris_flow_integration.py --maxfail=1`: 136 passed.
- After source freshness corrections: production module 34 passed; final source
  mutation selection 4 passed, including the newly added external DEM mask case.
- `wctl run-npm lint`: passed.
- `wctl run-npm test`: 110 suites, 861 tests passed after final retry-message fix.
- Canonical controller bundle rebuilt. Changed documentation lint passed.
- Full Python suite not run, per operator hold.

## Real project

`addicted-reservist`, stored Wallow IMG. Original failed job:
`0d4bc387-010e-44f7-8d3b-ef5f20691021`.
The IMG opened successfully; original failure was the internal DEM statistics
sidecar entering the strict uploaded-raster decoder.

Authenticated browser initial load and reload both restored the correct linked
job ID, two status/timeline blocks, and the `invalid_raster` traceback in Details.
Locator-based screenshot capture timed out after those successful assertions.
An earlier trial overlapped the rq-engine development reload and received a
transient 502; the later load/reload assertions used the restored service.

Live stored-candidate retry succeeded through the actual Upload dNBR button.
Receipt: HTTP 200 (the existing endpoint response); job
`54a8fe43-10c6-4f18-947b-31676c86f8e0`, attempt
`7a95eccc0a014e9db94840785e427523`. RQ ran 01:46:08–01:46:22 UTC.
The first browser script incorrectly expected 202 and stopped after enqueue;
read-only follow-up verified the job finished and all published signatures match.
No duplicate retry was submitted.

Authenticated follow-up verified accepted summary, completed job link and absence
of old failure Details, then reloaded and repeated the summary/link assertions.
Published state: HFA/Int16, 10 m cells, 100% watershed coverage, Auto scale 0.001,
prepared range -0.545 to 1.11. No M1 model run was submitted.
Playwright screenshot helpers timed out after functional assertions. A direct
CDP viewport capture then succeeded and was visually inspected: canonical
filename display, prepared-map summary, linked job ID, separate status/timeline
blocks, and collapsed clean Details. See [live control](upload_success.png).

Development web/RQ-engine processes were refreshed. No production deployment,
native binary change, or full Python suite. Implementation changes remain local.

## Independent reviews

`contract_correctness` and `contract_security` performed read-only contract and
implementation reviews. All findings closed in source/tests:

- Internal mask appearance/removal/content must affect freshness. Added DEM and
  watershed masks to snapshots, hashed original dependencies across preparation,
  retained originals in accepted signatures, and checked at publication.
- Retry must clear old Details and workflow message. Reuse reset_panel_state and
  show the current submission message while preserving the job link/map summary.
- Late old-job status/details must not overwrite a retry. Capture job identity
  in both shared callback paths, ignore superseded results/errors, and poll the
  new job when the old pending status fetch settles. Resolve/reject tests pass.

Security review: PASS, no unresolved medium/high findings. Correctness source
review: APPROVE. The live retry/reload closeout gate is satisfied by the evidence above.
