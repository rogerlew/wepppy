# Restore Portland group access and combined watershed results

This ExecPlan is maintained under `docs/prompt_templates/codex_exec_plans.md`. Keep Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective current. Package root: `docs/work-packages/20261012_portland_combined_viewer/`. The operator now authorizes forest execution through rollout readiness, including required local commits, forest restarts, and dev-agent permission changes; production mutation/deployment remains excluded.

## Purpose / Big Picture


A Portland group member should open the existing Portland collection links and see all selected watersheds with correct modeled values, units, ranges, and drilldown. The access correction must use existing group membership without publishing runs. The final viewer should reuse Deck.gl, the renderer already used by WEPPcloud's modern dashboard. A successful page load alone is insufficient: geometry and values must load and match retained model output.

## Progress


- [x] (2026-10-12 08:21 UTC) Scaffold package and capture operator's group-access intent; identify local `PortlandGroup` landing-page role.
- [x] M0: Refresh evidence, settle resource association/compatibility matrix, prepare canonical amendments, obtain two independent reviews, and record accepted checkpoint ancestor.
- [x] M1: Implement per-run group read authorization across the consumed surfaces and validate it directly.
- [x] M2: Prepare and validate legacy artifacts on a copied run; define repeatable bounded repair.
- [x] M3: Wire Deck.gl collection entry, generator, and old-link compatibility.
- [x] M4: Complete regression, browser, artifact, correctness, and security gates; retain the unrelated baseline frontend lint failure.
- [ ] M5: Complete authorized deployment, affected-run repair, live validation, and observation.

## Surprises & Discoveries


The October 10 investigation reported all 63 runs in nine Portland collection links exist under `/geodata/weppcloud_runs/` and lack PUBLIC markers. Combined entry returned 403 while the first run's geometry returned 200 anonymously. Both old viewers' loss/runoff data URLs returned 404; the empty generator returned 400. All seven current-condition runs retained `wepp/output/loss_pw0.txt` but lacked `wepp/output/interchange/loss_pw0.hill.parquet` and `watershed/subcatchments.parquet`. These are prior observations, not fresh retained evidence; M0 must reproduce them and retain sanitized results.

`combined_ws_viewer2` uses Leaflet.glify, not Deck.gl. Its introduction is commit `9e3c54dad` (2025-08-25). The generator still targets original Leaflet. Commit `97ae54748` (2026-05-03) added public-only validation; `f80bc5325` (2025-10-15) migrated old runoff visualization endpoints to query-engine. The generator's extent expansion assigns old bounds instead of the new outer bounds. Existing Deck.gl batch support requires a BatchRunner collection rather than arbitrary legacy IDs.

Local source now confirms `routes/locations.py:portland_index` requires `PortlandGroup`. This established role must not be conflated with the newer feature-action groups. The nine retained landing-page collections now supply the explicit63-ID server catalog reviewed at checkpoint `d75460acc`.

## Decision Log


2026-10-12 08:21 UTC, operator/Codex: Portland group members must see the referenced runs. Reuse the established membership mechanism and scope admission to authoritative Portland resources. Public markers were rejected because they widen publication instead of repairing group access. Prefix-based authorization and blanket validation removal are also rejected.

2026-10-12 08:21 UTC, Codex: target faithful migration of the combined workflow onto existing Deck.gl components, not a new service or forced BatchRunner migration. Scaffold completion is separate from implemented, wired, validated, deployed, and repaired status. Preserve data/display semantics; any parameterization change needs an ADR.

2026-10-12, forest handoff: preserve the existing legacy migration notice and its Load Without Migrating choice. Combined preparation remains additive and does not imply full-project migration. Accept the unchanged climate-test lint defect as a recorded baseline limitation; keep production identity/member acceptance in M5. ADR-0087 records the reviewed finite pointer-duration choice.

## Outcomes & Retrospective


Forest implementation and all 63 copied-run native preparations are complete. Each preparation records writer identity; 919 original file hashes match production and 24,669 hillslope rows match source values exactly. Independent reviews approve forest readiness with no unresolved high/medium findings. All nine collection browser checks passed; full Python passed 10,620 tests with 126 skips, and Jest passed 965 tests / 118 suites. Repository npm lint retains the unchanged climate.test.js conditional-expect defect; changed GL modules pass direct lint. Production remains unchanged. See tracker.md for current results and the rollout handoff for later, separately authorized production work.

## Context and Orientation


