# Theme Lab header conformance repair

Observed 2026-11-18 UTC in the actual isolated application: GET /ui/components/
returned HTTP 500 because header/_run_header_fixed.htm read ron.developer_mode,
but the gallery supplies current_ron, the same view model used throughout that
shared header. Existing tests provided both aliases and hid the defect.

Classification: implementation conformance defect, no normative behavior change.
Canonical authority: docs/schemas/project-developer-mode-contract.md, State and
lifecycle and UI sections. A false/missing legacy developer mode hides the
indicator; true shows it. No persistence, enablement, authorization, formulas or
other developer-mode behavior changes. Theme Lab's sample view remains valid.

Repair only that header expression to use current_ron. Add regression coverage
with ron absent, and missing/false/true mode on current_ron. Retest actual Theme Lab
HTTP/rendered browser output; a fixture-only template pass is insufficient.
