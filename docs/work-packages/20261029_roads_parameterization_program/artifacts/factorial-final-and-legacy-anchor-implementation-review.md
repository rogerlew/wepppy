# Final factorial evidence and legacy-anchor implementation review

**No remaining implementation blocker to the declared legacy-anchor pool.**
The factorial's required all-case runtime/log readback is complete. These are
artifact and implementation conclusions; scientific/parameter acceptance and
the full application-suite handoff gate remain separate.

## Completed factorial evidence

Reviewed `verify_combined_hydraulics_r4.py`
(`2c058ca8bcb3ab3207d6fee716cfef05d086b94ce3dd02d873c1606510253f1d`):
it binds the frozen script/declaration/dependencies, matches all result records,
rehashes artifacts and fresh/reused logs, invokes the actual runtime validator,
and recomputes loss metrics, accounting, and particle audits.

Independently matched all 928 declared tasks, records, and verifier rows; rehashed
19,488 core/auxiliary/output files and 1,856 execution logs; called the actual
runtime validator for all 928 cases; and reproduced all 928 particle audits.
Every case completed and retains its physical-audit pass. The three visible
flags are all `fraction_sum` findings: Denver/1718465 road-off buffer-cap,
year 8/day 228; site/2711250 road-off baseline, 2003/day 29; and site/1718465
road-on fill-fixed, 2008/day 278. No flag was removed or accepted by this review.

This closes the required actual-evidence readback for the frozen v2 fresh-log
manifest gap. The source remains unchanged at
`803d4a41587a7dc5eea03c31d16e82377c77b28de4d9d85abc30a4bba4adf526`.
Verification receipt SHA-256:
`de07228cbb893070f3e885a833980382436677ea7b665eac2882084d9eed38ca`.

Machine review: `/tmp/combined-hydraulics-r4-final-evidence-review.json`.

## Legacy anchors

Reviewed `legacy_soil_anchors_r4.py`
(`adfb7068a3e6e5070522edf2759483721d6131576da8528a3c38d8cf9aefd761`)
and declaration
`c259aae606bf01d33b6d1de777fa864c9dcc8ddf806b4b30ffb755772e9f3484`.

Independently verified all 116 unique cases: 1,392 native input files are exact
copies of their legacy sources, and all 116 auxiliary reference soils match.
Every staged soil reparses to its source record. Actual modern U12 inputs were
also rehashed; only `p1.sol` differs. Source and modern record identities,
prior exports, and complete legacy soil profiles remain fixed. No format
translation, mixed-role substitution, or parameter change is introduced.

The new harness records fresh stdout/stderr hashes explicitly and rechecks them
alongside the actual runtime contract. Its pool can reuse only the exact first
preflight record bound to the current declaration, and every final record goes
through `verify()`, including log hashes, runtime validation, loss/accounting
recomputation, and particle readback. The shared helper's frozen factorial root
is not used as the anchor output destination.

The actual first-case preflight independently passes artifact/log/runtime,
loss-metric, and particle readback; all 70 effective dependencies match.
Preflight receipt SHA-256:
`bdda4ca3e05310deda40b136f4d61ab4761e079d7d4a4c5c70c08be4d9ae3292`.

The remaining 115 executions and the implemented final all-case verification
must finish before interpreting the anchor results. No complete application-suite
pass is inferred from the currently running isolated shards.

Machine review: `/tmp/legacy-soil-anchors-r4-implementation-review.json`.