Start at repository root `/home/workdir/wepppy`; read root AGENTS.md and the nearest instructions for every edited subtree. `wepppy/weppcloud/routes/combined_watershed_viewer.py` parses run lists, requires PUBLIC markers, renders both legacy viewers, and exposes the URL generator. `wepppy/weppcloud/combined_watershed_viewer_generator.py` loads run configuration/map extents and constructs the share URL. `wepppy/weppcloud/templates/locations/portland/index.htm` supplies the nine scenario links; extract their run IDs and settings rather than manually recreating them.

`wepppy/weppcloud/routes/locations.py` guards the Portland landing page with PortlandGroup. `wepppy/weppcloud/utils/helpers.py` resolves canonical/legacy paths and ordinary run authorization. `wepppy/weppcloud/routes/nodb_api/project_bp.py` serves subcatchment geometry; `routes/nodb_api/wepp_bp.py` owns report/query surfaces. The query-engine under `wepppy/query_engine/` is the canonical async data service: call it directly, without adding Flask wrappers around its queries. Discover its actual auth and catalog contracts before changes.

`wepppy/weppcloud/routes/gl_dashboard.py`, `routes/batch_runner/batch_runner_bp.py:gl_dashboard_batch`, `templates/gl_dashboard.htm`, and `static/js/gl-dashboard/` contain the existing Deck.gl implementation. `batch-keys.js` preserves feature identity as a run ID plus a hillslope identifier so equal hillslope IDs in different runs do not collide. Reuse these mechanisms while preserving existing single-run/batch behavior. Read the dashboard's nearest AGENTS before editing it.

The canonical policy checkpoint is governed by `docs/standards/contract-first-change-standard.md`. Relevant current contracts include `docs/schemas/feature-access-governance-contract.md`, `weppcloud-browse-auth-contract.md`, `weppcloud-csrf-contract.md`, `output-scope-contract.md`, and `nodb-persistence-concurrency-contract.md`, plus `docs/ui-docs/controller-contract.md`. Read `docs/standards/generated-artifact-validation-standard.md`, `artifact-observability-standard.md`, and `hardening-lifecycle-standard.md`. A work package is not a replacement for canonical policy.

## Plan of Work


### M0 — Retain evidence and prepare the policy checkpoint


When implementation is requested, announce this plan explicitly. Use the wepp1-operator skill for read-only production inspection. Record hostname, UTC timestamp, deployed source/container revision, active services, and exact HTTP results. Resolve `/wc1/runs/` first and then the actual legacy path through `get_wd`; do not mistake absent canonical paths for lost data. Extract all nine collections from the deployed location template into a sanitized manifest, including actual configuration and resolved paths. Avoid recursive scans of large run trees.

Inventory membership and resource association without logging accounts' secrets or changing roles. Establish a server-owned Portland run association; prefer existing authoritative metadata/catalogs and never accept a user-supplied prefix as authorization. Enumerate ordinary public/owner/admin access, ownerless legacy access, member/nonmember/revoked membership, and all consumed data endpoints. The operator requires member access; unrelated existing anonymous behavior must not be removed by inference. Record precise compatibility decisions and any unresolved requirement.

Complete `artifacts/2026-10-12_contract_decision.md`; create `docs/ui-docs/contracts/combined-watershed-viewer-contract.md`, amend affected canonical cross-cutting obligations, and reconcile `docs/dev-notes/endpoint_security_notes.md`. Specify collection input, per-run checks, no partial authorization, membership revocation, response/error behavior, empty generator, optional variables, and link compatibility. Mark runtime conformance pending. Obtain two independent read-only contract reviews and disposition findings. Commit the accepted checkpoint separately before implementation; if commit authority remains unavailable, prepare the reviewable checkpoint and request it under the contract-first standard. Do not treat this scaffold as the ancestor.

### M1 — Restore bounded group read access


Replace the combined route's public-only assumption with a shared bounded read decision consistent with the approved contract. Preserve parsing and containment validation, independently authorized access, and current error contracts. Reuse PortlandGroup identity and the approved resource association; do not assign roles, add PUBLIC markers, or widen technical privileges. Require each run in a collection to pass before rendering or exposing metadata. Apply compatible authorization to the geometry, query, popup, and consumed file/catalog paths so fixing entry does not leave downstream denials or bypasses.

Extend `tests/weppcloud/routes/test_combined_watershed_viewer_security.py` and appropriate downstream tests. Directly exercise membership/resource checks for valid legacy state and hostile input, including a removed member and a mixed Portland/unrelated private collection. Keep existing public workflows. Document any shared helper change's effect on ownerless legacy runs. Acceptance: an authorized member reaches both page and data, while a caller without any valid grant cannot retrieve private collection data.

### M2 — Prove the legacy data path


Write the compatibility/regression and recovery manifest before any run-data mutation. Copy one current-condition run into an approved validation location; preserve source checksums and ordinary reader behavior. Discover existing geometry/summary/interchange converters and query-engine activation/catalog paths. Use retained model outputs first, with no model rerun or conversion triggered by GET. Missing source data must produce an explicit readiness failure rather than silent zero values.

