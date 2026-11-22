# RQ engine schema defaults code quality refactor

Closed locally 2026-11-21 (Pacific). The discovery API exposes the schemas, defaults, hints, output inventory and operation documentation an API client uses to plan work on a run. At c82da0a94 one module owns all ten HTTP routes, reads NoDb controllers, resolves capabilities and builds every operation descriptor. The refactor separates those responsibilities across 17 production modules. The router now measures 540 source lines, and 435 fixture-based HTTP responses matched the original bytes.

## Scope and acceptance

Faithfully extract the existing implementation. Keep router registration, authentication order, error envelopes, revision and ETag inputs, operation ordering and all serialized fields compatible. The executable acceptance artifacts are generated discovery responses and the application's route definitions. Compare representative outputs from the baseline and candidate, run route contract tests and the broad pytest gate, and review the diff. Measure every extracted module with the repository's SLOC, function length and complexity analyzer. See the [tracker](tracker.md) for status.

## Budget and impact

Use existing Python modules, FastAPI responses and test infrastructure. The package changes internal ownership only. Run data, parameterization, queues, dependencies, deployment and privileges are outside the change. Security impact is low because each authenticated handler still checks the same JWT scopes and run access before reading state. Include that ordering in correctness review. The intended beneficiaries are RQ engine maintainers and discovery API consumers.
