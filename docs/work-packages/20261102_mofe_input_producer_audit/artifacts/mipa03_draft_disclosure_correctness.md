# MIPA-03 draft release disclosure correctness review

Reviewer: `mipa03_contract_correctness`, 2026-11-03 UTC.
Scope: selected native `docs/release-notes/wepp_261029/main-r7.tex` draft,
SHA-256 `dc1a377bfaad5f49c3d22d7eae26ec04b6214729eaeb97d3ead11bfa9da5991e`.
Disposition: **content corrections requested; no publication approval**.
`FINALGATES` and `APPLICATIONRESULT` are intentional pending placeholders, not
findings. Final populated PDF/layout and manifest review remains separate.

## Actionable disclosure findings

1. **Medium, lines 70–71: test count overstates numerical agreement.**
   The 295 growth/hydraulic suite tests include source-fixture hashes,
   discriminating properties and deliberate reference/candidate domain failures.
   They are not 295 successful pairwise numerical comparisons. Replace
   “routines agree in 295 ... checks” with “The compiled-reference/candidate
   suites passed 295 checks, covering growth, hydraulics, residue,
   initialization and cutting.” This preserves the correct count without
   implying unsupported agreement or successful domain histories.
2. **Low, lines 31–35 and 70–76: make comparison scope explicit.**
   Add a short sentence that whole GROW/INITGR and extracted hydraulic, residue
   and cutting source spans were tested under the same compiler. This is source
   consumer compatibility, not historical-binary equivalence; historical build
   flags are not established by a contemporary sidecar. The existing reference
   source/binary binding is sound but does not establish that stronger claim.

Optional clarity: replace the unspecified “2005 fire day” with July 15, 2005
(day 196), and include the OFE 1 canopy example (.225 observed versus .165
transformed on that day). The retained mode/history QA supplies these values.

## Claims checked

All 30 table values independently recompute from the final history receipt:
transformed minus observed `Q`, `Ep+Es+Er`, `Dp`, `latqcc`, and terminal
`Total-Soil`, for daily/hourly and OFEs 1–3. Rounding to three decimals matches
every printed value. All 12 contributing terminal records have zero `frozwt`
and `Snow-Water`, so the liquid-storage description is justified. The per-element
diagnostic and non-conservation qualifications correctly limit the table.

Evidence: `/wc1/holdouts/mipa-native-r7-20261103/histories-final-v1/receipt.json`;
independently retained full-history audit and exact final-binary binding under
`mode-history-final-qa/`; and `mipa03_native_mode_history_qa.md`.
The 17,532 records per history and four observer-neutrality pairs agree with
that independent audit. Development and final numerical contrasts match exactly.

Six ordinary controls were independently checked against
`/wc1/holdouts/mipa-native-r7-20261103/controls-final-v1/receipt.json`.
Each before/after output map agrees, and all 84 retained output files were
rehash-verified against it. Seven ordinary outputs per case match revision 6.

The ten separate mode tests include actual final MAIN version2→3 execution,
fresh RAP hillslope pass creation and subsequent routing. The mode/history QA
binds watershed SHA-256
`4a9da3980d1a9249e566626c01de920de7dba5088ec25324dc1c6dd6eff8c825`.
This closes the actual combined-transition evidence gap in the earlier
implementation review; it must remain separate from the earlier collected
full-suite count. Its 9002 fixture establishes mode behavior, not 9005 formulas.

Scientific ownership and preserved quirks match the contract: anniversary
comparison, differing comparison/assignment bands, shared crop root parameter,
log/clamp ordering, .99 followed by .99 saturation treatment, layer feedback,
and absence of inferred scientific fixes. The synthetic-history description,
non-field-validity qualification, historical Roads limitations and undeployed
scope are appropriate. No scientific-fidelity or table-value defect was found.

Configured-application success, final mandatory gate counts, complete release
manifest and final PDF are pending. No production or report source was modified
by this review.

## Draft content closure

Reinspection after the author's edits confirms both disclosure findings closed:
the draft now says the suites “passed 295 checks,” identifies hash/property/domain
checks, distinguishes whole routines from extracted source spans, and disclaims
historical-binary equivalence with unknown old compiler flags. It also supplies
the specific July 15, 2005 date and the supported .225/.165 canopy example.
No remaining scientific-fidelity or table-content correction is requested at
this checkpoint. Final populated PDF, manifest and pending gates still require
review; this is not publication approval.

The subsequent populated four-page PDF is reviewed separately in
`mipa03_final_pdf_correctness.md`. Its bound content/visual PASS supersedes this
draft checkpoint's pending PDF review, without changing the retained draft findings.
