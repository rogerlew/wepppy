# Water and PASS Output Documentation Audit

Date: 2026-10-20. WEPPpy source revision: `1ecf04735`.
Scope: scientific meaning, field reference, user discovery and run-specific
interpretation of water/PASS outputs after ADR-0099. This is an audit and
proposal, not implementation or production deployment acceptance.

## Assessment

We provide a useful report chooser, output-file inventory, generated schema and
preview tables, and detailed developer contracts. We do not yet provide a
connected user-facing explanation of the spatial and temporal basis of water
and PASS values. Advanced users can find files without finding the rules needed
to combine them correctly. Renaming the existing link helps discovery but cannot
supply the missing scientific guidance.

The central lesson must be visible before a user opens a spreadsheet: raw water
rows are OFE observations; not all depths use the row's local area; an internal
transfer is not another hillslope outlet; physical WAT runoff and thresholded
PASS delivery are different products. TotalWatSed is a derived hillslope-summed
watershed table, not automatically routed channel/outlet discharge.

## Evidence and audit limits

Inspected current repository docs, authoritative water contracts/ADR, Usersum
manifest/navigation/search code, Results/report templates, the generated README
builder, native/Python metadata, and an existing run's generated README at
`/wc1/runs/in/incorporate-cerebrum/wepp/output/interchange/README.md`.

Built an in-memory Usersum document index from current manifest and source files
using `load_and_validate_contracts` and `build_generated_index`; no vendor sync,
index write, PostgreSQL synchronization or source mutation occurred. The dirty
`routes/usersum/generated/docs_index.json` was neither read nor modified.
Search counts below are literal content coverage in that fresh manifest-backed
index, not a production search-ranking/browser test. Live deployed docs may
lag these sources; production user click behavior was not measured.

## What exists and how users reach it

| Surface | What it provides | Discovery and shortcoming |
| --- | --- | --- |
| [WEPP Run Results](../../wepppy/weppcloud/routes/usersum/weppcloud/wepp-run-results.md) | Report chooser, purpose/cautions, year exclusion guidance | Direct help link in Results and Usersum Modeling Basics and Tuning. Good entry point; does not explain physical WAT versus PASS runoff or OFE area bases |
| [WEPP Interchange Outputs](../../wepppy/weppcloud/routes/usersum/weppcloud/wepp-interchange.md) | Parquet explanation, file inventory, scope paths, related access guide | Linked from Results guidance; nested under Technical Reference > Project Files and Maps. H.wat described generally as hillslope results, without one-row-per-OFE/day warning or formulas |
| Run `wepp/output/interchange/README.md` | Existing datasets, Arrow names/types/units/descriptions, three-row preview and interchange version | Direct Results link only when README exists; opens through file-browser Markdown rendering, not Usersum. It is not indexed as general user documentation |
| [Interchange developer README](../../wepppy/wepp/interchange/README.md) | Architecture, APIs, errors, schema versions, final physical-water-loader note | Not registered in Usersum manifest; implementation material dominates; no complete water/PASS interpretation reference |
| [TotalWatSed guide](../../wepppy/wepp/interchange/README.totalwatsed3.md) | Formula descriptions, volumes/depths, named runoff, lateral selection, stocks, diagnostics | Not registered in Usersum; linked from developer README. Useful material, but mixed with native implementation and inconsistent historical references |
| [Water aggregation contract](../schemas/hillslope-water-aggregation-contract.md), [ADR-0099](../adrs/ADR-0099-mofe-physical-water-consumers.md) | Most complete current field matrix, physical/PASS distinction, geometry, nulls, provenance and limits | Not registered in Usersum. Linked indirectly by indexed Features Export/Ash material; generic source rendering may allow access, but this is not ordinary search discovery |
| [MOFE closure audit contract](hillslope_mofe_water_balance_contract.md) | OFE budgets, transfers, storage, missing interception terms and residual cautions | Developer/tool-oriented, absolute source paths and old line references; QOFE-based equations need explicit version applicability |
| [Windows WEPP User Summary 2024](../../wepppy/weppcloud/routes/usersum/weppcloud/wepp-usersum-2024.md) | General model/run/output background, hillslope-to-watershed pass concept | Registered Technical Reference; not a current WEPPcloud field dictionary |
| [Vendored modernization brief](../../wepppy/weppcloud/routes/usersum/vendor/wepp-forest/docs/20260504-stakeholder-watbalance.md) | Historical architecture/lineage discussion | Registered at user role under Technical Reference. Only indexed QOFE hit, but not a QOFE explanation |
| [Dataset access guide](../../wepppy/weppcloud/routes/usersum/weppcloud/profile-jwt-dataset-access-python-r.md) | Authenticated Python/R download and Parquet access | Linked from inventory; explains obtaining bytes, not hydrologic calculations |
| Average annual and yearly report pages | Tables, units, CSV downloads, yearly exclusions | No direct water interpretation guide. Average annual description says aggregated .wat.dat totals; yearly says interchange, hiding the source distinction |
| Indexed Ash / Features Export module READMEs | New physical-WAT/PASS and aggregation notes for their own workflows | Relevant facts exist but users must approach via a different task/module; not a primary water/PASS guide |

