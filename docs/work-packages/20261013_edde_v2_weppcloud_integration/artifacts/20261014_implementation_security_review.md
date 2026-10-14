# EDDE integration implementation security review

## Findings and verdict

No additional concrete code vulnerability was identified in the reviewed candidate. **Preliminary disposition: hold final sign-off for acceptance evidence.** No high or medium vulnerability finding is open; the required artifact-observability and live hostile-request gates remain unverified below. This is not final release approval or authorization to deploy.

The independent correctness review identified provenance, discovery, and source-binding issues. The current candidate includes the corresponding station-report override, provenance clearing, source error retention, projection/year discovery, and grid/cell comparisons. Their complete closure remains the correctness reviewer's responsibility; security approval does not replace it.

## Metadata

- Reviewer: independent `security_reviewer`, `/root/edde_integration_contract_security`.
- Date: 2026-10-14 UTC.
- Candidate: uncommitted runtime changes over `85f6ae9f8`.
- Contract ancestor: `75b47f61f`; additive reader floor: `26c9e86ca`. Their ordering and ancestry to candidate HEAD were checked directly.
- Related artifacts: [contract security review](20261014_contract_security_review.md), [implementation correctness review](20261014_implementation_correctness_review.md), [reader-floor readback](reader-floor-reopen.json), and [page/report readback](browser-readback.json).
- Scope: EDDE selection/parser, builder and router; capability/catalog/discovery changes; climate/report templates; climate route selection handling; source client/adapter and shared publication precedents; focused tests and acceptance records available at review time.
- No runtime files were edited by this reviewer.

## Security triage and threat model

Security impact is **high**, with a dedicated final review required. A user authorized to build a project can now initiate bounded public data acquisition and existing CLIGEN/native execution. Request payloads and upstream data are untrusted; stored project capability identity controls available source choices. Existing project authorization, read-only behavior, and file publication safeguards must remain effective. Run owners are not granted arbitrary URLs, cache locations, filesystem paths, subprocess arguments, or new service credentials.

Valid legacy and absent/empty EDDE state remain supported. EDDE-specific source validation applies when building EDDE; selecting another method does not require an EDDE projection. The exact-current graph allowance does not override the worker's locale, projection, year, or spatial validation.

## Surface review

| Surface | Evidence and assessment |
| --- | --- |
| Input authority | `climate_routes.py:_validate_v2_climate_selection` checks stable catalog membership and rejects numeric attempts to authorize a different stored-graph selection. `climate_input_parser.py` restores its input snapshot on validation failure. `climate_edde_inputs.py` rejects unknown projection combinations, noninteger/bool years, out-of-envelope periods, unsupported locales/spatialization, and incompatible scaling. Worker preflight repeats these checks. |
| Auth/session/CSRF | The existing authenticated build-climate route and tracked queue remain in use. No auth/session/CSRF code or download/archive authorization was widened. Live negative request evidence is still required; mocked route-auth tests are not claimed as that proof. |
| Egress and credentials | `EddeClient` is reused unchanged: fixed anonymous public HTTPS origin, `trust_env=False`, no redirects, explicit timeout, safe source keys, ETag/If-Match and byte/hash validation. No payload-supplied endpoint or ambient credential transmission is introduced. Existing PRISM acquisition settings retain their prior authority. |
| Resource bounds | `_inventory` checks every requested year/month/variable and annual footprint before weather acquisition. Consecutive private temporary caches avoid shared-writer races and whole-period cache accumulation. Request period and existing queue timeout bound the job; a yearly budget is not a whole-job transfer cap. No automatic acquisition retries or fallback model/cell are added. |
| Failure retention | `_retain_cache` copies JSON identities and per-object attempt records in `finally` before ordinary yearly-cache cleanup. Early attempt status records requested coordinates and projection/years; failure status includes exception type/message. Raw NetCDF cache bytes are the explicitly disposable class. A killed process may leave an incomplete attempt and cache; it cannot legitimately claim completed readiness. |
| Path and file safety | Attempts use generated `mkdtemp` names under the validated climate directory. Generated hill filenames use integer IDs; source cache names are hashes. Existing climate-directory containment and `publish_files` regular-file/symlink checks are reused. No new shell interpolation or unrestricted user path is introduced. |
| Source integrity | Annual query grid source/hash and watershed cell must equal preflight identities. PRISM checks band count, georeferencing, coverage, mask, finite/order/precipitation requirements and product identifiers. Actual source metadata is retained. Final selected CLI files undergo semantic/date validation and hash attribution before publication. |
| Persistence/publication | `_inputs` snapshots source/period, station file identity, seed, locale, spatial geometry, scaling settings/map signature and acquisition configuration. `finalize` freshly hydrates under the lock; comparison precedes publication. Only named derived fields change. Real replay/publication tests demonstrate preserved previous CLI/state on scaling failure, supersession and denied replacement. |
| Reports | Jinja autoescaping and existing run-scoped browse URLs remain in use. Published provenance supplies the report's station and source identity; pending form values do not stand in for published projection/period. Switching away clears active EDDE attribution while retained attempts remain. |
| Supply chain and permissions | No added dependency, service, queue, privilege or deployment topology. Source client and native binaries follow the owned existing stack. Actual service identity, mounts and archive/restore permission parity remain environment acceptance evidence. |

