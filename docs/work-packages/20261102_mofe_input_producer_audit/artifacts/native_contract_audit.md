# Native MOFE consumer contract audit

Status: original static source audit, supplemented by separately bound S01 runtime
evidence under NATIVE-03. No new implementation or native execution in this audit.
Audit date: 2026-11-02 UTC. Scope: `/workdir/wepp-forest/src` consumers relevant to
WEPPpy/wepppyo3 multi-OFE input producers. OFE means overland flow element.

The inspected repository HEAD is `04f1c4d26bcef217009c124151f877dcbf3985cb`.
Read `AGENTS.md` in that repository. No native source, binaries, active inputs or
test artifacts were changed; no compilation or simulation was performed.
The source capacities below are **not verified deployed-binary capacities**.
Bind the actual selected executable and build manifest before claiming runtime
exposure, successful reproduction or remediation.

## Confirmed findings

### N1: PMET crop capacity differs from accepted management capacity

Severity: high; confirmed source bounds mismatch, runtime reproduction pending.

`src/infile.for:506` accepts `ncrop` through `ntype`. The inspected
`src/pntype.inc:8` and `src/pntype_hill.inc:8` specify `ntype=20`.
`src/infile.for:1550` calls `pmetcoef` for every scenario from 1 through `ncrop`.
However, `src/pmxcrp.inc:8` specifies `mxcrop=6`, and `src/ccrpet.inc:7`
allocates `kcb(mxcrop),rawp(mxcrop)`. Writes at `src/pmetcoef.for:63` and `:72`
use the caller's `iorder` without a six-scenario limit.

Trigger: more than six plant scenarios with PMET enabled, regardless of the
number of OFEs. A successful producer change that enumerates all plant scenarios
does not resolve this native mismatch. Both matched and missing-name fallback
branches write the out-of-range index.

Remediation prerequisite: determine exact supported scenario capacity for the
selected binary; coordinate native capacity repair or explicit producer rejection
of unsupported input. Do not impose a six-OFE limit: plant-scenario count and OFE
count are distinct. Native changes require their own build/release gates.

Acceptance: bounds-checked isolated native controls with six and seven scenarios,
plus per-OFE selected-coefficient readback from the supported executable. Retain
source/include/build provenance and distinguish successful parsing from safe use.

### N2: PMET identity is an eight-character first-match crop key

Severity: high correctness risk when producer names collide; native contract is
confirmed, concrete producer reachability belongs to the producer audits.

`src/scenhd.for:48` uses `FORMAT(A8)` for management scenario names.
`src/pmetcoef.for:20` and `:35` declare eight-character crop and lookup names.
The first match at `:61` is read at `:63`, followed by an immediate exit at `:65`.
The fourth column is read into local `line`; it is not an OFE selector. If no name
matches, `:68` through `:72` reread the first data row and print a notice.

Distinct OFE coefficients require distinct native crop identities and matching
management references. Adding duplicate rows cannot express different coefficients
for the same crop name. Names with an identical first eight characters collide.

Producer acceptance: complete scenario coverage across OFEs and rotations;
consistent native-normalized keys; reversed row-order controls; missing-name,
identical-duplicate, conflicting-duplicate and eight-character-prefix controls.
Preserve all references if an approved repair introduces unique names. Avoid
silently changing established crop identities or default-fallback semantics.

### N3: Process-probe PMET arguments differ from EVAPPM's lookup

Severity: medium/high validation risk; confirmed argument mismatch, runtime
authority and physical consequences not established by this audit.

`src/evappm.for:273` sets `crpindx=itype(nowcrp,iplane)` and uses
`kcb(crpindx),rawp(crpindx)` at `:289` and `:415`. In contrast, process-probe calls
pass `kcb(nowcrp),rawp(nowcrp)` at `src/watbal.for:1108` and
`src/watbal_hourly.for:1260`. Those values reach adapters through
`src/watbal_process_probe.f90:1413` and `:1689`.

