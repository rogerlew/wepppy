# MOFE input producer findings

**Audit opened:** 2026-11-02 19:32 UTC.
**Scope:** Original read-only audit plus approved bounded producer repair execution.
**Status:** M2/M3 producer source repairs implemented. The original findings below
retain baseline line references; see [execution disposition](20261102_producer_execution.md)
for repaired boundaries and validation. Current selected-release disposition: NATIVE-01/02 conformance verified for
261029 revision6; NATIVE-03 corrected at native `b581352b6` with bounded dynamic
acceptance. Historical rows below retain the original audit checkout evidence.
Specialized9005/RAP consumer acceptance remains HOLD; see MIPA-02 release evidence.

## Seed finding: incomplete PMET crop discovery

`wepppy/wepp/management/managements.py:get_plant_loop_names` enumerates `.man`
files but adds only `man.plants[0].name`. The writer in
`wepppy/wepp/management/pmetpara.py:pmetpara_prep` therefore cannot guarantee a
row for a downstream OFE's or later rotation's distinct crop. The Disturbed
writer also selects `man.plants[0].name`; its full applicability is under audit.

Native `src/infile.for` calls `pmetcoef` for every crop. `src/pmetcoef.for`
matches eight-character crop names and falls back to the first row when absent.
`src/evappm.for` selects `itype(nowcrp,iplane)`, so native PMET is not restricted
to OFE 1. The preliminary correction target is producer completeness and identity,
not per-OFE duplication of a globally crop-keyed table.

## Evidence classification

Confirmed source defects require a reachable trigger and exact source references.
Isolated reproductions establish only the exercised boundary. Static risks remain
investigative until reproduced or proven reachable. Existing tests are coverage
evidence only after their actual assertions are inspected; this audit does not
claim they were rerun. Unexamined surfaces remain explicit.

## Prioritized finding register

Severity describes potential input correctness impact, not measured project loss.
Source paths below are relative to WEPPpy unless prefixed with a sibling repository.
Line numbers refer to the inspected working trees, not an immutable clean release.

