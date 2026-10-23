# Roads parameter validation suite

Status: Closed 2026-10-23 UTC. Owner: Roger.
Starting revision: a7ea23927. Existing task-scoped commit authority persists.

Deliver a site-derived reproducible parameter suite, execute it, assess native
detachment/water/export responses, and vendor/link the generated report in Usersum.
Authority: [suite contract](../../schemas/roads-validation-suite-contract.md), existing
Roads accounting/summary/lifecycle contracts and Usersum specification.
Execute [the plan](prompts/completed/validation_execplan.md); maintain [tracker](tracker.md).

Compatibility is additive: new tests, scientific fixtures, documentation and the bounded production management-reference repair.
No model formula/default, auth policy or output-schema changes. Final executions
preserve source scientific artifacts; the initial source-log side effect and
its harness correction are recorded in the validation evidence.
Complexity budget: existing Python/pytest, native readers, model runner and Usersum
vendor pipeline; no new dependencies or services. Security impact: low, curated
public documentation and isolated scientific fixtures; exclude private project
metadata. Independent correctness and publication contract reviews are required.

Acceptance requires actual fresh matrix outputs, direct prepared-file readback,
three additive full-upload designs plus qualified positive and negative unrutted
checks, reproducible report/provenance, Usersum render
and navigation evidence, and focused/broad regression. Profile comparison is not
field calibration or whole-watershed routing validation by itself.

The pilot-discovered management repair retains all plant definitions and their
references in single/two-OFE inputs. See the management contract decision; no
scientific template parameters or defaults are changed. One stray non-data token
is removed from the paved sandy-loam soil template. Historical outputs
are not rewritten or certified; regenerated two-OFE no-traffic results may change.

## Delivered and validated

Implementation `a501c15cc` adds 516 executed cases across clay, loam, sand and silt,
retained numerical/provenance artifacts, full-project checks, two bounded input
repairs and a vendored Usersum report. Contract checkpoints: `c4774cf2a`,
`5ebc3b0ff`, `fa5c40a76`. Both final independent reviews approve. Broad regression:
11,647 passed, 131 skipped in 3,270.42 seconds. See
[validation evidence](artifacts/20261023_validation.md) and
[the published report](https://wc.bearhive.duckdns.org/weppcloud/usersum/doc/usersum.source.roads_validation).

Full-upload unrutted remains a verified negative control with two invalid upstream
OFE lengths. Its positive subset excludes exactly one recorded upload feature;
whole-site unrutted success and field calibration are not claimed. No deployment
or original-project rerun is included. Durable requirements and interpretation
remain in the suite contract, tests/roads/README.md and analysis_context.md.
