# Disturbed lookup runbook refactor

## Purpose and plan

Starting from local master, characterize the public runbook with deterministic client responses. Record the calls and generated files. Split artifact parsing and evidence generation out of the entry point and share repeated stage operations. Run the focused tests again and compare the same outputs before integrating locally.

## Progress

- [x] Locate the package export and live pytest entry point.
- [x] Characterize success and failure.
- [x] Extract and validate.

## Surprises & Discoveries

The manifest points to an opt-in live service. Its login page returned HTTP 503 during baseline inspection.

## Decision Log

Use a repeatable offline replay for exact call and evidence comparison. Keep the existing live test available for service verification.

## Outcomes & Retrospective

Four scoped replay cases reproduced the original client calls and both generated evidence files. The isolated pytest run passed all four and skipped the opt-in live test. See the [tracker](../../tracker.md) for measurements, test commands, and validation limits.