## Validation performed

Executed independently:

```text
wctl run-pytest tests/nodb/test_climate_edde_build.py tests/microservices/test_rq_engine_climate_routes.py tests/climates/test_edde_client.py --maxfail=1
53 passed, 1837 warnings in 6.47s
```

Log: `/home/workdir/wepppy-scratch/edde-integration-20261014/security-review-tests.log`.

The EDDE tests exercise real CLIGEN/native processing, actual NoDb finalization/reload and real filesystem rollback; their remote source/grid acquisition is a fixture. Existing client tests reject unsafe keys, changed identities, corrupt caches, partial downloads and budget overflow, and check ambient credential isolation. Existing route tests cover hidden raw-mode/unsupported-catalog rejection before parsing, using an auth stub. These test boundaries are intentionally distinguished from live source/auth acceptance.

`git diff --check` passed. Reader-floor evidence covers US/Canada ordinary and single-input structures, with direct reopen equality and unchanged stored bytes. Available live records show authenticated climate submissions and page/report readback for Canadian Single and US Multiple projects. These records do not alone prove archive content, negative access behavior, or exact WEPP consumption.

## Required evidence before final sign-off

1. Complete the independent correctness findings and final candidate review; identify the exact reviewed revision or immutable candidate receipt.
2. Retain live valid and hostile request receipts, including unauthorized/run-access denial and invalid source/period/spatial selections, demonstrating no enqueue or durable input mutation on rejection. Cover old capability graph numeric/catalog bypass attempts.
3. Exercise actual successful and failed EDDE attempt browser/download paths under normal configured service identity. Preserve retrieved payload hashes; a page returning 200 or showing a projection is insufficient.
4. Use canonical project archive/restore for both completed and failed attempt records, checking member paths, exact payload bytes and private directory modes. Verify subsequent climate rebuild cleanup retains attempts.
5. Retain configured identity/mount/umask evidence and actual US/Canada source-to-prepared-CLI-to-fresh-WEPP receipts. Report the existing RQ timeout and actual source footprint honestly; disposition all required quality gates without turning an incomplete/failed run into a pass.

## Residual risk and sign-off

Residual risks are public source availability, authenticated costly multi-year builds within the accepted bounds, interrupted workers, and the existing multi-file publication crash window. Private caches, explicit failures, durable source/attempt evidence and existing finalization rules are appropriate controls; no new threshold or broader authorization flow is requested. No exceptional risk acceptance is proposed.

Security reviewer records preliminary source-review approval with **final security gate pending** the concrete evidence above. No unresolved code vulnerability is waived, and no production deployment is approved.
