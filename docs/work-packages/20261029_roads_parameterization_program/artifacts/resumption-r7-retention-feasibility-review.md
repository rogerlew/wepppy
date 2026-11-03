# Revision-7 optional-retention feasibility review

Date: 2026-11-03 UTC. Independent read-only review by `mipa_contract_scope`.
Scope: source acquisition, cache association, input companions and experiment
feasibility. No model runs, native builds, source/default edits or withheld model
outcomes were used. Only this additive review artifact was written.

## Decision

A bounded source-associated default-versus-optional retention experiment is
scientifically justified, with **1718494 as the primary failure target** and
2711184 as an opposite-direction control. The retained source cache supports a
specific deeper-retention hypothesis for 1718494; its acquisition association is
not sufficient for an opted-in build. A fresh bounded seven-development-material
SDA acquisition using the existing owned builder is the concrete next preparation
step, followed by a paired input-only gate. No fetch or build was performed here.

The optional policy is materially different from the rejected conductivity,
density/porosity and roughness experiments: it changes only eligible source FC/WP
preparation at unchanged density under ADR-0132, without a new multiplier or POR
law. Existing studies do not reject this exact hypothesis, and do not establish
Roads benefit. The old Roads injection helper also lacks the required companion
propagation; prove that preparation before native execution. This review supports
bounded experiment feasibility, not default adoption or release acceptance.

## Correct case identities

The retained `engine-seeds-v3/declaration.json`, read for case metadata only,
maps `small_gravel_less_runon` and `small_gravel_dry_legacy` to **1718494**,
Flagstaff and Denver respectively. The historical
[buffer-process findings](buffer-process-interpretation-r4/findings.md) name these
B2/B3. Material 2711184 supplies B5 (site/gravel underprediction), B6 (site/paved
underprediction) and B9 (Denver/rutted underprediction). It must not be presented
as the B2/B3 small-failure material.

The current panel declaration contains exactly seven development materials:
1718465, 1718494, 1718510, 1856573, 2711184, 2711250 and 53949. The six withheld
IDs 1718472, 53975, 1718476, 665770, 2711196 and 658566 remain excluded. No native
outputs for withheld IDs were opened or used for selection.

## Primary target: 1718494 source feasibility

The retained `/wc1/runs/ad/addicted-reservist/soils/` cache is available with its
original WAL and human-readable metadata. The main database is 4096 bytes, SHA256
`352a9bb23c329c5a9bf235baf56917358b5b64b03f1a11d261fadae9c3cdb721`;
the WAL is 280192 bytes, SHA256
`e9e31f4874bab3e3fc7b1ee3e855cb105beba6995f791766ffe26f7467c31031`.
This review reconstructed the 68 committed WAL frames in memory, verified header
and frame checksums, and obtained SQLite integrity `ok` for 23 committed pages.
Disk main/WAL bytes were unchanged. An initial in-memory open required changing
only the reconstructed image's journal flags; no checkpoint or source write ran.

The cache, build log and source soil agree on Fruitland component 26348952,
100% component share, seven selected horizons, original density 1.5 g/cm³ and
source FC/WP branches. All seven horizons pass the current inverse screen from
the original cached fields. The first six have zero prepared rock mass and are
exact policy no-ops. The seventh provides the actual treatment contrast:

| Field | Retained original source / derived value |
| --- | --- |
| Horizon | 2C3, chkey 78593868 |
| Original depths | 99–152 cm; writer extends the terminal row to 1600 mm |
| Density | 1.5 g/cm³ |
| `fraggt10_r` / `frag3to10_r` / `sieveno10_r` | 0 / 0 / 87.5 |
| Prepared rock mass | 12.5%; distinct from cached `chfrags.fragvol_r = 3` |
| Original FC / WP | 16.2% / 7.2% |
| Default FC / WP | 0.185142857 / 0.082285714 |
| Optional FC / WP | 0.175099730 / 0.077822102 |
| Inverse fine-earth share / screen porosity | 0.925187032 / 0.433962264 |

