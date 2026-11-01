# SIFT rock conversion and frozen-water accounting

Status: completed bounded phase, 2026-11-01. Independent reviews pass; 120 focused
and 12,634 full-suite tests pass (423 skipped). All 480 private evidence files
are archived and verified; no deployment or native physics change.

BC SIFT now converts source rock volume to WEPP dry mass using fine-earth bulk
density. Actual generated files and three complete 16-year native histories
validate propagation, SAT 0.75, the 200 mm horizon split and existing native
caps. Separately, the complete unchanged FRWATC campaign retains 29 cases:
18 normal controls close and five threshold cases expose mapping discrepancies.
These findings do not promote a native capacity or surface-cover correction.

Start with [findings](artifacts/findings.md), [validation](artifacts/validation.md)
and the [proposed next study](artifacts/next-study.md). Commands and private
runtime requirements are in [reproduce](artifacts/reproduce.md). Independent
[science](artifacts/final-science-review.md),
[implementation](artifacts/implementation-review.md) and
[native packaging](artifacts/packaging-review.md) reviews retain their boundaries.
The [ExecPlan](prompts/active/sift_frozen_execplan.md) and [tracker](tracker.md)
record milestone status.

Operator authority: proceed with the recommended SIFT repair and separately
reviewed frozen-water/drainage investigation. Starting WEPPpy d15d1470f;
contract ancestor 6b08f3452; native evidence checkpoint add893ad6. Prior studies,
unrelated SSURGO/usersum changes, production deployments, historical projects,
withheld Roads materials and native model equations are preserved.

Retention: [archive receipt](artifacts/archive-receipt.json) binds every member
and the complete raw inventory. The archive holds the pre-closure scientific
publication snapshot; final closure metadata and the publication manifest are
retained in Git to avoid circular archive hashes.
