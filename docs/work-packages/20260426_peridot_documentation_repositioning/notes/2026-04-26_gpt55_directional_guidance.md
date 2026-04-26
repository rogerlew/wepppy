# GPT-5.5 Directional Guidance (2026-04-26)

This note captures user-provided framing constraints that must guide Peridot documentation revisions in this package.

## Core Positioning

Peridot should not be documented as a simple TOPAZ/TOP2WEPP replacement. Required framing:

- category shift from implicit raster segmentation to explicit graph abstraction
- topology as first-class structure (nodes, edges, relationships)
- decoupled abstraction layer (not tightly bound to a single physics kernel)
- execution design that supports iterative/composable and distributed workflows

## Narrative Corrections to Enforce

- Replace "modern reimplementation" language with "abstraction-layer shift" language.
- Explain why prior messaging is invisible to legacy mental models (TOPAZ/TOP2WEPP baseline assumptions).
- Make clear that visible user outcomes (speed, hillslope count) are downstream effects of deeper architectural changes.

## Required Communication Kit

Documentation set should provide:

1. One clean claim statement:
   - legacy model: raster/implicit abstraction
   - Peridot model: graph/explicit abstraction
2. One comparison-figure specification:
   - same watershed represented in legacy discretization vs Peridot graph terms
3. Three metric definitions:
   - element-count/scalability behavior
   - topology correctness/flexibility
   - execution parallelization potential

## Claim Discipline

Use claim labels in notes/artifacts when needed:

- `confirmed`: directly evidenced by code or measured artifact
- `inference`: reasoned from observed behavior/architecture
- `hypothesis`: directional statement requiring dedicated benchmark/publication follow-up

Do not present inference/hypothesis claims as measured results.
