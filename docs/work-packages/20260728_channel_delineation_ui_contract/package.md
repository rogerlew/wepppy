# Channel Delineation Controller Contract

**Status**: In progress
**Timezone**: UTC
**Package ID**: DOM-05
**Parent**: `20260716_pure_ui_contract_standardization_c`
**Security impact**: `high` if a production patch reaches the upload, route, or
RQ boundary; current audit scope is tests and documentation only

## Purpose

Audit the Channel Delineation controller from actual rendered controls through
the browser request, Watershed persistence, RQ execution, and reload. A user
must be able to select a valid channel configuration, build channels, and see
the durable configuration on reload.

## Scope

The audit covers actual template identity/state, the legacy and GL channel
controllers, request payloads, Watershed persistence, and the fetch/build RQ
boundary for DEM mode, MCL, CSA, stream pruning, depression smoothing, and
breach least-cost distance.

REM-05 supplies existing evidence for depression smoothing. It is not reopened
or broadened. Algorithms, defaults, enum values, map orchestration, upload
validation rules, queue wiring, authorization, CSRF, and NoDb schema changes
are excluded unless a focused test proves a production conformance mismatch.

## Acceptance

- Actual-template tests prove each risk-bearing field's submitted identity and
  selected/reloaded state.
- The legacy and GL controllers serialize the canonical values.
- Applicable persistence and RQ tests prove durable values cross the worker
  boundary.
- Any production repair is minimal, backward-compatible, reviewed in
  proportion to its actual risk, and covered by a regression test.
- Existing applicable frontend/backend gates pass.

## Decision

The operator authorized a sequential DOM-05 audit on 2026-07-28. This package
uses direct tests and no registry, generated manifest, or shared helper unless
repetition demonstrates a smaller, clearer test aid is necessary.