The current panel's input readback independently retains this 990–1600 mm row
in all three roles. Its nominal input-integral contrast is 6.126 mm FC and
2.723 mm WP over 610 mm, before native transformations. Upper-layer CPM=1 does not
rule out a deeper effect. Conversely, copying P04's 700 mm clipping would remove
this sole changed horizon and make the 1718494 treatment a no-op. Preserve the
frozen 1600 mm profile and use the admitted unclipped staging path.

**Acquisition association is the actual unresolved source gate.** The cache
metadata identifies SDA, retrieval implementation and 2026-09-11 generation time,
but does not retain the originating complete source queries/responses and hashes.
Other source-preparation receipts in that run identify only component/horizon
geometry for a debris-flow thickness workflow; their SDA request concerns survey
catalog metadata and does not bind these original retention fields. They do not
repair this gap. Rounded native soil values or a new hash of the old cache cannot
be substituted for an acquisition receipt.

A fresh development-only acquisition of the seven declared materials is justified:
it closes this gap and supplies same-cohort controls without touching withheld
results. Retain all five source-table families, exact queries, raw responses,
timestamps, completeness/error status and hashes; bind them to the actual builder
cache schema, ordered rows, missing-parent records and selected source fields as
P01/P04 did. Require success for the complete requested set. New source IDs or
values are source-vintage changes, not evidence for retention efficacy. Rebuild
both default and optional arms from this one cohort and separately account for
fresh-default versus frozen-U12 drift. Fresh acquisition is recommended here,
not performed or retroactively attributed to the old cache.

## Source and cache evidence

Retained root: `out/rock-water-development-20261101/`.
The operative acquisition is `P01-source-tables-v2`, not the nonexistent v1
destination named by the older preparation declaration. Its receipt hash is
`512aaca1984ccbaf238a42d92328b848c54e54e592c5ff48b50773f2c27c96bc`.
The five sequential SDA responses were acquired on 2026-11-02; they are a retained
consistent cohort, not an atomic database snapshot or a new live acquisition.

This review independently rehashed every retained XML response and SQL query
against the receipt, compared XML row values/nulls to the normalized JSON tables,
and compared ordered extracted rows with the finalized production SQLite schema.
The first-key auxiliary reductions match existing extraction behavior:

| Table | Raw rows | Cached rows | Missing-parent cache records |
| --- | ---: | ---: | ---: |
| component | 16 | 16 | 0 |
| chorizon | 91 | 91 | 0 |
| chfrags | 172 | 62 | 29 |
| chtexturegrp | 196 | 91 | 0 |
| corestrictions | 15 | 15 | 1 |

All ordered value and missing-parent comparisons pass. The finalized cache is
`P04-project-experiment-v5/profiles/collection.sqlite`, 69632 bytes, SHA256
`2f74c36460cc58520400a619c68097b23e77026144275ab89a3b8306d3e9f162`.
It has no WAL/SHM files and was opened immutable/read-only. Initial verification
attempts exposed differences between XML empty elements and omitted values, and
SQLite's permissive numeric/text affinity; the final comparison preserves those
semantics instead of coercing missing values to zero.

The source cohort contains only 67141, 67225, 2711184, 2711195, 2711198 and 2711253.
Material 2711184 selects Murtip component 28366541 at 45%; all seven source-decision
records join exact cached original fields. The five mineral decisions below are
eligible, Oi 85179894 is excluded before emission, and Cr 85179900 has missing
original density/FC/WP and remains the unchanged Rosetta fallback.