Generate additive artifacts using existing owned tools, then parse the exact files consumed by query-engine. Compare geometry IDs, hillslope joins, row counts, null handling, units, and numeric values with legacy output; state tolerances and preserve baseline/roads scope. Keep source NoDb/model outputs unchanged. Demonstrate repeatability, interruption recovery, and rollback of only new derived outputs. Check actual downstream query rows and browsable provenance. Extend the manifest to seven current-condition runs and all other linked scenarios only after the first run passes and production data preparation is authorized. An artifact existing on disk is not acceptance.

### M3 — Wire the collection viewer and generator


Add an arbitrary authorized collection context to the existing Deck.gl path, keeping BatchRunner and single-run entry behavior intact. Resolve each run's real configuration on the server. Use composite run/hillslope identities, correct union bounds, shared variable ranges/units, and per-run popup links. Honor existing `ws`, `center`, `zoom`, `units`, `varopts`, `varname`, and `title` parameters; validate and safely serialize them. Do not repoint legacy URLs to an incompatible dashboard input shape.

Repair generator GET without IDs so the form can be opened, and validate actual POST/CSRF behavior. Fix combined bounds, encode titles and JSON safely, validate empty/malformed/duplicate lists, and avoid leaking unauthorized run metadata. Preserve optional phosphorus behavior and make partial data failures visible. Wire Portland links and compatible old combined URLs to the finished viewer. Update module/user/operator documentation in the same change. Acceptance: an existing Portland link and a newly generated equivalent URL load the same populated map and settings.

### M4 — Validate behavior and review independently


Run the tests below, then exercise the actual collection with member and nonmember browser sessions. Cover absent artifacts, empty collections, populated data, supported legacy state, malformed inputs, stale membership, and mixed authorization separately from display-variable combinations. Check initial load, variable/range/unit changes, popups, pan/zoom, and share/reload. Include special characters in titles and overlapping hillslope IDs across runs. Verify optional phosphorus separately from required loss/runoff readiness.

Retain a manifest linking the candidate revision, source and generated files, consumer queries, rendered numeric samples, browser console/network evidence, and authorization outcomes. Independent correctness and security reviewers must complete the scaffolded review artifacts; medium/high findings must be fixed and rechecked. Mark implemented/wired/local/environment statuses distinctly. Passing broad tests does not substitute for the real legacy artifact path.

### M5 — Deploy and repair under operator authority


Prepare a concrete rollout/rollback record using `scripts/deploy-production.sh` and the installed production wctl preset after reading their current instructions. Deployment is a later authorized action; follow wepp1-operator queue gates and host ordering. No parallel registry/image workflow. Revalidate real process identity, groups, mounts, configuration, and generated-file readability before rollout. Record exact deployed revision and any approved data-preparation command/manifests.

On wepp1 verify all nine collection links as a PortlandGroup member and the negative access cases, using fresh requests rather than stale caches. Retain artifact parity and map-value evidence. Monitor existing request/error signals for seven days as proposed in package.md, recording who owns follow-up. Roll back on data leakage, wrong numerical values, or ordinary-access regressions. Only claim incident resolved after deployed rendering, repaired artifacts, access controls, and observation are evidenced. Update package, tracker, project board, and durable docs; move the completed plan only when all required work is done.

## Concrete Steps


From `/home/workdir/wepppy`, start with read-only discovery:

    git status --short
    git rev-parse HEAD
    rg -n 'PortlandGroup|combined_ws_viewer' wepppy/weppcloud/routes
    rg -n 'combined_ws_viewer' wepppy/weppcloud/templates/locations/portland/index.htm

After contract approval and implementation, use canonical checks:

    wctl run-pytest tests/weppcloud/routes/test_combined_watershed_viewer_security.py
    wctl run-pytest tests/weppcloud --maxfail=1
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20261012_portland_combined_viewer

Add exact converter, query-engine test, and authenticated Playwright commands to this section as their existing supported interfaces are established in M0/M2. Read `tests/AGENTS.md` and the Playwright smoke AGENTS before authoring/running those checks. Expected result is passing checks plus an actual populated map; record skips or unavailable environments rather than claiming conformance. Use the retained focused and broad suite receipts for forest readiness.

## Validation and Acceptance