The Results helper says "Each link respects the active run scope," while the
baseline interchange README href and existence check use `wepp/output/...`.
Roads has separate results/resource construction. A future guide link must be
checked in each real scope, not assumed correct by reusing the baseline URL.
This audit does not claim an observed Roads misrouting bug.

## Usersum discoverability evidence

The current manifest yields 68 active documents at `min_role: user`.
Literal case-insensitive content/title/heading matches are:

| Search term | Matching documents | Interpretation |
| --- | ---: | --- |
| `latqcc` | 0 | No indexed definition of the lateral-flow field Ayush needs |
| `QOFE` | 1 | Historical modernization brief mentions inconsistency; no definition |
| `SUBEVENT` | 2 | Ag Field Mod and WEPP-Forest Change Log, not a primary PASS guide |
| `H.wat` | 5 | Ash, Features Export, changelog, inventory, directory guide |
| `H.pass` | 3 | Ash, Features Export, inventory |
| `physical runoff` | 0 | No exact-phrase match; this does not mean there is no related wording |
| `water balance` | 8 | Mainly report/model/calibration/general guidance |

Search uses the manifest-backed catalog, with role filtering and PostgreSQL
search or an in-memory title/heading/body scorer. Repository Markdown files are
not automatically included. The four detailed documents (water contract,
ADR-0099, developer interchange README, TotalWatSed README) are absent from the
manifest. A `/usersum/src/...` link may render them, depending on manifest-only
configuration, but does not make them discoverable in search/navigation.

Current plausible user path is Results > WEPP Run Results guidance > WEPP
Interchange Outputs. That path reaches an inventory, not an accounting tutorial.
The direct Results > Interchange README path reaches schemas and preview rows.
Neither route answers "why do my lower-OFE water balance and PASS disagree?"
without additional technical investigation.

## Confirmed documentation discrepancies

| ID / priority | Finding | Why it matters / correction |
| --- | --- | --- |
| DOC-01 / high | H.wat metadata says Q is "Daily runoff over eff length", QOFE is "Daily runoff scaled to single OFE", and Area is "Area that depths apply over" | Those labels do not explain current cumulative-length Q, version-sensitive QOFE, or local versus cumulative area. Correct native and Python metadata together; include physical basis, not just units |
| DOC-02 / high | Usersum inventory describes H.wat as hillslope results and suggests reviewing infiltration, without explaining OFE grain or that infiltration is not a direct named field in the standard table | Add row grain and supported quantities; avoid implying one row per hill/day or a direct infiltration column |
| DOC-03 / high | Report pages and report chooser do not distinguish physical WAT runoff from PASS-based yearly/daily watershed runoff | Correct values can disagree legitimately. Put a short source/basis statement on each report and link a comparison guide |
| DOC-04 / high | PASS schema calls runoff/sbrunf merely depth and runvol/sbrunv merely volume | Explain internal/effective runoff basis, local lateral basis, routed volume authority and EVENT/SUBEVENT/NO EVENT gating. A zero PASS surface value does not prove zero physical runoff |
| DOC-05 / high | No indexed user-facing explanation of MOFE local loss weighting, terminal lateral conversion and internal transfers | Provide a worked two-OFE example and explicit safe/unsafe aggregations before exposing formulas as reusable recipes |
| DOC-06 / medium | TotalWatSed README links to `README.md#hwat-multi-ofe-schema-semantics`, but that heading is absent | Repair link to a maintained definition. Its absolute `/workdir/wepp-forest/...` reference also cannot serve a normal browser reader |
| DOC-07 / medium | Older TotalWatSed prose calls PASS runvol canonical without clearly qualifying thresholded delivery, and describes old QOFE inflation as OFE-count-scaled | Later paragraph distinguishes physical/PASS. Consolidate the explanation; historical scaling depends on geometry/producer and must not be generalized from equal-area OFEs |
| DOC-08 / medium | Closure developer contract presents QOFE-based local/outlet equations while the newer water contract calls QOFE version-sensitive | Qualify equations by supported producer semantics and show current valid alternatives. Do not teach an unconditional zero-residual expectation |
| DOC-09 / medium | Current water/output-scope/cache contracts still say implementation conformance is pending despite the completed package | Update current status with exact validated release and limitations; keep production rollout distinct. Closed package artifacts remain historical |
| DOC-10 / medium | Generated README advertises an interchange version but not the distinctions among model lineage, raw schema and consumer aggregation version | Users cannot infer corrected summaries or producer normalization from one version label. Explain those separately and show known/unknown lineage honestly |
| DOC-11 / medium | Metadata for IDs/dates is sparse; PASS gwbfv/gwdsv units are absent in inspected schema/README | Supply verified units and ID/date definitions. Do not guess groundwater units from the column name |
| DOC-12 / medium | Vendor configuration syncs the baseline forest repository, whereas a same-named document in the other forest checkout makes different architecture claims | Name lineage/date and link current output semantics separately. Do not overwrite synced vendor artifacts or imply one checkout describes every run |

