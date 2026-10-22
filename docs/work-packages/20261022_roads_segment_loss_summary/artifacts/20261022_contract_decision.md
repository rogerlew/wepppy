# Contract decision: source-qualified segment summary

Starting implementation: WEPPpy `61f17b0b7`, native `c941cb6` (no native changes planned).
Authority: Roger requested “scaffold and execute a work-package to correct the
roads_segment_loss_summary.parquet” following the concrete duplicated-attribution
diagnosis. Session task-scoped commit authorization remains in effect.

Classification: intended contract correction, not unchanged-contract conformance.
The Roads specification currently prescribes the faulty target-first join.
Amend it and output-scope contract; introduce roads-segment-loss-summary-contract
and ADR-0103 before implementation. Shared NoDb locking and Roads modeled-area
water contract are unchanged. Do not reopen closed packages.

Delta: original source-profile PASS exports/WAT area replace receiving-hillslope
loss; annualize over complete simulation years; preserve field names and add
provenance/scope; unsupported prism/buffer aliases become NULL. Missing sources
fail rather than become zero. Empty/legacy/skipped/malformed states are explicit
in the contract. Source-qualified reduction uses native interchange and DuckDB.

Security high: validate source/destination identity, pre/post consumption hashes,
atomic publication and existing modes. No auth/queue/execution topology change.
Regression: distinct roads sharing target must remain distinct; unrelated target
values cannot affect results; no-event years, MOFE and remainder scope, optional
empty state, missing/invalid IDs/dates/values, aliases and failure preservation.
Real isolated UM1 should yield about 4,810.818 kg/year across 34 original sources,
with segment 900001 about 4,071.013 kg/year, not repeated target rows totaling
50,397.2 kg/year. Validate actual downloadable CSV and archive/restore bytes.

## Review dispositions

Accounting review requested execution-duration binding, complete native calendar
checks, deterministic scope mapping, explicit NULL rejection, consumed Parquet
path/hash identity, and separation from failed-run lifecycle. All are included
in the current canonical contract. Integration review requested schema-level
annual units to avoid changing CSV headers and visible failure-stage retention;
both are included. Julian day bounds explicitly refer to days within each year.
No implementation files changed before final approvals/checkpoint.
