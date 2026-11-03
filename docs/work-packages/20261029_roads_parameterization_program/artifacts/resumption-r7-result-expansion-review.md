# Revision 7 seed results and panel expansion: implementation review

Reviewer: independent `mipa_contract_correctness`, 2026-11-03 UTC. This additive
review preserves the seed declarations, outputs and earlier reviews. No native
model was invoked by this reviewer. Scientific interpretation and scoring receive
a separate independent review.

## Findings and disposition

**Seed artifact readback, panel implementation/staging, scorer and launcher PASS.**
No major implementation finding remains. Execution requires the additive receipt
to bind the exact approved files and both reviews before launch. This does
not accept Roads parameters, current production preparation, withheld performance
or UI work.

Reviewed panel driver `rebaseline_r7_panel.py`, SHA256
`da7c6e21123d7e1b8c1f3b608cbfb615d5b24683e01be8f116b5abaad350c6e8`;
protocol `resumption-r7-panel-protocol.md`, SHA256
`7799810d4c7f84c9c82a10b2971b1330dcbe32716497aa06ad42d8642edaf958`.

## Independent seed output readback

Verified `engine-seeds-v3/results.json`, SHA256
`a649bea9c8504744128f2d791ca5992b0ea40c10aa356130412bff43e56c47be`,
against declaration SHA256
`c60b95c568980858c2b8f0fd0c6e0cf646900c73c0ca0f91bfc711007dbd384f`.

- All 36 results match their declared tasks and immutable per-case records;
  pre-audit native receipts, exit codes, stdout/stderr hashes, completion banners
  and UI/groundwater/PMET markers agree.
- All 252 ordinary output hashes, copied inputs/auxiliaries, source/reference
  records and outputs, binaries and current execution dependencies match their
  bindings. Each loss report was parsed again and matched its recorded metrics.
- PASS completeness and strict EVENT particle certificates were recomputed
  read-only and matched exactly for all 36 cases.
- All 36 full physical audits were rerun against disposable copies of the
  ordinary native outputs and run inputs. Each new audit exactly matched the
  recorded water, ELEMENT/EBE, sediment and invalid-water diagnostics.
- Inventoried and hashed every original per-case file before and after this
  verification, including existing interchange outputs. No original file or
  inventory changed. Converters never wrote into accepted evidence directories.
- All 18 r4 cases reproduced all seven historical ordinary outputs exactly.
  The r7 cases changed 116 of their 126 ordinary output files. All 36 passed
  the declared native, physical, completeness and strict EVENT predicates.

Machine evidence: `resumption-r7-seed-readback.json`, SHA256
`9ad2cf1d3bd693c68df88bcc7f8d8b7117483e877259eac5078643b48ee17539`.
R4 has 1,677 EVENT records and 31 positive non-EVENT terminal dates; r7 has
1,552 EVENT records and 26 such dates. A result hash or successful exit alone
was not used as evidence for these conclusions.

## Expansion source review

The panel driver verifies the accepted seed gate and its result binding before
declaration, selects the exact frozen 840-row conditioned-U12 source panel,
requires source-record equality and the historical r4 binary identity, and
copies all twelve native inputs unchanged. All 840 panel entries independently
matched their source JSON records; their historical auxiliary reference soils
exist. The panel contains seven development materials with 120 cases each.
The material allowlist excludes withheld materials.

For each task, the driver binds the FSWEPP reference record and output hashes,
requires matching climate/management/geometry input hashes, checks soil semantic
readback and exact output targets, and binds auxiliary `reference.sol` separately
as unconsumed provenance. It creates exclusive task directories. The r7 binary
is copied from the verified seed lane and must retain the same hash.

Worker execution delegates to the reviewed seed executor with an explicit panel
root. Its process-local root assignment leaves the parent seed gate path intact.
The declaration binds eight workers, a 300-second timeout, UID/GID, dependencies,
source panel and seed summary. Post-execution source/dependency/binary checks
remain. Native receipts precede parser/audit work; failures cannot be converted
into successful rows. An audit exception may stop aggregate result production:
such an attempt remains incomplete, retaining its declared 840 denominator and
per-case native evidence, and cannot satisfy acceptance through a subset.

## Residual limits and execution condition

