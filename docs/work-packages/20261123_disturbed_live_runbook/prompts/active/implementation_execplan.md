# Disturbed lookup runbook refactor

## Purpose and plan

Starting from local master, characterize the public runbook with deterministic client responses. Record the calls and generated files. Split artifact parsing and evidence generation out of the entry point and share repeated stage operations. Run the focused tests again and compare the same outputs before integrating locally.

## Progress

- [x] Locate the package export and live pytest entry point.
- [ ] Characterize success and failure.
- [ ] Extract and validate.

## Surprises & Discoveries

The manifest points to an opt-in live service. Its login page returned HTTP 503 during baseline inspection.

## Decision Log

Use a repeatable offline replay for exact call and evidence comparison. Keep the existing live test available for service verification.

## Outcomes & Retrospective

Pending validation.