DOC-01/DOC-11 metadata is visible in both the Python schema facades and native
`wepp_interchange/src/schema.rs`, and in the inspected existing run README.
Regenerating README alone reads persisted Arrow metadata; it cannot fix old
Parquet metadata or prove old numerical artifacts current. Version-aware prose
and an explicit old-artifact policy are needed.

## What advanced users should receive

### 1. A user guide: Understanding Water Balance and Runoff

Lead with which question each product answers. State whether a quantity is a
local OFE depth, physical hillslope outlet depth, thresholded hillslope export,
hillslope-summed watershed depth, or routed channel/watershed outlet quantity.
Include a simple hillslope diagram showing internal surface/lateral transfers
and one outlet. Explain that hourly internal calculation can still emit daily
water rows.

Show a product comparison: raw H*.wat.dat/H.wat.parquet, raw hillslope PASS /
H.pass.parquet, physical daily collapse/report/export, TotalWatSed, watershed
PASS and channel/outlet reports. Explain that Parquet conversion normally
preserves raw rows; the downstream calculation creates a hillslope summary.

Teach field-specific daily reduction, then temporal aggregation. For local
fluxes use sum(depth*area)/sum(area). For lateral outflow use terminal local
depth*terminal area/full hillslope area. Physical terminal Q is already a
hillslope depth for the supported producer geometry; do not multiply it by the
terminal area fraction again. For routed delivery use PASS runvol; explain why
it need not equal physical WAT volume on subthreshold days.

Include a two-OFE worked example with 250/750 m2, local ET2/6 yielding ET5 mm,
terminal lateral6 yielding hillslope lateral4.5 mm, and terminal physical Q8
remaining Q8 mm. Convert each to m3, and separately show incoming water in the
lower OFE budget. Add the workbook's actual lower-area fraction 0.39869388 as an
example of why rounded 0.4 is not exact. No example should imply that small
annual residual proves complete closure.

Explain storage versus flux, soil liquid/frozen totals, snow and interception,
initial/final storage, and why P+Irr versus RM depends on whether snow storage is
in the budget. Explain water years/calendar years, model calendars, warm-up,
selected years and the actual averaging divisor used by each report. Clarify
that Dp is not automatically same-day baseflow or measured outlet discharge.

### 2. A reference: Water and PASS Variables

For every exposed field, provide source name, meaning, units, row grain,
spatial denominator, sign/direction, time support, stock/flux/diagnostic class,
valid aggregation and version caveats. Include OFE ordering, native wepp_id,
Topaz mapping, sim_day_index, julian/calendar/water_year, stationary geometry,
missing values versus genuine zeros, duplicate records and partial topology.

Group WAT fields into inputs, local losses, surface routing, lateral routing,
storage and diagnostics. Cover Q/QOFE explicitly. Group PASS fields into event
kind, surface/lateral/tile volumes and depths, timing/peak metrics, sediment,
and groundwater terms. Describe raw headers/record variants and how interchange
normalizes EVENT, SUBEVENT and NO EVENT records; distinguish absent records from
records whose nonapplicable values are zero. Include watershed PASS layout as a
separate product, not a synonym for hillslope PASS.

Do not use the interchangeable word "runoff" without a scope and basis.
The EVENT threshold is tested against internal runoff, not a simple printed
WAT Q >= 1 mm rule. No recipe should reconstruct event eligibility from printed
Q alone. Verify variable-width/custom and contour applicability before claiming
that every formula is universally supported.

