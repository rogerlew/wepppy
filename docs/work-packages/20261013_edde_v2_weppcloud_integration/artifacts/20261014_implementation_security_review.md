# EDDE integration implementation security review

## Findings and verdict

**Final security disposition: PASS for candidate `d2ca5821b6eeb35438eaf8c28c1c794c9a10d5b3`.** No unresolved high, medium, or low security findings. Live request, artifact-observability, publication-retention and environment evidence now close the earlier security acceptance gaps. The broad repository Python suite remains a separate package gate; this review does not call it passing or authorize deployment.

The independent correctness review has separately passed the same candidate. Its provenance, discovery, source-binding and actionable-error findings are resolved. Security review verified the relevant controls and evidence after that final disposition; this sign-off does not replace correctness or broader quality gates.

## Metadata

- Reviewer: independent `security_reviewer`, `/root/edde_integration_contract_security`.
- Date: 2026-10-14 UTC.
- Candidate: committed runtime `d2ca5821b6eeb35438eaf8c28c1c794c9a10d5b3`; reviewed runtime files remain unchanged after that commit. Later acceptance receipts are named below.
- Contract ancestor: `75b47f61f`; additive capability-graph reader floor: `26c9e86ca`. Their ordering and ancestry to candidate HEAD were checked directly. This graph floor is not a complete EDDE NoDb/runtime rollback target; see the compatibility clarification below.
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
| Auth/session/CSRF | The existing authenticated build-climate route and tracked queue remain in use. No auth/session/CSRF code or download/archive authorization was widened. Live unauthenticated submission returns 401; authorized malformed requests return 400 with unchanged climate NoDb/CLI bytes. Actual browser submission and artifact downloads use the normal application paths. |
| Egress and credentials | `EddeClient` is reused unchanged: fixed anonymous public HTTPS origin, `trust_env=False`, no redirects, explicit timeout, safe source keys, ETag/If-Match and byte/hash validation. No payload-supplied endpoint or ambient credential transmission is introduced. Existing PRISM acquisition settings retain their prior authority. |
| Resource bounds | `_inventory` checks every requested year/month/variable and annual footprint before weather acquisition. Consecutive private temporary caches avoid shared-writer races and whole-period cache accumulation. Request period and existing queue timeout bound the job; a yearly budget is not a whole-job transfer cap. No automatic acquisition retries or fallback model/cell are added. |
| Failure retention | `_retain_cache` copies JSON identities and per-object attempt records in `finally` before ordinary yearly-cache cleanup. Early attempt status records requested coordinates and projection/years; failure status includes exception type/message. Raw NetCDF cache bytes are the explicitly disposable class. A killed process may leave an incomplete attempt and cache; it cannot legitimately claim completed readiness. |
| Path and file safety | Attempts use generated `mkdtemp` names under the validated climate directory. Generated hill filenames use integer IDs; source cache names are hashes. Existing climate-directory containment and `publish_files` regular-file/symlink checks are reused. No new shell interpolation or unrestricted user path is introduced. |
| Source integrity | Annual query grid source/hash and watershed cell must equal preflight identities. PRISM checks band count, georeferencing, coverage, mask, finite/order/precipitation requirements and product identifiers. Actual source metadata is retained. Final selected CLI files undergo semantic/date validation and hash attribution before publication. |
| Persistence/publication | `_inputs` snapshots source/period, station file identity, seed, locale, spatial geometry, scaling settings/map signature and acquisition configuration. `finalize` freshly hydrates under the lock; comparison precedes publication. Only named derived fields change. Real replay/publication tests demonstrate preserved previous CLI/state on scaling failure, supersession and denied replacement. |
| Reports | Jinja autoescaping and existing run-scoped browse URLs remain in use. Published provenance supplies the report's station and source identity; pending form values do not stand in for published projection/period. Switching away clears active EDDE attribution while retained attempts remain. |
| Supply chain and permissions | No added dependency, service, queue, privilege or deployment topology. Source client and native binaries follow the owned existing stack. Recorded worker/RQ/browse services share UID 1000, GID 993 and group 993; worker umask is 0022. Canonical NFS run/source mounts and byte/mode-preserving archive/restore are recorded. |

