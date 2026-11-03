# MIPA-03 specialized consumer execution

Local undeployed revision 7 implements the requested reference-preserving 9005,
revegetation and RAP compatibility. Broad Python validation is complete across retained segments; final publication
reviews and HTTPS delivery verification pass. The evidence register binds terminal results.
Scientific authority remains Anurag's reference, with no claim of his review.

## Decision and implementation

The operator's “preserve reference. that is anurag's domain” is recorded in
[ADR-0134](../../../adrs/ADR-0134-specialized-revegetation-reference-port.md#decision-provenance).
The [durable contract](../../../schemas/specialized-revegetation-consumer-contract.md)
sections **Mode and input matrix**, **Soil 9005 records and dynamics**, **RAP
records, dates and producer reconciliation**, and **Reference vegetation and fire
semantics** specify the implemented behavior and deliberate exceptions.

Reviewed standalone checkpoints WEPPpy `c8f6ea854` and native `ee9e73f8b`, with
hash confirmations `60ed676f9`/`db697ba20`, preceded production changes. WEPPpy
implementation is `57a17b2dc`; native model port is `0d99afdfe`. Historical reference
snapshots retain their exact bytes through narrow attributes and renormalization
at `1ee6cd68c`. Build source is `e0abe0581f77c6f66917e90daf8f8f429e9315c8`;
later native commits add tests, including actual controller-emitted cover fixtures.

Reference model `2e5928702edd5526a119216bd6be5997729ec72e` is bound to historical
binary `2c79a5ecb392a6ed7f70102ff7b6caac888d0cb9df1ce303c93eb10d447740a0`.
The reference repository is untouched. Unknown historical compiler flags preclude
claiming whole historical executable equivalence; compiled source comparisons use
the same current compiler on both sides.

Native reads now bind all seven 9005 header fields and exactly one restrictive
record per OFE. Specialized ground-cover conductivity and first-two-layer feedback
follow the reference, including the additional 0.99 factor after saturation cap.
Six cover bands per OFE/year are read; the first four drive isolated reachable
specialized vegetation calculations, including growth and LAI,
initialization/cutting, residue and fire resets. Texture, litter and bare fields
are bound without invented dynamic consumers. Strict physical records, calendar,
capacity, finite values and direct REAL token parsing prevent silent misbinding.
Single-event RAP fails explicitly; routing consumes matched passes without RAP
being reapplied. Ordinary GROW, PMET and revision-6 FC/HK ownership are preserved.

Producer changes reconcile integer/hydrated string year keys and exact climate
calendar equality; retain existing fallback/transform rules; normalize emitted
Gregorian dates while preserving saved text; retire stale flags on mode changes;
and preserve visible old/failed flags, dates and cover files through archive and
browse/download. Atomic publication avoids linked-source truncation and retains
existing permissions. No new dependency or service was introduced.

## Exact final artifacts and reproducible gates

Private evidence root: `/wc1/holdouts/mipa-native-r7-20261103`.
Native authoring/evidence root: `docs/release-notes/wepp_261029/` in the selected
release checkout `/home/workdir/wepp-forest-release-20261009`.

| Artifact | SHA256 |
| --- | --- |
| `wepp_261029` | `4a9da3980d1a9249e566626c01de920de7dba5088ec25324dc1c6dd6eff8c825` |
| `wepp_261029_hill` | `210d48da09ff60707ba2404dd32af1f0a74e95437d2cb900c5408121141a1936` |
| Approved four-page PDF | `0cdd7c74ac7c2277a144e27d9a8053578eb6e63b6819b857bd45691b9fe69b3c` |

Build command: `PATH=/usr/bin:/bin:$PATH TARGET_TAG=261029 tools/build_wepp_dated_release.sh`,
then `make -C src prepare_watershed_includes`. Canonical default branch is
`wepp_260430_negmeltfix_comparator`; capacity includes remain unchanged.
Both roles use the system compiler/runtime and `/lib64/ld-linux-x86-64.so.2`.
Native and vendored sidecars are byte-identical; the retained metadata authoring
script reproduces them idempotently. Revision-6 binaries, sidecars and issued
report bytes are frozen in `baseline-r6/`.

- `PATH=/usr/bin:/bin:$PATH pytest`: **1,750 passed**, two warnings,
  `native-pytest-v2.log`; committed fixtures/generators, no private prerequisite.
- `tools/run_hillslope_watchlist.py --binary release/wepp_261029_hill`:
  **31/31**, `watchlist-v2.log`; both `tools/smoke_wepp_binary_host.sh` checks,
  `tools/check_ablation_artifact_policy.py` and runtime provenance pass.
- Compiled reference/candidate suites: **295 checks**, including hashes,
  properties and explicit failures, not 295 identical end-to-end comparisons.
  Reader module: **27 passed**, including two actual twelve-OFE writer cases added
  after full-suite collection. Ten mode tests include actual same-process MAIN
  hillslope-to-routing. Focused counts overlap and must not be added to 1,750.
- Eight final daily/hourly, transformed/observed, observer-off/on 16-year histories:
  **17,532 unique finite water rows per case**, all seven ordinary files identical
  within each observer pair. Four additional 9005/no-RAP histories pass.
- Six ordinary daily/hourly controls preserve all **84 before/after file hashes**
  against revision 6. Unsupported revision-6 9005 is not a numerical oracle.
- Vendored runner/output checks: **8 passed**, both post-vendor smokes and
  provenance pass. `application-pair-v1/receipt.json` proves actual installed
  9005/RAP hill-to-watershed execution with the matched final pair.
- Focused Python **75 passed**, real archive/restore evidence; browse/download
  regression **1 passed/18 deselected** uses existing route auth stubs and is not
  a live-auth claim. Stub gate and changed broad-exception enforcement pass.
  Code-quality observability is retained separately without modifying unrelated
  existing quality reports.

## Generated artifacts and consequences

Supported `prepare_fork_run` copied `/wc1/runs/mi/mipa-awake-20261102` to
`/wc1/runs/mi/mipa-rap-20261103`. Complete canonical preparation and execution use
service UID 1000, GID/groups 993, umask 022, actual configured modules/settings and
normal NFS. The fork selects final binaries, 9005 soils and deterministic synthetic
35-year RAP inputs; this is engineering acceptance data, not observed vegetation.
All **1,536 original-project file hashes remain unchanged**.

The actual `Wepp.prep_hillslopes(max_workers=4)` and `run_hillslopes(max_workers=4)`
workflow produces **576 declared outputs** for 72 hills/235 OFEs/1986–2020. All
72 logs confirm the exact final binary and enabled baseflow/UI/cover companions.
Six actual interchange datasets and `HillslopeWatbalReport` pass; area is
5,493,585.58 square meters. Raw water has **3,004,240 unique finite records**,
12,784 days per OFE. Water-year labels 1986–2021 are the established report
convention, not 36 simulated calendar years. Optional `InterceptionStorage` is
unemitted and explicitly all-null; all 22 emitted floating water columns are finite.
Independent QA also verifies all 25 p7 raw/parquet columns across 140,624 rows.

Three isolated diagnostic reruns cover 1, 11 and 2 OFEs, including IDs 2 and 10:
**14 soil headers, 84 band rows and 2,940 native REAL cover values** bind correctly.
All **24 ordinary outputs** match the normal configured NFS execution exactly.
Dense observer tracing exceeded 300 seconds on NFS; the retained successful v2
uses the same service identity, inputs and final binary on container-local disk.
That diagnostic mount is not represented as production-mount parity; the complete
normal workflow itself passed on NFS.

The reviewed PDF quantifies transformed-minus-observed cumulative per-element
runoff, ET, drainage, lateral flow and final soil storage in six mode/OFE rows.
For example, daily OFE 1 changes runoff by +17.683 mm, ET by -145.970 mm,
drainage by +38.824 mm, lateral flow by +89.720 mm and final liquid soil storage
by +0.020 mm. First growth divergence is July 15, 2005; water divergence starts
the following day. These are bounded diagnostic differences, not watershed outlet
fluxes or a full conservation result. At the first growth divergence, OFE-1 canopy is 0.225 observed versus
0.165 transformed.

## Retained failures and dispositions

The first native full gate had 1,748 passes and one setup error: the new independent
module inherited an include-copy prerequisite and broke a legitimate hill-only
isolated build. The explicit recipe at `e0abe0581` fixes the dependency; seven
affected tests and a complete clean rebuild/full gate pass. Binary bytes are
identical before/after that build-only correction.

The configured execution initially passed all 72 native runs but the harness
expected the prior scenario's 504 files. Canonical revegetation adds graphics,
so the corrected readback derives 576 expected files from actual run cards.
No unnecessary model rerun was substituted. Audit versions also retain the initial
omission of two graphics summary rows and a mislabeled water-column inventory;
corrected `artifact-audit-v3.json` and independent all-artifact QA agree.
The first added twelve-OFE reader harness parsed native activation text as floats;
selecting the VALUES rows fixes that test-only error and the full reader rerun passes.

The broad Python first segment stopped at an obsolete prep-service test double
missing `runs_dir`: **1 failed, 6,440 passed, 182 skipped**. The repaired fixture
supplies a real temporary run directory and verifies stale-flag retirement;
all **3 module tests pass**. Full collection followed by ordered continuation
starts at that failed node and retains every selected/deselected ID in
`python-continuation-selection.json`. This second segment stopped with **1 failed,
6,138 passed, 242 skipped, 6,622 deselected** when catalog comparison returned its
database-wide advisory-lock busy response. The entire catalog module then passed
**24 tests without code changes**, supporting transient contention rather than a
consumer regression. A third full-collection continuation starts at that failed
catalog node and records `python-continuation-selection-v3.json`. The terminal third segment passes **206 tests, 1 skipped, 13,001 deselected**;
there is no uninterrupted full-suite pass claim and overlapping counts are not summed.

## Residual limits and review disposition

Reference recurring anniversaries, differing canopy comparison/assignment bands,
shared crop root-depth mutation and logarithm/clamp ordering are intentional
compatibility exceptions under the operator's decision. No scientific retuning
or claim of universal heterogeneous correctness, field validity or full budget
closure is made. Historical Roads magnitude failures remain unresolved; prior
744/840 results are not fresh revision-7 results.

BIGOUT's unchanged F10.5 disturbance-age field emits asterisks at ages of 10,000
days or more. **734,107 cells**, including maximum summaries, are exclusively in
“Days since last disturbance” across 72 graphics files. Every other numeric
graphics field is finite. Source/formatter comparison proves inheritance from
both reference and r6. This is a disclosed serialization limit, not nonfinite model
state; changing the format is outside this port. Installed water interchange and
reports do not consume it. Do not claim all 576 files are entirely numeric.

Independent correctness, security, native/history/configured-artifact QA and
final PDF correctness/visual QA reviews pass with no unresolved source findings.
Their `mipa03_*review*.md`, `mipa03_implementation_security.md`,
`mipa03_configured_artifact_qa.md` and `mipa03_final_pdf_*.md` records preserve
findings and closure evidence. Security triage is high for file publication;
review covers linked-source protection, permissions, failed evidence and real
workflow identity. Reviews are independent AI engineering controls, not human
scientific approval.

Only the reviewed PDF and source-free manifest may be delivered through the
existing static report route. No legacy source, private project data or logs
are public attachments. No deployment, executable-default change, Windows build,
installed Rust promotion or bulk original-project regeneration was performed.

## Terminal broad regression accounting

The first segment passed 6,440 tests before the repaired fixture failure; the
second passed 6,138 before transient catalog lock contention; the final ordered
continuation passed 206 (one skipped, 13,001 deselected). The fixture module passed
3 and catalog module passed 24 in focused reruns. Selection receipts retain exact
node IDs. These are overlapping segmented results, not one uninterrupted full
suite invocation. Both encountered failures have explicit successful dispositions.

## Publication and source-control closeout

Independent [publication security](mipa03_publication_security.md) and
[publication QA](mipa03_publication_qa.md) approve the exact PDF and manifest.
The existing HTTPS route returns 200 with `application/pdf` and `application/json`;
downloaded SHA256 values equal the approved bytes. All twelve earlier public
attachments remain unchanged. The detached delivery receipt is retained in native
`docs/release-notes/wepp_261029/evidence/delivery-receipt-r7.json` and the private
evidence root. Public manifest SHA256 is
`7c7d80526573e08148590a5196dbd0ff4990d55426d0f16c25a5582e203ab1ac`.

Native final release/evidence commit **`547b9e7eb`** is pushed to verified default
branch `wepp_260430_negmeltfix_comparator`. WEPPpy production implementation is
`57a17b2dc`; follow-up fixture/browse coverage is `5bffbd430`. The closing WEPPpy
commit contains matched binaries/sidecars, approved public attachments, review
records, executable evidence helpers and completed package documents. WEPPpy
push is not required by its repository instructions; no deployment occurred.

SOIL-02/COVER-01 are closed for this selected reference-preserving support matrix.
All in-scope package acceptance is complete with the explicit residual dispositions
above. The completed plan and tracker preserve earlier failed/HOLD stages as
history. The reference checkout remains clean. Unrelated working-tree changes
were preserved; the known test-generated management JSON delta was retained as
`test-generated-management.diff` before restoring that test artifact alone.

One test-ergonomics issue remains outside this repair: unique PostgreSQL schemas
do not isolate database-wide advisory locks. A dedicated integration-test database
would prevent this observed catalog contention without weakening production locks.