### 3. An analysis walkthrough and run-specific reference

Provide an Excel example and a Python or DuckDB example using the same known
fixture. Select a native hill, inspect full topology, select dates, compute
volumes and depths, and compare physical WAT with PASS and TotalWatSed. Show
what a legitimate threshold difference looks like, and what double counting
looks like. Preserve each native outlet before combining mapped features.

Explain exporting to CSV, retaining ID/date precision and metadata/units, and
accessing Parquet. Link the existing authenticated access guide rather than
repeating credential instructions. Show how to report a discrepancy with run ID,
scope, date, OFE IDs/areas, model/version information and source columns.

The generated run reference should remain a bounded schema/preview artifact,
but add a plain-language introduction, row grain, warning for version-sensitive
fields, exact scope/path, available provenance and links to the maintained
interpretation/reference guide. Keep raw-schema version separate from numerical
consumer version and model version. Do not imply every missing lineage can be
recovered from data values.

## Proposed discovery and interface

Replace the current link text with **Output files, columns, and sample data**.
Add a short description: "See which result files this run contains, their
variables and units, and a preview of the data." Keep its run-specific target.
Calling it a water-balance guide would overpromise what the current target does.

Add **Understanding water balance and runoff** as the stable interpretation link
beside the Water Balance Reports group. It should be available even when a run
has no generated README. The technical term "interchange" can appear in the
page explanation rather than being the main navigation cue.

From average annual report, yearly report, hydrograph, event P/Q/ET layer help
and H.wat/H.pass export selections, link directly to the relevant section.
Suggested report wording: "Hillslope runoff includes physical WAT runoff;
watershed delivery reports use PASS and can omit subthreshold surface export."
Tailor the short sentence to the actual report, and disclose year selection.

In Usersum, register the guide/reference with user visibility and searchable
headings containing water balance, runoff, lateral flow, ET, deep percolation,
OFE/MOFE, water file, pass file, Q, QOFE, latqcc, runvol and sbrunv. Link from
Run Results, Interchange Outputs, model guidance and relevant module docs.
Place the reference under Technical Reference > Project Files and Maps; an
interpretation guide near results would be natural. Adding items to Modeling
Basics and Tuning, Start Here, or Data/Sources/Policy requires explicit operator
permission per Usersum AGENTS; this audit makes no navigation edits.

Do not rely on a direct `/usersum/src/` URL or an unregistered README for search
visibility. Rebuild the approved manifest/index and validate role-aware search
only during implementation. Do not auto-sync unrelated vendor content.

## Recommended sequence and acceptance

First resolve the high-priority semantic text/metadata discrepancies against
ADR-0099 and current producer contracts. Create the user guide and reference,
then wire discovery and concise report context. Repair stale links/status and
version annotations in the same change. Keep scientific equations in current
canonical contracts; user prose/examples should be tested against them rather
than becoming another competing formula source.

Maintain ownership across layers: producer scientific definitions and native
metadata; WEPPpy consumer contracts and Python facade parity; one Usersum guide
and reference; generated run-specific metadata/preview. A metadata correction
requires paired native/Python review, not an isolated README edit.

Acceptance should demonstrate, as an ordinary user:

1. From Results, reach both interpretation and run-specific columns without
   knowing the word interchange or having developer access.
2. Search QOFE, latqcc, pass file and water balance; reach definitions and worked
   examples near the top, with correct user-role visibility.
3. Identify row grain, correct area, physical versus PASS basis and year selection
   for a downloaded value, and explain an expected WAT/PASS difference.
4. Reproduce the two-OFE example in a spreadsheet and code without summing
   internal routing boundaries or applying terminal-area scaling twice.
5. Follow all guide/reference links in Usersum and the file browser, including
   source-link rewriting, missing README, Roads/AgFields and historical artifacts.
6. Confirm native/Python metadata parity and inspect a newly generated README;
   preserve the small schema-plus-three-row generation performance contract.

Run docs lint/link checks, Usersum contract/index/search tests, relevant Results
and report-template tests, and an actual browser readback at user role. A
successful source lint is not proof of live search ranking or user comprehension.

## Audit outcome

The documentation substrate exists; the missing piece is a coherent user-facing
scientific explanation and entry points to it. No new documentation platform is
needed. This audit adds only this report. It does not modify runtime behavior,
Usersum navigation/index, vendor snapshots, run outputs or closed work packages.
