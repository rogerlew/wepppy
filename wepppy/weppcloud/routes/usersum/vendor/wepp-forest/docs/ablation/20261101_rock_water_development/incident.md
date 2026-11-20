# Rock-water accounting and frost compatibility development

- `incident_id`: `20261101_rock_water_development`
- `status`: `active`
- `scope`: `hillslope`
- `author`: `Codex`
- `date_utc`: `2026-11-01`
- `host_scope`: `dev`
- `contract_refs`: `requires_scientific_review`

## Problem and baseline

Whole-soil retention candidate84543461 with KSFLAG1 stops at simulation year9,
day355,OFE3,hour1 with HOURLY_WATER_UNMET. Relative allocatable ST is zero; dry
reference water is unavailable to this withdrawal. A tiny negative request does
not authorize a floor. A01-v2 unchanged-binary replay and A02-v3 insertion-only
IDAT observations reproduce STOP1 with byte-exact ordinary/full-frost outputs;
A02 also preserves all earlier observation bytes.

## Attribution and candidate

IDAT rounds new melt plus carried canopy water before allocating residue. At the
observed limiting branch this exceeds represented primitive supply by
5.820766091346741e-11m. Routing contributes zero. Merely widening downstream FIN
cannot repair already excessive accepted storage.

A03-v2 changes only the interception allocation mechanism and confirmed consumers:
IDAT allocation/net interception, daily/hourly FIN and ROCHEK effective-plane
interception subtraction. Existing capacities, allocation priority, geometry,
furrow placement and unmet-withdrawal guard remain. One independently reviewed
full16year replay completes17,532 daily records and exact target producer/consumer
budget checks. This is diagnostic improvement, not promotion.

Review found mixed-exponent and cancellation counterexamples to universal exact
conservation in the initial DOUBLE implementation. A04 develops an original
error-free expansion helper with exact accepted-store comparison. Scalar controls
are separate from native execution and do not admit physical retention/frost.
Carry-transfer and storm-depletion consumers still need direct assessment.

## Frost policy compatibility

F01-v4 executes ten unchanged-binary processes. Legacy2010 Roads reaches frostN
with or without frost.txt and has sidecar-sensitive frozen stocks. Legacy eRMiT
also reaches frostN; corrected retained readback validates all3,653 source-year
water records without rerunning models. Modern cases stop before simulation on
missing roughness-control.txt; no-hit does not prove suppression. F02-v2 prepares
six reviewed processes with explicit baseline roughness control: full16year modern
Roads and first two consecutive eRMiT source years7/8 on both engines. The latter
is exploratory; modern strict calendar validation excludes the original selected
nonconsecutive ten-year climate.

## Gates and evidence

Private raw root: /workdir/wepppy/out/rock-water-development-20261101.
Source-free program docs and original helpers:
/workdir/wepppy/docs/work-packages/20261101_rock_water_development.
The active ExecPlan, decision ledger and per-batch declarations bind evidence,
source, tools, runtimes and independent reviews. Private patches/binaries remain
outside public Git. Previous raw roots and historical packages remain immutable.

A03 target gate requires full completion, finite seven-output inventory, complete
calendar, exact primitive budget/capacity bounds and matching FIN/hourly allocation.
No target-only run admits non-target behavior. Wider12cell controls, domain/flux
closure, watchlist and full-project regressions remain mandatory before promotion.
Current mutation disposition is requires_scientific_review. No native source,
default binary, deployment or existing project has been changed.

## Remaining work

Resolve precision and confirmed shared-consumer risks, execute volumetric domains
and accepted fluxes, isolate frost from conductivity, then run canonical native
regression/release gates. Retain every failed candidate and parser invocation.
Update matrix/contract observations and finalize artifact inventories when each
stable checkpoint has no writers. Native release/adoption remains unapproved.

## Reviewed integration update

The original DOUBLE-only A03 proposal is rejected. A04 exact expansion helper
passes 20,839 fraction-oracle controls and all twelve full histories; zero-rock
pairs remain exact under both KS settings. A06 observes 64,935,267 domains without
an invalid domain, and A07 verifies selected storm/carry arithmetic without an
executed runoff response. Existing carry timing remains an open physical question.
F04 isolates frost from conductivity: legacy frost executes, but broad restoration
is not scientifically admitted; retain current policy.

N01 general candidate passes 1,260 tests, two host smokes and 31 watchlist cases.
N02 paired 491-hill/211-channel/nine-year watersheds complete with unchanged inputs
and output filenames. Outlet volume changes -0.82 m3, sediment -2.41 kg. Exact
placeholder profile outputs remain unavailable, not valid numeric profiles.
Independent scientific/implementation reviews admit the exact source/helper and
complete live test-tool/fixture set to canonical integration. This supersedes the
earlier no-source-change statement; released binaries remain unchanged.

Operator authorizes same-name undeployed wepp_261029 re-release with revision-5
notes after remaining Roads, full Disturbed and exact dated-binary gates. No
retention defaults, frost-policy change, deployment or Windows release is admitted.
Private N01-integration-v1/source-manifest.json binds all 56 integrated files.

## ELEMENT Sm serialization repair admitted

The original840case Roads comparison exposes numeric Sm stars also present in
revision4:74,267fields across99historical cases. Both SEDOUT and CONTIN used
F7.3 for watcon*1000. E01 adds bounded seven-character rendering only: F7.3,
F7.2, ES7.1 and ES7.0 as needed. Source-extracted and actual Rust controls pass
36cases each; four full histories replace14/14/14/0 fields with all other raw
bytes and six other outputs exact. Independently admitted for integration;
source test test_element_sm_format.py passes36 focused cases. No physical
parameter changes or numeric-star reader waiver. First partial build attempts
failed missing dependencies; final complete507-input staging succeeds.

The initial Roads reader also misclassified site source years2000–2015 as
relative1–16. Correct its explicit source-year contract in a fresh reader; retain
all840processes and failed receipts. Final dated pair must be rebuilt and gated
with both admitted changes.

## Bounded snow and freeze-restoration integration admitted

On 2026-11-02 the parent coordinating agent admitted both components under the
user-authorized program after independent actual science/implementation review.
[Snow cohort admission](../../../../wepppy/docs/work-packages/20261101_rock_water_development/artifacts/R05-snow-cap-cohort-science-admission.json)
binds all 21 histories and six response cases; positive runoff/sediment and
retained ET-policy consequences remain explicit.
[B04 actual disposition](../../../../wepppy/docs/work-packages/20261101_rock_water_development/artifacts/B04-restoration-science-actual-v1.md)
admits the bounded existing-ice donor cap, not universal thermal validity.

Canonical integration changes FRZNG, MELT and SNOWD with permanent fixtures and
source specifications. All 98 targeted actual-routine checks pass with zero
skips under the system compiler. Exact receipts and raw/staged/committed source
identity evidence are retained in WEPPpy's private
`combined-canonical-integration-v1` packet; historical proposals and failed
preparations remain immutable. No observer source or binary is integrated.

Final combined-source compatibility, complete native regression, fresh final
binary pairing, P03/project evidence and release/adoption gates remain pending.
Neither component admission changes retention/frost policy, validates retained
physiological semantics, or authorizes promotion, vendoring or deployment.
