# Code Review and Findings Disposition

## Scope

An independent risk-focused reviewer inspected parser strictness, schema
semantics, historical compatibility, consumer behavior, release provenance,
and the rebuilt shared object.

## Findings

| Severity | Finding | Disposition |
|----------|---------|-------------|
| High | A 12-only parser would break regeneration of historical 11-field LOSS files. | Fixed by supporting explicit uniform 11-field legacy and 12-field current layouts. |
| High | Per-row width acceptance could misclassify a truncated current row as legacy. | Fixed by detecting the first annual Hill width once per file and rejecting mixed layouts across all yearly sections. |
| Medium | Legacy absence was initially represented as valid IEEE NaN rather than Arrow null. | Fixed with an explicit missing value that produces a true nullable Arrow slot; `null_count` regression added. |
| Medium | The current-format fixture selector also matched the `Hillslopes` header. | Fixed by selecting rows whose first token is exactly `Hill`. |
| Medium | A legacy test retained the prior NaN expectation after true-null implementation. | Fixed to assert the native missing value and generated Arrow null count. |

## Final Review

The closing review approved with no unresolved correctness, compatibility,
release-provenance, or consumer findings. It verified source commit `fc3e361`,
release artifact SHA256
`faa9173665aee64e92ce077488121cc21b7a1cc06cb771b280df81c7862299f1`,
table-specific schema versioning, and the absence of positional production
consumers.
