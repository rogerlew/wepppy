# Omni test refactor tracker

## Progress

- [x] 2026-11-22 05:35 UTC. Capture the passing 229-case Omni baseline and choose extraction boundaries.
- [x] 2026-11-22 05:37 UTC. Split the module and scope dependency patches to individual tests.
- [x] 2026-11-22 05:39 UTC. Verify all 229 cases and run the 83 controller cases in reverse module order. Record source parity and quality measurements.
- [x] 2026-11-22 05:39 UTC. Document the new test selection and prepare the validated change for PR integration.

## Decisions

- 2026-11-22 05:35 UTC. Keep scenario and state tests in the original file. Move clone, selection, artifact, stream order and execution tests to siblings.
- 2026-11-22 05:35 UTC. Run the Omni suite and compare exact cases with the baseline, per the requested validation scope.
- 2026-11-22 05:37 UTC. Use real runtime dependency imports and scoped monkeypatches for tests that substitute raster behavior.

See the [validation record](artifacts/validation.md) and the [completed ExecPlan](prompts/completed/implementation_execplan.md).
