# Fresh Roads contexts after baseline-isolation conformance repair

Apply the unchanged five-context scope and acceptance checks in
[the original protocol](resumption-r7-current-roads-protocol.md).
The first v1 context failed baseline invariance because workspace staging linked
`tc_out.txt`, a generated native diagnostic. Preserve that failed root and all
receipts. The smallest conformance repair excludes this file while retaining the
`tc.txt` input; no model parameters or tolerances change.

Declare a fresh `current-roads-v2` root with the repaired production source and
new helper hashes. Require the original reviewed current-project-v2 source
inventory to remain unchanged, and independently review staging before execution.
Run all four positives and the identical full-upload negative sequentially.
Baseline preservation, physical accounting and report readback remain mandatory.
