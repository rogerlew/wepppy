# Roads controller code quality refactor

**Status**: Open; implementation complete, final acceptance in progress (2026-11-17)
**Timezone**: UTC

## Overview

Refactor `wepppy/nodb/mods/roads/roads.py` into a stable NoDb facade and focused internal collaborators. The measured baseline is 5,907 SLOC, 150 functions, and a 2,069-line `run_roads_wepp()` method. The intended result is easier review and testing while users retain the same upload, preparation, execution, inspection, and reporting behavior.

## Objectives and scope

Extract parameter/input handling, preparation orchestration, native input writers, design-specific execution, PASS assembly, report publication, and query presentation in independently validated passes. Preserve `Roads` imports, public signatures, private compatibility seams used by callers/tests, saved-state identity, lock boundaries, errors, and artifact schemas. Reuse `parameterization.py`, `_parameterization_comparisons.py`, `_unrutted.py`, `_segment_loss_summary.py`, and `monotonic_segments.py`.

No science, defaults, formulas, tolerances, unit conversion, template content, routing policy, upload format, API, queue topology, dependency, deployment, or user workflow changes are included. A discovered defect is recorded separately rather than silently corrected during extraction.

## Complexity Budget

- Existing mechanisms reused: NoDb locking/persistence, native WEPP runner, owned Rust/geospatial libraries, existing Roads helpers and lifecycle tooling.
- New mechanisms permitted: private Python modules and focused internal functions/classes only.
- Simplest plausible change first: delegate a cohesive input-validation responsibility while retaining the existing facade and transaction placement.
- Real acceptance condition: identical observable behavior and generated/consumed artifact semantics through the normal Roads lifecycle.
- Evidence before escalation: a retained failing case showing why a smaller extraction cannot preserve behavior.
- Prohibited expansion: new services, queues, datastores, dependencies, privilege changes, generalized plugin frameworks, or whole-controller persistence redesign.

## Implementation Fidelity and Evidence

**Fidelity target**: faithful extraction of the current `roads.py`, not surrogate builders. **Cutover proof**: tests enter through `Roads` and demonstrate the new collaborators are actually called. **Acceptance evidence type**: both fixture-based characterization and fresh native generated-output evidence. A helper existing on disk is implemented; it is wired only when the real facade delegates to it.

## Generated Artifact Validation Gate

Applicable to execution and all writer/publication extractions. Retain intent and reloaded `roads.nodb`, prepared segment membership, parameterization provenance, emitted slope/soil/management/run inputs, exact consumed paths, native executable identity, PASS/WAT and watershed results, execution manifests, summary/parquet readback, and current/historical report admission. Compare baseline and candidate using identical declared scientific inputs and binary. Parse numeric content and OFE (overland flow element) roles, not just hashes or file existence. Normalize only documented volatile fields such as scratch-root paths and timestamps; never normalize scientific differences away.

Exercise writers and native consumers directly, including failed/partial execution and retry. Full-project acceptance uses disposable copies of an available real project under `/wc1/runs/`, with source hashes retained; never mutate the source. Record unavailable fixtures or runtime as explicit open gates. Native binaries are not changed here: use and hash the currently installed executable, and verify the candidate Python checkout consumed by the container. No binary rebuild is required by this package.

Current claim: refactor implemented and focused tests pass; final native/project parity, broad-suite validation and review closeout remain in progress.

## Success Criteria

- The normal `Roads` lifecycle uses cohesive collaborators; no equivalent monolith is merely relocated.
- Public behavior, durable state, locking, diagnostic contracts, native input semantics, accounting, and report freshness remain equivalent.
- Before/after quality metrics cover the facade and every extracted file; missing complexity measurement is explicitly unresolved.
- Focused and broad regression gates, native/project artifact comparisons, and independent correctness, QA, and security reviews pass with no unresolved medium/high findings.
- Developer module map and applicable user/operator documentation reflect the final structure; execution plan and tracker record evidence and limitations.

The quality design targets are below the tool's red bands: file SLOC < 1,200, maximum function length < 150, and maximum measured cyclomatic complexity < 30 for the facade and extracted modules. These are decomposition targets, not permission to fragment coherent logic solely for a score. Root AGENTS makes bands observe-only; record any residual hotspot, concrete readability tradeoff, and follow-up instead of treating telemetry alone as a merge blocker. Behavioral and artifact gates remain mandatory.

## Parameterization ADR Gate

Parameterization change present: no. ADR required: no. Defaults, formulas, thresholds, fallback heuristics, and templates must remain unchanged. Any proposed change needs separate scope and the canonical ADR process before implementation.

## Security Impact and Review Gate

Implementation triage: **high**, because extraction traverses uploaded paths, workspace cleanup/link/copy operations, native execution, and result publication. Dedicated `artifacts/security_review.md` is required at implementation closeout using the security review template. The implementation preserves existing execution and publication boundaries. Preserve existing sanitization, authorization, execution identities, error translation, cancellation rollback, and path containment.

## Stakeholders and dependencies

The operator owns scope; the implementing agent owns task-branch changes and evidence; independent reviewers assess correctness, maintainability, and security. Prerequisites are a container consuming the exact candidate checkout, existing geospatial/native dependencies, a measured baseline, and disposable project fixtures. Do not remount or recreate another task's shared stack.

Related implementation history: [Unrutted partial crossings](../20261117_roads_unrutted_partial_crossings/package.md). Current contracts, not closed packages, govern behavior.

## Deliverables and execution

- [Active ExecPlan](prompts/active/roads_code_quality_refactor_execplan.md)
- [Tracker](tracker.md)
- [Baseline and extraction map](artifacts/baseline.md)
- Production extraction, regression coverage, artifact parity receipts, reviews, and module documentation (final acceptance pending).

This is a multi-milestone effort. Local acceptance, remote integration, publication, and deployment are separate states; no deployment is included. Use `docs/standards/integration-history-governance.md` for any later integration receipt.