Trigger: the current rotation-slot index differs from its plant-scenario index,
which can occur in heterogeneous MOFE management. Probe fields alone cannot prove
the coefficients actually selected by EVAPPM. Determine enabled adapter authority
before attributing physical model behavior to this mismatch.

Acceptance: observe actual EVAPPM selection for each OFE and rotation transition,
and independently compare adapter arguments to that selection. An observer repair
must not be conflated with a production numerical repair.

### NATIVE-03: FC/HK consumers use another OFE's coefficients

Severity: high; runtime-confirmed in S01, imported as a native dependency.
Canonical finding: **COR-S01-01, open**. The
[S01 final report](../../20261101_rock_water_development/artifacts/S01-final-disposition.md),
[evidence summary](../../20261101_rock_water_development/artifacts/S01-final-disposition.json)
and [correctness review](../../20261101_rock_water_development/artifacts/20261102_correctness_review.md)
retain the observations and independent reviews. No experiment is rerun here.

FC is a layer's field-capacity water depth above the dry reference; HK is the
exponent used for unsaturated conductivity adjustment. Both are shared layer-only
arrays, while relevant water states and soil properties are indexed by layer and
OFE. Sequential initialization overwrites FC/HK; subsequent consumers use the last
writer's coefficients without restoring the current OFE's values. For unequal
layer counts, the last writer must be established per layer, not assumed to be
the final OFE.

S01 retained H11 geometry/management/climate and assigned H11/H28/H40 materials
to OFEs 1/2/3. Four 2000–2015 histories covered default/optional retention, each
plain/observed. Each pair's seven ordinary outputs matched exactly. Under each
policy, binary32 readback found 10 of 15 observed slots on OFEs 1/2 consuming
OFE 3's initialized FC/HK. PURK used wrong-owner FC in water-excess calculations;
PERC actually executed the below-0.95 saturation power with wrong-owner HK.
These observations establish operand ownership, not corrected hydrograph error.
No repaired model or affected-project census was run. Equal coefficients can
conceal the defect; repeated source material alone is not a general safety class.

Provenance differs from N1–N3: S01 binds release source
`d2e14d96af5942409c9a315dc8594fcc164a702a` in
`/workdir/wepp-forest-release-20261009`, with exact executable/observer identities
in its retained receipts. It does not establish runtime behavior of the inspected
`04f1c4d...` checkout or an arbitrary deployed binary. The source pattern predates
revision 5; preexistence does not prove harmlessness or unchanged exposure.

Remediation prerequisite: separately authorize native correction and assess all
confirmed FC/HK consumers, including drainage/lateral paths. Preserve both input
policies and existing-project soils; neither policy fixes native array ownership.
Producer repairs may proceed within their own authority, but cannot close this
native gate or support unrestricted heterogeneous-use readiness.