| Horizon | Depth mm | RFG mass % | Density g/cm³ | Original FC/WP % | Default FC/WP | Optional FC/WP |
| --- | ---: | ---: | ---: | --- | --- | --- |
| A1 /85179895 | 180 | 15 | 0.78 | 26.7 /12.1 | .3141 /.1424 | .2809 /.1273 |
| A2 /85179896 | 360 | 5 | 0.78 | 27.2 /11.9 | .2863 /.1253 | .2762 /.1208 |
| Bw1 /85179897 | 610 | 5 | 0.80 | 27.2 /12.0 | .2863 /.1263 | .2763 /.1219 |
| Bw2 /85179898 | 1090 | 15 | 0.80 | 23.7 /8.7 | .2788 /.1024 | .2496 /.0916 |
| BC /85179899 | 1270 | 30 | 0.80 | 20.5 /6.6 | .2929 /.0943 | .2315 /.0745 |

The 200 mm split repeats A2 with preserved lineage. At nominal 700 mm clipping,
serialized default-minus-optional depth integrals are 12.922 mm FC, 5.600 mm WP and
7.322 mm FC-minus-WP. These are input arithmetic, not native UL, available storage,
drainage, initial absolute water or predicted sediment changes. Native remapping,
density adjustment, CPM and guards can change or suppress their interpretation.
The earlier observed CPM=1 at selected consumers cannot establish zero RFG in the
source profile; the actual emitted profile has 15%, 5% and deeper nonzero fragments.

The live original source `/wc1/runs/cl/clogging-starch/soils/2711184.sol` hashes to
`be583a9f9b43fe23800cdd0d7fbff9d5b29095ed8314b0d6178a77f41baf7cdd`.
It uses earlier component 27422944 and horizon 81898230 onward. Its first five
mineral FC/WP/RFG values agree numerically with the corresponding default values
above, but its deep fallback differs: FC/WP .1880/.0900 versus P04 .1958/.0815,
and conductivity 59.8734 versus 21.3038. It is not a byte-identical source vintage.
Build both experiment arms from the same bound cache; separately report any
fresh-default departure from frozen U12 instead of attributing it to retention.

## Supported path and preparation blocker

Using the current canonical `load_source_companion` through `wctl exec weppcloud`,
this review validated four retained artifacts under the known project root
`P04-installed-controller-v2/p04-installed-v2-candidate`:

| Artifact | Verified companion schema | Soil SHA256 |
| --- | --- | --- |
| `soils/2711184.sol` | source-v3 | `79806af16f2d15ded18f7f34e3b6ee1a0bcd7e33c04762cdb8e13197d64185b6` |
| `soils/2711184-loam-forest.sol` | treatment-v3 | `e4ef97ecbeed8a068605a5ee80deab541a7de3160cb63a89d114a0286070d79a` |
| `soils/hill_111.mofe.sol` | stack-v3, three OFEs | `d94b945a2c0911b535c6d50e49a314e00e4837f06037c27e48a97fc0b172ef2d` |
| `wepp/runs/p1.sol` | stage-v3, three OFEs | `65b2972aab5941d60d09ec466d0e078511557ce4dcda8a680e19b448ccb8e709` |

Forest treatment preserves source depth, density, FC, WP and RFG. The actual
stage records saturation .75, kslast .01, clipping enabled at 700 mm. Source and
parent hashes and identity joins validate recursively, rather than only trusting
receipt status. This is retained installed-pipeline evidence, not a fresh build.

Current optional treatment requires a 7778 single-source profile, 9002 treatment,
no numeric density override and no Rosetta recomputation flag. Stack inputs must
all be marked single-OFE treatment companions; mixed default/optional stacks and
uploads are unsupported. Staging accepts the supported stack path, no minimum
depth extension, and only 700 mm when clipping is enabled. All outputs require fresh
destinations. Existing markers/companions cannot be dropped or rewritten to bypass
these checks.

The old [builder bridge](builder_bridge.py) directly calls `to_over9000().write`,
then rewrites a composed soil for U12 road erosion values and upper-horizon K caps.
It does not construct the optional treatment/stack/stage companion chain. The
production Roads paths also remain legacy-template based. Neither path is proved
compatible by the P04 forest-chain result. Before running, use existing supported
workers/writers to express each frozen Roads role and carry the allowed hydraulic
conditioning into its actual companion. Validate source-to-role-to-stack-to-final
values without new density/geometry changes. If a required role operation cannot
be expressed by the admitted path, stop that lane and scope a reviewed extension;
do not silently call the resulting surrogate full-project validation.

