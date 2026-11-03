# MIPA-03 independent configured artifact QA

Disposition: **PASS for the configured execution and artifact claims below**.
This is not final PDF/publication approval. No production source, native binary,
configured input or reference repository was modified by this QA.

## Bound execution and readback

Reviewed the final configured acceptance fork at
`/wc1/runs/mi/mipa-rap-20261103`, with receipts under
`/wc1/holdouts/mipa-native-r7-20261103/configured-execution-v1` and preparation
under `configured-project`. The full run used 72 hillslopes, 235 OFEs, all 35
calendar years 1986–2020, deterministic synthetic cover and version 9005 soils.
This is synthetic acceptance evidence, not observed site vegetation validation.

Independent checks passed:

- Every declared input hash, all 72 run cards and native log hashes. Each log
  confirms the final binary, UI/baseflow companions, its own cover basename and
  successful native completion. Run cards independently declare exactly eight
  outputs each, including graphics; all 576 generated output hashes match.
- Recorded service UID 1000, GID 993, supplementary groups, settings and normal
  NFS run mount agree between preparation/service and execution contexts. The
  service context records umask 022. Actual installed pair bytes match the
  recorded final identities: watershed `4a9da3980d1a9249e566626c01de920de7dba5088ec25324dc1c6dd6eff8c825`
  and hillslope `210d48da09ff60707ba2404dd32af1f0a74e95437d2cb900c5408121141a1936`.
- All 72 raw water files were independently parsed. Every native numeric cell is
  finite; all 3,004,240 records have unique OFE/year/day keys and exactly the
  full expected calendar for each of the 235 OFEs.
- All six interchange parquet hashes and row counts agree with the receipt.
  The water dataset independently has the correct 235 hill/OFE identities,
  12,784 distinct daily records per OFE and the complete date range. Its 22
  native floating-point fields are nonnull and finite. Optional
  `InterceptionStorage` is absent from this native writer and explicitly null
  for all records; it is not counted among the finite native fields.
- A discriminating exact raw-to-parquet comparison covers all 25 native columns
  and 140,624 records on the 11-OFE hill p7, explicitly including OFEs 2 and 10.
  All cells agree exactly, without a tolerance adjustment.
- Day-one areas independently reproduce 72 report hills and 5,493,585.58 m².
  Water-year labels 1986–2021 agree with the parquet data; they do not add a
  simulated calendar year.
- The original source project's complete 1,536-file manifest still matches its
  saved pre-fork hashes. This independently supports the source-preservation
  claim, rather than relying only on a saved boolean.

The initial harness expectation of seven outputs per hill was incorrect for
canonical revegetation preparation with graphics enabled. The run cards support
the corrected 576-file inventory. The retained native logs and all artifacts
support the readback-only correction; the failed initial harness is not presented
as a successful attempt.

## Graphics limitation and corrected audit metadata

Independently scanned all 72 graphics files, every numeric token, every daily
row and all 144 min/max summary rows. Every simulation day appears exactly once
per implicit OFE position. All rows have the expected 104 fields. Exactly
734,107 cells contain asterisks, exclusively physical field 84, “Days since last
disturbance.” Every other numeric cell is finite.

The [independent formatter review](mipa03_graphics_limit_review.md) binds the
unchanged BIGOUT/BIGHDR sources and demonstrates finite disturbance ages
printing as stars once the inherited F10.5 width is exceeded. This audit confirms
the limitation's complete artifact extent. It does not reconstruct lost values,
claim all 576 files are fully numeric, or infer nonfinite model state from stars.
The format and saved graphics setting remain preserved.

During review, `artifact-audit.json` incorrectly stored the final graphics row
under `finite_water_columns`: the audit's graphics loop shadowed that variable.
The actual water finite checks had run, but the metadata inventory was invalid.
The parent preserved that receipt, corrected the variable names and generated
`artifact-audit-v3.json` without another model execution. The new column inventory
and every graphics count agree with this independent scan. Use v3 for the corrected
metadata; the original remains superseded evidence.

## Isolated configured observer probes

Independently verified `configured-observation-v2` for p8, p7 and p57, containing
1, 11 and 2 OFEs respectively. All copied declared inputs match the normal
configured run. The observer marker is the deliberate addition. All 84 cover
band rows, comprising 2,940 stored REAL values over 35 years, match emitted decks
when round-tripped to native REAL precision. OFE 2/10 values are distinct in p7.
All 14 native SOIL header records agree with the owned soil reader's texture enum,
uksat and lkeff. Dynamic trace values are finite, and every expected daily GROW
state is present. All 24 production output hashes match the unobserved configured
NFS execution exactly.

These probes used the same service identity and final binary on container-local
`/tmp` storage, then archived results. The earlier dense NFS trace attempt timed
out at 300 seconds and remains retained as failed/partial evidence. The local
probe success establishes consumed-state and output-neutrality evidence; it does
not erase the NFS diagnostic limitation or claim dense tracing passed there.
The complete normal configured workflow separately passed on the normal NFS mount.

## Report-content checkpoint and evidence

Checked all six numerical table rows in `main-r7.tex` directly against the final
history receipt; every displayed delta agrees at its stated precision. The final
native log reports 1,750 passing tests; watchlist reports 31 passing cases;
post-vendor checks report eight passes and both smoke logs show completion.
The separately added reader rerun reports 27 passes. These counts overlap and
must not be summed. The populated application paragraph distinguishes synthetic
cover, calendar versus water years, optional null storage, local observer probes
and the retained NFS timeout appropriately.

A missing closing TeX quotation mark on the graphics field name was reported to
the parent for correction. Final compiled PDF, manifest/public attachment binding
and publication approval remain a separate review checkpoint.

Reproducible independent scripts, logs and JSON results live under
`/wc1/holdouts/mipa-native-r7-20261103/configured-independent-qa/`:
`audit.py`, `audit_observers.py`, `audit.json`, `observers.json`,
`native-parquet-p7.json`, `source-preservation.json`, `report-table.json`,
`receipt-bindings.json` and `manifest.json`. The Python scripts use the WEPPpy
virtualenv for DuckDB, Arrow and the owned soil reader. No model rerun or shared
build was performed by this review.