Acceptance after authorization: bind exact source/build/binaries; retain the S01
failure as a baseline; compare initialized and actually consumed coefficients for
each OFE/layer under both policies. Include distinct materials and a repeated-material
control, distinguish initialization from dynamic calls, and require actual HK power
execution and exact plain/observer parity. Assess unequal layer support and other
confirmed shared consumers. Measure before/after runoff, drainage, storage and ET
on copied projects without claiming universal calibration. Scheduled tillage/later
density, Rosetta2/missing-density and guard activation remain explicit S01 limits.
General release and package closure remain HOLD until the native finding is
resolved under its own acceptance gates. The durable boundary is the
[whole-soil contract](../../../schemas/whole-soil-water-capacity-contract.md#known-native-coefficient-ownership-defect).

## Correct multi-OFE and intentionally shared contracts

| Surface | Native contract and evidence |
| --- | --- |
| Management count | Actual structure count is `nwsofe` at `src/infile.for:1335`; `jstruc` receives it at `:1336`; initial scenarios are assigned per OFE at `:1344`. Early `iofe` is builder metadata (`:490`). |
| Slope count | Must equal management structure count (`src/infile.for:1676`, `:1678`). |
| Soil count | Must equal management structure count (`src/infile.for:1952`). |
| Soil rows/tail | `src/input.for:366` and `:372` loop all OFEs; per-OFE headers, horizons and restrictive-layer tail are read at `:480`, `:539`, `:641`. |
| Hillslope aspect/width | Read once and copied to subsequent OFEs in hillslope mode; watershed-version branch reads per plane (`src/input.for:380`). Shared values here are intentional. |
| PMET consumption | Daily OFE loop reaches water balance (`src/contin.for:1009`, `:1077`); daily/hourly water balance selects EVAPPM (`src/watbal.for:525`, `src/watbal_hourly.for:628`); EVAPPM selects the OFE crop (`src/evappm.for:273`). |
| Climate | One climate file is opened for the hillslope (`src/infile.for:1705`). Appending OFE-specific climate records is not supported by this contract. |
| `snow.txt` | Three global parameters (`src/infile.for:1566`). |
| `frost.txt` | Global controls plus land-use-class factors, not OFE rows (`src/infile.for:1612`). |
| `gwcoeff.txt` | Shared initial groundwater depth and coefficients (`src/main.for:146`). |
| `wepp_ui.txt` | Presence enables a global mode; its contents are not an OFE table (`src/main.for:188`). |

This inventory is bounded to the inspected input and PMET paths. It is not an
exhaustive audit of every native irrigation, channel, phosphorus or management
operation contract.

## Work-package acceptance implications

Classify producer artifacts as crop-keyed, OFE-ordered or intentionally shared.
Use a heterogeneous MOFE fixture with distinct crops and at least one rotation
transition. Read back the actual staged files and native coefficients for every
OFE; count equality alone cannot detect a consistent but incorrect permutation.
Keep N1 as a native capacity prerequisite and N3 as an observability dependency.
Record baseline/current binary identity; source HEAD alone is insufficient.

## Source SHA256 inventory

Paths below are relative to `/workdir/wepp-forest/src` and bind the inspected
bytes. Concurrent work may subsequently change the repository; rehash before
using these findings as execution provenance.

| File | SHA256 |
| --- | --- |
| `pmetcoef.for` | `a036b0e9e740483f971f714edc8904bea6ad44812673d77c4ef4ff993ff31447` |
| `ccrpet.inc` | `bf72eeb30e9396dda647f2cb2e5d27f65fbbebaaad4deb158936598cddbc464f` |
| `pmxcrp.inc` | `23d0127a56a6719fca1f7406b2b256e85d4211adc748ac7ebd9750ea9be80323` |
| `pntype.inc` | `da2b25dd7f8eaa71968f71919da6bc2c9abc13a9ea9498ec03a98f0a723e27e1` |
| `pntype_hill.inc` | `da2b25dd7f8eaa71968f71919da6bc2c9abc13a9ea9498ec03a98f0a723e27e1` |
| `infile.for` | `c49c4fd3ea624c87096dc0d13d1c64765304b979653dc1aaebaabe936bbae54a` |
| `evappm.for` | `f06caa44a40c2ab35ea118597821005aff5b5e4a9e2c9ec110c6ec5766e9f038` |
| `watbal.for` | `8711af6f0f8db921389a4a1d8738bc10e69203457b1e36fff704e1f86bf696de` |
| `watbal_hourly.for` | `e01316b307b5e66ee528e09862646a3a2fecaaa04795ff52a4f5d4776540fbd1` |
| `watbal_process_probe.f90` | `7607b5bf8e9166316dd18b469b59702c6f68abd22401f6fa035e02ecc41167d6` |
| `input.for` | `5f27a73cb9bc63fe20b60a08ef67a0adb86adc6eebb6fe184fd4636f68a0e455` |
| `main.for` | `36196c9535c43db1e6ae331e4012ebac947c3e27ece10fd169649b0bf3afeacd` |
| `scenhd.for` | `796e2a0c22680be4fd954cae05f204d2a6189b49298008149473401cf8b618be` |
| `contin.for` | `62114ead977361a75750ddea5a48dc0001d15d80a1856d9f8964a98dbbbe1523` |