| ID | Priority / evidence | Trigger and finding | Repair target and acceptance |
| --- | --- | --- | --- |
| PMET-01 | High; real writer reproduction | `managements.py:3353` discovers only the first plant scenario; a two-OFE `.man` with `Tah_6892` and `OFE2_Tah_6892` produces only the first PMET row. Single-OFE multi-crop rotations also qualify. | `wepppy/wepp/management/managements.py:get_plant_loop_names`; enumerate required crops deterministically and prove every native crop resolves to intended coefficients. Uniform scalar coefficients can conceal the error. |
| PMET-02 | High; confirmed source path | Disturbed uses scalar `domlc_d`, `domsoil_d` and source `plants[0]`, not final segment assignments/synthesized names (`disturbed.py:2033,2047,2050,2112`). | `wepppy/nodb/mods/disturbed/disturbed.py:pmetpara_prep`; join segment soil/management provenance to final crop identity. Verify mixed disturbance and soil textures with different intended coefficients. |
| PMET-03 | High; confirmed format mismatch | `wepppy/wepp/management/utils/multi_ofe.py:309,314` prefixes long crop names; native keys are only eight characters. Conflicting equal-prefix rows select the first match. Disturbed can also emit same-name/different-coefficient rows across hillslopes. | Define collision-safe identity/reference handling and consistent duplicate semantics before implementing complete enumeration. Reverse table order in tests; intended results must not depend on it. |
| MAN-01 | High; real writer reproduction | Ordinary merge renames plants but misses `operation.data.iresad` remapping (`multi_ofe.py:304–345`); downstream residue operation selects the upstream plant. | Mirror the existing deduplicating branch's remapping at `:184–186`. Parse emitted operations 10/12 with distinct residue plant properties and verify correct OFE ownership. |
| MAN-02 | High; real producer reproduction | Both merge branches use the base OFE's rotation topology (`multi_ofe.py:241–246,366–372`). One-year oats plus two-year corn/soybean loses OFE2 Year 2; expanding to four years repeats Year 1. | Establish temporal alignment contract; preserve each schedule over requested simulation years or explicitly reject unsupported combinations before publication. Test 1/2 and 2/3-year cycles and both merge branches. Do not silently truncate. |
| MAN-03 | High; actual serialized readback failure, root cause open | The mixed multiple-rotation case expanded with `build_multiple_year_man(4)` writes a file rejected by `read_management()` with `IndexError: pop from empty list`; unexpanded round-trip also changes one OFE2 reference list. | Investigate `managements.py:2740–2806`, rotation serialization and reused year objects in `multi_ofe.py`. Compare intended, in-memory, serialized/reparsed and native timelines. Retain separately from MAN-02 until a shared root cause is proved. |
| SOIL-01 | High; actual method isolated via AST | `wepppy/wepp/soils/utils/wepp_soil_util.py:493–511` checks OFE0's developed land use once before applying `kslast` to all OFEs; staging calls it at `wepppy/nodb/core/wepp.py:742`. | Apply existing eligibility per OFE, including preservation mode and legacy top-level alias semantics. Test both orders through actual preparation and parsed `.sol`, not only extracted-method execution. |
| COVER-01 | High; confirmed static order defect | RAP creates string IDs (`rap_ts.py:163`) then sorts lexically in ordinary/transformed cover (`:361,435`): 1,10,11,2 rather than numerical order. | `wepppy/nodb/mods/rap/rap_ts.py`; align complete OFE sets/order with `.slp/.sol/.man`. Use at least 12 distinct cover blocks and the matching 9005 consumer. |
| SOIL-02 | Medium; confirmed emitted-field selection | Version 9005 writes `self.simple_texture_enum` for every OFE (`wepp_soil_util.py:748,863`); property `:1345` derives texture from OFE0 (`:1261,1272`). | Derive from current OFE or preserve admitted explicit input per the contract. Validate different textures in both orders, normal/debug serialization and preservation mode. Native 9005 verification remains open. |
| SLOPE-01 | High; installed native writer reproduction | Active buffer length zero emits NaN and a zero-length OFE; negative length emits negative length. Rust `wepp_interchange/src/mofe.rs:61,87–89,323–327`; numeric values reach it from `watershed_routes.py:1100`, `watershed.py:764`, `watershed_mixins.py:259`. | Validate enabled-buffer semantics at the owned native boundary and existing Python error boundary. Cover zero, negative, nonfinite, equal/greater-than-hillslope and ordinary values; no invalid generated file may be accepted as prepared. |
| SLOPE-02 | Medium; installed native writer reproduction | Accepted explicit fractions `[0,0.00001,1]` on 100 m emit one-point `1 0.00` OFE. Rust `mofe.rs:318,337` loses endpoint/length to output precision; `ag_fields/concept1_inputs.py:92–107,131` admits strictly positive tiny intervals. | Guarantee normalized endpoints and positive representable lengths, with explicit rejection where representation is impossible. Do not silently merge OFEs. Test native readback and cross-file identities. No affected actual project established. |
| API-01 | Low; confirmed inherited behavior | `min_length` is exposed by `slope_file.py:272` and Rust binding `lib.rs:1239`, but Rust `_min_length` at `mofe.rs:24` is unused. Requested minimum 10 m can emit 1 m OFEs. Legacy Python also ignored it. | Resolve/document the API contract separately; enforcing a new minimum is a behavior/parameterization decision, not an automatic audit repair. |
| NATIVE-01 | High; confirmed source bounds defect | Native accepts `ncrop <= ntype=20` (`infile.for:506`, `pntype*.inc:8`) but `ccrpet.inc:7` allocates arrays with `mxcrop=6` (`pmxcrp.inc:8`). `pmetcoef.for:63,72` writes all crop indices. | Native dependency, not producer-only repair authority. Prove 6/7-scenario behavior with a bound-checked isolated build and exact selected binary capacities; obtain separate authorization for a native correction or compatibility restriction. Missing PMET rows do not prevent the out-of-bounds fallback write. |
| NATIVE-02 | Medium/high validation dependency; confirmed argument mismatch | Actual EVAPPM uses `itype(nowcrp,iplane)` (`evappm.for:273,289,415`); daily/hourly adapters receive `kcb(nowcrp),rawp(nowcrp)` (`watbal.for:1108`, `watbal_hourly.for:1260`). | Observe actual EVAPPM lookup or separately validate/fix the adapter. Runtime authority and physical impact are unestablished; existing probe fields alone cannot prove correct MOFE PMET selection. |
| NATIVE-03 | High; imported S01 runtime confirmation, COR-S01-01 open | Layer-only FC/HK arrays retain another OFE's initialized values. With H11/H28/H40 materials on three OFEs, 10/15 observed slots use OFE 3's coefficients under each retention policy; actual PURK FC and executed PERC HK operands were observed. | Native dependency requiring separate repair authority. Verify initialized-versus-consumed ownership for each OFE/layer, distinct/repeated-material controls, both policies, executed HK branch and other confirmed shared consumers. Measure correction consequences; producer-only repair cannot close the native correctness HOLD. |

## Evidence retained and reproduction limits