The seed sample establishes comparability, not the full-panel magnitude gate.
The expansion renews the current-engine result for historical conditioned inputs;
it does not exercise current complete production preparation. Engine differences
do not isolate FC/HK causality. Water diagnostics retain their explicit incomplete
closure scope. Strict particle criteria cover EVENT payloads; positive terminal
sediment on SUBEVENT/NO EVENT dates remains disclosed without inventing payloads
or changing the native runoff threshold. Snow consumption has no dynamic trace
in this experiment.

Before panel execution, independently verify the completed declaration, all 840
unique task paths, 10,080 native-input copies and 840 auxiliaries, source/reference
bindings, exact binary/dependency identities, UID/GID and empty output directories.
Do not modify the frozen driver/protocol after declaration. No full-panel result
or acceptance conclusion is made by this pre-execution review.

## Final panel staging readback

Independently verified `panel840-v1/declaration.json`, SHA256
`68fa8f4507821db21e104a625da0f6ba6401136bc6408594c4051344a51f6b04`.
All 840 tasks are unique, with 10,080 native-input copies and 840 auxiliary copies
matching retained sources as separate regular files. Verified 5,880 source-output
bindings and 5,880 reference-output bindings, all 80 dependencies, the r7 binary,
executed panel driver, frozen source-panel and seed-summary identities. All output
directories were empty and no execution-start receipt existed. The declaration
binds UID 1000/GID 993, eight workers and 300 seconds per call. Machine evidence
is `resumption-r7-panel-staging-readback.json`.

## Scorer and reviewed-launcher review

**R7-SCORE-01 — Medium, pre-execution freeze gap.** The initial scorer records
its current source and restriction-metadata hashes but does not compare them to
the additive `execution-review.json`/`execution-review-verified.json` receipts.
The launcher verifies those files before native execution; a later scorer or
metadata change could nevertheless be silently used at scoring. Require the
scorer to verify the review receipt's identity, exact declaration binding and
current scorer/metadata/acceptance file hashes before producing an output.
Closed by final independent readback: the scorer invokes
`verify_execution_review` before loading/scoring results, validates the verified
receipt hash, exact panel declaration and review decisions, and matches canonical
service-path entries to the current scorer, restriction metadata and acceptance
bytes. Changed or missing bindings fail before score creation.

No arithmetic defect was identified. The scorer preserves meaningful/small-load
thresholds, exact 840-case membership and failed-case denominators. Numerical
agreement cannot override its physical/runtime/particle/completeness veto. It
reports raw and equal emitted-material-family weighting, all major strata and
57 higher-order axis combinations as descriptive intersections, signed bias with
zeros separate, and recoveries/regressions. Its final scientific acceptance flag
remains false. SLID labels are excluded from material signatures while all native
soil fields across matched contexts are retained.

Independent focused run: the final **28 scoring tests passed**, including ten
review-receipt, declaration, file-byte, path, approval and missing-verification
checks. An independent
arithmetic-only control using the frozen r4 exports reproduced 713/766 meaningful
and 31/74 small-load passes, with seven distinct emitted material families and
both numerical gates unmet. Synthetic validity flags in that control tested
arithmetic only and are not renewed physical acceptance of historical cases.

The thin launcher checks the receipt/declaration, review pass decisions, its own
source and every bound file before creating a one-time verification receipt and
calling the unchanged panel driver. Its final approval requires the completed
receipt to include the scorer, metadata, acceptance and both independent reviews.

Approved exact scorer SHA256:
`32a7b7a4acffb0acc124014548cb30b7d75e379d0162c3e34ffb240f4585791e`.
Approved exact launcher SHA256:
`a383c107924ebd742d25930b808ceebcf6aac65d67c4e57cf79444fce9de6c12`.
Restriction provenance SHA256:
`cd9679d20d79cd7581c5859eee92c99873ddde0fdf14cb70381ed0822984425c`.
Acceptance SHA256:
`16d6980c4188ea511540cd63161af852c6a7d164856f07665224b8cb8d3f2db4`.
These approvals apply to the exact panel declaration above. Post-execution reviews
must use new artifacts rather than altering this pre-execution review after it is
bound. No panel outcome is pre-approved.