## Validation performed

Executed independently against the committed runtime candidate:

```text
wctl run-pytest tests/nodb/test_climate_edde_build.py tests/microservices/test_rq_engine_climate_routes.py tests/climates/test_edde_client.py --maxfail=1
59 passed, 1837 warnings in 6.66s
```

Log: `/home/workdir/wepppy-scratch/edde-integration-20261014/security-review-final-tests.log`. The earlier preliminary candidate passed 53 tests; six added cases cover the changed-grid/report and actionable-error regressions.

The EDDE tests exercise real CLIGEN/native processing, actual NoDb finalization/reload and real filesystem rollback; their remote source/grid acquisition is a fixture. Existing client tests reject unsafe keys, changed identities, corrupt caches, partial downloads and budget overflow, and check ambient credential isolation. Existing route tests cover hidden raw-mode/unsupported-catalog rejection before parsing, using an auth stub. These test boundaries are intentionally distinguished from live source/auth acceptance.

`git diff --check` passed during source review. Reader-floor evidence covers US/Canada ordinary and single-input structures, with direct reopen equality and unchanged stored bytes. Final live records below extend successful request/page rendering into rejection, exact artifact, archive/restore and consumer evidence.

## Final live evidence and observability gate

| Evidence | Verified result |
| --- | --- |
| [Hostile requests](hostile-http-no-mutation.json) | Five authenticated invalid projection/period/spatial/scaling submissions return 400 and retain the exact prior climate NoDb/CLI bytes. Unauthenticated submission returns 401. Error fields/messages describe the EDDE correction required. |
| [Legacy capability rejection](legacy-catalog-rejection.json) | Both numeric-only mode 17 and explicit EDDE catalog requests fail under the old saved capabilities, without durable climate-state change. The compatibility reader does not grant new source authority. |
| [Browser submission](negative-browser-submission.json), [failed job](negative-job.json) | Actual browser-controlled Canadian Multiple request reaches the worker and fails explicitly on missing PRISM normals. Prior Single publication is preserved; no spatial fallback occurs. |
| [Download hashes](browser-download-hashes.json) | Twelve actual HTTP 200 downloads match local byte counts and SHA-256: published CLI/provenance, completed/failed attempt status and canonical project archives. |
| [Before restore](archive-before-restore.json), [after restore](archive-after-restore.json) and `archive_readback.py` | Records are equal: 104 climate members for the completed Canadian project and 117 for its PRISM-rejected clone. Every file hash matches the corresponding canonical archive payload; all directory modes match, including 0700 attempt directories. Both restore jobs finished, and the failed reason survives restore. |
| [Rebuild retention](retention-readback.json), [job](retention-rebuild-job.json) | A subsequent successful climate build preserves all 100 prior completed/failed attempt files byte-for-byte. The retained inventory now contains two completed attempts and one failed attempt. |
| [Runtime environment](runtime-environment.json) | Forest development Compose identities/mounts, worker umask, native binary hash and actual RQ climate timeout 216000 seconds are recorded. Private attempt permissions remain service-readable and survive restore. No production parity or deployment is inferred beyond these stated identities/configuration. |
| [Source acquisition](source-acquisition-summary.json) | Both accepted projects record one requested year, planned weather footprint 1,164,990,696 bytes, source-grid identity/hash and actual native cell. These are live source records; the four-billion-byte budget is per yearly query, not per multiyear job. |
| [Prepared inputs and consumers](artifact-readback.json) | All 53 Canadian Single and 83 US Multiple prepared climates have corresponding fresh parsed WEPP water-balance output: 366 finite daily rows for 2060 and precipitation matching the exact prepared CLI. Both final WEPP job trees have all nodes finished; earlier failed probes remain retained. |

Comparable artifact convention is the existing climate observed/PRISM staging and publication path. The new EDDE attempt/source/generated inventory is visible under ordinary `climate/edde-build-*` paths. Existing canonical browser/archive paths remain authoritative; no hidden-only project records, custom download authorization, or new archive exclusions were introduced.

No concrete security evidence gap remains for the reviewed integration boundaries. The broader Python suite was still running at final security review. Package closeout must record its actual disposition separately; this security PASS is not a substitute for that gate. Live evidence samples MPI SSP3-7.0 in 2060 at the stated projects, not every supported model/year combination.

