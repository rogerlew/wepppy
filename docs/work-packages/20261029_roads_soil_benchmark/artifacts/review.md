# Study correctness review

Self-review, 2026-10-29. No independent-agent review is claimed.

## Evidence checks

- All 2,880 declared matrix cases exist; expected identities and six execution
  variants are checked before report generation.
- Binary-only controls share all consumed scientific inputs. Soil comparisons
  share geometry, climate and management. The current-selection control's
  management change is explicit.
- All consumed input and native output hashes were rechecked. Source templates,
  production builders, binaries and fixture manifest retain their pinned identities.
- Daily WAT checks validate every calendar/OFE tuple and finite numeric fields.
  All five climates have 5,844 days; all main profiles have three OFEs.
- Missing annual summaries and unsupported zero-loss layouts fail explicitly.
  Regression coverage uses retained native output, disjoint loss regions,
  legitimate zero export, missing-year and missing-day failures.
- No ratio denominator floor, omitted out-of-band groups or forced monotonic
  interpretation. Printed zero and near-resolution reference exports remain visible.
- Screening excludes Charleston and clay loam. Validation candidates were fixed
  before seeing held-out results; no subsequent fitting occurred.
- Main-report spatial net loss is distinguished from daily PASS detachment and
  road-prism erosion. Supplemental PASS metrics remain separately named.
- Long-road controls exceed the reference API bound and are identified as stress
  controls. They are not counted in the admitted matched-profile matrix.

## Findings and disposition

No production candidate is accepted. Material wet-climate unrutted failures
remain despite good pooled agreement. Generated specimens are 7778 base soils,
not landuse-conditioned prepared 9002/9005 soils; the report names that limitation
and the next bounded experiment. Full-project Roads integration, physical field
validation, production parameter changes and deployment were not performed.

Two reference-template admission defects were repaired only for the exact
hashed inputs in scratch; originals and failed attempts remain available.
The resumed final matrix records the prior completed-case hashes and a separate
execution source snapshot. The final report rechecks those immutable records.

The supplemental high-loss case required a report-consistency tolerance for
native accumulation precision; its actual mean difference is retained. Main
matrix results had already passed the stricter decimal-only check. Source
snapshots bind the original main report and the supplemental analysis separately.

Final repository validation: 12,076 passed, 298 skipped, no failures across
disjoint groups. Exact commands, counts and retained logs are recorded in
[validation.md](validation.md). Scientific rejection remains independent of
these passing software checks.