NATIVE-03 is imported runtime evidence from the rock/water investigation, not a
new producer finding or a rerun of this audit's native checkout. Its detailed
[native dependency record](native_contract_audit.md#native-03-fchk-consumers-use-another-ofes-coefficients)
links the authoritative S01 report and receipts. The register now has fifteen
entries: eleven producer findings, one API ambiguity and three native dependencies.

Detailed reports: [management/PMET](management_audit.md),
[Python inputs](python_inputs_audit.md), [Rust producers](rust_audit.md), and
[native contracts](native_contract_audit.md). Their scripts and small generated
files are retained alongside them. Source inspection and execution provenance
are recorded separately; an installed extension is not claimed to have been
built from the inspected HEAD.

Management reproductions exercise real Python synthesis/serialization. The soil
override probe extracts the actual method through AST but does not run full soil
preparation. RAP order and texture enum are source-level findings. Rust cases use
the installed py312 extension, SHA256
`7f67d3a8e56066d43b2fdb1ffc5360d357d61f2fcc963190c67fe288373702ad`,
with no rebuild. Native PMET array/probe findings remain static only. NATIVE-03 separately reuses
S01's four complete ownership histories on its bound release source; no new native
simulation, deployed-project census or repaired-output impact study ran in this audit.

## Consumer and variant coverage

| Surface | Audit result | Remaining acceptance |
| --- | --- | --- |
| Generic/Disturbed PMET and management stacking | Findings PMET-01–03, MAN-01–03; staging prepares management before PMET, so no ordering defect established. | Real per-segment coefficients, rotations, native identity and capacity. |
| Soil staging, transforms, 9005 writer | SOIL-01/02; saturation, depth clipping/minimum depth and anisotropy iterate all OFEs. | Actual staging, aliases, uploads and matching 9005 native binary. |
| Native soil-water coefficient ownership | NATIVE-03 imports runtime-confirmed wrong-OFE FC/HK consumption under both retention policies. | Separate native authority and all-consumer validation; correct emitted soil identity alone does not prove correct consumption. |
| RAP ordinary/transformed cover | COVER-01. | At least 12 OFEs with distinct bands and consumer readback. |
| Rust slope automatic/explicit writers and Python callers | SLOPE-01/02, API-01; writer loops all OFEs. | Source-profile negative cases, map/slope consistency and complete native deck. |
| Rust watershed MOFE map | Shape, requested-ID uniqueness, source-cell presence and contiguous labels checked; fraction validation admits equal boundaries. | Zero-length interval rejection across map/slope boundaries; no actual corrupt map proved. |
| Soil stack and final staging count checks | `SoilMultipleOfeSynth.write` declares `len(stack)` while appending all source OFEs (`wepppy/wepp/soils/utils/multi_ofe.py:69–87`); current callers generally use single-OFE sources. Final staging lacks an obvious joint identity check. | Risk controls: multi-OFE stack member, stale/mismatched source counts. Not classified as an observed malformed project. |
| Roads controlled routed decks | Explicit scenario order/count observed; no concrete defect established in inspected path. | Broader specialized producers and treatment propagation remain unexamined. |
| Climate, snow/frost, groundwater, UI flag | Native contracts intentionally share climate/parameters or class factors; not first-OFE defects. | Preserve global semantics; no artificial per-OFE expansion. |
| Rust PMET/soil/management producers | None found in audited modules; these remain Python-owned. `roads_flowpath` emits geometry rather than WEPP decks. | Not a claim that every crate or external producer was audited. |

## Priority and scope disposition

NATIVE-03 adds a confirmed downstream correctness blocker alongside the PMET
dependencies. Reuse S01 evidence rather than rerunning it for documentation.
Producer input-identity acceptance and native coefficient-ownership acceptance
must remain separate; fixing one does not establish the other. Native correction,
affected-consumer assessment and before/after consequence validation require
separate authorization. The existing COR-S01-01/general-release HOLD remains.

Resolve native PMET capacity and trustworthy observation before claiming end-to-end
PMET repair. Independently reproduce and repair management reference/calendar
defects, per-OFE soil/cover selection, and invalid slope emission. API-01 and
unproven boundary risks require decisions/reproductions, not speculative behavior
changes. SOIL-02/COVER-01 need the actual 9005-capable consumer: the inspected
`/workdir/wepp-forest/src/input.for:471–473` reads an older header layout and
cannot establish 9005 texture/cover consumption.

These findings justify the work package. They do not authorize changing binaries,
model physics, native capacities, existing project inputs or retained rock/water
evidence. Rock/water local closeout is complete; its native correctness and package
closure remain blocked. The current handoff is an audit and implementation scaffold.
