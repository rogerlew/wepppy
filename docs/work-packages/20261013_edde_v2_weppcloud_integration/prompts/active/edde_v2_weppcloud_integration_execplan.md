# Execute EDDE v2 WEPPcloud integration

This living ExecPlan follows docs/prompt_templates/codex_exec_plans.md. The operator authorized execution. Update this plan and tracker through final acceptance; do not alter closed feasibility/PRISM packages. No production deployment is included.

## Purpose / Big Picture


Expose Future EDDE v2 in eligible US/Canadian projects using the accepted raw source and CLIGEN hybrid. A user selects model/scenario and future years, generates Single or eligible Multiple PRISM climates, runs WEPP, and inspects the actual source and generated artifacts. Existing methods and saved project capabilities remain intact.

## Progress


- [x] Inspect existing catalog, parser, build router, PRISM staging, capability authorities and RQ build path; identify additive mode17 and one combined projection field.
- [x] M1: Complete canonical contracts, two independent reviews, standalone checkpoint and additive capability reader floor.
- [x] M2: Wire catalog/profile authority, atomic parsing and staged EDDE build with project/grid/PRISM eligibility, source acquisition and supersession checks.
- [x] M3: Add UI projection control, provenance/report visibility, user/operator documentation and regression coverage.
- [ ] M4: Validate actual US/Canada job-to-WEPP artifacts, negative cases, compatibility, browser/archive, required gates and independent correctness/security review; commit handoff.

## Surprises & Discoveries


Schema-v3 capabilities are exact registered structures, not an extensible dataset list. Additive climate exposure requires reader-first registration for both ordinary and single-input variants. Stored graphs cannot gain EDDE silently. Existing PRISM staging captures observed years and cannot be called blindly for a future build; reuse its native revision and normal-acquisition helpers within the new EDDE staging transaction. Source acquisition reads full monthly objects, so private yearly caches avoid retaining an entire multidecade archive in project downloads.

## Decision Log


The operator explicitly authorized this package after accepting raw EDDE and station-derived auxiliary weather. Use one combined model/scenario select to prevent impossible combinations and retain existing future-year/station/spatial controls. No default projection is invented. Admit initial archived ranges, with live record checks. Reuse the existing tracked climate RQ job and timeout; acquire with one private yearly cache and the existing client budget. Blank seed omits CLIGEN -r, matching the existing daily-replay path; explicit study seeds remain reproducible. All generated evidence remains visible in project climate attempts; temporary source cache is reconstructible from manifests.

## Context and Orientation


Work in /home/workdir/wepppy. Starting revision6acfb3d23; preserve unrelated generated usersum docs_index.json. Catalog/profile/graph owners are wepppy/nodb/locales/{climate_catalog,locale_profiles,capability_graph}.py and capability_structures/catalog.json. Climate facade, input parser and router live under wepppy/nodb/core/. Use a narrow climate_edde_build.py collaborator, existing _derived_build.finalize/publish_files and climate_build_helpers normal/native writer helpers. Existing client/adapter are wepppy/climates/edde/{client,cligen}.py. Frontend is controllers_js/climate.js, controls/climate_pure.htm and reports/climate.htm. RQ build-climate already captures/replays payload and provides tracked conflict handling. Read nearest instructions and current contracts before edits.

## Plan of Work


M1 promotes EDDE-WEPP-01 to docs/schemas/edde-v2-weppcloud-contract.md and amends capability/RQ/client references. Retain exact scope/state/error matrix in contract decision artifact, obtain required two independent reviews and commit ancestor. Register new graph shapes before changing live catalog/profile writers; retain direct reopening/unchanged-byte evidence.

M2 adds mode17, optional durable projection property, required EDDE year/projection validation with parser rollback, locale and spatial validation, and a staged builder. Validate grid and all required normals before weather acquisition; collect one watershed series per year into retained CSV/manifest. Use existing station/seed behavior and EDDE replay. Produce and validate Multiple PRISM files before publication, including finite/ordered normals, nonnegative target precipitation, positive reference precipitation and matching period/unit provenance. Apply supported None/Scalar/Monthlies/Spatial scaling in stage; reject AnnualMonthlies before enqueue because future observations are unavailable. Skip the router scaling pass for EDDE. Capture all influencing selection/scaling/geometry settings and compare fresh inputs at commit; retain failed attempts. Update snapshot maps/years/monthlies/provenance only with successful artifacts. Preserve old outputs across failed rebuilds and retained attempts across normal cleanup.

