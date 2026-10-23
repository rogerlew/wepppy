# Roads parameter validation suite

Status: active specification, 2026-10-23 UTC. Owner: Roger.
Starting revision: a7ea23927. Existing task-scoped commit authority persists.

Deliver a site-derived reproducible parameter suite, execute it, assess native
detachment/water/export responses, and vendor/link the generated report in Usersum.
Authority: [suite contract](../../schemas/roads-validation-suite-contract.md), existing
Roads accounting/summary/lifecycle contracts and Usersum specification.
Execute [the plan](prompts/active/validation_execplan.md); maintain [tracker](tracker.md).

Compatibility is additive: new tests, scientific fixtures, documentation and the bounded production management-reference repair.
No model formula/default, original run, auth policy or output-schema changes.
Complexity budget: existing Python/pytest, native readers, model runner and Usersum
vendor pipeline; no new dependencies or services. Security impact: low, curated
public documentation and isolated scientific fixtures; exclude private project
metadata. Independent correctness and publication contract reviews are required.

Acceptance requires actual fresh matrix outputs, direct prepared-file readback,
four-design full-project validation, reproducible report/provenance, Usersum render
and navigation evidence, and focused/broad regression. Profile comparison is not
field calibration or whole-watershed routing validation by itself.

The pilot-discovered management repair retains all plant definitions and their
references in single/two-OFE inputs. See the management contract decision; no
legacy scientific templates or parameter defaults are changed. Historical outputs
are not rewritten or certified; regenerated two-OFE no-traffic results may change.