## Smallest informative protocol

1. Acquire and freeze one seven-development-material source cohort through the
   existing owned SSURGO path, with the complete association evidence above.
   Freeze exact r7 executable hashes and a fresh disposable root. Build default
   and optional source profiles with the same installed builder, full requested
   success, unchanged source selection/fallback and original-source eligibility
   readback. Report each fresh-default departure from frozen U12 separately.
2. Perform a preparation-only gate for each frozen road/fill/buffer role, including
   U12 erosion values and upper-layer K conditioning. Preserve identical density,
   geometry, 200 mm support, saturation, restriction, management, climate and
   sidecars in both arms. Preserve full frozen depth: do not import P04's 700 mm
   clipping. Only eligible FC/WP and necessary provenance may differ. Require
   canonical source/treatment/stack/stage companions and independent final-input
   readback. Keep all roles on the same policy; mixed-policy stacking is outside
   the admitted API. If actual U12 conditioning cannot be represented through
   the supported companion path, stop before native calls and review that precise
   extension, without dropping markers or forging provenance.
3. Predeclare four paired full-period cases: B2 and B3 (1718494 small failures),
   B4 (site/1718465/outunrut/gravel/high passing same-signature control), and B5
   (site/2711184/outunrut/gravel/high opposite-direction control). Use the exact
   retained case keys. This is eight generated runs after the preparation gate,
   not an initial 840-case sweep. If fresh source preparation changes a case's
   non-retention behavior, report its new baseline explicitly and do not label
   the policy result a clean recovery of frozen U12.
4. Reuse exact-r7 legacy anchors only where input/executable hashes match; execute
   both freshly generated arms. Verify consumed deeper retention, per-OFE FC/HK,
   native remapping/guards and relevant drainage/ET branches with existing
   observations. No observer source/build modification is authorized by this
   review. If observations cannot establish that the changed deeper row reaches
   the relevant consumer, retain the evidence gap rather than infer from inputs.
5. Retain full-period physical/calendar/strict particle checks and original
   magnitude classifications, plus annual runoff, surface return, deep/lateral
   drainage, storage, ET and sediment by OFE and outlet. Stop/reject on physical
   failure, absent consumed retention change, undeclared input changes or harm
   to opposite/passing controls. A null result ends this source-policy lane for
   the tested configuration; it does not justify a new multiplier. A defensible
   response permits a declared wider development panel only. Existing withheld,
   UI, default-promotion and acceptance gates remain separate.

## What prior studies do and do not settle

The [physical-capacity review](buffer-capacity-physical-review-r4/findings.md)
rejects dry-offset fitting and an immediate daily UL refresh as demonstrated
remedies, and its [next-study boundary](buffer-capacity-physical-review-r4/next-study.md)
rejects a global POR multiplier. Neither is the ADR-0132 producer inverse.
The prior hydraulic factorial and road-pore experiment changed K and/or density
with scaled retention; they do not isolate this same-source, unchanged-density
policy. ADR-0127 reports a bounded prototype response with essentially unchanged
initial absolute water, which warns against interpreting reduced prepared FC as
increased initial pore storage. P03/P04 admit only their bounded source/consumer
path, not Roads magnitude or general physical validity.

The updated r7 full-panel counts supplied for this review remain 713/766 meaningful
and 31/74 small, with no recoveries/regressions despite 218 changed annual quantities.
They motivate a distinct mechanism but do not favor this policy by themselves.
No criteria, withheld split, default adoption or human UI gate changes follow from
this feasibility verdict. The active program remains unaccepted until its existing
[acceptance](../acceptance.md) and [autonomy](../autonomy.md) obligations are met.