M3 exposes the combined select via catalog input sections, ensures serializer visibility and saved-state reload, adds truthful source/hybrid/report links and domain docs. Update API discovery schema for EDDE fields if existing schema is closed/explicit. Preserve auth/CSRF and queue shape; update dependency catalog only if enqueue wiring changes.

M4 uses actual eligible source projects copied to new scratch runs, including Canadian geometry, source data acquisition, authenticated request/worker acceptance, Single/Multiple and negative cases. Trace persisted selection to exact generated and prepared CLI hashes, fresh WEPP outputs and report/download/archive readback. Reuse hash-verified source caches only through real client integrity checks; do not label fixture-only execution live acquisition. Record identity/mounts/config/umask and source inputs. Review correctness and security, resolve findings, run required gates and keep failed probes as evidence.

## Concrete Steps


Use wctl run-pytest for focused catalog/parser/build/routes/template tests, wctl run-npm lint/test for controllers, rebuild controllers with the canonical build script. Run wctl run-pytest tests --maxfail=1 after substantive changes; stubtest changed API targets and check-test-stubs. Run changed-exception enforcement, code-quality observability and scoped doc-lint. RQ graph checks apply if enqueue wiring changes. Record actual commands/results in artifacts and tracker.

## Validation and Acceptance


Require nonempty complete finite daily source records, native-cell eligibility, ordered final CLI temperatures, unchanged CLIGEN guards, persisted model/scenario/years and actual prepared-file hashes. Canadian point climate on US geometry is insufficient: actual Canadian project acceptance remains required. Existing/absent optional metadata must not block legacy methods; malformed selections must fail before mutation/enqueue. Source and auxiliary-field attribution must reach reports. No stale status or filename existence substitutes for parsed content and fresh consumer evidence.

## Idempotence and Recovery


Use new visible attempt directories and isolated scratch projects; do not rebuild originals. Cache bytes are disposable; manifests/extracted points/generated evidence are retained. Failed/stale builds must preserve previous publication and cannot restore old input settings. Rollback preserves reader floors once new capability graphs have been written, and disables new writer exposure through existing release procedures only when separately authorized.

## Artifacts and Notes


Keep contract/review decisions, source identities, exact graph identities, actual project/consumer receipts, validation logs and failures under this package. Original feasibility evidence is immutable. Canonical current rules live outside work-packages.

## Interfaces and Dependencies


No new dependency, service, queue, provider or scientific correction. Public client interface remains stable. Additive mode/catalog/projection fields are specified in EDDE-WEPP-01; all prior identifiers and persisted capabilities remain supported.

## Outcomes & Retrospective


M1–M3 implemented. Contract checkpoint `75b47f61f` and reader floor `26c9e86ca` precede writer changes. Actual Canadian Single and US Multiple PRISM climate jobs passed. All 53 Canadian hillslope WEPP water-balance files contain the requested 366 days of 2060 and precipitation matching their prepared CLI files; all 83 US prepared CLI hashes match published spatial climates. US full WEPP initially stopped because the copied source project had never built soils; build those through the existing API and retry. M4 full-suite, failed-attempt/archive evidence and final reviews remain in progress. No production deployment.

Contract review amendment (2026-10-14 UTC): clarified scaling availability and atomic publication, normal validation/provenance, optional application seed and failed source-cache diagnostics. These resolve integration gaps without changing scientific policy.

Acceptance discoveries (2026-10-14 UTC): existing Wmesque PRISM 800m M4 products are 1991–2020, verified from original provider XML; response metadata has no explicit period, so record the provider product contract and actual acquired hashes. An older US saved graph correctly rejects EDDE until an explicit supported capability refresh. Reader-floor reopening passes all eight US/Canada, ordinary/single-input, single/multiple-OFE cases with unchanged config bytes.