The original current-condition link names seven runs: BRnearMultnoma, FirCreek, LittleSandy, NorthFork, SouthFork, CedarCreek, and BlazedAlder, with IDs/configuration strings recoverable from the Portland template. Its title is Portland Current Conditions, units English, variable loss, center approximately [45.4367563, -121.9887543], zoom 10, and ranges runoff/subrunoff/baseflow 0.5, phosphorus 0.1, loss 4000. Preserve those settings. Also cover GRIDMET, future climate, Eagle/Norse simulated fire, high/moderate/low severity, and prescribed fire links.

A current member must see the authorized maps without changing PUBLIC markers. A revoked member loses only group-derived access. Public/owner/admin grants retain their contracted behavior, and no collection grants access to unrelated private runs. Missing required data is an explicit readiness failure, not a blank successful map; optional data remains optional. Bound error behavior, visibility, transport, and cache semantics must be fixed in the M0 canonical contract before code.

## Idempotence and Recovery


Keep existing branch and unrelated changes. No membership changes or PUBLIC markers are part of repair. Hash and preserve source data before additive preparation; only remove or restore outputs owned by this package's manifest. Record an interrupted-conversion retry procedure and never delete an entire run to recover. Do not overwrite existing derived artifacts without a retained baseline and explicit plan. Production code rollback follows the inspected canonical deployment path. Keep failed evidence and provenance visible through established authorized project tools.

## Artifacts and Notes


Use `artifacts/` for sanitized production observations, collection manifest, contract reviews/ancestor record, compatibility plan, generated-content comparisons, browser evidence, and rollout/recovery records. The original correctness/security checklists are historical scaffold templates; their successor implementation reviews carry current verdicts. Never store passwords, session cookies, tokens, or broad user-account dumps. Root tracker and package tracker must link the final evidence.

## Interfaces and Dependencies


Reuse Flask's existing route/identity system, `get_wd`, established PortlandGroup membership, current query-engine endpoints, NoDb readers, existing interchange conversion, and Deck.gl modules. No new external dependency is permitted. Preserve public function and URL contracts unless the accepted checkpoint names the exact compatible change. Keep the collection context explicit about run ID and actual config; keep feature identity composite across runs. No queue wiring is planned; if evidence requires it, revise the complexity budget and follow RQ catalog/live-tree gates before proceeding.

Revision note (2026-10-12 08:21 UTC): initial scaffold records the operator's group-access correction and separates entry authorization, data readiness, rendering, and deployment proof. No implementation milestone has started.

Revision note (2026-10-12 16:40 UTC): forest execution authorized. Fresh inventory confirms all 63 runs are ownerless; PCV-01 preserves their existing downstream visibility while repairing bounded collection admission. Reuse focused Deck.gl components rather than the full batch dashboard.

Revision note (2026-10-12 forest implementation): M0–M3 complete. All 63 original preparations were rolled back using verified manifests, their evidence directories retained, and regenerated with the final atomic-publication helper and content-addressed native/Python writer identity. Repeated Topaz polygon fragments are valid; identifier mappings must still be bijective and complete. Review-driven fixes also retain required variables when optional phosphorus is absent, disable controls during loading, return readiness errors for undelineated runs, restrict rollback output names, and remove bounds-viewer remote payload/HTML injection paths.

Revision note (2026-10-12 final mouse acceptance): actual picking found the correct polygon, but Deck/Mjolnir measured synchronous software-GPU picking (~2.5 seconds) as gesture duration and rejected it against the 250 ms tap limit. A scoped five-second click recognizer setting passed experimental picking, pan, zoom and share checks. The independent correctness reviewer approved this finite allowance over an unlimited cutoff; no distance/drag/double-click setting changes. Final served-code audit passed in 2.0 minutes, including unchanged selection after dragging, pan/zoom/share, artifact byte parity and all-nine native sample parity. ADR-0087 records the UI-only threshold choice.

Revision note (2026-10-12 regression follow-up): the initial broad run stopped after 8,764 passes/126 skips because a new test patched a stale parent-module reference. New route fixtures now use importlib.import_module consistently. The full WEPPcloud group additionally exposed its old standalone Portland render fixture missing the new collection-URL context; supplied the real catalog URL builder without changing assertions. All 1,969 WEPPcloud tests now pass. Required full-repository rerun passed 10,620 tests / 126 skips; all browser/access, artifact and role-restoration receipts are retained.

Revision note (forest handoff): M0–M4 are complete. Candidate `9c8293008` contains the runtime changes; follow-up documentation/evidence and a bounded drilldown smoke branch do not alter runtime. All 63 preparations and 919 original files passed identity/parity review. The sample run shell opens through the existing migration notice and Load Without Migrating under independent Admin; full production member/report acceptance remains M5. Exact dev-agent roles are restored and stored browser credentials deleted. No production writes or push occurred. Repository npm lint fails the preexisting unchanged climate controller test; that receipt is retained rather than reported as a pass.
