# MOFE Water Consumer Accounting

**Status**: Complete (2026-10-20); development acceptance validated.
**Started**: 2026-10-20 20:15 UTC.
**Owner**: WEPPpy/wepppyo3 maintainers; requesting operator.
**Plan**: [ExecPlan](prompts/completed/mofe_water_consumer_accounting_execplan.md).
**Tracking**: [Tracker](tracker.md).

## Purpose

Make hillslope precipitation, outlet runoff and lateral flow represent the same
physical control volume in reports, dashboards, daily loaders and exports.
The preceding ET/Dp package corrected local losses but explicitly preserved
routed fields. This package addresses the remaining consumer discrepancies;
it does not reopen that closed historical package or change WEPP physics.

The operator requested execution on 2026-10-20, superseding the prior scaffold
instruction. M1 paired-source investigation found that physical WAT runoff and
PASS-exported runoff differ because of model event thresholds. The operator selected physical WAT runoff; see the
[contract preparation](artifacts/20261020_contract_decision.md).
Canonical amendments and ADR-0099 passed two independent reviews. Implementation and the paired native release now pass generated-output and
browser validation. Production deployments and original project outputs remain
unchanged.

## Evidence and scope

[Consumer audit](notes/consumer-audit.md) inventories direct calculations,
indirect consumers, controls and unresolved version semantics. A retained
[readback receipt](artifacts/20261020_audit_readback.json) binds Ayush Poudel's
workbook to its SHA-256 and records an actual native-writer counterexample.
The workbook itself remains at its supplied `/tmp` path and is not committed.
Its formulas are evidence, not a complete or authoritative model contract.

Confirmed remediation targets:

1. Native average-annual hillslope report sums P, QOFE and latqcc over OFEs.
2. Dashboard selected and comparison event branches sum P and Q over OFEs.
3. Daily WAT collapse averages cumulative Q and internal lateral transfers;
   Ash/WATAR consume Q from this frame.
4. Features Export uses terminal representatives for fields beyond ET/Dp,
   including unconverted local lateral depth and local precipitation/state fields.
5. AshPost's streamflow correction subtracts all-OFE QOFE volumes, counting
   internal runoff transfers as exported water.

Also disposition TotalWatSed's raw Q/QOFE diagnostic columns, legacy R residual
calculations and the closure tools' QOFE assumptions. Do not silently change
legacy public column meanings, model calibration, storage temporal aggregation,
or diagnostic transfer sums. Every finding needs a regression-backed fix or an
explicit, visible scope/compatibility disposition before implementation closure.

## Proposed scientific direction

For local fluxes, including P and existing ET/Dp, daily hillslope depth is
`sum(depth_i * local_area_i) / sum(local_area_i)`. For serial lateral routing,
outlet-equivalent depth is `latqcc_terminal * area_terminal / area_hillslope`.
Internal runon cancels when forming the whole-hillslope budget; it remains
necessary in each local OFE budget. Never sum local routed depths or treat every
OFE boundary as a separate hillslope outlet.

Surface runoff must be derived from a verified outlet-volume basis. H.pass
`runvol` is a candidate authority already used by TotalWatSed. Terminal WAT Q
is cumulative-length normalized in the inspected non-contour source. QOFE is
local-area normalized in the supplied workbook but duplicates Q in the current
non-contour daily/hourly writers. Establish supported versions, contour/width
assumptions and source availability before choosing consumer behavior. Do not
infer semantics from equality of numeric values or blindly rescale QOFE.

Keep raw WAT interchange rows and schemas intact. Raw mode remains OFE-local;
collapsed hillslope mode must document each field's basis. Keep ET/Dp fixes,
public APIs, existing temporal selection/divisors and baseline/Roads scope
isolation unless an independently reviewed contract explicitly changes them.

## Compatibility and regression plan

Before code edits, amend current canonical water, output-scope, report-cache,
Features Export and any affected Ash contracts, and add a parameterization ADR.
The current water contract explicitly preserves routed sums; this work changes
intended behavior and requires two independent contract reviews and a standalone
checkpoint ancestor. Record execution/commit authority at that milestone.

Version report and export numerical caches. Assess Ash model and AshPost output
refresh mechanisms: a daily-loader correction changes persisted model outputs,
not just a view. Preserve historical artifacts and label stale/unverified
results; no bulk deletion, original-run regeneration or production rollout.
Pair native builds, Python facade checks, startup hash and image source ref.

Required cases include unequal OFE areas, serial three-OFE routing, single OFE,
unequal widths/contour provenance, mapped native IDs, sparse/missing terminal
days, joined sources, absent observations, hidden Area selection, nonfinite
inputs, all temporal modes and old/new source/cache generations. Explicitly
separate local flux totals, outlet totals, internal transfer diagnostics and
storage snapshots. Require real serialized/exported/browser results, not only
mocked orchestration or arithmetic copied into tests.

## Acceptance

For the retained synthetic daily fixture, corrected hillslope P/Q/lateral/ET/Dp
are 10/8/4.5/5/7 mm. The currently installed native writer instead returns
20/12.6666667/10/5/7. Preserve this pre-fix evidence.

For the workbook's complete Two_OFE records and actual printed areas,
average-annual P/Q/lateral/ET/Dp are approximately
1080.016129/119.753300/283.678541/502.543831/175.323871 mm. Compare using all 31
calendar years for this fixture; do not silently apply the report's different
existing annual divisor. The -1.283414 mm/year residual is before complete
storage accounting and does not establish exact physical closure.

Final execution must reconcile fresh native report rows, daily loader, selected
and comparison SQL, Features Export and affected Ash outputs against independent
volume/area and pass-file controls. Retain source versions, requests, hashes,
cache state, serialized identities/geometries and user-visible downloads on an
isolated actual MOFE project. Production deployment and historical repair are
separate acceptance claims.

## Boundaries and complexity budget

Reuse Rust, DuckDB and existing cache/materialization paths. No new dependency,
service, queue, datastore, privilege or runtime topology. No WEPP source or
binary changes, annualization redesign, channel-physics changes, generic
aggregation framework, unrelated GeoJSON-envelope repair or wholesale legacy R
deletion. If provenance cannot resolve a field, document that blocker instead
of inventing a fallback that hides an unknown normalization.

**Security impact**: low; existing authenticated routes, contained native paths,
publication permissions and output schemas remain intact. No new process,
service, dependency, privilege or deployment topology. Independent
correctness review and artifact readback are mandatory for execution closeout.

**Highest claim**: implemented physical WAT accounting with reviewed contracts,
focused and broad regressions plus actual generated/browser/export readback.
Report performance and independent review are complete. See the
[validation receipt](artifacts/20261020_validation.md) for combined gate coverage
and retained scientific limits. No production rollout.