## Residual risk and sign-off

Residual risks are public source availability, authenticated costly multi-year builds within the accepted bounds, interrupted workers, and the existing multi-file publication crash window. Private caches, explicit failures, durable source/attempt evidence and existing finalization rules are appropriate controls; no new threshold or broader authorization flow is requested. No exceptional risk acceptance is proposed.

Security reviewer signs **PASS** for candidate `d2ca5821b` after final correctness review and the concrete security evidence above. No unresolved finding is waived and no exceptional risk acceptance is required. Package owner retains responsibility for remaining broad quality gates and final handoff; no production deployment is approved.

## Calendar publication amendment review

**PASS for the bounded follow-up delta reviewed on 2026-10-14 UTC**, based on `93524e393` with the calendar/publication changes still uncommitted at review time. No new security finding. This delta closes a data-integrity gap: a valid replacement request could previously change the WEPP-consumed simulation length/start before successful publication, even when the previous CLI survived a failed rebuild.

The EDDE parser now preserves published `_input_years` despite requested future bounds or a submitted `input_years` value; the existing successful staged finalizer remains its assignment boundary. `calendar_start_year` reads the active CLI for EDDE instead of pending request bounds. The absent-safe mode check preserves the prior calendar fallback for minimal or absent mode state. Other modes retain their previous parsing/calendar behavior. No auth, path construction, egress, cache, subprocess, archive or publication-lock boundary changed.

Reviewed runtime identities:

- `wepppy/nodb/core/climate.py`: SHA-256 `1d07d71f636d4e930a8ddf209fd2d659018bf216e630ecff98fe3e42db6e49e0`.
- `wepppy/nodb/core/climate_input_parser.py`: SHA-256 `8bd96babcef559837b4aa93f561967cfdba94480ae6b29f7de7945e1817513e1`.

The new regression generates a real 2060 climate, submits 2061–2062 with `input_years=99`, injects acquisition failure, and verifies durable reload retains one published year, calendar start 2060, identical provenance and the CLI hash. The retained validation log `/tmp/edde-period-final-tests.log` records **62 passed** across the existing input-parser, user-defined CLI calendar, and EDDE builder modules; `/tmp/edde-period-regression.log` records **46 passed** for EDDE and RQ route tests. The initial direct-mode-access compatibility failure was corrected with the absent-safe check before this disposition; it is not relabeled as a passing run.

[Live submission](period-rejection-submission.json), [failed worker](period-rejection-job.json), and [fresh readback](failed-period-readback.json) independently prove the same publication separation through the existing endpoint/worker: requested years remain 2061–2062, PRISM rejects missing normals, and the prior climate still supplies one year starting in 2060 with unchanged CLI bytes and published 2060 provenance. This is a failed replacement with retained valid publication, not a successful new climate build. The prior security PASS therefore extends to this exact bounded delta; the independent correctness amendment and actual broad-suite disposition remain separate package responsibilities.

## Capability-floor and runtime rollback clarification

**Documentation precision review: PASS.** Revision `26c9e86ca` is a capability-graph-only compatibility minimum. The reopening harness loads its graph class/catalog while retaining current runtime dependencies; it does not deserialize EDDE climate NoDb with a wholly rolled-back application.

Direct inspection of the accepted Canadian `climate.nodb` confirms that `py/state/_climate_mode` uses jsonpickle enum reconstruction for `wepppy.nodb.core.climate.ClimateMode(17)`. The enum at `26c9e86ca` ends at mode 16. Therefore that revision alone must not be represented as capable of reopening saved EDDE climate state, even though it recognizes the additive capability graphs.

Rollback of projects that have saved EDDE state must retain both graph compatibility and EDDE-aware mode 17 hydration/build support, including the published-calendar behavior. The reviewed runtime is `d2ca5821b` plus calendar fix `202ab65f3`; an equivalent backport requires its own conformance evidence. No full rollback deployment was executed or validated. This clarification changes no runtime or authorization boundary and introduces no new security finding; it prevents graph-only evidence from being overstated as complete application rollback assurance.
